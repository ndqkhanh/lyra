"""Tests for the reward_model module."""

from __future__ import annotations

import pytest
from lyra_policy_optimizer.exceptions import RewardModelError
from lyra_policy_optimizer.reward_model import (
    RewardConfig,
    RewardModel,
    RewardSignal,
    RewardSummary,
)


class TestRewardConfig:
    """Test RewardConfig dataclass."""

    def test_default_config(self) -> None:
        """RewardConfig should have sensible defaults."""
        config = RewardConfig()
        assert config.metrics == ("accuracy", "latency", "cost")
        assert config.weights == (0.5, 0.25, 0.25)
        assert config.discount_factor == 0.99
        assert config.shaping_enabled is True

    def test_frozen(self) -> None:
        """RewardConfig should be frozen."""
        config = RewardConfig()
        with pytest.raises(AttributeError):
            config.discount_factor = 0.5  # type: ignore[misc]


class TestRewardSignal:
    """Test RewardSignal dataclass."""

    def test_create_signal(self) -> None:
        """RewardSignal should store values correctly."""
        signal = RewardSignal(
            metric="accuracy",
            value=0.95,
            normalized=0.95,
            weight=0.5,
            timestamp=1000.0,
        )
        assert signal.metric == "accuracy"
        assert signal.value == 0.95
        assert signal.normalized == 0.95
        assert signal.timestamp == 1000.0


class TestRewardSummary:
    """Test RewardSummary dataclass."""

    def test_create_summary(self) -> None:
        """RewardSummary should aggregate signals."""
        signals = (
            RewardSignal("acc", 0.95, 0.95, 0.5, 1.0),
            RewardSignal("lat", 0.1, 0.5, 0.25, 1.0),
        )
        summary = RewardSummary(
            signals=signals,
            total_reward=0.8,
            discounted_reward=0.79,
            cumulative=1.6,
        )
        assert len(summary.signals) == 2
        assert summary.total_reward == 0.8
        assert summary.cumulative == 1.6


