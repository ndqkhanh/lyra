"""Agent UX Framework — interaction patterns, feedback mechanisms, progressive disclosure.
"""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)
__all__ = ["UXPattern", "InteractionMode", "UXFramework"]

@dataclass
class UXPattern:
    name: str
    description: str
    context: str

class InteractionMode:
    CHAT = "chat"
    COMMAND = "command"
    VISUAL = "visual"
    AUTOMATIC = "automatic"
    HYBRID = "hybrid"

class UXFramework:
    def __init__(self):
        self.patterns: list[UXPattern] = []
        self._default_mode = InteractionMode.CHAT

    def register_pattern(self, name: str, description: str, context: str) -> UXPattern:
        p = UXPattern(name, description, context)
        self.patterns.append(p)
        return p

    def suggest_mode(self, task_type: str, user_expertise: float = 0.5) -> str:
        if user_expertise > 0.8: return InteractionMode.COMMAND
        if "visual" in task_type.lower(): return InteractionMode.VISUAL
        if "batch" in task_type.lower() or "cron" in task_type.lower(): return InteractionMode.AUTOMATIC
        return InteractionMode.CHAT

    @property
    def stats(self) -> dict[str, Any]:
        return {"patterns": len(self.patterns), "default_mode": self._default_mode}
