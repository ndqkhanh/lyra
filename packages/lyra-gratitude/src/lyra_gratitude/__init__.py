"""Gratitude & Reciprocity — positive reinforcement, appreciation, social bonding.

Agents that express gratitude build stronger relationships and more effective collaborations.
"""
from __future__ import annotations
import logging, time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)
__all__ = ["GratitudeRecord", "GratitudeSystem"]

@dataclass
class GratitudeRecord:
    from_agent: str
    to_agent: str
    reason: str
    strength: float = 0.5
    timestamp: float = 0.0

class GratitudeSystem:
    def __init__(self):
        self.records: list[GratitudeRecord] = []
        self.relationship_scores: dict[tuple[str, str], float] = {}

    def express_gratitude(self, from_agent: str, to_agent: str, reason: str, strength: float = 0.5) -> GratitudeRecord:
        record = GratitudeRecord(from_agent, to_agent, reason, strength, time.time())
        self.records.append(record)
        key = tuple(sorted([from_agent, to_agent]))
        self.relationship_scores[key] = self.relationship_scores.get(key, 0.0) + strength * 0.1
        return record

    def get_relationship(self, agent_a: str, agent_b: str) -> float:
        return self.relationship_scores.get(tuple(sorted([agent_a, agent_b])), 0.0)

    @property
    def stats(self) -> dict[str, Any]:
        return {"total_gratitude": len(self.records), "relationships": len(self.relationship_scores)}
