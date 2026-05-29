"""
Reasoning Orchestrator - Adaptive compute allocation and strategy selection.
"""

import time
from typing import Optional

from ..types import (
    ComputeBudget,
    DifficultyEstimate,
    DifficultyLevel,
    ReasoningConfig,
    ReasoningDepth,
    ReasoningStrategy,
)


class DifficultyEstimator:
    """Estimates task difficulty for compute allocation."""

    def __init__(self, model: str = "claude-3-5-sonnet-20241022"):
        self.model = model

    def estimate(self, task: str) -> DifficultyEstimate:
        """
        Estimate task difficulty.

        Uses heuristics based on:
        - Task length
        - Complexity indicators (math, code, reasoning keywords)
        - Question structure
        """
        # Simple heuristic-based estimation
        task_lower = task.lower()

        # Count complexity indicators
        complexity_score = 0

        # Math indicators
        math_keywords = ["prove", "calculate", "derive", "theorem", "equation"]
        complexity_score += sum(1 for kw in math_keywords if kw in task_lower)

        # Reasoning indicators
        reasoning_keywords = ["why", "how", "explain", "analyze", "compare"]
        complexity_score += sum(0.5 for kw in reasoning_keywords if kw in task_lower)

        # Multi-step indicators
        if "step" in task_lower or "first" in task_lower or "then" in task_lower:
            complexity_score += 1

        # Length factor
        word_count = len(task.split())
        if word_count > 100:
            complexity_score += 2
        elif word_count > 50:
            complexity_score += 1

        # Determine difficulty level
        if complexity_score >= 5:
            level = DifficultyLevel.VERY_HARD
            confidence = 0.8
        elif complexity_score >= 3:
            level = DifficultyLevel.HARD
            confidence = 0.75
        elif complexity_score >= 2:
            level = DifficultyLevel.MEDIUM
            confidence = 0.7
        elif complexity_score >= 1:
            level = DifficultyLevel.EASY
            confidence = 0.65
        else:
            level = DifficultyLevel.TRIVIAL
            confidence = 0.6

        # Recommend strategy based on difficulty
        if level in [DifficultyLevel.VERY_HARD, DifficultyLevel.HARD]:
            strategy = ReasoningStrategy.TREE_SEARCH
        elif "hypothesis" in task_lower or "propose" in task_lower:
            strategy = ReasoningStrategy.HYPOTHESIS
        elif "debate" in task_lower or "perspectives" in task_lower:
            strategy = ReasoningStrategy.DEBATE
        else:
            strategy = ReasoningStrategy.CHAIN_OF_THOUGHT

        # Recommend budget based on difficulty
        budget = self._create_budget(level)

        reasoning = f"Task complexity score: {complexity_score}. Detected {level.value} difficulty."

        return DifficultyEstimate(
            level=level,
            confidence=confidence,
            reasoning=reasoning,
            recommended_strategy=strategy,
            recommended_budget=budget,
        )

    def _create_budget(self, level: DifficultyLevel) -> ComputeBudget:
        """Create compute budget based on difficulty."""
        budget_map = {
            DifficultyLevel.TRIVIAL: (1000, 30, 10),
            DifficultyLevel.EASY: (2000, 60, 20),
            DifficultyLevel.MEDIUM: (5000, 120, 30),
            DifficultyLevel.HARD: (10000, 300, 50),
            DifficultyLevel.VERY_HARD: (20000, 600, 100),
        }

        max_tokens, max_time, max_steps = budget_map[level]

        return ComputeBudget(
            max_tokens=max_tokens,
            max_time_seconds=max_time,
            max_steps=max_steps,
        )


