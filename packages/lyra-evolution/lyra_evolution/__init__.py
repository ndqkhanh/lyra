"""lyra-evolution: closed-loop self-evolution for Lyra (Phases E, H, K, L)."""
from __future__ import annotations

# Phase E — closed-loop controller
from .control_record import ControlRecord, new_control_record
from .controller import ClosedLoopController, ControllerConfig, HaltSignal, HITLCallback
from .integration import create_hitl_callback
from .reflexion import ReflexionEngine, ReflexionLesson
from .sandbox_verifier import SafetyRule, SandboxVerifier
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

# MOSS-style source-level evolution
from .moss_evolution import (
    SourceEvolutionEngine,
    SourcePatch,
    PatchResult,
    PatchTarget,
    ModificationSeverity,
    UserConsentGate,
    GovernanceJIT,
)

# Phase 6 — Council Mode, Escher-Loop RSI, GEAR-Evolve, Self-Improvement
from .council import CouncilMode as _CouncilMode
from .escher import EscherLoop as _EscherLoop
from .gear import GEAREvolve as _GEAREvolve
from .improvement import SelfImprovement as _SelfImprovement
from .models import (  # noqa: F401
    CouncilDecision,
    CouncilMember,
    CouncilVote,
    EscherGeneration,
    EscherSolver,
    EvolutionMetrics,
    GEARStrategy,
)

CouncilMode = _CouncilMode
EscherLoop = _EscherLoop
GEAREvolve = _GEAREvolve
SelfImprovement = _SelfImprovement

__version__ = "0.2.0"

__all__ = [
    # Phase E
    "BudgetViolation",
    "ClosedLoopController",
    "ControlRecord",
    "ControllerConfig",
    "HaltSignal",
    "HITLCallback",
    "ReflexionEngine",
    "ReflexionLesson",
    "SafetyRule",
    "SandboxVerifier",
    "SkillCandidate",
    "SkillLibrary",
    "StabilityBudget",
    "StabilityState",
    "VoyagerAccumulator",
    "create_hitl_callback",
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
    # MOSS-style source-level evolution
    "SourceEvolutionEngine",
    "SourcePatch",
    "PatchResult",
    "PatchTarget",
    "ModificationSeverity",
    "UserConsentGate",
    "GovernanceJIT",
    # Phase 6 — Council Mode, Escher-Loop RSI, GEAR-Evolve, Self-Improvement
    "CouncilMember",
    "CouncilVote",
    "CouncilDecision",
    "CouncilMode",
    "EscherSolver",
    "EscherGeneration",
    "EscherLoop",
    "GEARStrategy",
    "GEAREvolve",
    "SelfImprovement",
    "EvolutionMetrics",
]
