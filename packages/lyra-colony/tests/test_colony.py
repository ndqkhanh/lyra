"""Tests for Colony package."""

import pytest
from lyra_colony import AgentColony, ColonyConfig


class TestAgentColony:
    @pytest.mark.asyncio
    async def test_process_task(self):
        colony = AgentColony()
        result = await colony.process_task({"type": "research", "complexity": 0.5, "capabilities": ["search", "analyze"]})
        assert "coalition_id" in result
        assert result["coalition_id"] is not None

    def test_stats(self):
        colony = AgentColony()
        s = colony.stats
        assert "active_coalitions" in s
        assert "total_agents" in s
