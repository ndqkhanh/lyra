"""Phase O.7 — closed-loop SKILL.md optimizer.

Where ``lyra skill reflect`` does a one-shot LLM rewrite based on the
failure ledger, the optimizer runs an **iterative scored loop**:

    for round in 0..max_rounds:
        score = executor(current_md, scenarios)
        if score >= target_pass_rate: break
        analysis = analyst(current_md, failing_scenarios)
        mutation = mutator(current_md, analysis)
        new_md = apply(mutation, current_md)
        new_score = executor(new_md, scenarios)
        if new_score > score:
            accept (current_md = new_md)
        else:
            revert

The structure is borrowed from awesome-llm-apps'
``self-improving-agent-skills`` (Executor / Analyst / Mutator), pared
down to fit lyra's provider-pluggable, ledger-aware design.

Constraints we keep from the upstream pattern:

* **One mutation per round** — chosen from a small enum. Free-text
  rewrites drift; constrained mutations are debuggable.
* **Accept-or-revert** — never commit a regression.
* **Best-so-far in memory** — disk is only touched at the end, and
  only on ``--apply``.

I/O kept out of this module on purpose: the LLM is injected via the
:class:`LLMRunner` protocol (the CLI shim wires the real provider;
tests inject a stub). The mutations log is appended via callbacks so
this file never imports ``lyra_cli``.
"""
from __future__ import annotations

import difflib
import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional, Protocol


# ── Public schema ───────────────────────────────────────────────


class MutationStrategy(str, Enum):
    """The four constrained shapes a single round may emit.

    Borrowed verbatim from the upstream optimizer's Pydantic enum so
    SKILL.md mutations stay debuggable round-by-round. Free-text
    rewrites (which is what ``lyra skill reflect`` does) drift; this
    is the failure mode forcing the enum exists to prevent.
    """

    ADD_EXAMPLE = "add_example"
    ADD_CONSTRAINT = "add_constraint"
    RESTRUCTURE = "restructure"
    ADD_EDGE_CASE = "add_edge_case"


@dataclass(frozen=True)
class OptimizeScenario:
    """One prompt + binary eval criterion the executor scores against.

    ``eval_criterion`` should phrase the question so a yes-leaning
    answer means *the skill worked*. The executor LLM is asked to
    answer it with ``yes`` / ``no`` after observing the agent's
    response to ``prompt``.
    """

    prompt: str
    eval_criterion: str


@dataclass(frozen=True)
class FailureAnalysis:
    """Analyst output: what's wrong and which lever to pull.

    The analyst LLM is *forced* to pick exactly one strategy and one
    target section so the mutator below has an unambiguous brief.
    """

    diagnosis: str
    target_section: str
    strategy: MutationStrategy
    failing_scenarios: tuple[str, ...] = ()


@dataclass(frozen=True)
class SkillMutation:
    """Mutator output: one structured edit to SKILL.md.

    ``old_text`` and ``new_text`` are anchored snippets, not the full
    file. The applier (see :func:`_apply_mutation`) does a
    single-pass string replace; if ``old_text`` does not appear
    verbatim the mutation is rejected (``applied=False``) and the
    round is treated as a no-op revert.
    """

    strategy: MutationStrategy
    target_section: str
    old_text: str
    new_text: str
    reasoning: str = ""


@dataclass
class ScenarioResult:
    """Per-scenario outcome the executor reports back."""

    prompt: str
    passed: bool
    reason: str = ""


@dataclass
class OptimizeRound:
    """One iteration of the loop, captured for the mutation log."""

    round_no: int
    pre_score: float
    post_score: float
    analysis: Optional[FailureAnalysis] = None
    mutation: Optional[SkillMutation] = None
    accepted: bool = False
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "round_no": self.round_no,
            "pre_score": self.pre_score,
            "post_score": self.post_score,
            "analysis": (
                {
                    "diagnosis": self.analysis.diagnosis,
                    "target_section": self.analysis.target_section,
                    "strategy": self.analysis.strategy.value,
                    "failing_scenarios": list(self.analysis.failing_scenarios),
                }
                if self.analysis
                else None
            ),
            "mutation": (
                {
                    "strategy": self.mutation.strategy.value,
                    "target_section": self.mutation.target_section,
                    "old_text": self.mutation.old_text,
                    "new_text": self.mutation.new_text,
                    "reasoning": self.mutation.reasoning,
                }
                if self.mutation
                else None
            ),
            "accepted": self.accepted,
            "error": self.error,
        }


