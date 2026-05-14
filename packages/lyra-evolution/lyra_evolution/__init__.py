"""lyra-evolution: closed-loop self-evolution for Lyra (Phases E, H, K, L)."""
from __future__ import annotations

# Phase E — closed-loop controller
from .control_record import ControlRecord, new_control_record
from .controller import ClosedLoopController, ControllerConfig, HaltSignal
from .reflexion import ReflexionEngine, ReflexionLesson
from .stability import BudgetViolation, StabilityBudget, StabilityState
from .voyager import SkillCandidate, SkillLibrary, VoyagerAccumulator

# Phase H — Ctx2Skill extraction
from .ctx2skill import (
    Ctx2SkillExtractor,
    CrossTimeReplayValidator,
    ExtractionResult,
    SkillDraft,
    TraceRecord,
)

# Phase K — co-evolutionary verification
from .evoverifier import (
    CoEvolutionGate,
    IsolatedVerifier,
    VerificationOutcome,
    VerificationReport,
    VerificationTask,
)

# Phase L — adaptive compression promotion
from .compression import (
    CompressedArtifact,
    CompressionConfig,
    CompressionLevel,
    CompressionPromoter,
)

__version__ = "0.1.0"

__all__ = [
    # Phase E
    "BudgetViolation",
    "ClosedLoopController",
    "ControlRecord",
    "ControllerConfig",
    "HaltSignal",
    "ReflexionEngine",
    "ReflexionLesson",
    "SkillCandidate",
    "SkillLibrary",
    "StabilityBudget",
    "StabilityState",
    "VoyagerAccumulator",
    "new_control_record",
    # Phase H
    "Ctx2SkillExtractor",
    "CrossTimeReplayValidator",
    "ExtractionResult",
    "SkillDraft",
    "TraceRecord",
    # Phase K
    "CoEvolutionGate",
    "IsolatedVerifier",
    "VerificationOutcome",
    "VerificationReport",
    "VerificationTask",
    # Phase L
    "CompressedArtifact",
    "CompressionConfig",
    "CompressionLevel",
    "CompressionPromoter",
]
