"""
Real-time cost dashboard for Lyra's routing layer.

Provides per-model and per-task-type cost tracking, budget alerts, and
optimization suggestions.

Usage::

    dashboard = CostDashboard()

    # Record costs as they happen
    dashboard.record_completion(
        model="claude-sonnet-4-6",
        provider="anthropic",
        task_type="code_review",
        input_tokens=500,
        output_tokens=200,
        input_cost=0.0015,
        output_cost=0.006,
        latency_ms=1200,
    )

    # Check budget status
    status = dashboard.budget_status()

    # Get optimisation suggestions
    suggestions = dashboard.optimization_suggestions()
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


# ---------------------------------------------------------------------------
# CostBreakdown
# ---------------------------------------------------------------------------


@dataclass
class CostBreakdown:
    """Cost breakdown categorised by model, task type, or session.

    Attributes:
        by_model:    Dict mapping ``"provider/model"`` -> total cost in USD.
        by_task_type: Dict mapping task type -> total cost in USD.
        total_cost:  Sum of all costs in USD.
    """

    by_model: dict[str, float] = field(default_factory=dict)
    by_task_type: dict[str, float] = field(default_factory=dict)
    total_cost: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "by_model": dict(sorted(self.by_model.items(), key=lambda x: -x[1])),
            "by_task_type": dict(sorted(self.by_task_type.items(), key=lambda x: -x[1])),
            "total_cost": round(self.total_cost, 4),
        }


# ---------------------------------------------------------------------------
# CompletionRecord
# ---------------------------------------------------------------------------


@dataclass
class CompletionRecord:
    """A single completion cost record.

    Attributes:
        model:        Model name (e.g. ``"claude-sonnet-4-6"``).
        provider:     Provider name (e.g. ``"anthropic"``).
        task_type:    Task type (e.g. ``"code_review"``).
        input_tokens:  Number of input tokens.
        output_tokens: Number of output tokens.
        input_cost:   Cost of input tokens in USD.
        output_cost:  Cost of output tokens in USD.
        latency_ms:   Wall-clock time in milliseconds.
        timestamp:    ISO-formatted timestamp.
        session_id:   Optional session identifier for per-session breakdown.
    """

    model: str
    provider: str
    task_type: str
    input_tokens: int
    output_tokens: int
    input_cost: float
    output_cost: float
    latency_ms: float = 0.0
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )
    session_id: str | None = None

    @property
    def total_cost(self) -> float:
        return self.input_cost + self.output_cost

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "provider": self.provider,
            "task_type": self.task_type,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "input_cost": self.input_cost,
            "output_cost": self.output_cost,
            "total_cost": round(self.total_cost, 6),
            "latency_ms": self.latency_ms,
            "timestamp": self.timestamp,
            "session_id": self.session_id,
        }


# ---------------------------------------------------------------------------
# CostDashboard
# ---------------------------------------------------------------------------


@dataclass
class CostDashboard:
    """Real-time per-model and per-task-type cost tracking.

    Attributes:
        budget_limit: Maximum allowed cost in USD before alerts fire.
        records:      List of recorded completions.
    """

    budget_limit: float = 50.0
    records: list[CompletionRecord] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_completion(
        self,
        model: str,
        provider: str,
        task_type: str,
        input_tokens: int,
        output_tokens: int,
        input_cost: float,
        output_cost: float,
        latency_ms: float = 0.0,
        session_id: str | None = None,
    ) -> CompletionRecord:
        """Record a completion and return the record.

        Args:
            model:        Model name.
            provider:     Provider name.
            task_type:    Task type.
            input_tokens:  Input token count.
            output_tokens: Output token count.
            input_cost:   Input cost in USD.
            output_cost:  Output cost in USD.
            latency_ms:   Latency in milliseconds.
            session_id:   Optional session identifier.

        Returns:
            The created :class:`CompletionRecord`.
        """
        record = CompletionRecord(
            model=model,
            provider=provider,
            task_type=task_type,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            input_cost=input_cost,
            output_cost=output_cost,
            latency_ms=latency_ms,
            session_id=session_id,
        )
        self.records.append(record)
        return record

    # ------------------------------------------------------------------
    # Cost breakdown
    # ------------------------------------------------------------------

    def breakdown(self) -> CostBreakdown:
        """Return a :class:`CostBreakdown` across all recorded completions.

        Returns:
            CostBreakdown with costs aggregated by model and task type.
        """
        by_model: dict[str, float] = defaultdict(float)
        by_task_type: dict[str, float] = defaultdict(float)
        total: float = 0.0

        for rec in self.records:
            key = f"{rec.provider}/{rec.model}"
            by_model[key] += rec.total_cost
            by_task_type[rec.task_type] += rec.total_cost
            total += rec.total_cost

        return CostBreakdown(
            by_model=dict(by_model),
            by_task_type=dict(by_task_type),
            total_cost=total,
        )

    def breakdown_by_session(self, session_id: str) -> CostBreakdown:
        """Return a :class:`CostBreakdown` filtered to one session.

        Args:
            session_id: The session to filter by.

        Returns:
            CostBreakdown for that session.
        """
        by_model: dict[str, float] = defaultdict(float)
        by_task_type: dict[str, float] = defaultdict(float)
        total: float = 0.0

        for rec in self.records:
            if rec.session_id != session_id:
                continue
            key = f"{rec.provider}/{rec.model}"
            by_model[key] += rec.total_cost
            by_task_type[rec.task_type] += rec.total_cost
            total += rec.total_cost

        return CostBreakdown(
            by_model=dict(by_model),
            by_task_type=dict(by_task_type),
            total_cost=total,
        )

    # ------------------------------------------------------------------
    # Budget alerts
    # ------------------------------------------------------------------

    def budget_status(self) -> dict[str, Any]:
        """Return the current budget status.

        Returns:
            Dict with ``budget_limit``, ``total_spent``, ``remaining``,
            ``percent_used``, and ``alert`` (level string).
        """
        total_spent = sum(r.total_cost for r in self.records)
        remaining = max(0.0, self.budget_limit - total_spent)
        percent_used = (
            round(total_spent / self.budget_limit * 100, 1)
            if self.budget_limit > 0
            else 0.0
        )

        if percent_used >= 100:
            alert = "critical"
        elif percent_used >= 80:
            alert = "warning"
        elif percent_used >= 50:
            alert = "info"
        else:
            alert = "ok"

        return {
            "budget_limit": self.budget_limit,
            "total_spent": round(total_spent, 4),
            "remaining": round(remaining, 4),
            "percent_used": percent_used,
            "alert": alert,
        }

    def budget_alerts(self) -> list[dict[str, Any]]:
        """Return actionable budget alerts.

        Returns a list of alert dicts:
        - ``level``: ``"critical"``, ``"warning"``, or ``"info"``.
        - ``message``: Human-readable alert text.
        - ``current_spend``: Current spend in USD.
        - ``threshold``: The threshold that was crossed.

        Returns:
            List of alert dicts, empty if no alerts are warranted.
        """
        alerts: list[dict[str, Any]] = []
        total_spent = sum(r.total_cost for r in self.records)

        if self.budget_limit <= 0:
            return alerts

        percent_used = total_spent / self.budget_limit

        if percent_used >= 1.0:
            alerts.append({
                "level": "critical",
                "message": (
                    f"Budget limit of ${self.budget_limit:.2f} has been "
                    f"exceeded (${total_spent:.2f} spent). Consider increasing "
                    f"the budget or switching cheaper models."
                ),
                "current_spend": round(total_spent, 4),
                "threshold": self.budget_limit,
            })
        elif percent_used >= 0.8:
            alerts.append({
                "level": "warning",
                "message": (
                    f"Budget is {percent_used * 100:.0f}% utilised "
                    f"(${total_spent:.2f} / ${self.budget_limit:.2f})."
                ),
                "current_spend": round(total_spent, 4),
                "threshold": self.budget_limit * 0.8,
            })
        elif percent_used >= 0.5:
            alerts.append({
                "level": "info",
                "message": (
                    f"Budget is {percent_used * 100:.0f}% utilised "
                    f"(${total_spent:.2f} / ${self.budget_limit:.2f})."
                ),
                "current_spend": round(total_spent, 4),
                "threshold": self.budget_limit * 0.5,
            })

        return alerts

    # ------------------------------------------------------------------
    # Optimisation suggestions
    # ------------------------------------------------------------------

    def optimization_suggestions(self) -> list[dict[str, Any]]:
        """Generate cost optimisation suggestions based on recorded data.

        Heuristics:
        - If Opus is used for simple tasks, suggest switching to Sonnet.
        - If Sonnet is used for very simple tasks, suggest switching to Haiku.
        - If a model has high latency but similar cost to alternatives,
          suggest the alternative.
        - If a particular task type dominates costs, suggest batching.

        Returns:
            List of suggestion dicts with ``message`` and ``potential_savings``.
        """
        suggestions: list[dict[str, Any]] = []

        if not self.records:
            return suggestions

        breakdown = self.breakdown()

        # 1. Check for expensive models used on low-cost task types
        expensive_models = [
            key for key in breakdown.by_model.keys()
            if "opus" in key.lower() or "premium" in key.lower()
        ]
        cheap_task_types = {"simple_lookup", "chat", "greeting", "standard"}

        for model_key in expensive_models:
            model_cost = breakdown.by_model.get(model_key, 0.0)
            if model_cost == 0.0:
                continue
            # Count cheap-task completions on this model
            cheap_task_cost = 0.0
            for rec in self.records:
                rec_key = f"{rec.provider}/{rec.model}"
                if rec_key == model_key and rec.task_type in cheap_task_types:
                    cheap_task_cost += rec.total_cost

            if cheap_task_cost > 0.5:  # Significant waste
                suggestions.append({
                    "message": (
                        f"Model '{model_key}' spent ${cheap_task_cost:.2f} on "
                        f"simple tasks ({', '.join(sorted(cheap_task_types))}). "
                        f"Switch to Sonnet or Haiku for these tasks to save "
                        f"approximately ${cheap_task_cost * 0.6:.2f}/day."
                    ),
                    "potential_savings": round(cheap_task_cost * 0.6, 2),
                })

        # 2. Check for Sonnet-level spend that could be handled by Haiku
        sonnet_keys = [
            key for key in breakdown.by_model.keys()
            if "sonnet" in key.lower()
        ]
        for model_key in sonnet_keys:
            model_cost = breakdown.by_model.get(model_key, 0.0)
            if model_cost == 0.0:
                continue
            haiku_compatible_cost = 0.0
            for rec in self.records:
                rec_key = f"{rec.provider}/{rec.model}"
                if rec_key == model_key and rec.task_type in cheap_task_types:
                    haiku_compatible_cost += rec.total_cost

            if haiku_compatible_cost > 0.3:
                savings = haiku_compatible_cost * 0.5
                suggestions.append({
                    "message": (
                        f"Model '{model_key}' spent ${haiku_compatible_cost:.2f} "
                        f"on simple tasks. Switch to Haiku to save ~"
                        f"${savings:.2f}."
                    ),
                    "potential_savings": round(savings, 2),
                })

        # 3. Task type cost dominance
        if breakdown.by_task_type:
            dominant_task = max(
                breakdown.by_task_type.items(),
                key=lambda x: x[1],
            )
            dominant_cost = dominant_task[1]
            total = breakdown.total_cost
            if total > 0 and dominant_cost / total > 0.5:
                suggestions.append({
                    "message": (
                        f"Task type '{dominant_task[0]}' accounts for "
                        f"{dominant_cost / total * 100:.0f}% of total cost "
                        f"(${dominant_cost:.2f}). Consider batching or "
                        f"deduplicating requests of this type."
                    ),
                    "potential_savings": round(dominant_cost * 0.15, 2),
                })

        return suggestions

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def summary(self) -> dict[str, Any]:
        """Return a human-readable summary of all dashboard state.

        Returns:
            Dict with breakdown, budget status, and optimisation suggestions.
        """
        return {
            "breakdown": self.breakdown().to_dict(),
            "budget_status": self.budget_status(),
            "budget_alerts": self.budget_alerts(),
            "optimization_suggestions": self.optimization_suggestions(),
            "total_completions": len(self.records),
            "latest_timestamp": (
                max(r.timestamp for r in self.records)
                if self.records
                else None
            ),
        }


__all__ = [
    "CompletionRecord",
    "CostBreakdown",
    "CostDashboard",
]
