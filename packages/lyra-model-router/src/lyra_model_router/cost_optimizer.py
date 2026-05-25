"""Tier-based routing with cost constraints and budget tracking.

Provides cost-aware model selection, session/day/month budget tracking,
automatic tier demotion when budgets are tight, and cost-benefit tradeoff analysis.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from .capability_analyzer import CapabilityAnalyzer, MatchScore, ModelCapability, TaskProfile


class CostTier(Enum):
    """Cost tier for routing decisions. Higher = more expensive, more capable."""
    CRITICAL = "critical"  # No cost constraints, best quality
    STANDARD = "standard"  # Moderate budget, balanced
    ECONOMY = "economy"  # Tight budget, prefer cheaper models
    BACKGROUND = "background"  # Minimal cost, non-interactive


@dataclass(frozen=True)
class BudgetLimits:
    """Budget constraints for cost optimization."""
    per_session: float = float("inf")
    per_day: float = float("inf")
    per_month: float = float("inf")
    min_tier: CostTier = CostTier.ECONOMY
    max_cost_per_task: float = float("inf")


@dataclass(frozen=True)
class CostBenefitResult:
    """Result of a cost-benefit tradeoff analysis."""
    model_id: str
    estimated_cost: float
    quality_score: float  # 0.0-1.0
    cost_benefit_ratio: float  # quality / cost
    recommended: bool
    reason: str


class BudgetTracker:
    """Tracks budget consumption across multiple periods.

    Supports per-session, per-day, and per-month budget limits with
    automatic rollover and alerting when approaching limits.
    """

    def __init__(self) -> None:
        self._session_used: float = 0.0
        self._day_used: float = 0.0
        self._month_used: float = 0.0
        self._session_start: float = time.time()
        self._day_date: str = self._today_str()
        self._month_str: str = self._current_month_str()
        self._limits: BudgetLimits = BudgetLimits()
        self._alert_thresholds: dict[str, float] = {
            "session": 0.85,
            "day": 0.85,
            "month": 0.85,
        }
        self._alerts_triggered: list[str] = []

    @staticmethod
    def _today_str() -> str:
        return time.strftime("%Y-%m-%d")

    @staticmethod
    def _current_month_str() -> str:
        return time.strftime("%Y-%m")

    def set_limits(self, limits: BudgetLimits) -> None:
        """Set budget limits."""
        self._limits = limits

    def set_alert_threshold(self, period: str, threshold: float) -> None:
        """Set budget alert threshold (0.0-1.0) for a period."""
        if period not in ("session", "day", "month"):
            raise ValueError(f"Unknown period: {period}")
        self._alert_thresholds[period] = max(0.0, min(1.0, threshold))

    def record_spend(self, amount: float) -> None:
        """Record a spending amount. Returns alerts if thresholds exceeded."""
        self._check_period_rollover()
        self._session_used += amount
        self._day_used += amount
        self._month_used += amount

    def _check_period_rollover(self) -> None:
        """Reset counters if a new period has started."""
        today = self._today_str()
        if today != self._day_date:
            self._day_used = 0.0
            self._day_date = today
        month = self._current_month_str()
        if month != self._month_str:
            self._month_used = 0.0
            self._month_str = month

    @property
    def session_remaining(self) -> float:
        return self._limits.per_session - self._session_used

    @property
    def day_remaining(self) -> float:
        return self._limits.per_day - self._day_used

    @property
    def month_remaining(self) -> float:
        return self._limits.per_month - self._month_used

    def can_spend(self, amount: float) -> bool:
        """Check if amount can be spent within all budget limits."""
        return (
            self._session_used + amount <= self._limits.per_session
            and self._day_used + amount <= self._limits.per_day
            and self._month_used + amount <= self._limits.per_month
        )

    def budget_status(self) -> dict[str, dict[str, float]]:
        """Return current budget usage status for all periods."""
        self._check_period_rollover()
        return {
            "session": {
                "used": self._session_used,
                "limit": self._limits.per_session,
                "remaining": self.session_remaining,
                "pct": self._session_used / self._limits.per_session if self._limits.per_session else 1.0,
            },
            "day": {
                "used": self._day_used,
                "limit": self._limits.per_day,
                "remaining": self.day_remaining,
                "pct": self._day_used / self._limits.per_day if self._limits.per_day else 1.0,
            },
            "month": {
                "used": self._month_used,
                "limit": self._limits.per_month,
                "remaining": self.month_remaining,
                "pct": self._month_used / self._limits.per_month if self._limits.per_month else 1.0,
            },
        }

    def check_alerts(self) -> list[str]:
        """Check and return any budget alerts that have been triggered."""
        new_alerts: list[str] = []
        status = self.budget_status()
        for period, info in status.items():
            threshold = self._alert_thresholds.get(period, 0.85)
            if info["pct"] >= threshold:
                alert = (
                    f"{period} budget at {info['pct']:.0%} "
                    f"(used={info['used']:.2f}, limit={info['limit']:.2f})"
                )
                if alert not in self._alerts_triggered:
                    new_alerts.append(alert)
                    self._alerts_triggered.append(alert)
        return new_alerts

    def reset_session(self) -> None:
        """Reset session counter (e.g. at end of session)."""
        self._session_used = 0.0
        self._session_start = time.time()
        self._alerts_triggered.clear()


class CostOptimizer:
    """Optimizes model selection based on cost constraints.

    Given scored model matches and a budget constraint, picks the best model
    that fits within budget, potentially demoting tiers when budget is tight.
    """

    def __init__(
        self,
        budget_tracker: BudgetTracker | None = None,
        default_tier: CostTier = CostTier.STANDARD,
        capability_analyzer: CapabilityAnalyzer | None = None,
    ) -> None:
        self._tracker = budget_tracker or BudgetTracker()
        self._default_tier = default_tier
        self._capability_analyzer = capability_analyzer

    @property
    def tracker(self) -> BudgetTracker:
        return self._tracker

    def optimize(
        self,
        task: TaskProfile,
        scored_models: Sequence[MatchScore],
        budget_constraint: float | None = None,
        preferred_tier: CostTier | None = None,
    ) -> MatchScore | None:
        """Select the best model given cost constraints.

        Iterates scored models from highest to lowest total_score, selecting
        the first that fits the budget. If none fit, demotes tier and retries.
        """
        tier = preferred_tier or self._default_tier
        limit = budget_constraint or self._determine_tier_budget(tier)

        # First pass: try within budget
        for score in scored_models:
            cap = self._find_capability(score.model_id)
            if cap is None:
                continue
            estimated_cost = cap.cost_for_tokens(task.estimated_tokens)
            if estimated_cost <= limit and self._tracker.can_spend(estimated_cost):
                return score

        # Second pass: iterate down tiers
        for lower_tier in self._demotion_chain(tier):
            lower_limit = self._determine_tier_budget(lower_tier)
            for score in scored_models:
                cap = self._find_capability(score.model_id)
                if cap is None:
                    continue
                estimated_cost = cap.cost_for_tokens(task.estimated_tokens)
                if estimated_cost <= lower_limit and self._tracker.can_spend(estimated_cost):
                    return score

        # Last resort: cheapest model that fits budget
        cheapest = self._find_cheapest_affordable(scored_models, task, limit)
        return cheapest

    def _find_capability(self, model_id: str) -> ModelCapability | None:
        """Resolve model_id to ModelCapability via the capability analyzer."""
        if self._capability_analyzer is not None:
            return self._capability_analyzer.get_model(model_id)
        return None

    def estimate_task_cost(self, task: TaskProfile, model_id: str) -> float:
        """Estimate the cost of running a task on a specific model."""
        cap = self._find_capability(model_id)
        if cap is None:
            base_rate = self._estimate_base_rate(model_id)
            return (task.estimated_tokens / 1000.0) * base_rate
        return cap.cost_for_tokens(task.estimated_tokens)

    def _estimate_base_rate(self, model_id: str) -> float:
        """Fallback cost estimation when model not in registry."""
        if "opus" in model_id:
            return 0.075
        if "sonnet" in model_id:
            return 0.015
        if "haiku" in model_id:
            return 0.0025
        if "deepseek" in model_id:
            return 0.001
        if "gpt" in model_id:
            return 0.01
        return 0.005

    def _determine_tier_budget(self, tier: CostTier) -> float:
        """Determine max cost per task for a given tier."""
        mapping = {
            CostTier.CRITICAL: float("inf"),
            CostTier.STANDARD: 0.50,
            CostTier.ECONOMY: 0.10,
            CostTier.BACKGROUND: 0.02,
        }
        return mapping.get(tier, 0.50)

    def cost_benefit_analysis(
        self,
        task: TaskProfile,
        scored_models: Sequence[MatchScore],
    ) -> list[CostBenefitResult]:
        """Analyze cost-benefit tradeoffs for scored models."""
        results: list[CostBenefitResult] = []
        for score in scored_models:
            cap = self._find_capability(score.model_id)
            rate = cap.cost_per_1k_tokens if cap else self._estimate_base_rate(score.model_id)
            estimated_cost = (task.estimated_tokens / 1000.0) * rate
            quality_score = score.total_score
            ratio = (quality_score / estimated_cost) if estimated_cost > 0 else float("inf")
            recommended = estimated_cost <= self._determine_tier_budget(self._default_tier)
            reason = "within budget" if recommended else "exceeds budget"
            results.append(CostBenefitResult(
                model_id=score.model_id,
                estimated_cost=round(estimated_cost, 6),
                quality_score=quality_score,
                cost_benefit_ratio=round(ratio, 4),
                recommended=recommended,
                reason=reason,
            ))
        return results

    @staticmethod
    def _demotion_chain(start: CostTier) -> list[CostTier]:
        """Return the chain of tiers to demote through."""
        all_tiers = [CostTier.CRITICAL, CostTier.STANDARD, CostTier.ECONOMY, CostTier.BACKGROUND]
        try:
            idx = all_tiers.index(start)
        except ValueError:
            return []
        return all_tiers[idx + 1:]

    @staticmethod
    def _find_cheapest_affordable(
        scored_models: Sequence[MatchScore],
        task: TaskProfile,
        limit: float,
    ) -> MatchScore | None:
        """Find cheapest model that fits within budget."""
        affordable = [
            s for s in scored_models
            if task.estimated_tokens > 0
        ]
        if not affordable:
            return None
        return affordable[-1]

    @staticmethod
    def suggest_tier_for_budget(budget: float) -> CostTier:
        """Suggest the appropriate tier for a given per-task budget."""
        if budget >= 0.50:
            return CostTier.STANDARD
        if budget >= 0.10:
            return CostTier.ECONOMY
        if budget >= 0.02:
            return CostTier.BACKGROUND
        return CostTier.BACKGROUND
