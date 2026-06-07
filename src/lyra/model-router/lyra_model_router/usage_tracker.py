"""Track model usage, costs, latency, and quality metrics."""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass


@dataclass(frozen=True)
class UsageRecord:
    """A single usage record for a routed task.

    Attributes:
        model_id: The model used.
        task_type: The task category.
        tokens_in: Number of input tokens.
        tokens_out: Number of output tokens.
        latency_ms: Response latency in milliseconds.
        cost: Cost in USD.
        timestamp: Unix timestamp of the record.
    """
    model_id: str
    task_type: str
    tokens_in: int
    tokens_out: int
    latency_ms: float
    cost: float
    timestamp: float


@dataclass(frozen=True)
class UsageStats:
    """Aggregated usage statistics for a model or task type."""
    total_calls: int
    total_tokens_in: int
    total_tokens_out: int
    total_cost: float
    total_latency_ms: float
    avg_latency_ms: float
    avg_cost_per_call: float


class UsageTracker:
    """Tracks model usage and provides aggregated statistics.

    Supports per-model and per-task-type aggregation, as well as
    session cost estimation.
    """

    def __init__(self) -> None:
        self._records: list[UsageRecord] = []
        self._session_start: float = time.time()

    async def record_usage(self, record: UsageRecord) -> None:
        """Record a usage record."""
        self._records.append(record)

    async def get_stats_per_model(self) -> dict[str, UsageStats]:
        """Get aggregated usage statistics per model."""
        grouped: dict[str, list[UsageRecord]] = defaultdict(list)
        for r in self._records:
            grouped[r.model_id].append(r)
        return {
            mid: self._aggregate(recs)
            for mid, recs in grouped.items()
        }

    async def get_stats_per_task(self) -> dict[str, UsageStats]:
        """Get aggregated usage statistics per task type."""
        grouped: dict[str, list[UsageRecord]] = defaultdict(list)
        for r in self._records:
            grouped[r.task_type].append(r)
        return {
            tt: self._aggregate(recs)
            for tt, recs in grouped.items()
        }

    async def estimate_session_cost(self) -> float:
        """Estimate the total cost for the current session."""
        return sum(r.cost for r in self._records)

    @property
    def total_calls(self) -> int:
        """Total number of recorded calls."""
        return len(self._records)

    @staticmethod
    def _aggregate(records: list[UsageRecord]) -> UsageStats:
        """Aggregate a list of usage records into summary stats."""
        if not records:
            return UsageStats(
                total_calls=0, total_tokens_in=0, total_tokens_out=0,
                total_cost=0.0, total_latency_ms=0.0,
                avg_latency_ms=0.0, avg_cost_per_call=0.0,
            )
        n = len(records)
        total_tokens_in = sum(r.tokens_in for r in records)
        total_tokens_out = sum(r.tokens_out for r in records)
        total_cost = sum(r.cost for r in records)
        total_latency = sum(r.latency_ms for r in records)
        return UsageStats(
            total_calls=n,
            total_tokens_in=total_tokens_in,
            total_tokens_out=total_tokens_out,
            total_cost=total_cost,
            total_latency_ms=total_latency,
            avg_latency_ms=round(total_latency / n, 2),
            avg_cost_per_call=round(total_cost / n, 6),
        )
