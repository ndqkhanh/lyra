"""SDLC workflow state machine.

Manages phase transitions and validates workflow state changes.
"""

from __future__ import annotations

from typing import Callable

from lyra_core.orchestration.workflow.models import SDLCPhase


class WorkflowStateMachine:
    """State machine for SDLC workflow phase transitions.

    Manages valid phase transitions and executes callbacks on state changes.
    """

    # Valid phase transitions
    _TRANSITIONS: dict[SDLCPhase, list[SDLCPhase]] = {
        SDLCPhase.DISCOVERY: [SDLCPhase.DESIGN, SDLCPhase.FAILED],
        SDLCPhase.DESIGN: [SDLCPhase.IMPLEMENTATION, SDLCPhase.DISCOVERY, SDLCPhase.FAILED],
        SDLCPhase.IMPLEMENTATION: [SDLCPhase.TESTING, SDLCPhase.FAILED],
        SDLCPhase.TESTING: [SDLCPhase.REVIEW, SDLCPhase.IMPLEMENTATION, SDLCPhase.FAILED],
        SDLCPhase.REVIEW: [SDLCPhase.COMPLETED, SDLCPhase.FAILED],
        SDLCPhase.COMPLETED: [],
        SDLCPhase.FAILED: [],
    }

    def __init__(self, initial_phase: SDLCPhase = SDLCPhase.DISCOVERY) -> None:
        """Initialize state machine.

        Args:
            initial_phase: Starting phase (default: DISCOVERY)
        """
        self._current_phase = initial_phase
        self._callbacks: dict[SDLCPhase, list[Callable[[SDLCPhase, SDLCPhase], None]]] = {}

    @property
    def current_phase(self) -> SDLCPhase:
        """Get current phase."""
        return self._current_phase

    def can_transition(self, target_phase: SDLCPhase) -> bool:
        """Check if transition to target phase is valid.

        Args:
            target_phase: Target phase

        Returns:
            True if transition is valid
        """
        return target_phase in self._TRANSITIONS[self._current_phase]

    def get_next_phases(self) -> list[SDLCPhase]:
        """Get list of valid next phases from current phase.

        Returns:
            List of valid next phases
        """
        return self._TRANSITIONS[self._current_phase].copy()

    def transition_to(self, target_phase: SDLCPhase) -> None:
        """Transition to target phase.

        Args:
            target_phase: Target phase

        Raises:
            ValueError: If transition is invalid
        """
        if not self.can_transition(target_phase):
            raise ValueError(
                f"Invalid transition from {self._current_phase.value} "
                f"to {target_phase.value}"
            )

        old_phase = self._current_phase
        self._current_phase = target_phase

        # Execute callbacks
        self._execute_callbacks(old_phase, target_phase)

    def register_callback(
        self,
        phase: SDLCPhase,
        callback: Callable[[SDLCPhase, SDLCPhase], None],
    ) -> None:
        """Register callback to execute when entering a phase.

        Args:
            phase: Phase to trigger callback
            callback: Callback function (old_phase, new_phase) -> None
        """
        if phase not in self._callbacks:
            self._callbacks[phase] = []
        self._callbacks[phase].append(callback)

    def _execute_callbacks(self, old_phase: SDLCPhase, new_phase: SDLCPhase) -> None:
        """Execute callbacks for phase transition.

        Args:
            old_phase: Previous phase
            new_phase: New phase
        """
        if new_phase in self._callbacks:
            for callback in self._callbacks[new_phase]:
                callback(old_phase, new_phase)

    def reset(self, phase: SDLCPhase = SDLCPhase.DISCOVERY) -> None:
        """Reset state machine to initial phase.

        Args:
            phase: Phase to reset to (default: DISCOVERY)
        """
        self._current_phase = phase

    @staticmethod
    def get_phase_progress(phase: SDLCPhase) -> float:
        """Get progress percentage for a phase.

        Args:
            phase: SDLC phase

        Returns:
            Progress as float (0.0 to 1.0)
        """
        progress_map = {
            SDLCPhase.DISCOVERY: 0.0,
            SDLCPhase.DESIGN: 0.2,
            SDLCPhase.IMPLEMENTATION: 0.4,
            SDLCPhase.TESTING: 0.7,
            SDLCPhase.REVIEW: 0.9,
            SDLCPhase.COMPLETED: 1.0,
            SDLCPhase.FAILED: 0.0,
        }
        return progress_map[phase]


__all__ = ["WorkflowStateMachine"]
