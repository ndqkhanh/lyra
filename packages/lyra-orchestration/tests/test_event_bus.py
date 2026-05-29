"""Tests for lyra-orchestration event_bus module."""

from __future__ import annotations

import asyncio

import pytest

from lyra_orchestration.event_bus import (
    AgentCompleted,
    AgentFailed,
    AgentStarted,
    Event,
    EventBus,
    EventPriority,
    ExploitAttempted,
    IntegrationSynced,
    MemoryIngested,
    ScanCompleted,
    Subscription,
    VulnerabilityDiscovered,
)


class TestEvent:
    def test_creation_defaults(self):
        e = Event(event_type="test.event")
        assert e.event_type == "test.event"
        assert e.event_id is not None
        assert e.priority == EventPriority.NORMAL
        assert e.timestamp is not None

    def test_creation_with_priority(self):
        e = Event(event_type="test.event", priority=EventPriority.CRITICAL)
        assert e.priority == EventPriority.CRITICAL

    def test_metadata(self):
        e = Event(event_type="test.event", metadata={"key": "value"})
        assert e.metadata["key"] == "value"


class TestDomainEvents:
    def test_agent_started(self):
        e = AgentStarted(agent_id="a1", agent_type="executor")
        assert e.event_type == "agent.started"
        assert e.agent_id == "a1"

    def test_agent_completed(self):
        e = AgentCompleted(agent_id="a1", agent_type="executor", result={"ok": True})
        assert e.event_type == "agent.completed"
        assert e.result == {"ok": True}

    def test_agent_failed(self):
        e = AgentFailed(agent_id="a1", agent_type="executor", error="timeout")
        assert e.event_type == "agent.failed"
        assert e.error == "timeout"

    def test_scan_completed(self):
        e = ScanCompleted(target="app", findings=[{"id": 1}], scan_type="sast")
        assert e.event_type == "scan.completed"
        assert len(e.findings) == 1

    def test_vulnerability_discovered(self):
        e = VulnerabilityDiscovered(
            cve="CVE-2024-1234",
            severity="HIGH",
            exploitable=True,
            affected_asset="api-server",
            affected_service="auth",
        )
        assert e.cve == "CVE-2024-1234"
        assert e.severity == "HIGH"
        assert e.exploitable is True

    def test_exploit_attempted(self):
        e = ExploitAttempted(target="api", exploit_name="sqli", success=True)
        assert e.exploit_name == "sqli"
        assert e.success is True

    def test_memory_ingested(self):
        e = MemoryIngested(namespace="default", doc_count=42)
        assert e.namespace == "default"
        assert e.doc_count == 42

    def test_integration_synced(self):
        e = IntegrationSynced(provider="github", items_fetched=100)
        assert e.provider == "github"


class TestSubscription:
    def test_creation(self):
        s = Subscription(subscription_id="s1", event_type="test", handler=lambda e: None)
        assert s.subscription_id == "s1"

    def test_hash(self):
        s1 = Subscription(subscription_id="s1", event_type="t", handler=lambda e: None)
        s2 = Subscription(subscription_id="s1", event_type="t", handler=lambda e: None)
        assert hash(s1) == hash(s2)


class TestEventBus:
    @pytest.fixture
    def bus(self):
        return EventBus()

    def test_subscribe_returns_subscription(self, bus):
        sub = bus.subscribe("test.event", lambda e: None)
        assert isinstance(sub, Subscription)
        assert sub.event_type == "test.event"

    def test_unsubscribe(self, bus):
        sub = bus.subscribe("test.event", lambda e: None)
        bus.unsubscribe(sub)
        assert len(bus._subscriptions.get("test.event", set())) == 0

    def test_multiple_subscriptions_same_type(self, bus):
        bus.subscribe("test.event", lambda e: None)
        bus.subscribe("test.event", lambda e: None)
        assert len(bus._subscriptions["test.event"]) == 2

    @pytest.mark.asyncio
    async def test_publish_calls_handler(self, bus):
        called = []
        bus.subscribe("test.event", lambda e: called.append(e.event_type))
        await bus.publish(Event(event_type="test.event"))
        assert len(called) == 1
        assert called[0] == "test.event"

    @pytest.mark.asyncio
    async def test_publish_async_handler(self, bus):
        called = []

        async def async_handler(event):
            called.append("async")

        bus.subscribe("test.event", async_handler)
        await bus.publish(Event(event_type="test.event"))
        assert len(called) == 1
        assert called[0] == "async"

    @pytest.mark.asyncio
    async def test_publish_multiple_handlers(self, bus):
        results = []
        bus.subscribe("test.event", lambda e: results.append(1))
        bus.subscribe("test.event", lambda e: results.append(2))
        bus.subscribe("test.event", lambda e: results.append(3))
        await bus.publish(Event(event_type="test.event"))
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_publish_no_subscribers_no_error(self, bus):
        await bus.publish(Event(event_type="unsubscribed.event"))

    @pytest.mark.asyncio
    async def test_publish_stores_history(self, bus):
        await bus.publish(Event(event_type="test.event"))
        await bus.publish(Event(event_type="test.event"))
        assert len(bus._event_history) == 2

    @pytest.mark.asyncio
    async def test_history_capped(self, bus):
        bus._max_history = 5
        for i in range(10):
            await bus.publish(Event(event_type=f"e{i}"))
        assert len(bus._event_history) <= 5

    @pytest.mark.asyncio
    async def test_handler_error_does_not_propagate(self, bus):
        def bad_handler(event):
            raise RuntimeError("test error")

        bus.subscribe("test.event", bad_handler)
        await bus.publish(Event(event_type="test.event"))  # Should not raise

    def test_get_history_all(self, bus):
        bus._event_history = [Event(event_type="a"), Event(event_type="b"), Event(event_type="a")]
        history = bus.get_history()
        assert len(history) == 3

    def test_get_history_filtered(self, bus):
        bus._event_history = [Event(event_type="a"), Event(event_type="b")]
        history = bus.get_history(event_type="a")
        assert len(history) == 1

    def test_get_history_limit(self, bus):
        bus._event_history = [Event(event_type=f"e{i}") for i in range(200)]
        history = bus.get_history(limit=10)
        assert len(history) == 10

    def test_clear_history(self, bus):
        bus._event_history = [Event(event_type="a"), Event(event_type="b")]
        bus.clear_history()
        assert len(bus._event_history) == 0

    def test_get_stats(self, bus):
        bus._event_history = [
            Event(event_type="a"),
            Event(event_type="a"),
            Event(event_type="b"),
        ]
        stats = bus.get_stats()
        assert stats["total_events"] == 3
        assert stats["event_counts"]["a"] == 2
        assert stats["event_counts"]["b"] == 1

    def test_priority_ordering(self, bus):
        call_order = []

        bus.subscribe(
            "test.event", lambda e: call_order.append("critical"), priority=EventPriority.CRITICAL
        )
        bus.subscribe("test.event", lambda e: call_order.append("low"), priority=EventPriority.LOW)
        bus.subscribe(
            "test.event", lambda e: call_order.append("normal"), priority=EventPriority.NORMAL
        )

        asyncio.run(bus.publish(Event(event_type="test.event")))
        # Highest priority (CRITICAL=4) delivered first
        assert call_order[0] == "critical"
