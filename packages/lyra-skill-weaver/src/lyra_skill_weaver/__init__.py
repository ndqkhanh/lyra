"""Lyra Skill Weaver — Dynamic skill composition engine.

Composes agent skills into execution plans using multiple patterns:
- Sequential (pipeline)
- Parallel (fan-out/fan-in)
- Conditional (if-then-else)
- Iterative (loops with convergence)
- Hybrid (mixed patterns)

Supports skill discovery, quality evaluation, gap analysis,
composition optimization, profiling, and caching.
"""

from __future__ import annotations

from .skill_weaver import (
    SkillType,
    CompositionPattern,
    SkillStatus,
    SkillMetadata,
    SkillIO,
    SkillDefinition,
    SkillEdge,
    SkillGraph,
    SkillRegistry,
    CompositionPlan,
    SkillWeaver,
)

from .composer import (
    CompositionNode,
    CompositionResult,
    CompositionCallback,
    SequentialComposer,
    ParallelComposer,
    ConditionalComposer,
    IterativeComposer,
    HybridComposer,
    MasterComposer,
)

from .discovery import (
    DiscoveryMethod,
    QualityTier,
    QualityReport,
    GapAnalysis,
    SkillDiscoveryEngine,
)

from .optimizer import (
    OptimizationObjective,
    ProfilingResult,
    OptimizationResult,
    CompositionProfiler,
    PlanCache,
    CompositionOptimizer,
)

from .exceptions import (
    SkillWeaverError,
    SkillNotFoundError,
    SkillConflictError,
    CompositionError,
    CircularDependencyError,
    DiscoveryError,
    OptimizationError,
    ValidationError,
)

__all__ = [
    # Skill weaver core
    "SkillType",
    "CompositionPattern",
    "SkillStatus",
    "SkillMetadata",
    "SkillIO",
    "SkillDefinition",
    "SkillEdge",
    "SkillGraph",
    "SkillRegistry",
    "CompositionPlan",
    "SkillWeaver",
    # Composers
    "CompositionNode",
    "CompositionResult",
    "CompositionCallback",
    "SequentialComposer",
    "ParallelComposer",
    "ConditionalComposer",
    "IterativeComposer",
    "HybridComposer",
    "MasterComposer",
    # Discovery
    "DiscoveryMethod",
    "QualityTier",
    "QualityReport",
    "GapAnalysis",
    "SkillDiscoveryEngine",
    # Optimizer
    "OptimizationObjective",
    "ProfilingResult",
    "OptimizationResult",
    "CompositionProfiler",
    "PlanCache",
    "CompositionOptimizer",
    # Exceptions
    "SkillWeaverError",
    "SkillNotFoundError",
    "SkillConflictError",
    "CompositionError",
    "CircularDependencyError",
    "DiscoveryError",
    "OptimizationError",
    "ValidationError",
]
