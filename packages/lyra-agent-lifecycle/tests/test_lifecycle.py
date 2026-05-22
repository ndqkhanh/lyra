"""Tests for Agent Lifecycle package."""

import pytest
from lyra_agent_lifecycle import LifecycleManager, ContributionTracker, AgentSpec


class TestContributionTracker:
    def test_record_and_average(self):
        t = ContributionTracker()
        t.record_contribution("agent_1", 0.8)
        t.record_contribution("agent_1", 0.9)
        assert t.average_contribution("agent_1") > 0

    def test_underperforming(self):
        t = ContributionTracker()
        for _ in range(5):
            t.record_contribution("bad_agent", 0.05)
        assert t.is_underperforming("bad_agent", threshold=0.1)


class TestLifecycleManager:
    def test_spawn_and_retire(self):
        m = LifecycleManager()
        aid = m.spawn_agent(AgentSpec("researcher", ["search", "analyze"]))
        assert aid in m.active_agents
        assert m.retire_agent(aid) == True
        assert aid not in m.active_agents

    def test_evolve_agent(self):
        m = LifecycleManager()
        aid = m.spawn_agent(AgentSpec("coder", ["python"]))
        m.evolve_agent(aid, ["python", "rust", "go"])
        assert len(m.active_agents[aid].capabilities) == 3

    def test_stats(self):
        m = LifecycleManager()
        m.spawn_agent(AgentSpec("a1", ["c1"]))
        m.spawn_agent(AgentSpec("a2", ["c2"]))
        s = m.stats
        assert s["active"] == 2
        assert s["total_spawned"] == 2
