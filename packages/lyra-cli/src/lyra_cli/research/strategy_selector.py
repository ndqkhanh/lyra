"""
Strategy selector using UCB1 bandit algorithm.

Learns which research strategy (breadth-first, depth-first, best-first)
performs best for different query types by treating strategy selection
as a multi-armed bandit problem.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from math import log, sqrt
from typing import Dict, List, Optional


class StrategyType(Enum):
    """Available research exploration strategies."""

    BREADTH_FIRST = auto()
    DEPTH_FIRST = auto()
    BEST_FIRST = auto()


# Default query type categories — consumers can add more.
DEFAULT_QUERY_TYPES: List[str] = [
    "factual",
    "comparative",
    "exploratory",
    "technical",
    "controversial",
]


@dataclass(frozen=True)
class StrategyResult:
    """Feedback record for a single strategy execution."""

    strategy_type: StrategyType
    query_type: str
    reward: float  # 0.0 – 1.0, higher is better
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class StrategySelector:
    """
    UCB1 bandit-based strategy selector.

    Maintains separate bandit arms per query type.  The UCB1 formula
    balances exploration (try under-explored strategies) with
    exploitation (use strategies that have worked before).

    UCB1 arm value::

        value = mean_reward + sqrt(2 * ln(total_pulls) / arm_pulls + eps)
    """

    def __init__(
        self,
        exploration_constant: float = 2.0,
        query_types: Optional[List[str]] = None,
    ) -> None:
        self.exploration_constant = exploration_constant

        # Available strategies
        self._strategies: List[StrategyType] = list(StrategyType)

        # Per-query-type counts and cumulative rewards
        self._query_types: List[str] = query_types or DEFAULT_QUERY_TYPES.copy()

        # counts[query_type][strategy_name] -> int
        self._counts: Dict[str, Dict[str, int]] = {}
        # rewards[query_type][strategy_name] -> float (cumulative)
        self._rewards: Dict[str, Dict[str, float]] = {}

        # Feedback history
        self._history: List[StrategyResult] = []

        self._init_bandits()

    def _init_bandits(self) -> None:
        """Initialise bandit arms for each query type."""
        for qt in self._query_types:
            self._counts[qt] = {s.name: 0 for s in self._strategies}
            self._rewards[qt] = {s.name: 0.0 for s in self._strategies}

    # ---- public API -----------------------------------------------------

    def select_strategy(
        self,
        query_type: str = "factual",
    ) -> StrategyType:
        """
        Select the best strategy for *query_type* using UCB1.

        Falls back to BREADTH_FIRST if the query type is unknown.
        """
        if query_type not in self._counts:
            return StrategyType.BREADTH_FIRST

        counts = self._counts[query_type]
        rewards = self._rewards[query_type]

        total_pulls = sum(counts.values())

        # If any arm hasn't been pulled, try it first (exploration bonus)
        for s in self._strategies:
            if counts[s.name] == 0:
                return s

        # UCB1 selection
        best_strategy: Optional[StrategyType] = None
        best_value = -float("inf")

        for s in self._strategies:
            mean = rewards[s.name] / counts[s.name]
            bonus = sqrt(
                (2.0 * log(total_pulls)) / counts[s.name]
            )
            value = mean + self.exploration_constant * bonus

            if value > best_value:
                best_value = value
                best_strategy = s

        return best_strategy or StrategyType.BREADTH_FIRST

    def update_feedback(
        self,
        strategy: StrategyType,
        reward: float,
        query_type: str = "factual",
    ) -> None:
        """Record the reward for a strategy execution."""
        reward = max(0.0, min(1.0, reward))

        self._history.append(StrategyResult(
            strategy_type=strategy,
            query_type=query_type,
            reward=reward,
        ))

        if query_type in self._counts:
            self._counts[query_type][strategy.name] += 1
            self._rewards[query_type][strategy.name] += reward

    def add_query_type(self, query_type: str) -> None:
        """Register a new query type for bandit tracking."""
        if query_type not in self._counts:
            self._counts[query_type] = {s.name: 0 for s in self._strategies}
            self._rewards[query_type] = {s.name: 0.0 for s in self._strategies}
            self._query_types.append(query_type)

    # ---- analysis -------------------------------------------------------

    def get_strategy_stats(self, query_type: str) -> Dict[str, dict]:
        """Return per-strategy statistics for a query type."""
        if query_type not in self._counts:
            return {}

        counts = self._counts[query_type]
        rewards = self._rewards[query_type]

        stats: Dict[str, dict] = {}
        for s in self._strategies:
            pulls = counts[s.name]
            stats[s.name] = {
                "pulls": pulls,
                "total_reward": round(rewards[s.name], 3),
                "mean_reward": round(
                    rewards[s.name] / pulls, 3
                ) if pulls > 0 else 0.0,
            }
        return stats

    def get_confusion_matrix(self) -> Dict[str, Dict[str, float]]:
        """
        Build a confusion matrix showing strategy performance per query type.

        Returns {query_type: {strategy_name: mean_reward}}.
        """
        matrix: Dict[str, Dict[str, float]] = {}
        for qt in self._query_types:
            if qt not in self._counts:
                continue
            counts = self._counts[qt]
            rewards = self._rewards[qt]
            row: Dict[str, float] = {}
            for s in self._strategies:
                pulls = counts[s.name]
                row[s.name] = round(
                    rewards[s.name] / pulls, 3
                ) if pulls > 0 else 0.0
            matrix[qt] = row
        return matrix

    def get_history(self) -> List[StrategyResult]:
        """Return the full feedback history."""
        return self._history.copy()
