"""v3.13 P0-3 — behaviour-shape guardrails.

Covers :mod:`lyra_core.contracts.guardrails`, the pure-decision
module stolen from ``nousresearch/hermes-agent``'s
``tool_guardrails.py`` (see
``docs/context-engineering-deep-research-v2.md`` §3.2 + §7 P0-3).

The contract under test:

* No events → OK.
* Same exact error repeated → WARN at 2×, HALT at 5×.
* Same tool failing (any error) → WARN at 3×, HALT at 8×.
* No-progress steps in a row → WARN at 2, HALT at 5.
* Worst verdict wins when multiple signals fire on the same event.
* A successful interruption resets every streak.
* No state, no side effects — every call with the same inputs
  returns the same result.
"""
from __future__ import annotations

import pytest

from lyra_core.contracts.guardrails import (
    BehaviourEnvelope,
    GuardrailVerdict,
    TraceEvent,
    evaluate,
)


# --- empty / no signal --------------------------------------------------- #


class TestEmptyAndOK:
    def test_no_events_returns_ok(self) -> None:
        res = evaluate([])
        assert res.verdict is GuardrailVerdict.OK
        assert res.streak == 0
        assert res.reason == ""

    def test_single_success_returns_ok(self) -> None:
        res = evaluate(
            [TraceEvent(tool="Read", failed=False, produced_progress=True)]
        )
        assert res.verdict is GuardrailVerdict.OK

    def test_failure_below_threshold_returns_ok(self) -> None:
        # exact_failure_warn_after=2; 1 failure is still OK.
        res = evaluate(
            [
                TraceEvent(
                    tool="Read", failed=True,
                    error_signature="ENOENT:/tmp/x",
                ),
            ]
        )
        assert res.verdict is GuardrailVerdict.OK


# --- exact-failure streak ------------------------------------------------ #


class TestExactFailureStreak:
    def _err(self, n: int, sig: str = "ENOENT:/tmp/x") -> list[TraceEvent]:
        return [
            TraceEvent(tool="Read", failed=True, error_signature=sig)
            for _ in range(n)
        ]

    def test_two_in_a_row_warns(self) -> None:
        res = evaluate(self._err(2))
        assert res.verdict is GuardrailVerdict.WARN
        assert res.streak == 2
        assert "same error repeated" in res.reason

    def test_five_in_a_row_halts(self) -> None:
        res = evaluate(self._err(5))
        assert res.verdict is GuardrailVerdict.HALT
        assert res.streak == 5

    def test_different_signatures_do_not_trip(self) -> None:
        events = [
            TraceEvent(
                tool="Read", failed=True,
                error_signature=f"ENOENT:/tmp/x{i}",
            )
            for i in range(4)
        ]
        # Same tool, same exit, but signatures all differ →
        # exact-failure doesn't trip. Same-tool *does* though (4 ≥ 3).
        res = evaluate(events)
        assert res.verdict is GuardrailVerdict.WARN
        assert "tool" in res.reason  # same-tool message, not exact-error

    def test_success_interruption_resets(self) -> None:
        events = (
            self._err(3)
            + [TraceEvent(tool="Read", failed=False)]
            + self._err(1)
        )
        # Tail: 1 failure → below warn threshold. The earlier streak
        # is forgotten because the success interrupted it.
        res = evaluate(events)
        assert res.verdict is GuardrailVerdict.OK


# --- same-tool-failure streak -------------------------------------------- #


class TestSameToolFailureStreak:
    def _err_varied(self, tool: str, n: int) -> list[TraceEvent]:
        return [
            TraceEvent(
                tool=tool, failed=True,
                error_signature=f"e{i}",  # distinct each time
            )
            for i in range(n)
        ]

    def test_three_in_a_row_warns(self) -> None:
        res = evaluate(self._err_varied("Shell", 3))
        assert res.verdict is GuardrailVerdict.WARN
        assert "'Shell'" in res.reason
        assert res.streak == 3

    def test_eight_in_a_row_halts(self) -> None:
        res = evaluate(self._err_varied("Shell", 8))
        assert res.verdict is GuardrailVerdict.HALT
        assert res.streak == 8

    def test_different_tool_breaks_streak(self) -> None:
        events = (
            self._err_varied("Shell", 4)
            + [TraceEvent(tool="Read", failed=True, error_signature="x")]
        )
        # Tail is just one 'Read' failure → below warn.
        res = evaluate(events)
        assert res.verdict is GuardrailVerdict.OK