class StrategySelector:
    """Selects optimal reasoning strategy for a task."""

    def __init__(self):
        self.strategy_history = {}

    def select(
        self,
        task: str,
        difficulty: DifficultyEstimate,
        config: ReasoningConfig,
    ) -> ReasoningStrategy:
        """
        Select reasoning strategy.

        Priority:
        1. User-specified strategy (if not AUTO)
        2. Difficulty-based recommendation
        3. Task-based heuristics
        """
        # If user specified a strategy, use it
        if config.strategy != ReasoningStrategy.AUTO:
            return config.strategy

        # Use difficulty-based recommendation
        return difficulty.recommended_strategy

    def record_performance(
        self,
        strategy: ReasoningStrategy,
        success: bool,
        tokens: int,
        duration: float,
    ) -> None:
        """Record strategy performance for future selection."""
        if strategy not in self.strategy_history:
            self.strategy_history[strategy] = {
                "uses": 0,
                "successes": 0,
                "total_tokens": 0,
                "total_duration": 0.0,
            }

        stats = self.strategy_history[strategy]
        stats["uses"] += 1
        if success:
            stats["successes"] += 1
        stats["total_tokens"] += tokens
        stats["total_duration"] += duration


class ComputeAllocator:
    """Allocates compute budget based on task and depth."""

    def allocate(
        self,
        difficulty: DifficultyEstimate,
        config: ReasoningConfig,
    ) -> ComputeBudget:
        """
        Allocate compute budget.

        Considers:
        - Task difficulty
        - Requested depth
        - User-specified limits
        """
        # Start with difficulty-based budget
        base_budget = difficulty.recommended_budget

        # Adjust based on depth
        depth_multipliers = {
            ReasoningDepth.QUICK: 0.5,
            ReasoningDepth.STANDARD: 1.0,
            ReasoningDepth.COMPREHENSIVE: 2.0,
        }

        multiplier = depth_multipliers[config.depth]

        # Apply user limits
        max_tokens = min(
            int(base_budget.max_tokens * multiplier),
            config.max_tokens,
        )

        max_steps = min(
            int(base_budget.max_steps * multiplier),
            config.max_steps,
        )

        # Time scales with tokens
        max_time = base_budget.max_time_seconds * multiplier

        return ComputeBudget(
            max_tokens=max_tokens,
            max_time_seconds=max_time,
            max_steps=max_steps,
        )


class ReasoningOrchestrator:
    """
    Orchestrates reasoning execution with adaptive compute allocation.

    Responsibilities:
    - Estimate task difficulty
    - Select reasoning strategy
    - Allocate compute budget
    - Monitor execution
    - Decide when to stop
    """

    def __init__(self, model: str = "claude-3-5-sonnet-20241022"):
        self.difficulty_estimator = DifficultyEstimator(model)
        self.strategy_selector = StrategySelector()
        self.compute_allocator = ComputeAllocator()

    def prepare(
        self,
        task: str,
        config: Optional[ReasoningConfig] = None,
    ) -> tuple[ReasoningStrategy, ComputeBudget, DifficultyEstimate]:
        """
        Prepare for reasoning execution.

        Returns:
            (strategy, budget, difficulty_estimate)
        """
        if config is None:
            config = ReasoningConfig()

        # Estimate difficulty
        difficulty = self.difficulty_estimator.estimate(task)

        # Select strategy
        strategy = self.strategy_selector.select(task, difficulty, config)

        # Allocate budget
        budget = self.compute_allocator.allocate(difficulty, config)

        return strategy, budget, difficulty

    def should_stop(
        self,
        budget: ComputeBudget,
        steps_count: int,
        current_score: float,
        threshold: float = 0.8,
    ) -> bool:
        """
        Decide if reasoning should stop early.

        Stop if:
        - Budget exhausted
        - High confidence reached
        - Diminishing returns detected
        """
        # Budget exhausted
        if not budget.has_budget():
            return True

        # High confidence reached
        if current_score >= threshold and steps_count >= 5:
            return True

        # Minimum steps not reached
        if steps_count < 3:
            return False

        return False

    def record_execution(
        self,
        strategy: ReasoningStrategy,
        success: bool,
        tokens: int,
        duration: float,
    ) -> None:
        """Record execution for learning."""
        self.strategy_selector.record_performance(
            strategy, success, tokens, duration
        )