class TestRewardModel:
    """Test RewardModel class."""

    @pytest.fixture
    def model(self) -> RewardModel:
        return RewardModel()

    @pytest.mark.asyncio
    async def test_compute_reward_basic(self, model: RewardModel) -> None:
        """Compute reward should return a valid summary."""
        metrics = {"accuracy": 0.95, "latency": 0.1, "cost": 0.05}
        config = RewardConfig()
        summary = await model.compute_reward(metrics, config)
        assert isinstance(summary, RewardSummary)
        assert len(summary.signals) == 3
        assert summary.total_reward > 0
        assert summary.discounted_reward > 0

    @pytest.mark.asyncio
    async def test_compute_reward_empty_metrics(
        self, model: RewardModel
    ) -> None:
        """Compute reward should reject empty metrics."""
        with pytest.raises(RewardModelError, match="metrics"):
            await model.compute_reward({}, RewardConfig())

    @pytest.mark.asyncio
    async def test_compute_reward_mismatched_weights(
        self, model: RewardModel
    ) -> None:
        """Compute reward should reject mismatched metrics/weights."""
        config = RewardConfig(
            metrics=("accuracy",), weights=(0.5, 0.25)
        )
        with pytest.raises(RewardModelError, match="same length"):
            await model.compute_reward({"accuracy": 0.95}, config)

    @pytest.mark.asyncio
    async def test_compute_reward_negative_weight(
        self, model: RewardModel
    ) -> None:
        """Compute reward should reject negative weights."""
        config = RewardConfig(weights=(-0.5, 0.25, 0.25))
        with pytest.raises(RewardModelError, match="weights"):
            await model.compute_reward(
                {"accuracy": 0.95, "latency": 0.1, "cost": 0.05},
                config,
            )

    @pytest.mark.asyncio
    async def test_compute_reward_zero_total_weight(
        self, model: RewardModel
    ) -> None:
        """Compute reward should reject zero total weight."""
        config = RewardConfig(weights=(0.0, 0.0, 0.0))
        with pytest.raises(RewardModelError, match="total weight"):
            await model.compute_reward(
                {"accuracy": 0.95, "latency": 0.1, "cost": 0.05},
                config,
            )

    @pytest.mark.asyncio
    async def test_compute_reward_missing_metric(
        self, model: RewardModel
    ) -> None:
        """Compute reward should reject missing metrics."""
        with pytest.raises(RewardModelError, match="not found"):
            await model.compute_reward(
                {"accuracy": 0.95}, RewardConfig()
            )

    @pytest.mark.asyncio
    async def test_shape_reward(self, model: RewardModel) -> None:
        """Shape reward should modify signals."""
        signals = (
            RewardSignal("acc", 0.5, 0.5, 0.5, 1.0),
            RewardSignal("lat", 0.8, 0.8, 0.5, 2.0),
        )
        shaped = await model.shape_reward(signals)
        assert len(shaped) == 2
        assert shaped[1].normalized >= signals[1].normalized

    @pytest.mark.asyncio
    async def test_shape_reward_empty(self, model: RewardModel) -> None:
        """Shape reward with empty signals should return empty."""
        shaped = await model.shape_reward(())
        assert shaped == ()

    @pytest.mark.asyncio
    async def test_normalize_rewards(self, model: RewardModel) -> None:
        """Normalize rewards should map to [0, 1]."""
        rewards = (1.0, 3.0, 5.0)
        normalized = await model.normalize_rewards(rewards)
        assert len(normalized) == 3
        assert abs(normalized[0]) < 1e-10
        assert abs(normalized[2] - 1.0) < 1e-10
        assert all(0.0 <= n <= 1.0 for n in normalized)

    @pytest.mark.asyncio
    async def test_normalize_rewards_empty(self, model: RewardModel) -> None:
        """Normalize empty rewards should return empty."""
        assert await model.normalize_rewards(()) == ()

    @pytest.mark.asyncio
    async def test_normalize_rewards_all_equal(
        self, model: RewardModel
    ) -> None:
        """Normalize all-equal rewards should return 0.5 for each."""
        normalized = await model.normalize_rewards((2.0, 2.0, 2.0))
        assert all(n == 0.5 for n in normalized)

    @pytest.mark.asyncio
    async def test_normalize_single_value(self, model: RewardModel) -> None:
        """Normalize single-element tuple."""
        normalized = await model.normalize_rewards((4.2,))
        assert len(normalized) == 1
        assert abs(normalized[0] - 0.5) < 1e-10

    def test_compute_discounted(self, model: RewardModel) -> None:
        """Compute discounted sum of rewards."""
        result = model.compute_discounted((1.0, 1.0, 1.0), 0.5)
        expected = 1.0 + 0.5 + 0.25
        assert abs(result - expected) < 1e-10

    def test_compute_discounted_empty(self, model: RewardModel) -> None:
        """Compute discounted with empty rewards should return 0."""
        assert model.compute_discounted((), 0.5) == 0.0

    def test_compute_discounted_invalid_gamma(
        self, model: RewardModel
    ) -> None:
        """Compute discounted with invalid gamma should raise."""
        with pytest.raises(RewardModelError, match="gamma"):
            model.compute_discounted((1.0,), 1.5)

    def test_compute_discounted_gamma_one(self, model: RewardModel) -> None:
        """Compute discounted with gamma=1 should sum directly."""
        result = model.compute_discounted((1.0, 2.0, 3.0), 1.0)
        assert abs(result - 6.0) < 1e-10

    @pytest.mark.asyncio
    async def test_metric_accuracy_high(self, model: RewardModel) -> None:
        """High accuracy should produce high normalized value."""
        config = RewardConfig(metrics=("accuracy",), weights=(1.0,))
        summary = await model.compute_reward({"accuracy": 1.0}, config)
        assert summary.signals[0].normalized == 1.0
        assert abs(summary.total_reward - 1.0) < 1e-10

    @pytest.mark.asyncio
    async def test_metric_latency_sigmoid(self, model: RewardModel) -> None:
        """Latency should use sigmoid normalization."""
        config = RewardConfig(metrics=("latency",), weights=(1.0,))
        summary = await model.compute_reward({"latency": 0.0}, config)
        assert 0.0 < summary.signals[0].normalized <= 1.0

    @pytest.mark.asyncio
    async def test_metric_cost_sigmoid(self, model: RewardModel) -> None:
        """Cost should use sigmoid normalization."""
        config = RewardConfig(metrics=("cost",), weights=(1.0,))
        summary = await model.compute_reward({"cost": 10.0}, config)
        assert summary.signals[0].normalized < 0.5

    @pytest.mark.asyncio
    async def test_cumulative_tracking(self, model: RewardModel) -> None:
        """Cumulative reward should track across calls."""
        config = RewardConfig(
            metrics=("accuracy",), weights=(1.0,), discount_factor=1.0
        )
        r1 = await model.compute_reward({"accuracy": 0.5}, config)
        r2 = await model.compute_reward({"accuracy": 0.7}, config)
        assert r2.cumulative == r1.total_reward + r2.total_reward
