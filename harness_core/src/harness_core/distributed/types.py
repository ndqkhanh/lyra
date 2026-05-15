"""Types for distributed — Envelope + Subscription + matching helpers."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Envelope:
    """One message on the bus.

    >>> e = Envelope.create(
    ...     topic="agent.alice",
    ...     payload={"hello": "world"},
    ...     issued_by="loop-1",
    ... )
    >>> e.topic
    'agent.alice'
    """

    envelope_id: str
    topic: str
    payload: dict
    issued_by: str
    timestamp: float
    reply_to: Optional[str] = None
    correlation_id: Optional[str] = None

    @classmethod
    def create(
        cls,
        *,
        topic: str,
        payload: dict,
        issued_by: str,
        reply_to: Optional[str] = None,
        correlation_id: Optional[str] = None,
        envelope_id: Optional[str] = None,
        timestamp: Optional[float] = None,
    ) -> "Envelope":
        if not topic:
            raise ValueError("topic must be non-empty")
        return cls(
            envelope_id=envelope_id or str(uuid.uuid4()),
            topic=topic,
            payload=dict(payload),
            issued_by=issued_by,
            timestamp=timestamp if timestamp is not None else time.time(),
            reply_to=reply_to,
            correlation_id=correlation_id,
        )


def topic_matches(pattern: str, topic: str) -> bool:
    """NATS-style topic match.

    - ``*`` in a pattern segment matches exactly one topic segment.
    - ``>`` as the last pattern segment matches one-or-more remaining segments.
    - Otherwise segments must match literally.

    >>> topic_matches("agent.*", "agent.alice")
    True
    >>> topic_matches("agent.*", "agent.alice.x")
    False
    >>> topic_matches("agent.>", "agent.alice.x")
    True
    >>> topic_matches("agent.alice", "agent.alice")
    True
    >>> topic_matches("agent.bob", "agent.alice")
    False
    """
    if not pattern or not topic:
        return False
    pat_parts = pattern.split(".")
    top_parts = topic.split(".")
    for i, p in enumerate(pat_parts):
        if p == ">":
            # ``>`` must be the last segment AND consume one-or-more remaining.
            return i == len(pat_parts) - 1 and i < len(top_parts)
        if i >= len(top_parts):
            return False
        if p == "*":
            continue
        if p != top_parts[i]:
            return False
    return len(pat_parts) == len(top_parts)


@dataclass
class Subscription:
    """Handle to a subscription. ``unsubscribe()`` detaches the handler.

    Subscriptions are managed by :class:`Bus`; do not construct directly —
    use :meth:`Bus.subscribe`.
    """

    sub_id: str
    topic_pattern: str
    handler: object  # callable: (Envelope) -> Optional[dict]
    _bus: object = field(default=None)
    _active: bool = True

    def unsubscribe(self) -> None:
        if self._active and self._bus is not None:
            self._bus._remove_subscription(self.sub_id)  # noqa: SLF001
        self._active = False

    @property
    def active(self) -> bool:
        return self._active


__all__ = ["Envelope", "Subscription", "topic_matches"]
