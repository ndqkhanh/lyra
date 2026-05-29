"""Lyra Policy Optimizer — RL-based policy search, reward modeling, policy gradient optimization,
constrained optimization, policy evaluation, and safe deployment strategies."""

from __future__ import annotations

from lyra_policy_optimizer.constrained_optimizer import (
    ConstrainedOptimizer,
    ConstrainedResult,
    ConstraintConfig,
    ConstraintViolation,
)
from lyra_policy_optimizer.deployment_strategies import (
    DeploymentConfig,
    DeploymentPlan,
    DeploymentResult,
    DeploymentStage,
    DeploymentStrategies,
)
from lyra_policy_optimizer.policy_evaluator import (
    EpisodeResult,
    EvalConfig,
    PolicyComparison,
    PolicyEvaluation,
    PolicyEvaluator,
)
from lyra_policy_optimizer.policy_gradient import (
    GradientConfig,
    GradientResult,
    GradientStep,
    PolicyGradientOptimizer,
)
from lyra_policy_optimizer.policy_search import (
    PolicyCandidate,
    PolicySearch,
    SearchConfig,
    SearchResult,
)
from lyra_policy_optimizer.reward_model import (
    RewardConfig,
    RewardModel,
    RewardSignal,
    RewardSummary,
)
from lyra_policy_optimizer.strategy_optimizer import (
    StrategyAllocation,
    StrategyConfig,
    StrategyOptimizer,
    StrategyPerformance,
)

__all__ = [
    # policy_search
    "PolicyCandidate",
    "PolicySearch",
    "SearchConfig",
    "SearchResult",
    # reward_model
    "RewardConfig",
    "RewardModel",
    "RewardSignal",
    "RewardSummary",
    # policy_gradient
    "GradientConfig",
    "GradientResult",
    "GradientStep",
    "PolicyGradientOptimizer",
    # constrained_optimizer
    "ConstraintConfig",
    "ConstrainedOptimizer",
    "ConstrainedResult",
    "ConstraintViolation",
    # policy_evaluator
    "EvalConfig",
    "EpisodeResult",
    "PolicyComparison",
    "PolicyEvaluation",
    "PolicyEvaluator",
    # deployment_strategies
    "DeploymentConfig",
    "DeploymentPlan",
    "DeploymentResult",
    "DeploymentStage",
    "DeploymentStrategies",
    # strategy_optimizer
    "StrategyAllocation",
    "StrategyConfig",
    "StrategyOptimizer",
    "StrategyPerformance",
]
