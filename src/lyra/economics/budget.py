"""
Cost economics — BudgetController with session budget caps,
cost-per-provider tracking, and budget alerts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class BudgetAlertLevel(Enum):
    """Severity level for a budget alert."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class BudgetAlert:
    """A budget alert raised when cost thresholds are crossed.

    Attributes:
        level: Severity level.
        message: Human-readable alert message.
        provider: Provider that triggered the alert (or None for session-level).
        current_cost: Current cost at alert time.
        threshold: Threshold that was crossed.
        timestamp: When the alert was raised.
    """

    level: BudgetAlertLevel
    message: str
    current_cost: float
    threshold: float
    provider: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Serialize alert to dictionary."""
        return {
            "level": self.level.value,
            "message": self.message,
            "current_cost": self.current_cost,
            "threshold": self.threshold,
            "provider": self.provider,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ProviderCostRecord:
    """Per-provider cost tracking record.

    Attributes:
        provider_name: Name of the provider (e.g. "openai", "anthropic").
        total_cost: Cumulative cost for this provider.
        request_count: Number of requests made.
        last_request: Timestamp of the last request.
    """

    provider_name: str
    total_cost: float = 0.0
    request_count: int = 0
    last_request: datetime | None = None

    def record_request(self, cost: float) -> None:
        """Record a request with the given cost.

        Args:
            cost: Cost of the request in the provider's billing unit.
        """
        self.total_cost += cost
        self.request_count += 1
        self.last_request = datetime.now(timezone.utc)

    @property
    def average_cost(self) -> float:
        """Average cost per request."""
        if self.request_count == 0:
            return 0.0
        return self.total_cost / self.request_count


class BudgetController:
    """Controls session budgets, tracks per-provider costs, and raises alerts.

    Example::

        controller = BudgetController(session_budget=10.0)
        controller.set_provider_budget("openai", 5.0)
        controller.record_cost("openai", 1.2)
        alerts = controller.check_budgets()
    """

    def __init__(self, session_budget: float = 0.0):
        """Initialize BudgetController.

        Args:
            session_budget: Maximum cost allowed for this session (0 = unlimited).
        """
        self._session_budget = session_budget
        self._session_cost: float = 0.0
        self._provider_budgets: dict[str, float] = {}
        self._provider_records: dict[str, ProviderCostRecord] = {}
        self._alerts: list[BudgetAlert] = []
        self._warning_threshold: float = 0.8  # 80% of budget

    @property
    def session_budget(self) -> float:
        """The maximum session budget (0 = unlimited)."""
        return self._session_budget

    @property
    def session_cost(self) -> float:
        """Total accumulated session cost."""
        return self._session_cost

    @property
    def session_remaining(self) -> float:
        """Remaining budget for this session.

        Returns 0.0 if unlimited budget.
        """
        if self._session_budget == 0.0:
            return 0.0
        remaining = self._session_budget - self._session_cost
        return max(remaining, 0.0)

    @property
    def session_usage_ratio(self) -> float:
        """Fraction of session budget used (0.0 to 1.0).

        Returns 0.0 if budget is unlimited.
        """
        if self._session_budget == 0.0:
            return 0.0
        return min(self._session_cost / self._session_budget, 1.0)

    def set_provider_budget(self, provider: str, budget: float) -> None:
        """Set a per-provider budget cap.

        Args:
            provider: Provider name.
            budget: Maximum cost for this provider.
        """
        self._provider_budgets[provider] = budget

    def get_provider_budget(self, provider: str) -> float:
        """Get the budget cap for a provider.

        Returns 0.0 if no cap is set.
        """
        return self._provider_budgets.get(provider, 0.0)

    def record_cost(self, provider: str, cost: float) -> list[BudgetAlert]:
        """Record a cost against a provider and check budgets.

        Args:
            provider: Provider name.
            cost: Cost to record.

        Returns:
            List of alerts triggered by this recording.
        """
        # Update session cost
        self._session_cost += cost

        # Update provider record
        if provider not in self._provider_records:
            self._provider_records[provider] = ProviderCostRecord(
                provider_name=provider
            )
        self._provider_records[provider].record_request(cost)

        # Check budgets and return any alerts
        return self.check_budgets()

    def record_or_drain(self, provider: str, cost: float) -> list[BudgetAlert]:
        """Record cost and return alerts, but do not double-add.

        Identical to record_cost — kept for symmetrical API.
        """
        return self.record_cost(provider, cost)

    def check_budgets(self) -> list[BudgetAlert]:
        """Check all budgets and return new alerts.

        Returns:
            List of new BudgetAlert instances.
        """
        new_alerts: list[BudgetAlert] = []

        # Check session budget
        if self._session_budget > 0.0:
            ratio = self._session_cost / self._session_budget
            if ratio >= 1.0:
                new_alerts.append(
                    BudgetAlert(
                        level=BudgetAlertLevel.CRITICAL,
                        message=(
                            f"Session budget exhausted: "
                            f"${self._session_cost:.2f} / ${self._session_budget:.2f}"
                        ),
                        current_cost=self._session_cost,
                        threshold=self._session_budget,
                    )
                )
            elif ratio >= self._warning_threshold:
                new_alerts.append(
                    BudgetAlert(
                        level=BudgetAlertLevel.WARNING,
                        message=(
                            f"Session budget approaching limit: "
                            f"{ratio:.0%} used "
                            f"(${self._session_cost:.2f} / ${self._session_budget:.2f})"
                        ),
                        current_cost=self._session_cost,
                        threshold=self._session_budget * self._warning_threshold,
                    )
                )

        # Check per-provider budgets
        for provider, budget in self._provider_budgets.items():
            record = self._provider_records.get(provider)
            if record is None or budget <= 0.0:
                continue
            ratio = record.total_cost / budget
            if ratio >= 1.0:
                new_alerts.append(
                    BudgetAlert(
                        level=BudgetAlertLevel.CRITICAL,
                        message=(
                            f"Provider '{provider}' budget exhausted: "
                            f"${record.total_cost:.2f} / ${budget:.2f}"
                        ),
                        current_cost=record.total_cost,
                        threshold=budget,
                        provider=provider,
                    )
                )
            elif ratio >= self._warning_threshold:
                new_alerts.append(
                    BudgetAlert(
                        level=BudgetAlertLevel.WARNING,
                        message=(
                            f"Provider '{provider}' budget approaching limit: "
                            f"{ratio:.0%} used "
                            f"(${record.total_cost:.2f} / ${budget:.2f})"
                        ),
                        current_cost=record.total_cost,
                        threshold=budget * self._warning_threshold,
                        provider=provider,
                    )
                )

        self._alerts.extend(new_alerts)
        return new_alerts

    def get_alerts(self, level: BudgetAlertLevel | None = None) -> list[BudgetAlert]:
        """Get all alerts, optionally filtered by level.

        Args:
            level: If set, only return alerts at this level.

        Returns:
            List of matching alerts.
        """
        if level is None:
            return list(self._alerts)
        return [a for a in self._alerts if a.level == level]

    def get_provider_records(self) -> dict[str, ProviderCostRecord]:
        """Get all provider cost records."""
        return dict(self._provider_records)

    def reset_session(self) -> None:
        """Reset session costs and alerts, keeping provider budgets."""
        self._session_cost = 0.0
        self._alerts.clear()
        self._provider_records.clear()

    def to_dict(self) -> dict[str, Any]:
        """Serialize controller state to dictionary."""
        return {
            "session_budget": self._session_budget,
            "session_cost": self._session_cost,
            "session_remaining": self.session_remaining,
            "session_usage_ratio": self.session_usage_ratio,
            "provider_budgets": dict(self._provider_budgets),
            "provider_records": {
                p: r.total_cost for p, r in self._provider_records.items()
            },
            "alert_count": len(self._alerts),
        }
