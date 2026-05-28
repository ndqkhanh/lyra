"""Tests for the budget manager."""

from __future__ import annotations

from pathlib import Path

import pytest

from lyra_cli.autonomy.budget_manager import (
    BudgetExceededError,
    BudgetManager,
    CostEntry,
)


class TestBudgetManager:
    """Suite: BudgetManager cost tracking and limit enforcement."""

    def test_record_usage_creates_entry(self, tmp_path: Path) -> None:
        mgr = BudgetManager(data_dir=tmp_path)
        entry = mgr.record_usage(
            model="claude-opus-4",
            prompt_tokens=100,
            completion_tokens=50,
            cost_usd=0.015,
        )
        assert entry.model == "claude-opus-4"
        assert entry.prompt_tokens == 100
        assert entry.completion_tokens == 50
        assert entry.cost_usd == 0.015
        assert entry.total_tokens == 150

    def test_summary_after_recordings(self, tmp_path: Path) -> None:
        mgr = BudgetManager(data_dir=tmp_path)
        mgr.record_usage(model="model-a", prompt_tokens=100, cost_usd=0.01)
        mgr.record_usage(model="model-b", completion_tokens=200, cost_usd=0.02)

        summary = mgr.summary()
        assert summary.total_cost_usd == 0.03
        assert summary.total_tokens == 300
        assert summary.entry_count == 2

    def test_check_limits_passes_when_under(self, tmp_path: Path) -> None:
        mgr = BudgetManager(
            data_dir=tmp_path,
            daily_limit_usd=100.0,
            monthly_limit_usd=1000.0,
        )
        mgr.record_usage(model="test", cost_usd=1.0)
        # Should not raise
        mgr.check_limits()

    def test_check_limits_raises_when_daily_exceeded(self, tmp_path: Path) -> None:
        mgr = BudgetManager(
            data_dir=tmp_path,
            daily_limit_usd=0.01,
            monthly_limit_usd=1000.0,
        )
        mgr.record_usage(model="test", cost_usd=0.02)
        with pytest.raises(BudgetExceededError, match="Daily"):
            mgr.check_limits()

    def test_check_limits_raises_when_monthly_exceeded(self, tmp_path: Path) -> None:
        mgr = BudgetManager(
            data_dir=tmp_path,
            daily_limit_usd=1000.0,
            monthly_limit_usd=0.01,
        )
        mgr.record_usage(model="test", cost_usd=0.02)
        with pytest.raises(BudgetExceededError, match="Monthly"):
            mgr.check_limits()

    def test_reset_daily_clears_today(self, tmp_path: Path) -> None:
        mgr = BudgetManager(data_dir=tmp_path)
        mgr.record_usage(model="test", cost_usd=0.10)
        removed = mgr.reset_daily()
        assert removed >= 1
        summary = mgr.summary()
        assert summary.daily_cost_usd == 0.0

    def test_summary_degraded_flag(self, tmp_path: Path) -> None:
        """Degraded should be True when daily exceeds warning threshold."""
        mgr = BudgetManager(
            data_dir=tmp_path,
            daily_limit_usd=10.0,
            warning_threshold=0.5,
        )
        mgr.record_usage(model="test", cost_usd=6.0)  # 60% of daily
        summary = mgr.summary()
        assert summary.degraded is True

    def test_persistence_survives_reload(self, tmp_path: Path) -> None:
        mgr1 = BudgetManager(data_dir=tmp_path)
        mgr1.record_usage(model="persist-test", cost_usd=0.05)

        mgr2 = BudgetManager(data_dir=tmp_path)
        summary = mgr2.summary()
        assert summary.entry_count >= 1
        assert summary.total_cost_usd >= 0.05

    def test_cost_entry_total_tokens(self) -> None:
        entry = CostEntry(
            timestamp="2025-01-01T00:00:00",
            model="test",
            prompt_tokens=10,
            completion_tokens=20,
        )
        assert entry.total_tokens == 30
