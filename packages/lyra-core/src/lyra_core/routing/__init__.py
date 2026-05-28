"""Provider/model routing layer — cascade, policy, RL-optimized, and dynamic pricing."""

from __future__ import annotations

from .cascade import (
    CascadeDecision,
    CascadeResult,
    CascadeStage,
    ConfidenceCascadeRouter,
    ConfidenceEstimator,
    ProviderInvocation,
)
from .dynamic_pricing import (
    DynamicPricingEngine,
    PricingSnapshot,
    PricingTier,
    ProviderQuote,
)
from .experience_buffer import Experience, ExperienceBuffer, VALID_ACTIONS
from .policy import (
    ModelTier,
    RoutingConfig,
    RoutingDecision,
    RoutingSignals,
    TrajectoryBudget,
    TrajectoryRouter,
    route_step,
)
from .policy_network import (
    ACTION_SPACE,
    HIDDEN_DIM,
    NUM_ACTIONS,
    PolicyNetwork,
    PolicyWeights,
)
from .reward_calculator import RewardCalculator, RewardComponents, RewardConfig
from .rl_policy_optimizer import (
    RLPriorityOptimizer,
    RLRouterConfig,
    RLRoutingDecision,
    TrainingMetrics,
)
from .state_encoder import (
    FEATURE_DIM,
    TOOL_CATEGORY_MAP,
    StateEncoder,
    StateVector,
)

__all__ = [
    # Cascade
    "CascadeDecision",
    "CascadeResult",
    "CascadeStage",
    "ConfidenceCascadeRouter",
    "ConfidenceEstimator",
    "ProviderInvocation",
    # Policy (signal-driven)
    "ModelTier",
    "RoutingConfig",
    "RoutingDecision",
    "RoutingSignals",
    "TrajectoryBudget",
    "TrajectoryRouter",
    "route_step",
    # RL Routing
    "ACTION_SPACE",
    "Experience",
    "ExperienceBuffer",
    "FEATURE_DIM",
    "HIDDEN_DIM",
    "NUM_ACTIONS",
    "PolicyNetwork",
    "PolicyWeights",
    "RLPriorityOptimizer",
    "RLRouterConfig",
    "RLRoutingDecision",
    "RewardCalculator",
    "RewardComponents",
    "RewardConfig",
    "StateEncoder",
    "StateVector",
    "TOOL_CATEGORY_MAP",
    "TrainingMetrics",
    "VALID_ACTIONS",
    # Dynamic Pricing
    "DynamicPricingEngine",
    "PricingSnapshot",
    "PricingTier",
    "ProviderQuote",
]
