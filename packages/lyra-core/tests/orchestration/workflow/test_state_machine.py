"""Tests for workflow state machine."""

import pytest

from lyra_core.orchestration.workflow.models import SDLCPhase
from lyra_core.orchestration.workflow.state_machine import WorkflowStateMachine


class TestWorkflowStateMachine:
    """Test suite for WorkflowStateMachine."""

    def test_initial_phase(self) -> None:
        """Test state machine initializes with correct phase."""
        sm = WorkflowStateMachine(initial_phase=SDLCPhase.DISCOVERY)
        assert sm.current_phase == SDLCPhase.DISCOVERY

    def test_valid_transitions(self) -> None:
        """Test valid phase transitions."""
        sm = WorkflowStateMachine(initial_phase=SDLCPhase.DISCOVERY)

        # Discovery -> Design
        assert sm.can_transition(SDLCPhase.DESIGN)
        sm.transition_to(SDLCPhase.DESIGN)
        assert sm.current_phase == SDLCPhase.DESIGN

        # Design -> Implementation
        assert sm.can_transition(SDLCPhase.IMPLEMENTATION)
        sm.transition_to(SDLCPhase.IMPLEMENTATION)
        assert sm.current_phase == SDLCPhase.IMPLEMENTATION

        # Implementation -> Testing
        assert sm.can_transition(SDLCPhase.TESTING)
        sm.transition_to(SDLCPhase.TESTING)
        assert sm.current_phase == SDLCPhase.TESTING

        # Testing -> Review
        assert sm.can_transition(SDLCPhase.REVIEW)
        sm.transition_to(SDLCPhase.REVIEW)
        assert sm.current_phase == SDLCPhase.REVIEW

        # Review -> Completed
        assert sm.can_transition(SDLCPhase.COMPLETED)
        sm.transition_to(SDLCPhase.COMPLETED)
        assert sm.current_phase == SDLCPhase.COMPLETED

    def test_invalid_transitions(self) -> None:
        """Test invalid phase transitions are rejected."""
        sm = WorkflowStateMachine(initial_phase=SDLCPhase.DISCOVERY)

        # Cannot skip phases
        assert not sm.can_transition(SDLCPhase.IMPLEMENTATION)
        assert not sm.can_transition(SDLCPhase.TESTING)
        assert not sm.can_transition(SDLCPhase.REVIEW)
        assert not sm.can_transition(SDLCPhase.COMPLETED)

        # Cannot transition from terminal states
        sm.transition_to(SDLCPhase.DESIGN)
        sm.transition_to(SDLCPhase.IMPLEMENTATION)
        sm.transition_to(SDLCPhase.TESTING)
        sm.transition_to(SDLCPhase.REVIEW)
        sm.transition_to(SDLCPhase.COMPLETED)

        assert not sm.can_transition(SDLCPhase.DISCOVERY)
        assert not sm.can_transition(SDLCPhase.DESIGN)

    def test_transition_to_failed(self) -> None:
        """Test transition to FAILED state from any phase."""
        sm = WorkflowStateMachine(initial_phase=SDLCPhase.DISCOVERY)
        assert sm.can_transition(SDLCPhase.FAILED)
        sm.transition_to(SDLCPhase.FAILED)
        assert sm.current_phase == SDLCPhase.FAILED

        # Cannot transition from FAILED
        assert not sm.can_transition(SDLCPhase.DISCOVERY)

    def test_backward_transitions(self) -> None:
        """Test allowed backward transitions."""
        sm = WorkflowStateMachine(initial_phase=SDLCPhase.DISCOVERY)

        # Design can go back to Discovery
        sm.transition_to(SDLCPhase.DESIGN)
        assert sm.can_transition(SDLCPhase.DISCOVERY)
        sm.transition_to(SDLCPhase.DISCOVERY)
        assert sm.current_phase == SDLCPhase.DISCOVERY

        # Testing can go back to Implementation
        sm.transition_to(SDLCPhase.DESIGN)
        sm.transition_to(SDLCPhase.IMPLEMENTATION)
        sm.transition_to(SDLCPhase.TESTING)
        assert sm.can_transition(SDLCPhase.IMPLEMENTATION)
        sm.transition_to(SDLCPhase.IMPLEMENTATION)
        assert sm.current_phase == SDLCPhase.IMPLEMENTATION

    def test_invalid_transition_raises_error(self) -> None:
        """Test that invalid transitions raise ValueError."""
        sm = WorkflowStateMachine(initial_phase=SDLCPhase.DISCOVERY)

        with pytest.raises(ValueError, match="Invalid transition"):
            sm.transition_to(SDLCPhase.IMPLEMENTATION)

    def test_get_next_phases(self) -> None:
        """Test getting list of valid next phases."""
        sm = WorkflowStateMachine(initial_phase=SDLCPhase.DISCOVERY)

        next_phases = sm.get_next_phases()
        assert SDLCPhase.DESIGN in next_phases
        assert SDLCPhase.FAILED in next_phases
        assert len(next_phases) == 2

    def test_callbacks(self) -> None:
        """Test phase transition callbacks."""
        sm = WorkflowStateMachine(initial_phase=SDLCPhase.DISCOVERY)

        callback_called = []

        def on_design(old_phase: SDLCPhase, new_phase: SDLCPhase) -> None:
            callback_called.append((old_phase, new_phase))

        sm.register_callback(SDLCPhase.DESIGN, on_design)
        sm.transition_to(SDLCPhase.DESIGN)

        assert len(callback_called) == 1
        assert callback_called[0] == (SDLCPhase.DISCOVERY, SDLCPhase.DESIGN)

    def test_multiple_callbacks(self) -> None:
        """Test multiple callbacks for same phase."""
        sm = WorkflowStateMachine(initial_phase=SDLCPhase.DISCOVERY)

        callback_order = []

        def callback1(old: SDLCPhase, new: SDLCPhase) -> None:
            callback_order.append(1)

        def callback2(old: SDLCPhase, new: SDLCPhase) -> None:
            callback_order.append(2)

        sm.register_callback(SDLCPhase.DESIGN, callback1)
        sm.register_callback(SDLCPhase.DESIGN, callback2)
        sm.transition_to(SDLCPhase.DESIGN)

        assert callback_order == [1, 2]

    def test_reset(self) -> None:
        """Test resetting state machine."""
        sm = WorkflowStateMachine(initial_phase=SDLCPhase.DISCOVERY)
        sm.transition_to(SDLCPhase.DESIGN)
        sm.transition_to(SDLCPhase.IMPLEMENTATION)

        sm.reset()
        assert sm.current_phase == SDLCPhase.DISCOVERY

        sm.reset(SDLCPhase.TESTING)
        assert sm.current_phase == SDLCPhase.TESTING

    def test_get_phase_progress(self) -> None:
        """Test phase progress calculation."""
        assert WorkflowStateMachine.get_phase_progress(SDLCPhase.DISCOVERY) == 0.0
        assert WorkflowStateMachine.get_phase_progress(SDLCPhase.DESIGN) == 0.2
        assert WorkflowStateMachine.get_phase_progress(SDLCPhase.IMPLEMENTATION) == 0.4
        assert WorkflowStateMachine.get_phase_progress(SDLCPhase.TESTING) == 0.7
        assert WorkflowStateMachine.get_phase_progress(SDLCPhase.REVIEW) == 0.9
        assert WorkflowStateMachine.get_phase_progress(SDLCPhase.COMPLETED) == 1.0
        assert WorkflowStateMachine.get_phase_progress(SDLCPhase.FAILED) == 0.0

    def test_phase_validation(self) -> None:
        """Test phase validation logic."""
        sm = WorkflowStateMachine(initial_phase=SDLCPhase.DISCOVERY)

        # Valid forward progression
        assert sm.can_transition(SDLCPhase.DESIGN)
        assert not sm.can_transition(SDLCPhase.COMPLETED)

        # After transitioning
        sm.transition_to(SDLCPhase.DESIGN)
        assert sm.can_transition(SDLCPhase.IMPLEMENTATION)
        assert sm.can_transition(SDLCPhase.DISCOVERY)  # Can go back
        assert not sm.can_transition(SDLCPhase.TESTING)  # Cannot skip
