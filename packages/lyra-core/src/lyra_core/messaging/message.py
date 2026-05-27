"""Message protocol and base classes."""
from dataclasses import dataclass
from typing import Protocol

from lyra_core.messaging.types import MessageType


@dataclass(frozen=True)
class Message:
    """Base message class.

    All messages must have a type. Subclasses can add additional fields.
    """

    type: MessageType


class MessageHandler(Protocol):
    """Protocol for message handlers.

    Handlers must implement the handle method.
    """

    def handle(self, message: Message) -> None:
        """Handle a message.

        Args:
            message: Message to handle
        """
        ...
