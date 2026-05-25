"""Lyra Model Router — Intelligent model routing, capability matching, cost optimization.

Routes agent tasks to optimal LLM models based on capability scoring, cost constraints,
cross-model verification, and tool-usage gap detection. Supports tier-based routing with
budget tracking, usage analytics, and hot-reloadable configuration.
"""

from __future__ import annotations

from .capability_analyzer import (
    CapabilityAnalyzer,
    ComplexityLevel,
    DomainType,
    LatencySensitivity,
    MatchScore,
    ModelCapability,
    TaskProfile,
)

from .cost_optimizer import (
    BudgetLimits,
    BudgetTracker,
    CostOptimizer,
    CostTier,
)

from .knowing_doing_gap import (
    GapRecommendation,
    KnowingDoingGapDetector,
    ToolCategory,
    ToolNecessitySignal,
)

from .cross_model_verifier import (
    CrossModelVerifier,
    ModelFamily,
    ValidationResult,
)

from .router_config import (
    FallbackRule,
    HealthStatus,
    ModelRegistryEntry,
    PolicyType,
    RouterConfig,
    RoutingPolicy,
)

from .router import (
    ModelRouter,
    ModelSelection,
    RouterPipeline,
)

from .usage_tracker import (
    BudgetAlert,
    UsageRecord,
    UsageStats,
    UsageTracker,
)

from .exceptions import (
    BudgetExceededError,
    CapabilityMismatchError,
    ModelNotFoundError,
    RouterError,
    RoutingError,
    VerificationError,
)

__all__ = [
    # Capability Analyzer
    "TaskProfile",
    "ModelCapability",
    "MatchScore",
    "ComplexityLevel",
    "DomainType",
    "LatencySensitivity",
    "CapabilityAnalyzer",
    # Cost Optimizer
    "CostTier",
    "BudgetLimits",
    "BudgetTracker",
    "CostOptimizer",
    # Knowing-Doing Gap
    "ToolCategory",
    "ToolNecessitySignal",
    "GapRecommendation",
    "KnowingDoingGapDetector",
    # Cross-Model Verifier
    "ModelFamily",
    "ValidationResult",
    "CrossModelVerifier",
    # Router Config
    "PolicyType",
    "RouterConfig",
    "RoutingPolicy",
    "FallbackRule",
    "ModelRegistryEntry",
    "HealthStatus",
    # Router
    "ModelSelection",
    "RouterPipeline",
    "ModelRouter",
    # Usage Tracker
    "UsageRecord",
    "UsageStats",
    "BudgetAlert",
    "UsageTracker",
    # Exceptions
    "RouterError",
    "ModelNotFoundError",
    "BudgetExceededError",
    "VerificationError",
    "CapabilityMismatchError",
    "RoutingError",
]
