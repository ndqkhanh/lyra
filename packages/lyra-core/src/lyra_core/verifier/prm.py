"""Process Reward Model (PRM) adapter (v1.8 Wave-2 §8.5).

Inspired by *Qwen2.5-Math-PRM* and the *Process Reward Model lessons* paper
(Qwen team, 2025 — mirrored under ``papers/qwen-process-reward-lessons.pdf``)
and OpenAI's earlier PRM800K corpus.

Where the *outcome* reward (``..tdd_reward``) only scores the final patch,
a *process* reward scores each intermediate reasoning step. That granularity
lets Lyra:

- abort obviously-broken trajectories early (saves tokens),
- give Tournament TTS (``..tts.tournament``) a much sharper discriminator,
- feed Confidence-Cascade (``..routing.cascade``) per-step confidence
  instead of a single final estimate.

The Lyra contract is *adapter*-style: the actual PRM (Qwen2.5-Math-PRM,
Critic-RM, or our future homegrown one) is plug-replaceable. v1.8 ships
the contract + a stub; v1.9 wires in Qwen2.5-Math-PRM behind a feature flag.
"""
from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol


class StepLabel(str, Enum):
    """The label space PRMs commonly emit."""

    GOOD = "good"
    NEUTRAL = "neutral"
    BAD = "bad"


@dataclass(frozen=True)
class PrmStepScore:
    """The PRM's verdict on a single step in a chain-of-thought."""

    step_index: int
    label: StepLabel
    score: float                 # [0, 1]; higher == better step
    rationale: str = ""


@dataclass(frozen=True)
class PrmTrajectoryScore:
    """Aggregated PRM verdict on a full reasoning trajectory."""

    overall: float               # [0, 1]; aggregated step scores
    worst_step_index: int
    worst_step_label: StepLabel
    step_scores: tuple[PrmStepScore, ...] = field(default_factory=tuple)


class PrmAdapter(Protocol):
    """Plug point for any concrete PRM (Qwen, Critic-RM, custom)."""

    def score_trajectory(self, steps: Sequence[str]) -> PrmTrajectoryScore: ...

    def score_step(self, step_index: int, step: str) -> PrmStepScore: ...


# ---------------------------------------------------------------------------
# Phase-1 heuristic fallback — `default_prm_adapter()`
# ---------------------------------------------------------------------------
#
# v1.9 Phase 1 will swap the default to a Qwen2.5-Math-PRM-7B-backed
# adapter behind a feature flag (see `papers/qwen-process-reward-lessons.pdf`).
# Until that ships — and on no-network / no-GPU CI runners forever —
# `default_prm_adapter()` returns a deterministic *heuristic* PRM that
# satisfies the property contract the test suite cares about (good
# arithmetic ≫ bad arithmetic) without requiring a model download. The
# heuristic is intentionally narrow: it scores arithmetic equalities by
# evaluating both sides safely; everything else falls back to NEUTRAL.
# Real-PRM behaviour on free-form reasoning is reserved for v1.9.

_ARITH_EXPR_RE = re.compile(
    r"^\s*([0-9+\-*/().\s]+?)\s*=\s*([0-9+\-*/().\s]+?)\s*$"
)
_SAFE_CHARS_RE = re.compile(r"^[0-9+\-*/().\s]+$")


def _safe_eval_arith(expr: str) -> float | None:
    """Evaluate a simple arithmetic expression, or ``None`` if unsafe.

    The whitelist (digits, ``+ - * / ( ) .`` and whitespace) is chosen so
    that ``eval`` cannot reach any name/attribute/call. We further harden
    by passing empty globals + locals so even number objects can't be
    coerced to anything dangerous.
    """
    if not _SAFE_CHARS_RE.match(expr):
        return None
    try:
        return float(eval(expr, {"__builtins__": {}}, {}))
    except Exception:
        return None


@dataclass
class HeuristicArithmeticPrm:
    """A deterministic PRM heuristic — Lyra's no-network fallback.

    *Not* a real PRM. Use :func:`default_prm_adapter` to obtain it; v1.9
    Phase 1 will replace the factory's return value with the real
    Qwen2.5-Math-PRM-7B adapter while preserving this class as the
    explicit no-network fallback (callers that need offline determinism
    can keep instantiating it directly).
    """

    correct_score: float = 0.95
    incorrect_score: float = 0.05
    neutral_score: float = 0.5

    def score_step(self, step_index: int, step: str) -> PrmStepScore:
        match = _ARITH_EXPR_RE.match(step)
        if match is not None:
            lhs = _safe_eval_arith(match.group(1))
            rhs = _safe_eval_arith(match.group(2))
            if lhs is not None and rhs is not None:
                if abs(lhs - rhs) < 1e-9:
                    return PrmStepScore(
                        step_index=step_index,
                        label=StepLabel.GOOD,
                        score=self.correct_score,
                        rationale=f"arithmetic-check: {lhs} == {rhs}",
                    )
                return PrmStepScore(
                    step_index=step_index,
                    label=StepLabel.BAD,
                    score=self.incorrect_score,
                    rationale=f"arithmetic-check: {lhs} != {rhs}",
                )
        return PrmStepScore(
            step_index=step_index,
            label=StepLabel.NEUTRAL,
            score=self.neutral_score,
            rationale="heuristic-fallback: not an arithmetic step",
        )

    def score_trajectory(self, steps: Sequence[str]) -> PrmTrajectoryScore:
        scored = tuple(
            self.score_step(idx, step) for idx, step in enumerate(steps)
        )
        if not scored:
            return PrmTrajectoryScore(
                overall=0.0,
                worst_step_index=-1,
                worst_step_label=StepLabel.NEUTRAL,
                step_scores=(),
            )
        worst = min(scored, key=lambda s: s.score)
        return PrmTrajectoryScore(
            overall=sum(s.score for s in scored) / len(scored),
            worst_step_index=worst.step_index,
            worst_step_label=worst.label,
            step_scores=scored,
        )


def default_prm_adapter() -> PrmAdapter:
    """Return Lyra's currently-installed default PRM adapter.

    v1.8 returns :class:`HeuristicArithmeticPrm` — deterministic, no
    network, satisfies the property contract on obvious arithmetic.
    v1.9 Phase 1 will swap this to a Qwen2.5-Math-PRM-7B-backed adapter
    behind a feature flag; the swap happens *here* so that downstream
    callers (Tournament TTS discriminator, Confidence-Cascade
    confidence source) keep seeing the same factory.
    """
    return HeuristicArithmeticPrm()
