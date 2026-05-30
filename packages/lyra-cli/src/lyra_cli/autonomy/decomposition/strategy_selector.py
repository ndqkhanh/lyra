"""Strategy Selector — selects the optimal decomposition strategy based on goal type.

Part of the intelligent goal decomposer (Step 5.1).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class DecompositionStrategy(StrEnum):
    TOP_DOWN = "top_down"
    BOTTOM_UP = "bottom_up"
    BREADTH_FIRST = "breadth_first"
    DEPTH_FIRST = "depth_first"
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    HYBRID = "hybrid"


@dataclass(frozen=True)
class StrategyRecommendation:
    strategy: DecompositionStrategy
    confidence: float
    reasoning: str
    estimated_subgoals: int
    parallelism_suitable: bool


class StrategySelector:
    """Selects the optimal goal decomposition strategy based on goal characteristics.

    Analyzes goal type, complexity, dependencies, and parallelism potential
    to recommend the best decomposition approach.

    Usage::

        selector = StrategySelector()
        rec = selector.select(
            goal_type="architecture_design",
            complexity=0.8,
            has_dependencies=True,
        )
        print(f"Use {rec.strategy.value} with confidence {rec.confidence}")
    """

    # Strategy preferences by goal characteristic
    _STRATEGY_SCORES: dict[DecompositionStrategy, dict[str, float]] = {
        DecompositionStrategy.TOP_DOWN: {
            "architecture_design": 0.95,
            "system_design": 0.9,
            "refactoring": 0.85,
            "planning": 0.9,
            "research": 0.7,
            "implementation": 0.5,
            "debugging": 0.4,
            "default": 0.6,
        },
        DecompositionStrategy.BOTTOM_UP: {
            "implementation": 0.85,
            "debugging": 0.8,
            "testing": 0.8,
            "refactoring": 0.7,
            "default": 0.5,
        },
        DecompositionStrategy.BREADTH_FIRST: {
            "research": 0.9,
            "exploration": 0.95,
            "analysis": 0.85,
            "default": 0.5,
        },
        DecompositionStrategy.DEPTH_FIRST: {
            "debugging": 0.9,
            "implementation": 0.75,
            "optimization": 0.8,
            "default": 0.4,
        },
        DecompositionStrategy.PARALLEL: {
            "testing": 0.9,
            "data_processing": 0.95,
            "benchmarking": 0.9,
            "implementation": 0.7,
            "default": 0.5,
        },
        DecompositionStrategy.SEQUENTIAL: {
            "planning": 0.85,
            "deployment": 0.9,
            "migration": 0.85,
            "default": 0.5,
        },
        DecompositionStrategy.HYBRID: {
            "architecture_design": 0.8,
            "system_design": 0.85,
            "refactoring": 0.75,
            "research": 0.6,
            "default": 0.4,
        },
    }

    def select(
        self,
        goal_type: str = "default",
        complexity: float = 0.5,
        has_dependencies: bool = False,
        is_parallelizable: bool = False,
        estimated_scope: int = 5,
    ) -> StrategyRecommendation:
        scores: list[tuple[DecompositionStrategy, float]] = []

        for strategy, type_scores in self._STRATEGY_SCORES.items():
            base = type_scores.get(goal_type, type_scores["default"])

            # Adjust for complexity
            if complexity > 0.7 and strategy in (
                DecompositionStrategy.TOP_DOWN,
                DecompositionStrategy.HYBRID,
            ):
                base += 0.1
            elif complexity < 0.3 and strategy in (
                DecompositionStrategy.BOTTOM_UP,
                DecompositionStrategy.DEPTH_FIRST,
            ):
                base += 0.1

            # Adjust for dependencies
            if has_dependencies and strategy == DecompositionStrategy.SEQUENTIAL:
                base += 0.15
            elif not has_dependencies and strategy == DecompositionStrategy.PARALLEL:
                base += 0.15

            # Adjust for parallelizability
            if is_parallelizable and strategy == DecompositionStrategy.PARALLEL:
                base += 0.1

            scores.append((strategy, min(base, 1.0)))

        scores.sort(key=lambda x: x[1], reverse=True)
        best_strategy, best_score = scores[0]

        return StrategyRecommendation(
            strategy=best_strategy,
            confidence=best_score,
            reasoning=self._build_reasoning(
                best_strategy, goal_type, complexity, has_dependencies
            ),
            estimated_subgoals=max(1, estimated_scope),
            parallelism_suitable=(
                is_parallelizable
                or best_strategy in (DecompositionStrategy.PARALLEL, DecompositionStrategy.HYBRID)
            ),
        )

    @staticmethod
    def _build_reasoning(
        strategy: DecompositionStrategy,
        goal_type: str,
        complexity: float,
        has_dependencies: bool,
    ) -> str:
        parts = [f"Selected {strategy.value} for '{goal_type}'"]
        if complexity > 0.7:
            parts.append("due to high complexity")
        elif complexity < 0.3:
            parts.append("due to low complexity")
        if has_dependencies and strategy == DecompositionStrategy.SEQUENTIAL:
            parts.append("with inter-dependency handling")
        return ". ".join(parts)
