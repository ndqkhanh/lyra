"""Direct inter-agent messaging with threading, prioritisation, and inbox management."""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto

from lyra_agent_swarm.exceptions import MessagingError


class MessagePriority(Enum):
    """Urgency level of an inter-agent message."""

    LOW = auto()
    NORMAL = auto()
    HIGH = auto()
    URGENT = auto()


@dataclass(frozen=True)
class AgentMessage:
    """An immutable message sent between agents."""

    message_id: str
    sender: str
    recipient: str
    subject: str
    body: str
    priority: MessagePriority = MessagePriority.NORMAL
    reply_to: str | None = None
    timestamp: float = field(default_factory=time.time)
    is_read: bool = False


@dataclass(frozen=True)
class MessageThread:
    """A linked chain of messages sharing the same root."""

    root_id: str
    messages: tuple[str, ...] = ()
    subject: str = ""


@dataclass(frozen=True)
class MessagingConfig:
    """Configuration governing messaging limits."""

    max_inbox_size: int = 1000
    message_ttl: float = 86400.0  # 24 hours


class TeamMessaging:
    """Manages inter-agent message sending, inbox storage, and threading."""

    def __init__(self, config: MessagingConfig | None = None) -> None:
        self._config = config or MessagingConfig()
        self._messages: dict[str, AgentMessage] = {}
        self._inboxes: dict[str, list[str]] = defaultdict(list)
        self._threads: dict[str, MessageThread] = {}
        self._counter: int = 0

    @property
    def config(self) -> MessagingConfig:
        return self._config

    def send(
        self,
        sender: str,
        recipient: str,
        subject: str,
        body: str,
        priority: MessagePriority = MessagePriority.NORMAL,
        reply_to: str | None = None,
    ) -> str:
        self._counter += 1
        message_id = f"msg-{self._counter}"

        if reply_to is not None and reply_to not in self._messages:
            raise MessagingError(f"Reply target message '{reply_to}' not found")

        message = AgentMessage(
            message_id=message_id,
            sender=sender,
            recipient=recipient,
            subject=subject,
            body=body,
            priority=priority,
            reply_to=reply_to,
        )
        self._messages[message_id] = message
        self._inboxes[recipient].append(message_id)

        # Manage thread tracking
        root_id = reply_to
        if root_id is not None:
            # Walk up to find the root
            current = self._messages.get(root_id)
            while current is not None and current.reply_to is not None:
                current = self._messages.get(current.reply_to)
            if current is not None:
                root_id = current.message_id

        if root_id is not None and root_id in self._threads:
            old_thread = self._threads[root_id]
            self._threads[root_id] = MessageThread(
                root_id=root_id,
                messages=old_thread.messages + (message_id,),
                subject=old_thread.subject,
            )
        elif root_id is not None:
            self._threads[root_id] = MessageThread(
                root_id=root_id,
                messages=(message_id,),
                subject=subject,
            )

        return message_id

    def broadcast(
        self,
        sender: str,
        recipients: list[str],
        subject: str,
        body: str,
    ) -> list[str]:
        if not recipients:
            raise MessagingError("No recipients specified for broadcast")
        ids: list[str] = []
        for recipient in recipients:
            mid = self.send(sender, recipient, subject, body)
            ids.append(mid)
        return ids

    def get_inbox(self, agent_id: str) -> list[AgentMessage]:
        msg_ids = self._inboxes.get(agent_id, [])
        result: list[AgentMessage] = []
        now = time.time()
        for mid in msg_ids:
            msg = self._messages.get(mid)
            if msg is None:
                continue
            if now - msg.timestamp > self._config.message_ttl:
                continue
            result.append(msg)
        # Sort by priority (URGENT first), then by timestamp
        priority_order = {
            MessagePriority.URGENT: 0,
            MessagePriority.HIGH: 1,
            MessagePriority.NORMAL: 2,
            MessagePriority.LOW: 3,
        }
        result.sort(key=lambda m: (priority_order.get(m.priority, 99), -m.timestamp))
        return result[: self._config.max_inbox_size]

    def mark_read(self, message_id: str) -> None:
        msg = self._messages.get(message_id)
        if msg is None:
            raise MessagingError(f"Message '{message_id}' not found")
        self._messages[message_id] = AgentMessage(
            message_id=msg.message_id,
            sender=msg.sender,
            recipient=msg.recipient,
            subject=msg.subject,
            body=msg.body,
            priority=msg.priority,
            reply_to=msg.reply_to,
            timestamp=msg.timestamp,
            is_read=True,
        )

    def get_thread(self, root_id: str) -> MessageThread | None:
        return self._threads.get(root_id)

    def get_message(self, message_id: str) -> AgentMessage | None:
        return self._messages.get(message_id)
