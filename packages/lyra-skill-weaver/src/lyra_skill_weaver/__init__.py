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

from .composer import (
    CompositionCallback,
    CompositionNode,
    CompositionResult,
    ConditionalComposer,
    HybridComposer,
    IterativeComposer,
    MasterComposer,
    ParallelComposer,
    SequentialComposer,
)
from .discovery import (
    DiscoveryMethod,
    GapAnalysis,
    QualityReport,
    QualityTier,
    SkillDiscoveryEngine,
)
from .exceptions import (
    CircularDependencyError,
    CompositionError,
    DiscoveryError,
    OptimizationError,
    SkillConflictError,
    SkillNotFoundError,
    SkillWeaverError,
    ValidationError,
)
from .optimizer import (
    CompositionOptimizer,
    CompositionProfiler,
    OptimizationObjective,
    OptimizationResult,
    PlanCache,
    ProfilingResult,
)
from .skill_weaver import (
    CompositionPattern,
    CompositionPlan,
    SkillDefinition,
    SkillEdge,
    SkillGraph,
    SkillIO,
    SkillMetadata,
    SkillRegistry,
    SkillStatus,
    SkillType,
    SkillWeaver,
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
