"""Tests for Unified EventBus (P4-X)."""
from __future__ import annotations

import os
import tempfile
import time

import pytest

from lyra_harness_core.events.eventbus import (
    Event,
    EventBus,
    Subscription,
    get_event_bus,
    set_event_bus,
)


# ---------------------------------------------------------------------------
# Event
# ---------------------------------------------------------------------------


class TestEvent:
    def test_create_defaults(self):
        e = Event.create("test.event")
        assert e.name == "test.event"
        assert len(e.event_id) == 12
        assert e.payload == {}
        assert e.source == ""
        assert e.timestamp > 0

    def test_create_with_payload(self):
        e = Event.create("tool.call", {"tool": "echo", "args": {}}, source="test")
        assert e.payload["tool"] == "echo"
        assert e.source == "test"

    def test_create_with_boot_id(self):
        e = Event.create("boot.event", boot_id="abc123")
        assert e.boot_id == "abc123"

    def test_to_dict_roundtrip(self):
        e = Event.create("test.event", {"key": "value"}, source="src", boot_id="b1")
        d = e.to_dict()
        assert d["name"] == "test.event"
        assert d["payload"] == {"key": "value"}

    def test_from_dict(self):
        raw = {
            "event_id": "abc123",
            "name": "test.event",
            "payload": {"x": 1},
            "source": "s",
            "timestamp": 100.0,
            "boot_id": "b1",
        }
        e = Event.from_dict(raw)
        assert e.event_id == "abc123"
        assert e.name == "test.event"
        assert e.payload == {"x": 1}

    def test_frozen(self):
        e = Event.create("test.event")
        with pytest.raises(Exception):
            e.name = "other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Subscription
# ---------------------------------------------------------------------------


class TestSubscription:
    def test_subscription_fields(self):
        calls: list[Event] = []

        def handler(e: Event) -> None:
            calls.append(e)

        sub = Subscription(id="s1", prefix_filter="tool.", callback=handler)
        assert sub.id == "s1"
        assert sub.prefix_filter == "tool."

        # Verify callback works
        e = Event.create("tool.call")
        sub.callback(e)
        assert len(calls) == 1


# ---------------------------------------------------------------------------
# EventBus — Core
# ---------------------------------------------------------------------------


