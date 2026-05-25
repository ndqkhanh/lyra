"""lyra-skill-loader: progressive-disclosure skill loading with trigger matching, context budgeting, compilation, and dependency resolution."""
from __future__ import annotations

from .exceptions import (
    BudgetExceededError,
    CompilationError,
    ConfigError,
    DependencyError,
    LoaderError,
    TriggerError,
)
from .loader_config import (
    BALANCED,
    FULL_LOAD,
    MINIMAL,
    STRICT_BUDGET,
    CacheConfig,
    LoaderConfig,
    TierConfig,
    get_preset,
)
from .tiered_loader import (
    LoadTier,
    LoadedSkill,
    LoaderStats,
    SkillContent,
    SkillMetadata,
    SkillReferences,
    TieredLoader,
)
from .trigger_matcher import (
    MatchConfig,
    MatchResult,
    Trigger,
    TriggerMatcher,
    TriggerType,
)
from .context_aware_loader import (
    BudgetConfig,
    ContextAwareLoader,
    ContextBudget,
    EvictionPolicy,
    LoadDecision,
    LoadPlan,
)
from .skill_compiler import (
    CompiledIndex,
    CompiledSkill,
    SkillCompiler,
)
from .dependency_resolver import (
    DependencyGraph,
    DependencyResolver,
    ResolutionResult,
    SkillNode,
)

__all__ = [
    "BudgetExceededError",
    "CompilationError",
    "ConfigError",
    "DependencyError",
    "LoaderError",
    "TriggerError",
    "BALANCED",
    "FULL_LOAD",
    "MINIMAL",
    "STRICT_BUDGET",
    "CacheConfig",
    "LoaderConfig",
    "TierConfig",
    "get_preset",
    "LoadTier",
    "LoadedSkill",
    "LoaderStats",
    "SkillContent",
    "SkillMetadata",
    "SkillReferences",
    "TieredLoader",
    "MatchConfig",
    "MatchResult",
    "Trigger",
    "TriggerMatcher",
    "TriggerType",
    "BudgetConfig",
    "ContextAwareLoader",
    "ContextBudget",
    "EvictionPolicy",
    "LoadDecision",
    "LoadPlan",
    "CompiledIndex",
    "CompiledSkill",
    "SkillCompiler",
    "DependencyGraph",
    "DependencyResolver",
    "ResolutionResult",
    "SkillNode",
]
