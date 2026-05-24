"""Lyra AGI Cost Tracking & Optimization.

Phase 0 of the Lyra AGI V4 Ultra Plan. Implements the Economics layer (Section 16).
"""

from __future__ import annotations

from lyra_cost.cache import PromptCache, SemanticCache
from lyra_cost.models import (
    TIER_PRICING,
    CallOutcome,
    CacheStats,
    CostRecord,
    LoopDetectionResult,
    ModelTier,
    SessionBudget,
    TaskCostSummary,
    TierConfig,
)
from lyra_cost.optimization import CostOptimizer, TierRecommendation
from lyra_cost.safeguards import BudgetDegrader, CircuitBreaker, LoopDetector
from lyra_cost.tracker import CostTracker

__version__ = "0.1.0"

__all__ = [
    # Models
    "ModelTier",
    "CallOutcome",
    "CostRecord",
    "TaskCostSummary",
    "SessionBudget",
    "CacheStats",
    "LoopDetectionResult",
    "TierConfig",
    "TIER_PRICING",
    # Tracker
    "CostTracker",
    # Cache
    "PromptCache",
    "SemanticCache",
    # Safeguards
    "CircuitBreaker",
    "LoopDetector",
    "BudgetDegrader",
    # Optimization
    "CostOptimizer",
    "TierRecommendation",
]
