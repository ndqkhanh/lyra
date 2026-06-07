"""Tests for src/economics/budget.py."""
from __future__ import annotations

import pytest

from lyra.economics.budget import BudgetAlertLevel, BudgetController, ProviderCostRecord


class TestProviderCostRecord:
    """Tests for ProviderCostRecord."""

    def test_record_increments(self):
        """Recording a request updates count and cost."""
        record = ProviderCostRecord(provider_name="openai")
        record.record_request(1.5)
        assert record.request_count == 1
        assert record.total_cost == 1.5

    def test_average_cost(self):
        """average_cost returns mean cost per request."""
        record = ProviderCostRecord(provider_name="openai")
        record.record_request(1.0)
        record.record_request(3.0)
        assert record.average_cost == 2.0

    def test_average_cost_zero_requests(self):
        """average_cost is 0 when no requests recorded."""
        record = ProviderCostRecord(provider_name="openai")
        assert record.average_cost == 0.0


class TestBudgetController:
    """Tests for BudgetController."""

    def test_no_budget_unlimited(self):
        """With no budget, usage ratio is 0 and remaining is 0."""
        ctrl = BudgetController(session_budget=0.0)
        assert ctrl.session_budget == 0.0
        assert ctrl.session_usage_ratio == 0.0
        assert ctrl.session_remaining == 0.0

    def test_session_budget_exhaustion(self):
        """Recording cost at or above budget triggers critical alert."""
        ctrl = BudgetController(session_budget=10.0)
        alerts = ctrl.record_cost("openai", 10.0)
        critical = [a for a in alerts if a.level == BudgetAlertLevel.CRITICAL]
        assert len(critical) >= 1
        assert "exhausted" in critical[0].message

    def test_session_budget_warning(self):
        """Recording cost above warning threshold triggers warning."""
        ctrl = BudgetController(session_budget=10.0)
        alerts = ctrl.record_cost("openai", 8.5)
        warnings = [a for a in alerts if a.level == BudgetAlertLevel.WARNING]
        assert len(warnings) >= 1

    def test_provider_budget_exhaustion(self):
        """Per-provider budget exhaustion triggers critical alert."""
        ctrl = BudgetController(session_budget=100.0)
        ctrl.set_provider_budget("anthropic", 5.0)
        alerts = ctrl.record_cost("anthropic", 5.0)
        provider_critical = [
            a
            for a in alerts
            if a.level == BudgetAlertLevel.CRITICAL and a.provider == "anthropic"
        ]
        assert len(provider_critical) >= 1

    def test_reset_session(self):
        """reset_session clears costs and alerts but keeps budgets."""
        ctrl = BudgetController(session_budget=10.0)
        ctrl.set_provider_budget("openai", 5.0)
        ctrl.record_cost("openai", 3.0)
        ctrl.reset_session()
        assert ctrl.session_cost == 0.0
        assert ctrl.get_alerts() == []
        assert ctrl.get_provider_budget("openai") == 5.0

    def test_get_alerts_filtered(self):
        """get_alerts with level filter returns only that level."""
        ctrl = BudgetController(session_budget=10.0)
        ctrl.record_cost("openai", 9.0)  # warning
        ctrl.record_cost("openai", 1.0)  # critical
        criticals = ctrl.get_alerts(BudgetAlertLevel.CRITICAL)
        warnings = ctrl.get_alerts(BudgetAlertLevel.WARNING)
        assert len(criticals) >= 1
        assert len(warnings) >= 1

    def test_to_dict(self):
        """to_dict serialises state."""
        ctrl = BudgetController(session_budget=10.0)
        ctrl.set_provider_budget("openai", 5.0)
        ctrl.record_cost("openai", 2.0)
        d = ctrl.to_dict()
        assert d["session_cost"] == 2.0
        assert d["session_budget"] == 10.0
        assert "openai" in d["provider_records"]
