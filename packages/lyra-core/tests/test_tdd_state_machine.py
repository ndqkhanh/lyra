"""Red tests for the TDD state machine.

Contract (see docs/tdd-discipline.md):
    IDLE → PLAN → RED → GREEN → REFACTOR → SHIP
plus a loopback RED → GREEN → REFACTOR → RED allowed (new failing test)
and REFACTOR → SHIP only when full suite green.

These tests assert the transition table + illegal-transition rejection.
"""
from __future__ import annotations

import pytest

from lyra_core.tdd.state import (
    IllegalTDDTransition,
    TDDState,
    TDDStateMachine,
)


def test_initial_state_is_idle() -> None:
    sm = TDDStateMachine()
    assert sm.state is TDDState.IDLE


@pytest.mark.parametrize(
    "from_state, to_state",
    [
        (TDDState.IDLE, TDDState.PLAN),
        (TDDState.PLAN, TDDState.RED),
        (TDDState.RED, TDDState.GREEN),
        (TDDState.GREEN, TDDState.REFACTOR),
        (TDDState.REFACTOR, TDDState.SHIP),
        # loopback: refactor triggered a new failing test
        (TDDState.REFACTOR, TDDState.RED),
        # escape from GREEN back to RED when a new test is required
        (TDDState.GREEN, TDDState.RED),
    ],
)
def test_legal_transitions(from_state: TDDState, to_state: TDDState) -> None:
    sm = TDDStateMachine(initial=from_state)
    sm.transition(to_state, reason="legal")
    assert sm.state is to_state


@pytest.mark.parametrize(
    "from_state, to_state",
    [
        # cannot jump from IDLE straight to RED (must PLAN first)
        (TDDState.IDLE, TDDState.RED),
        # cannot jump from IDLE to GREEN
        (TDDState.IDLE, TDDState.GREEN),
        # cannot skip RED
        (TDDState.PLAN, TDDState.GREEN),
        # cannot go backwards from SHIP
        (TDDState.SHIP, TDDState.GREEN),
        (TDDState.SHIP, TDDState.RED),
        # cannot ship from RED (tests still failing!)
        (TDDState.RED, TDDState.SHIP),
        # cannot plan again once in RED/GREEN/REFACTOR without explicit reset
        (TDDState.GREEN, TDDState.PLAN),
    ],
)
def test_illegal_transitions_raise(from_state: TDDState, to_state: TDDState) -> None:
    sm = TDDStateMachine(initial=from_state)
    with pytest.raises(IllegalTDDTransition):
        sm.transition(to_state, reason="illegal")


def test_transition_records_history() -> None:
    sm = TDDStateMachine()
    sm.transition(TDDState.PLAN, reason="got a task")
    sm.transition(TDDState.RED, reason="wrote failing test")
    history = sm.history
    assert [h.to_state for h in history] == [TDDState.PLAN, TDDState.RED]
    assert all(h.reason for h in history), "every transition must carry a reason"


def test_transition_requires_reason() -> None:
    """Reasons are mandatory — they show up in the HIR trace for auditability."""
    sm = TDDStateMachine()
    with pytest.raises(ValueError):
        sm.transition(TDDState.PLAN, reason="")


def test_reset_returns_to_idle() -> None:
    sm = TDDStateMachine(initial=TDDState.SHIP)
    sm.reset(reason="new task")
    assert sm.state is TDDState.IDLE


def test_in_tdd_phase_helper() -> None:
    """Some hooks need to know quickly: are we in a TDD-active state?"""
    sm = TDDStateMachine()
    assert not sm.in_tdd_phase()
    sm.transition(TDDState.PLAN, reason="task")
    assert sm.in_tdd_phase()
    sm.transition(TDDState.RED, reason="t1")
    assert sm.in_tdd_phase()
    sm.transition(TDDState.GREEN, reason="t1 passing")
    assert sm.in_tdd_phase()
    sm.transition(TDDState.REFACTOR, reason="clean up")
    assert sm.in_tdd_phase()
    sm.transition(TDDState.SHIP, reason="done")
    assert not sm.in_tdd_phase()