class TestEventBus:
    @pytest.fixture
    def bus(self):
        return EventBus()

    def test_emit_single(self, bus):
        e = bus.emit("test.event", {"key": "val"})
        assert e.name == "test.event"
        assert len(e.event_id) == 12

    def test_emit_returns_event(self, bus):
        e = bus.emit("test.event")
        assert isinstance(e, Event)
        assert e.boot_id == bus._boot_id

    def test_buffer_stores_events(self, bus):
        bus.emit("e1")
        bus.emit("e2")
        assert len(bus.recent(10)) == 2

    def test_recent_respects_n(self, bus):
        for i in range(10):
            bus.emit(f"e{i}")
        assert len(bus.recent(3)) == 3

    def test_recent_newest_last(self, bus):
        bus.emit("first")
        bus.emit("second")
        recent = bus.recent(10)
        assert recent[-1].name == "second"
        assert recent[0].name == "first"

    def test_buffer_snapshot_newest_first(self, bus):
        bus.emit("older")
        time.sleep(0.001)
        bus.emit("newer")
        snapshot = bus.buffer_snapshot()
        assert snapshot[0].name == "newer"

    def test_circular_buffer_drops_oldest(self, bus):
        bus._max_buffer = 5
        for i in range(10):
            bus.emit(f"e{i}")
        recent = bus.recent(10)
        assert len(recent) == 5
        assert recent[0].name == "e5"  # e0-e4 dropped

    def test_events_matching(self, bus):
        bus.emit("tool.pre_execute")
        bus.emit("tool.post_execute")
        bus.emit("session.start")
        matching = bus.events_matching("tool.")
        assert len(matching) == 2

    def test_clear_buffer(self, bus):
        bus.emit("e1")
        bus.clear_buffer()
        assert len(bus.recent(10)) == 0

    # -- Subscriptions --------------------------------------------------------

    def test_subscribe_receives_matching(self, bus):
        received: list[Event] = []
        bus.subscribe("tool.", lambda e: received.append(e))
        bus.emit("tool.call", {"arg": 1})
        assert len(received) == 1
        assert received[0].payload == {"arg": 1}

    def test_subscribe_no_match_not_received(self, bus):
        received: list[Event] = []
        bus.subscribe("tool.", lambda e: received.append(e))
        bus.emit("session.start")
        assert len(received) == 0

    def test_subscribe_all_prefix(self, bus):
        received: list[Event] = []
        bus.subscribe("", lambda e: received.append(e))
        bus.emit("a")
        bus.emit("b")
        assert len(received) == 2

    def test_unsubscribe(self, bus):
        received: list[Event] = []
        sid = bus.subscribe("tool.", lambda e: received.append(e))
        bus.emit("tool.call")
        assert len(received) == 1
        assert bus.unsubscribe(sid)
        bus.emit("tool.call")
        assert len(received) == 1  # no new delivery

    def test_unsubscribe_nonexistent(self, bus):
        assert not bus.unsubscribe("nonexistent")

    def test_subscription_count(self, bus):
        assert bus.subscription_count() == 0
        bus.subscribe("a.", lambda e: None)
        bus.subscribe("b.", lambda e: None)
        assert bus.subscription_count() == 2

    def test_subscriber_exception_does_not_crash(self, bus):
        def bad_handler(e: Event) -> None:
            raise RuntimeError("boom")

        received: list[Event] = []
        bus.subscribe("tool.", bad_handler)
        bus.subscribe("tool.", lambda e: received.append(e))
        bus.emit("tool.call")  # should not crash
        assert len(received) == 1  # good handler still called

    def test_multiple_matching_subscribers(self, bus):
        r1: list[Event] = []
        r2: list[Event] = []
        bus.subscribe("tool.", lambda e: r1.append(e))
        bus.subscribe("tool.", lambda e: r2.append(e))
        bus.emit("tool.call")
        assert len(r1) == 1
        assert len(r2) == 1

    # -- Stats ----------------------------------------------------------------

    def test_stats_defaults(self, bus):
        s = bus.stats()
        assert s["total_emitted"] == 0
        assert s["total_delivered"] == 0
        assert s["buffer_size"] == 0
        assert s["max_buffer"] == 4096
        assert s["subscriptions"] == 0
        assert s["dropped"] == 0

    def test_stats_after_emit(self, bus):
        bus.subscribe("tool.", lambda e: None)
        bus.emit("tool.call")
        bus.emit("tool.call")
        s = bus.stats()
        assert s["total_emitted"] == 2
        assert s["total_delivered"] == 2
        assert s["buffer_size"] == 2

    def test_stats_dropped(self, bus):
        bus._max_buffer = 2
        for _ in range(5):
            bus.emit("e")
        assert bus.stats()["dropped"] >= 1

    # -- Persistence ----------------------------------------------------------

    def test_persistence_roundtrip(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".jsonl") as f:
            path = f.name

        try:
            bus = EventBus(persistence_path=path)
            bus.emit("e1", {"n": 1})
            bus.emit("e2", {"n": 2})

            replayed = bus.replay()
            assert len(replayed) == 2
            assert replayed[0].name == "e1"
            assert replayed[0].payload == {"n": 1}
        finally:
            os.unlink(path)

    def test_replay_since(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".jsonl") as f:
            path = f.name

        try:
            bus = EventBus(persistence_path=path)
            bus.emit("old", {}, source="s")
            mid = time.time()
            time.sleep(0.01)
            bus.emit("new", {}, source="s")

            recent_events = bus.replay(since=mid)
            assert len(recent_events) == 1
            assert recent_events[0].name == "new"
        finally:
            os.unlink(path)

    def test_replay_by_boot(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".jsonl") as f:
            path = f.name

        try:
            bus1 = EventBus(persistence_path=path, boot_id="boot-a")
            bus1.emit("from_a")
            bus2 = EventBus(persistence_path=path, boot_id="boot-b")  # same file
            bus2.emit("from_b")

            # Replay from boot-a only
            events_a = bus1.replay_by_boot("boot-a")
            assert all(e.boot_id == "boot-a" for e in events_a)
            assert len(events_a) == 1
            assert events_a[0].name == "from_a"
        finally:
            os.unlink(path)

    def test_replay_no_file_returns_empty(self):
        bus = EventBus(persistence_path="/nonexistent/path.jsonl")
        assert bus.replay() == []

    def test_no_persistence_when_path_empty(self, bus):
        # Should not crash
        bus.emit("e")
        assert bus.replay() == []


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------


class TestSingleton:
    def test_get_event_bus_returns_same(self):
        b1 = get_event_bus()
        b2 = get_event_bus()
        assert b1 is b2

    def test_set_event_bus_replaces(self):
        original = get_event_bus()
        new_bus = EventBus()
        set_event_bus(new_bus)
        try:
            assert get_event_bus() is new_bus
        finally:
            set_event_bus(original)

    def test_singleton_is_eventbus(self):
        assert isinstance(get_event_bus(), EventBus)
