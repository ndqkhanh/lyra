"""Tests for evolution cost meter."""
import pytest
import time
from lyra_cli.evolution.cost_meter import CostMeter, BudgetCap


def test_cost_meter_initialization():
    """Test cost meter initializes with zero costs."""
    meter = CostMeter()

    assert meter.tokens_used == 0
    assert meter.dollars_spent == 0.0
    assert meter.wall_clock_s >= 0.0


def test_add_tokens_without_cost():
    """Test adding tokens without cost tracking."""
    meter = CostMeter()

    meter.add_tokens(1000)

    assert meter.tokens_used == 1000
    assert meter.dollars_spent == 0.0


def test_add_tokens_with_cost():
    """Test adding tokens with cost tracking."""
    meter = CostMeter()

    # Add 1000 tokens at $0.001 per token
    meter.add_tokens(1000, cost_per_token=0.001)

    assert meter.tokens_used == 1000
    assert meter.dollars_spent == 1.0


def test_cost_accumulation():
    """Test that costs accumulate correctly."""
    meter = CostMeter()

    meter.add_tokens(500, cost_per_token=0.001)
    meter.add_tokens(500, cost_per_token=0.001)

    assert meter.tokens_used == 1000
    assert meter.dollars_spent == 1.0


def test_wall_clock_tracking():
    """Test wall clock time tracking."""
    meter = CostMeter()

    # Wait a bit
    time.sleep(0.1)

    meter.update_wall_clock()

    assert meter.wall_clock_s >= 0.1


def test_budget_check_under_limit():
    """Test budget check when under all limits."""
    meter = CostMeter()
    budget = BudgetCap(
        max_tokens=10000,
        max_dollars=10.0,
        max_wall_clock_s=60.0,
    )

    meter.add_tokens(1000, cost_per_token=0.001)

    assert meter.check_budget(budget) is True


def test_budget_check_token_limit_exceeded():
    """Test budget check when token limit exceeded."""
    meter = CostMeter()
    budget = BudgetCap(max_tokens=1000)

    meter.add_tokens(1001)

    assert meter.check_budget(budget) is False


def test_budget_check_dollar_limit_exceeded():
    """Test budget check when dollar limit exceeded."""
    meter = CostMeter()
    budget = BudgetCap(max_dollars=1.0)

    meter.add_tokens(2000, cost_per_token=0.001)

    assert meter.check_budget(budget) is False


def test_budget_check_time_limit_exceeded():
    """Test budget check when time limit exceeded."""
    meter = CostMeter()
    budget = BudgetCap(max_wall_clock_s=0.05)

    time.sleep(0.1)

    assert meter.check_budget(budget) is False


def test_get_stats():
    """Test getting cost statistics."""
    meter = CostMeter()

    meter.add_tokens(1000, cost_per_token=0.001)
    time.sleep(0.1)

    stats = meter.get_stats()

    assert stats["tokens_used"] == 1000
    assert stats["dollars_spent"] == 1.0
    assert stats["wall_clock_s"] >= 0.1


def test_multiple_operations_tracking():
    """Test tracking multiple operations."""
    meter = CostMeter()

    # Simulate multiple operations
    meter.add_tokens(500, cost_per_token=0.001)  # $0.50
    meter.add_tokens(300, cost_per_token=0.002)  # $0.60
    meter.add_tokens(200, cost_per_token=0.001)  # $0.20

    assert meter.tokens_used == 1000
    assert meter.dollars_spent == pytest.approx(1.3, rel=0.01)


def test_budget_cap_none_values():
    """Test budget cap with None values (no limit)."""
    meter = CostMeter()
    budget = BudgetCap()  # All None

    meter.add_tokens(1000000, cost_per_token=0.001)

    # Should pass since no limits set
    assert meter.check_budget(budget) is True


def test_cost_meter_precision():
    """Test cost meter maintains precision for small costs."""
    meter = CostMeter()

    # Add very small costs
    for _ in range(1000):
        meter.add_tokens(1, cost_per_token=0.0001)

    assert meter.tokens_used == 1000
    assert meter.dollars_spent == pytest.approx(0.1, rel=0.01)
