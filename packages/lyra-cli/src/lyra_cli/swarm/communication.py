"""
Agent Communication for message passing and shared state.

Implements:
- Pub/sub message broadcasting
- Point-to-point direct messaging
- Shared state with versioning and CAS
- Topic-based subscription management
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any
from uuid import uuid4


class MessageType(Enum):
    """Types of messages exchanged between agents."""

    REQUEST = auto()
    RESPONSE = auto()
    BROADCAST = auto()
    ERROR = auto()
    HEARTBEAT = auto()
    STATE_UPDATE = auto()
    CONSENSUS_VOTE = auto()
    LEADER_ELECTION = auto()


@dataclass
class Message:
    """A message exchanged between agents."""

    message_id: str = field(default_factory=lambda: f"msg_{uuid4().hex[:8]}")
    msg_type: MessageType = MessageType.REQUEST
    sender_id: str = ""
    recipient_id: str | None = None
    topic: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    correlation_id: str | None = None


@dataclass
class SharedStateEntry:
    """A versioned entry in the shared state."""

    key: str = ""
    value: Any = None
    version: int = 0
    updated_by: str = ""
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class CommunicationConfig:
    """Configuration for agent communication."""

    max_queue_size: int = 1000
    message_timeout: float = 30.0
    state_sync_interval: float = 5.0
    max_subscribers_per_topic: int = 100


class AgentCommunication:
    """
    Handles message passing and shared state between agents.

    Features:
    - Publish/subscribe messaging by topic
    - Point-to-point direct messaging
    - Shared key-value state with optimistic locking via versioning
    - Subscription management and filtering
    """

    def __init__(self, config: CommunicationConfig | None = None) -> None:
        self.config = config or CommunicationConfig()
        self._mailboxes: dict[str, asyncio.Queue] = {}
        self._subscriptions: dict[str, set[str]] = {}
        self._shared_state: dict[str, SharedStateEntry] = {}
        self._subscriber_callbacks: dict[str, list[Callable[[Message], Any]]] = {}
        self._lock: asyncio.Lock = asyncio.Lock()
        self._stats: dict[str, int] = {
            "messages_sent": 0,
            "messages_received": 0,
            "broadcasts_sent": 0,
            "state_updates": 0,
        }

    async def register_agent(self, agent_id: str) -> None:
        """
        Register an agent for message delivery.

        Args:
            agent_id: The agent to register
        """
        async with self._lock:
            if agent_id not in self._mailboxes:
                self._mailboxes[agent_id] = asyncio.Queue(
                    maxsize=self.config.max_queue_size
                )

    async def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent from the communication system."""
        async with self._lock:
            self._mailboxes.pop(agent_id, None)
            self._subscriptions.pop(agent_id, None)
            self._subscriber_callbacks.pop(agent_id, None)

    async def send_message(self, message: Message) -> bool:
        """
        Send a point-to-point message to a specific agent.

        Args:
            message: The message to send

        Returns:
            True if delivered, False if recipient not found
        """
        if message.recipient_id is None:
            return False

        async with self._lock:
            mailbox = self._mailboxes.get(message.recipient_id)
            if mailbox is None:
                return False
            try:
                mailbox.put_nowait(message)
                self._stats["messages_sent"] += 1
                return True
            except asyncio.QueueFull:
                return False

    async def send_request(
        self,
        recipient_id: str,
        sender_id: str,
        payload: dict[str, Any],
        timeout: float | None = None,
    ) -> Message | None:
        """
        Send a request and wait for a response.

        Args:
            recipient_id: Target agent
            sender_id: Sending agent
            payload: Request payload
            timeout: How long to wait for a response

        Returns:
            Response message, or None on timeout
        """
        correlation_id = uuid4().hex
        request = Message(
            msg_type=MessageType.REQUEST,
            sender_id=sender_id,
            recipient_id=recipient_id,
            payload=payload,
            correlation_id=correlation_id,
        )

        await self.register_agent(sender_id)
        sent = await self.send_message(request)
        if not sent:
            return None

        deadline = datetime.now().timestamp() + (timeout or self.config.message_timeout)
        while datetime.now().timestamp() < deadline:
            async with self._lock:
                mailbox = self._mailboxes.get(sender_id)
                if mailbox is not None and not mailbox.empty():
                    try:
                        response = mailbox.get_nowait()
                        if (isinstance(response, Message)
                                and response.correlation_id == correlation_id):
                            self._stats["messages_received"] += 1
                            return response
                    except asyncio.QueueEmpty:
                        pass
            await asyncio.sleep(0.05)

        return None

    async def send_response(
        self,
        request: Message,
        sender_id: str,
        payload: dict[str, Any],
    ) -> bool:
        """
        Send a response to a previous request.

        Args:
            request: The original request message
            sender_id: The agent sending the response
            payload: Response payload

        Returns:
            True if delivered
        """
        response = Message(
            msg_type=MessageType.RESPONSE,
            sender_id=sender_id,
            recipient_id=request.sender_id,
            payload=payload,
            correlation_id=request.correlation_id,
        )
        return await self.send_message(response)

    async def publish(self, topic: str, message: Message) -> int:
        """
        Publish a message to all subscribers of a topic.

        Args:
            topic: The topic to publish to
            message: The message to broadcast

        Returns:
            Number of subscribers the message was delivered to
        """
        message.topic = topic
        message.msg_type = MessageType.BROADCAST

        async with self._lock:
            subscribers = self._subscriptions.get(topic, set()).copy()
            self._stats["broadcasts_sent"] += 1

        delivered = 0
        for sub_id in subscribers:
            async with self._lock:
                mailbox = self._mailboxes.get(sub_id)
                if mailbox is not None:
                    try:
                        mailbox.put_nowait(message)
                        delivered += 1
                        self._stats["messages_sent"] += 1
                    except asyncio.QueueFull:
                        pass
                    callbacks = self._subscriber_callbacks.get(sub_id, [])
                    for cb in callbacks:
                        try:
                            cb(message)
                        except Exception:
                            pass
        return delivered

    async def subscribe(self, agent_id: str, topic: str) -> None:
        """
        Subscribe an agent to a topic.

        Args:
            agent_id: The subscribing agent
            topic: The topic to subscribe to
        """
        async with self._lock:
            if topic not in self._subscriptions:
                self._subscriptions[topic] = set()
            if len(self._subscriptions[topic]) < self.config.max_subscribers_per_topic:
                self._subscriptions[topic].add(agent_id)

    async def unsubscribe(self, agent_id: str, topic: str) -> None:
        """Unsubscribe an agent from a topic."""
        async with self._lock:
            subs = self._subscriptions.get(topic)
            if subs:
                subs.discard(agent_id)

    async def register_callback(
        self,
        agent_id: str,
        callback: Callable[[Message], Any],
    ) -> None:
        """Register a callback for incoming messages."""
        async with self._lock:
            if agent_id not in self._subscriber_callbacks:
                self._subscriber_callbacks[agent_id] = []
            self._subscriber_callbacks[agent_id].append(callback)

    async def read_messages(self, agent_id: str) -> list[Message]:
        """
        Read all pending messages for an agent.

        Args:
            agent_id: The agent to read messages for

        Returns:
            List of pending messages
        """
        messages: list[Message] = []
        async with self._lock:
            mailbox = self._mailboxes.get(agent_id)
            if mailbox is None:
                return messages
            while not mailbox.empty():
                try:
                    msg = mailbox.get_nowait()
                    messages.append(msg)
                    self._stats["messages_received"] += 1
                except asyncio.QueueEmpty:
                    break
        return messages

    async def set_state(
        self,
        key: str,
        value: Any,
        agent_id: str,
        expected_version: int | None = None,
    ) -> bool:
        """
        Set a shared state value with optimistic locking.

        Args:
            key: State key
            value: New value
            agent_id: The agent updating the state
            expected_version: Expected current version (CAS)

        Returns:
            True if updated, False if version conflict
        """
        async with self._lock:
            current = self._shared_state.get(key)
            if expected_version is not None and current is not None:
                if current.version != expected_version:
                    return False

            new_version = (current.version + 1) if current else 1
            self._shared_state[key] = SharedStateEntry(
                key=key,
                value=value,
                version=new_version,
                updated_by=agent_id,
            )
            self._stats["state_updates"] += 1
        return True

    async def get_state(self, key: str) -> SharedStateEntry | None:
        """Get a shared state entry by key."""
        async with self._lock:
            return self._shared_state.get(key)

    async def get_all_state(self) -> dict[str, SharedStateEntry]:
        """Get all shared state entries."""
        async with self._lock:
            return dict(self._shared_state)

    def get_stats(self) -> dict[str, int]:
        """Get communication statistics."""
        return dict(self._stats)

    @property
    def registered_agent_count(self) -> int:
        """Get the number of registered agents."""
        return len(self._mailboxes)
