"""Curiosity & Novelty Seeking — intrinsic motivation, exploration drive, information gain.

Agents that only respond to explicit tasks will never achieve AGI.
Curiosity drives agents to explore novel states, seek information, and grow.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

__all__ = ["CuriosityDrive", "NoveltyEngine"]


@dataclass
class CuriosityDrive:
    exploration_rate: float = 0.3
    information_gain: float = 0.0
    novelty_seeking: float = 0.5


class NoveltyEngine:
    def __init__(self):
        self._explored: set[str] = set()
        self._curiosity = CuriosityDrive()
        self._explorations = 0

    def assess_novelty(self, opportunity: str) -> float:
        key = opportunity.lower()[:30]
        if key in self._explored:
            return 0.0
        return self._curiosity.novelty_seeking * (1.0 - len(self._explored) / 100.0)

    def explore(self, opportunity: str) -> dict[str, Any]:
        self._explorations += 1
        self._explored.add(opportunity.lower()[:30])
        info_gain = random.uniform(0.1, 0.5) * self._curiosity.novelty_seeking
        self._curiosity.information_gain += info_gain
        self._curiosity.exploration_rate = max(0.1, self._curiosity.exploration_rate * 0.99)
        return {"novelty_score": info_gain, "total_explored": len(self._explored), "explorations": self._explorations}

    @property
    def stats(self) -> dict[str, Any]:
        return {"explorations": self._explorations, "unique_discoveries": len(self._explored), "curiosity": self._curiosity.novelty_seeking}
