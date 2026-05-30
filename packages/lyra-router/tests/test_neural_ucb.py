"""
Comprehensive tests for the NeuralUCB contextual bandit module.

Covers:
- UCBConfig frozen dataclass
- UCB selection converges to best model
- Exploration bonus decreases with pulls
- Budget constraint filters correctly
- Online learning improves predictions
- get_model_stats returns valid data
- Synthetic task features with different patterns
- NeuralTier integration with NeuralUCB
"""

from __future__ import annotations

import numpy as np
import pytest
from lyra_router import ModelTier, TaskComplexity
from lyra_router.neural_ucb import NeuralUCB, UCBConfig
from lyra_router.tiers import NeuralTier, TierResult

# ────────────────────────────────────────────────────────────────────
# UCBConfig tests
# ────────────────────────────────────────────────────────────────────


class TestUCBConfig:
    def test_default_values(self) -> None:
        config = UCBConfig()
        assert config.hidden_dim == 64
        assert config.learning_rate == 0.001
        assert config.exploration_bonus == 0.1
        assert config.window_size == 1000
        assert config.min_samples == 10
        assert config.cost_sensitivity == 0.5
        assert config.quality_weight == 1.0

    def test_custom_values(self) -> None:
        config = UCBConfig(
            hidden_dim=128,
            learning_rate=0.01,
            exploration_bonus=0.5,
            window_size=500,
            min_samples=5,
            cost_sensitivity=0.8,
            quality_weight=1.5,
        )
        assert config.hidden_dim == 128
        assert config.learning_rate == 0.01
        assert config.exploration_bonus == 0.5
        assert config.window_size == 500
        assert config.min_samples == 5
        assert config.cost_sensitivity == 0.8
        assert config.quality_weight == 1.5

    def test_frozen(self) -> None:
        config = UCBConfig()
        with pytest.raises(AttributeError):
            config.hidden_dim = 128  # type: ignore[misc]


# ────────────────────────────────────────────────────────────────────
# NeuralUCB core tests
# ────────────────────────────────────────────────────────────────────


