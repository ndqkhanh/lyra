"""SLA definition, enforcement, budget tracking, and violation management.

Defines Service Level Objectives (SLOs) and Service Level Indicators (SLIs),
enforces policies, and tracks budgets for tokens, time, and cost.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from .exceptions import (
    BudgetExceededError,
    InvalidMetricError,
)

logger = logging.getLogger(__name__)


# ── Enums and data classes ──────────────────────────────────────────────


class SLIMetric(Enum):
    """Service Level Indicator metrics."""

    LATENCY_P50 = "latency_p50"
    LATENCY_P95 = "latency_p95"
    LATENCY_P99 = "latency_p99"
    AVAILABILITY = "availability"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"
    QUALITY_SCORE = "quality_score"
    TOKEN_USAGE = "token_usage"
    COST_PER_TASK = "cost_per_task"
    SUCCESS_RATE = "success_rate"


class BudgetType(Enum):
    """Types of budgets to track."""

    TOKEN = auto()
    COST = auto()
    TIME = auto()
    TASK_COUNT = auto()


class ViolationSeverity(Enum):
    """Severity of SLA violations."""

    WARNING = auto()
    MINOR = auto()
    MAJOR = auto()
    CRITICAL = auto()


@dataclass
class SLO:
    """Service Level Objective definition.

    Attributes:
        metric: Which SLI to measure.
        target: Target value (e.g., 1000ms for latency).
        comparator: Comparison operator: 'lt', 'gt', 'lte', 'gte'.
        window_seconds: Rolling window for measurement.
        burn_rate_threshold: Alert on budget burn rate.
    """

    metric: SLIMetric
    target: float
    comparator: str = "lt"  # 'lt', 'gt', 'lte', 'gte'
    window_seconds: float = 300.0  # 5 minutes
    burn_rate_threshold: float = 1.0  # 1x budget burn triggers warning

    def evaluate(self, value: float) -> bool:
        """Check if a value meets the SLO target.

        Returns:
            True if compliant.
        """
        if self.comparator == "lt":
            return value < self.target
        elif self.comparator == "gt":
            return value > self.target
        elif self.comparator == "lte":
            return value <= self.target
        elif self.comparator == "gte":
            return value >= self.target
        return False


@dataclass
class SLA:
    """Service Level Agreement for an agent or service.

    Attributes:
        agent_id: Agent/service identifier.
        name: Human-readable SLA name.
        slos: List of SLOs.
        error_budget_pct: Allowed error budget (e.g., 0.1% for 99.9% availability).
        budget_limits: Per-budget-type limits.
        created_at: When the SLA was created.
        updated_at: Last modification time.
        enabled: Whether this SLA is active.
    """

    agent_id: str
    name: str = ""
    slos: list[SLO] = field(default_factory=list)
    error_budget_pct: float = 0.1
    budget_limits: dict[BudgetType, float] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    enabled: bool = True


@dataclass
class SLAViolation:
    """Record of an SLA violation.

    Attributes:
        violation_id: Unique identifier.
        agent_id: Which agent violated.
        metric: Which metric was violated.
        slo_target: The SLO target value.
        actual: The actual measured value.
        severity: Violation severity.
        timestamp: When the violation occurred.
        details: Additional context.
    """

    violation_id: str = field(default_factory=lambda: str(int(time.time() * 1000)))
    agent_id: str = ""
    metric: str = ""
    slo_target: float = 0.0
    actual: float = 0.0
    severity: ViolationSeverity = ViolationSeverity.WARNING
    timestamp: float = field(default_factory=time.time)
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class Budget:
    """Tracks budget consumption for an agent.

    Attributes:
        budget_type: What is being tracked.
        limit: Maximum allowed.
        consumed: Amount consumed so far.
        remaining: Amount remaining.
    """

    budget_type: BudgetType
    limit: float
    consumed: float = 0.0

    @property
    def remaining(self) -> float:
        """Amount remaining in the budget."""
        return max(0.0, self.limit - self.consumed)

    @property
    def utilization_pct(self) -> float:
        """Percentage of budget utilized."""
        if self.limit <= 0:
            return 0.0
        return (self.consumed / self.limit) * 100.0

    @property
    def is_exhausted(self) -> bool:
        """Whether the budget is exhausted."""
        return self.consumed >= self.limit

    def consume(self, amount: float) -> float:
        """Consume budget and return remaining amount.

        Raises:
            BudgetExceededError: If budget is exceeded.
        """
        if self.consumed + amount > self.limit:
            raise BudgetExceededError(
                self.budget_type.name, self.limit, self.consumed + amount
            )
        self.consumed += amount
        return self.remaining


# ── SLA Manager ────────────────────────────────────────────────────────


class SLAManager:
    """Manages SLA definitions, enforcement, violation tracking, and budgets.

    Provides centralized SLA lifecycle management across multiple agents,
    with real-time compliance checking and budget tracking.
    """

    VALID_METRICS = [m.value for m in SLIMetric]

    def __init__(
        self,
        default_error_budget_pct: float = 0.1,
        max_violation_history: int = 10000,
    ) -> None:
        self.default_error_budget_pct = default_error_budget_pct
        self._slas: dict[str, SLA] = {}
        self._violations: deque[SLAViolation] = deque(maxlen=max_violation_history)
        self._budgets: dict[str, dict[BudgetType, Budget]] = {}
        self._metric_observations: dict[str, dict[str, deque[tuple[float, float]]]] = {}

    # ── SLA lifecycle ──────────────────────────────────────────────────

    def define_sla(self, sla: SLA) -> None:
        """Define or update an SLA for an agent.

        Args:
            sla: The SLA definition.
        """
        sla.updated_at = time.time()
        self._slas[sla.agent_id] = sla
        logger.info("SLA defined for '%s' with %d SLOs", sla.agent_id, len(sla.slos))

    def remove_sla(self, agent_id: str) -> bool:
        """Remove an SLA definition.

        Returns:
            True if removed, False if not found.
        """
        if agent_id in self._slas:
            del self._slas[agent_id]
            return True
        return False

    def get_sla(self, agent_id: str) -> SLA | None:
        """Get the SLA for an agent."""
        return self._slas.get(agent_id)

    def list_slas(self) -> list[SLA]:
        """List all defined SLAs."""
        return list(self._slas.values())

    # ── Metric recording ───────────────────────────────────────────────

    def record_metric(
        self,
        agent_id: str,
        metric: str,
        value: float,
        timestamp: float | None = None,
    ) -> None:
        """Record a metric observation for an agent.

        Args:
            agent_id: Agent identifier.
            metric: Metric name (must be in VALID_METRICS).
            value: Observed value.
            timestamp: Optional timestamp (defaults to now).

        Raises:
            InvalidMetricError: If metric is not valid.
        """
        if metric not in self.VALID_METRICS:
            raise InvalidMetricError(metric, self.VALID_METRICS)

        ts = timestamp or time.time()
        if agent_id not in self._metric_observations:
            self._metric_observations[agent_id] = {}
        if metric not in self._metric_observations[agent_id]:
            self._metric_observations[agent_id][metric] = deque(maxlen=10000)
        self._metric_observations[agent_id][metric].append((ts, value))

    def record_batch(
        self,
        agent_id: str,
        metrics: dict[str, float],
        timestamp: float | None = None,
    ) -> None:
        """Record multiple metrics at once."""
        ts = timestamp or time.time()
        for metric, value in metrics.items():
            self.record_metric(agent_id, metric, value, ts)

    def get_metric_values(
        self,
        agent_id: str,
        metric: str,
        window_seconds: float | None = None,
    ) -> list[float]:
        """Get metric values, optionally within a time window.

        Args:
            agent_id: Agent identifier.
            metric: Metric name.
            window_seconds: Optional time window to filter.

        Returns:
            List of metric values.
        """
        obs = self._metric_observations.get(agent_id, {}).get(metric, deque())
        if window_seconds is not None:
            cutoff = time.time() - window_seconds
            obs = [(ts, v) for ts, v in obs if ts >= cutoff]
            return [v for _, v in obs]
        return [v for _, v in obs]

    # ── Budget management ──────────────────────────────────────────────

    def set_budget(
        self,
        agent_id: str,
        budget_type: BudgetType,
        limit: float,
    ) -> Budget:
        """Set a budget limit for an agent.

        Args:
            agent_id: Agent identifier.
            budget_type: Type of budget.
            limit: Maximum limit value.

        Returns:
            The budget object.
        """
        if agent_id not in self._budgets:
            self._budgets[agent_id] = {}
        budget = Budget(budget_type=budget_type, limit=limit)
        self._budgets[agent_id][budget_type] = budget
        return budget

    def consume_budget(
        self,
        agent_id: str,
        budget_type: BudgetType,
        amount: float,
    ) -> float:
        """Consume from a budget.

        Args:
            agent_id: Agent identifier.
            budget_type: Which budget to consume from.
            amount: Amount to consume.

        Returns:
            Remaining budget.

        Raises:
            BudgetExceededError: If budget is exceeded.
        """
        if agent_id not in self._budgets or budget_type not in self._budgets[agent_id]:
            # Auto-create budget with reasonable default
            default_limits = {
                BudgetType.TOKEN: 1_000_000,
                BudgetType.COST: 100.0,
                BudgetType.TIME: 3600.0,
                BudgetType.TASK_COUNT: 1000,
            }
            self.set_budget(agent_id, budget_type, default_limits.get(budget_type, 1000.0))

        budget = self._budgets[agent_id][budget_type]
        return budget.consume(amount)

    def get_budget(self, agent_id: str, budget_type: BudgetType) -> Budget | None:
        """Get a specific budget."""
        return self._budgets.get(agent_id, {}).get(budget_type)

    def get_all_budgets(self, agent_id: str) -> dict[BudgetType, Budget]:
        """Get all budgets for an agent."""
        return self._budgets.get(agent_id, {})

    def reset_budget(self, agent_id: str, budget_type: BudgetType) -> None:
        """Reset a budget's consumption to zero."""
        budget = self.get_budget(agent_id, budget_type)
        if budget:
            budget.consumed = 0.0

    # ── Compliance checking ────────────────────────────────────────────

    async def check_compliance(self, agent_id: str) -> dict[str, Any]:
        """Check SLA compliance for an agent.

        Args:
            agent_id: Agent identifier.

        Returns:
            Compliance report dict.
        """
        sla = self._slas.get(agent_id)
        if not sla or not sla.enabled:
            return {"compliant": True, "agent_id": agent_id, "message": "No active SLA"}

        violations: list[dict[str, Any]] = []
        total_slos = len(sla.slos)
        violated_slos = 0

        for slo in sla.slos:
            values = self.get_metric_values(agent_id, slo.metric.value, slo.window_seconds)
            if not values:
                continue

            # Compute aggregate value based on metric type
            metric_name = slo.metric.value
            if "p50" in metric_name:
                agg_value = self._percentile(values, 50)
            elif "p95" in metric_name:
                agg_value = self._percentile(values, 95)
            elif "p99" in metric_name:
                agg_value = self._percentile(values, 99)
            elif metric_name in ("error_rate", "cost_per_task"):
                agg_value = sum(values) / len(values)
            elif metric_name in ("availability", "success_rate"):
                agg_value = sum(values) / len(values)
            else:
                agg_value = sum(values) / len(values)

            compliant = slo.evaluate(agg_value)

            if not compliant:
                violated_slos += 1
                severity = self._assess_severity(agg_value, slo.target, slo.comparator)
                violation = SLAViolation(
                    agent_id=agent_id,
                    metric=metric_name,
                    slo_target=slo.target,
                    actual=agg_value,
                    severity=severity,
                )
                self._violations.append(violation)
                violations.append({
                    "metric": metric_name,
                    "target": slo.target,
                    "actual": agg_value,
                    "severity": severity.name,
                })

                if severity == ViolationSeverity.CRITICAL:
                    logger.critical(
                        "CRITICAL SLA violation: %s %s=%.2f (target=%s %.2f)",
                        agent_id, metric_name, agg_value, slo.comparator, slo.target,
                    )
                else:
                    logger.warning(
                        "SLA violation: %s %s=%.2f (target=%s %.2f) [%s]",
                        agent_id, metric_name, agg_value, slo.comparator, slo.target,
                        severity.name,
                    )

        compliance_pct = ((total_slos - violated_slos) / max(total_slos, 1)) * 100.0

        return {
            "compliant": violated_slos == 0,
            "agent_id": agent_id,
            "compliance_pct": compliance_pct,
            "total_slos": total_slos,
            "violated_slos": violated_slos,
            "violations": violations,
        }

    async def check_all_compliance(self) -> dict[str, Any]:
        """Check compliance for all agents simultaneously.

        Returns:
            Dict mapping agent_id to compliance report.
        """
        tasks = [self.check_compliance(aid) for aid in self._slas]
        results = await asyncio.gather(*tasks)
        return {r["agent_id"]: r for r in results}

    def _assess_severity(
        self, actual: float, target: float, comparator: str
    ) -> ViolationSeverity:
        """Assess violation severity based on deviation from target."""
        if target == 0:
            return ViolationSeverity.CRITICAL if actual != 0 else ViolationSeverity.WARNING

        deviation = abs(actual - target) / abs(target)

        if deviation > 1.0:
            return ViolationSeverity.CRITICAL
        elif deviation > 0.5:
            return ViolationSeverity.MAJOR
        elif deviation > 0.2:
            return ViolationSeverity.MINOR
        else:
            return ViolationSeverity.WARNING

    def _percentile(self, values: list[float], p: float) -> float:
        """Compute percentile of a list of values."""
        if not values:
            return 0.0
        sorted_vals = sorted(values)
        k = (len(sorted_vals) - 1) * p / 100.0
        f = int(k)
        c = k - f
        if f + 1 < len(sorted_vals):
            return sorted_vals[f] + c * (sorted_vals[f + 1] - sorted_vals[f])
        return sorted_vals[f]

    # ── Error budget tracking ──────────────────────────────────────────

    def get_error_budget_remaining(self, agent_id: str) -> dict[str, float]:
        """Calculate remaining error budget for an agent's SLOs.

        Returns:
            Dict of metric -> remaining_error_budget_pct.
        """
        sla = self._slas.get(agent_id)
        if not sla:
            return {}

        budgets: dict[str, float] = {}
        for slo in sla.slos:
            values = self.get_metric_values(agent_id, slo.metric.value, slo.window_seconds)
            if not values:
                budgets[slo.metric.value] = sla.error_budget_pct
                continue

            failures = sum(1 for v in values if not slo.evaluate(v))
            total = len(values)
            failure_rate = failures / total if total > 0 else 0.0
            remaining = max(0.0, sla.error_budget_pct - failure_rate * 100)
            budgets[slo.metric.value] = remaining

        return budgets

    # ── Violation querying ─────────────────────────────────────────────

    def get_violations(
        self,
        agent_id: str | None = None,
        since: float | None = None,
        severity: ViolationSeverity | None = None,
    ) -> list[SLAViolation]:
        """Query violations with optional filters.

        Args:
            agent_id: Filter by agent.
            since: Filter by timestamp.
            severity: Filter by severity.

        Returns:
            Matching violations.
        """
        results = list(self._violations)

        if agent_id:
            results = [v for v in results if v.agent_id == agent_id]
        if since:
            results = [v for v in results if v.timestamp >= since]
        if severity:
            results = [v for v in results if v.severity == severity]

        return results

    def get_violation_count(self, agent_id: str | None = None) -> int:
        """Get violation count, optionally filtered by agent."""
        if agent_id:
            return sum(1 for v in self._violations if v.agent_id == agent_id)
        return len(self._violations)

    # ── Summary ────────────────────────────────────────────────────────

    @property
    def summary(self) -> dict[str, Any]:
        """Get SLA manager summary."""
        agents_with_budgets = {
            aid: {
                bt.name: {
                    "limit": b.limit,
                    "consumed": b.consumed,
                    "remaining": b.remaining,
                    "utilization_pct": b.utilization_pct,
                }
                for bt, b in budgets.items()
            }
            for aid, budgets in self._budgets.items()
        }

        return {
            "agents_with_sla": len(self._slas),
            "total_violations": len(self._violations),
            "recent_violations": [
                {
                    "agent_id": v.agent_id,
                    "metric": v.metric,
                    "severity": v.severity.name,
                    "actual": v.actual,
                    "timestamp": v.timestamp,
                }
                for v in list(self._violations)[-5:]
            ],
            "budgets": agents_with_budgets,
        }
