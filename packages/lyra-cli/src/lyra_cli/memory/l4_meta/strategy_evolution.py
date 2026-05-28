"""Strategy evolution — automated refinement of agent strategies over time.

Implements a lightweight evolutionary loop that mutates, scores, and
selects strategies based on observed outcomes across sessions.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from enum import StrEnum


class StrategyStatus(StrEnum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    EXPERIMENTAL = "experimental"
    ARCHIVED = "archived"


@dataclass(frozen=True)
class Strategy:
    strategy_id: str
    name: str
    description: str
    status: StrategyStatus
    success_rate: float
    total_uses: int
    created_at: float
    last_used: float | None
    parent_id: str | None


class StrategyEvolution:
    """Automated refinement of agent strategies through usage feedback.

    Tracks strategy performance, promotes successful variants, and
    deprecates underperforming strategies. Supports mutation-based
    exploration of strategy variants.
    """

    def __init__(self) -> None:
        self._strategies: dict[str, Strategy] = {}
        self._generation: int = 0

    def register(self, name: str, description: str) -> Strategy:
        sid = hashlib.sha256(f"{name}|{time.time()}".encode()).hexdigest()[:10]
        strategy = Strategy(
            strategy_id=sid,
            name=name,
            description=description,
            status=StrategyStatus.EXPERIMENTAL,
            success_rate=0.5,
            total_uses=0,
            created_at=time.time(),
            last_used=None,
            parent_id=None,
        )
        self._strategies[sid] = strategy
        self._generation += 1
        return strategy

    def record_outcome(self, strategy_id: str, success: bool) -> Strategy | None:
        current = self._strategies.get(strategy_id)
        if current is None:
            return None

        new_rate = (
            (current.success_rate * current.total_uses + (1.0 if success else 0.0))
            / (current.total_uses + 1)
        )

        new_status = current.status
        if current.total_uses >= 10:
            if new_rate >= 0.8:
                new_status = StrategyStatus.ACTIVE
            elif new_rate < 0.3:
                new_status = StrategyStatus.DEPRECATED

        updated = Strategy(
            strategy_id=current.strategy_id,
            name=current.name,
            description=current.description,
            status=new_status,
            success_rate=round(new_rate, 4),
            total_uses=current.total_uses + 1,
            created_at=current.created_at,
            last_used=time.time(),
            parent_id=current.parent_id,
        )
        self._strategies[strategy_id] = updated
        return updated

    def mutate(self, strategy_id: str, variation_suffix: str) -> Strategy | None:
        parent = self._strategies.get(strategy_id)
        if parent is None:
            return None
        return self.register(
            name=f"{parent.name}::{variation_suffix}",
            description=f"[Mutation of {parent.strategy_id}] {parent.description}",
        )

    def get_active(self) -> list[Strategy]:
        return [s for s in self._strategies.values() if s.status == StrategyStatus.ACTIVE]

    def get_experimental(self) -> list[Strategy]:
        return [s for s in self._strategies.values() if s.status == StrategyStatus.EXPERIMENTAL]

    def stats(self) -> dict:
        active = self.get_active()
        return {
            "total_strategies": len(self._strategies),
            "active": len(active),
            "generation": self._generation,
            "avg_success_rate": (
                sum(s.success_rate for s in active) / max(len(active), 1)
                if active else 0.0
            ),
        }
