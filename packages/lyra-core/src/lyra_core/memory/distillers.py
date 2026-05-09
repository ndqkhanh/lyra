"""Concrete :class:`~lyra_core.memory.reasoning_bank.Distiller` implementations.

The reasoning bank ships a ``Distiller`` *Protocol* but no concrete
implementation: callers either bring their own (LLM-backed) or fall back
to ``_StubDistiller`` from the tests. That's friction nobody should have
to absorb when wiring the bank into a real session.

This module ships two production distillers:

- :class:`HeuristicDistiller` — deterministic, rule-based, **no LLM
  call**. Fits the v1.8 §3.2 contract: every trajectory yields at
  least one lesson, failures *must* yield an anti-skill. Used by the
  default agent-loop wiring so the bank fills up even when the user
  hasn't configured a smart-slot model for distillation.

- :class:`LLMDistiller` (Phase 2) — wraps any callable that takes a
  prompt and returns a JSON-shaped lesson list. Plug a smart-slot
  client into it for richer, language-model-quality lessons. Defined
  here as a typed scaffold; the prompt template lives at
  ``prompts/distiller.md`` (Phase 2 of the §3.2 roadmap).

Both implementations are deterministic for a fixed input — that's the
:class:`Distiller` contract and what the snapshot tests rely on.
"""
from __future__ import annotations

import hashlib
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Final

from .reasoning_bank import (
    Distiller,
    Lesson,
    Trajectory,
    TrajectoryOutcome,
    TrajectoryStep,
)

# ---------------------------------------------------------------------------
# Heuristic patterns
# ---------------------------------------------------------------------------

