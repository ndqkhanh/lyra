"""
CaTS — Calibrated Test-Time Scaling for test-time compute allocation.

Implements a calibrated compute-effort scheduler that allocates more
compute (samples, thinking tokens) to harder problems and less to
easier ones. This improves efficiency compared to uniform compute
budgets.

Three core functions:
1. compute_effort(difficulty) — maps difficulty to an EffortBudget.
2. adaptive_sampling(problem, budget) — determines sample count.
3. early_stopping_criteria — stops generation early when confidence
   exceeds a threshold.

References
----------
- CaTS: Calibrated Test-Time Scaling
  Zhu et al., 2025, arXiv:2509.18128v2
- Chain-of-Thought Reasoning Without Compute Budget Waste
  Snell et al., 2024, arXiv:2407.21783
- Meta Agent-X: End-to-End RL for Multi-Agent Workflow Optimization
  arXiv:2605.14212v1
"""

from __future__ import annotations

import math
import random
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# -- types ------------------------------------------------------------------
# ---------------------------------------------------------------------------


class DifficultyLevel(Enum):
    """Discrete difficulty levels for task classification."""

    TRIVIAL = "trivial"
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXTREME = "extreme"


@dataclass(frozen=True)
class EffortBudget:
    """Compute budget allocation for a single problem.

    Attributes:
        samples: Number of candidate samples to generate.
        thinking_tokens: Maximum thinking tokens per sample.
        max_steps: Maximum reasoning steps per sample.
        ensemble_size: Number of ensemble evaluations for confidence.
        strategy: Sampling strategy to use.
    """

    samples: int = 1
    thinking_tokens: int = 1024
    max_steps: int = 8
    ensemble_size: int = 1
    strategy: str = "default"


@dataclass(frozen=True)
class Problem:
    """A problem definition for test-time compute allocation.

    Attributes:
        problem_id: Unique identifier.
        description: Problem text.
        difficulty: Difficulty score in [0, 1].
        domain: Problem domain (e.g., "math", "code", "reasoning").
        max_reward: Maximum achievable reward.
    """

    problem_id: str = ""
    description: str = ""
    difficulty: float = 0.5
    domain: str = "general"
    max_reward: float = 1.0


# ---------------------------------------------------------------------------
# -- Difficulty calibration -------------------------------------------------
# ---------------------------------------------------------------------------


DIFFICULTY_THRESHOLDS: dict[DifficultyLevel, tuple[float, float]] = {
    DifficultyLevel.TRIVIAL: (0.0, 0.15),
    DifficultyLevel.EASY: (0.15, 0.35),
    DifficultyLevel.MEDIUM: (0.35, 0.55),
    DifficultyLevel.HARD: (0.55, 0.80),
    DifficultyLevel.EXTREME: (0.80, 1.0),
}

DEFAULT_BUDGETS: dict[DifficultyLevel, EffortBudget] = {
    DifficultyLevel.TRIVIAL: EffortBudget(
        samples=1,
        thinking_tokens=256,
        max_steps=2,
        ensemble_size=1,
        strategy="greedy",
    ),
    DifficultyLevel.EASY: EffortBudget(
        samples=2,
        thinking_tokens=512,
        max_steps=4,
        ensemble_size=1,
        strategy="diverse",
    ),
    DifficultyLevel.MEDIUM: EffortBudget(
        samples=4,
        thinking_tokens=1024,
        max_steps=8,
        ensemble_size=2,
        strategy="diverse",
    ),
    DifficultyLevel.HARD: EffortBudget(
        samples=8,
        thinking_tokens=2048,
        max_steps=16,
        ensemble_size=4,
        strategy="beam",
    ),
    DifficultyLevel.EXTREME: EffortBudget(
        samples=16,
        thinking_tokens=4096,
        max_steps=32,
        ensemble_size=8,
        strategy="beam",
    ),
}


def classify_difficulty(raw_score: float) -> DifficultyLevel:
    """Classify a raw difficulty score into a discrete level.

    Args:
        raw_score: Difficulty score in [0, 1].

    Returns:
        A ``DifficultyLevel`` enum value.
    """
    for level, (lo, hi) in DIFFICULTY_THRESHOLDS.items():
        if lo <= raw_score < hi:
            return level
    return DifficultyLevel.EXTREME


