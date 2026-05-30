"""Unified EventBus — P4-X BREAKTHROUGH (HIGH impact, MEDIUM effort).

A bounded circular buffer event bus with JSONL persistence, subscription
filtering, and boot-scoped IDs. Replaces fragmented event systems across
the codebase with a single unified dispatch.

Integrates with the 50+ event hook pipeline (hooks.py) and provides a
migration path from ad-hoc event emitters.

See: plan-phase5-master-plan.md §P4-X
"""
from __future__ import annotations

import json
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Event:
    """A single event emitted on the unified bus.

    Attributes:
        event_id: Unique, boot-scoped identifier (UUID).
        name: Event name (e.g. "tool.pre_execute", "session.start").
        payload: Arbitrary event data (serializable to JSON).
        source: Which component emitted the event.
        timestamp: Unix timestamp when the event was created.
        boot_id: Boot-scoped identifier for correlation across restarts.
    """

    event_id: str
    name: str
    payload: dict[str, Any] = field(default_factory=dict)
    source: str = ""
    timestamp: float = 0.0
    boot_id: str = ""

    @classmethod
    def create(
        cls,
        name: str,
        payload: dict[str, Any] | None = None,
        source: str = "",
        boot_id: str = "",
        timestamp: float | None = None,
    ) -> Event:
        """Create a new event with a generated UUID."""
        return cls(
            event_id=uuid.uuid4().hex[:12],
            name=name,
            payload=payload or {},
            source=source,
            timestamp=timestamp or time.time(),
            boot_id=boot_id,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "name": self.name,
            "payload": self.payload,
            "source": self.source,
            "timestamp": self.timestamp,
            "boot_id": self.boot_id,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Event:
        return cls(
            event_id=raw["event_id"],
            name=raw["name"],
            payload=raw.get("payload", {}),
            source=raw.get("source", ""),
            timestamp=raw.get("timestamp", 0.0),
            boot_id=raw.get("boot_id", ""),
        )


# Subscription callback signature
Subscriber = Callable[[Event], None]


@dataclass
class Subscription:
    """A subscription to events matching a filter.

    The filter is a prefix string — a subscription for "tool." receives
    all events whose name starts with "tool." (e.g., "tool.pre_execute",
    "tool.post_execute").
    """

    id: str
    prefix_filter: str
    callback: Subscriber
    created_at: float = field(default_factory=time.time)


class EventBus:
    """Unified event bus with bounded buffer and JSONL persistence.

    Key design decisions:
    - Bounded circular buffer: 4096 events default (configurable)
    - JSONL persistence: append-only file for crash recovery and replay
    - Subscription filtering: prefix-based (e.g., "tool." matches "tool.pre_execute")
    - Thread-safe: all public methods use a re-entrant lock
    - Boot-scoped IDs: events carry a boot_id for correlation across restarts

    Usage::

        bus = EventBus()
        bus.subscribe("tool.", lambda e: print(f"Tool event: {e.name}"))
        bus.emit("tool.pre_execute", {"tool": "echo"})
        # → prints "Tool event: tool.pre_execute"
    """

    MAX_BUFFER = 4096

    def __init__(
        self,
        max_buffer: int = MAX_BUFFER,
        persistence_path: str = "",
        boot_id: str = "",
    ) -> None:
        self._lock = threading.RLock()
        self._buffer: list[Event] = []
        self._max_buffer = max_buffer
        self._subscriptions: dict[str, Subscription] = {}
        self._persistence_path = persistence_path
        self._boot_id = boot_id or uuid.uuid4().hex[:8]
        self._total_emitted: int = 0
        self._total_delivered: int = 0
        self._dropped: int = 0

    # -- Emit -----------------------------------------------------------------

    def emit(
        self,
        name: str,
        payload: dict[str, Any] | None = None,
        source: str = "",
    ) -> Event:
        """Emit an event to the bus.

        The event is added to the circular buffer, persisted if a
        persistence path is configured, and dispatched to all matching
        subscribers synchronously.
        """
        event = Event.create(
            name=name,
            payload=payload,
            source=source,
            boot_id=self._boot_id,
        )

        with self._lock:
            self._total_emitted += 1

            # Circular buffer
            self._buffer.append(event)
            if len(self._buffer) > self._max_buffer:
                self._buffer = self._buffer[-self._max_buffer:]
                self._dropped += 1

        # Persist (outside lock to avoid I/O contention)
        self._persist(event)

        # Dispatch to subscribers
        self._dispatch(event)

        return event

    def _dispatch(self, event: Event) -> None:
        """Deliver event to all matching subscribers."""
        with self._lock:
            subs = list(self._subscriptions.values())

        delivered = 0
        for sub in subs:
            if event.name.startswith(sub.prefix_filter):
                try:
                    sub.callback(event)
                    delivered += 1
                except Exception:
                    pass  # subscriber errors must not crash the bus

        with self._lock:
            self._total_delivered += delivered

    # -- Subscribe / Unsubscribe ----------------------------------------------

    def subscribe(self, prefix_filter: str, callback: Subscriber) -> str:
        """Subscribe to events matching a prefix filter.

        Args:
            prefix_filter: Prefix string (e.g., "tool.", "session.", or "" for all).
            callback: Function to call with each matching Event.

        Returns:
            A subscription ID that can be used to unsubscribe.
        """
        sub = Subscription(
            id=uuid.uuid4().hex[:8],
            prefix_filter=prefix_filter,
            callback=callback,
        )
        with self._lock:
            self._subscriptions[sub.id] = sub
        return sub.id

    def unsubscribe(self, subscription_id: str) -> bool:
        """Remove a subscription by ID.

        Returns:
            True if the subscription was found and removed.
        """
        with self._lock:
            if subscription_id in self._subscriptions:
                del self._subscriptions[subscription_id]
                return True
            return False

    def subscription_count(self) -> int:
        """Return the number of active subscriptions."""
        with self._lock:
            return len(self._subscriptions)

    # -- Buffer access --------------------------------------------------------

    def buffer_snapshot(self) -> list[Event]:
        """Return a snapshot of the current buffer (newest first)."""
        with self._lock:
            return list(reversed(self._buffer))

    def recent(self, n: int = 100) -> list[Event]:
        """Return the N most recent events."""
        with self._lock:
            return list(self._buffer[-n:])

    def events_matching(self, prefix_filter: str) -> list[Event]:
        """Return all buffered events matching a prefix filter."""
        with self._lock:
            return [e for e in self._buffer if e.name.startswith(prefix_filter)]

    # -- Stats ----------------------------------------------------------------

    def stats(self) -> dict[str, Any]:
        """Return aggregate statistics."""
        with self._lock:
            return {
                "total_emitted": self._total_emitted,
                "total_delivered": self._total_delivered,
                "buffer_size": len(self._buffer),
                "max_buffer": self._max_buffer,
                "subscriptions": len(self._subscriptions),
                "dropped": self._dropped,
                "boot_id": self._boot_id,
                "persistence_path": self._persistence_path,
            }

    def clear_buffer(self) -> None:
        """Clear the in-memory buffer (does not affect persistence)."""
        with self._lock:
            self._buffer.clear()

    # -- Persistence ----------------------------------------------------------

    def _persist(self, event: Event) -> None:
        """Append event to the JSONL persistence file (if configured)."""
        if not self._persistence_path:
            return
        try:
            line = json.dumps(event.to_dict(), default=str)
            with open(self._persistence_path, "a") as f:
                f.write(line + "\n")
        except OSError:
            pass  # persistence is best-effort

    def replay(self, since: float = 0.0) -> list[Event]:
        """Replay events from the persistence file.

        Args:
            since: Only return events with timestamp >= this value.

        Returns:
            List of replayed Event objects.
        """
        if not self._persistence_path:
            return []

        events: list[Event] = []
        try:
            with open(self._persistence_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        raw = json.loads(line)
                        event = Event.from_dict(raw)
                        if event.timestamp >= since:
                            events.append(event)
                    except (json.JSONDecodeError, KeyError):
                        continue  # skip corrupted lines
        except FileNotFoundError:
            return []
        return events

    def replay_by_boot(self, boot_id: str) -> list[Event]:
        """Replay events from a specific boot session."""
        if not self._persistence_path:
            return []

        events: list[Event] = []
        try:
            with open(self._persistence_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        raw = json.loads(line)
                        if raw.get("boot_id") == boot_id:
                            events.append(Event.from_dict(raw))
                    except (json.JSONDecodeError, KeyError):
                        continue
        except FileNotFoundError:
            return []
        return events


# -- Singleton access ---------------------------------------------------------


_global_bus: EventBus | None = None
_global_lock = threading.Lock()


def get_event_bus() -> EventBus:
    """Get or create the global singleton EventBus."""
    global _global_bus
    with _global_lock:
        if _global_bus is None:
            _global_bus = EventBus()
        return _global_bus


def set_event_bus(bus: EventBus) -> None:
    """Replace the global singleton EventBus (for testing)."""
    global _global_bus
    with _global_lock:
        _global_bus = bus


__all__ = [
    "Event",
    "EventBus",
    "get_event_bus",
    "set_event_bus",
    "Subscriber",
    "Subscription",
]
