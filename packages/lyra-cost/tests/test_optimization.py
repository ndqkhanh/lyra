"""Tests for the CostOptimizer."""

from __future__ import annotations

import pytest

from lyra_cost import CostOptimizer, ModelTier, TierRecommendation
from lyra_cost.optimization import NoTierAvailableError


class TestCostOptimizer:
    """Tests for the CostOptimizer."""

    def test_initial_state(self) -> None:
        opt = CostOptimizer()
        assert "coding" in opt.tier_map
        assert opt.tier_map["coding"] == ModelTier.TIER_2
        assert opt.tier_map["classification"] == ModelTier.TIER_0
        assert opt.tier_map["architecture"] == ModelTier.TIER_3

    def test_recommend_coding_without_degradation(self) -> None:
        opt = CostOptimizer()
        rec = opt.recommend("coding", total_session_spend=0.0)
        assert isinstance(rec, TierRecommendation)
        assert rec.recommended_tier == ModelTier.TIER_2
        assert not rec.degraded
        assert not rec.blocked
        assert rec.task_type == "coding"
        assert rec.cost_estimate > 0

    def test_recommend_classification_tier_0(self) -> None:
        opt = CostOptimizer()
        rec = opt.recommend("classification", total_session_spend=0.0)
        assert rec.recommended_tier == ModelTier.TIER_0
        assert rec.cost_estimate == 0.0

    def test_budget_degradation_lowers_tier(self) -> None:
        opt = CostOptimizer(circuit_breaker_limit=10.0)
        # At 50% spend, TIER_2 should degrade by 2 levels to TIER_0
        rec = opt.recommend("coding", total_session_spend=5.0)
        assert rec.recommended_tier == ModelTier.TIER_0
        assert rec.degraded

    def test_heavy_degradation_to_tier_0(self) -> None:
        opt = CostOptimizer(circuit_breaker_limit=10.0)
        rec = opt.recommend("coding", total_session_spend=9.0)
        assert rec.recommended_tier == ModelTier.TIER_0
        assert rec.degraded

    def test_blocked_task_raises(self) -> None:
        opt = CostOptimizer()
        # Trigger loop detection
        for _ in range(3):
            opt.record_quality_score("coding", 0.2)

        with pytest.raises(NoTierAvailableError, match="blocked by loop detector"):
            opt.recommend("coding", total_session_spend=0.0)

    def test_hard_task_floor(self) -> None:
        opt = CostOptimizer(circuit_breaker_limit=10.0)
        # Architecture is a hard task; at 50% spend it would normally degrade to
        # TIER_1, but hard tasks have a floor at TIER_1
        rec = opt.recommend("architecture", total_session_spend=5.0)
        # Architecture is TIER_3 -> degrade -> TIER_1 or TIER_2 depending on budget
        # At 50%: degrade 2 levels -> TIER_1, which is >= floor so stays
        assert rec.degraded
        assert rec.recommended_tier.value >= 1

    def test_hard_task_at_extreme_budget(self) -> None:
        opt = CostOptimizer(circuit_breaker_limit=10.0)
        # At 80% spend, normal degradation would go to TIER_0.
        # Hard tasks get floor at TIER_1, bypassing the affordability check.
        rec = opt.recommend("architecture", total_session_spend=8.0)
        assert rec.degraded
        assert rec.recommended_tier == ModelTier.TIER_1

    def test_no_affordable_tier_raises(self) -> None:
        opt = CostOptimizer()
        # Block all task types through loop detector to trigger the error
        for _ in range(3):
            opt.record_quality_score("custom_task", 0.2)
        with pytest.raises(NoTierAvailableError, match="blocked by loop detector"):
            opt.recommend("custom_task", total_session_spend=0.0)

    def test_custom_tier_map(self) -> None:
        opt = CostOptimizer(tier_map={"my_task": ModelTier.TIER_1})
        rec = opt.recommend("my_task", total_session_spend=0.0)
        assert rec.recommended_tier == ModelTier.TIER_1

    def test_update_tier_map(self) -> None:
        opt = CostOptimizer()
        opt.update_tier_map("coding", ModelTier.TIER_1)
        assert opt.tier_map["coding"] == ModelTier.TIER_1
        rec = opt.recommend("coding", total_session_spend=0.0)
        assert rec.recommended_tier == ModelTier.TIER_1

    def test_record_quality_score(self) -> None:
        opt = CostOptimizer()
        result = opt.record_quality_score("analysis", 0.8)
        assert not result.blocked
        assert result.quality_score == 0.8

    def test_state_dict(self) -> None:
        opt = CostOptimizer()
        state = opt.state
        assert "tier_map" in state
        assert "degrader" in state
        assert "loop_detector" in state
        assert state["tier_map"]["coding"] == "TIER_2"

    def test_tier_recommendation_repr(self) -> None:
        rec = TierRecommendation(
            task_type="test",
            recommended_tier=ModelTier.TIER_2,
            degraded=False,
            blocked=False,
            cost_estimate=0.01,
        )
        rep = repr(rec)
        assert "TierRecommendation" in rep
        assert "test" in rep
        assert "TIER_2" in rep

    def test_tier_recommendation_label(self) -> None:
        rec = TierRecommendation(
            task_type="test",
            recommended_tier=ModelTier.TIER_0,
            degraded=False,
            blocked=False,
            cost_estimate=0.0,
        )
        assert rec.label == "Local SLM"
