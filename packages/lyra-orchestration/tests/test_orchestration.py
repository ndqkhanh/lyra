"""Tests for event bus and coordinator."""

import asyncio

import pytest

from lyra_orchestration import (
    AgentCoordinator,
    EventBus,
    ScanCompleted,
)


@pytest.mark.asyncio
async def test_event_bus_publish_subscribe():
    """Test basic pub/sub."""
    bus = EventBus()
    received_events = []

    async def handler(event):
        received_events.append(event)

    # Subscribe
    subscription = bus.subscribe("scan.completed", handler)

    # Publish
    event = ScanCompleted(
        target="192.168.1.100",
        findings=[{"cve": "CVE-2021-44228"}],
        scan_type="nmap",
    )
    await bus.publish(event)

    # Wait for async handlers
    await asyncio.sleep(0.1)

    assert len(received_events) == 1
    assert received_events[0].target == "192.168.1.100"

    # Unsubscribe
    bus.unsubscribe(subscription)


@pytest.mark.asyncio
async def test_event_history():
    """Test event history tracking."""
    bus = EventBus()

    # Publish events
    await bus.publish(ScanCompleted(target="host1", findings=[], scan_type="nmap"))
    await bus.publish(ScanCompleted(target="host2", findings=[], scan_type="nmap"))

    # Get history
    history = bus.get_history()
    assert len(history) == 2

    # Filter by type
    scan_history = bus.get_history(event_type="scan.completed")
    assert len(scan_history) == 2


@pytest.mark.asyncio
async def test_agent_coordinator_parallel():
    """Test parallel agent execution."""
    bus = EventBus()
    coordinator = AgentCoordinator(bus)

    results = []

    async def agent1():
        await asyncio.sleep(0.1)
        results.append("agent1")
        return {"status": "done"}

    async def agent2():
        await asyncio.sleep(0.1)
        results.append("agent2")
        return {"status": "done"}

    # Register agents
    coordinator.register_agent("agent1", "recon", agent1)
    coordinator.register_agent("agent2", "scan", agent2)

    # Execute
    execution_results = await coordinator.execute()

    assert len(results) == 2
    assert execution_results["agent1"]["status"] == "completed"
    assert execution_results["agent2"]["status"] == "completed"


@pytest.mark.asyncio
async def test_agent_coordinator_dependencies():
    """Test agent dependency management."""
    bus = EventBus()
    coordinator = AgentCoordinator(bus)

    execution_order = []

    async def agent1():
        execution_order.append("agent1")
        return {"data": "from_agent1"}

    async def agent2():
        execution_order.append("agent2")
        return {"data": "from_agent2"}

    # Register with dependency
    coordinator.register_agent("agent1", "recon", agent1)
    coordinator.register_agent("agent2", "scan", agent2, dependencies=["agent1"])

    # Execute
    await coordinator.execute()

    # Agent1 should execute before agent2
    assert execution_order == ["agent1", "agent2"]


@pytest.mark.asyncio
async def test_agent_coordinator_failure():
    """Test agent failure handling."""
    bus = EventBus()
    coordinator = AgentCoordinator(bus)

    async def failing_agent():
        raise ValueError("Test error")

    coordinator.register_agent("failing", "test", failing_agent)

    results = await coordinator.execute()

    assert results["failing"]["status"] == "failed"
    assert "Test error" in results["failing"]["error"]


def test_event_bus_stats():
    """Test event bus statistics."""
    bus = EventBus()

    stats = bus.get_stats()
    assert stats["total_events"] == 0
    assert stats["total_subscriptions"] == 0


def test_coordinator_stats():
    """Test coordinator statistics."""
    bus = EventBus()
    coordinator = AgentCoordinator(bus)

    async def dummy():
        pass

    coordinator.register_agent("agent1", "test", dummy)

    stats = coordinator.get_stats()
    assert stats["total_tasks"] == 1
    assert stats["pending"] == 1
