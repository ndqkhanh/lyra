"""Tests for the agent monitor module."""

from __future__ import annotations

import time

import pytest
from lyra_cockpit.agent_monitor import (
    AgentMonitor,
    AgentStatus,
    MonitorConfig,
    ResourceUsage,
)
from lyra_cockpit.exceptions import MonitorError


class TestMonitorConfig:
    def test_default_values(self) -> None:
        config = MonitorConfig()
        assert config.refresh_interval == 1.0
        assert config.max_agents == 50
        assert config.alert_threshold_cpu == 90.0

    def test_custom_values(self) -> None:
        config = MonitorConfig(refresh_interval=2.5, max_agents=10, alert_threshold_cpu=80.0)
        assert config.refresh_interval == 2.5
        assert config.max_agents == 10
        assert config.alert_threshold_cpu == 80.0


class TestAgentStatus:
    def test_creation(self) -> None:
        now = time.time()
        status = AgentStatus(
            agent_id="agent-001",
            state="idle",
            cpu_pct=12.5,
            mem_mb=256.0,
            active_tasks=0,
            last_heartbeat=now,
        )
        assert status.agent_id == "agent-001"
        assert status.state == "idle"
        assert status.cpu_pct == 12.5
        assert status.active_tasks == 0

    def test_high_cpu(self) -> None:
        now = time.time()
        status = AgentStatus(
            agent_id="agent-busy",
            state="busy",
            cpu_pct=95.0,
            mem_mb=1024.0,
            active_tasks=3,
            last_heartbeat=now,
        )
        assert status.cpu_pct == 95.0
        assert status.active_tasks == 3

    def test_frozen(self) -> None:
        now = time.time()
        status = AgentStatus("a1", "idle", 0.0, 0.0, 0, now)
        with pytest.raises(AttributeError):
            status.state = "busy"  # type: ignore[misc]


class TestResourceUsage:
    def test_creation(self) -> None:
        usage = ResourceUsage(
            agent_id="agent-001",
            token_count=15000,
            latency_ms=250.5,
            cost_estimate=0.015,
        )
        assert usage.agent_id == "agent-001"
        assert usage.token_count == 15000
        assert usage.latency_ms == 250.5
        assert usage.cost_estimate == 0.015

    def test_zero_values(self) -> None:
        usage = ResourceUsage(
            agent_id="agent-002", token_count=0, latency_ms=0.0, cost_estimate=0.0
        )
        assert usage.token_count == 0

    def test_frozen(self) -> None:
        usage = ResourceUsage("a1", 0, 0.0, 0.0)
        with pytest.raises(AttributeError):
            usage.token_count = 100  # type: ignore[misc]


class TestAgentMonitor:
    def test_config_property(self) -> None:
        config = MonitorConfig(refresh_interval=5.0)
        monitor = AgentMonitor(config)
        assert monitor.config.refresh_interval == 5.0

    def test_register_agent(self) -> None:
        monitor = AgentMonitor()
        monitor.register_agent("agent-001")
        status = monitor._agents["agent-001"]
        assert status.agent_id == "agent-001"
        assert status.state == "unknown"

    def test_register_agent_duplicate(self) -> None:
        monitor = AgentMonitor()
        monitor.register_agent("agent-001")
        monitor.register_agent("agent-001")  # Should not raise
        assert len(monitor._agents) == 1

    def test_register_agent_max_reached(self) -> None:
        config = MonitorConfig(max_agents=2)
        monitor = AgentMonitor(config)
        monitor.register_agent("a1")
        monitor.register_agent("a2")
        with pytest.raises(MonitorError, match="maximum of 2"):
            monitor.register_agent("a3")

    @pytest.mark.asyncio
    async def test_poll_agent_unregistered_raises(self) -> None:
        monitor = AgentMonitor()
        with pytest.raises(MonitorError, match="not registered"):
            await monitor.poll_agent("unknown")

    @pytest.mark.asyncio
    async def test_poll_agent_updates_heartbeat(self) -> None:
        monitor = AgentMonitor()
        monitor.register_agent("agent-001")
        status_before = monitor._agents["agent-001"]
        await monitor.poll_agent("agent-001")
        status_after = monitor._agents["agent-001"]
        assert status_after.last_heartbeat >= status_before.last_heartbeat

    @pytest.mark.asyncio
    async def test_poll_all_empty(self) -> None:
        monitor = AgentMonitor()
        results = await monitor.poll_all()
        assert results == ()

    @pytest.mark.asyncio
    async def test_poll_all_returns_all(self) -> None:
        monitor = AgentMonitor()
        monitor.register_agent("a1")
        monitor.register_agent("a2")
        results = await monitor.poll_all()
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_get_resource_usage_registered(self) -> None:
        monitor = AgentMonitor()
        monitor.register_agent("agent-001")
        usage = await monitor.get_resource_usage("agent-001")
        assert usage.agent_id == "agent-001"

    @pytest.mark.asyncio
    async def test_get_resource_usage_unregistered_raises(self) -> None:
        monitor = AgentMonitor()
        with pytest.raises(MonitorError, match="not registered"):
            await monitor.get_resource_usage("unknown")

    def test_record_resource_usage(self) -> None:
        monitor = AgentMonitor()
        usage = ResourceUsage("a1", 100, 50.0, 0.01)
        monitor.record_resource_usage("a1", usage)
        assert len(monitor._resources["a1"]) == 1

    def test_subscribe_alerts(self) -> None:
        monitor = AgentMonitor()
        alerts: list[AgentStatus] = []

        def callback(status: AgentStatus) -> None:
            alerts.append(status)

        monitor.subscribe_alerts(callback)
        monitor.update_status(AgentStatus("a1", "busy", 95.0, 512.0, 2, time.time()))
        assert len(alerts) == 1
        assert alerts[0].agent_id == "a1"

    def test_subscribe_alerts_below_threshold(self) -> None:
        monitor = AgentMonitor()
        alerts: list[AgentStatus] = []

        def callback(status: AgentStatus) -> None:
            alerts.append(status)

        monitor.subscribe_alerts(callback)
        monitor.update_status(AgentStatus("a1", "idle", 30.0, 256.0, 1, time.time()))
        assert len(alerts) == 0

    def test_update_status(self) -> None:
        monitor = AgentMonitor()
        now = time.time()
        monitor.update_status(AgentStatus("a1", "busy", 50.0, 512.0, 2, now))
        assert monitor._agents["a1"].state == "busy"
        assert monitor._agents["a1"].cpu_pct == 50.0

    def test_multiple_subscribers(self) -> None:
        monitor = AgentMonitor()
        alerts_1: list[AgentStatus] = []
        alerts_2: list[AgentStatus] = []

        monitor.subscribe_alerts(lambda s: alerts_1.append(s))
        monitor.subscribe_alerts(lambda s: alerts_2.append(s))

        monitor.update_status(AgentStatus("a1", "busy", 95.0, 512.0, 2, time.time()))
        assert len(alerts_1) == 1
        assert len(alerts_2) == 1
