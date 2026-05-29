"""Tests for CircuitBreaker, LoopDetector, and BudgetDegrader."""

from __future__ import annotations

from lyra_cost import BudgetDegrader, CircuitBreaker, LoopDetector, ModelTier


class TestCircuitBreaker:
    """Tests for the CircuitBreaker safeguard."""

    def test_initial_state(self) -> None:
        cb = CircuitBreaker(limit=5.0)
        assert cb.limit == 5.0
        assert cb.total_spent == 0.0
        assert cb.call_count == 0
        assert not cb.is_open
        assert not cb.check()

    def test_record_spend_below_limit(self) -> None:
        cb = CircuitBreaker(limit=10.0)
        cb.record_spend(2.0)
        assert not cb.is_open
        assert cb.total_spent == 2.0
        assert cb.call_count == 1

    def test_record_spend_triggers_breaker(self) -> None:
        cb = CircuitBreaker(limit=5.0)
        cb.record_spend(5.0)
        assert cb.is_open
        assert cb.check()

    def test_record_spend_exceeds_limit(self) -> None:
        cb = CircuitBreaker(limit=5.0)
        cb.record_spend(6.0)
        assert cb.is_open

    def test_multiple_records_cumulative(self) -> None:
        cb = CircuitBreaker(limit=5.0)
        cb.record_spend(2.0)
        cb.record_spend(2.0)
        assert not cb.is_open
        cb.record_spend(2.0)
        assert cb.is_open
        assert cb.total_spent == 6.0
        assert cb.call_count == 3

    def test_reset(self) -> None:
        cb = CircuitBreaker(limit=5.0)
        cb.record_spend(5.0)
        assert cb.is_open
        cb.reset()
        assert not cb.is_open
        assert cb.total_spent == 0.0
        assert cb.call_count == 0

    def test_state_dict(self) -> None:
        cb = CircuitBreaker(limit=5.0)
        cb.record_spend(3.0)
        state = cb.state
        assert state["is_open"] is False
        assert state["total_spent"] == 3.0
        assert state["call_count"] == 1
        assert state["limit"] == 5.0

    def test_zero_limit_triggers_immediately(self) -> None:
        cb = CircuitBreaker(limit=0.0)
        cb.record_spend(0.01)
        assert cb.is_open


class TestLoopDetector:
    """Tests for the LoopDetector safeguard."""

    def test_initial_state(self) -> None:
        ld = LoopDetector(consecutive_low_limit=3)
        assert not ld.blocked_tasks

    def test_single_good_score(self) -> None:
        ld = LoopDetector()
        result = ld.record_score("coding", 0.8)
        assert not result.blocked
        assert result.consecutive_low == 0

    def test_single_low_score(self) -> None:
        ld = LoopDetector(consecutive_low_limit=3)
        result = ld.record_score("coding", 0.2)
        assert not result.blocked
        assert result.consecutive_low == 1

    def test_consecutive_low_scores_block(self) -> None:
        ld = LoopDetector(consecutive_low_limit=3)
        ld.record_score("coding", 0.2)  # 1
        ld.record_score("coding", 0.1)  # 2
        result = ld.record_score("coding", 0.15)  # 3 -> blocked
        assert result.blocked
        assert result.consecutive_low == 3
        assert ld.is_blocked("coding")
        assert "coding" in ld.blocked_tasks

    def test_good_score_resets_counter(self) -> None:
        ld = LoopDetector(consecutive_low_limit=3)
        ld.record_score("coding", 0.2)  # 1
        ld.record_score("coding", 0.1)  # 2
        ld.record_score("coding", 0.8)  # resets
        result = ld.record_score("coding", 0.2)  # back to 1
        assert not result.blocked
        assert result.consecutive_low == 1

    def test_different_task_types_independent(self) -> None:
        ld = LoopDetector(consecutive_low_limit=3)
        for _ in range(3):
            ld.record_score("coding", 0.2)
        assert ld.is_blocked("coding")
        assert not ld.is_blocked("analysis")

        ld.record_score("analysis", 0.2)
        assert not ld.is_blocked("analysis")

    def test_unblock_task(self) -> None:
        ld = LoopDetector(consecutive_low_limit=3)
        for _ in range(3):
            ld.record_score("coding", 0.2)
        assert ld.is_blocked("coding")

        ld.unblock("coding")
        assert not ld.is_blocked("coding")
        # After unblock, scoring again should start fresh
        result = ld.record_score("coding", 0.2)
        assert result.consecutive_low == 1
        assert not result.blocked

    def test_reset(self) -> None:
        ld = LoopDetector(consecutive_low_limit=3)
        for _ in range(3):
            ld.record_score("coding", 0.2)
        assert ld.is_blocked("coding")
        ld.reset()
        assert not ld.blocked_tasks
        assert not ld.is_blocked("coding")

    def test_quality_score_normalisation(self) -> None:
        ld = LoopDetector(consecutive_low_limit=3)
        # Score passed directly in 0-1 range (value <= 0.3 is low)
        ld.record_score("test", 0.2)  # normalised remains 0.2 (low)
        ld.record_score("test", 0.1)  # normalised remains 0.1 (low)
        result = ld.record_score("test", 0.15)  # 3 consecutive low -> blocked
        assert result.blocked

    def test_state_dict(self) -> None:
        ld = LoopDetector(consecutive_low_limit=3)
        ld.record_score("coding", 0.2)
        state = ld.state
        assert state["consecutive_low_limit"] == 3
        assert "coding" in state["tracked_task_types"]


