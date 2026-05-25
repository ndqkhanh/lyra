"""Tests for the budget dashboard module."""

from __future__ import annotations

import pytest

from lyra_cockpit.budget_dashboard import (
    BudgetConfig,
    BudgetDashboard,
    BudgetReport,
    CostEntry,
)
from lyra_cockpit.exceptions import BudgetError


class TestBudgetConfig:
    def test_default_values(self) -> None:
        config = BudgetConfig()
        assert config.daily_limit == 50.0
        assert config.monthly_limit == 1000.0
        assert config.alert_threshold == 0.8
        assert config.currency == "USD"

    def test_custom_values(self) -> None:
        config = BudgetConfig(daily_limit=100.0, monthly_limit=2000.0, alert_threshold=0.9, currency="EUR")
        assert config.daily_limit == 100.0
        assert config.monthly_limit == 2000.0
        assert config.alert_threshold == 0.9
        assert config.currency == "EUR"


class TestCostEntry:
    def test_creation(self) -> None:
        entry = CostEntry(
            entry_id="cost-001",
            category="inference",
            amount=0.025,
            model="claude-sonnet-4",
            token_count=15000,
            timestamp=1000.0,
        )
        assert entry.entry_id == "cost-001"
        assert entry.category == "inference"
        assert entry.amount == 0.025
        assert entry.model == "claude-sonnet-4"

    def test_frozen(self) -> None:
        entry = CostEntry("c1", "cat", 0.0, "m", 0, 0.0)
        with pytest.raises(AttributeError):
            entry.amount = 1.0  # type: ignore[misc]


class TestBudgetReport:
    def test_creation(self) -> None:
        report = BudgetReport(
            daily_spend=25.0,
            monthly_spend=500.0,
            remaining_daily=25.0,
            remaining_monthly=500.0,
            projected_monthly=750.0,
            alerts=("Daily spend at 50% of limit",),
        )
        assert report.daily_spend == 25.0
        assert report.monthly_spend == 500.0
        assert report.remaining_daily == 25.0
        assert report.projected_monthly == 750.0

    def test_empty_alerts(self) -> None:
        report = BudgetReport(0.0, 0.0, 50.0, 1000.0, 0.0, alerts=())
        assert report.alerts == ()

    def test_frozen(self) -> None:
        report = BudgetReport(0.0, 0.0, 0.0, 0.0, 0.0, ())
        with pytest.raises(AttributeError):
            report.daily_spend = 100.0  # type: ignore[misc]


class TestBudgetDashboard:
    @pytest.mark.asyncio
    async def test_record_cost(self) -> None:
        dashboard = BudgetDashboard()
        entry_id = await dashboard.record_cost("inference", 0.025, "claude-sonnet-4", 15000)
        assert entry_id.startswith("cost-")

    @pytest.mark.asyncio
    async def test_record_cost_empty_category_raises(self) -> None:
        dashboard = BudgetDashboard()
        with pytest.raises(BudgetError, match="cannot be empty"):
            await dashboard.record_cost("", 1.0, "model", 100)

    @pytest.mark.asyncio
    async def test_record_cost_negative_amount_raises(self) -> None:
        dashboard = BudgetDashboard()
        with pytest.raises(BudgetError, match="cannot be negative"):
            await dashboard.record_cost("inference", -1.0, "model", 100)

    @pytest.mark.asyncio
    async def test_get_current_report_empty(self) -> None:
        dashboard = BudgetDashboard()
        report = await dashboard.get_current_report()
        assert report.daily_spend == 0.0
        assert report.monthly_spend == 0.0
        assert report.alerts == ()

    @pytest.mark.asyncio
    async def test_get_current_report_with_spend(self) -> None:
        dashboard = BudgetDashboard()
        await dashboard.record_cost("inference", 10.0, "sonnet", 5000)
        report = await dashboard.get_current_report()
        assert report.daily_spend == 10.0
        assert report.remaining_daily == 40.0

    @pytest.mark.asyncio
    async def test_daily_exceeded_alert(self) -> None:
        config = BudgetConfig(daily_limit=5.0)
        dashboard = BudgetDashboard(config)
        await dashboard.record_cost("inference", 6.0, "sonnet", 5000)
        report = await dashboard.get_current_report()
        assert len(report.alerts) >= 1
        assert "exceeded" in report.alerts[0]

    @pytest.mark.asyncio
    async def test_daily_threshold_alert(self) -> None:
        config = BudgetConfig(daily_limit=100.0, alert_threshold=0.5)
        dashboard = BudgetDashboard(config)
        await dashboard.record_cost("inference", 60.0, "sonnet", 5000)
        report = await dashboard.get_current_report()
        assert len(report.alerts) >= 1
        assert "threshold" in report.alerts[0]

    @pytest.mark.asyncio
    async def test_monthly_exceeded_alert(self) -> None:
        config = BudgetConfig(monthly_limit=10.0)
        dashboard = BudgetDashboard(config)
        await dashboard.record_cost("inference", 15.0, "sonnet", 5000)
        report = await dashboard.get_current_report()
        assert any("Monthly limit" in a for a in report.alerts)

    @pytest.mark.asyncio
    async def test_monthly_threshold_alert(self) -> None:
        config = BudgetConfig(monthly_limit=100.0, alert_threshold=0.5)
        dashboard = BudgetDashboard(config)
        await dashboard.record_cost("inference", 60.0, "sonnet", 5000)
        report = await dashboard.get_current_report()
        assert any("Monthly spend" in a for a in report.alerts)

    @pytest.mark.asyncio
    async def test_get_cost_history_empty(self) -> None:
        dashboard = BudgetDashboard()
        history = await dashboard.get_cost_history(hours=24)
        assert history == ()

    @pytest.mark.asyncio
    async def test_get_cost_history_with_entries(self) -> None:
        dashboard = BudgetDashboard()
        await dashboard.record_cost("inference", 0.025, "sonnet", 1000)
        await dashboard.record_cost("storage", 0.01, "haiku", 500)
        history = await dashboard.get_cost_history(hours=24)
        assert len(history) == 2

    @pytest.mark.asyncio
    async def test_config_property(self) -> None:
        config = BudgetConfig(daily_limit=200.0)
        dashboard = BudgetDashboard(config)
        assert dashboard.config.daily_limit == 200.0

    @pytest.mark.asyncio
    async def test_multiple_categories(self) -> None:
        dashboard = BudgetDashboard()
        await dashboard.record_cost("inference", 5.0, "sonnet", 3000)
        await dashboard.record_cost("embedding", 2.0, "haiku", 10000)
        report = await dashboard.get_current_report()
        assert report.daily_spend == 7.0

    @pytest.mark.asyncio
    async def test_projected_monthly(self) -> None:
        dashboard = BudgetDashboard()
        await dashboard.record_cost("inference", 30.0, "sonnet", 15000)
        report = await dashboard.get_current_report()
        # Should have some projection
        assert report.projected_monthly > 0.0
