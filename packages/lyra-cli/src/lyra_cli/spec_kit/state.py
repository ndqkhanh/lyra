"""Reactive state management for spec-kit flow."""

from __future__ import annotations
from typing import Callable

from .models import SpecKitState, Phase


class StateManager:
    """Manages SpecKitState with reactive updates."""

    def __init__(self):
        self._state = SpecKitState()
        self._listeners: list[Callable[[SpecKitState], None]] = []

    @property
    def state(self) -> SpecKitState:
        """Get current state."""
        return self._state

    def subscribe(self, listener: Callable[[SpecKitState], None]) -> None:
        """Subscribe to state changes."""
        self._listeners.append(listener)

    def update_phase(self, new_phase: Phase) -> None:
        """Update phase and notify listeners."""
        self._state.phase = new_phase
        self._notify()

    def update_draft(self, artifact: str, content: str) -> None:
        """Update draft content."""
        if artifact == "spec":
            self._state.spec_draft = content
        elif artifact == "plan":
            self._state.plan_draft = content
        elif artifact == "tasks":
            self._state.tasks_draft = content
        elif artifact == "constitution":
            self._state.constitution_draft = content
        self._notify()

    def reset(self) -> None:
        """Reset to idle state."""
        self._state = SpecKitState()
        self._notify()

    def _notify(self) -> None:
        """Notify all listeners of state change."""
        for listener in self._listeners:
            listener(self._state)
