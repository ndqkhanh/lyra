"""Per-agent Mailbox + MailboxRouter — peer-to-peer messaging.

Mailboxes are FIFO inboxes; the router fans broadcast messages out to all
known mailboxes. Sending across mailboxes uses the recipient agent_id;
broadcast uses the wildcard ``"*"``.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class Message:
    """One agent-to-agent message.

    ``recipient="*"`` is broadcast to all mailboxes registered with the router.
    """

    msg_id: str
    sender: str
    recipient: str
    body: str
    sent_at: float = field(default_factory=time.time)
    payload: dict[str, Any] = field(default_factory=dict)
    in_reply_to: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.msg_id:
            raise ValueError("msg_id must be non-empty")
        if not self.sender:
            raise ValueError("sender must be non-empty")
        if not self.recipient:
            raise ValueError("recipient must be non-empty")

    @property
    def is_broadcast(self) -> bool:
        return self.recipient == "*"


@dataclass
class Mailbox:
    """Per-agent FIFO inbox.

    >>> mb = Mailbox(agent_id="spoke-1")
    >>> mb.deliver(Message(msg_id="m1", sender="lead", recipient="spoke-1",
    ...                     body="task assigned"))
    >>> msg = mb.receive()
    >>> msg.body
    'task assigned'
    """

    agent_id: str
    _inbox: list[Message] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.agent_id:
            raise ValueError("agent_id must be non-empty")

    def deliver(self, message: Message) -> None:
        """Append a message to the inbox.

        Broadcast (recipient='*') is allowed; for direct delivery, the
        recipient must match this mailbox's agent_id.
        """
        if not message.is_broadcast and message.recipient != self.agent_id:
            raise ValueError(
                f"recipient mismatch: message addressed to "
                f"{message.recipient!r}, mailbox is {self.agent_id!r}"
            )
        self._inbox.append(message)

    def receive(self) -> Optional[Message]:
        """Pop the oldest message; FIFO. Returns None if inbox empty."""
        if not self._inbox:
            return None
        return self._inbox.pop(0)

    def peek(self) -> Optional[Message]:
        """Look at the oldest message without removing it."""
        return self._inbox[0] if self._inbox else None

    def __len__(self) -> int:
        return len(self._inbox)

    def drain(self) -> list[Message]:
        """Return all messages, clearing the inbox."""
        out, self._inbox = self._inbox, []
        return out


@dataclass
class MailboxRouter:
    """Route messages to mailboxes; fan broadcasts out.

    Each mailbox registers; sends are dispatched by recipient.
    """

    _mailboxes: dict[str, Mailbox] = field(default_factory=dict)
    _undelivered: list[Message] = field(default_factory=list)

    def register(self, mailbox: Mailbox) -> None:
        if mailbox.agent_id in self._mailboxes:
            raise ValueError(
                f"mailbox for agent {mailbox.agent_id!r} already registered"
            )
        self._mailboxes[mailbox.agent_id] = mailbox

    def unregister(self, agent_id: str) -> bool:
        if agent_id in self._mailboxes:
            del self._mailboxes[agent_id]
            return True
        return False

    def get(self, agent_id: str) -> Optional[Mailbox]:
        return self._mailboxes.get(agent_id)

    def send(
        self,
        *,
        sender: str,
        recipient: str,
        body: str,
        payload: Optional[dict[str, Any]] = None,
        in_reply_to: Optional[str] = None,
    ) -> Message:
        """Send a message. Returns the constructed :class:`Message`."""
        msg = Message(
            msg_id=str(uuid.uuid4()),
            sender=sender,
            recipient=recipient,
            body=body,
            payload=payload or {},
            in_reply_to=in_reply_to,
        )
        self._dispatch(msg)
        return msg

    def _dispatch(self, message: Message) -> None:
        if message.is_broadcast:
            for mb in self._mailboxes.values():
                # Don't echo broadcasts back to the sender.
                if mb.agent_id == message.sender:
                    continue
                # Construct a per-recipient message so deliver() validates.
                per_recipient = Message(
                    msg_id=message.msg_id,
                    sender=message.sender,
                    recipient=mb.agent_id,
                    body=message.body,
                    payload=message.payload,
                    sent_at=message.sent_at,
                    in_reply_to=message.in_reply_to,
                )
                mb.deliver(per_recipient)
            return
        target = self._mailboxes.get(message.recipient)
        if target is None:
            self._undelivered.append(message)
            return
        target.deliver(message)

    @property
    def undelivered(self) -> list[Message]:
        """Messages whose recipient mailbox isn't registered."""
        return list(self._undelivered)

    def stats(self) -> dict[str, int]:
        return {
            "mailboxes": len(self._mailboxes),
            "undelivered": len(self._undelivered),
            "queued_total": sum(len(mb) for mb in self._mailboxes.values()),
        }


__all__ = ["Mailbox", "MailboxRouter", "Message"]
