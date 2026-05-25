"""Tests for the policy_evaluator module."""

from __future__ import annotations

import pytest

from lyra_policy_optimizer.exceptions import PolicyEvaluationError
from lyra_policy_optimizer.policy_evaluator import (
    EvalConfig,
    EpisodeResult,
    PolicyComparison,
    PolicyEvaluation,
    PolicyEvaluator,
)
from lyra_policy_optimizer.policy_search import PolicyCandidate


class TestEvalConfig:
    """Test EvalConfig dataclass."""

    def test_default_config(self) -> None:
        """EvalConfig should have sensible defaults."""
        config = EvalConfig()
        assert config.num_episodes == 100
        assert config.horizon == 50
        assert "reward" in config.eval_metrics

    def test_frozen(self) -> None:
        """EvalConfig should be frozen."""
        config = EvalConfig()
        with pytest.raises(AttributeError):
            config.num_episodes = 50  # type: ignore[misc]


class TestEpisodeResult:
    """Test EpisodeResult dataclass."""

    def test_create_episode(self) -> None:
        """EpisodeResult should store episode data correctly."""
        metrics = (("reward", 1.5), ("steps", 10.0))
        result = EpisodeResult(
            episode=0, total_reward=1.5, success=True, steps=10, metrics=metrics
        )
        assert result.total_reward == 1.5
        assert result.success is True
        assert result.steps == 10


class TestPolicyEvaluation:
    """Test PolicyEvaluation dataclass."""

    def test_create_evaluation(self) -> None:
        """PolicyEvaluation should aggregate episode results."""
        policy = PolicyCandidate("p1", (("lr", 0.01),), 0.9, 0.1, 0)
        episodes = (
            EpisodeResult(0, 5.0, True, 50, (("r", 5.0),)),
            EpisodeResult(1, 3.0, True, 45, (("r", 3.0),)),
        )
        evaluation = PolicyEvaluation(
            policy=policy,
            episodes=episodes,
            avg_reward=4.0,
            success_rate=1.0,
            std_reward=1.0,
        )
        assert evaluation.avg_reward == 4.0
        assert evaluation.success_rate == 1.0


class TestPolicyComparison:
    """Test PolicyComparison dataclass."""

    def test_create_comparison(self) -> None:
        """PolicyComparison should identify a winner."""
        eval_a = PolicyEvaluation(
            PolicyCandidate("a", (), 0.5, 0.1, 0), (), 5.0, 0.8, 1.0
        )
        eval_b = PolicyEvaluation(
            PolicyCandidate("b", (), 0.4, 0.2, 0), (), 3.0, 0.6, 1.5
        )
        comparison = PolicyComparison(
            evaluations=(eval_a, eval_b),
            winner=eval_a.policy,
            confidence=0.8,
            recommendation="Use policy a",
        )
        assert comparison.winner is not None
        assert comparison.winner.candidate_id == "a"
        assert comparison.confidence == 0.8


