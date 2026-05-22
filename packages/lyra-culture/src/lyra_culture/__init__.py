"""Agent Culture — shared norms, values, and practices across agent communities.

As agent populations grow in lyra-ecology, culture emerges naturally.
This layer observes, measures, and guides that process.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

__all__ = [
    "CulturalNorm",
    "AgentCulture",
]


@dataclass
class CulturalNorm:
    name: str
    description: str
    adherence: float = 0.5
    emergence_generation: int = 0
    last_enforced: float = 0.0


class AgentCulture:
    """Tracks shared norms, values, and practices across agent collectives."""

    def __init__(self):
        self.norms: dict[str, CulturalNorm] = {}
        self._violations: list[dict[str, Any]] = []
        self._enforcements: list[dict[str, Any]] = []
        self._generation = 0

    def establish_norm(self, name: str, description: str) -> CulturalNorm:
        norm = CulturalNorm(
            name=name,
            description=description,
            emergence_generation=self._generation,
        )
        self.norms[name] = norm
        logger.info(f"Norm established: {name}")
        return norm

    def detect_violation(self, agent_id: str, norm_name: str, behavior: str) -> bool:
        norm = self.norms.get(norm_name)
        if not norm:
            return False
        self._violations.append({
            "agent_id": agent_id,
            "norm": norm_name,
            "behavior": behavior[:100],
            "time": time.time(),
            "generation": self._generation,
        })
        return True

    def enforce_norm(self, norm_name: str) -> bool:
        norm = self.norms.get(norm_name)
        if not norm:
            return False
        norm.adherence = min(1.0, norm.adherence + 0.05)
        norm.last_enforced = time.time()
        self._enforcements.append({
            "norm": norm_name,
            "time": time.time(),
            "generation": self._generation,
        })
        return True

    def evolve_culture(self, feedback: list[dict[str, Any]]) -> list[str]:
        self._generation += 1
        evolved = []
        for norm in list(self.norms.values()):
            if norm.adherence < 0.2:
                del self.norms[norm.name]
                evolved.append(f"norm '{norm.name}' dissolved (adherence too low)")
        # Create new norms from feedback patterns
        for fb in feedback[-5:]:
            if "pattern" in fb and fb["pattern"] not in self.norms:
                self.establish_norm(fb["pattern"], f"Auto-discovered: {fb.get('description', fb['pattern'])}")
                evolved.append(f"norm '{fb['pattern']}' emerged from feedback")
        return evolved

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "active_norms": len(self.norms),
            "total_violations": len(self._violations),
            "total_enforcements": len(self._enforcements),
            "generation": self._generation,
            "norms": {n: round(v.adherence, 2) for n, v in self.norms.items()},
        }