@dataclass
class OptimizeResult:
    """Full outcome of an :func:`optimize_skill` call."""

    skill_id: str
    initial_score: float
    final_score: float
    rounds: list[OptimizeRound] = field(default_factory=list)
    final_md: str = ""
    target_reached: bool = False

    @property
    def accepted_rounds(self) -> int:
        return sum(1 for r in self.rounds if r.accepted)

    @property
    def diff(self) -> str:
        """Unified diff from the initial body to ``final_md``."""
        return _unified_diff(self._initial_md, self.final_md)

    # Set by :func:`optimize_skill` for the diff property; not exposed
    # because external mutation of this field would lie about the loop.
    _initial_md: str = ""


# ── LLM protocol ────────────────────────────────────────────────


class LLMRunner(Protocol):
    """Minimal LLM interface the optimizer needs.

    ``call`` runs one synchronous completion against the provider and
    returns the raw text. The optimizer parses JSON out of the text
    itself rather than relying on provider-side structured-output
    support, because lyra's :mod:`lyra_cli.providers` adapter does
    not have a uniform Pydantic-output API yet — see survey notes.

    Implementations should:

    * Set ``temperature=0`` for determinism in scoring.
    * Honour cancellation if the caller raises; the optimizer does
      not need streaming.
    """

    def call(self, prompt: str, *, system: str = "", max_tokens: int = 2048) -> str:
        ...


# ── Prompt templates ────────────────────────────────────────────


_EXECUTOR_SYSTEM = """You are a strict evaluator. Given a SKILL.md and a user prompt,
imagine the agent followed the skill literally and produced a response.
Then judge whether the response would satisfy the eval criterion.
Reply with EXACTLY one JSON object: {"passed": true|false, "reason": "<one short sentence>"}.
No prose, no markdown fences, no extra keys."""


_EXECUTOR_TEMPLATE = """SKILL.md body:
---
{skill_body}
---

User prompt:
{prompt}

Eval criterion (yes-leaning answer means the skill worked):
{eval_criterion}

Respond with JSON only."""


_ANALYST_SYSTEM = """You diagnose why a SKILL.md is failing some scenarios.
Reply with EXACTLY one JSON object with keys:
  "diagnosis": one short sentence explaining the gap,
  "target_section": which section of the skill to edit (e.g. "examples", "steps", "header"),
  "strategy": ONE of ["add_example","add_constraint","restructure","add_edge_case"].
No prose, no markdown fences, no extra keys."""


_ANALYST_TEMPLATE = """SKILL.md body:
---
{skill_body}
---

Failing scenarios (prompt → why it failed):
{failures}

Pick exactly one mutation strategy and one target section."""


_MUTATOR_SYSTEM = """You make ONE small edit to a SKILL.md.
Reply with EXACTLY one JSON object with keys:
  "old_text": a verbatim snippet from the current SKILL.md (must appear exactly once),
  "new_text": the replacement,
  "reasoning": one short sentence on why this edit helps.
The edit must be a single contiguous string. Do not rewrite the whole file.
No prose, no markdown fences, no extra keys."""


_MUTATOR_TEMPLATE = """Current SKILL.md body:
---
{skill_body}
---

Diagnosis: {diagnosis}
Target section: {target_section}
Strategy: {strategy}

Propose the smallest edit that closes the gap. Return JSON only."""


# ── Core loop ────────────────────────────────────────────────────


MutationCallback = Callable[[OptimizeRound], None]


