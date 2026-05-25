"""Latent communication bus — shared infrastructure for agent-to-agent message passing."""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable

from lyra_recursive_link.exceptions import BusError, MessageDeliveryError
from lyra_recursive_link.latent_encoder import LatentVector


class MessagePriority(Enum):
    LOW = auto()
    NORMAL = auto()
    HIGH = auto()
    CRITICAL = auto()


@dataclass(frozen=True)
class BusMessage:
    sender_id: str
    latent: LatentVector
    timestamp: float
    priority: MessagePriority = MessagePriority.NORMAL
    ttl: float = 60.0
    message_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    topic: str = "default"


@dataclass(frozen=True)
class BusConfig:
    max_queue_size: int = 1000
    broadcast_enabled: bool = True
    persistence_enabled: bool = True
    default_ttl: float = 60.0


@dataclass(frozen=True)
class Subscription:
    agent_id: str
    filter_pattern: str = "default"
    active: bool = True


@dataclass(frozen=True)
class BusStats:
    messages_sent: int
    pending: int
    active_subscribers: int
    compression_saved_tokens: int


class CommunicationBus:
    """Shared latent-space communication bus for multi-agent message passing."""

    def __init__(self, config: BusConfig | None = None) -> None:
        self.config = config or BusConfig()
        self._messages: dict[str, BusMessage] = {}
        self._pending: dict[str, list[str]] = {}  # agent_id -> [message_id, ...]
        self._subscriptions: dict[str, Subscription] = {}
        self._acknowledged: set[str] = set()
        self._lock = asyncio.Lock()
        self._total_messages_sent: int = 0
        self._compression_saved: int = 0

    async def publish(
        self,
        sender_id: str,
        latent: LatentVector,
        priority: MessagePriority = MessagePriority.NORMAL,
        topic: str = "default",
    ) -> str:
        async with self._lock:
            if len(self._messages) >= self.config.max_queue_size:
                raise BusError(
                    f"Bus queue is full ({self.config.max_queue_size} messages)"
                )

            msg = BusMessage(
                sender_id=sender_id,
                latent=latent,
                timestamp=time.time(),
                priority=priority,
                ttl=self.config.default_ttl,
                topic=topic,
            )
            self._messages[msg.message_id] = msg
            self._total_messages_sent += 1

            saved = (
                latent.original_length - latent.compressed_length
            ) * 2
            self._compression_saved += max(0, saved)

            for agent_id, sub in list(self._subscriptions.items()):
                if not sub.active:
                    continue
                if sub.filter_pattern == topic or sub.filter_pattern == "default":
                    if agent_id not in self._pending:
                        self._pending[agent_id] = []
                    self._pending[agent_id].append(msg.message_id)

            return msg.message_id

    def subscribe(self, agent_id: str, filter_pattern: str = "default") -> Subscription:
        if not agent_id:
            raise BusError("agent_id cannot be empty")
        sub = Subscription(
            agent_id=agent_id, filter_pattern=filter_pattern, active=True
        )
        self._subscriptions[agent_id] = sub
        return sub

    async def broadcast(
        self,
        latent: LatentVector,
        exclude_senders: set[str] | None = None,
        priority: MessagePriority = MessagePriority.NORMAL,
    ) -> list[str]:
        if not self.config.broadcast_enabled:
            raise BusError("Broadcast is disabled in BusConfig")

        exclude = exclude_senders or set()
        recipient_ids: list[str] = []

        async with self._lock:
            for agent_id in list(self._subscriptions.keys()):
                if agent_id not in exclude:
                    msg = BusMessage(
                        sender_id="broadcast",
                        latent=latent,
                        timestamp=time.time(),
                        priority=priority,
                        ttl=self.config.default_ttl,
                        topic="broadcast",
                    )
                    self._messages[msg.message_id] = msg
                    self._total_messages_sent += 1
                    if agent_id not in self._pending:
                        self._pending[agent_id] = []
                    self._pending[agent_id].append(msg.message_id)
                    recipient_ids.append(agent_id)

            saved = (latent.original_length - latent.compressed_length) * 2
            self._compression_saved += max(0, saved) * max(1, len(recipient_ids))

        return recipient_ids

    async def get_pending(self, agent_id: str) -> list[BusMessage]:
        async with self._lock:
            pending_ids = list(self._pending.get(agent_id, []))
            now = time.time()
            messages: list[BusMessage] = []
            for mid in pending_ids:
                msg = self._messages.get(mid)
                if msg is None:
                    continue
                if msg.ttl > 0 and (now - msg.timestamp) > msg.ttl:
                    self._messages.pop(mid, None)
                    continue
                messages.append(msg)
            return messages

    async def acknowledge(self, message_id: str, agent_id: str) -> None:
        async with self._lock:
            if message_id not in self._messages:
                raise MessageDeliveryError(
                    f"Message {message_id} not found"
                )
            self._acknowledged.add(message_id)

            pending_list = self._pending.get(agent_id, [])
            if message_id in pending_list:
                pending_list.remove(message_id)

            if self.config.persistence_enabled:
                pass
            else:
                self._messages.pop(message_id, None)

    def unsubscribe(self, agent_id: str) -> None:
        self._subscriptions.pop(agent_id, None)
        self._pending.pop(agent_id, None)

    def get_stats(self) -> BusStats:
        now = time.time()
        active_pending = 0
        for pending_ids in self._pending.values():
            for mid in pending_ids:
                msg = self._messages.get(mid)
                if msg is not None:
                    if msg.ttl <= 0 or (now - msg.timestamp) <= msg.ttl:
                        active_pending += 1

        active_subs = sum(
            1 for s in self._subscriptions.values() if s.active
        )

        return BusStats(
            messages_sent=self._total_messages_sent,
            pending=active_pending,
            active_subscribers=active_subs,
            compression_saved_tokens=self._compression_saved,
        )

    async def cleanup_expired(self) -> int:
        """Remove expired messages. Returns number of messages removed."""
        async with self._lock:
            now = time.time()
            expired_ids: list[str] = []
            for mid, msg in list(self._messages.items()):
                if msg.ttl > 0 and (now - msg.timestamp) > msg.ttl:
                    expired_ids.append(mid)

            for mid in expired_ids:
                self._messages.pop(mid, None)
                for pending_list in self._pending.values():
                    if mid in pending_list:
                        pending_list.remove(mid)

            return len(expired_ids)
