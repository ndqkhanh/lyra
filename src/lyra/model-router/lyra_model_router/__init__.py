"""Lyra Model Router — Intelligent model routing, capability matching, cost optimization.

Routes agent tasks to optimal LLM models based on capability scoring, cost constraints,
cross-model verification, and tool-usage gap detection. Supports tier-based routing with
budget tracking, usage analytics, and configurable model registry.

V2 API (IntelligentModelRouter): multi-turn, cost-aware, anytime inference routing
with 4-tier cascade (Haiku → Sonnet → Opus → Gemini/OpenRouter).

V3 API (Plan 10): 5-layer intelligent router with 15-category task classification,
1-10 complexity estimation, performance history learning, and confidence-thresholded
escalation with cross-provider fallback chains.
"""

from __future__ import annotations

# V1 API
from .capability_analyzer import CapabilityAnalyzer, TaskRequirements
from .complexity_estimator import ComplexityEstimate, ComplexityEstimator
from .confidence_escalation import (
    ConfidenceEscalator,
    EscalationReason,
    EscalationResult,
    EscalationStep,
    ProviderHealth,
)
from .cost_optimizer import BudgetLimit, CostOptimizer
from .cross_model_verifier import CrossModelVerifier, VerificationResult
from .exceptions import ModelRouterError
from .knowing_doing_gap import GapReport, KnowingDoingGapDetector

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
from .performance_history import (
    ModelPerformance,
    PerformanceHistory,
    PerformanceRecord,
    Recommendation,
)
from .router_config import ModelCapability, RouterConfig, default_config
from .router_v2 import IntelligentModelRouter

# V3 API — Plan 10: 5-layer intelligent router
from .task_classifier import ClassificationResult, TaskCategory, TaskClassifier
from .usage_tracker import UsageRecord, UsageStats, UsageTracker

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
    # V3 — Task Classifier (15 categories)
    "ClassificationResult",
    "TaskCategory",
    "TaskClassifier",
    # V3 — Complexity Estimator (1-10 scale)
    "ComplexityEstimate",
    "ComplexityEstimator",
    # V3 — Performance History (learned success rates)
    "ModelPerformance",
    "PerformanceHistory",
    "PerformanceRecord",
    "Recommendation",
    # V3 — Confidence Escalation (threshold + fallback chains)
    "ConfidenceEscalator",
    "EscalationReason",
    "EscalationResult",
    "EscalationStep",
    "ProviderHealth",
]
