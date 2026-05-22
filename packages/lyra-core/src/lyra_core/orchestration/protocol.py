"""Message protocol for agent-to-agent communication.

Defines the message structure, types, and serialization methods for
asynchronous communication between agents in the orchestration system.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class MessageType(Enum):
    """Type of message being sent between agents."""

    REQUEST = "request"  # Synchronous request-response
    RESPONSE = "response"  # Response to a request
    EVENT = "event"  # Asynchronous event notification
    TASK = "task"  # Task assignment
    CONSENSUS = "consensus"  # Consensus voting message


@dataclass(frozen=True)
class Message:
    """Immutable message for agent-to-agent communication.

    Attributes:
        id: Unique message identifier
        type: Type of message (request, response, event, task, consensus)
        sender: Agent ID of the sender
        receiver: Agent ID of the receiver (or "broadcast" for all)
        payload: Message payload containing action and data
        timestamp: ISO 8601 timestamp when message was created
        trace_id: Distributed tracing ID for observability
        reply_to: Optional message ID this is replying to
    """

    id: str
    type: MessageType
    sender: str
    receiver: str
    payload: dict[str, Any]
    timestamp: str
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    reply_to: str | None = None

    @staticmethod
    def create(
        type: MessageType,
        sender: str,
        receiver: str,
        payload: dict[str, Any],
        trace_id: str | None = None,
        reply_to: str | None = None,
    ) -> Message:
        """Create a new message with auto-generated ID and timestamp.

        Args:
            type: Type of message
            sender: Agent ID of sender
            receiver: Agent ID of receiver
            payload: Message payload
            trace_id: Optional trace ID (auto-generated if not provided)
            reply_to: Optional message ID this is replying to

        Returns:
            New Message instance
        """
        return Message(
            id=str(uuid.uuid4()),
            type=type,
            sender=sender,
            receiver=receiver,
            payload=payload,
            timestamp=datetime.now(timezone.utc).isoformat(),
            trace_id=trace_id or str(uuid.uuid4()),
            reply_to=reply_to,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize message to dictionary.

        Returns:
            Dictionary representation of the message
        """
        return {
            "id": self.id,
            "type": self.type.value,
            "sender": self.sender,
            "receiver": self.receiver,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "trace_id": self.trace_id,
            "reply_to": self.reply_to,
        }

    def to_json(self) -> str:
        """Serialize message to JSON string.

        Returns:
            JSON string representation of the message
        """
        return json.dumps(self.to_dict())

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Message:
        """Deserialize message from dictionary.

        Args:
            data: Dictionary containing message data

        Returns:
            Message instance

        Raises:
            ValueError: If required fields are missing or invalid
        """
        try:
            return Message(
                id=data["id"],
                type=MessageType(data["type"]),
                sender=data["sender"],
                receiver=data["receiver"],
                payload=data["payload"],
                timestamp=data["timestamp"],
                trace_id=data.get("trace_id", str(uuid.uuid4())),
                reply_to=data.get("reply_to"),
            )
        except (KeyError, ValueError) as e:
            raise ValueError(f"Invalid message data: {e}") from e

    @staticmethod
    def from_json(json_str: str) -> Message:
        """Deserialize message from JSON string.

        Args:
            json_str: JSON string containing message data

        Returns:
            Message instance

        Raises:
            ValueError: If JSON is invalid or required fields are missing
        """
        try:
            data = json.loads(json_str)
            return Message.from_dict(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}") from e


__all__ = ["Message", "MessageType"]
