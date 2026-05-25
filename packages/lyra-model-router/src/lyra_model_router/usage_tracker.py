"""Track model usage, costs, latency, and quality metrics.

Provides per-model, per-task-type, and per-time-period aggregation of usage data,
budget alerting when approaching limits, and exportable usage reports.
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from typing import Any, Sequence


@dataclass(frozen=True)
class UsageRecord:
    """A single usage record for a routed task."""
    model_id: str
    task_type: str
    tokens_used: int = 0
    cost: float = 0.0
    latency_ms: float = 0.0
    success: bool = True
    model_tier: str = ""
    timestamp: float = 0.0

    def __post_init__(self) -> None:
        # If timestamp is not set, use object.__setattr__ since frozen
        if self.timestamp == 0.0:
            object.__setattr__(self, "timestamp", time.time())


@dataclass(frozen=True)
class UsageStats:
    """Aggregated usage statistics for a model or task type."""
    total_calls: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    total_latency_ms: float = 0.0
    success_count: int = 0
    failure_count: int = 0
    avg_latency_ms: float = 0.0
    avg_cost_per_call: float = 0.0
    avg_tokens_per_call: float = 0.0

    def __post_init__(self) -> None:
        # Auto-compute averages
        if self.total_calls > 0:
            object.__setattr__(self, "avg_latency_ms", self.total_latency_ms / self.total_calls)
            object.__setattr__(self, "avg_cost_per_call", self.total_cost / self.total_calls)
            object.__setattr__(self, "avg_tokens_per_call", self.total_tokens / self.total_calls)


@dataclass(frozen=True)
class BudgetAlert:
    """Alert raised when usage approaches or exceeds budget limits."""
    model_id: str
    alert_type: str  # "cost", "tokens", "latency", "error_rate"
    threshold: float
    current_value: float
    message: str
    timestamp: float = 0.0

    def __post_init__(self) -> None:
        if self.timestamp == 0.0:
            object.__setattr__(self, "timestamp", time.time())


class UsageTracker:
    """Tracks model usage, aggregates statistics, and raises budget alerts.

    Supports per-model, per-task-type, and per-time-period aggregation.
    Exports usage reports in dict/JSON format.
    """

    def __init__(self) -> None:
        self._records: list[UsageRecord] = []
        self._alerts: list[BudgetAlert] = []
        self._cost_budget: float = float("inf")
        self._token_budget: int = 0
        self._alert_callbacks: list[callable] = []

    def set_cost_budget(self, budget: float) -> None:
        """Set a total cost budget. When exceeded, alerts are raised."""
        self._cost_budget = budget

    def set_token_budget(self, budget: int) -> None:
        """Set a total token budget. When exceeded, alerts are raised."""
        self._token_budget = budget

    def on_alert(self, callback: callable) -> None:
        """Register a callback for budget alerts."""
        self._alert_callbacks.append(callback)

    def record(self, record: UsageRecord) -> None:
        """Record a usage record and check budget limits."""
        self._records.append(record)
        self._check_budgets(record)

    def record_many(self, records: Sequence[UsageRecord]) -> None:
        """Record multiple usage records at once."""
        for record in records:
            self._records.append(record)
            self._check_budgets(record)

    def _check_budgets(self, record: UsageRecord) -> None:
        """Check budgets and raise alerts if exceeded."""
        total_cost = sum(r.cost for r in self._records)
        total_tokens = sum(r.tokens_used for r in self._records)

        if total_cost > self._cost_budget:
            alert = BudgetAlert(
                model_id=record.model_id,
                alert_type="cost",
                threshold=self._cost_budget,
                current_value=total_cost,
                message=f"Cost budget exceeded: {total_cost:.4f} > {self._cost_budget:.4f}",
            )
            self._alerts.append(alert)
            for cb in self._alert_callbacks:
                cb(alert)

        if self._token_budget > 0 and total_tokens > self._token_budget:
            alert = BudgetAlert(
                model_id=record.model_id,
                alert_type="tokens",
                threshold=float(self._token_budget),
                current_value=float(total_tokens),
                message=f"Token budget exceeded: {total_tokens} > {self._token_budget}",
            )
            self._alerts.append(alert)
            for cb in self._alert_callbacks:
                cb(alert)

    # ── Aggregation ──────────────────────────────────────────────────

    def stats_by_model(self, model_id: str | None = None) -> dict[str, UsageStats]:
        """Aggregate usage statistics per model."""
        grouped: dict[str, list[UsageRecord]] = defaultdict(list)
        for r in self._records:
            if model_id is None or r.model_id == model_id:
                grouped[r.model_id].append(r)
        return {mid: self._aggregate(recs) for mid, recs in grouped.items()}

    def stats_by_task_type(self, task_type: str | None = None) -> dict[str, UsageStats]:
        """Aggregate usage statistics per task type."""
        grouped: defaultdict[str, list[UsageRecord]] = defaultdict(list)
        for r in self._records:
            if task_type is None or r.task_type == task_type:
                grouped[r.task_type].append(r)
        return {tt: self._aggregate(recs) for tt, recs in grouped.items()}

    def stats_by_time_period(self, start: float, end: float) -> UsageStats:
        """Aggregate usage statistics for a specific time range."""
        filtered = [
            r for r in self._records
            if start <= r.timestamp <= end
        ]
        return self._aggregate(filtered)

    def stats_by_tier(self) -> dict[str, UsageStats]:
        """Aggregate usage statistics per model tier."""
        grouped: defaultdict[str, list[UsageRecord]] = defaultdict(list)
        for r in self._records:
            tier = r.model_tier or "unknown"
            grouped[tier].append(r)
        return {tier: self._aggregate(recs) for tier, recs in grouped.items()}

    @staticmethod
    def _aggregate(records: list[UsageRecord]) -> UsageStats:
        """Aggregate a list of usage records into summary stats."""
        if not records:
            return UsageStats()
        total_calls = len(records)
        total_tokens = sum(r.tokens_used for r in records)
        total_cost = sum(r.cost for r in records)
        total_latency = sum(r.latency_ms for r in records)
        success_count = sum(1 for r in records if r.success)
        failure_count = total_calls - success_count
        return UsageStats(
            total_calls=total_calls,
            total_tokens=total_tokens,
            total_cost=total_cost,
            total_latency_ms=total_latency,
            success_count=success_count,
            failure_count=failure_count,
        )

    # ── Summary & Export ──────────────────────────────────────────────

    def recent_records(self, count: int = 10) -> list[UsageRecord]:
        """Return the most recent usage records."""
        return self._records[-count:] if self._records else []

    def alerts(self, alert_type: str | None = None) -> list[BudgetAlert]:
        """Return alerts, optionally filtered by type."""
        if alert_type is None:
            return list(self._alerts)
        return [a for a in self._alerts if a.alert_type == alert_type]

    def total_cost(self) -> float:
        """Return total accumulated cost."""
        return sum(r.cost for r in self._records)

    def total_tokens(self) -> int:
        """Return total tokens used."""
        return sum(r.tokens_used for r in self._records)

    @property
    def total_calls(self) -> int:
        return len(self._records)

    def clear(self) -> None:
        """Clear all records and alerts."""
        self._records.clear()
        self._alerts.clear()

    def export(self) -> dict[str, Any]:
        """Export full usage report as a dictionary."""
        return {
            "total_calls": self.total_calls,
            "total_cost": self.total_cost(),
            "total_tokens": self.total_tokens(),
            "alerts_count": len(self._alerts),
            "models": {
                mid: asdict(stats)
                for mid, stats in self.stats_by_model().items()
            },
            "task_types": {
                tt: asdict(stats)
                for tt, stats in self.stats_by_task_type().items()
            },
            "tiers": {
                tier: asdict(stats)
                for tier, stats in self.stats_by_tier().items()
            },
        }

    def export_json(self, indent: int = 2) -> str:
        """Export full usage report as JSON string."""
        return json.dumps(self.export(), indent=indent)
