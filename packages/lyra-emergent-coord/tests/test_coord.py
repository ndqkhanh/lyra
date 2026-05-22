"""Tests for Emergent Coordinator package."""

import pytest
from lyra_emergent_coord import EmergentCoordinator, Coalition


class TestEmergentCoordinator:
    def test_register_and_form_sync(self):
        c = EmergentCoordinator()
        c.register_agent("agent_1", ["search", "analyze"])
        c.register_agent("agent_2", ["code", "debug"])
        import asyncio
        coalition = asyncio.run(c.form_coalition({"type": "research", "complexity": 0.5, "capabilities": ["search", "analyze"]}))
        assert isinstance(coalition, Coalition)
