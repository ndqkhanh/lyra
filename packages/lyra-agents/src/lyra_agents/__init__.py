"""
Lyra Agents - Advanced agent capabilities.

This package provides:
- Model routing (Haiku, Sonnet, Opus)
- Prompt optimization
- Self-improvement loops
- A/B testing for prompts
"""

from lyra_agents.model_router import (
    ModelCapability,
    ModelRouter,
    ModelTier,
    RoutingDecision,
    TaskComplexity,
)
from lyra_agents.prompt_optimizer import PromptOptimizer
from lyra_agents.self_improvement import (
    ExecutionFeedback,
    PromptVariant,
    SelfImprovementLoop,
)

__version__ = "0.1.0"

__all__ = [
    # Model Router
    "ModelRouter",
    "ModelTier",
    "ModelCapability",
    "RoutingDecision",
    "TaskComplexity",
    # Prompt Optimizer
    "PromptOptimizer",
    # Self-Improvement
    "SelfImprovementLoop",
    "ExecutionFeedback",
    "PromptVariant",
]
