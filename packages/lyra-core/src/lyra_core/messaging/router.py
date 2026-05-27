"""Message router for pattern-based routing."""
import re
from typing import Callable

from lyra_core.messaging.message import Message


class MessageRouter:
    """Routes messages based on patterns.

    Supports glob-style patterns for message type matching.
    """

    def __init__(self) -> None:
        """Initialize message router."""
        self._routes: list[tuple[str, Callable[[Message], None]]] = []

    def add_route(
        self,
        pattern: str,
        handler: Callable[[Message], None],
    ) -> None:
        """Add route with pattern.

        Args:
            pattern: Pattern to match (supports * wildcard)
            handler: Handler function
        """
        self._routes.append((pattern, handler))

    def route(self, message: Message) -> None:
        """Route message to matching handlers.

        Args:
            message: Message to route
        """
        message_type_str = str(message.type.value)

        for pattern, handler in self._routes:
            if self._matches_pattern(message_type_str, pattern):
                handler(message)

    def _matches_pattern(self, message_type: str, pattern: str) -> bool:
        """Check if message type matches pattern.

        Args:
            message_type: Message type string
            pattern: Pattern with * wildcards

        Returns:
            True if matches
        """
        # Convert glob pattern to regex
        regex_pattern = pattern.replace(".", r"\.").replace("*", ".*")
        regex_pattern = f"^{regex_pattern}$"
        return bool(re.match(regex_pattern, message_type))
