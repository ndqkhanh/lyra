"""harness_core.distributed — in-process pub/sub bus emulating NATS semantics.

Multi-agent systems need a transport. Production usually wires NATS
leaf-node mesh, Redis Streams, or ZeroMQ; the in-process :class:`Bus`
here is the deterministic, dependency-free fallback that ships in tests
and lets harness_core composers (teams, marketplace, isolation) wire
pub/sub without standing up a broker.

Key features:
    - Wildcard subscriptions (``*`` for one segment, ``>`` for tail).
    - Namespace prefixing for tenant/project isolation.
    - Synchronous publish; one-shot inbox-style request/reply with timeout.
    - Optional witness emission for audit-grade messaging.

Used by Lyra (architecture-spec hub), Aegis-Ops (post-mortem broadcast),
Mentat-Learn (cross-channel signal sharing), Orion-Code (cross-agent
PR coordination), Polaris (sub-agent fanout in research sessions).
"""
from __future__ import annotations

from .bus import Bus, Handler
from .types import Envelope, Subscription, topic_matches

__all__ = [
    "Bus",
    "Envelope",
    "Handler",
    "Subscription",
    "topic_matches",
]