_TOOL_CALL_RE: Final = re.compile(r"^(tool_call|tool|edit)\b", re.IGNORECASE)
_FAIL_PAYLOAD_RE: Final = re.compile(
    r"\b(error|exception|traceback|failed|failure|denied|timeout)\b",
    re.IGNORECASE,
)
_PASS_PAYLOAD_RE: Final = re.compile(
    r"\b(passed|ok|success|verified|green)\b",
    re.IGNORECASE,
)
_TEST_PAYLOAD_RE: Final = re.compile(r"\bpytest\b|\btest_|\.test\.|\.spec\.", re.IGNORECASE)
_RECOVERY_HINT_RE: Final = re.compile(
    r"\b(retry|fix|fall ?back|workaround|use\s+\w+\s+instead)\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# HeuristicDistiller
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HeuristicDistiller(Distiller):
    """Deterministic distiller — no LLM, no network, fast.

    Emits up to two lessons per trajectory:

    1. **Polarity-matching lesson** (always emitted). For SUCCESS
       trajectories: a one-liner summarising the dominant tool sequence
       ("did X then Y to reach the artefact"). For FAILURE trajectories:
       the anti-skill ("X followed by Y led to <error excerpt>").

    2. **Recovery lesson** (FAILURE only, if a recovery hint is
       detectable in later steps). Captures the move that *would* have
       worked or that the trace started doing before time ran out — so
       the next attempt at the same task signature gets the hint up
       front instead of rediscovering it.

    The implementation is intentionally crude. Phase 3 will add a BM25
    re-ranker on top so duplicate lessons collapse before they hit the
    bank. The shape stays compatible.
    """

    max_body_chars: int = 280

    def distill(self, trajectory: Trajectory) -> Sequence[Lesson]:
        if not trajectory.steps:
            return self._empty_trajectory_fallback(trajectory)

        lessons: list[Lesson] = [self._primary_lesson(trajectory)]

        if trajectory.outcome is TrajectoryOutcome.FAILURE:
            recovery = self._recovery_lesson(trajectory)
            if recovery is not None:
                lessons.append(recovery)

        return tuple(lessons)

    def _primary_lesson(self, trajectory: Trajectory) -> Lesson:
        tool_steps = [s for s in trajectory.steps if _TOOL_CALL_RE.match(s.kind)]
        if tool_steps:
            sketch = " → ".join(self._step_summary(s) for s in tool_steps[:4])
        else:
            sketch = " → ".join(self._step_summary(s) for s in trajectory.steps[:4])

        if trajectory.outcome is TrajectoryOutcome.SUCCESS:
            title = f"Strategy: {self._task_title(trajectory)}"
            body = (
                f"Sequence that worked: {sketch}. "
                f"Final artefact size: {len(trajectory.final_artefact)} chars."
            )
        else:
            failure_excerpt = self._first_failure_excerpt(trajectory)
            title = f"Anti-skill: {self._task_title(trajectory)}"
            body = (
                f"Sequence that failed: {sketch}. "
                f"Symptom: {failure_excerpt}."
            )

        return self._build_lesson(
            trajectory=trajectory,
            polarity=trajectory.outcome,
            title=title,
            body=self._truncate(body),
            slot="primary",
        )

    def _recovery_lesson(self, trajectory: Trajectory) -> Lesson | None:
        recovery_step = next(
            (s for s in trajectory.steps if _RECOVERY_HINT_RE.search(s.payload)),
            None,
        )
        if recovery_step is None:
            return None

        title = f"Recovery hint: {self._task_title(trajectory)}"
        body = (
            f"Trace contained a recovery candidate at step {recovery_step.index}: "
            f"{self._truncate(recovery_step.payload, limit=160)}."
        )
        return self._build_lesson(
            trajectory=trajectory,
            polarity=TrajectoryOutcome.SUCCESS,
            title=title,
            body=self._truncate(body),
            slot="recovery",
        )

    def _empty_trajectory_fallback(self, trajectory: Trajectory) -> tuple[Lesson, ...]:
        """Even an empty trajectory must produce *some* lesson on failure.

        The §3.2 contract is `record(failure)` always yields ≥1 anti-skill;
        we honour it for the degenerate case so callers never have to
        special-case "did the bank actually grow?".
        """
        if trajectory.outcome is not TrajectoryOutcome.FAILURE:
            return ()
        title = f"Anti-skill: {self._task_title(trajectory)}"
        body = (
            "Trajectory ended in failure with no observed steps; the agent "
            "was unable to act on the task. Consider a different decomposition "
            "or check tool availability."
        )
        return (
            self._build_lesson(
                trajectory=trajectory,
                polarity=TrajectoryOutcome.FAILURE,
                title=title,
                body=self._truncate(body),
                slot="primary",
            ),
        )

    def _build_lesson(
        self,
        *,
        trajectory: Trajectory,
        polarity: TrajectoryOutcome,
        title: str,
        body: str,
        slot: str,
    ) -> Lesson:
        digest = hashlib.sha1(
            f"{trajectory.id}|{polarity.value}|{slot}|{title}".encode()
        ).hexdigest()[:12]
        return Lesson(
            id=f"l-{slot}-{digest}",
            polarity=polarity,
            title=title,
            body=body,
            task_signatures=(trajectory.task_signature,),
            source_trajectory_ids=(trajectory.id,),
        )

    @staticmethod
    def _task_title(trajectory: Trajectory) -> str:
        sig = trajectory.task_signature.strip() or "untitled-task"
        return sig if len(sig) <= 60 else sig[:59] + "…"

    @staticmethod
    def _step_summary(step: TrajectoryStep) -> str:
        head = step.payload.strip().splitlines()[0] if step.payload else step.kind
        head = head.strip()
        if len(head) > 60:
            head = head[:57] + "…"
        return head or step.kind

    @staticmethod
    def _first_failure_excerpt(trajectory: Trajectory) -> str:
        for step in trajectory.steps:
            if _FAIL_PAYLOAD_RE.search(step.payload):
                excerpt = step.payload.strip().splitlines()[0]
                return excerpt[:120] + ("…" if len(excerpt) > 120 else "")
        last = trajectory.steps[-1]
        excerpt = last.payload.strip().splitlines()[0] if last.payload else last.kind
        return excerpt[:120] + ("…" if len(excerpt) > 120 else "")

    def _truncate(self, body: str, *, limit: int | None = None) -> str:
        cap = limit if limit is not None else self.max_body_chars
        body = " ".join(body.split())
        if len(body) <= cap:
            return body
        return body[: cap - 1] + "…"


# ---------------------------------------------------------------------------
# LLMDistiller (Phase 2 scaffold)
# ---------------------------------------------------------------------------

LessonJSON = dict[str, str]
LLMCallable = Callable[[str], list[LessonJSON]]


@dataclass(frozen=True)
class LLMDistiller(Distiller):
    """Wraps a smart-slot LLM call to produce richer lessons.

    The contract is intentionally narrow: ``llm`` is any callable
    receiving the rendered prompt and returning a list of dicts with
    ``polarity``, ``title``, ``body`` keys (any extra keys ignored).
    Polarity may be ``"success"`` or ``"failure"``; everything else
    falls back to the trajectory's outcome.

    This Phase-2 distiller is **off the hot path** — wire it into
    ``PreSessionEnd`` (or a cron) rather than the agent loop so the
    extra LLM call doesn't add to per-turn latency.
    """

    llm: LLMCallable

    def distill(self, trajectory: Trajectory) -> Sequence[Lesson]:
        prompt = self._render_prompt(trajectory)
        try:
            payloads = list(self.llm(prompt))
        except Exception:
            return HeuristicDistiller().distill(trajectory)
        if not payloads:
            return HeuristicDistiller().distill(trajectory)
        out: list[Lesson] = []
        for idx, payload in enumerate(payloads):
            polarity_str = str(payload.get("polarity", trajectory.outcome.value)).lower()
            polarity = (
                TrajectoryOutcome.SUCCESS
                if polarity_str == "success"
                else TrajectoryOutcome.FAILURE
            )
            title = str(payload.get("title", "")).strip() or f"Lesson {idx}"
            body = str(payload.get("body", "")).strip() or "(no body)"
            digest = hashlib.sha1(
                f"{trajectory.id}|llm|{idx}|{title}".encode()
            ).hexdigest()[:12]
            out.append(
                Lesson(
                    id=f"l-llm-{digest}",
                    polarity=polarity,
                    title=title[:120],
                    body=body[:1024],
                    task_signatures=(trajectory.task_signature,),
                    source_trajectory_ids=(trajectory.id,),
                )
            )
        return tuple(out)

    @staticmethod
    def _render_prompt(trajectory: Trajectory) -> str:
        steps = "\n".join(
            f"  {s.index:02d} [{s.kind}] {s.payload[:200]}" for s in trajectory.steps
        )
        return (
            "You are a reasoning-memory distiller for the Lyra agent harness.\n"
            "Convert the trajectory below into 1-3 retrievable lessons. Each\n"
            "lesson must have polarity (success or failure), a short title,\n"
            "and a body that another agent could read in <10 seconds and\n"
            "apply on the next attempt at this kind of task.\n"
            "\n"
            f"Task signature: {trajectory.task_signature}\n"
            f"Outcome: {trajectory.outcome.value}\n"
            "Steps:\n"
            f"{steps}\n"
            "\n"
            "Return JSON: a list of {polarity, title, body} objects."
        )


__all__ = ["HeuristicDistiller", "LLMCallable", "LLMDistiller", "LessonJSON"]
