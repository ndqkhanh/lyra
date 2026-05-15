"""CostTracker — record every call; surface aggregated reports + alerts."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Iterable, Optional

from .types import (
    BillingPeriod,
    CostEntry,
    CostReport,
    CostThresholdAlert,
    PricingTable,
)


_GROUP_BY_AXES = ("project", "user_id", "operation", "tag", "day")


@dataclass
class CostTracker:
    """Record + aggregate cost entries.

    Production wires :class:`PricingTable` from a config file or billing-API
    snapshot; the tracker computes per-call cost from the pricing table when
    the caller doesn't pass an explicit ``cost_usd`` to :meth:`record`.

    >>> tracker = CostTracker(pricing=PricingTable(prices={
    ...     "llm_call": {"input_per_M": 3.0, "output_per_M": 15.0},
    ... }))
    >>> entry = tracker.record(
    ...     operation="llm_call",
    ...     project="polaris",
    ...     user_id="alice",
    ...     input_tokens=10_000,
    ...     output_tokens=5_000,
    ... )
    >>> entry.cost_usd  # 0.03 + 0.075 = 0.105
    0.105
    """

    pricing: Optional[PricingTable] = None
    _entries: list[CostEntry] = field(default_factory=list)

    # --- Recording -------------------------------------------------------

    def record(
        self,
        *,
        operation: str,
        project: str,
        user_id: str = "anonymous",
        input_tokens: int = 0,
        output_tokens: int = 0,
        active_params: Optional[int] = None,
        cost_usd: Optional[float] = None,
        tags: tuple[str, ...] = (),
        metadata: Optional[dict] = None,
        timestamp: Optional[float] = None,
    ) -> CostEntry:
        """Record one cost event. If ``cost_usd`` is None, compute from pricing."""
        if cost_usd is None:
            if self.pricing is None:
                cost_usd = 0.0
            else:
                cost_usd = self.pricing.compute_cost(
                    operation=operation,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )
        entry = CostEntry.create(
            operation=operation,
            project=project,
            user_id=user_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            active_params=active_params,
            cost_usd=cost_usd,
            tags=tags,
            metadata=metadata,
            timestamp=timestamp,
        )
        self._entries.append(entry)
        return entry

    def __len__(self) -> int:
        return len(self._entries)

    def all_entries(self) -> list[CostEntry]:
        return list(self._entries)

    # --- Aggregation -----------------------------------------------------

    def total(
        self,
        *,
        project: Optional[str] = None,
        user_id: Optional[str] = None,
        operation: Optional[str] = None,
        period: Optional[BillingPeriod] = None,
    ) -> float:
        """Total USD spend across entries matching the filter."""
        return sum(
            e.cost_usd
            for e in self._filter(
                project=project,
                user_id=user_id,
                operation=operation,
                period=period,
            )
        )

    def total_tokens(
        self,
        *,
        project: Optional[str] = None,
        user_id: Optional[str] = None,
        operation: Optional[str] = None,
        period: Optional[BillingPeriod] = None,
    ) -> int:
        """Total tokens (input + output) across matching entries."""
        return sum(
            e.total_tokens
            for e in self._filter(
                project=project,
                user_id=user_id,
                operation=operation,
                period=period,
            )
        )

    def report(
        self,
        *,
        group_by: str = "project",
        period: Optional[BillingPeriod] = None,
        sort_by_cost_desc: bool = True,
    ) -> CostReport:
        """Build a grouped CostReport.

        Valid ``group_by``: ``"project"``, ``"user_id"``, ``"operation"``,
        ``"tag"`` (one row per distinct tag; entries with multiple tags
        contribute to multiple rows), ``"day"`` (UTC day boundary).
        """
        if group_by not in _GROUP_BY_AXES:
            raise ValueError(
                f"group_by must be one of {_GROUP_BY_AXES}, got {group_by!r}"
            )

        scope = list(self._filter(period=period))
        groups: dict[str, dict] = {}
        for e in scope:
            keys = self._keys_for(e, group_by=group_by)
            for key in keys:
                row = groups.setdefault(key, {
                    "cost_usd": 0.0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "n_calls": 0,
                })
                row["cost_usd"] += e.cost_usd
                row["input_tokens"] += e.input_tokens
                row["output_tokens"] += e.output_tokens
                row["n_calls"] += 1

        rows = list(groups.items())
        if sort_by_cost_desc:
            rows.sort(key=lambda kv: -kv[1]["cost_usd"])
        else:
            rows.sort(key=lambda kv: kv[0])

        grand_total_usd = sum(r["cost_usd"] for _, r in rows)
        grand_total_tokens = sum(
            r["input_tokens"] + r["output_tokens"] for _, r in rows
        )

        return CostReport(
            grouped_by=group_by,
            period=period,
            rows=tuple((k, dict(v)) for k, v in rows),
            grand_total_usd=round(grand_total_usd, 6),
            grand_total_tokens=grand_total_tokens,
        )

    # --- Threshold alerting ---------------------------------------------

    def check_threshold(
        self,
        *,
        threshold_usd: float,
        project: Optional[str] = None,
        user_id: Optional[str] = None,
        period: Optional[BillingPeriod] = None,
    ) -> Optional[CostThresholdAlert]:
        """Fire an alert if spend over the period exceeds the threshold."""
        if threshold_usd < 0:
            raise ValueError(f"threshold_usd must be >= 0, got {threshold_usd}")
        actual = self.total(project=project, user_id=user_id, period=period)
        if actual <= threshold_usd:
            return None

        scope_parts = []
        if project is not None:
            scope_parts.append(f"project={project}")
        if user_id is not None:
            scope_parts.append(f"user={user_id}")
        scope = "/".join(scope_parts) if scope_parts else "global"

        return CostThresholdAlert(
            triggered_at=time.time(),
            threshold_usd=threshold_usd,
            actual_usd=actual,
            scope=scope,
            period=period,
            note=f"spend {actual:.6f} exceeds threshold {threshold_usd:.6f}",
        )

    # --- Internals -------------------------------------------------------

    def _filter(
        self,
        *,
        project: Optional[str] = None,
        user_id: Optional[str] = None,
        operation: Optional[str] = None,
        period: Optional[BillingPeriod] = None,
    ) -> Iterable[CostEntry]:
        for e in self._entries:
            if project is not None and e.project != project:
                continue
            if user_id is not None and e.user_id != user_id:
                continue
            if operation is not None and e.operation != operation:
                continue
            if period is not None and not period.contains(e.timestamp):
                continue
            yield e

    @staticmethod
    def _keys_for(entry: CostEntry, *, group_by: str) -> list[str]:
        if group_by == "project":
            return [entry.project]
        if group_by == "user_id":
            return [entry.user_id]
        if group_by == "operation":
            return [entry.operation]
        if group_by == "tag":
            return list(entry.tags) if entry.tags else ["<no-tags>"]
        if group_by == "day":
            # UTC day key as ISO date (YYYY-MM-DD).
            import datetime as _dt
            d = _dt.datetime.utcfromtimestamp(entry.timestamp).date()
            return [d.isoformat()]
        raise ValueError(f"unsupported group_by: {group_by!r}")


__all__ = ["CostTracker"]
