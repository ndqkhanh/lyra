"""Tests for the strategy_optimizer module."""

from __future__ import annotations

import pytest

from lyra_policy_optimizer.exceptions import StrategyError
from lyra_policy_optimizer.strategy_optimizer import (
    StrategyAllocation,
    StrategyConfig,
    StrategyOptimizer,
    StrategyPerformance,
)


class TestStrategyConfig:
    """Test StrategyConfig dataclass."""

    def test_default_config(self) -> None:
        """StrategyConfig should have sensible defaults."""
        config = StrategyConfig()
        assert len(config.exploration_strategies) == 4
        assert "epsilon_greedy" in config.exploration_strategies
        assert config.adaptation_rate == 0.1

    def test_custom_config(self) -> None:
        """StrategyConfig should accept custom values."""
        config = StrategyConfig(
            exploration_strategies=("ucb", "random"),
            adaptation_rate=0.05,
        )
        assert config.exploration_strategies == ("ucb", "random")
        assert config.adaptation_rate == 0.05

    def test_frozen(self) -> None:
        """StrategyConfig should be frozen."""
        config = StrategyConfig()
        with pytest.raises(AttributeError):
            config.adaptation_rate = 0.5  # type: ignore[misc]


class TestStrategyPerformance:
    """Test StrategyPerformance dataclass."""

    def test_create_performance(self) -> None:
        """StrategyPerformance should store metrics correctly."""
        perf = StrategyPerformance(
            strategy="ucb",
            avg_reward=0.82,
            success_rate=0.85,
            usage_count=30,
            last_used=1000.0,
        )
        assert perf.strategy == "ucb"
        assert perf.avg_reward == 0.82
        assert perf.success_rate == 0.85
        assert perf.usage_count == 30


class TestStrategyAllocation:
    """Test StrategyAllocation dataclass."""

    def test_create_allocation(self) -> None:
        """StrategyAllocation should store allocations correctly."""
        alloc = StrategyAllocation(
            allocations=(("ucb", 0.4), ("random", 0.6)),
            best_strategy="ucb",
            exploration_budget=100.0,
        )
        assert len(alloc.allocations) == 2
        assert alloc.best_strategy == "ucb"
        assert alloc.exploration_budget == 100.0


