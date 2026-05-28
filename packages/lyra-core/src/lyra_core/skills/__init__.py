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
from .knowledge_transfer import (
    KnowledgeTransferEngine,
    PatternMatch,
    SkillEmbedding,
    TransferResult,
    TransferStatus,
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
from .compactor import CompactionReport, SkillCompactor
from .instinct import (
    DetectedPattern,
    InstinctReport,
    InstinctSystem,
    Observation,
    ObservationType,
    PatternType,
)
from .skill_opt import (
    OptimizationPass,
    OptimizationStrategy,
    SkillOptConfig,
    SkillOptimizer,
    TextEdit,
)
from .validation_gate import (
    GateNumber,
    GateResult,
    GateStatus,
    SkillValidationPipeline,
    ValidationReport,
)

__all__ = [
    "CompactionReport",
    "CallableFederator",
    "FederatedRegistry",
    "FederationConflict",
    "FederationReport",
    "FilesystemFederator",
    "GateNumber",
    "GateResult",
    "GateStatus",
    "DetectedPattern",
    "HybridSkillRouter",
    "InstinctReport",
    "InstinctSystem",
    "KnowledgeTransferEngine",
    "Observation",
    "ObservationType",
    "OptimizationPass",
    "OptimizationReport",
    "OptimizationStrategy",
    "PatternMatch",
    "PatternType",
    "RouterDecision",
    "Skill",
    "SkillAlreadyExists",
    "SkillCompactor",
    "SkillEmbedding",
    "SkillNotFound",
    "SkillManifest",
    "SkillMatch",
    "SkillOptConfig",
    "SkillOptimizer",
    "SkillRegistry",
    "SkillSynthesizer",
    "SkillValidationPipeline",
    "SynthesisError",
    "SynthesisReport",
    "TextEdit",
    "TransferResult",
    "TransferStatus",
    "TriggerOptimizer",
    "ValidationReport",
]
