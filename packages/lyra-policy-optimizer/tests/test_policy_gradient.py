"""Tests for the policy_gradient module."""

from __future__ import annotations

import pytest
from lyra_policy_optimizer.exceptions import PolicyGradientError
from lyra_policy_optimizer.policy_gradient import (
    GradientConfig,
    GradientResult,
    GradientStep,
    PolicyGradientOptimizer,
)


class TestGradientConfig:
    """Test GradientConfig dataclass."""

    def test_default_config(self) -> None:
        """GradientConfig should have sensible defaults."""
        config = GradientConfig()
        assert config.learning_rate == 0.01
        assert config.batch_size == 32
        assert config.entropy_coef == 0.01
        assert config.max_grad_norm == 1.0
        assert config.optimizer == "adam"

    def test_frozen(self) -> None:
        """GradientConfig should be frozen."""
        config = GradientConfig()
        with pytest.raises(AttributeError):
            config.learning_rate = 0.1  # type: ignore[misc]


class TestGradientStep:
    """Test GradientStep dataclass."""

    def test_create_step(self) -> None:
        """GradientStep should store step data correctly."""
        params = (("param_0", 0.5), ("param_1", 0.3))
        step = GradientStep(
            step=0, loss=0.5, gradient_norm=0.1, policy_params=params
        )
        assert step.step == 0
        assert step.loss == 0.5
        assert step.gradient_norm == 0.1
        assert len(step.policy_params) == 2


class TestGradientResult:
    """Test GradientResult dataclass."""

    def test_create_result(self) -> None:
        """GradientResult should store optimization result."""
        step = GradientStep(0, 0.5, 0.1, ())
        result = GradientResult(
            steps=(step,), final_loss=0.5, converged=True, total_steps=1
        )
        assert result.final_loss == 0.5
        assert result.converged is True
        assert result.total_steps == 1


