"""GEAR-Evolve Self-Modifying Search.

Self-modifying search controller that learns which search strategies
perform best for different problem types and adapts the
exploration/exploitation balance over time.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import Any

from .models import GEARStrategy

logger = logging.getLogger(__name__)


class GEAREvolve:
    """Self-modifying search controller.

    Maintains a registry of search strategies, selects the best one
    for each problem, and continuously updates strategy performance
    based on outcomes. Over time it adapts exploration/exploitation
    and can discover or prune strategies.
    """

    def __init__(
        self,
        *,
        initial_exploration: float = 0.5,
        decay_factor: float = 0.95,
        min_exploration: float = 0.05,
        seed: int | None = None,
    ) -> None:
        """Initialise the GEAR-Evolve controller.

        Args:
            initial_exploration: Starting exploration weight (0-1).
            decay_factor: Multiplier applied to exploration each adaptation step.
            min_exploration: Floor for exploration weight.
            seed: Optional RNG seed for reproducibility.
        """
        self._strategies: dict[str, GEARStrategy] = {}
        self._global_exploration = initial_exploration
        self._decay_factor = decay_factor
        self._min_exploration = min_exploration
        self._performance_log: list[tuple[str, float, datetime]] = []

        import random

        self._rng = random.Random(seed)

    # ------------------------------------------------------------------
    # Strategy registry
    # ------------------------------------------------------------------

    def register_strategy(self, strategy: GEARStrategy) -> None:
        """Add a search strategy to the registry.

        Args:
            strategy: The strategy to register.
        """
        self._strategies[strategy.strategy_id] = strategy
        logger.info("Registered strategy '%s'", strategy.strategy_id)

    @property
    def strategy_count(self) -> int:
        """Number of registered strategies."""
        return len(self._strategies)

    def list_strategies(self) -> list[GEARStrategy]:
        """Return all registered strategies."""
        return list(self._strategies.values())

    # ------------------------------------------------------------------
    # Strategy selection
    # ------------------------------------------------------------------

    def select_strategy(
        self,
        problem: str | None = None,
        *,
        problem_features: Sequence[float] | None = None,
    ) -> GEARStrategy:
        """Pick the best strategy for a given problem.

        Balances between exploitation (best historical performer) and
        exploration (trying under-used strategies). When no strategies
        exist a default is created on-the-fly.

        Args:
            problem: Human-readable problem description (optional).
            problem_features: Numeric feature vector for strategy matching.

        Returns:
            The selected strategy.
        """
        if not self._strategies:
            default = GEARStrategy(strategy_id="default")
            self._strategies[default.strategy_id] = default
            return default

        # Epsilon-greedy: exploit vs explore
        if self._rng.random() < self._global_exploration:
            # Explore — pick a random strategy biased toward under-used ones
            chosen = self._explore()
            logger.debug("Exploring with strategy '%s'", chosen.strategy_id)
        else:
            # Exploit — pick the best by success rate
            chosen = self._exploit(features=problem_features)
            logger.debug("Exploiting with strategy '%s'", chosen.strategy_id)

        return chosen

    def _exploit(
        self,
        features: Sequence[float] | None = None,
    ) -> GEARStrategy:
        """Return the strategy with the highest success rate.

        When feature vectors are provided, strategies with similar
        problem_features are weighted more heavily.
        """
        best: GEARStrategy | None = None
        best_score = float("-inf")

        for s in self._strategies.values():
            score = s.success_rate
            if features is not None and s.problem_features:
                score += self._feature_similarity(features, s.problem_features)
            if score > best_score:
                best_score = score
                best = s

        return best if best is not None else next(iter(self._strategies.values()))

    def _explore(self) -> GEARStrategy:
        """Pick a strategy favouring those with fewer uses."""
        strategies = list(self._strategies.values())
        if not strategies:
            return GEARStrategy(strategy_id="fallback")

        # Weight inversely by total_uses so under-used strategies are favoured
        total_uses = sum(max(1, s.total_uses) for s in strategies)
        weights = []
        for s in strategies:
            inv_weight = total_uses / max(1, s.total_uses)
            weights.append(inv_weight)

        return self._rng.choices(strategies, weights=weights, k=1)[0]

    @staticmethod
    def _feature_similarity(
        a: Sequence[float],
        b: Sequence[float],
    ) -> float:
        """Cosine-like similarity between two feature vectors."""
        if not a or not b:
            return 0.0
        min_len = min(len(a), len(b))
        dot = sum(a[i] * b[i] for i in range(min_len))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b) / 2.0  # scaled to [0, ~0.5]

    # ------------------------------------------------------------------
    # Search execution
    # ------------------------------------------------------------------

    def execute_search(
        self,
        strategy: GEARStrategy,
        problem: str,
        *,
        searcher: Callable[[GEARStrategy, str], Any] | None = None,
    ) -> Any:
        """Run a search using the given strategy.

        Args:
            strategy: The strategy to employ.
            problem: Problem description or query.
            searcher: Callable that performs the actual search.
                      Defaults to a no-op.

        Returns:
            Search result (type varies by searcher).
        """
        logger.info("Executing search '%s' for problem: %.80s", strategy.strategy_id, problem)

        if searcher is not None:
            result = searcher(strategy, problem)
        else:
            result = {"strategy": strategy.strategy_id, "problem": problem, "status": "noop"}

        # Update usage metadata
        updated = GEARStrategy(
            strategy_id=strategy.strategy_id,
            problem_features=strategy.problem_features,
            success_rate=strategy.success_rate,
            exploration_weight=strategy.exploration_weight,
            total_uses=strategy.total_uses + 1,
            last_used=datetime.now(UTC),
        )
        self._strategies[strategy.strategy_id] = updated

        return result

    # ------------------------------------------------------------------
    # Performance feedback
    # ------------------------------------------------------------------

    def update_strategy_performance(
        self,
        strategy: GEARStrategy,
        outcome: float,
    ) -> None:
        """Update a strategy's success rate based on a search outcome.

        Uses exponential moving average for smooth adaptation.

        Args:
            strategy: The strategy to update.
            outcome: 1.0 for success, 0.0 for failure, or intermediate.
        """
        if not 0.0 <= outcome <= 1.0:
            raise ValueError(f"outcome must be in [0, 1], got {outcome}")

        alpha = 0.1  # EMA smoothing factor
        new_rate = alpha * outcome + (1 - alpha) * strategy.success_rate

        updated = GEARStrategy(
            strategy_id=strategy.strategy_id,
            problem_features=strategy.problem_features,
            success_rate=round(new_rate, 4),
            exploration_weight=strategy.exploration_weight,
            total_uses=strategy.total_uses,
            last_used=strategy.last_used,
        )
        self._strategies[strategy.strategy_id] = updated
        self._performance_log.append((strategy.strategy_id, outcome, datetime.now(UTC)))

        logger.debug(
            "Strategy '%s' updated: success_rate=%.4f (outcome=%.2f)",
            strategy.strategy_id,
            new_rate,
            outcome,
        )

    # ------------------------------------------------------------------
    # Exploration / exploitation adaptation
    # ------------------------------------------------------------------

    def adapt_exploration(
        self,
        performance_history: Sequence[float] | None = None,
    ) -> float:
        """Adjust the global exploration/exploitation balance.

        Decays exploration over time (favour exploitation as strategies
        mature) but can also adjust upward if recent performance is poor.

        Args:
            performance_history: Recent outcomes (optional, for adaptive logic).

        Returns:
            New exploration weight.
        """
        # Base decay
        self._global_exploration *= self._decay_factor

        # If recent performance is declining, boost exploration
        if performance_history and len(performance_history) >= 3:
            recent = list(performance_history)[-3:]
            if sum(recent) / len(recent) < 0.3:
                boost = 0.15
                self._global_exploration = min(0.8, self._global_exploration + boost)
                logger.debug(
                    "Performance low, boosting exploration to %.3f", self._global_exploration
                )

        self._global_exploration = max(self._min_exploration, self._global_exploration)

        logger.info("Adapted exploration weight to %.4f", self._global_exploration)
        return self._global_exploration

    @property
    def exploration_weight(self) -> float:
        """Current global exploration weight."""
        return self._global_exploration

    # ------------------------------------------------------------------
    # Strategy discovery & pruning
    # ------------------------------------------------------------------

    def discover_new_strategies(
        self,
        *,
        count: int = 1,
        generator: Callable[[], GEARStrategy] | None = None,
    ) -> list[GEARStrategy]:
        """Generate novel search strategies.

        Either uses the provided generator callable or creates a
        default randomised strategy. This enables open-ended
        exploration of the search-strategy space.

        Args:
            count: How many new strategies to create.
            generator: Optional factory for custom strategy generation.

        Returns:
            Newly created strategies.
        """
        new_strategies: list[GEARStrategy] = []
        for _ in range(count):
            if generator is not None:
                strategy = generator()
            else:
                strategy = GEARStrategy(
                    exploration_weight=self._global_exploration,
                )
            self._strategies[strategy.strategy_id] = strategy
            new_strategies.append(strategy)

        logger.info("Discovered %d new strategy/strategies", count)
        return new_strategies

    def prune_ineffective_strategies(self, threshold: float = 0.1) -> int:
        """Remove strategies whose success rate falls below *threshold*.

        A strategy must have been tried at least 5 times before being
        eligible for pruning, to avoid discarding strategies prematurely.

        Args:
            threshold: Minimum success rate to survive.

        Returns:
            Number of strategies pruned.
        """
        to_remove = [
            sid
            for sid, s in self._strategies.items()
            if s.total_uses >= 5 and s.success_rate < threshold
        ]

        for sid in to_remove:
            del self._strategies[sid]
            logger.info("Pruned underperforming strategy '%s' (rate=%.3f)", sid, 0.0)

        return len(to_remove)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def get_best_strategy(self) -> GEARStrategy | None:
        """Return the strategy with the highest success rate."""
        if not self._strategies:
            return None
        return max(self._strategies.values(), key=lambda s: s.success_rate)

    def summary(self) -> dict[str, Any]:
        """Return a summary dict of the controller state."""
        best = self.get_best_strategy()
        return {
            "total_strategies": len(self._strategies),
            "exploration_weight": self._global_exploration,
            "best_strategy": best.strategy_id if best else None,
            "best_success_rate": best.success_rate if best else 0.0,
            "total_logged_outcomes": len(self._performance_log),
        }
