"""Typed cost-tracking primitives — CostEntry, BillingPeriod, CostReport."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class CostEntry:
    """One recorded cost event — typed + content-addressable for audit.

    >>> e = CostEntry.create(
    ...     operation="llm_call",
    ...     project="polaris",
    ...     user_id="alice",
    ...     input_tokens=1000,
    ...     output_tokens=500,
    ...     cost_usd=0.0125,
    ... )
    >>> e.cost_usd
    0.0125
    """

    entry_id: str
    timestamp: float
    operation: str  # "llm_call" | "retrieval" | "embedding" | "tool_call" | "custom"
    project: str
    user_id: str
    input_tokens: int = 0
    output_tokens: int = 0
    active_params: Optional[int] = None  # MoE-aware accounting per active_params module
    cost_usd: float = 0.0
    tags: frozenset[str] = field(default_factory=frozenset)
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.entry_id:
            raise ValueError("entry_id must be non-empty")
        if not self.operation:
            raise ValueError("operation must be non-empty")
        if not self.project:
            raise ValueError("project must be non-empty")
        if self.input_tokens < 0 or self.output_tokens < 0:
            raise ValueError("token counts must be >= 0")
        if self.cost_usd < 0:
            raise ValueError(f"cost_usd must be >= 0, got {self.cost_usd}")
        if self.timestamp < 0:
            raise ValueError(f"timestamp must be >= 0, got {self.timestamp}")

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @classmethod
    def create(
        cls,
        *,
        operation: str,
        project: str,
        user_id: str = "anonymous",
        input_tokens: int = 0,
        output_tokens: int = 0,
        active_params: Optional[int] = None,
        cost_usd: float = 0.0,
        tags: tuple[str, ...] = (),
        metadata: Optional[dict] = None,
        timestamp: Optional[float] = None,
        entry_id: Optional[str] = None,
    ) -> "CostEntry":
        """Construct with auto-generated entry_id + current time."""
        return cls(
            entry_id=entry_id or str(uuid.uuid4()),
            timestamp=timestamp if timestamp is not None else time.time(),
            operation=operation,
            project=project,
            user_id=user_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            active_params=active_params,
            cost_usd=cost_usd,
            tags=frozenset(tags),
            metadata=dict(metadata or {}),
        )


@dataclass(frozen=True)
class BillingPeriod:
    """A time range for billing/aggregation queries."""

    start: float  # epoch seconds
    end: float

    def __post_init__(self) -> None:
        if self.start < 0:
            raise ValueError(f"start must be >= 0, got {self.start}")
        if self.end < self.start:
            raise ValueError(
                f"end ({self.end}) must be >= start ({self.start})"
            )

    @property
    def duration_seconds(self) -> float:
        return self.end - self.start

    def contains(self, timestamp: float) -> bool:
        return self.start <= timestamp <= self.end

    @classmethod
    def last_n_seconds(cls, n: float, *, now: Optional[float] = None) -> "BillingPeriod":
        ts = now if now is not None else time.time()
        return cls(start=ts - n, end=ts)


@dataclass(frozen=True)
class CostReport:
    """Aggregated cost view, grouped by some axis (project/user/operation)."""

    grouped_by: str  # the axis
    period: Optional[BillingPeriod]
    rows: tuple[tuple[str, dict], ...]  # ordered (group_key, totals_dict) pairs
    grand_total_usd: float
    grand_total_tokens: int

    def top_n(self, n: int = 10) -> list[tuple[str, dict]]:
        """Top-N rows by cost_usd descending."""
        ordered = sorted(self.rows, key=lambda kv: -kv[1].get("cost_usd", 0))
        return ordered[:n]

    def for_key(self, key: str) -> Optional[dict]:
        for k, v in self.rows:
            if k == key:
                return v
        return None


@dataclass(frozen=True)
class CostThresholdAlert:
    """Fired when a project / user spend exceeds a configured threshold."""

    triggered_at: float
    threshold_usd: float
    actual_usd: float
    scope: str  # e.g. "project=polaris" | "user=alice" | "global"
    period: Optional[BillingPeriod] = None
    note: str = ""

    @property
    def overage_usd(self) -> float:
        return max(0.0, self.actual_usd - self.threshold_usd)


# --- Pricing table -----------------------------------------------------


@dataclass
class PricingTable:
    """Per-operation pricing in USD per 1M tokens.

    >>> p = PricingTable(prices={
    ...     "llm_call": {"input_per_M": 3.0, "output_per_M": 15.0},
    ...     "embedding": {"input_per_M": 0.13, "output_per_M": 0.0},
    ... })
    >>> p.compute_cost(operation="llm_call", input_tokens=1_000_000, output_tokens=500_000)
    10.5
    """

    prices: dict[str, dict[str, float]] = field(default_factory=dict)
    # default_input_per_M / default_output_per_M used when operation not in prices.
    default_input_per_M: float = 0.0
    default_output_per_M: float = 0.0

    def compute_cost(
        self,
        *,
        operation: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Compute USD cost for one call given the table's per-M pricing."""
        if input_tokens < 0 or output_tokens < 0:
            raise ValueError("token counts must be >= 0")
        op_prices = self.prices.get(operation, {})
        input_per_M = op_prices.get("input_per_M", self.default_input_per_M)
        output_per_M = op_prices.get("output_per_M", self.default_output_per_M)
        cost = (input_tokens / 1_000_000.0) * input_per_M + (
            output_tokens / 1_000_000.0
        ) * output_per_M
        return round(cost, 6)


__all__ = [
    "BillingPeriod",
    "CostEntry",
    "CostReport",
    "CostThresholdAlert",
    "PricingTable",
]
