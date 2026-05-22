"""Emergent Coordinator — Task-driven coalition formation with bidding and lead election."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

__all__ = [
    "TaskAdvertisement",
    "Bid",
    "Coalition",
    "EmergentCoordinator",
]




@dataclass
class TaskAdvertisement:
    task_id: str
    task_type: str
    complexity: float
    required_capabilities: list[str]


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
    formation_time: float


class EmergentCoordinator:
    """Task-driven coalition formation with emergent lead election."""

    def __init__(self):
        self.agent_capabilities: dict[str, list[str]] = {}
        self.agent_load: dict[str, float] = {}
        self.coalitions: list[Coalition] = []

    def register_agent(self, agent_id: str, capabilities: list[str]) -> None:
        self.agent_capabilities[agent_id] = capabilities
        self.agent_load[agent_id] = 0.0

    async def form_coalition(self, task_spec: dict[str, Any]) -> Coalition:
        advertisement = TaskAdvertisement(
            task_id=str(uuid.uuid4())[:8],
            task_type=task_spec.get("type", "general"),
            complexity=task_spec.get("complexity", 0.5),
            required_capabilities=task_spec.get("capabilities", []),
        )

        bids = await self._collect_bids(advertisement)
        selected = self._select_members(bids, min(3, len(bids)))
        leader = self._elect_leader(selected)

        coalition = Coalition(
            id=str(uuid.uuid4())[:8],
            task_id=advertisement.task_id,
            leader_id=leader,
            member_ids=selected,
            formation_time=__import__("time").time(),
        )
        self.coalitions.append(coalition)
        return coalition

    async def _collect_bids(self, advertisement: TaskAdvertisement) -> list[Bid]:
        bids = []
        for agent_id, capabilities in self.agent_capabilities.items():
            overlap = len(set(capabilities) & set(advertisement.required_capabilities))
            if overlap > 0:
                bid = Bid(
                    agent_id=agent_id,
                    capability_score=overlap / max(len(advertisement.required_capabilities), 1),
                    current_load=self.agent_load.get(agent_id, 0.0),
                )
                bid.total_score = bid.capability_score * 0.7 + (1.0 - bid.current_load) * 0.3
                bids.append(bid)
        return sorted(bids, key=lambda b: b.total_score, reverse=True)

    def _select_members(self, bids: list[Bid], count: int) -> list[str]:
        return [b.agent_id for b in bids[:count]]

    def _elect_leader(self, member_ids: list[str]) -> str:
        if not member_ids:
            return "unknown"
        return member_ids[0]
