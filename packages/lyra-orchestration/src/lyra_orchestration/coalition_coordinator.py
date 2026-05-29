"""Coalition-aware agent coordinator — extends AgentCoordinator with emergent coalition formation.

Integration between lyra-orchestration and the Superorganism Plan (lyra-emergent-coord).
Allows agents to self-organize into task-driven coalitions via bidding.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Bid:
    agent_id: str
    capability_score: float
    current_load: float
    total_score: float = 0.0


@dataclass
class Coalition:
    id: str
    task_id: str
    leader_id: str
    member_ids: list[str]
    task_type: str
    status: str = "forming"  # forming, active, dissolving


class BidBasedScheduler:
    """Schedules tasks by collecting bids from available agents."""

    def __init__(self):
        self.agent_capabilities: dict[str, list[str]] = {}
        self.agent_load: dict[str, float] = {}

    def register_agent(self, agent_id: str, capabilities: list[str]) -> None:
        self.agent_capabilities[agent_id] = capabilities
        self.agent_load[agent_id] = 0.0

    def collect_bids(self, required_capabilities: list[str]) -> list[Bid]:
        bids = []
        for agent_id, capabilities in self.agent_capabilities.items():
            overlap = len(set(capabilities) & set(required_capabilities))
            if overlap > 0:
                bid = Bid(
                    agent_id=agent_id,
                    capability_score=overlap / max(len(required_capabilities), 1),
                    current_load=self.agent_load.get(agent_id, 0.0),
                )
                bid.total_score = bid.capability_score * 0.7 + (1.0 - bid.current_load) * 0.3
                bids.append(bid)
        return sorted(bids, key=lambda b: b.total_score, reverse=True)

    def select_agents(self, bids: list[Bid], count: int = 3) -> list[str]:
        return [b.agent_id for b in bids[:count]]


class CoalitionAwareCoordinator:
    """Coordinates agents via emergent coalitions. Integrates with EventBus."""

    def __init__(self, scheduler: BidBasedScheduler | None = None):
        self.scheduler = scheduler or BidBasedScheduler()
        self.coalitions: dict[str, Coalition] = {}
        self._coalition_counter = 0

    async def form_coalition(
        self, task_id: str, task_type: str, required_capabilities: list[str]
    ) -> Coalition:
        bids = self.scheduler.collect_bids(required_capabilities)
        selected = self.scheduler.select_agents(bids)
        if not selected:
            raise RuntimeError(f"No agents available for task {task_id}")

        self._coalition_counter += 1
        coalition = Coalition(
            id=f"COAL-{self._coalition_counter:04d}",
            task_id=task_id,
            leader_id=selected[0],
            member_ids=selected,
            task_type=task_type,
            status="forming",
        )
        self.coalitions[coalition.id] = coalition
        coalition.status = "active"
        logger.info(f"Coalition {coalition.id} formed for {task_type} with {len(selected)} agents")
        return coalition

    async def dissolve_coalition(self, coalition_id: str) -> None:
        if coalition_id in self.coalitions:
            self.coalitions[coalition_id].status = "dissolving"
            del self.coalitions[coalition_id]

    def get_coalition(self, coalition_id: str) -> Coalition | None:
        return self.coalitions.get(coalition_id)

    @property
    def active_coalitions(self) -> list[Coalition]:
        return [c for c in self.coalitions.values() if c.status == "active"]