class TestPolicyGradientOptimizer:
    """Test PolicyGradientOptimizer class."""

    @pytest.fixture
    def optimizer(self) -> PolicyGradientOptimizer:
        return PolicyGradientOptimizer()

    @pytest.mark.asyncio
    async def test_compute_gradient_basic(
        self, optimizer: PolicyGradientOptimizer
    ) -> None:
        """Compute gradient should return valid gradient."""
        params = (1.0, 2.0, 3.0)
        rewards = (0.5, 0.8, 0.9)
        config = GradientConfig()
        grad = await optimizer.compute_gradient(params, rewards, config)
        assert len(grad) == 3
        assert all(isinstance(g, float) for g in grad)

    @pytest.mark.asyncio
    async def test_compute_gradient_empty_params(
        self, optimizer: PolicyGradientOptimizer
    ) -> None:
        """Compute gradient should reject empty params."""
        with pytest.raises(PolicyGradientError, match="params"):
            await optimizer.compute_gradient((), (0.5,), GradientConfig())

    @pytest.mark.asyncio
    async def test_compute_gradient_empty_rewards(
        self, optimizer: PolicyGradientOptimizer
    ) -> None:
        """Compute gradient should reject empty rewards."""
        with pytest.raises(PolicyGradientError, match="rewards"):
            await optimizer.compute_gradient((1.0,), (), GradientConfig())

    @pytest.mark.asyncio
    async def test_compute_gradient_length_mismatch(
        self, optimizer: PolicyGradientOptimizer
    ) -> None:
        """Compute gradient should reject length mismatch."""
        with pytest.raises(PolicyGradientError, match="same length"):
            await optimizer.compute_gradient(
                (1.0, 2.0), (0.5,), GradientConfig()
            )

    @pytest.mark.asyncio
    async def test_compute_gradient_negative_lr(
        self, optimizer: PolicyGradientOptimizer
    ) -> None:
        """Compute gradient should reject negative learning rate."""
        config = GradientConfig(learning_rate=-0.01)
        with pytest.raises(PolicyGradientError, match="learning_rate"):
            await optimizer.compute_gradient((1.0,), (0.5,), config)

    @pytest.mark.asyncio
    async def test_compute_gradient_invalid_batch_size(
        self, optimizer: PolicyGradientOptimizer
    ) -> None:
        """Compute gradient should reject zero batch size."""
        config = GradientConfig(batch_size=0)
        with pytest.raises(PolicyGradientError, match="batch_size"):
            await optimizer.compute_gradient((1.0,), (0.5,), config)

    @pytest.mark.asyncio
    async def test_compute_gradient_grad_clipping(
        self, optimizer: PolicyGradientOptimizer
    ) -> None:
        """Compute gradient should clip gradient norms."""
        large_params = (100.0, 200.0)
        rewards = (1.0, 0.0)
        config = GradientConfig(max_grad_norm=0.5)
        grad = await optimizer.compute_gradient(large_params, rewards, config)
        grad_norm = sum(g**2 for g in grad) ** 0.5
        assert grad_norm <= 0.5 + 1e-6

    @pytest.mark.asyncio
    async def test_compute_gradient_with_sgd(
        self, optimizer: PolicyGradientOptimizer
    ) -> None:
        """Compute gradient should support sgd optimizer."""
        config = GradientConfig(optimizer="sgd")
        grad = await optimizer.compute_gradient(
            (1.0, 2.0), (0.5, 0.8), config
        )
        assert len(grad) == 2

    @pytest.mark.asyncio
    async def test_compute_gradient_unknown_optimizer(
        self, optimizer: PolicyGradientOptimizer
    ) -> None:
        """Compute gradient should reject unknown optimizer."""
        config = GradientConfig(optimizer="unknown")
        with pytest.raises(PolicyGradientError, match="unknown optimizer"):
            await optimizer.compute_gradient(
                (1.0,), (0.5,), config
            )

    @pytest.mark.asyncio
    async def test_apply_gradient_step(
        self, optimizer: PolicyGradientOptimizer
    ) -> None:
        """Apply gradient step should update parameters."""
        params = (1.0, 2.0, 3.0)
        grad = (0.1, 0.2, 0.3)
        updated = await optimizer.apply_gradient_step(params, grad, 0.01)
        assert len(updated) == 3
        for i in range(3):
            assert updated[i] == params[i] - 0.01 * grad[i]

    @pytest.mark.asyncio
    async def test_apply_gradient_step_empty_params(
        self, optimizer: PolicyGradientOptimizer
    ) -> None:
        """Apply gradient step should reject empty params."""
        with pytest.raises(PolicyGradientError, match="params"):
            await optimizer.apply_gradient_step((), (0.1,), 0.01)

    @pytest.mark.asyncio
    async def test_apply_gradient_step_empty_grad(
        self, optimizer: PolicyGradientOptimizer
    ) -> None:
        """Apply gradient step should reject empty grad."""
        with pytest.raises(PolicyGradientError, match="grad"):
            await optimizer.apply_gradient_step((1.0,), (), 0.01)

    @pytest.mark.asyncio
    async def test_apply_gradient_step_length_mismatch(
        self, optimizer: PolicyGradientOptimizer
    ) -> None:
        """Apply gradient step should reject length mismatch."""
        with pytest.raises(PolicyGradientError, match="same length"):
            await optimizer.apply_gradient_step((1.0,), (0.1, 0.2), 0.01)

    @pytest.mark.asyncio
    async def test_apply_gradient_step_invalid_lr(
        self, optimizer: PolicyGradientOptimizer
    ) -> None:
        """Apply gradient step should reject invalid lr."""
        with pytest.raises(PolicyGradientError, match="lr"):
            await optimizer.apply_gradient_step((1.0,), (0.1,), 0.0)

    @pytest.mark.asyncio
    async def test_optimize_policy(
        self, optimizer: PolicyGradientOptimizer
    ) -> None:
        """Optimize policy should return gradient result."""

        def reward_fn(params: tuple[float, ...]) -> float:
            return -sum(p**2 for p in params)

        config = GradientConfig(batch_size=10, learning_rate=0.01)
        result = await optimizer.optimize_policy(
            (1.0, 2.0), reward_fn, config
        )
        assert isinstance(result, GradientResult)
        assert len(result.steps) > 0
        assert isinstance(result.final_loss, float)

    @pytest.mark.asyncio
    async def test_optimize_policy_empty_params(
        self, optimizer: PolicyGradientOptimizer
    ) -> None:
        """Optimize policy should reject empty initial params."""

        def reward_fn(params: tuple[float, ...]) -> float:
            return -sum(p**2 for p in params)

        with pytest.raises(PolicyGradientError, match="initial_params"):
            await optimizer.optimize_policy(
                (), reward_fn, GradientConfig()
            )

    @pytest.mark.asyncio
    async def test_single_param_gradient(
        self, optimizer: PolicyGradientOptimizer
    ) -> None:
        """Compute gradient with single parameter."""
        config = GradientConfig()
        grad = await optimizer.compute_gradient((0.5,), (0.9,), config)
        assert len(grad) == 1
        assert isinstance(grad[0], float)
