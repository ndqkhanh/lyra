"""Agent Lifecycle — Dynamic agent spawn/retire/evolve lifecycle management."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

__all__ = [
    "AgentSpec",
    "ContributionTracker",
    "LifecycleManager",
]




@dataclass
class AgentSpec:
    agent_type: str
    capabilities: list[str]
    min_contribution: float = 0.1
    max_idle_seconds: float = 3600.0


class ContributionTracker:
    """Tracks agent contribution over time."""

    def __init__(self):
        self.contributions: dict[str, list[float]] = {}

    def record_contribution(self, agent_id: str, score: float) -> None:
        if agent_id not in self.contributions:
            self.contributions[agent_id] = []
        self.contributions[agent_id].append(score)

    def average_contribution(self, agent_id: str) -> float:
        scores = self.contributions.get(agent_id, [])
        if not scores:
            return 0.0
        return sum(scores[-20:]) / min(len(scores[-20:]), 20)

    def is_underperforming(self, agent_id: str, threshold: float = 0.1) -> bool:
        return self.average_contribution(agent_id) < threshold


class LifecycleManager:
    """Manages spawning, retiring, and evolving agents."""

    def __init__(self):
        self.active_agents: dict[str, AgentSpec] = {}
        self.retired_agents: dict[str, AgentSpec] = {}
        self.tracker = ContributionTracker()
        self.total_spawned: int = 0

    def spawn_agent(self, spec: AgentSpec) -> str:
        agent_id = f"{spec.agent_type}_{self.total_spawned}"
        self.active_agents[agent_id] = spec
        self.total_spawned += 1
        return agent_id

    def retire_agent(self, agent_id: str) -> bool:
        if agent_id not in self.active_agents:
            return False
        self.retired_agents[agent_id] = self.active_agents.pop(agent_id)
        return True

    def evolve_agent(self, agent_id: str, new_capabilities: list[str]) -> bool:
        if agent_id not in self.active_agents:
            return False
        self.active_agents[agent_id].capabilities = new_capabilities
        return True

    def cleanup_underperformers(self, threshold: float = 0.1) -> list[str]:
        retired = []
        for agent_id in list(self.active_agents.keys()):
            if self.tracker.is_underperforming(agent_id, threshold):
                self.retire_agent(agent_id)
                retired.append(agent_id)
        return retired

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "active": len(self.active_agents),
            "retired": len(self.retired_agents),
            "total_spawned": self.total_spawned,
        }