class TestBudgetDegrader:
    """Tests for the BudgetDegrader safeguard."""

    def test_no_degradation_at_low_spend(self) -> None:
        d = BudgetDegrader(circuit_breaker_limit=10.0)
        assert d.degrade(ModelTier.TIER_3, 0.0) == ModelTier.TIER_3
        assert d.degrade(ModelTier.TIER_2, 1.0) == ModelTier.TIER_2

    def test_degrade_one_level_at_25_percent(self) -> None:
        d = BudgetDegrader(circuit_breaker_limit=10.0)
        assert d.degrade(ModelTier.TIER_3, 2.5) == ModelTier.TIER_2
        assert d.degrade(ModelTier.TIER_2, 2.5) == ModelTier.TIER_1

    def test_degrade_two_levels_at_50_percent(self) -> None:
        d = BudgetDegrader(circuit_breaker_limit=10.0)
        assert d.degrade(ModelTier.TIER_3, 5.0) == ModelTier.TIER_1
        assert d.degrade(ModelTier.TIER_2, 5.0) == ModelTier.TIER_0

    def test_degrade_to_minimum_at_75_percent(self) -> None:
        d = BudgetDegrader(circuit_breaker_limit=10.0)
        assert d.degrade(ModelTier.TIER_3, 7.5) == ModelTier.TIER_0
        assert d.degrade(ModelTier.TIER_0, 7.5) == ModelTier.TIER_0

    def test_max_allowed_tier(self) -> None:
        d = BudgetDegrader(circuit_breaker_limit=10.0)
        assert d.max_allowed_tier(0.0) == ModelTier.TIER_3
        assert d.max_allowed_tier(2.5) == ModelTier.TIER_2
        assert d.max_allowed_tier(5.0) == ModelTier.TIER_1
        assert d.max_allowed_tier(7.5) == ModelTier.TIER_0

    def test_can_afford(self) -> None:
        d = BudgetDegrader(circuit_breaker_limit=10.0)
        assert d.can_afford(ModelTier.TIER_3, 0.0)
        assert d.can_afford(ModelTier.TIER_2, 2.5)
        assert not d.can_afford(ModelTier.TIER_3, 2.5)
        assert d.can_afford(ModelTier.TIER_0, 10.0)
        assert not d.can_afford(ModelTier.TIER_1, 10.0)

    def test_zero_limit(self) -> None:
        d = BudgetDegrader(circuit_breaker_limit=0.0)
        # With zero limit, any spend >= 0 means 100% fraction -> degrade to TIER_0
        assert d.degrade(ModelTier.TIER_3, 0.0) == ModelTier.TIER_0

    def test_state_dict(self) -> None:
        d = BudgetDegrader(circuit_breaker_limit=5.0)
        assert d.state["circuit_breaker_limit"] == 5.0

    def test_reset_no_error(self) -> None:
        d = BudgetDegrader()
        d.reset()  # no-op, should not raise
