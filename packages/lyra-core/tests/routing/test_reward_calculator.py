"""Tests for the RL reward calculator."""
from __future__ import annotations

import pytest
from lyra_core.routing.reward_calculator import (
    RewardCalculator,
    RewardComponents,
    RewardConfig,
)


class TestRewardConfig:
    def test_default_weights_sum_to_one(self):
        cfg = RewardConfig()
        total = cfg.quality_weight + cfg.cost_weight + cfg.latency_weight + cfg.safety_weight
        assert abs(total - 1.0) < 0.01

    def test_invalid_weights_rejected(self):
        with pytest.raises(ValueError, match="sum"):
            RewardConfig(quality_weight=1.0)

    def test_frozen_dataclass(self):
        cfg = RewardConfig()
        with pytest.raises(Exception):
            cfg.quality_weight = 0.9  # type: ignore[misc]


class TestRewardCalculator:
    def test_perfect_quality_gives_positive_reward(self):
        calc = RewardCalculator()
        comp = calc.compute(quality=1.0, cost_usd=0.0, latency_ms=0.0)
        assert comp.total > 0.0
        assert comp.quality_score > 0.0

    def test_low_quality_reduces_reward(self):
        calc = RewardCalculator()
        good = calc.compute(quality=1.0)
        bad = calc.compute(quality=0.3)
        assert bad.total < good.total

    def test_high_cost_adds_penalty(self):
        calc = RewardCalculator()
        cheap = calc.compute(cost_usd=0.001, tier="fast")
        expensive = calc.compute(cost_usd=1.0, tier="advisor")
        assert expensive.cost_penalty > cheap.cost_penalty

    def test_high_latency_adds_penalty(self):
        calc = RewardCalculator()
        fast = calc.compute(latency_ms=100.0)
        slow = calc.compute(latency_ms=5000.0)
        assert slow.latency_penalty > fast.latency_penalty

    def test_latency_below_threshold_no_penalty(self):
        calc = RewardCalculator()
        comp = calc.compute(latency_ms=500.0)
        assert comp.latency_penalty == 0.0

    def test_safety_flagged_adds_penalty(self):
        calc = RewardCalculator()
        safe = calc.compute(safety_flagged=False)
        flagged = calc.compute(safety_flagged=True)
        assert flagged.safety_penalty > safe.safety_penalty

    def test_tier_affects_cost_penalty(self):
        calc = RewardCalculator()
        fast = calc.compute(cost_usd=0.1, tier="fast")
        advisor = calc.compute(cost_usd=0.1, tier="advisor")
        assert advisor.cost_penalty > fast.cost_penalty

    def test_reward_components_are_frozen(self):
        comp = RewardComponents(
            quality_score=0.5,
            cost_penalty=0.1,
            latency_penalty=0.0,
            safety_penalty=0.0,
            total=0.4,
        )
        with pytest.raises(Exception):
            comp.total = 1.0  # type: ignore[misc]

    def test_reward_bounded(self):
        calc = RewardCalculator()
        comp = calc.compute(quality=0.0, cost_usd=100.0, latency_ms=100000.0, safety_flagged=True)
        assert comp.total <= 1.0
        assert comp.total >= -1.0

    def test_config_accessible(self):
        calc = RewardCalculator()
        assert isinstance(calc.config, RewardConfig)
