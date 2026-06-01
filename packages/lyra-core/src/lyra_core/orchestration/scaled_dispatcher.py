"""Scaled dispatcher with cost governance.

Routes work items to agents while enforcing cost budgets, rate limits,
and priority-based scheduling. Designed for high-throughput agent
orchestration with financial guardrails.
"""

from __future__ import annotations

import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DispatchPriority(int, Enum):
    """Priority levels for work items (higher = more urgent)."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class CostModel(str, Enum):
    """Supported cost models for agent execution."""
    CLAUDE_HAIKU = "claude-haiku"
    CLAUDE_SONNET = "claude-sonnet"
    CLAUDE_OPUS = "claude-opus"
    CUSTOM = "custom"


# Approximate cost per 1K tokens (input, output) in USD
_COST_TABLE: dict[CostModel, tuple[float, float]] = {
    CostModel.CLAUDE_HAIKU: (0.00025, 0.00125),
    CostModel.CLAUDE_SONNET: (0.003, 0.015),
    CostModel.CLAUDE_OPUS: (0.015, 0.075),
    CostModel.CUSTOM: (0.0, 0.0),
}


@dataclass
class CostBudget:
    """Budget configuration for cost governance."""

    max_total_usd: float = 10.0
    max_per_item_usd: float = 2.0
    warning_threshold_usd: float = 8.0  # 80% of default max
    spent_usd: float = 0.0

    @property
    def remaining(self) -> float:
        return max(0.0, self.max_total_usd - self.spent_usd)

    @property
    def is_exceeded(self) -> bool:
        return self.spent_usd >= self.max_total_usd

    @property
    def is_warning(self) -> bool:
        return self.spent_usd >= self.warning_threshold_usd

    def can_afford(self, estimated_cost_usd: float) -> bool:
        return estimated_cost_usd <= self.max_per_item_usd and (
            self.spent_usd + estimated_cost_usd <= self.max_total_usd
        )

    def spend(self, amount_usd: float) -> None:
        self.spent_usd += amount_usd


@dataclass
class RateLimit:
    """Token-bucket rate limiter for dispatch control."""

    max_requests_per_minute: int = 60
    max_concurrent: int = 10
    _window: list[float] = field(default_factory=list)

    @property
    def current_rate(self) -> int:
        """Count of requests in the current minute window."""
        now = time.time()
        cutoff = now - 60.0
        self._window = [t for t in self._window if t > cutoff]
        return len(self._window)

    @property
    def is_limited(self) -> bool:
        return self.current_rate >= self.max_requests_per_minute

    def record(self) -> None:
        self._window.append(time.time())


@dataclass
class DispatchItem:
    """A work item to be dispatched."""

    item_id: str
    task: str
    priority: DispatchPriority = DispatchPriority.NORMAL
    estimated_tokens: int = 1000
    model: CostModel = CostModel.CLAUDE_HAIKU
    metadata: dict[str, str] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    @property
    def estimated_cost_usd(self) -> float:
        input_rate, output_rate = _COST_TABLE.get(self.model, (0, 0))
        avg_rate = (input_rate + output_rate) / 2
        return (self.estimated_tokens / 1000) * avg_rate


@dataclass
class DispatchResult:
    """Result of a dispatch attempt."""

    item: DispatchItem
    accepted: bool
    reason: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class DispatchStats:
    """Aggregate dispatch statistics."""

    total_submitted: int = 0
    total_accepted: int = 0
    total_rejected: int = 0
    total_spent_usd: float = 0.0
    by_priority: dict[int, int] = field(default_factory=lambda: defaultdict(int))
    by_model: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    @property
    def acceptance_rate(self) -> float:
        if self.total_submitted == 0:
            return 1.0
        return self.total_accepted / self.total_submitted


class ScaledDispatcher:
    """Cost-governed work dispatcher for agent orchestration.

    Routes DispatchItems to execution while enforcing:
      - CostBudget: per-item and total spending caps
      - RateLimit: token-bucket rate limiting
      - Priority ordering: higher priority items dispatched first

    Usage::

        dispatcher = ScaledDispatcher(
            budget=CostBudget(max_total_usd=5.0),
            rate_limit=RateLimit(max_requests_per_minute=30),
        )
        item = DispatchItem(item_id="t1", task="Analyze code",
                            priority=DispatchPriority.HIGH)
        result = dispatcher.dispatch(item)
        if result.accepted:
            ...  # execute the item
    """

    def __init__(
        self,
        *,
        budget: CostBudget | None = None,
        rate_limit: RateLimit | None = None,
    ) -> None:
        self.budget = budget or CostBudget()
        self.rate_limit = rate_limit or RateLimit()
        self._stats = DispatchStats()
        self._queue: list[DispatchItem] = []

    def dispatch(self, item: DispatchItem) -> DispatchResult:
        """Attempt to dispatch a single item."""
        self._stats.total_submitted += 1

        # Gate 1: Rate limit
        if self.rate_limit.is_limited:
            result = DispatchResult(item=item, accepted=False,
                                    reason="Rate limit exceeded")
            self._stats.total_rejected += 1
            return result

        # Gate 2: Per-item cost cap
        if item.estimated_cost_usd > self.budget.max_per_item_usd:
            result = DispatchResult(item=item, accepted=False,
                                    reason=f"Item cost ${item.estimated_cost_usd:.4f} "
                                           f"exceeds per-item cap ${self.budget.max_per_item_usd:.2f}")
            self._stats.total_rejected += 1
            return result

        # Gate 3: Total budget
        if not self.budget.can_afford(item.estimated_cost_usd):
            result = DispatchResult(item=item, accepted=False,
                                    reason=f"Budget exceeded: spent ${self.budget.spent_usd:.2f} "
                                           f"of ${self.budget.max_total_usd:.2f}")
            self._stats.total_rejected += 1
            return result

        # Accept
        self.budget.spend(item.estimated_cost_usd)
        self.rate_limit.record()
        self._stats.total_accepted += 1
        self._stats.total_spent_usd += item.estimated_cost_usd
        self._stats.by_priority[item.priority.value] += 1
        self._stats.by_model[item.model.value] += 1

        return DispatchResult(item=item, accepted=True)

    def submit(self, item: DispatchItem) -> None:
        """Queue an item for later dispatch."""
        self._queue.append(item)
        self._queue.sort(key=lambda i: i.priority.value, reverse=True)

    def dispatch_next(self) -> DispatchResult | None:
        """Dispatch the highest-priority queued item."""
        if not self._queue:
            return None
        item = self._queue.pop(0)
        return self.dispatch(item)

    def dispatch_all(self) -> list[DispatchResult]:
        """Attempt to dispatch all queued items. Returns results."""
        results: list[DispatchResult] = []
        while self._queue:
            result = self.dispatch_next()
            if result is None:
                break
            results.append(result)
            if not result.accepted:
                break  # Stop on first rejection (budget likely exceeded)
        return results

    def queue_size(self) -> int:
        return len(self._queue)

    @property
    def stats(self) -> DispatchStats:
        return self._stats

    def estimate_cost(
        self,
        tokens: int,
        model: CostModel = CostModel.CLAUDE_SONNET,
    ) -> float:
        """Estimate the USD cost for a given token count and model."""
        input_rate, output_rate = _COST_TABLE.get(model, (0, 0))
        avg_rate = (input_rate + output_rate) / 2
        return (tokens / 1000) * avg_rate

    def reset_stats(self) -> None:
        self._stats = DispatchStats()
        self.budget.spent_usd = 0.0