def optimize_skill(
    skill_id: str,
    *,
    current_md: str,
    scenarios: list[OptimizeScenario],
    llm: LLMRunner,
    max_rounds: int = 20,
    target_pass_rate: float = 1.0,
    on_round: Optional[MutationCallback] = None,
) -> OptimizeResult:
    """Run the Executor/Analyst/Mutator loop and return the trace.

    Pure of disk I/O — caller decides whether to write ``final_md``
    back via :mod:`lyra_skills.installer`. ``on_round`` fires after
    each round (accepted or rejected) so callers can stream
    progress to a terminal or persist a mutation log.

    Termination:

    * Pass rate hits ``target_pass_rate`` (default 1.0).
    * ``max_rounds`` reached. The upstream caps at 50; we default
      lower because every round costs at least ``len(scenarios)+2``
      LLM calls.
    * An LLM call raises. The exception bubbles after the in-progress
      round is recorded with ``error`` set.
    """
    if not scenarios:
        raise ValueError("optimize_skill needs at least one scenario")
    rounds_cap = max(1, min(int(max_rounds), 50))

    best_md = current_md
    best_score, _ = _score(best_md, scenarios, llm)
    initial_score = best_score

    result = OptimizeResult(
        skill_id=skill_id,
        initial_score=initial_score,
        final_score=initial_score,
        final_md=best_md,
    )
    object.__setattr__(result, "_initial_md", current_md)

    if best_score >= target_pass_rate:
        result.target_reached = True
        return result

    for round_no in range(1, rounds_cap + 1):
        pre_score = best_score
        pre_results = _score_detail(best_md, scenarios, llm)
        failures = [r for r in pre_results if not r.passed]
        if not failures:
            best_score = sum(1 for r in pre_results if r.passed) / len(pre_results)
            result.target_reached = True
            break

        round_state = OptimizeRound(
            round_no=round_no,
            pre_score=pre_score,
            post_score=pre_score,
        )

        try:
            analysis = _analyse(best_md, failures, llm)
            round_state.analysis = analysis
            mutation = _mutate(best_md, analysis, llm)
            round_state.mutation = mutation
            new_md, applied = _apply_mutation(best_md, mutation)
            if not applied:
                round_state.error = "mutation old_text not found verbatim"
                if on_round:
                    on_round(round_state)
                result.rounds.append(round_state)
                continue

            new_score, _ = _score(new_md, scenarios, llm)
            round_state.post_score = new_score
            if new_score > pre_score:
                best_md = new_md
                best_score = new_score
                round_state.accepted = True
                if new_score >= target_pass_rate:
                    if on_round:
                        on_round(round_state)
                    result.rounds.append(round_state)
                    result.target_reached = True
                    break
        except Exception as e:  # noqa: BLE001 — surface error per round
            round_state.error = f"{type(e).__name__}: {e}"
            if on_round:
                on_round(round_state)
            result.rounds.append(round_state)
            raise

        if on_round:
            on_round(round_state)
        result.rounds.append(round_state)

    result.final_md = best_md
    result.final_score = best_score
    return result


# ── Executor ─────────────────────────────────────────────────────


def _score(
    skill_body: str,
    scenarios: list[OptimizeScenario],
    llm: LLMRunner,
) -> tuple[float, list[ScenarioResult]]:
    results = _score_detail(skill_body, scenarios, llm)
    if not results:
        return 0.0, results
    passed = sum(1 for r in results if r.passed)
    return passed / len(results), results


def _score_detail(
    skill_body: str,
    scenarios: list[OptimizeScenario],
    llm: LLMRunner,
) -> list[ScenarioResult]:
    out: list[ScenarioResult] = []
    for sc in scenarios:
        prompt = _EXECUTOR_TEMPLATE.format(
            skill_body=skill_body,
            prompt=sc.prompt,
            eval_criterion=sc.eval_criterion,
        )
        raw = llm.call(prompt, system=_EXECUTOR_SYSTEM, max_tokens=200)
        data = _parse_json_obj(raw)
        passed = bool(data.get("passed"))
        reason = str(data.get("reason", "") or "")
        out.append(ScenarioResult(prompt=sc.prompt, passed=passed, reason=reason))
    return out


# ── Analyst ──────────────────────────────────────────────────────


