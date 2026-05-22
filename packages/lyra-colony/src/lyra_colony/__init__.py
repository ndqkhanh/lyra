"""Colony — Self-organizing agent colony runtime with emergent coordination."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from lyra_emergent_coord import Coalition, EmergentCoordinator
from lyra_gossip_memory import GossipProtocol
from lyra_agent_lifecycle import LifecycleManager

logger = logging.getLogger(__name__)


@dataclass
class ColonyConfig:
    max_agents: int = 20
    min_agents: int = 3
    task_timeout: float = 300.0
    gossip_interval: float = 30.0


class AgentColony:
    """Self-organizing agent colony runtime."""

    def __init__(self, config: Optional[ColonyConfig] = None):
        self.config = config or ColonyConfig()
        self.coordinator = EmergentCoordinator()
        self.gossip = GossipProtocol()
        self.lifecycle = LifecycleManager()
        self.active_coalitions: dict[str, Coalition] = {}
        self.metrics: dict[str, Any] = {}

    async def process_task(self, task_spec: dict[str, Any]) -> dict[str, Any]:
        coalition = await self.coordinator.form_coalition(task_spec)
        self.active_coalitions[coalition.id] = coalition

        leader = coalition.leader_id
        results = {}
        for member in coalition.member_ids:
            results[member] = {"status": "assigned"}

        results["coordinator"] = leader
        results["coalition_id"] = coalition.id
        return results

    async def gossip_cycle(self):
        while True:
            for coalition in self.active_coalitions.values():
                for member_id in coalition.member_ids:
                    summary = self.gossip.share(member_id, {"task_type": "general", "success": True})
            await asyncio.sleep(self.config.gossip_interval)

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "active_coalitions": len(self.active_coalitions),
            "total_agents": len(self.lifecycle.active_agents),
            "gossip_messages": self.gossip.message_count,
        }
