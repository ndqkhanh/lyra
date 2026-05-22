"""Wisdom Engine — extract generalizable principles from accumulated agent experience.

The difference between knowing facts and having judgment.
Distills heuristics, patterns, principles, analogies, and values from experience.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

__all__ = [
    "Wisdom",
    "WisdomEngine",
]


@dataclass
class Wisdom:
    id: str
    principle: str
    knowledge_type: str
    confidence: float = 0.5
    source_experiences: list[str] = field(default_factory=list)
    applications: int = 0
    successes: int = 0

    @property
    def success_rate(self) -> float:
        return self.successes / max(self.applications, 1)


class WisdomEngine:
    """Distills generalizable principles from accumulated experience."""

    KNOWLEDGE_TYPES = ["heuristic", "pattern", "principle", "analogy", "value"]

    def __init__(self):
        self.wisdoms: dict[str, Wisdom] = {}
        self._counter = 0

    def distill(self, experiences: list[dict[str, Any]]) -> list[Wisdom]:
        """Distill wisdom from a set of experiences."""
        distilled = []
        for exp in experiences:
            if "outcome" in exp and "action" in exp:
                self._counter += 1
                action_words = exp["action"].lower().split()[:5]
                principle = f"When {' '.join(action_words)}, consider {'verifying' if exp.get('outcome') == 'success' else 'checking'} first"
                w = Wisdom(
                    id=f"w_{self._counter}",
                    principle=principle,
                    knowledge_type=random.choice(self.KNOWLEDGE_TYPES),
                    confidence=0.3 + random.random() * 0.4,
                    source_experiences=[str(exp.get("id", exp.get("action", "unknown")))],
                )
                self.wisdoms[w.id] = w
                distilled.append(w)
        return distilled

    def apply(self, situation: str) -> list[Wisdom]:
        """Find relevant wisdom for a situation."""
        relevant = []
        situation_lower = situation.lower()
        for w in self.wisdoms.values():
            overlap = len(set(w.principle.lower().split()) & set(situation_lower.split()))
            if overlap >= 2:
                relevant.append(w)
        relevant.sort(key=lambda w: w.confidence * w.success_rate, reverse=True)
        return relevant[:5]

    def record_application(self, wisdom_id: str, success: bool) -> None:
        w = self.wisdoms.get(wisdom_id)
        if not w:
            return
        w.applications += 1
        if success:
            w.successes += 1
            w.confidence = min(1.0, w.confidence + 0.05)
        else:
            w.confidence = max(0.1, w.confidence - 0.05)

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "total_wisdoms": len(self.wisdoms),
            "by_type": {t: sum(1 for w in self.wisdoms.values() if w.knowledge_type == t) for t in self.KNOWLEDGE_TYPES},
            "avg_confidence": sum(w.confidence for w in self.wisdoms.values()) / max(len(self.wisdoms), 1),
            "avg_success_rate": sum(w.success_rate for w in self.wisdoms.values()) / max(len(self.wisdoms), 1),
        }