def _analyse(
    skill_body: str,
    failures: list[ScenarioResult],
    llm: LLMRunner,
) -> FailureAnalysis:
    failure_lines = "\n".join(
        f"- prompt={r.prompt!r}  reason={r.reason!r}" for r in failures[:8]
    )
    prompt = _ANALYST_TEMPLATE.format(
        skill_body=skill_body,
        failures=failure_lines or "(no failures captured)",
    )
    raw = llm.call(prompt, system=_ANALYST_SYSTEM, max_tokens=400)
    data = _parse_json_obj(raw)
    strategy_raw = str(data.get("strategy") or "").strip().lower()
    try:
        strategy = MutationStrategy(strategy_raw)
    except ValueError as e:
        raise ValueError(
            f"analyst returned unknown strategy: {strategy_raw!r} "
            f"(expected one of {[s.value for s in MutationStrategy]})"
        ) from e
    return FailureAnalysis(
        diagnosis=str(data.get("diagnosis") or "").strip(),
        target_section=str(data.get("target_section") or "").strip(),
        strategy=strategy,
        failing_scenarios=tuple(r.prompt for r in failures),
    )


# ── Mutator ──────────────────────────────────────────────────────


def _mutate(
    skill_body: str,
    analysis: FailureAnalysis,
    llm: LLMRunner,
) -> SkillMutation:
    prompt = _MUTATOR_TEMPLATE.format(
        skill_body=skill_body,
        diagnosis=analysis.diagnosis,
        target_section=analysis.target_section,
        strategy=analysis.strategy.value,
    )
    raw = llm.call(prompt, system=_MUTATOR_SYSTEM, max_tokens=800)
    data = _parse_json_obj(raw)
    return SkillMutation(
        strategy=analysis.strategy,
        target_section=analysis.target_section,
        old_text=str(data.get("old_text") or ""),
        new_text=str(data.get("new_text") or ""),
        reasoning=str(data.get("reasoning") or "").strip(),
    )


# ── Mutation application ────────────────────────────────────────


def _apply_mutation(skill_body: str, mutation: SkillMutation) -> tuple[str, bool]:
    """Apply *mutation* via single-pass string replacement.

    Returns ``(new_body, applied)``. ``applied`` is ``False`` when
    ``old_text`` is empty or doesn't appear verbatim or appears more
    than once — single-pass anchoring is how we keep the edit
    auditable.
    """
    if not mutation.old_text:
        return skill_body, False
    count = skill_body.count(mutation.old_text)
    if count != 1:
        return skill_body, False
    return skill_body.replace(mutation.old_text, mutation.new_text), True


# ── JSON parsing ────────────────────────────────────────────────


_FENCE_RE = re.compile(r"^```(?:json)?\s*\n?(.*?)\n?```\s*$", re.DOTALL)


def _parse_json_obj(raw: str) -> dict[str, Any]:
    """Best-effort JSON extraction from a model response.

    Models sometimes wrap output in triple-backtick ``json`` fences
    despite the system prompt asking otherwise. We strip those first
    and fall back to extracting the first ``{...}`` substring if the
    whole body isn't valid JSON. Anything that still doesn't parse
    becomes ``{}`` — the caller decides what to do with an empty
    dict (analyst raises, executor treats as ``passed=False``).
    """
    text = (raw or "").strip()
    fence = _FENCE_RE.match(text)
    if fence:
        text = fence.group(1).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            return {}
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return {}
    return data if isinstance(data, dict) else {}


# ── Diffing ──────────────────────────────────────────────────────


def _unified_diff(a: str, b: str) -> str:
    return "".join(
        difflib.unified_diff(
            a.splitlines(keepends=True),
            b.splitlines(keepends=True),
            fromfile="SKILL.md.before",
            tofile="SKILL.md.after",
            n=2,
        )
    )


__all__ = [
    "FailureAnalysis",
    "LLMRunner",
    "MutationStrategy",
    "OptimizeResult",
    "OptimizeRound",
    "OptimizeScenario",
    "ScenarioResult",
    "SkillMutation",
    "optimize_skill",
]
