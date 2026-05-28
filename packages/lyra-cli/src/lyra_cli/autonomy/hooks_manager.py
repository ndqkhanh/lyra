"""Lifecycle hooks for Lyra autonomy.

Provides a plugin-based hook system that notifies registered handlers
on lifecycle events: on_start, on_complete, on_error, on_blocked,
on_resume.
"""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


class HookEvent(enum.Enum):
    """Lifecycle events the hook system dispatches."""

    ON_START = "on_start"
    ON_COMPLETE = "on_complete"
    ON_ERROR = "on_error"
    ON_BLOCKED = "on_blocked"
    ON_RESUME = "on_resume"


# Handler signature: receives the event and a mutable context dict.
HookHandler = Callable[[HookEvent, dict[str, Any]], None]


@dataclass
class HooksManager:
    """Manages lifecycle hook registration and dispatch.

    Handlers are invoked in registration order.  A failing handler does
    not prevent subsequent handlers from running; the error is logged.

    Usage::

        hooks = HooksManager()
        hooks.register(HookEvent.ON_START, my_start_handler)
        hooks.register(HookEvent.ON_ERROR, my_error_handler)

        # ... somewhere in the engine loop ...
        hooks.fire(HookEvent.ON_START, {"goal_id": "abc"})
    """

    handlers: dict[HookEvent, list[HookHandler]] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register(
        self,
        event: HookEvent,
        handler: HookHandler,
        *,
        name: str | None = None,
    ) -> None:
        """Register *handler* for *event*.

        Args:
            event: The lifecycle event to subscribe to.
            handler: Callable invoked when *event* fires.
            name: Optional human-readable label (used in logs).
        """
        if event not in self.handlers:
            self.handlers[event] = []
        self.handlers[event].append(handler)
        label = name or getattr(handler, "__name__", str(handler))
        logger.debug("hook_registered: event=%s handler=%s", event.value, label)

    def unregister(self, event: HookEvent, handler: HookHandler) -> bool:
        """Remove *handler* from *event*. Returns True if removed."""
        if event not in self.handlers:
            return False
        try:
            self.handlers[event].remove(handler)
            return True
        except ValueError:
            return False

    def fire(self, event: HookEvent, context: dict[str, Any] | None = None) -> None:
        """Invoke all handlers registered for *event*.

        Each handler receives the event and a mutable context dict that
        accumulates data across the lifecycle.
        """
        if event not in self.handlers:
            return

        ctx: dict[str, Any] = context if context is not None else {}
        for handler in self.handlers[event]:
            try:
                handler(event, ctx)
            except Exception:
                logger.exception(
                    "hook_handler_failed: event=%s handler=%s",
                    event.value,
                    getattr(handler, "__name__", str(handler)),
                )

    def registered_count(self, event: HookEvent | None = None) -> int:
        """Count registered handlers, optionally for a specific *event*."""
        if event is not None:
            return len(self.handlers.get(event, []))
        return sum(len(hs) for hs in self.handlers.values())

    def clear(self) -> None:
        """Remove all registered handlers."""
        self.handlers.clear()
