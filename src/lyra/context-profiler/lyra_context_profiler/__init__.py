"""Context Profiler — Real-time context window analysis and optimization for Lyra AGI.

Provides comprehensive context window profiling with multi-factor importance
scoring, intelligent compaction, dynamic optimization, and configurable
strategies for managing LLM context windows efficiently.
"""

from __future__ import annotations

from .compaction import (
    CompactionEngine,
    CompactionError,
    CompactionMode,
    CompactionResult,
    DisclosureLevel,
    DuplicateDetector,
    EmptyContextError,
    HierarchicalSummarizer,
    IrreversibleCompactionError,
    SummarizationLevel,
)
from .importance import (
    ContextElementProtocol,
    DependencyScorer,
    ImportanceCalculator,
    ImportanceError,
    InsufficientDataError,
    MLImportancePredictor,
    RecencyScorer,
    ScoreWeights,
    TaskRelevanceScorer,
    TfidfCalculator,
)
from .optimizer import (
    CacheWarmingStrategy,
    ClusterConfig,
    ContextOptimizer,
    EvictionCandidate,
    EvictionError,
    EvictionPolicy,
    NoOptimizationNeededError,
    OptimizationResult,
    OptimizerError,
    WindowSizeRecommendation,
)
from .profiler import (
    CompactionRecommendation,
    ContextAnalyzer,
    ContextDashboard,
    ContextElement,
    ContextElementType,
    ContextHealth,
    ContextProfile,
    ContextProfiler,
    InvalidContextElementError,
    MetricsCollector,
    ProfileAnalysisError,
    ProfileMatcher,
    ProfilerError,
    TokenBudget,
    TokenBudgetExceededError,
)
from .strategies import (
    CompactionStrategy,
    StrategyParameters,
    StrategyPresets,
    StrategyRecord,
    StrategyRegistry,
)

__all__ = [
    # ── Profiler (Core) ───────────────────────────────────────────────
    "ContextElement",
    "ContextElementType",
    "ContextHealth",
    "ContextProfile",
    "ContextProfiler",
    "ContextAnalyzer",
    "ProfileMatcher",
    "ContextDashboard",
    "CompactionRecommendation",
    "TokenBudget",
    "MetricsCollector",
    # ── Profiler Exceptions ───────────────────────────────────────────
    "ProfilerError",
    "TokenBudgetExceededError",
    "ProfileAnalysisError",
    "InvalidContextElementError",
    # ── Importance ────────────────────────────────────────────────────
    "ImportanceCalculator",
    "TfidfCalculator",
    "RecencyScorer",
    "TaskRelevanceScorer",
    "DependencyScorer",
    "MLImportancePredictor",
    "ScoreWeights",
    "ContextElementProtocol",
    # ── Importance Exceptions ─────────────────────────────────────────
    "ImportanceError",
    "InsufficientDataError",
    # ── Compaction ────────────────────────────────────────────────────
    "CompactionEngine",
    "CompactionMode",
    "CompactionResult",
    "DisclosureLevel",
    "DuplicateDetector",
    "HierarchicalSummarizer",
    "SummarizationLevel",
    # ── Compaction Exceptions ─────────────────────────────────────────
    "CompactionError",
    "IrreversibleCompactionError",
    "EmptyContextError",
    # ── Optimizer ─────────────────────────────────────────────────────
    "ContextOptimizer",
    "EvictionCandidate",
    "EvictionPolicy",
    "OptimizationResult",
    "WindowSizeRecommendation",
    "CacheWarmingStrategy",
    "ClusterConfig",
    # ── Optimizer Exceptions ──────────────────────────────────────────
    "OptimizerError",
    "NoOptimizationNeededError",
    "EvictionError",
    # ── Strategies ────────────────────────────────────────────────────
    "CompactionStrategy",
    "StrategyParameters",
    "StrategyPresets",
    "StrategyRecord",
    "StrategyRegistry",
]
