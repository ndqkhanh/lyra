"""Bus — in-process pub/sub emulating NATS leaf-node mesh semantics.

Pure stdlib, deterministic, synchronous: handlers run inline on
:meth:`publish`. Production wires nats.py / aio-nats / Redis Streams /
ZeroMQ through the same surface; the in-process Bus is the cold-start
fallback that's testable without a broker.

Features:

    - Wildcard subscriptions (``agent.*``, ``agent.>``) per NATS conventions.
    - Namespace-prefixed buses (``Bus(namespace="proj-A")`` → all topics
      published or subscribed get ``proj-A.`` prefixed transparently).
    - Request/reply with timeout: a request sets up a one-shot reply
      subscriber on a unique inbox topic, publishes, then drains pending
      replies until either a reply arrives or the timeout (against a
      pluggable clock) elapses.
    - Witness emission: every publish optionally records a CUSTOM witness
      on a :class:`WitnessLattice` so distributed messaging is auditable.

The bus does not run handlers concurrently and does not own a thread —
it's a synchronous router. Concurrency is the caller's responsibility.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from ..provenance import WitnessKind, WitnessLattice
from .types import Envelope, Subscription, topic_matches


Handler = Callable[[Envelope], Optional[dict]]


@dataclass
class Bus:
    """In-process pub/sub bus.

    >>> bus = Bus()
    >>> received = []
    >>> sub = bus.subscribe("agent.*", lambda env: received.append(env.topic))
    >>> _ = bus.publish(topic="agent.alice", payload={"hi": 1})
    >>> received
    ['agent.alice']
    """

    namespace: str = ""
    lattice: Optional[WitnessLattice] = None
    audit_kind: WitnessKind = WitnessKind.CUSTOM
    clock_fn: Any = field(default_factory=lambda: time.time)
    _subs: dict[str, Subscription] = field(default_factory=dict)
    _envelopes: list[Envelope] = field(default_factory=list)
    _pending_replies: dict[str, list[Envelope]] = field(default_factory=dict)

    # --- Public API ------------------------------------------------------

    def subscribe(self, topic_pattern: str, handler: Handler) -> Subscription:
        """Register a handler for a topic pattern. Returns a Subscription handle."""
        if not topic_pattern:
            raise ValueError("topic_pattern must be non-empty")
        full_pattern = self._with_namespace(topic_pattern)
        sub = Subscription(
            sub_id=str(uuid.uuid4()),
            topic_pattern=full_pattern,
            handler=handler,
            _bus=self,
        )
        self._subs[sub.sub_id] = sub
        return sub

    def publish(
        self,
        *,
        topic: str,
        payload: dict,
        issued_by: str = "anonymous",
        reply_to: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Envelope:
        """Publish a message; invoke every matching subscriber inline."""
        full_topic = self._with_namespace(topic)
        full_reply_to = (
            self._with_namespace(reply_to) if reply_to else None
        )
        env = Envelope.create(
            topic=full_topic,
            payload=payload,
            issued_by=issued_by,
            reply_to=full_reply_to,
            correlation_id=correlation_id,
            timestamp=self.clock_fn(),
        )
        self._envelopes.append(env)
        self._record_audit(env)
        self._dispatch(env)
        return env

    def request(
        self,
        *,
        topic: str,
        payload: dict,
        timeout: float,
        issued_by: str = "anonymous",
        poll_interval: float = 0.0,
    ) -> Optional[Envelope]:
        """Publish a request; return the first reply or None on timeout.

        How it works:
            1. Generate a unique inbox topic (``_INBOX.<uuid>``).
            2. Subscribe a one-shot collector to the inbox.
            3. Publish the request with ``reply_to=inbox`` so handlers can
               publish replies back through :meth:`publish`. Inline-replies
               populate the inbox synchronously.
            4. Drain the inbox until a reply arrives or ``timeout`` elapses
               against ``clock_fn``.
        """
        if timeout < 0:
            raise ValueError(f"timeout must be >= 0, got {timeout}")
        inbox = f"_INBOX.{uuid.uuid4()}"
        full_inbox = self._with_namespace(inbox)
        replies: list[Envelope] = []
        sub = self.subscribe(inbox, lambda env: replies.append(env) or None)

        try:
            self.publish(
                topic=topic,
                payload=payload,
                issued_by=issued_by,
                reply_to=inbox,
                correlation_id=str(uuid.uuid4()),
            )
            if replies:
                return replies[0]
            # No inline reply — poll the clock until timeout elapses.
            t_start = self.clock_fn()
            while (self.clock_fn() - t_start) < timeout:
                if replies:
                    return replies[0]
                if poll_interval > 0:
                    time.sleep(poll_interval)
                else:
                    break
            return replies[0] if replies else None
        finally:
            sub.unsubscribe()

    def reply(
        self,
        *,
        to: Envelope,
        payload: dict,
        issued_by: str = "anonymous",
    ) -> Optional[Envelope]:
        """Helper: publish a reply to the ``reply_to`` of an envelope.

        Returns the published envelope or None if the request had no reply_to.
        """
        if not to.reply_to:
            return None
        # ``to.reply_to`` is already namespace-qualified.
        env = Envelope.create(
            topic=to.reply_to,
            payload=payload,
            issued_by=issued_by,
            correlation_id=to.correlation_id,
            timestamp=self.clock_fn(),
        )
        self._envelopes.append(env)
        self._record_audit(env)
        self._dispatch(env)
        return env

    def history(
        self,
        *,
        topic_pattern: Optional[str] = None,
    ) -> list[Envelope]:
        """All envelopes ever published on this bus, optionally filtered."""
        if topic_pattern is None:
            return list(self._envelopes)
        full_pattern = self._with_namespace(topic_pattern)
        return [e for e in self._envelopes if topic_matches(full_pattern, e.topic)]

    def n_subscriptions(self) -> int:
        return len(self._subs)

    # --- Internals -------------------------------------------------------

    def _dispatch(self, env: Envelope) -> None:
        # Iterate over a snapshot — handlers may un/subscribe during dispatch.
        for sub in list(self._subs.values()):
            if not sub.active:
                continue
            if topic_matches(sub.topic_pattern, env.topic):
                sub.handler(env)

    def _remove_subscription(self, sub_id: str) -> None:
        self._subs.pop(sub_id, None)

    def _with_namespace(self, topic: str) -> str:
        if not self.namespace:
            return topic
        prefix = f"{self.namespace}."
        if topic.startswith(prefix):
            return topic
        return prefix + topic

    def _record_audit(self, env: Envelope) -> None:
        if self.lattice is None:
            return
        from ..provenance import Witness
        w = Witness.create(
            kind=self.audit_kind,
            issued_by=env.issued_by,
            content={
                "topic": env.topic,
                "envelope_id": env.envelope_id,
                "reply_to": env.reply_to,
                "correlation_id": env.correlation_id,
                "payload_keys": sorted(env.payload.keys()),
            },
        )
        self.lattice.ledger.append(w)


__all__ = ["Bus", "Handler"]
