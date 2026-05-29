"""Lyra experience and learning engine (Phase 7).

Captures agent trajectories, extracts reusable patterns and anti-patterns,
runs continuous learning loops, and distills successful patterns into
reusable skills.
"""

from __future__ import annotations

from lyra_core.experience.anti_pattern import AntiPattern, AntiPatternRegistry, MatchResult
from lyra_core.experience.extractor import (
    ExperienceExtractor,
    ExperienceRecord,
    ExtractedPattern,
    PatternType,
)
from lyra_core.experience.learning_loop import (
    ImprovementCycle,
    LearningLoop,
    LoopConfig,
    LoopState,
)
from lyra_core.experience.skill_distiller import (
    DistillationResult,
    DistilledSkill,
    SkillCandidate,
    SkillDistiller,
)

__all__ = [
    "AntiPattern",
    "AntiPatternRegistry",
    "DistillationResult",
    "DistilledSkill",
    "ExperienceExtractor",
    "ExperienceRecord",
    "ExtractedPattern",
    "ImprovementCycle",
    "LearningLoop",
    "LoopConfig",
    "LoopState",
    "MatchResult",
    "PatternType",
    "SkillCandidate",
    "SkillDistiller",
]