# --- no-progress streak -------------------------------------------------- #


class TestNoProgressStreak:
    def _steps(self, n: int) -> list[TraceEvent]:
        return [
            TraceEvent(tool="Read", failed=False, produced_progress=False)
            for _ in range(n)
        ]

    def test_two_warns(self) -> None:
        res = evaluate(self._steps(2))
        assert res.verdict is GuardrailVerdict.WARN
        assert "no progress" in res.reason
        assert res.streak == 2

    def test_five_halts(self) -> None:
        res = evaluate(self._steps(5))
        assert res.verdict is GuardrailVerdict.HALT
        assert res.streak == 5

    def test_progress_step_resets(self) -> None:
        events = self._steps(4) + [
            TraceEvent(tool="Read", produced_progress=True)
        ]
        res = evaluate(events)
        assert res.verdict is GuardrailVerdict.OK


# --- worst-wins selection ------------------------------------------------ #


class TestWorstWins:
    def test_halt_beats_warn(self) -> None:
        # 5 same-error failures (HALT on exact) + same tool every
        # time. Both signals trigger; HALT must win.
        events = [
            TraceEvent(
                tool="Read", failed=True,
                error_signature="ENOENT:/tmp/x",
                produced_progress=False,
            )
            for _ in range(5)
        ]
        res = evaluate(events)
        assert res.verdict is GuardrailVerdict.HALT

    def test_warn_when_only_warn_fires(self) -> None:
        # 2 exact-error failures (WARN), 2 same-tool (WARN — but
        # under 3 so no same-tool fire), 2 no-progress (WARN).
        events = [
            TraceEvent(
                tool="Read", failed=True,
                error_signature="ENOENT:/tmp/x",
                produced_progress=False,
            )
            for _ in range(2)
        ]
        res = evaluate(events)
        assert res.verdict is GuardrailVerdict.WARN


# --- envelope customisation --------------------------------------------- #


class TestEnvelope:
    def test_custom_envelope_is_respected(self) -> None:
        env = BehaviourEnvelope(
            exact_failure_warn_after=1, exact_failure_block_after=2,
        )
        events = [
            TraceEvent(
                tool="x", failed=True, error_signature="e",
            )
        ]
        res = evaluate(events, env)
        # With warn_after=1, even a single failure warns.
        assert res.verdict is GuardrailVerdict.WARN

    def test_envelope_validates_monotonic_thresholds(self) -> None:
        # warn > block is invalid for every axis.
        with pytest.raises(ValueError):
            BehaviourEnvelope(
                exact_failure_warn_after=10,
                exact_failure_block_after=2,
            )
        with pytest.raises(ValueError):
            BehaviourEnvelope(
                same_tool_failure_warn_after=10,
                same_tool_failure_halt_after=2,
            )
        with pytest.raises(ValueError):
            BehaviourEnvelope(
                no_progress_warn_after=10,
                no_progress_block_after=2,
            )

    def test_envelope_defaults_match_hermes(self) -> None:
        # Defaults are documented in the v2 plan §7 P0-3; this is
        # the regression-guard so a drift gets a clean failure.
        env = BehaviourEnvelope()
        assert env.exact_failure_warn_after == 2
        assert env.exact_failure_block_after == 5
        assert env.same_tool_failure_warn_after == 3
        assert env.same_tool_failure_halt_after == 8
        assert env.no_progress_warn_after == 2
        assert env.no_progress_block_after == 5


# --- purity guarantee --------------------------------------------------- #


def test_evaluate_is_deterministic() -> None:
    """Pure-decision contract: same input → same output, every call."""
    events = [
        TraceEvent(tool="Read", failed=True, error_signature="x")
        for _ in range(3)
    ]
    a = evaluate(events)
    b = evaluate(events)
    c = evaluate(list(events))  # different list, same content
    assert a == b == c


def test_evaluate_does_not_mutate_input() -> None:
    events = [
        TraceEvent(tool="Read", failed=True, error_signature="x")
        for _ in range(3)
    ]
    before = list(events)
    evaluate(events)
    assert events == before