class TestPolicyEvaluator:
    """Test PolicyEvaluator class."""

    @pytest.fixture
    def evaluator(self) -> PolicyEvaluator:
        return PolicyEvaluator()

    @pytest.fixture
    def sample_policy(self) -> PolicyCandidate:
        return PolicyCandidate(
            "test_policy",
            (("learning_rate", 0.01), ("batch_size", 32.0)),
            0.85, 0.1, 0,
        )

    @pytest.mark.asyncio
    async def test_evaluate_policy(
        self, evaluator: PolicyEvaluator, sample_policy: PolicyCandidate
    ) -> None:
        """Evaluate policy should return valid evaluation."""
        config = EvalConfig(num_episodes=5, horizon=10)
        evaluation = await evaluator.evaluate_policy(sample_policy, config)
        assert isinstance(evaluation, PolicyEvaluation)
        assert len(evaluation.episodes) == 5
        assert 0 <= evaluation.success_rate <= 1
        assert evaluation.avg_reward >= 0

    @pytest.mark.asyncio
    async def test_evaluate_policy_invalid_episodes(
        self, evaluator: PolicyEvaluator, sample_policy: PolicyCandidate
    ) -> None:
        """Evaluate policy should reject invalid num_episodes."""
        config = EvalConfig(num_episodes=0)
        with pytest.raises(PolicyEvaluationError, match="num_episodes"):
            await evaluator.evaluate_policy(sample_policy, config)

    @pytest.mark.asyncio
    async def test_evaluate_policy_invalid_horizon(
        self, evaluator: PolicyEvaluator, sample_policy: PolicyCandidate
    ) -> None:
        """Evaluate policy should reject invalid horizon."""
        config = EvalConfig(horizon=0)
        with pytest.raises(PolicyEvaluationError, match="horizon"):
            await evaluator.evaluate_policy(sample_policy, config)

    @pytest.mark.asyncio
    async def test_compare_policies(
        self, evaluator: PolicyEvaluator
    ) -> None:
        """Compare policies should identify a winner."""
        policy_a = PolicyCandidate(
            "a", (("learning_rate", 0.1), ("batch_size", 64.0)), 0.9, 0.05, 0
        )
        policy_b = PolicyCandidate(
            "b", (("learning_rate", 0.001), ("batch_size", 16.0)), 0.6, 0.2, 0
        )
        comparison = await evaluator.compare_policies((policy_a, policy_b))
        assert isinstance(comparison, PolicyComparison)
        assert comparison.winner is not None
        assert len(comparison.evaluations) == 2

    @pytest.mark.asyncio
    async def test_compare_policies_empty(
        self, evaluator: PolicyEvaluator
    ) -> None:
        """Compare policies should reject empty list."""
        with pytest.raises(PolicyEvaluationError, match="policies"):
            await evaluator.compare_policies(())

    @pytest.mark.asyncio
    async def test_compare_policies_single(
        self, evaluator: PolicyEvaluator
    ) -> None:
        """Compare policies with single policy should work."""
        policy = PolicyCandidate(
            "only", (("lr", 0.01), ("bs", 32.0)), 0.8, 0.1, 0
        )
        comparison = await evaluator.compare_policies((policy,))
        assert comparison.winner is not None
        assert comparison.winner.candidate_id == "only"
        assert comparison.confidence == 1.0

    @pytest.mark.asyncio
    async def test_ab_test(
        self, evaluator: PolicyEvaluator
    ) -> None:
        """A/B test should compare two policies."""
        policy_a = PolicyCandidate(
            "A", (("lr", 0.1), ("bs", 64.0)), 0.9, 0.0, 0
        )
        policy_b = PolicyCandidate(
            "B", (("lr", 0.001), ("bs", 16.0)), 0.6, 0.0, 0
        )
        result = await evaluator.ab_test(policy_a, policy_b)
        assert isinstance(result, PolicyComparison)
        assert result.winner is not None
        assert result.recommendation != ""

    @pytest.mark.asyncio
    async def test_episode_result_structure(
        self, evaluator: PolicyEvaluator, sample_policy: PolicyCandidate
    ) -> None:
        """Each episode should have correct structure."""
        config = EvalConfig(num_episodes=3, horizon=5)
        evaluation = await evaluator.evaluate_policy(sample_policy, config)
        for episode in evaluation.episodes:
            assert episode.total_reward > 0
            assert isinstance(episode.success, bool)
            assert isinstance(episode.steps, int)

    @pytest.mark.asyncio
    async def test_different_policies_produce_different_results(
        self, evaluator: PolicyEvaluator
    ) -> None:
        """Different policies should produce different evaluations."""
        high_lr = PolicyCandidate(
            "high", (("learning_rate", 0.5), ("batch_size", 32.0)), 0.9, 0.0, 0
        )
        low_lr = PolicyCandidate(
            "low", (("learning_rate", 0.0001), ("batch_size", 32.0)), 0.5, 0.0, 0
        )
        cfg = EvalConfig(num_episodes=10)
        eval_high = await evaluator.evaluate_policy(high_lr, cfg)
        eval_low = await evaluator.evaluate_policy(low_lr, cfg)
        assert eval_high.avg_reward != eval_low.avg_reward
