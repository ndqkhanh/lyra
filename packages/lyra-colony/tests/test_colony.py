"""Tests for Colony package."""

import pytest
from lyra_colony import AgentColony


class TestAgentColony:
    def test_process_task_sync(self):
        colony = AgentColony()
        import asyncio
        result = asyncio.run(colony.process_task({"type": "research", "complexity": 0.5, "capabilities": ["search", "analyze"]}))
        assert "coalition_id" in result

    def test_stats(self):
        colony = AgentColony()
        s = colony.stats
        assert "active_coalitions" in s
