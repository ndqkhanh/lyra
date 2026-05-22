"""Tests for Emergent Coordinator package."""

import pytest
from lyra_emergent_coord import EmergentCoordinator, TaskAdvertisement, Bid, Coalition


class TestEmergentCoordinator:
    @pytest.mark.asyncio
    async def test_register_and_form(self):
        c = EmergentCoordinator()
        c.register_agent("agent_1", ["search", "analyze"])
        c.register_agent("agent_2", ["code", "debug"])
        coalition = await c.form_coalition({"type": "research", "complexity": 0.5, "capabilities": ["search", "analyze"]})
        assert isinstance(coalition, Coalition)
        assert len(coalition.member_ids) > 0
        assert coalition.leader_id is not None
