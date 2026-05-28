"""Autonomous state machine for Lyra.

Defines a finite-state machine with states: IDLE, PLANNING, EXECUTING,
VERIFYING, RECOVERING, COMPLETED, BLOCKED.  Each transition can be
guarded by a callable predicate, and listeners are notified on every
transition.
"""

from __future__ import annotations

import enum
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


class AutonomyState(enum.Enum):
    """All possible states of the Lyra autonomy engine."""

    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    RECOVERING = "recovering"
    COMPLETED = "completed"
    BLOCKED = "blocked"


# Guard predicate: receives current state and returns True if transition allowed
GuardFn = Callable[[AutonomyState], bool]
# Transition callback: receives from-state, to-state, and optional context
TransitionCallback = Callable[[AutonomyState, AutonomyState, dict[str, Any]], None]


@dataclass(frozen=True)
class StateTransition:
    """A single allowed transition in the state machine."""

    from_state: AutonomyState
    to_state: AutonomyState
    guard: GuardFn | None = None


class TransitionError(Exception):
    """Raised when a state transition is not allowed or a guard rejects it."""


def _default_transitions() -> list[StateTransition]:
    """Build the canonical transition table."""
    return [
        StateTransition(AutonomyState.IDLE, AutonomyState.PLANNING),
        StateTransition(AutonomyState.PLANNING, AutonomyState.EXECUTING),
        StateTransition(AutonomyState.PLANNING, AutonomyState.BLOCKED),
        StateTransition(AutonomyState.EXECUTING, AutonomyState.VERIFYING),
        StateTransition(AutonomyState.EXECUTING, AutonomyState.RECOVERING),
        StateTransition(AutonomyState.EXECUTING, AutonomyState.BLOCKED),
        StateTransition(AutonomyState.VERIFYING, AutonomyState.EXECUTING),
        StateTransition(AutonomyState.VERIFYING, AutonomyState.RECOVERING),
        StateTransition(AutonomyState.VERIFYING, AutonomyState.COMPLETED),
        StateTransition(AutonomyState.RECOVERING, AutonomyState.PLANNING),
        StateTransition(AutonomyState.RECOVERING, AutonomyState.BLOCKED),
        StateTransition(AutonomyState.BLOCKED, AutonomyState.PLANNING),
        StateTransition(AutonomyState.COMPLETED, AutonomyState.IDLE),
    ]


@dataclass
class StateMachine:
    """Finite-state machine for autonomy lifecycle.

    Attributes:
        state: The current :class:`AutonomyState`.
        transitions: Ordered list of allowed transitions.
        context: Arbitrary key-value store carried across transitions.
        listeners: Callables notified on every successful transition.
    """

    state: AutonomyState = AutonomyState.IDLE
    transitions: list[StateTransition] = field(default_factory=_default_transitions)
    context: dict[str, Any] = field(default_factory=dict)
    listeners: list[TransitionCallback] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def transition_to(
        self,
        target: AutonomyState,
        *,
        payload: dict[str, Any] | None = None,
    ) -> None:
        """Attempt to move to *target*, raising on failure."""
        allowed = [t for t in self.transitions if t.from_state == self.state and t.to_state == target]
        if not allowed:
            raise TransitionError(
                f"No allowed transition from {self.state.value!r} to {target.value!r}"
            )

        for rule in allowed:
            if rule.guard is not None and not rule.guard(self.state):
                raise TransitionError(
                    f"Guard rejected transition from {self.state.value!r} to {target.value!r}"
                )

        from_state = self.state
        self.state = target
        if payload:
            self.context.update(payload)

        self._notify(from_state, target)
        logger.info("state_transition: %s -> %s", from_state.value, target.value)

    def add_listener(self, cb: TransitionCallback) -> None:
        """Register a callback invoked on every successful transition."""
        self.listeners.append(cb)

    def remove_listener(self, cb: TransitionCallback) -> None:
        """Unregister a previously added listener."""
        self.listeners.remove(cb)

    def in_state(self, *states: AutonomyState) -> bool:
        """Return True if the machine is currently in one of *states*."""
        return self.state in states

    def reset(self) -> None:
        """Hard-reset the machine back to IDLE and clear context."""
        self.state = AutonomyState.IDLE
        self.context.clear()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _notify(self, from_state: AutonomyState, to_state: AutonomyState) -> None:
        for cb in self.listeners:
            try:
                cb(from_state, to_state, self.context)
            except Exception:
                logger.exception("state_machine_listener_failed")


