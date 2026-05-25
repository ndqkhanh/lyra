"""Lyra Model Router — Intelligent model routing, capability matching, cost optimization.

Routes agent tasks to optimal LLM models based on capability scoring, cost constraints,
cross-model verification, and tool-usage gap detection. Supports tier-based routing with
budget tracking, usage analytics, and configurable model registry.

V2 API (IntelligentModelRouter): multi-turn, cost-aware, anytime inference routing
with 4-tier cascade (Haiku → Sonnet → Opus → Gemini/OpenRouter).
"""

from __future__ import annotations

# V1 API
from .capability_analyzer import CapabilityAnalyzer, TaskRequirements
from .cost_optimizer import BudgetLimit, CostOptimizer
from .cross_model_verifier import CrossModelVerifier, VerificationResult
from .exceptions import ModelRouterError
from .knowing_doing_gap import GapReport, KnowingDoingGapDetector
from .router_config import ModelCapability, RouterConfig, default_config
from .usage_tracker import UsageRecord, UsageStats, UsageTracker

# V2 API — 4-tier intelligent model cascade routing
from .models_v2 import (
    Budget,
    ModelProvider,
    ModelSpec,
    ModelTier,
    RouterSnapshot,
    RoutingDecision,
    RoutingStrategy,
    TurnContext,
)
from .router_v2 import IntelligentModelRouter

__all__ = [
    # V1 — Capability Analyzer
    "TaskRequirements",
    "CapabilityAnalyzer",
    # V1 — Cost Optimizer
    "BudgetLimit",
    "CostOptimizer",
    # V1 — Cross-Model Verifier
    "VerificationResult",
    "CrossModelVerifier",
    # V1 — Exceptions
    "ModelRouterError",
    # V1 — Knowing-Doing Gap
    "GapReport",
    "KnowingDoingGapDetector",
    # V1 — Router Config
    "ModelCapability",
    "RouterConfig",
    "default_config",
    # V1 — Usage Tracker
    "UsageRecord",
    "UsageStats",
    "UsageTracker",
    # V2 — Intelligent Model Router
    "Budget",
    "ModelProvider",
    "ModelSpec",
    "ModelTier",
    "RouterSnapshot",
    "RoutingDecision",
    "RoutingStrategy",
    "TurnContext",
    "IntelligentModelRouter",
]
