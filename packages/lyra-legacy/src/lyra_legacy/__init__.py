"""Legacy & Reputation — long-term identity, impact tracking, memory preservation.

Tracks what an agent has accomplished, how it's perceived by others,
and preserves its knowledge when retired.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

__all__ = [
    "ReputationScore",
    "AgentLegacy",
]


@dataclass
class ReputationScore:
    trustworthiness: float = 0.5
    competence: float = 0.5
    reliability: float = 0.5
    helpfulness: float = 0.5


class AgentLegacy:
    """Tracks long-term identity, impact, and knowledge preservation."""

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.reputation = ReputationScore()
        self.achievements: list[dict[str, Any]] = []
        self.contributions: list[dict[str, Any]] = []
        self.knowledge_base: dict[str, str] = {}
        self._retired = False

    def record_achievement(self, description: str, impact: float = 0.5) -> None:
        self.achievements.append({
            "description": description,
            "impact": impact,
            "timestamp": time.time(),
        })

    def record_contribution(self, target: str, value: str) -> None:
        self.contributions.append({
            "target": target,
            "value": value,
            "timestamp": time.time(),
        })

    def update_reputation(self, dimension: str, delta: float) -> None:
        if dimension == "trustworthiness":
            self.reputation.trustworthiness = max(0, min(1, self.reputation.trustworthiness + delta))
        elif dimension == "competence":
            self.reputation.competence = max(0, min(1, self.reputation.competence + delta))
        elif dimension == "reliability":
            self.reputation.reliability = max(0, min(1, self.reputation.reliability + delta))
        elif dimension == "helpfulness":
            self.reputation.helpfulness = max(0, min(1, self.reputation.helpfulness + delta))

    def preserve_knowledge(self, key: str, value: str) -> None:
        self.knowledge_base[key] = value

    def retire(self) -> dict[str, Any]:
        self._retired = True
        archive = {
            "agent_id": self.agent_id,
            "reputation": {
                "trustworthiness": self.reputation.trustworthiness,
                "competence": self.reputation.competence,
                "reliability": self.reputation.reliability,
                "helpfulness": self.reputation.helpfulness,
            },
            "achievements": len(self.achievements),
            "contributions": len(self.contributions),
            "knowledge_entries": len(self.knowledge_base),
        }
        logger.info(f"Agent {self.agent_id} retired with {len(self.achievements)} achievements")
        return archive

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "retired": self._retired,
            "achievements": len(self.achievements),
            "contributions": len(self.contributions),
            "knowledge": len(self.knowledge_base),
            "reputation": {
                "trustworthiness": self.reputation.trustworthiness,
                "competence": self.reputation.competence,
            },
        }