class TestStrategyOptimizer:
    """Test StrategyOptimizer class."""

    @pytest.fixture
    def optimizer(self) -> StrategyOptimizer:
        return StrategyOptimizer()

    @pytest.mark.asyncio
    async def test_evaluate_strategies(
        self, optimizer: StrategyOptimizer
    ) -> None:
        """Evaluate strategies should return performance for each."""
        config = StrategyConfig()
        performances = await optimizer.evaluate_strategies(config)
        assert len(performances) == 4
        for perf in performances:
            assert isinstance(perf, StrategyPerformance)
            assert perf.usage_count > 0
            assert 0 <= perf.avg_reward <= 1

    @pytest.mark.asyncio
    async def test_evaluate_strategies_empty(
        self, optimizer: StrategyOptimizer
    ) -> None:
        """Evaluate strategies should reject empty config."""
        config = StrategyConfig(exploration_strategies=())
        with pytest.raises(StrategyError, match="exploration_strategies"):
            await optimizer.evaluate_strategies(config)

    @pytest.mark.asyncio
    async def test_evaluate_strategies_invalid_rate(
        self, optimizer: StrategyOptimizer
    ) -> None:
        """Evaluate strategies should reject invalid adaptation_rate."""
        config = StrategyConfig(adaptation_rate=0.0)
        with pytest.raises(StrategyError, match="adaptation_rate"):
            await optimizer.evaluate_strategies(config)

    @pytest.mark.asyncio
    async def test_evaluate_strategies_high_rate(
        self, optimizer: StrategyOptimizer
    ) -> None:
        """Evaluate strategies should reject rate > 1."""
        config = StrategyConfig(adaptation_rate=2.0)
        with pytest.raises(StrategyError, match="adaptation_rate"):
            await optimizer.evaluate_strategies(config)

    @pytest.mark.asyncio
    async def test_allocate_resources(
        self, optimizer: StrategyOptimizer
    ) -> None:
        """Allocate resources should distribute budget."""
        performances = (
            StrategyPerformance("ucb", 0.82, 0.85, 30, 100.0),
            StrategyPerformance("random", 0.55, 0.7, 100, 100.0),
        )
        allocation = await optimizer.allocate_resources(performances, 100.0)
        assert isinstance(allocation, StrategyAllocation)
        assert len(allocation.allocations) >= 2
        assert allocation.best_strategy == "ucb"

    @pytest.mark.asyncio
    async def test_allocate_resources_empty(
        self, optimizer: StrategyOptimizer
    ) -> None:
        """Allocate resources should reject empty performances."""
        with pytest.raises(StrategyError, match="performances"):
            await optimizer.allocate_resources((), 100.0)

    @pytest.mark.asyncio
    async def test_allocate_resources_zero_budget(
        self, optimizer: StrategyOptimizer
    ) -> None:
        """Allocate resources should reject zero budget."""
        performances = (
            StrategyPerformance("ucb", 0.82, 0.85, 30, 100.0),
        )
        with pytest.raises(StrategyError, match="budget"):
            await optimizer.allocate_resources(performances, 0.0)

    @pytest.mark.asyncio
    async def test_allocate_resources_no_info(
        self, optimizer: StrategyOptimizer
    ) -> None:
        """Allocate resources should handle zero total performance."""
        performances = (
            StrategyPerformance("ucb", 0.0, 0.0, 0, 100.0),
        )
        allocation = await optimizer.allocate_resources(performances, 100.0)
        assert allocation.best_strategy == "ucb"
        assert allocation.exploration_budget == 100.0

    @pytest.mark.asyncio
    async def test_allocate_resources_single(
        self, optimizer: StrategyOptimizer
    ) -> None:
        """Allocate resources with single strategy should work."""
        performances = (
            StrategyPerformance("only_one", 0.75, 0.8, 10, 100.0),
        )
        allocation = await optimizer.allocate_resources(performances, 50.0)
        assert allocation.best_strategy == "only_one"

    @pytest.mark.asyncio
    async def test_adapt_over_time(
        self, optimizer: StrategyOptimizer
    ) -> None:
        """Adapt over time should return updated config."""
        history = (
            StrategyPerformance("ucb", 0.82, 0.85, 30, 100.0),
            StrategyPerformance("random", 0.55, 0.7, 100, 100.0),
            StrategyPerformance("epsilon_greedy", 0.75, 0.8, 50, 100.0),
        )
        config = await optimizer.adapt_over_time(history)
        assert isinstance(config, StrategyConfig)
        assert config.adaptation_rate >= 0.05
        # Best performing strategy should be first
        assert config.exploration_strategies[0] == "ucb"

    @pytest.mark.asyncio
    async def test_adapt_over_time_empty(
        self, optimizer: StrategyOptimizer
    ) -> None:
        """Adapt over time should reject empty history."""
        with pytest.raises(StrategyError, match="history"):
            await optimizer.adapt_over_time(())

    @pytest.mark.asyncio
    async def test_thompson_sampling_performance(
        self, optimizer: StrategyOptimizer
    ) -> None:
        """Thompson sampling should have the highest reward."""
        config = StrategyConfig(
            exploration_strategies=("thompson_sampling",),
        )
        performances = await optimizer.evaluate_strategies(config)
        assert len(performances) == 1
        assert performances[0].avg_reward == 0.88

    @pytest.mark.asyncio
    async def test_random_performance(
        self, optimizer: StrategyOptimizer
    ) -> None:
        """Random strategy should have the lowest reward."""
        config = StrategyConfig(
            exploration_strategies=("random",),
        )
        performances = await optimizer.evaluate_strategies(config)
        assert len(performances) == 1
        assert performances[0].avg_reward == 0.55

    @pytest.mark.asyncio
    async def test_allocation_sum(
        self, optimizer: StrategyOptimizer
    ) -> None:
        """Allocation total should not exceed budget significantly."""
        performances = (
            StrategyPerformance("ucb", 0.82, 0.85, 30, 100.0),
            StrategyPerformance("random", 0.55, 0.7, 100, 100.0),
            StrategyPerformance("epsilon_greedy", 0.75, 0.8, 50, 100.0),
        )
        allocation = await optimizer.allocate_resources(performances, 100.0)
        allocated_sum = sum(a[1] for a in allocation.allocations)
        assert allocated_sum <= 100.0 + 1e-6
