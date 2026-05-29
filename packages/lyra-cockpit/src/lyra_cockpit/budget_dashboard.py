"""Budget dashboard — cost tracking and budget management.

Tracks per-category costs, computes daily/monthly budget reports,
and generates alerts when spending exceeds configured thresholds.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass

from .exceptions import BudgetError


@dataclass(frozen=True)
class BudgetConfig:
    """Configuration for budget management.

    Attributes:
        daily_limit: Maximum daily spend in USD.
        monthly_limit: Maximum monthly spend in USD.
        alert_threshold: Fraction of limit at which alerts fire (0.0 to 1.0).
        currency: Currency string (e.g., "USD").
    """

    daily_limit: float = 50.0
    monthly_limit: float = 1000.0
    alert_threshold: float = 0.8
    currency: str = "USD"


@dataclass(frozen=True)
class CostEntry:
    """A single cost entry record.

    Attributes:
        entry_id: Unique identifier for this cost entry.
        category: Cost category (e.g., "inference", "storage").
        amount: Cost amount in the configured currency.
        model: Model identifier (e.g., "claude-sonnet-4").
        token_count: Number of tokens consumed.
        timestamp: Unix timestamp when the cost was incurred.
    """

    entry_id: str
    category: str
    amount: float
    model: str
    token_count: int
    timestamp: float


@dataclass(frozen=True)
class BudgetReport:
    """A budget report summarising current spend.

    Attributes:
        daily_spend: Total spend today.
        monthly_spend: Total spend this month.
        remaining_daily: Remaining daily budget.
        remaining_monthly: Remaining monthly budget.
        projected_monthly: Projected end-of-month spend.
        alerts: Tuple of alert messages.
    """

    daily_spend: float
    monthly_spend: float
    remaining_daily: float
    remaining_monthly: float
    projected_monthly: float
    alerts: tuple[str, ...]


class BudgetDashboard:
    """Cost tracking and budget management dashboard.

    Records cost entries, computes budget reports, and generates alerts
    when spending approaches configured limits.
    """

    def __init__(self, config: BudgetConfig | None = None) -> None:
        """Initialise the budget dashboard.

        Args:
            config: Optional budget configuration. Uses defaults if
                not provided.
        """
        self._config = config or BudgetConfig()
        self._entries: list[CostEntry] = []

    @property
    def config(self) -> BudgetConfig:
        """Return the budget configuration."""
        return self._config

    async def record_cost(self, category: str, amount: float, model: str, tokens: int) -> str:
        """Record a new cost entry.

        Args:
            category: Cost category (e.g., "inference").
            amount: Cost amount.
            model: Model identifier.
            tokens: Number of tokens consumed.

        Returns:
            The entry_id of the recorded cost entry.

        Raises:
            BudgetError: If category is empty or amount is negative.
        """
        if not category or not category.strip():
            raise BudgetError("Category cannot be empty")
        if amount < 0:
            raise BudgetError("Amount cannot be negative")

        entry_id = f"cost-{uuid.uuid4().hex[:12]}"
        entry = CostEntry(
            entry_id=entry_id,
            category=category.strip(),
            amount=amount,
            model=model,
            token_count=tokens,
            timestamp=time.time(),
        )
        self._entries.append(entry)
        return entry_id

    async def get_current_report(self) -> BudgetReport:
        """Compute and return the current budget report.

        Returns:
            A BudgetReport with daily/monthly spend, remaining budgets,
            projections, and alerts.
        """
        now = time.time()
        day_start = now - (now % 86400)
        month_start = now - (now % (86400 * 30))

        daily_spend = sum(e.amount for e in self._entries if e.timestamp >= day_start)
        monthly_spend = sum(e.amount for e in self._entries if e.timestamp >= month_start)

        remaining_daily = max(0.0, self._config.daily_limit - daily_spend)
        remaining_monthly = max(0.0, self._config.monthly_limit - monthly_spend)

        # Projected monthly based on daily rate
        hours_elapsed = (now - month_start) / 3600
        projected = monthly_spend
        if hours_elapsed > 1:
            projected = (monthly_spend / hours_elapsed) * (30 * 24)

        alerts_list: list[str] = []
        if daily_spend >= self._config.daily_limit:
            alerts_list.append(
                f"Daily limit of {self._config.currency} {self._config.daily_limit} exceeded"
            )
        elif daily_spend >= self._config.daily_limit * self._config.alert_threshold:
            alerts_list.append(

                    f"Daily spend at {daily_spend / self._config.daily_limit:.0%}"
                    f" of limit (threshold: {self._config.alert_threshold:.0%})"

            )

        if monthly_spend >= self._config.monthly_limit:
            alerts_list.append(
                f"Monthly limit of {self._config.currency} {self._config.monthly_limit} exceeded"
            )
        elif monthly_spend >= self._config.monthly_limit * self._config.alert_threshold:
            alerts_list.append(

                    f"Monthly spend at {monthly_spend / self._config.monthly_limit:.0%}"
                    f" of limit (threshold: {self._config.alert_threshold:.0%})"

            )

        return BudgetReport(
            daily_spend=daily_spend,
            monthly_spend=monthly_spend,
            remaining_daily=remaining_daily,
            remaining_monthly=remaining_monthly,
            projected_monthly=projected,
            alerts=tuple(alerts_list),
        )

    async def get_cost_history(self, hours: int = 24) -> tuple[CostEntry, ...]:
        """Get cost entries from the last N hours.

        Args:
            hours: Number of hours to look back.

        Returns:
            A tuple of CostEntry instances from the specified period.
        """
        cutoff = time.time() - (hours * 3600)
        return tuple(e for e in self._entries if e.timestamp >= cutoff)
