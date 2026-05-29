"""Event bus for publish-subscribe messaging."""

from collections import defaultdict
from collections.abc import Awaitable, Callable

from lyra_core.messaging.message import Message
from lyra_core.messaging.types import MessageType


class EventBus:
    """Event bus for cross-component communication.

    Supports both synchronous and asynchronous message handlers.
    """

    def __init__(self) -> None:
        """Initialize event bus."""
        self._handlers: dict[MessageType, list[Callable[[Message], None]]] = defaultdict(list)
        self._async_handlers: dict[MessageType, list[Callable[[Message], Awaitable[None]]]] = (
            defaultdict(list)
        )
        self._error_handler: Callable[[Exception], None] | None = None

    def subscribe(
        self,
        message_type: MessageType,
        handler: Callable[[Message], None],
    ) -> None:
        """Subscribe handler to message type.

        Args:
            message_type: Type of message to subscribe to
            handler: Handler function
        """
        self._handlers[message_type].append(handler)

    def unsubscribe(
        self,
        message_type: MessageType,
        handler: Callable[[Message], None],
    ) -> None:
        """Unsubscribe handler from message type.

        Args:
            message_type: Type of message to unsubscribe from
            handler: Handler function to remove
        """
        if handler in self._handlers[message_type]:
            self._handlers[message_type].remove(handler)

    def subscribe_async(
        self,
        message_type: MessageType,
        handler: Callable[[Message], Awaitable[None]],
    ) -> None:
        """Subscribe async handler to message type.

        Args:
            message_type: Type of message to subscribe to
            handler: Async handler function
        """
        self._async_handlers[message_type].append(handler)

    def publish(self, message: Message) -> None:
        """Publish message to all subscribers.

        Args:
            message: Message to publish
        """
        handlers = self._handlers.get(message.type, [])
        for handler in handlers:
            try:
                handler(message)
            except Exception as e:
                if self._error_handler:
                    self._error_handler(e)

    async def publish_async(self, message: Message) -> None:
        """Publish message to all async subscribers.

        Args:
            message: Message to publish
        """
        # Call sync handlers first
        self.publish(message)

        # Then call async handlers
        async_handlers = self._async_handlers.get(message.type, [])
        for handler in async_handlers:
            try:
                await handler(message)
            except Exception as e:
                if self._error_handler:
                    self._error_handler(e)

    def set_error_handler(
        self,
        handler: Callable[[Exception], None],
    ) -> None:
        """Set error handler for handler exceptions.

        Args:
            handler: Error handler function
        """
        self._error_handler = handler
