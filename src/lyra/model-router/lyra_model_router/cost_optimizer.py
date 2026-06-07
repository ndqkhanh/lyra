"""Tier-based cost-optimized model selection."""

from __future__ import annotations

from dataclasses import dataclass

from .capability_analyzer import TaskRequirements
from .exceptions import ModelRouterError
from .router_config import ModelCapability, RouterConfig


@dataclass(frozen=True)
class BudgetLimit:
    """Budget constraints for a routing decision.

    Attributes:
        max_cost_per_task: Maximum cost allowed per task in USD.
        max_tokens_per_task: Maximum tokens allowed per task.
        preferred_tier: Preferred routing tier (0-3).
    """
    max_cost_per_task: float
    max_tokens_per_task: int
    preferred_tier: int


# Tier-to-model mapping for default routing
_TIER_MODEL_MAP: dict[int, str] = {
    0: "claude-opus-4-7",
    1: "claude-sonnet-4-6",
    2: "claude-haiku-4-5",
    3: "deepseek-v4-flash",
}

# Category-to-tier mapping
_CATEGORY_TIER_MAP: dict[str, int] = {
    "architecture": 0,
    "research": 0,
    "coding": 1,
    "review": 1,
    "lookup": 2,
    "execution": 3,
}


class CostOptimizer:
    """Optimizes model selection based on cost constraints and task requirements.

    Uses tier-based routing:
    - Tier 0 (Critical): token-heavy, complex tasks -> flagship models
    - Tier 1 (Standard): coding, review -> standard models
    - Tier 2 (Economy): lookup, simple tasks -> economy models
    - Tier 3 (Background): batch, meta tasks -> cheapest models
    """

    async def select_model(
        self,
        requirements: TaskRequirements,
        budget_limit: BudgetLimit | None = None,
        config: RouterConfig | None = None,
    ) -> ModelCapability:
        """Select the optimal model based on task requirements and budget.

        Args:
            requirements: Analyzed task requirements.
            budget_limit: Optional budget constraints.
            config: Router configuration (uses default if None).

        Returns:
            The selected ModelCapability.

        Raises:
            ModelRouterError: If no suitable model can be found.
        """
        if config is None:
            from .router_config import default_config
            config = default_config()

        # Determine target tier
        target_tier = budget_limit.preferred_tier if budget_limit else None
        if target_tier is None:
            target_tier = _determine_tier(requirements, budget_limit)

        # Try tiers from target upward (higher number = cheaper), then downward
        tier_attempts = list(range(target_tier, 4)) + list(range(target_tier - 1, -1, -1))

        for tier in tier_attempts:
            candidates = [
                m for m in config.model_registry.values()
                if m.tier == tier
            ]
            if not candidates:
                continue
            candidates.sort(key=lambda m: m.cost_per_1k_tokens)

            # If no budget limit, pick cheapest at this tier
            if budget_limit is None or budget_limit.max_cost_per_task >= float("inf"):
                return candidates[0]

            # Filter by budget and return first affordable
            for m in candidates:
                if m.cost_per_1k_tokens <= budget_limit.max_cost_per_task:
                    return m

        # Last resort: cheapest model overall
        all_models = sorted(
            config.model_registry.values(),
            key=lambda m: m.cost_per_1k_tokens,
        )
        if all_models:
            return all_models[0]

        raise ModelRouterError("No models available in registry")


def _determine_tier(
    requirements: TaskRequirements,
    budget_limit: BudgetLimit | None,
) -> int:
    """Determine the appropriate routing tier based on requirements and budget."""
    # Check budget first
    if budget_limit is not None:
        if budget_limit.preferred_tier <= 3:
            return budget_limit.preferred_tier

    # Use category mapping
    if requirements.category in _CATEGORY_TIER_MAP:
        tier = _CATEGORY_TIER_MAP[requirements.category]
    else:
        tier = 1

    # Escalate tier for high complexity
    if requirements.complexity_score >= 0.8 and tier > 0:
        tier = max(0, tier - 1)
    elif requirements.complexity_score >= 0.5 and tier > 2:
        tier = 2

    return tier
