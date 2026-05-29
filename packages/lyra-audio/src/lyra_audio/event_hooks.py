"""
Event Hooks - Event-driven audio system.

Features:
- Event registration
- Hook execution
- Custom callbacks
"""

from collections.abc import Callable
from enum import Enum
from typing import Any


class LyraEvent(Enum):
    """Lyra audio events."""

    # Session events
    SESSION_START = "session_start"
    SESSION_END = "session_end"

    # Task events
    TASK_START = "task_start"
    TASK_COMPLETE = "task_complete"
    TASK_FAILED = "task_failed"

    # User interaction
    PROMPT_SUBMIT = "prompt_submit"
    PROMPT_CANCEL = "prompt_cancel"

    # Errors
    ERROR_GENERAL = "error_general"
    ERROR_SYNTAX = "error_syntax"
    ERROR_LOGIC = "error_logic"
    ERROR_NETWORK = "error_network"
    ERROR_RATE_LIMIT = "error_rate_limit"

    # System events
    CONTEXT_COMPACT = "context_compact"
    MEMORY_SAVE = "memory_save"
    CACHE_HIT = "cache_hit"

    # Achievements
    MILESTONE_10 = "milestone_10"
    MILESTONE_50 = "milestone_50"
    MILESTONE_100 = "milestone_100"
    STREAK_7 = "streak_7"
    PERFECT_DAY = "perfect_day"

    # Special
    EASTER_EGG = "easter_egg"
    RANDOM_FUN = "random_fun"


class EventHookSystem:
    """
    Event-driven audio hook system.

    Features:
    - Event registration
    - Hook execution
    - Custom callbacks
    """

    def __init__(self):
        """Initialize event hook system."""
        self.hooks: dict[str, list[Callable]] = {}
        self.sound_manager = None  # Will be set by SoundManager

    def register_hook(self, event: str, callback: Callable):
        """
        Register custom hook.

        Args:
            event: Event name
            callback: Callback function
        """
        if event not in self.hooks:
            self.hooks[event] = []
        self.hooks[event].append(callback)

    def unregister_hook(self, event: str, callback: Callable):
        """
        Unregister hook.

        Args:
            event: Event name
            callback: Callback function
        """
        if event in self.hooks and callback in self.hooks[event]:
            self.hooks[event].remove(callback)

    def trigger(self, event: str, context: dict[str, Any] | None = None):
        """
        Trigger event.

        Args:
            event: Event name
            context: Event context
        """
        context = context or {}

        # Play sound if sound manager is available
        if self.sound_manager:
            self.sound_manager.play_event(event)

        # Execute custom hooks
        if event in self.hooks:
            for hook in self.hooks[event]:
                try:
                    hook(context)
                except Exception:
                    pass  # Fail silently

    def clear_hooks(self, event: str | None = None):
        """
        Clear hooks.

        Args:
            event: Event name, or None to clear all
        """
        if event:
            self.hooks.pop(event, None)
        else:
            self.hooks.clear()

    def list_events(self) -> list[str]:
        """List all registered events."""
        return list(self.hooks.keys())
