"""Tests for FleetManager."""

from __future__ import annotations

import pytest

from lyra_cli.swarm.fleet_manager import (
    FleetConfig,
    FleetManager,
    AgentInstance,
    AgentStatus,
    ResourceProfile,
)


@pytest.mark.asyncio
async def test_spawn_agent_creates_instance() -> None:
    """Spawning an agent should create it with RUNNING status."""
    fm = FleetManager()
    agent = await fm.spawn_agent(name="test_agent", agent_type="worker")
    assert agent.name == "test_agent"
    assert agent.agent_type == "worker"
    assert agent.status == AgentStatus.RUNNING


@pytest.mark.asyncio
async def test_terminate_agent_removes_from_fleet() -> None:
    """Terminating an agent should remove it from the fleet."""
    fm = FleetManager()
    agent = await fm.spawn_agent(name="to_kill")
    assert agent.agent_id in fm.agents

    result = await fm.terminate_agent(agent.agent_id)
    assert result is True
    assert agent.agent_id not in fm.agents


@pytest.mark.asyncio
async def test_assign_and_complete_task() -> None:
    """Assigning a task should mark agent busy, completing should update stats."""
    fm = FleetManager()
    agent = await fm.spawn_agent(name="worker")

    assigned = await fm.assign_task_to_agent(agent.agent_id)
    assert assigned is True

    busy_agent = await fm.get_agent(agent.agent_id)
    assert busy_agent is not None
    assert busy_agent.status == AgentStatus.BUSY

    await fm.complete_task_for_agent(agent.agent_id, success=True)
    updated = await fm.get_agent(agent.agent_id)
    assert updated is not None
    assert updated.tasks_completed == 1


@pytest.mark.asyncio
async def test_record_heartbeat_resurrects_failed_agent() -> None:
    """A heartbeat from a failed agent should reset it to RUNNING."""
    fm = FleetManager()
    agent = await fm.spawn_agent(name="resilient")
    await fm.terminate_agent(agent.agent_id)
    agent.status = AgentStatus.FAILED
    fm.agents[agent.agent_id] = agent

    result = await fm.record_heartbeat(agent.agent_id)
    assert result is True
    revived = await fm.get_agent(agent.agent_id)
    assert revived is not None
    assert revived.status == AgentStatus.RUNNING


@pytest.mark.asyncio
async def test_get_idle_agents() -> None:
    """get_idle_agents should return only agents with low load."""
    fm = FleetManager()
    agent = await fm.spawn_agent(name="idle_agent")
    idle = await fm.get_idle_agents()
    assert any(a.agent_id == agent.agent_id for a in idle)


@pytest.mark.asyncio
async def test_get_fleet_summary() -> None:
    """get_fleet_summary should return a comprehensive fleet snapshot."""
    fm = FleetManager()
    await fm.spawn_agent(name="flash")
    await fm.spawn_agent(name="json")

    summary = fm.get_fleet_summary()
    assert summary["total_agents"] == 2
    assert "status_breakdown" in summary
    assert "average_load" in summary
