"""Safety controls for Lyra AGI cost management.

Implements three safeguards:
- CircuitBreaker: Hard $5/session spend limit
- LoopDetector: Blocks tasks after 3 consecutive low-quality scores
- BudgetDegrader: Downgrades model tier as session spend increases
"""

from __future__ import annotations

import logging
import time
from typing import Any

from lyra_cost.models import (
    LoopDetectionResult,
    ModelTier,
    SessionBudget,
)

logger = logging.getLogger(__name__)

# Quality scores are expected to be in [0, 1] range. A score <= LOW_QUALITY_THRESHOLD
# is considered low and counts toward the consecutive-low counter.
_LOW_QUALITY_THRESHOLD = 0.3  # equivalent to 1.5/5


class CircuitBreaker:
    """Hard spend limit per session.

    Once total_spent >= limit, all further calls are blocked until reset.
    """

    def __init__(self, limit: float = 5.0) -> None:
        self._limit = limit
        self._total_spent = 0.0
        self._call_count = 0
        self._is_open = False

    @property
    def limit(self) -> float:
        return self._limit

    @property
    def total_spent(self) -> float:
        return self._total_spent

    @property
    def call_count(self) -> int:
        return self._call_count

    @property
    def is_open(self) -> bool:
        return self._is_open

    def record_spend(self, amount: float) -> bool:
        """Record a spend and return whether the breaker is now open."""
        self._total_spent += amount
        self._call_count += 1
        if not self._is_open and self._total_spent >= self._limit:
            self._is_open = True
            logger.warning(
                "Circuit breaker OPEN: $%.4f spent (limit $%.2f)",
                self._total_spent,
                self._limit,
            )
        return self._is_open

    def check(self) -> bool:
        """Check whether the circuit breaker is open (True = calls blocked)."""
        if self._is_open:
            logger.warning("Circuit breaker is OPEN — calls blocked")
        return self._is_open

    def reset(self) -> None:
        self._total_spent = 0.0
        self._call_count = 0
        self._is_open = False
        logger.info("Circuit breaker reset")

    @property
    def state(self) -> dict[str, Any]:
        return {
            "is_open": self._is_open,
            "total_spent": round(self._total_spent, 4),
            "call_count": self._call_count,
            "limit": self._limit,
        }


class LoopDetector:
    """Detects low-quality loops and blocks a task type.

    If a task_type receives CONSECUTIVE_LOW_LIMIT consecutive quality scores
    at or below LOW_QUALITY_THRESHOLD, the task type is blocked.

    A score above the threshold resets the consecutive counter.
    """

    def __init__(self, consecutive_low_limit: int = 3) -> None:
        self._consecutive_low_limit = consecutive_low_limit
        self._task_scores: dict[str, list[float]] = {}
        self._blocked_tasks: set[str] = set()

    @property
    def blocked_tasks(self) -> frozenset[str]:
        return frozenset(self._blocked_tasks)

    def record_score(self, task_type: str, quality_score: float) -> LoopDetectionResult:
        """Record a quality score and get the loop detection result.

        Quality scores should be in [0, 1] range (0=poor, 1=excellent).
        The result indicates whether the task is now blocked.
        """
        # Normalise from 0-5 scale if needed
        normalised = quality_score / 5.0 if quality_score > 1.0 else quality_score

        if task_type in self._task_scores:
            self._task_scores[task_type].append(normalised)
        else:
            self._task_scores[task_type] = [normalised]

        # Count consecutive low scores from the end
        scores = self._task_scores[task_type]
        consecutive_low = 0
        for s in reversed(scores):
            if s <= _LOW_QUALITY_THRESHOLD:
                consecutive_low += 1
            else:
                break

        blocked = False
        if consecutive_low >= self._consecutive_low_limit:
            self._blocked_tasks.add(task_type)
            blocked = True
            logger.warning(
                "Task '%s' blocked: %d consecutive low scores",
                task_type,
                consecutive_low,
            )

        return LoopDetectionResult(
            task_type=task_type,
            quality_score=normalised,
            consecutive_low=consecutive_low,
            blocked=blocked,
        )

    def is_blocked(self, task_type: str) -> bool:
        """Check whether a task type is currently blocked."""
        return task_type in self._blocked_tasks

    def unblock(self, task_type: str) -> None:
        """Manually unblock a task type and reset its score history."""
        self._blocked_tasks.discard(task_type)
        self._task_scores.pop(task_type, None)
        logger.info("Task '%s' unblocked", task_type)

    def reset(self) -> None:
        self._task_scores.clear()
        self._blocked_tasks.clear()
        logger.info("Loop detector reset")

    @property
    def state(self) -> dict[str, Any]:
        return {
            "blocked_tasks": list(self._blocked_tasks),
            "tracked_task_types": list(self._task_scores.keys()),
            "consecutive_low_limit": self._consecutive_low_limit,
        }


class BudgetDegrader:
    """Budget-aware model tier degradation.

    As session spend crosses defined thresholds, the recommended tier is
    downgraded to conserve budget. This prevents runaway costs on a single
    session.

    Degradation thresholds (as fraction of circuit_breaker_limit):
        - 0%  -> tier stays as-is
        - 25% -> degrade by 1 level
        - 50% -> degrade by 2 levels
        - 75% -> degrade by 3 levels (min TIER_0)
    """

    def __init__(self, circuit_breaker_limit: float = 5.0) -> None:
        self._limit = circuit_breaker_limit

    def degrade(self, current_tier: ModelTier, total_spent: float) -> ModelTier:
        """Return the degraded tier based on current spend."""
        if self._limit <= 0:
            return ModelTier.TIER_0 if total_spent >= 0 else current_tier
        fraction = total_spent / self._limit if self._limit > 0 else 0.0
        return self._degrade_from(current_tier, fraction)

    def max_allowed_tier(self, total_spent: float) -> ModelTier:
        """Return the most expensive tier allowed at the current spend level."""
        if self._limit <= 0:
            return ModelTier.TIER_0 if total_spent >= 0 else ModelTier.TIER_3
        fraction = total_spent / self._limit if self._limit > 0 else 0.0
        return self._degrade_from(ModelTier.TIER_3, fraction)

    @staticmethod
    def _degrade_from(tier: ModelTier, fraction: float) -> ModelTier:
        if fraction >= 0.75:
            return ModelTier.TIER_0
        if fraction >= 0.50:
            levels_down = 2
        elif fraction >= 0.25:
            levels_down = 1
        else:
            return tier
        target = tier.value - levels_down
        if target <= 0:
            return ModelTier.TIER_0
        return ModelTier(target)

    def can_afford(self, tier: ModelTier, total_spent: float) -> bool:
        """Check whether a given tier is affordable at current spend."""
        allowed = self.max_allowed_tier(total_spent)
        return tier.value <= allowed.value

    def reset(self) -> None:
        logger.info("Budget degrader reset (no internal state to clear)")

    @property
    def state(self) -> dict[str, Any]:
        return {
            "circuit_breaker_limit": self._limit,
        }
