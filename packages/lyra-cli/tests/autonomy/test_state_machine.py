"""Tests for the autonomous state machine."""

from __future__ import annotations

import pytest

from lyra_cli.autonomy.state_machine import (
    AutonomyState,
    StateMachine,
    StateTransition,
    TransitionError,
)


class TestStateMachine:
    """Suite: StateMachine transitions, guards, listeners, reset."""

    def test_initial_state_is_idle(self) -> None:
        sm = StateMachine()
        assert sm.state == AutonomyState.IDLE

    def test_valid_transition_idle_to_planning(self) -> None:
        sm = StateMachine()
        sm.transition_to(AutonomyState.PLANNING)
        assert sm.state == AutonomyState.PLANNING

    def test_invalid_transition_raises(self) -> None:
        sm = StateMachine()
        with pytest.raises(TransitionError):
            sm.transition_to(AutonomyState.COMPLETED)  # IDLE -> COMPLETED is not allowed

    def test_full_healthy_cycle(self) -> None:
        """IDLE -> PLANNING -> EXECUTING -> VERIFYING -> COMPLETED -> IDLE."""
        sm = StateMachine()
        sm.transition_to(AutonomyState.PLANNING)
        sm.transition_to(AutonomyState.EXECUTING)
        sm.transition_to(AutonomyState.VERIFYING)
        assert sm.state == AutonomyState.VERIFYING
        sm.transition_to(AutonomyState.COMPLETED)
        assert sm.state == AutonomyState.COMPLETED
        sm.transition_to(AutonomyState.IDLE)
        assert sm.state == AutonomyState.IDLE

    def test_blocked_path(self) -> None:
        """PLANNING -> BLOCKED -> PLANNING."""
        sm = StateMachine()
        sm.transition_to(AutonomyState.PLANNING)
        sm.transition_to(AutonomyState.BLOCKED)
        assert sm.state == AutonomyState.BLOCKED
        sm.transition_to(AutonomyState.PLANNING)
        assert sm.state == AutonomyState.PLANNING

    def test_recovery_path(self) -> None:
        """EXECUTING -> RECOVERING -> PLANNING."""
        sm = StateMachine()
        sm.transition_to(AutonomyState.PLANNING)
        sm.transition_to(AutonomyState.EXECUTING)
        sm.transition_to(AutonomyState.RECOVERING)
        assert sm.state == AutonomyState.RECOVERING
        sm.transition_to(AutonomyState.PLANNING)
        assert sm.state == AutonomyState.PLANNING

    def test_guard_rejects_transition(self) -> None:
        sm = StateMachine()
        # Add a guard that always returns False for a specific transition
        guarded = StateTransition(
            AutonomyState.IDLE,
            AutonomyState.PLANNING,
            guard=lambda s: False,
        )
        sm.transitions.append(guarded)
        with pytest.raises(TransitionError, match="Guard rejected"):
            sm.transition_to(AutonomyState.PLANNING)

    def test_listener_is_called_on_transition(self) -> None:
        sm = StateMachine()
        calls: list[tuple[AutonomyState, AutonomyState]] = []

        def listener(from_state: AutonomyState, to_state: AutonomyState, ctx: dict) -> None:
            calls.append((from_state, to_state))

        sm.add_listener(listener)
        sm.transition_to(AutonomyState.PLANNING)
        assert len(calls) == 1
        assert calls[0] == (AutonomyState.IDLE, AutonomyState.PLANNING)

    def test_listener_removal(self) -> None:
        sm = StateMachine()

        def listener(*args: object) -> None:
            pass

        sm.add_listener(listener)
        sm.remove_listener(listener)
        sm.transition_to(AutonomyState.PLANNING)
        # No assertion needed — removing a non-removed listener would raise

    def test_in_state_check(self) -> None:
        sm = StateMachine()
        assert sm.in_state(AutonomyState.IDLE)
        assert not sm.in_state(AutonomyState.PLANNING)
        sm.transition_to(AutonomyState.PLANNING)
        assert sm.in_state(AutonomyState.PLANNING, AutonomyState.IDLE)

    def test_reset(self) -> None:
        sm = StateMachine()
        sm.transition_to(AutonomyState.PLANNING)
        sm.context["key"] = "value"
        sm.reset()
        assert sm.state == AutonomyState.IDLE
        assert sm.context == {}

    def test_transition_payload_updates_context(self) -> None:
        sm = StateMachine()
        sm.transition_to(AutonomyState.PLANNING, payload={"goal": "test"})
        assert sm.context.get("goal") == "test"

    def test_listener_error_does_not_crash(self) -> None:
        sm = StateMachine()

        def broken(*args: object) -> None:
            raise RuntimeError("boom")

        sm.add_listener(broken)
        # Should not raise
        sm.transition_to(AutonomyState.PLANNING)
        assert sm.state == AutonomyState.PLANNING
