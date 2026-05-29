"""Unified EventBus with JSONL persistence.

Replaces the fragmented event systems:
  - HIR JSONL (lyra-core/observability/hir.py)
  - TypedEventBus (lyra-orchestration/event_bus.py)
  - MessageBus (lyra-colony/communication.py)

Inspired by cmux's CmuxEventBus:
  - Thread-safe singleton with circular buffer
  - Boot-scoped IDs, sequence numbers
  - Subscription filtering by name/category
  - Backpressure via per-subscriber queue limits
  - JSONL file persistence for crash recovery
  - Every event carries an origin field
"""

from __future__ import annotations

import json
import logging
import threading
import time
from collections import defaultdict
from collections.abc import Callable, Coroutine
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ── Event Types ─────────────────────────────────────────────────────────────


class EventCategory(str, Enum):
    """Categories for subscription filtering. Inspired by cmux."""

    LIFECYCLE = "lifecycle"          # agent create/start/stop/destroy
    TASK = "task"                     # task start/complete/fail
    TOOL = "tool"                     # tool call/result
    REVIEW = "review"                 # adversarial review pass/fail
    NOTIFICATION = "notification"     # human-in-the-loop alerts
    TELEMETRY = "telemetry"           # metrics, cost, performance
    SYSTEM = "system"                 # server-level events
    CONFIG = "config"                 # configuration changes
    WORKSTREAM = "workstream"         # workstream item state changes


@dataclass(frozen=True)
class Event:
    """Immutable event envelope."""

    event_id: str
    seq: int
    category: EventCategory
    name: str
    source_agent_id: str = ""
    source_project_id: str = ""
    origin: str = ""  # file:line where event was published
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    correlation_id: str | None = None

    def to_json(self) -> str:
        return json.dumps(asdict(self), default=str)


# ── Subscription ────────────────────────────────────────────────────────────


@dataclass
class Subscription:
    """A subscriber's filter and callback."""

    id: str
    categories: tuple[EventCategory, ...] = ()
    name_patterns: tuple[str, ...] = ()
    agent_ids: tuple[str, ...] = ()
    project_ids: tuple[str, ...] = ()
    callback: Callable[[Event], Coroutine[Any, Any, None]] | None = None
    queue_max: int = 1024  # per-subscriber backpressure limit
    _pending: list[Event] = field(default_factory=list, repr=False)

    def matches(self, event: Event) -> bool:
        """Check if an event matches this subscription's filters."""
        if self.categories and event.category not in self.categories:
            return False
        if self.name_patterns:
            if not any(p in event.name for p in self.name_patterns):
                return False
        if self.agent_ids and event.source_agent_id not in self.agent_ids:
            return False
        if self.project_ids and event.source_project_id not in self.project_ids:
            return False
        return True


# ── EventBus ────────────────────────────────────────────────────────────────


