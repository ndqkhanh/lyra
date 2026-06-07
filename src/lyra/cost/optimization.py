"""Cost optimizer for Lyra AGI — model tier recommendations.

The CostOptimizer recommends the most cost-effective model tier for a given
task type, given current budget state and task requirements.
"""

from __future__ import annotations

import logging
from typing import Any

from lyra.cost.models import TIER_LABELS, TIER_PRICING, ModelTier
from lyra.cost.safeguards import BudgetDegrader, LoopDetector

logger = logging.getLogger(__name__)

# Default task-type-to-tier mappings.
# These can be overridden per instance.
_DEFAULT_TIER_MAP: dict[str, ModelTier] = {
    "classification": ModelTier.TIER_0,
    "routing": ModelTier.TIER_0,
    "trivial": ModelTier.TIER_0,
    "extraction": ModelTier.TIER_1,
    "summarization": ModelTier.TIER_1,
    "high_volume": ModelTier.TIER_1,
    "simple_task": ModelTier.TIER_1,
    "coding": ModelTier.TIER_2,
    "analysis": ModelTier.TIER_2,
    "debugging": ModelTier.TIER_2,
    "code_review": ModelTier.TIER_2,
    "architecture": ModelTier.TIER_3,
    "hard_reasoning": ModelTier.TIER_3,
    "planning": ModelTier.TIER_3,
    "research": ModelTier.TIER_3,
}

# Task types that require TIER_3 reasoning — these should never be degraded below
# the minimum specified tier, even under budget pressure, except at the hard cap.
_HARD_TASK_TYPES: frozenset[str] = frozenset(
    {
        "architecture",
        "hard_reasoning",
        "planning",
    }
)


class NoTierAvailableError(Exception):
    """Raised when no viable tier can be recommended."""


class TierRecommendation:
    """Recommendation for a single task's model tier."""

    def __init__(
        self,
        task_type: str,
        recommended_tier: ModelTier,
        degraded: bool,
        blocked: bool,
        cost_estimate: float,
    ) -> None:
        self.task_type = task_type
        self.recommended_tier = recommended_tier
        self.degraded = degraded
        self.blocked = blocked
        self.cost_estimate = cost_estimate

    @property
    def label(self) -> str:
        return TIER_LABELS.get(self.recommended_tier, f"Tier {self.recommended_tier.value}")

    def __repr__(self) -> str:
        return (
            f"TierRecommendation(task_type={self.task_type!r}, "
            f"tier={self.recommended_tier.name}, "
            f"degraded={self.degraded}, "
            f"blocked={self.blocked}, "
            f"cost_estimate={self.cost_estimate:.6f})"
        )


class CostOptimizer:
    """Recommends model tiers for tasks based on budget, loop state, and task type.

    The optimizer considers:
    1. Whether the task type is blocked (loop detection)
    2. The default tier for the task type
    3. Budget degradation
    4. Whether the task type is "hard" (minimum tier floor)
    """

    def __init__(
        self,
        tier_map: dict[str, ModelTier] | None = None,
        circuit_breaker_limit: float = 5.0,
    ) -> None:
        self._tier_map = dict(_DEFAULT_TIER_MAP)
        if tier_map:
            self._tier_map.update(tier_map)
        self._degrader = BudgetDegrader(circuit_breaker_limit)
        self._loop_detector = LoopDetector()

    @property
    def tier_map(self) -> dict[str, ModelTier]:
        return dict(self._tier_map)

    @property
    def degrader(self) -> BudgetDegrader:
        return self._degrader

    @property
    def loop_detector(self) -> LoopDetector:
        return self._loop_detector

    def recommend(
        self,
        task_type: str,
        total_session_spend: float,
        estimated_input_tokens: int = 1000,
        estimated_output_tokens: int = 500,
    ) -> TierRecommendation:
        """Recommend a tier for a task, considering budget and loop state.

        Args:
            task_type: The type of task (e.g. "coding", "architecture").
            total_session_spend: Current total spend for the session.
            estimated_input_tokens: Expected input tokens for the task.
            estimated_output_tokens: Expected output tokens for the task.

        Returns:
            A TierRecommendation with the recommended tier and metadata.

        Raises:
            NoTierAvailableError: If even TIER_0 is blocked or unavailable.
        """
        # 1. Check if blocked by loop detector
        if self._loop_detector.is_blocked(task_type):
            logger.warning("Task '%s' is blocked by loop detector", task_type)
            raise NoTierAvailableError(f"Task '{task_type}' is blocked by loop detector")

        # 2. Get the default tier for this task type
        default_tier = self._tier_map.get(task_type, ModelTier.TIER_1)

        # 3. Apply budget degradation
        degraded_tier = self._degrader.degrade(default_tier, total_session_spend)

        # 4. Enforce minimum tier for hard task types
        is_degraded = degraded_tier != default_tier
        hard_task_floor_used = False
        if is_degraded and task_type in _HARD_TASK_TYPES:
            # Hard tasks have a floor at TIER_1 — overrides normal degradation
            if degraded_tier.value < 1:  # below TIER_1
                degraded_tier = ModelTier.TIER_1
                hard_task_floor_used = True
                logger.info(
                    "Hard task '%s': floor enforced at TIER_1",
                    task_type,
                )

        # 5. Estimate cost
        input_price, output_price = TIER_PRICING[degraded_tier]
        cost_estimate = (estimated_input_tokens / 1_000_000) * input_price + (
            estimated_output_tokens / 1_000_000
        ) * output_price

        # 6. Check affordability — skip for hard tasks at their enforced floor
        if not hard_task_floor_used and not self._degrader.can_afford(
            degraded_tier, total_session_spend
        ):
            raise NoTierAvailableError(
                f"No affordable tier for '{task_type}' at spend ${total_session_spend:.2f}"
            )

        return TierRecommendation(
            task_type=task_type,
            recommended_tier=degraded_tier,
            degraded=is_degraded,
            blocked=False,
            cost_estimate=cost_estimate,
        )

    def record_quality_score(self, task_type: str, score: float) -> Any:
        """Record a quality score for loop detection.

        Returns the LoopDetectionResult from the loop detector.
        """
        return self._loop_detector.record_score(task_type, score)

    def update_tier_map(self, task_type: str, tier: ModelTier) -> None:
        """Override the default tier for a specific task type."""
        self._tier_map[task_type] = tier
        logger.info("Tier map updated: %s -> %s", task_type, tier.name)

    @property
    def state(self) -> dict[str, Any]:
        return {
            "tier_map": {k: v.name for k, v in self._tier_map.items()},
            "degrader": self._degrader.state,
            "loop_detector": self._loop_detector.state,
        }