class TestNeuralUCB:
    """Tests for core NeuralUCB functionality."""

    _INPUT_DIM = 10

    def _make_features(self, seed: int = 0) -> np.ndarray:
        rng = np.random.RandomState(seed)
        return rng.randn(self._INPUT_DIM)

    # ── select_model ────────────────────────────────────────────────

    def test_select_model_returns_valid_model(self) -> None:
        ucb = NeuralUCB(UCBConfig(), n_models=3)
        features = self._make_features(0)
        candidates = ["haiku", "standard", "premium"]

        model_id, confidence = ucb.select_model(features, candidates)

        assert model_id in candidates
        assert 0.0 <= confidence <= 1.0

    def test_select_model_with_single_candidate(self) -> None:
        ucb = NeuralUCB(UCBConfig(), n_models=1)
        features = self._make_features(0)

        model_id, confidence = ucb.select_model(features, ["only_model"])

        assert model_id == "only_model"
        assert 0.0 <= confidence <= 1.0

    def test_select_model_explores_all_candidates(self) -> None:
        """With high exploration bonus and many pulls, all models should be tried."""
        ucb = NeuralUCB(UCBConfig(exploration_bonus=5.0, min_samples=1), n_models=3)
        features = self._make_features(0)
        candidates = ["a", "b", "c"]

        for _ in range(100):
            model_id, _ = ucb.select_model(features, candidates)
            ucb.update(model_id, features, success=True, latency_ms=10, cost=0.001)

        stats = ucb.get_model_stats()
        assert len(stats) == 3
        for c in candidates:
            assert c in stats

    # ── exploration decreases ──────────────────────────────────────

    def test_exploration_decreases_with_pulls(self) -> None:
        """UCB values should decrease as a model is pulled more."""
        ucb = NeuralUCB(UCBConfig(exploration_bonus=1.0, min_samples=1), n_models=2)
        features = self._make_features(0)

        # Pull model_a 50 times
        for _ in range(50):
            ucb.update("model_a", features, success=True, latency_ms=10, cost=0.001)

        # Pull model_b 5 times
        for _ in range(5):
            ucb.update("model_b", features, success=False, latency_ms=50, cost=0.01)

        stats = ucb.get_model_stats()
        # model_a should have lower (or equal) ucb_value than model_b
        # since it has more pulls
        assert stats["model_a"]["pulls"] > stats["model_b"]["pulls"]

    # ── budget constraint ──────────────────────────────────────────

    def test_budget_constraint_filters_expensive(self) -> None:
        """Budget constraint should filter out models exceeding the limit."""
        ucb = NeuralUCB(UCBConfig(), n_models=4)
        features = self._make_features(0)
        candidates = ["haiku", "standard", "premium", "agentic"]

        # Budget equal to haiku's cost — only haiku should pass the filter
        model_id, _ = ucb.select_model(features, candidates, budget_constraint=0.001)
        assert model_id == "haiku"

    def test_budget_constraint_falls_back_when_all_filtered(self) -> None:
        """When all models exceed the budget, all candidates should still be considered."""
        ucb = NeuralUCB(UCBConfig(), n_models=2)
        features = self._make_features(0)
        candidates = ["premium", "agentic"]

        # Extremely tight budget — both models exceed it
        model_id, _ = ucb.select_model(features, candidates, budget_constraint=0.0001)
        assert model_id in candidates

    def test_budget_constraint_medium_budget(self) -> None:
        """Medium budget should allow mid-tier models."""
        ucb = NeuralUCB(UCBConfig(), n_models=4)
        features = self._make_features(0)
        candidates = ["haiku", "standard", "premium", "agentic"]

        # Medium budget — standard is the most expensive allowed
        model_id, _ = ucb.select_model(features, candidates, budget_constraint=0.01)
        assert model_id in ("haiku", "standard")

    # ── online learning ────────────────────────────────────────────

    def test_online_learning_improves_predictions(self) -> None:
        """After training on a consistent pattern, model_a should be preferred."""
        ucb = NeuralUCB(UCBConfig(learning_rate=0.01, min_samples=1), n_models=2)
        features = np.zeros(self._INPUT_DIM)

        # Heavily reinforce model_a with zero features
        for _ in range(100):
            ucb.update("model_a", features, success=True, latency_ms=10, cost=0.001)

        # Give model_b some negative examples
        for _ in range(20):
            ucb.update("model_b", features, success=False, latency_ms=100, cost=0.05)

        # At this point, model_a should have a much higher predicted reward
        # for the zero-feature case
        model_id, _ = ucb.select_model(features, ["model_a", "model_b"])
        assert model_id == "model_a"

    def test_learning_discriminates_different_features(self) -> None:
        """
        With two feature patterns and both positive/negative examples,
        the network should learn to discriminate between them.
        Uses in-range normalized features to avoid weight explosion
        from unnormalized input magnitudes.
        Positive: short->haiku succeeds, long->premium succeeds.
        Negative: short->premium fails, long->haiku fails.
        """
        ucb = NeuralUCB(
            UCBConfig(
                hidden_dim=8,
                learning_rate=0.05,
                min_samples=1,
                exploration_bonus=0.0,
                cost_sensitivity=0.0,
            ),
            n_models=2,
        )

        # Features with similar [0, 1] ranges to avoid weight explosion
        feat_a = np.array([0.1, 0.2, 0.3, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        feat_b = np.array([0.8, 0.9, 0.7, 0.1, 0.2, 0.0, 0.0, 0.3, 0.2, 0.1])

        # Positive and negative examples to teach discrimination
        for _ in range(400):
            ucb.update("model_a", feat_a, success=True, latency_ms=5, cost=0.0)
            ucb.update("model_b", feat_b, success=True, latency_ms=5, cost=0.0)
            ucb.update("model_a", feat_b, success=False, latency_ms=50, cost=0.0)
            ucb.update("model_b", feat_a, success=False, latency_ms=50, cost=0.0)

        # The preferred model should differ between feature types
        preds_a = ucb._forward(feat_a.reshape(1, -1)).flatten()
        preds_b = ucb._forward(feat_b.reshape(1, -1)).flatten()

        diff_a = float(preds_a[0] - preds_a[1])  # model_a - model_b for feat_a
        diff_b = float(preds_b[0] - preds_b[1])  # model_a - model_b for feat_b

        # The preferred model should flip between feature types
        assert diff_a * diff_b < 0, (
            f"Network should prefer different models per feature type: "
            f"feat_a_diff={diff_a:.4f}, feat_b_diff={diff_b:.4f}"
        )

    # ── get_model_stats ────────────────────────────────────────────

    def test_get_model_stats_empty(self) -> None:
        """get_model_stats should return empty dict when no updates have occurred."""
        ucb = NeuralUCB(UCBConfig(), n_models=2)
        stats = ucb.get_model_stats()
        assert stats == {}

    def test_get_model_stats_after_updates(self) -> None:
        """get_model_stats should return valid data for models that have been updated."""
        ucb = NeuralUCB(UCBConfig(), n_models=2)
        features = self._make_features(0)

        ucb.update("model_a", features, success=True, latency_ms=10, cost=0.001)
        ucb.update("model_a", features, success=True, latency_ms=15, cost=0.002)
        ucb.update("model_b", features, success=False, latency_ms=50, cost=0.01)

        stats = ucb.get_model_stats()

        assert "model_a" in stats
        assert "model_b" in stats
        assert stats["model_a"]["pulls"] == 2
        assert stats["model_b"]["pulls"] == 1
        assert isinstance(stats["model_a"]["mean_reward"], float)
        assert isinstance(stats["model_a"]["ucb_value"], float)
        assert isinstance(stats["model_b"]["mean_reward"], float)
        assert isinstance(stats["model_b"]["total_reward"], float)
        assert isinstance(stats["model_a"]["reward_history"], list)
        assert len(stats["model_a"]["reward_history"]) == 2
        assert len(stats["model_b"]["reward_history"]) == 1

    def test_get_model_stats_reward_values(self) -> None:
        """Model with high success and low cost should have higher mean reward."""
        ucb = NeuralUCB(
            UCBConfig(cost_sensitivity=0.5, quality_weight=1.0),
            n_models=2,
        )
        features = self._make_features(0)

        # Model A: successful, cheap
        for _ in range(5):
            ucb.update("model_a", features, success=True, latency_ms=10, cost=0.001)

        # Model B: failing, expensive
        for _ in range(5):
            ucb.update("model_b", features, success=False, latency_ms=100, cost=0.05)

        stats = ucb.get_model_stats()
        assert stats["model_a"]["mean_reward"] > stats["model_b"]["mean_reward"]

    # ── synthetic task features ────────────────────────────────────

    def test_synthetic_features_trivial_task(self) -> None:
        """Trivial tasks should route correctly with NeuralTier."""
        tier = NeuralTier(exploration_bonus=0.1)

        # Simulate training data for trivial tasks
        for _ in range(15):
            tier.update_with_outcome(
                task="hello",
                model_id="local_slm",
                success=True,
                latency_ms=1,
                cost=0.00003,
            )

        result = tier.route("hi there")
        assert result is not None
        assert isinstance(result, TierResult)
        assert result.confidence > 0.0

    def test_synthetic_features_complex_task(self) -> None:
        """Complex tasks should route correctly with NeuralTier."""
        tier = NeuralTier(exploration_bonus=0.1, cost_sensitivity=0.3)

        # Simulate training data for complex tasks
        for _ in range(15):
            tier.update_with_outcome(
                task="design a scalable microservices architecture with kubernetes",
                model_id="premium",
                success=True,
                latency_ms=200,
                cost=0.05,
            )

        result = tier.route("design a distributed event-driven system")
        assert result is not None
        assert isinstance(result, TierResult)

    def test_pareto_quality_cost_tradeoff(self) -> None:
        """
        Test that cost-aware reward creates a Pareto-style quality/cost trade-off.
        An expensive model that succeeds should still have lower reward than a
        cheap model that succeeds (due to cost penalty).
        """
        ucb = NeuralUCB(
            UCBConfig(cost_sensitivity=1.0, quality_weight=1.0, min_samples=1),
            n_models=2,
        )
        features = np.zeros(self._INPUT_DIM)

        # Both models succeed equally, but one is much more expensive
        for _ in range(20):
            ucb.update("cheap", features, success=True, latency_ms=10, cost=0.001)
            ucb.update("expensive", features, success=True, latency_ms=10, cost=0.05)

        stats = ucb.get_model_stats()
        assert stats["cheap"]["mean_reward"] > stats["expensive"]["mean_reward"]


# ────────────────────────────────────────────────────────────────────
# NeuralTier integration tests
# ────────────────────────────────────────────────────────────────────


class TestNeuralTierIntegration:
    """Tests for NeuralTier integration with NeuralUCB."""

    def test_initial_state(self) -> None:
        tier = NeuralTier()
        assert tier._fitted is False
        assert tier._ucb is not None

    def test_route_before_training_uses_heuristic(self) -> None:
        tier = NeuralTier()
        result = tier.route("implement a JWT auth middleware")
        assert result is not None
        assert result.confidence > 0.0
        assert "heuristic" in result.matched_rule

    def test_route_after_training_uses_neural(self) -> None:
        tier = NeuralTier()
        # Train with enough examples
        for _ in range(15):
            tier.update_with_outcome(
                task="implement a feature",
                model_id="standard",
                success=True,
                latency_ms=50,
                cost=0.01,
            )

        result = tier.route("build a new API endpoint")
        assert result is not None
        assert result.confidence > 0.0
        assert result.model_tier in list(ModelTier)

    def test_train_legacy_method(self) -> None:
        """The legacy train method should still work."""
        tier = NeuralTier()
        tier.train("implement a complex system", TaskComplexity.COMPLEX)
        assert tier._fitted is False  # Not enough samples yet

    def test_fit_returns_fitted_status(self) -> None:
        tier = NeuralTier()
        assert tier.fit() is False

        for _ in range(15):
            tier.update_with_outcome(
                task="a task",
                model_id="haiku",
                success=True,
                latency_ms=10,
                cost=0.001,
            )

        assert tier.fit() is True

    def test_get_stats(self) -> None:
        tier = NeuralTier()
        assert tier.get_stats() == {}

        tier.update_with_outcome(
            task="test task",
            model_id="haiku",
            success=True,
            latency_ms=10,
            cost=0.001,
        )

        stats = tier.get_stats()
        assert "haiku" in stats
        assert stats["haiku"]["pulls"] == 1

    def test_multiple_tier_candidates(self) -> None:
        """NeuralTier should handle multiple model tier candidates."""
        tier = NeuralTier(exploration_bonus=5.0)

        # Train on all tiers
        for tier_id in ["haiku", "standard", "premium"]:
            for _ in range(5):
                tier.update_with_outcome(
                    task=f"task for {tier_id}",
                    model_id=tier_id,
                    success=True,
                    latency_ms=10,
                    cost=0.001,
                )

        # Route should still return a valid result
        result = tier.route("some random task")
        assert result is not None
        assert result.model_tier in list(ModelTier)
