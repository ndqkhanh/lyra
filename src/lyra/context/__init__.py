"""
Context module for Lyra workspace state management.

Provides:
- WorkspaceReport: evolving compressed workspace representation
- CompactionStrategy: configurable compression policies
- AdaptiveContextFabric: ACON-style context optimization with compression,
  policy evolution, and speculative planning
- TypedExperienceUnit / UnitLibrary / Scheduler: ACE-style typed experience
  units for memory, strategy, workflow, and skill evolution

v8.1 additions:
- LayeredCompactionEngine: threshold-escalating 3-layer context compressor
- CompositeRetentionScore: weighted importance + recency + relevance scoring
- StructuralCodeProtection: AST-aware code block protection from compaction
- TaskTypeProfile / TaskTypeProfiles: per-task-type compaction profiles
- CostPerTokenTracker / CostPerTokenRecord: compaction cost tracking
- UnitScoring: per-unit-type success rate tracking
- library_save_to_json / library_load_from_json: cross-session persistence
- library_prune_by_usage_threshold: usage-based pruning
- library_get_scoring: aggregate scoring per unit type
"""

from lyra.context.adaptive_fabric import (
    AdaptiveContextFabric,
    ContextPolicy,
    CostPerTokenRecord,
    CostPerTokenTracker,
    ProfileType,
    TaskTypeProfile,
    TaskTypeProfiles,
)
from lyra.context.compaction import COMPACTION_PROMPTS, CompactionStrategy
from lyra.context.experience_units import (
    ExperienceUnitType,
    Scheduler,
    TypedExperienceUnit,
    UnitLibrary,
    UnitScoring,
    library_get_scoring,
    library_load_from_json,
    library_prune_by_usage_threshold,
    library_save_to_json,
)
from lyra.context.layered_compaction import (
    CompositeRetentionScore,
    LayeredCompactionEngine,
    StructuralCodeProtection,
)
from lyra.context.workspace_report import WorkspaceReport

__version__ = "0.3.0"

__all__ = [
    # Original
    "WorkspaceReport",
    "CompactionStrategy",
    "COMPACTION_PROMPTS",
    "AdaptiveContextFabric",
    "ContextPolicy",
    "TypedExperienceUnit",
    "ExperienceUnitType",
    "UnitLibrary",
    "Scheduler",
    # v8.1 context
    "CompositeRetentionScore",
    "LayeredCompactionEngine",
    "StructuralCodeProtection",
    "TaskTypeProfile",
    "TaskTypeProfiles",
    "ProfileType",
    "CostPerTokenRecord",
    "CostPerTokenTracker",
    "UnitScoring",
    "library_save_to_json",
    "library_load_from_json",
    "library_prune_by_usage_threshold",
    "library_get_scoring",
]
