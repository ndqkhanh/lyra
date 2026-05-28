"""Event dispatcher - Event routing and handling"""

from collections import defaultdict
from collections.abc import Callable

from .protocol import Event

EventHandler = Callable[[Event], None]


class EventDispatcher:
    """Event dispatcher for routing events to handlers

    Implements observer pattern for event-driven architecture.
    """

    def __init__(self):
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._global_handlers: list[EventHandler] = []

    def on(self, event_type: str, handler: EventHandler) -> None:
        """Register event handler for specific event type

        Args:
            event_type: Event type to listen for (e.g., "turn.started")
            handler: Callback function to handle event
        """
        self._handlers[event_type].append(handler)

    def on_any(self, handler: EventHandler) -> None:
        """Register global event handler for all events

        Args:
            handler: Callback function to handle any event
        """
        self._global_handlers.append(handler)

    def off(self, event_type: str, handler: EventHandler) -> None:
        """Unregister event handler

        Args:
            event_type: Event type
            handler: Handler to remove
        """
        if event_type in self._handlers:
            self._handlers[event_type].remove(handler)

    def emit(self, event: Event) -> None:
        """Emit event to all registered handlers

        Args:
            event: Event to emit
        """
        # Get event type from event
        event_type = getattr(event, "type", None)

        # Call global handlers
        for handler in self._global_handlers:
            try:
                handler(event)
            except Exception as e:
                print(f"Error in global handler: {e}")

        # Call specific handlers
        if event_type and event_type in self._handlers:
            for handler in self._handlers[event_type]:
                try:
                    handler(event)
                except Exception as e:
                    print(f"Error in handler for {event_type}: {e}")

    def clear(self) -> None:
        """Clear all handlers"""
        self._handlers.clear()
        self._global_handlers.clear()

    def handler_count(self, event_type: str | None = None) -> int:
        """Get number of registered handlers

        Args:
            event_type: Specific event type, or None for all handlers

        Returns:
            Number of handlers
        """
        if event_type is None:
            return len(self._global_handlers) + sum(
                len(handlers) for handlers in self._handlers.values()
            )
        return len(self._handlers.get(event_type, []))