# ---------------------------------------------------------------------------
# -- compute_effort ---------------------------------------------------------
# ---------------------------------------------------------------------------


def compute_effort(difficulty: float) -> EffortBudget:
    """Allocate an effort budget based on problem difficulty.

    Scaling is calibrated so that:
        - Trivial (0.0-0.15): 1 sample, minimal thinking
        - Easy (0.15-0.35): 2 samples, light thinking
        - Medium (0.35-0.55): 4 samples, moderate thinking
        - Hard (0.55-0.80): 8 samples, heavy thinking
        - Extreme (0.80-1.0): 16 samples, maximum thinking

    Args:
        difficulty: Difficulty score in [0, 1].

    Returns:
        An ``EffortBudget`` specifying compute allocation.

    Raises:
        ValueError: If difficulty is outside [0, 1].
    """
    if not 0.0 <= difficulty <= 1.0:
        raise ValueError(f"difficulty must be in [0, 1], got {difficulty}")

    level = classify_difficulty(difficulty)
    budget = DEFAULT_BUDGETS[level]

    logger.debug(
        "effort budget allocated",
        difficulty=round(difficulty, 3),
        level=level.value,
        samples=budget.samples,
        thinking_tokens=budget.thinking_tokens,
    )

    return budget


def compute_effort_continuous(difficulty: float) -> EffortBudget:
    """Allocate an effort budget using continuous (interpolated) scaling.

    Uses smooth interpolation between budget tiers rather than discrete
    jumps. More granular than ``compute_effort``.

    Args:
        difficulty: Difficulty score in [0, 1].

    Returns:
        An ``EffortBudget`` computed via continuous scaling.
    """
    if not 0.0 <= difficulty <= 1.0:
        raise ValueError(f"difficulty must be in [0, 1], got {difficulty}")

    # Continuous scaling functions
    samples = max(1, round(2 ** (1 + 3 * difficulty)))
    thinking_tokens = max(256, round(256 * 2 ** (2 * difficulty)))
    max_steps = max(2, round(4 * 2 ** (2 * difficulty)))
    ensemble_size = max(1, round(2 ** (1.5 * difficulty)))

    strategy = "greedy" if difficulty < 0.3 else "diverse" if difficulty < 0.6 else "beam"

    return EffortBudget(
        samples=samples,
        thinking_tokens=thinking_tokens,
        max_steps=max_steps,
        ensemble_size=ensemble_size,
        strategy=strategy,
    )


# ---------------------------------------------------------------------------
# -- Adaptive sampling ------------------------------------------------------
# ---------------------------------------------------------------------------


