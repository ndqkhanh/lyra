"""Reuse-first hybrid skill router + in-session skill synthesis.

Wave-F Task 6 ships the registry + router; Task 8 will add the
synthesiser entry point (stitched onto the same registry).
"""
from __future__ import annotations

from .federation import (
    CallableFederator,
    FederatedRegistry,
    FederationConflict,
    FederationReport,
    FilesystemFederator,
    SkillManifest,
)
from .optimizer import OptimizationReport, TriggerOptimizer
from .registry import (
    Skill,
    SkillAlreadyExists,
    SkillNotFound,
    SkillRegistry,
)
from .router import (
    HybridSkillRouter,
    RouterDecision,
    SkillMatch,
)
from .synthesizer import (
    SkillSynthesizer,
    SynthesisError,
    SynthesisReport,
)

__all__ = [
    "CallableFederator",
    "FederatedRegistry",
    "FederationConflict",
    "FederationReport",
    "FilesystemFederator",
    "HybridSkillRouter",
    "OptimizationReport",
    "RouterDecision",
    "Skill",
    "SkillAlreadyExists",
    "SkillNotFound",
    "SkillManifest",
    "SkillMatch",
    "SkillRegistry",
    "SkillSynthesizer",
    "SynthesisError",
    "SynthesisReport",
    "TriggerOptimizer",
]
