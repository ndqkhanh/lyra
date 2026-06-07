"""Meta-strategy optimization for adaptive exploration."""

from __future__ import annotations

import time
from dataclasses import dataclass

from .exceptions import StrategyError


@dataclass(frozen=True)
class StrategyConfig:
    """Configuration for meta-strategy optimization."""

    exploration_strategies: tuple[str, ...] = (
        "epsilon_greedy",
        "ucb",
        "thompson_sampling",
        "random",
    )
    adaptation_rate: float = 0.1


@dataclass(frozen=True)
class StrategyPerformance:
    """Performance metrics for a single exploration strategy."""

    strategy: str
    avg_reward: float
    success_rate: float
    usage_count: int
    last_used: float


@dataclass(frozen=True)
class StrategyAllocation:
    """Resource allocation across strategies."""

    allocations: tuple[tuple[str, float], ...]
    best_strategy: str
    exploration_budget: float


class StrategyOptimizer:
    """Optimizer for adaptive exploration strategy selection."""

    async def evaluate_strategies(
        self, config: StrategyConfig
    ) -> tuple[StrategyPerformance, ...]:
        """Evaluate all configured strategies and return their performance."""
        if not config.exploration_strategies:
            raise StrategyError("exploration_strategies must not be empty")
        if config.adaptation_rate <= 0 or config.adaptation_rate > 1:
            raise StrategyError("adaptation_rate must be in (0, 1]")

        now = time.time()
        performances: list[StrategyPerformance] = []

        for strategy in config.exploration_strategies:
            perf = self._simulate_strategy_performance(strategy, now)
            performances.append(perf)

        return tuple(performances)

    async def allocate_resources(
        self,
        performances: tuple[StrategyPerformance, ...],
        budget: float,
    ) -> StrategyAllocation:
        """Allocate a budget across strategies based on their performance."""
        if not performances:
            raise StrategyError("performances must not be empty")
        if budget <= 0:
            raise StrategyError("budget must be positive")

        total_perf = sum(
            (p.avg_reward * p.success_rate) for p in performances
        )
        if total_perf <= 0:
            total_perf = 1.0

        allocations: list[tuple[str, float]] = []
        for perf in performances:
            weight = (perf.avg_reward * perf.success_rate) / total_perf
            allocations.append((perf.strategy, round(weight * budget, 4)))

        best = max(performances, key=lambda p: p.avg_reward)

        remaining = budget - sum(a[1] for a in allocations)
        allocations.append(("remaining", round(remaining, 4)))

        return StrategyAllocation(
            allocations=tuple(allocations),
            best_strategy=best.strategy,
            exploration_budget=budget,
        )

    async def adapt_over_time(
        self, history: tuple[StrategyPerformance, ...]
    ) -> StrategyConfig:
        """Adapt strategy configuration based on historical performance."""
        if not history:
            raise StrategyError("history must not be empty")

        sorted_by_reward = sorted(
            history, key=lambda p: p.avg_reward, reverse=True
        )
        top_strategies = tuple(
            p.strategy for p in sorted_by_reward
        )

        adaptation = max(0.05, min(0.5, sum(p.avg_reward for p in history) / len(history)))

        return StrategyConfig(
            exploration_strategies=top_strategies,
            adaptation_rate=adaptation,
        )

    def _simulate_strategy_performance(
        self, strategy: str, now: float
    ) -> StrategyPerformance:
        """Simulate performance for a given strategy."""
        base_rewards = {
            "epsilon_greedy": 0.75,
            "ucb": 0.82,
            "thompson_sampling": 0.88,
            "random": 0.55,
        }
        base_usage = {
            "epsilon_greedy": 50,
            "ucb": 30,
            "thompson_sampling": 20,
            "random": 100,
        }

        avg_reward = base_rewards.get(strategy, 0.6)
        usage_count = base_usage.get(strategy, 10)
        success_rate = avg_reward + (1.0 - avg_reward) * 0.3

        return StrategyPerformance(
            strategy=strategy,
            avg_reward=avg_reward,
            success_rate=min(1.0, success_rate),
            usage_count=usage_count,
            last_used=now,
        )
