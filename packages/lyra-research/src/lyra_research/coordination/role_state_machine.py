"""Role state machine for managing role lifecycle.

States:
- PENDING: Role is waiting to start
- RUNNING: Role is currently executing
- WAITING: Role is waiting for dependencies
- COMPLETED: Role finished successfully
- FAILED: Role execution failed
- RETRYING: Role is retrying after failure
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum


class RoleState(str, Enum):
    """States in the role lifecycle."""

    PENDING = "pending"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass(frozen=True)
class RoleTransition:
    """Transition between role states.

    Attributes:
        from_state: Starting state
        to_state: Target state
        condition: Function that returns True if transition is allowed
        action: Function to execute during transition
    """

    from_state: RoleState
    to_state: RoleState
    condition: Callable[[], bool]
    action: Callable[[], None] | None = None

    def can_transition(self) -> bool:
        """Check if transition is allowed."""
        return self.condition()

    def execute(self) -> None:
        """Execute transition action."""
        if self.action:
            self.action()


class RoleStateMachine:
    """State machine for managing role lifecycle.

    Manages state transitions with validation and actions.
    """

    def __init__(self) -> None:
        """Initialize state machine with default transitions."""
        self._transitions: dict[tuple[RoleState, str], RoleTransition] = {}
        self._current_state: dict[str, RoleState] = {}
        self._setup_default_transitions()

    def _setup_default_transitions(self) -> None:
        """Setup default state transitions."""
        # PENDING → RUNNING
        self.add_transition(
            RoleTransition(
                from_state=RoleState.PENDING,
                to_state=RoleState.RUNNING,
                condition=lambda: True,
            ),
            event="start",
        )

        # RUNNING → COMPLETED
        self.add_transition(
            RoleTransition(
                from_state=RoleState.RUNNING,
                to_state=RoleState.COMPLETED,
                condition=lambda: True,
            ),
            event="complete",
        )

        # RUNNING → FAILED
        self.add_transition(
            RoleTransition(
                from_state=RoleState.RUNNING,
                to_state=RoleState.FAILED,
                condition=lambda: True,
            ),
            event="fail",
        )

        # RUNNING → WAITING
        self.add_transition(
            RoleTransition(
                from_state=RoleState.RUNNING,
                to_state=RoleState.WAITING,
                condition=lambda: True,
            ),
            event="wait",
        )

        # WAITING → RUNNING
        self.add_transition(
            RoleTransition(
                from_state=RoleState.WAITING,
                to_state=RoleState.RUNNING,
                condition=lambda: True,
            ),
            event="resume",
        )

        # FAILED → RETRYING
        self.add_transition(
            RoleTransition(
                from_state=RoleState.FAILED,
                to_state=RoleState.RETRYING,
                condition=lambda: True,
            ),
            event="retry",
        )

        # RETRYING → RUNNING
        self.add_transition(
            RoleTransition(
                from_state=RoleState.RETRYING,
                to_state=RoleState.RUNNING,
                condition=lambda: True,
            ),
            event="start",
        )

    def add_transition(self, transition: RoleTransition, event: str) -> None:
        """Add a state transition.

        Args:
            transition: Transition to add
            event: Event that triggers the transition
        """
        key = (transition.from_state, event)
        self._transitions[key] = transition

    def get_state(self, role_name: str) -> RoleState:
        """Get current state of a role.

        Args:
            role_name: Name of the role

        Returns:
            Current state (defaults to PENDING)
        """
        return self._current_state.get(role_name, RoleState.PENDING)

    def set_state(self, role_name: str, state: RoleState) -> None:
        """Set state of a role.

        Args:
            role_name: Name of the role
            state: New state
        """
        self._current_state[role_name] = state

    def transition(self, role_name: str, event: str) -> tuple[bool, str | None]:
        """Execute state transition for a role.

        Args:
            role_name: Name of the role
            event: Event triggering the transition

        Returns:
            Tuple of (success, error_message)
        """
        current_state = self.get_state(role_name)
        key = (current_state, event)

        # Check if transition exists
        if key not in self._transitions:
            return False, f"No transition from {current_state.value} on event '{event}'"

        transition = self._transitions[key]

        # Check if transition is allowed
        if not transition.can_transition():
            return (
                False,
(
                    f"Transition condition not met for {current_state.value} → "
                    f"{transition.to_state.value}"
                ),
            )

        # Execute transition
        try:
            transition.execute()
            self.set_state(role_name, transition.to_state)
            return True, None
        except Exception as e:
            return False, f"Transition action failed: {str(e)}"

    def can_transition(self, role_name: str, event: str) -> bool:
        """Check if a transition is possible.

        Args:
            role_name: Name of the role
            event: Event to check

        Returns:
            True if transition is possible
        """
        current_state = self.get_state(role_name)
        key = (current_state, event)

        if key not in self._transitions:
            return False

        return self._transitions[key].can_transition()

    def get_available_events(self, role_name: str) -> list[str]:
        """Get available events for a role in its current state.

        Args:
            role_name: Name of the role

        Returns:
            List of available event names
        """
        current_state = self.get_state(role_name)
        events = []

        for (state, event), transition in self._transitions.items():
            if state == current_state and transition.can_transition():
                events.append(event)

        return events

    def reset(self, role_name: str) -> None:
        """Reset role to PENDING state.

        Args:
            role_name: Name of the role
        """
        self.set_state(role_name, RoleState.PENDING)

    def reset_all(self) -> None:
        """Reset all roles to PENDING state."""
        self._current_state.clear()