class EventBus:
    """Unified event bus for Lyra.

    Thread-safe. Supports both sync publish and async subscriber dispatch.
    Maintains a bounded circular buffer in memory and writes every event
    to a JSONL file for crash recovery and replay.
    """

    _instance: EventBus | None = None
    _lock = threading.Lock()

    def __init__(
        self,
        buffer_size: int = 4096,
        replay_path: Path | None = None,
    ) -> None:
        self._buffer: list[Event] = []
        self._buffer_size = buffer_size
        self._seq: int = 0
        self._subscriptions: dict[str, Subscription] = {}
        self._subscription_lock = threading.Lock()
        self._replay_path = replay_path
        if self._replay_path:
            self._replay_path.parent.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get(cls, buffer_size: int = 4096, replay_path: str = ".lyra/events.jsonl") -> EventBus:
        """Get (or create) the singleton EventBus."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(
                        buffer_size=buffer_size,
                        replay_path=Path(replay_path),
                    )
        return cls._instance

    # ── Publish ─────────────────────────────────────────────────────────

    def publish(
        self,
        category: EventCategory,
        name: str,
        *,
        source_agent_id: str = "",
        source_project_id: str = "",
        origin: str = "",
        payload: dict[str, Any] | None = None,
        correlation_id: str | None = None,
    ) -> Event:
        """Publish an event synchronously. Thread-safe."""
        self._seq += 1
        event = Event(
            event_id=f"evt_{self._seq:016x}",
            seq=self._seq,
            category=category,
            name=name,
            source_agent_id=source_agent_id,
            source_project_id=source_project_id,
            origin=origin,
            payload=payload or {},
            correlation_id=correlation_id,
        )

        # Append to circular buffer
        if len(self._buffer) >= self._buffer_size:
            self._buffer.pop(0)
        self._buffer.append(event)

        # Persist to JSONL
        if self._replay_path:
            try:
                with open(self._replay_path, "a") as f:
                    f.write(event.to_json() + "\n")
            except Exception:
                logger.warning("Failed to persist event to %s", self._replay_path,
                               exc_info=True)

        # Dispatch to matching subscriptions
        with self._subscription_lock:
            for sub in list(self._subscriptions.values()):
                if sub.matches(event):
                    sub._pending.append(event)
                    # Enforce backpressure: drop oldest if queue exceeds limit
                    while len(sub._pending) > sub.queue_max:
                        sub._pending.pop(0)

        return event

    # ── Subscribe ───────────────────────────────────────────────────────

    def subscribe(
        self,
        *,
        categories: tuple[EventCategory, ...] = (),
        name_patterns: tuple[str, ...] = (),
        agent_ids: tuple[str, ...] = (),
        project_ids: tuple[str, ...] = (),
        callback: Callable[[Event], Coroutine[Any, Any, None]] | None = None,
        queue_max: int = 1024,
    ) -> Subscription:
        """Register a subscription. Returns the Subscription object."""
        sub = Subscription(
            id=f"sub_{self._seq:016x}",
            categories=categories,
            name_patterns=name_patterns,
            agent_ids=agent_ids,
            project_ids=project_ids,
            callback=callback,
            queue_max=queue_max,
        )
        with self._subscription_lock:
            self._subscriptions[sub.id] = sub
        return sub

    def unsubscribe(self, subscription_id: str) -> None:
        """Remove a subscription."""
        with self._subscription_lock:
            self._subscriptions.pop(subscription_id, None)

    # ── Drain ───────────────────────────────────────────────────────────

    async def drain_subscriptions(self) -> None:
        """Deliver pending events to all subscribers' callbacks.

        Should be called periodically from the event loop.
        """
        with self._subscription_lock:
            subs = list(self._subscriptions.values())

        for sub in subs:
            if sub.callback is None:
                continue
            while sub._pending:
                event = sub._pending.pop(0)
                try:
                    await sub.callback(event)
                except Exception:
                    logger.warning("Subscriber %s failed to handle event %s",
                                   sub.id, event.event_id, exc_info=True)

    # ── Query ───────────────────────────────────────────────────────────

    def recent_events(
        self,
        category: EventCategory | None = None,
        limit: int = 100,
    ) -> list[Event]:
        """Get recent events, optionally filtered by category."""
        events = self._buffer
        if category:
            events = [e for e in events if e.category == category]
        return list(reversed(events[-limit:]))

    def replay(
        self,
        since_seq: int = 0,
        category: EventCategory | None = None,
    ) -> list[Event]:
        """Replay events since a given sequence number."""
        events = [e for e in self._buffer if e.seq > since_seq]
        if category:
            events = [e for e in events if e.category == category]
        return events

    @property
    def sequence(self) -> int:
        """Current sequence number."""
        return self._seq

    @property
    def subscriber_count(self) -> int:
        """Number of active subscriptions."""
        return len(self._subscriptions)


# ── Convenience: project-scoped bus ─────────────────────────────────────────


class ProjectEventBus:
    """A project-scoped wrapper that auto-fills project_id.

    Use this in agent code to avoid repeating source_project_id on every call.
    """

    def __init__(self, bus: EventBus, project_id: str) -> None:
        self._bus = bus
        self._project_id = project_id

    def emit(
        self,
        category: EventCategory,
        name: str,
        *,
        source_agent_id: str = "",
        origin: str = "",
        payload: dict[str, Any] | None = None,
        correlation_id: str | None = None,
    ) -> Event:
        return self._bus.publish(
            category=category,
            name=name,
            source_agent_id=source_agent_id,
            source_project_id=self._project_id,
            origin=origin,
            payload=payload,
            correlation_id=correlation_id,
        )


# ── Metrics Collector ───────────────────────────────────────────────────────


class EventMetrics:
    """Collects aggregate metrics from the event stream."""

    def __init__(self, bus: EventBus) -> None:
        self._bus = bus

    def event_rate(self, category: EventCategory | None = None,
                   window_seconds: float = 60.0) -> float:
        """Events per second over the given window."""
        now = time.time()
        events = self._bus.recent_events(category=category, limit=1000)
        recent = [e for e in events if now - e.timestamp <= window_seconds]
        if not recent:
            return 0.0
        elapsed = max(now - recent[-1].timestamp, 1e-6)
        return len(recent) / elapsed

    def category_counts(self, window_seconds: float = 300.0) -> dict[str, int]:
        """Count events per category in the recent window."""
        now = time.time()
        counts: dict[str, int] = defaultdict(int)
        for e in self._bus.recent_events(limit=2000):
            if now - e.timestamp <= window_seconds:
                counts[e.category.value] += 1
        return dict(counts)

    def agent_activity(self, window_seconds: float = 300.0) -> dict[str, int]:
        """Count events per agent in the recent window."""
        now = time.time()
        counts: dict[str, int] = defaultdict(int)
        for e in self._bus.recent_events(limit=2000):
            if now - e.timestamp <= window_seconds and e.source_agent_id:
                counts[e.source_agent_id] += 1
        return dict(counts)
