"""Attribute costs to specific agents and operations."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class CostEntry:
    """A single cost attribution entry."""

    entry_id: str
    agent_id: str
    operation: str
    model: str
    token_cost: float
    compute_cost: float
    total_cost: float
    timestamp: float


@dataclass(frozen=True)
class CostBreakdown:
    """Aggregated cost breakdown."""

    total_cost: float = 0.0
    by_agent: Tuple[Tuple[str, float], ...] = ()
    by_model: Tuple[Tuple[str, float], ...] = ()
    by_operation: Tuple[Tuple[str, float], ...] = ()
    period_hours: float = 24.0


@dataclass(frozen=True)
class CostConfig:
    """Configuration for cost calculation."""

    prompt_cost_per_1k: float = 0.003
    completion_cost_per_1k: float = 0.015
    compute_cost_per_second: float = 0.0001


class CostAttributor:
    """Tracks and attributes costs to agents, models, and operations."""

    def __init__(
        self,
        config: CostConfig | None = None,
    ) -> None:
        self._config = config or CostConfig()
        self._entries: List[CostEntry] = []

    async def attribute_cost(
        self,
        agent_id: str,
        operation: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        duration_s: float,
    ) -> CostEntry:
        """Calculate and record a cost entry."""
        token_cost = (
            (prompt_tokens / 1000) * self._config.prompt_cost_per_1k
            + (completion_tokens / 1000) * self._config.completion_cost_per_1k
        )
        compute_cost = duration_s * self._config.compute_cost_per_second
        total_cost = token_cost + compute_cost

        entry = CostEntry(
            entry_id=uuid.uuid4().hex[:12],
            agent_id=agent_id,
            operation=operation,
            model=model,
            token_cost=round(token_cost, 6),
            compute_cost=round(compute_cost, 6),
            total_cost=round(total_cost, 6),
            timestamp=time.time(),
        )
        self._entries.append(entry)
        return entry

    async def get_cost_breakdown(
        self,
        period_hours: float = 24.0,
    ) -> CostBreakdown:
        """Get aggregated cost breakdown for a time period."""
        now = time.time()
        cutoff = now - (period_hours * 3600)

        recent = [e for e in self._entries if e.timestamp >= cutoff]

        total_cost = sum(e.total_cost for e in recent)

        # By agent
        agent_cost: Dict[str, float] = {}
        for e in recent:
            agent_cost[e.agent_id] = agent_cost.get(e.agent_id, 0.0) + e.total_cost

        # By model
        model_cost: Dict[str, float] = {}
        for e in recent:
            model_cost[e.model] = model_cost.get(e.model, 0.0) + e.total_cost

        # By operation
        op_cost: Dict[str, float] = {}
        for e in recent:
            op_cost[e.operation] = op_cost.get(e.operation, 0.0) + e.total_cost

        return CostBreakdown(
            total_cost=round(total_cost, 6),
            by_agent=tuple(sorted(agent_cost.items())),
            by_model=tuple(sorted(model_cost.items())),
            by_operation=tuple(sorted(op_cost.items())),
            period_hours=period_hours,
        )

    async def get_agent_cost(self, agent_id: str) -> CostBreakdown:
        """Get cost breakdown specifically for a single agent."""
        agent_entries = [e for e in self._entries if e.agent_id == agent_id]
        if not agent_entries:
            return CostBreakdown()

        total_cost = sum(e.total_cost for e in agent_entries)

        model_cost: Dict[str, float] = {}
        op_cost: Dict[str, float] = {}
        for e in agent_entries:
            model_cost[e.model] = model_cost.get(e.model, 0.0) + e.total_cost
            op_cost[e.operation] = op_cost.get(e.operation, 0.0) + e.total_cost

        return CostBreakdown(
            total_cost=round(total_cost, 6),
            by_agent=((agent_id, round(total_cost, 6)),),
            by_model=tuple(sorted(model_cost.items())),
            by_operation=tuple(sorted(op_cost.items())),
            period_hours=0.0,
        )
