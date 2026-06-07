"""
Model router — routes tasks to the appropriate provider/model combination.

The routing system has three strategies:
1. **Static tier router** (``ModelRouter``) — Task-type-to-effort-level
   mapping with fallback chain (Phase 1, deployed now).
2. **Learned router** (``LearnedRouter``) — DeBERTa-v3-small multi-head
   router with best-of-N selection (BEST-Route architecture). Requires
   training data generation (Phase 2).
3. **Memory-augmented router** (``MemoryAugmentedRouter``) — Compound
   routing with cache-hit awareness: verbatim turn-pair storage,
   hybrid BM25+cosine retrieval, confidence-gated cheap-model execution
   (Knowledge Access paper, Phase 2).

v8.1 additions:
- ConfidenceEstimator: multi-signal confidence detection (length anomaly,
  refusal patterns, inconsistency heuristics).
- EscalationDecision: encapsulates cascade escalation metadata.
- CascadeStats: aggregate cascade routing statistics.
- auto_tune(): adjusts confidence thresholds per model from outcome data.
- CostDashboard / CostBreakdown / CompletionRecord: real-time cost tracking
  with budget alerts and optimization suggestions.
"""

from lyra.routing.cascade import (
    CascadeConfig,
    CascadeRouter,
    CascadeStats,
    ConfidenceEstimator,
    EscalationDecision,
    OutcomeStats,
)
from lyra.routing.cost_dashboard import CompletionRecord, CostBreakdown, CostDashboard
from lyra.routing.learned_router import (
    LearnedRouter,
    LearnedRouterState,
    ProxyRewardModel,
    SamplingDepth,
    ScoredCandidate,
    TripleCandidate,
    create_learned_router,
)
from lyra.routing.memory_router import (
    MemoryAugmentedRouter,
    MemoryEntry,
    MemoryRouterLayer,
    MemoryRouterMetrics,
    MemorySearchResult,
    MemoryStore,
    confidence_gate,
)
from lyra.routing.provider.router import ModelRouter

__all__ = [
    # Static router
    "ModelRouter",
    # Learned router
    "LearnedRouter",
    "LearnedRouterState",
    "ProxyRewardModel",
    "ScoredCandidate",
    "TripleCandidate",
    "SamplingDepth",
    "create_learned_router",
    # Memory-augmented router
    "MemoryAugmentedRouter",
    "MemoryEntry",
    "MemorySearchResult",
    "MemoryStore",
    "MemoryRouterLayer",
    "MemoryRouterMetrics",
    "confidence_gate",
    # Cascade (original)
    "CascadeConfig",
    "CascadeRouter",
    "OutcomeStats",
    # v8.1 cascade
    "CascadeStats",
    "ConfidenceEstimator",
    "EscalationDecision",
    # v8.1 cost dashboard
    "CostDashboard",
    "CostBreakdown",
    "CompletionRecord",
]
