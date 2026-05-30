"""
Lyra Model Router (V4) — 3-tier intelligent model routing with budget awareness.

DecisionBench (2605.19099) shows routing fidelity is 7.5-29.5%.
This router closes that gap with a 3-tier cascade:

- **Tier 1 — Rule Layer** (0-1ms, $0): Keyword/pattern matching, catches 50-60%.
- **Tier 2 — Semantic Match** (5-50ms, <$0.001): TF-IDF similarity + complexity estimation, catches
20-30%.
- **Tier 3 — Neural Router** (20-100ms, ~$0.001): MLP classifier with online RL.

Budget-aware routing (Google BATS pattern) with 4 regimes and a $5/session
circuit breaker. Multi-provider: Anthropic, DeepSeek, Google, OpenAI, OpenRouter.

Usage::

    from lyra_router import ModelRouter

    router = ModelRouter()
    decision = router.route("implement a JWT auth middleware")
    print(decision.model)

    router.record_outcome(decision, success=True, latency_ms=150, cost=0.002)
"""

from __future__ import annotations

from .budget import BudgetTracker
from .models import (
    BudgetRegime,
    ModelAssignment,
    ModelTier,
    Provider,
    RoutingDecision,
    TaskComplexity,
    get_cost_estimate,
    get_tier_for_complexity,
)
from .neural_ucb import NeuralUCB, UCBConfig
from .providers import ProviderRegistry
from .router import ModelRouter
from .tiers import NeuralTier, RuleTier, SemanticTier, TierResult

__all__ = [
    # Core router
    "ModelRouter",
    # Budget
    "BudgetTracker",
    # Models / enums
    "BudgetRegime",
    "ModelAssignment",
    "ModelTier",
    "Provider",
    "RoutingDecision",
    "TaskComplexity",
    "get_cost_estimate",
    "get_tier_for_complexity",
    # NeuralUCB
    "NeuralUCB",
    "UCBConfig",
    # Providers
    "ProviderRegistry",
    # Tiers
    "NeuralTier",
    "RuleTier",
    "SemanticTier",
    "TierResult",
]
