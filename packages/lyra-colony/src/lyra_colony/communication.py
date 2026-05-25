"""Inter-agent communication subsystem for the colony runtime.

Provides message passing, pub/sub channels, broadcast/multicast,
message persistence, and multiple communication protocols.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class CommunicationError(Exception):
    """Base exception for communication errors."""


class ChannelNotFoundError(CommunicationError):
    """Raised when a pub/sub channel does not exist."""


class MessageDeliveryError(CommunicationError):
    """Raised when a message could not be delivered."""


class SubscriptionError(CommunicationError):
    """Raised when a subscription operation fails."""


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Protocol(Enum):
    """Communication protocol for a message."""

    REQUEST_REPLY = auto()
    FIRE_FORGET = auto()
    STREAMING = auto()


class MessagePriority(Enum):
    """Priority level for messages."""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _new_id() -> str:
    return uuid4().hex[:12]


def _now() -> float:
    return time.monotonic()


# ---------------------------------------------------------------------------
# Dataclass models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Message:
    """An immutable message passed between agents.

    Attributes:
        message_id: Unique message identifier.
        sender_id: Agent that sent the message.
        recipient_id: Target agent (None for broadcasts).
        topic: Pub/sub topic the message belongs to.
        protocol: Communication protocol.
        priority: Message priority.
        payload: Message body.
        correlation_id: For request-reply correlation.
        sent_at: Monotonic timestamp when sent.
        ttl_seconds: Time-to-live in seconds.
    """

    message_id: str = field(default_factory=_new_id)
    sender_id: str = ""
    recipient_id: str | None = None
    topic: str = "general"
    protocol: Protocol = Protocol.FIRE_FORGET
    priority: MessagePriority = MessagePriority.NORMAL
    payload: dict[str, Any] = field(default_factory=dict)
    correlation_id: str | None = None
    sent_at: float = field(default_factory=_now)
    ttl_seconds: float = 60.0

    def is_expired(self, now: float | None = None) -> bool:
        now = now or _now()
        return (now - self.sent_at) > self.ttl_seconds


@dataclass(frozen=True)
class MessageDeliveryReceipt:
    """Receipt for message delivery.

    Attributes:
        message_id: The delivered message.
        recipient_id: Who received it.
        delivered_at: When delivery happened.
        acknowledged: Whether the recipient acknowledged.
    """

    message_id: str
    recipient_id: str
    delivered_at: float = field(default_factory=_now)
    acknowledged: bool = False


# ---------------------------------------------------------------------------
# Channel
# ---------------------------------------------------------------------------


class Channel:
    """A pub/sub channel for topic-based messaging.

    Agents subscribe to channels and receive messages published to
    the channel's topic.
    """

    def __init__(self, topic: str, *, max_buffer: int = 1000) -> None:
        self.topic = topic
        self._max_buffer = max_buffer
        self._subscribers: set[str] = set()
        self._message_log: list[Message] = []
        self._delivery_receipts: list[MessageDeliveryReceipt] = []

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)

    def subscribe(self, agent_id: str) -> bool:
        if agent_id in self._subscribers:
            return False
        self._subscribers.add(agent_id)
        logger.debug("Agent %s subscribed to channel %s", agent_id, self.topic)
        return True

    def unsubscribe(self, agent_id: str) -> bool:
        if agent_id not in self._subscribers:
            return False
        self._subscribers.discard(agent_id)
        logger.debug("Agent %s unsubscribed from channel %s", agent_id, self.topic)
        return True

    def is_subscribed(self, agent_id: str) -> bool:
        return agent_id in self._subscribers

    def publish(self, message: Message) -> list[MessageDeliveryReceipt]:
        """Publish a message to all subscribers. Returns delivery receipts."""
        receipts: list[MessageDeliveryReceipt] = []
        for sub in self._subscribers:
            if sub == message.sender_id:
                continue  # don't deliver to self
            receipt = MessageDeliveryReceipt(
                message_id=message.message_id,
                recipient_id=sub,
                acknowledged=False,
            )
            receipts.append(receipt)

        self._message_log.append(message)
        if len(self._message_log) > self._max_buffer:
            self._message_log = self._message_log[-self._max_buffer:]

        self._delivery_receipts.extend(receipts)
        return receipts

    def get_history(self, limit: int = 100) -> list[Message]:
        """Return recent messages on this channel."""
        return self._message_log[-limit:]

    def snapshot(self) -> dict[str, Any]:
        return {
            "topic": self.topic,
            "subscriber_count": len(self._subscribers),
            "message_count": len(self._message_log),
        }


# ---------------------------------------------------------------------------
# MessageBus
# ---------------------------------------------------------------------------


class MessageBus:
    """Central message bus for inter-agent communication.

    Supports:
    - Point-to-point message passing
    - Topic-based pub/sub channels
    - Broadcast and multicast
    - Message persistence and replay
    - Request-reply, fire-forget, and streaming protocols
    """

    def __init__(self, *, max_history: int = 10_000) -> None:
        self._max_history = max_history
        self._channels: dict[str, Channel] = {}
        self._message_log: list[Message] = []
        self._receipts: list[MessageDeliveryReceipt] = []
        self._pending_requests: dict[str, asyncio.Future[Message]] = {}
        self._agent_queues: dict[str, asyncio.Queue[Message]] = defaultdict(
            lambda: asyncio.Queue(maxsize=500)
        )

    # ------------------------------------------------------------------
    # Channel management
    # ------------------------------------------------------------------

    def create_channel(self, topic: str) -> Channel:
        """Create a new pub/sub channel."""
        if topic in self._channels:
            raise SubscriptionError(f"Channel '{topic}' already exists")
        channel = Channel(topic)
        self._channels[topic] = channel
        logger.info("Created channel: %s", topic)
        return channel

    def get_channel(self, topic: str) -> Channel:
        """Get or create a channel by topic."""
        if topic not in self._channels:
            return self.create_channel(topic)
        return self._channels[topic]

    def remove_channel(self, topic: str) -> bool:
        """Remove a channel."""
        if topic not in self._channels:
            return False
        del self._channels[topic]
        logger.info("Removed channel: %s", topic)
        return True

    def list_channels(self) -> list[str]:
        return list(self._channels.keys())

    # ------------------------------------------------------------------
    # Subscription management
    # ------------------------------------------------------------------

    def subscribe(self, agent_id: str, topic: str) -> bool:
        channel = self.get_channel(topic)
        return channel.subscribe(agent_id)

    def unsubscribe(self, agent_id: str, topic: str) -> bool:
        channel = self._channels.get(topic)
        if channel is None:
            return False
        return channel.unsubscribe(agent_id)

    def unsubscribe_all(self, agent_id: str) -> None:
        for channel in self._channels.values():
            channel.unsubscribe(agent_id)

    # ------------------------------------------------------------------
    # Message sending
    # ------------------------------------------------------------------

    async def send(
        self,
        message: Message,
        *,
        ack_timeout: float = 10.0,
    ) -> MessageDeliveryReceipt:
        """Send a message to a specific recipient. Returns a delivery receipt."""
        if message.protocol == Protocol.REQUEST_REPLY and message.recipient_id:
            return await self._request_reply(message, ack_timeout)
        elif message.protocol == Protocol.STREAMING and message.recipient_id:
            return await self._stream(message)
        else:
            return self._fire_forget(message)

    async def publish(self, topic: str, message: Message) -> list[MessageDeliveryReceipt]:
        """Publish a message to a topic channel."""
        channel = self.get_channel(topic)
        receipts = channel.publish(message)
        self._receipts.extend(receipts)

        # Also enqueue to individual agent queues
        for receipt in receipts:
            q = self._agent_queues[receipt.recipient_id]
            try:
                q.put_nowait(message)
            except asyncio.QueueFull:
                logger.warning("Agent %s queue full, dropping message %s", receipt.recipient_id, message.message_id)

        self._log_message(message)
        return receipts

    async def broadcast(
        self,
        message: Message,
        agent_ids: Sequence[str],
    ) -> list[MessageDeliveryReceipt]:
        """Send a message to a list of agents."""
        receipts: list[MessageDeliveryReceipt] = []
        for aid in agent_ids:
            receipt = MessageDeliveryReceipt(
                message_id=message.message_id,
                recipient_id=aid,
            )
            self._agent_queues[aid].put_nowait(message)
            receipts.append(receipt)
        self._receipts.extend(receipts)
        self._log_message(message)
        return receipts

    async def multicast(
        self,
        message: Message,
        agent_ids: Sequence[str],
    ) -> list[MessageDeliveryReceipt]:
        """Send a message to a group of agents (identical to broadcast in this impl)."""
        return await self.broadcast(message, agent_ids)

    # ------------------------------------------------------------------
    # Protocol implementations
    # ------------------------------------------------------------------

    def _fire_forget(self, message: Message) -> MessageDeliveryReceipt:
        receipt = MessageDeliveryReceipt(
            message_id=message.message_id,
            recipient_id=message.recipient_id or "unknown",
            acknowledged=False,
        )
        if message.recipient_id:
            try:
                self._agent_queues[message.recipient_id].put_nowait(message)
            except asyncio.QueueFull:
                logger.warning("Queue full for agent %s", message.recipient_id)
        self._log_message(message)
        self._receipts.append(receipt)
        return receipt

    async def _request_reply(
        self,
        message: Message,
        ack_timeout: float = 10.0,
    ) -> MessageDeliveryReceipt:
        future: asyncio.Future[Message] = asyncio.Future()
        self._pending_requests[message.message_id] = future

        if message.recipient_id:
            try:
                self._agent_queues[message.recipient_id].put_nowait(message)
            except asyncio.QueueFull:
                raise MessageDeliveryError(f"Queue full for {message.recipient_id}")

        self._log_message(message)

        try:
            await asyncio.wait_for(future, timeout=ack_timeout)
            receipt = MessageDeliveryReceipt(
                message_id=message.message_id,
                recipient_id=message.recipient_id or "unknown",
                acknowledged=True,
            )
        except asyncio.TimeoutError:
            receipt = MessageDeliveryReceipt(
                message_id=message.message_id,
                recipient_id=message.recipient_id or "unknown",
                acknowledged=False,
            )
        finally:
            self._pending_requests.pop(message.message_id, None)

        self._receipts.append(receipt)
        return receipt

    async def _stream(self, message: Message) -> MessageDeliveryReceipt:
        if message.recipient_id:
            try:
                self._agent_queues[message.recipient_id].put_nowait(message)
            except asyncio.QueueFull:
                logger.warning("Queue full for streaming to %s", message.recipient_id)

        receipt = MessageDeliveryReceipt(
            message_id=message.message_id,
            recipient_id=message.recipient_id or "unknown",
            acknowledged=True,
        )
        self._log_message(message)
        self._receipts.append(receipt)
        return receipt

    # ------------------------------------------------------------------
    # Reply support
    # ------------------------------------------------------------------

    def reply(self, original: Message, payload: dict[str, Any]) -> Message:
        """Create a reply message correlated to the original."""
        return Message(
            sender_id=original.recipient_id or "",
            recipient_id=original.sender_id,
            topic=original.topic,
            protocol=Protocol.REQUEST_REPLY,
            priority=original.priority,
            payload=payload,
            correlation_id=original.message_id,
        )

    def acknowledge(self, request_message_id: str) -> bool:
        """Acknowledge a pending request."""
        future = self._pending_requests.pop(request_message_id, None)
        if future and not future.done():
            future.set_result(
                Message(
                    message_id="ack-" + request_message_id,
                    payload={"status": "acknowledged"},
                )
            )
            return True
        return False

    # ------------------------------------------------------------------
    # Agent message retrieval
    # ------------------------------------------------------------------

    async def receive(self, agent_id: str, timeout: float | None = None) -> Message:
        """Receive the next message for an agent (blocking)."""
        q = self._agent_queues[agent_id]
        if timeout is not None:
            return await asyncio.wait_for(q.get(), timeout=timeout)
        return await q.get()

    async def receive_batch(
        self,
        agent_id: str,
        max_messages: int = 50,
        timeout: float = 0.1,
    ) -> list[Message]:
        """Receive a batch of messages for an agent."""
        q = self._agent_queues[agent_id]
        messages: list[Message] = []
        try:
            while len(messages) < max_messages:
                msg = await asyncio.wait_for(q.get(), timeout=timeout)
                messages.append(msg)
        except asyncio.TimeoutError:
            pass
        return messages

    # ------------------------------------------------------------------
    # Persistence and replay
    # ------------------------------------------------------------------

    def _log_message(self, message: Message) -> None:
        self._message_log.append(message)
        if len(self._message_log) > self._max_history:
            self._message_log = self._message_log[-self._max_history:]

    def get_message_history(self, limit: int = 100) -> list[Message]:
        """Return the most recent messages across all channels."""
        return self._message_log[-limit:]

    def replay_for_agent(
        self,
        agent_id: str,
        since_timestamp: float | None = None,
        limit: int = 100,
    ) -> list[Message]:
        """Replay messages relevant to an agent, optionally since a timestamp."""
        relevant: list[Message] = []
        for msg in reversed(self._message_log):
            if len(relevant) >= limit:
                break
            if since_timestamp is not None and msg.sent_at <= since_timestamp:
                continue
            # Include if this agent is the recipient, sender, or subscribed to topic
            if msg.recipient_id == agent_id or msg.sender_id == agent_id:
                relevant.append(msg)
                continue
            channel = self._channels.get(msg.topic)
            if channel and channel.is_subscribed(agent_id):
                relevant.append(msg)
        return list(reversed(relevant))

    # ------------------------------------------------------------------
    # Queries and snapshot
    # ------------------------------------------------------------------

    def get_delivery_stats(self) -> dict[str, Any]:
        """Return aggregate delivery statistics."""
        total = len(self._receipts)
        acked = sum(1 for r in self._receipts if r.acknowledged)
        return {
            "total_sent": total,
            "acknowledged": acked,
            "ack_rate": acked / total if total > 0 else 0.0,
            "total_messages_logged": len(self._message_log),
            "active_channels": len(self._channels),
            "pending_requests": len(self._pending_requests),
        }

    def snapshot(self) -> dict[str, Any]:
        """Return a current-state snapshot."""
        return {
            "channels": [ch.snapshot() for ch in self._channels.values()],
            "total_messages": len(self._message_log),
            "pending_requests": len(self._pending_requests),
            "agent_queues": {aid: q.qsize() for aid, q in self._agent_queues.items()},
        }
