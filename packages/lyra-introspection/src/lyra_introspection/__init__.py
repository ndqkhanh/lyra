"""Introspection — self-consciousness monitoring, meta-cognition awareness tracking."""
from __future__ import annotations
import logging, time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)
__all__ = ["CognitiveState", "IntrospectionEngine"]

@dataclass
class CognitiveState:
    is_processing: bool = False
    current_task: str = ""
    confidence: float = 0.5
    cognitive_load: float = 0.0
    errors_this_session: int = 0
    tasks_completed: int = 0

class IntrospectionEngine:
    def __init__(self):
        self._state = CognitiveState()
        self._history: list[CognitiveState] = []

    def begin_task(self, task: str) -> None:
        self._state.is_processing = True
        self._state.current_task = task
        self._state.cognitive_load = min(1.0, self._state.cognitive_load + 0.1)
        self._snapshot()

    def complete_task(self, success: bool) -> None:
        self._state.is_processing = False
        self._state.tasks_completed += 1
        if not success: self._state.errors_this_session += 1
        self._state.cognitive_load = max(0.0, self._state.cognitive_load - 0.15)
        self._snapshot()

    def check_overload(self) -> bool:
        return self._state.cognitive_load > 0.8

    def get_state(self) -> CognitiveState:
        return self._state

    def _snapshot(self) -> None:
        self._history.append(CognitiveState(**{k: v for k, v in self._state.__dict__.items() if not k.startswith('_')}))

    @property
    def stats(self) -> dict[str, Any]:
        return {"tasks_completed": self._state.tasks_completed, "errors": self._state.errors_this_session, "current_load": self._state.cognitive_load, "history_length": len(self._history)}
