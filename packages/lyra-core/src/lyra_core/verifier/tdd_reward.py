"""TDD-Reward inference signal (v1.8 Wave-1 §3.4).

Inspired by *TDD-Bench-Verified* and the TDD-as-RL-reward thread that
emerged at NeurIPS 2025 (mirrored under ``papers/tdd-bench-verified.pdf``).

The intuition: in a TDD project, *the failing test* is a free, deterministic,
human-authored reward signal. Every attempt the agent produces can be scored
on `(tests written → tests now passing) / (tests touched)` without an LLM
judge in the loop.

Lyra v1.8 uses ``TddRewardSignal`` in three places:

1. **Tournament TTS** (``..tts.tournament``) — the discriminator's score
   is a convex combination of TDD reward + PRM step quality.
2. **ReasoningBank** (``..memory.reasoning_bank``) — failure trajectories
   are tagged with the offending test name so distillation can be specific.
3. **Confidence-Cascade** (``..routing.cascade``) — TDD reward gates
   whether the cascade escalates to a stronger model.

Phase 0: contract only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Protocol, Sequence


@dataclass(frozen=True)
class TddTestOutcome:
    """One row of test results before/after the agent's attempt.

    Named ``TddTestOutcome`` rather than ``TestOutcome`` so that pytest's
    ``python_classes = "Test*"`` collector doesn't mistake this dataclass
    for a test class when test modules import it.
    """

    nodeid: str            # e.g. "tests/test_foo.py::test_bar"
    was_failing_before: bool
    is_passing_after: bool
    is_new_test: bool = False        # introduced by the attempt itself


@dataclass(frozen=True)
class TddRewardSignal:
    """Numeric reward + the receipts that produced it.

    ``score`` is in [0, 1]. The constituent ratios are kept so downstream
    consumers (verifier UI, ReasoningBank, cascade router) can show
    *why* the attempt got the score it did.
    """

    score: float
    ratio_red_to_green: float        # red→green / total red
    ratio_green_kept_green: float     # green→green / total green-before
    new_tests_added: int
    sources: Sequence[TddTestOutcome] = field(default_factory=tuple)


class TddRewardComputer(Protocol):
    """Computes a ``TddRewardSignal`` from a pair of test runs.

    The contract is intentionally pure. Implementations may parse pytest
    JSON, JUnit XML, or anything else — the signature does not care.
    """

    def compute(self, outcomes: Sequence[TddTestOutcome]) -> TddRewardSignal: ...


def _validate(outcomes: Sequence[TddTestOutcome]) -> None:
    seen: set[str] = set()
    for o in outcomes:
        if o.nodeid in seen:
            raise ValueError(f"duplicate nodeid: {o.nodeid}")
        seen.add(o.nodeid)


_DEFAULT_WEIGHTS: Mapping[str, float] = {
    "red_to_green": 0.6,
    "green_kept": 0.3,
    "new_tests": 0.1,
}
_WEIGHT_KEYS = frozenset(_DEFAULT_WEIGHTS.keys())


def compute_tdd_reward(
    outcomes: Sequence[TddTestOutcome],
    *,
    weights: Mapping[str, float] | None = None,
) -> TddRewardSignal:
    """Compute the per-attempt TDD reward signal.

    The reward combines three first-class TDD intuitions:

        score = (Σ w_i * r_i for i in active) / (Σ w_i for i in active)

    where ``i`` ranges over three terms:

    - ``red_to_green`` — fraction of previously-failing tests now passing.
      Active iff there were any previously-failing tests.
    - ``green_kept``    — fraction of previously-passing tests still passing.
      Active iff there were any previously-passing tests.
    - ``new_tests``     — bonus term, contributes 1.0 only if the attempt
      added at least one new test. *Inactive* (dropped from both numerator
      and denominator) when no new test was added, so an attempt that just
      makes existing tests pass is not penalised for the absence of bonuses.

    A term is dropped from both numerator and denominator whenever either:
    (a) its denominator data is missing (e.g. no green-before tests), or
    (b) its weight is zero (operator opted out). Weights are floor-clamped
    to ``>= 0``; custom ``weights`` overrides the defaults key-wise.

    If no term is active (e.g. an empty outcome list), ``score == 0.0``.
    """
    _validate(outcomes)
    effective_weights = _normalise_weights(weights)

    red_before = [o for o in outcomes if o.was_failing_before]
    green_before = [o for o in outcomes if not o.was_failing_before]
    red_to_green = sum(1 for o in red_before if o.is_passing_after)
    green_kept = sum(1 for o in green_before if o.is_passing_after)
    new_tests_added = sum(1 for o in outcomes if o.is_new_test)

    ratio_red = (red_to_green / len(red_before)) if red_before else 0.0
    ratio_green = (green_kept / len(green_before)) if green_before else 0.0

    active: list[tuple[float, float]] = []
    if red_before and effective_weights["red_to_green"] > 0.0:
        active.append((effective_weights["red_to_green"], ratio_red))
    if green_before and effective_weights["green_kept"] > 0.0:
        active.append((effective_weights["green_kept"], ratio_green))
    if new_tests_added > 0 and effective_weights["new_tests"] > 0.0:
        active.append((effective_weights["new_tests"], 1.0))

    weight_sum = sum(w for w, _ in active)
    if weight_sum > 0:
        score = sum(w * r for w, r in active) / weight_sum
    else:
        score = 0.0

    return TddRewardSignal(
        score=score,
        ratio_red_to_green=ratio_red,
        ratio_green_kept_green=ratio_green,
        new_tests_added=new_tests_added,
        sources=tuple(outcomes),
    )


def _normalise_weights(weights: Mapping[str, float] | None) -> Mapping[str, float]:
    if weights is None:
        return dict(_DEFAULT_WEIGHTS)
    extra = set(weights.keys()) - _WEIGHT_KEYS
    if extra:
        raise ValueError(
            f"unknown weight key(s): {sorted(extra)!r}; allowed: {sorted(_WEIGHT_KEYS)!r}"
        )
    merged: dict[str, float] = dict(_DEFAULT_WEIGHTS)
    for key, value in weights.items():
        if value < 0:
            raise ValueError(f"weight {key!r} must be >= 0, got {value}")
        merged[key] = float(value)
    return merged
