"""Comprehensive tests for the unified EventBus."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from lyra_core.events import (
    Event,
    EventBus,
    EventCategory,
    EventMetrics,
    ProjectEventBus,
)


class TestEvent:
    def test_create_event(self):
        e = Event(event_id="e1", seq=1, category=EventCategory.LIFECYCLE,
                  name="agent.started")
        assert e.event_id == "e1"
        assert e.seq == 1
        assert e.category == EventCategory.LIFECYCLE

    def test_to_json(self):
        e = Event(event_id="e1", seq=1, category=EventCategory.TASK,
                  name="task.completed", payload={"result": "ok"})
        j = e.to_json()
        assert "e1" in j
        assert "task.completed" in j
        assert "result" in j

    def test_event_immutable(self):
        e = Event(event_id="e1", seq=1, category=EventCategory.TASK,
                  name="test")
        with pytest.raises(Exception):
            e.name = "changed"  # type: ignore[misc]

    def test_all_categories(self):
        for cat in EventCategory:
            e = Event(event_id="e1", seq=1, category=cat, name="test")
            assert e.category == cat


class TestSubscription:
    def test_empty_matches_all(self):
        from lyra_core.events import Subscription
        sub = Subscription(id="sub1")
        e = Event(event_id="e1", seq=1, category=EventCategory.TASK,
                  name="test")
        assert sub.matches(e)

    def test_category_filter(self):
        from lyra_core.events import Subscription
        sub = Subscription(id="sub1", categories=(EventCategory.LIFECYCLE,))
        e1 = Event(event_id="e1", seq=1, category=EventCategory.LIFECYCLE,
                   name="test")
        e2 = Event(event_id="e2", seq=2, category=EventCategory.TASK,
                   name="test")
        assert sub.matches(e1)
        assert not sub.matches(e2)

    def test_name_pattern_filter(self):
        from lyra_core.events import Subscription
        sub = Subscription(id="sub1", name_patterns=("agent.",))
        e1 = Event(event_id="e1", seq=1, category=EventCategory.LIFECYCLE,
                   name="agent.started")
        e2 = Event(event_id="e2", seq=2, category=EventCategory.LIFECYCLE,
                   name="task.completed")
        assert sub.matches(e1)
        assert not sub.matches(e2)

    def test_agent_id_filter(self):
        from lyra_core.events import Subscription
        sub = Subscription(id="sub1", agent_ids=("a1",))
        e1 = Event(event_id="e1", seq=1, category=EventCategory.TASK,
                   name="test", source_agent_id="a1")
        e2 = Event(event_id="e2", seq=2, category=EventCategory.TASK,
                   name="test", source_agent_id="a2")
        assert sub.matches(e1)
        assert not sub.matches(e2)


class TestEventBus:
    def test_singleton(self):
        bus1 = EventBus.get()
        bus2 = EventBus.get()
        assert bus1 is bus2

    def test_publish_increments_seq(self):
        bus = EventBus()
        assert bus.sequence == 0
        bus.publish(EventCategory.TASK, "test")
        assert bus.sequence == 1
        bus.publish(EventCategory.TASK, "test2")
        assert bus.sequence == 2

    def test_publish_returns_event(self):
        bus = EventBus()
        e = bus.publish(EventCategory.TASK, "test")
        assert isinstance(e, Event)
        assert e.seq == 1

    def test_recent_events(self):
        bus = EventBus(buffer_size=10)
        for i in range(5):
            bus.publish(EventCategory.TASK, f"task.{i}")
        events = bus.recent_events()
        assert len(events) == 5

    def test_recent_events_respects_limit(self):
        bus = EventBus(buffer_size=10)
        for i in range(20):
            bus.publish(EventCategory.TASK, f"task.{i}")
        events = bus.recent_events()
        assert len(events) <= 100  # default limit
        assert len(bus.recent_events(limit=5)) == 5

    def test_recent_events_category_filter(self):
        bus = EventBus()
        bus.publish(EventCategory.LIFECYCLE, "test")
        bus.publish(EventCategory.TASK, "test2")
        bus.publish(EventCategory.TASK, "test3")

        lifecycle_events = bus.recent_events(category=EventCategory.LIFECYCLE)
        assert all(e.category == EventCategory.LIFECYCLE for e in lifecycle_events)

    def test_circular_buffer(self):
        bus = EventBus(buffer_size=3)
        for i in range(5):
            bus.publish(EventCategory.TASK, f"task.{i}")
        events = bus.recent_events()
        assert len(events) == 3
        # The oldest 2 should be dropped
        seqs = [e.seq for e in events]
        assert 1 not in seqs
        assert 2 not in seqs

    def test_subscribe_and_dispatch(self):
        bus = EventBus()
        received = []

        async def handler(e: Event) -> None:
            received.append(e)

        sub = bus.subscribe(
            categories=(EventCategory.TASK,),
            callback=handler,
        )
        bus.publish(EventCategory.TASK, "test.task")
        bus.publish(EventCategory.LIFECYCLE, "test.lifecycle")

        import asyncio
        asyncio.run(bus.drain_subscriptions())

        assert len(received) == 1
        assert received[0].name == "test.task"

    def test_unsubscribe(self):
        bus = EventBus()
        sub = bus.subscribe()
        assert bus.subscriber_count == 1
        bus.unsubscribe(sub.id)
        assert bus.subscriber_count == 0

    def test_replay_since_seq(self):
        bus = EventBus()
        for i in range(5):
            bus.publish(EventCategory.TASK, f"task.{i}")

        # Events 3-4 (seq > 2)
        replayed = bus.replay(since_seq=2)
        assert len(replayed) == 3
        assert all(e.seq > 2 for e in replayed)

    def test_jsonl_persistence(self):
        with tempfile.TemporaryDirectory() as tmp:
            replay_path = Path(tmp) / "events.jsonl"
            bus = EventBus(replay_path=replay_path)
            bus.publish(EventCategory.TASK, "test1")
            bus.publish(EventCategory.LIFECYCLE, "test2")

            assert replay_path.exists()
            lines = replay_path.read_text().strip().split("\n")
            assert len(lines) == 2

    def test_backpressure_enforcement(self):
        bus = EventBus()
        received = []

        async def handler(e: Event) -> None:
            received.append(e)

        sub = bus.subscribe(callback=handler, queue_max=2)
        # Publish more than queue_max
        for i in range(5):
            bus.publish(EventCategory.TASK, f"task.{i}")

        # Only last 2 should be in pending queue
        assert len(sub._pending) == 2


class TestProjectEventBus:
    def test_auto_fills_project_id(self):
        bus = EventBus()
        pb = ProjectEventBus(bus, "my_project")
        e = pb.emit(EventCategory.TASK, "test")
        assert e.source_project_id == "my_project"

    def test_passes_agent_id(self):
        bus = EventBus()
        pb = ProjectEventBus(bus, "my_project")
        e = pb.emit(EventCategory.TASK, "test", source_agent_id="agent_1")
        assert e.source_agent_id == "agent_1"
        assert e.source_project_id == "my_project"


class TestEventMetrics:
    def test_empty_bus(self):
        bus = EventBus()
        metrics = EventMetrics(bus)
        assert metrics.event_rate() == 0.0

    def test_category_counts(self):
        bus = EventBus()
        bus.publish(EventCategory.TASK, "t1")
        bus.publish(EventCategory.TASK, "t2")
        bus.publish(EventCategory.LIFECYCLE, "l1")

        metrics = EventMetrics(bus)
        counts = metrics.category_counts(window_seconds=3600)
        assert counts.get("task", 0) == 2
        assert counts.get("lifecycle", 0) == 1

    def test_agent_activity(self):
        bus = EventBus()
        bus.publish(EventCategory.TASK, "t1", source_agent_id="agent_a")
        bus.publish(EventCategory.TASK, "t2", source_agent_id="agent_a")
        bus.publish(EventCategory.TASK, "t3", source_agent_id="agent_b")

        metrics = EventMetrics(bus)
        activity = metrics.agent_activity(window_seconds=3600)
        assert activity.get("agent_a", 0) == 2
        assert activity.get("agent_b", 0) == 1