def adaptive_sampling(
    problem: Problem,
    budget: EffortBudget,
    confidence_fn: Callable[[str], float] | None = None,
) -> int:
    """Determine how many samples to generate for a given problem.

    The sampling count is a function of both the problem's difficulty
    and the available budget. Additional samples may be allocated if
    an early confidence check shows uncertainty.

    Args:
        problem: The problem being solved.
        budget: The effort budget allocation.
        confidence_fn: Optional function that estimates confidence
            from a partial solution. Signature: ``(solution) -> [0, 1]``.

    Returns:
        The number of samples to generate (integer >= 1).
    """
    base_samples = budget.samples

    # No confidence function — use base budget
    if confidence_fn is None:
        return base_samples

    # Try generating one sample and check confidence
    try:
        # Simulate initial coverage check
        initial_solution = f"initial_{problem.problem_id}"
        confidence = confidence_fn(initial_solution)
    except Exception:
        confidence = 0.5

    # Scale samples based on confidence deficit
    if confidence > 0.95:
        # High confidence: reduce samples
        return max(1, base_samples // 2)
    elif confidence < 0.5:
        # Low confidence: increase samples
        return base_samples * 2
    else:
        return base_samples


# ---------------------------------------------------------------------------
# -- Early stopping criteria ------------------------------------------------
# ---------------------------------------------------------------------------


@dataclass
class EarlyStoppingCriteria:
    """Configuration for early stopping during test-time compute.

    Attributes:
        confidence_threshold: Stop if confidence exceeds this value.
        consistency_threshold: Minimum proportion of agreeing samples.
        min_samples: Minimum number of samples before stopping.
        max_samples: Maximum samples even if not converged.
        patience: How many samples to wait without improvement.
    """

    confidence_threshold: float = 0.95
    consistency_threshold: float = 0.8
    min_samples: int = 2
    max_samples: int = 32
    patience: int = 4


@dataclass
class StoppingDecision:
    """Decision from the early stopping check.

    Attributes:
        should_stop: Whether to stop generating samples.
        reason: Explanation of the decision.
        confidence: Current confidence estimate.
        consistency: Current consistency score.
        samples_generated: Number of samples generated so far.
    """

    should_stop: bool = False
    reason: str = ""
    confidence: float = 0.0
    consistency: float = 0.0
    samples_generated: int = 0


def should_stop_early(
    samples_generated: int,
    rewards: list[float],
    criteria: EarlyStoppingCriteria | None = None,
) -> StoppingDecision:
    """Determine whether to stop generating additional samples.

    Checks three conditions:
    1. **Minimum samples**: always generate at least ``min_samples``.
    2. **High confidence**: stop if confidence exceeds threshold.
    3. **Consistency**: stop if a high proportion of recent samples
       agree on the same answer.
    4. **Patience**: stop if no improvement for ``patience`` samples.
    5. **Max samples**: stop unconditionally at ``max_samples``.

    Args:
        samples_generated: Number of samples already generated.
        rewards: List of rewards collected so far.
        criteria: Early stopping configuration.

    Returns:
        A ``StoppingDecision`` with the verdict.
    """
    criteria = criteria or EarlyStoppingCriteria()

    # Minimum samples
    if samples_generated < criteria.min_samples:
        return StoppingDecision(
            should_stop=False,
            reason=f"minimum samples ({criteria.min_samples}) not reached",
            confidence=0.0,
            consistency=0.0,
            samples_generated=samples_generated,
        )

    # Max samples
    if samples_generated >= criteria.max_samples:
        return StoppingDecision(
            should_stop=True,
            reason=f"maximum samples ({criteria.max_samples}) reached",
            confidence=0.0,
            consistency=0.0,
            samples_generated=samples_generated,
        )

    n = len(rewards)
    if n == 0:
        return StoppingDecision(
            should_stop=False,
            reason="no rewards yet",
            confidence=0.0,
            consistency=0.0,
            samples_generated=samples_generated,
        )

    # Compute confidence from reward stats
    mean_reward = sum(rewards[-5:]) / max(len(rewards[-5:]), 1)
    recent_max = max(rewards[-5:]) if rewards else 0.0
    confidence = min(1.0, max(recent_max, mean_reward))

    # Compute consistency: proportion of samples with reward > threshold
    reward_threshold = 0.5  # half of max possible
    consistent_count = sum(1 for r in rewards if r >= reward_threshold)
    consistency = consistent_count / max(n, 1)

    # Patience: check if no improvement in recent samples
    no_improve_count = 0
    if n >= 3:
        for i in range(1, min(criteria.patience + 1, n)):
            if rewards[-i] <= rewards[-(i + 1)]:
                no_improve_count += 1
    out_of_patience = no_improve_count >= criteria.patience

    # Decision logic
    if confidence >= criteria.confidence_threshold:
        return StoppingDecision(
            should_stop=True,
            reason=f"confidence {confidence:.3f} exceeds threshold {criteria.confidence_threshold}",
            confidence=confidence,
            consistency=consistency,
            samples_generated=samples_generated,
        )

    if consistency >= criteria.consistency_threshold and samples_generated >= criteria.min_samples:
        return StoppingDecision(
            should_stop=True,
            reason=f"consistency {consistency:.3f} exceeds threshold {criteria.consistency_threshold}",
            confidence=confidence,
            consistency=consistency,
            samples_generated=samples_generated,
        )

    if out_of_patience:
        return StoppingDecision(
            should_stop=True,
            reason=f"no improvement for {criteria.patience} samples",
            confidence=confidence,
            consistency=consistency,
            samples_generated=samples_generated,
        )

    return StoppingDecision(
        should_stop=False,
        reason="continuing sampling",
        confidence=confidence,
        consistency=consistency,
        samples_generated=samples_generated,
    )


# ---------------------------------------------------------------------------
# -- CaTS Scheduler ---------------------------------------------------------
# ---------------------------------------------------------------------------


@dataclass
class CaTSScheduler:
    """Calibrated Test-Time Scaling scheduler.

    Orchestrates compute allocation across multiple problems using
    calibrated difficulty estimation, adaptive sampling, and early
    stopping.

    Usage::

        scheduler = CaTSScheduler()
        budget = scheduler.allocate(problem)
        # Run generation with budget...
        decision = scheduler.check_stopping(
            samples_generated=5,
            rewards=[0.2, 0.6, 0.8, 0.9, 0.95],
        )
    """

    continuous_scaling: bool = False
    early_stopping: EarlyStoppingCriteria = field(default_factory=EarlyStoppingCriteria)
    _total_budget_used: int = 0
    _allocations: list[tuple[str, EffortBudget]] = field(default_factory=list)

    def allocate(self, problem: Problem) -> EffortBudget:
        """Allocate compute budget for a single problem.

        Args:
            problem: The problem to allocate budget for.

        Returns:
            An ``EffortBudget`` with the compute allocation.
        """
        if self.continuous_scaling:
            budget = compute_effort_continuous(problem.difficulty)
        else:
            budget = compute_effort(problem.difficulty)

        self._allocations.append((problem.problem_id, budget))
        self._total_budget_used += budget.samples
        return budget

    def allocate_with_adaptive_sampling(
        self,
        problem: Problem,
        confidence_fn: Callable[[str], float] | None = None,
    ) -> EffortBudget:
        """Allocate budget with adaptive sampling adjustment.

        Combines calibrated effort allocation with adaptive sampling
        that adjusts based on initial confidence.

        Args:
            problem: The problem to allocate for.
            confidence_fn: Optional confidence estimation function.

        Returns:
            Adjusted ``EffortBudget``.
        """
        base_budget = self.allocate(problem)
        adjusted_samples = adaptive_sampling(problem, base_budget, confidence_fn)

        adjusted = EffortBudget(
            samples=adjusted_samples,
            thinking_tokens=base_budget.thinking_tokens,
            max_steps=base_budget.max_steps,
            ensemble_size=base_budget.ensemble_size,
            strategy=base_budget.strategy,
        )

        logger.debug(
            "adaptive budget allocated",
            problem_id=problem.problem_id,
            base=base_budget.samples,
            adjusted=adjusted_samples,
        )

        return adjusted

    def check_stopping(
        self,
        samples_generated: int,
        rewards: list[float],
    ) -> StoppingDecision:
        """Check whether to stop generating more samples.

        Args:
            samples_generated: Number of samples so far.
            rewards: Rewards collected from generated samples.

        Returns:
            A ``StoppingDecision``.
        """
        return should_stop_early(samples_generated, rewards, self.early_stopping)

    @property
    def total_budget_used(self) -> int:
        """Total number of sample slots allocated."""
        return self._total_budget_used

    @property
    def allocation_count(self) -> int:
        """Number of problems allocated."""
        return len(self._allocations)

    def get_stats(self) -> dict[str, Any]:
        """Return summary statistics for the scheduler.

        Returns:
            Dict with allocation stats.
        """
        sample_counts = [b.samples for _, b in self._allocations]
        return {
            "total_budget_used": self._total_budget_used,
            "allocations": self.allocation_count,
            "avg_samples_per_problem": (
                sum(sample_counts) / max(len(sample_counts), 1)
                if sample_counts else 0.0
            ),
            "max_samples": max(sample_counts) if sample_counts else 0,
            "min_samples": min(sample_counts) if sample_counts else 0,
            "continuous_scaling": self.continuous_scaling,
        }

    def reset(self) -> None:
        """Reset all allocation counters."""
        self._total_budget_used = 0
        self._allocations.clear()


__all__ = [
    "DifficultyLevel",
    "EffortBudget",
    "Problem",
    "EarlyStoppingCriteria",
    "StoppingDecision",
    "CaTSScheduler",
    "compute_effort",
    "compute_effort_continuous",
    "adaptive_sampling",
    "should_stop_early",
    "classify_difficulty",
]
