"""Tests for harness_core.evals — equal_budget, ttc_curve, active_params."""
from __future__ import annotations

import pytest

from harness_core.evals import (
    ActiveParamAccount,
    ActiveParamReading,
    BudgetController,
    BudgetExhausted,
    TTCCurve,
    TTCPoint,
)


class TestBudgetController:
    def test_consume_within_budget(self):
        ctrl = BudgetController(budget_tokens=1000)
        assert ctrl.consume(400) == 600
        assert ctrl.consume(300) == 300
        assert ctrl.remaining() == 300

    def test_consume_exhausts(self):
        ctrl = BudgetController(budget_tokens=100)
        ctrl.consume(80)
        with pytest.raises(BudgetExhausted) as exc:
            ctrl.consume(50)
        assert "20 remain" in str(exc.value)

    def test_negative_consumption_rejected(self):
        ctrl = BudgetController(budget_tokens=100)
        with pytest.raises(ValueError):
            ctrl.consume(-1)

    def test_reserve_returns_bool(self):
        ctrl = BudgetController(budget_tokens=100)
        assert ctrl.reserve(60) is True
        assert ctrl.reserve(50) is False
        assert ctrl.remaining() == 40

    def test_reset(self):
        ctrl = BudgetController(budget_tokens=100)
        ctrl.consume(50)
        ctrl.reset()
        assert ctrl.remaining() == 100

    def test_fraction_used(self):
        ctrl = BudgetController(budget_tokens=100)
        ctrl.consume(25)
        assert ctrl.fraction_used == 0.25

    def test_zero_budget_fraction(self):
        ctrl = BudgetController(budget_tokens=0)
        assert ctrl.fraction_used == 1.0  # treat as fully used

    def test_label_in_error(self):
        ctrl = BudgetController(budget_tokens=10)
        with pytest.raises(BudgetExhausted) as exc:
            ctrl.consume(100, label="planner")
        assert "planner" in str(exc.value)


class TestTTCPoint:
    def test_valid(self):
        p = TTCPoint(budget_tokens=100, accuracy=0.5, label="a")
        assert p.budget_tokens == 100

    def test_invalid_accuracy(self):
        with pytest.raises(ValueError):
            TTCPoint(budget_tokens=100, accuracy=1.5)
        with pytest.raises(ValueError):
            TTCPoint(budget_tokens=100, accuracy=-0.1)

    def test_invalid_budget(self):
        with pytest.raises(ValueError):
            TTCPoint(budget_tokens=-1, accuracy=0.5)


class TestTTCCurve:
    def test_add_and_sort(self):
        curve = TTCCurve()
        curve.add(budget_tokens=300, accuracy=0.7)
        curve.add(budget_tokens=100, accuracy=0.5)
        curve.add(budget_tokens=200, accuracy=0.6)
        sorted_pts = curve.sorted_points()
        assert [p.budget_tokens for p in sorted_pts] == [100, 200, 300]

    def test_inflection_when_plateaus(self):
        curve = TTCCurve()
        # Rising then plateau
        curve.add(budget_tokens=100, accuracy=0.5)
        curve.add(budget_tokens=200, accuracy=0.7)
        curve.add(budget_tokens=300, accuracy=0.71)
        curve.add(budget_tokens=400, accuracy=0.71)
        inflection = curve.find_inflection(epsilon=0.05, window=2)
        assert inflection is not None
        assert inflection.budget_tokens == 200

    def test_no_inflection_still_rising(self):
        curve = TTCCurve()
        curve.add(budget_tokens=100, accuracy=0.3)
        curve.add(budget_tokens=200, accuracy=0.5)
        curve.add(budget_tokens=300, accuracy=0.7)
        # Last point — no future window
        inflection = curve.find_inflection(epsilon=0.01, window=2)
        assert inflection is None

    def test_decline_detected(self):
        curve = TTCCurve()
        curve.add(budget_tokens=100, accuracy=0.5)
        curve.add(budget_tokens=200, accuracy=0.7)
        curve.add(budget_tokens=300, accuracy=0.6)  # SealQA-style decline
        first_decline = curve.find_decline()
        assert first_decline is not None
        assert first_decline.budget_tokens == 200

    def test_no_decline(self):
        curve = TTCCurve()
        curve.add(budget_tokens=100, accuracy=0.5)
        curve.add(budget_tokens=200, accuracy=0.6)
        curve.add(budget_tokens=300, accuracy=0.7)
        assert curve.find_decline() is None

    def test_csv(self):
        curve = TTCCurve()
        curve.add(budget_tokens=100, accuracy=0.5, label="run-a")
        out = curve.to_csv()
        assert "budget_tokens,accuracy,label" in out
        assert "100,0.500000,run-a" in out


class TestActiveParamReading:
    def test_valid(self):
        r = ActiveParamReading(total_params=47_000_000_000, active_params=12_900_000_000, n_tokens=1000)
        assert r.active_param_token_cost == 12_900_000_000 * 1000

    def test_total_below_active_rejected(self):
        with pytest.raises(ValueError):
            ActiveParamReading(total_params=10, active_params=20, n_tokens=100)

    def test_negative_tokens(self):
        with pytest.raises(ValueError):
            ActiveParamReading(total_params=10, active_params=10, n_tokens=-1)


class TestActiveParamAccount:
    def test_record_and_total(self):
        acc = ActiveParamAccount()
        acc.record(ActiveParamReading(total_params=100, active_params=50, n_tokens=10))
        acc.record(ActiveParamReading(total_params=100, active_params=50, n_tokens=20))
        assert acc.total_active_cost() == 50 * 10 + 50 * 20

    def test_cost_per_grade(self):
        acc = ActiveParamAccount()
        acc.record(ActiveParamReading(total_params=100, active_params=50, n_tokens=10))
        cpg = acc.cost_per_grade(accuracy_delta=0.1)
        assert cpg == (50 * 10) / 0.1

    def test_cost_per_grade_zero_delta_rejected(self):
        acc = ActiveParamAccount()
        acc.record(ActiveParamReading(total_params=100, active_params=50, n_tokens=10))
        with pytest.raises(ValueError):
            acc.cost_per_grade(accuracy_delta=0.0)
        with pytest.raises(ValueError):
            acc.cost_per_grade(accuracy_delta=-0.1)

    def test_moe_savings_dense(self):
        # Dense model: total = active, no savings
        acc = ActiveParamAccount()
        acc.record(ActiveParamReading(total_params=70, active_params=70, n_tokens=100))
        assert acc.moe_savings_ratio() == 0.0

    def test_moe_savings_sparse(self):
        # Mixtral 8x7B: total ~47B, active ~13B → ~72% savings
        acc = ActiveParamAccount()
        acc.record(ActiveParamReading(total_params=47, active_params=13, n_tokens=100))
        ratio = acc.moe_savings_ratio()
        assert 0.7 < ratio < 0.75

    def test_empty_savings_zero(self):
        acc = ActiveParamAccount()
        assert acc.moe_savings_ratio() == 0.0
