"""Unit tests for CostMeter and BudgetCap."""
import pytest
from lyra_cli.evolution.cost_meter import CostMeter, BudgetCap


class TestCostMeter:
    """Test cost tracking functionality."""

    def test_initial_state(self):
        """New meter should start at zero."""
        meter = CostMeter()
        assert meter.tokens_used == 0
        assert meter.dollars_spent == 0.0
        assert meter.wall_clock_s == 0.0

    def test_check_budget_under_limit(self):
        """Should pass when under budget."""
        meter = CostMeter()
        meter.tokens_used = 50000
        meter.dollars_spent = 5.0

        cap = BudgetCap(max_dollars=10.0, max_tokens=100000)
        assert meter.check_budget(cap) is True

    def test_check_budget_over_dollars(self):
        """Should fail when over dollar limit."""
        meter = CostMeter()
        meter.dollars_spent = 11.0

        cap = BudgetCap(max_dollars=10.0)
        assert meter.check_budget(cap) is False

    def test_check_budget_over_tokens(self):
        """Should fail when over token limit."""
        meter = CostMeter()
        meter.tokens_used = 150000

        cap = BudgetCap(max_tokens=100000)
        assert meter.check_budget(cap) is False

    def test_check_budget_at_exact_limit(self):
        """Should pass at exact limit."""
        meter = CostMeter()
        meter.tokens_used = 100000
        meter.dollars_spent = 10.0

        cap = BudgetCap(max_dollars=10.0, max_tokens=100000)
        assert meter.check_budget(cap) is True

    def test_check_budget_no_limits(self):
        """Should always pass with no limits."""
        meter = CostMeter()
        meter.tokens_used = 1000000
        meter.dollars_spent = 100.0

        cap = BudgetCap()  # No limits
        assert meter.check_budget(cap) is True

    def test_check_budget_only_dollar_limit(self):
        """Should only check dollar limit if token limit not set."""
        meter = CostMeter()
        meter.tokens_used = 1000000  # High tokens
        meter.dollars_spent = 5.0  # Low dollars

        cap = BudgetCap(max_dollars=10.0)  # Only dollar limit
        assert meter.check_budget(cap) is True

    def test_check_budget_only_token_limit(self):
        """Should only check token limit if dollar limit not set."""
        meter = CostMeter()
        meter.tokens_used = 50000  # Low tokens
        meter.dollars_spent = 100.0  # High dollars

        cap = BudgetCap(max_tokens=100000)  # Only token limit
        assert meter.check_budget(cap) is True

    def test_accumulate_tokens(self):
        """Should accumulate tokens over multiple operations."""
        meter = CostMeter()
        meter.tokens_used += 10000
        meter.tokens_used += 20000
        meter.tokens_used += 30000

        assert meter.tokens_used == 60000

    def test_accumulate_dollars(self):
        """Should accumulate dollars over multiple operations."""
        meter = CostMeter()
        meter.dollars_spent += 1.5
        meter.dollars_spent += 2.5
        meter.dollars_spent += 3.0

        assert meter.dollars_spent == 7.0

    def test_wall_clock_tracking(self):
        """Should track wall clock time."""
        meter = CostMeter()
        meter.wall_clock_s = 120.5

        assert meter.wall_clock_s == 120.5


class TestBudgetCap:
    """Test budget cap configuration."""

    def test_default_budget_cap(self):
        """Default cap should have no limits."""
        cap = BudgetCap()
        assert cap.max_dollars is None
        assert cap.max_tokens is None

    def test_dollar_only_cap(self):
        """Can create cap with only dollar limit."""
        cap = BudgetCap(max_dollars=10.0)
        assert cap.max_dollars == 10.0
        assert cap.max_tokens is None

    def test_token_only_cap(self):
        """Can create cap with only token limit."""
        cap = BudgetCap(max_tokens=100000)
        assert cap.max_tokens == 100000
        assert cap.max_dollars is None

    def test_both_limits_cap(self):
        """Can create cap with both limits."""
        cap = BudgetCap(max_dollars=10.0, max_tokens=100000)
        assert cap.max_dollars == 10.0
        assert cap.max_tokens == 100000

    def test_zero_limits(self):
        """Zero limits should be valid."""
        cap = BudgetCap(max_dollars=0.0, max_tokens=0)
        assert cap.max_dollars == 0.0
        assert cap.max_tokens == 0

        # Meter with any usage should exceed
        meter = CostMeter()
        meter.tokens_used = 1
        meter.dollars_spent = 0.01
        assert meter.check_budget(cap) is False
