"""Two-phase verifier + cross-channel evidence (Phase 5)."""
from __future__ import annotations

from .adversarial import (
    ARISStage,
    ARISVerdict,
    AdversarialReviewer,
    CrossModelPairing,
    ReviewHistory,
    StageResult,
    VerificationEvidence,
)
from .cross_channel import CrossChannelFinding, cross_channel_check
from .evaluator_family import EvaluatorFamily, detect_family, is_degraded_eval
from .evidence import EvidenceError, validate_file_line
from .objective import ObjectiveEvidence, ObjectiveVerdict, verify_objective
from .prm import (
    HeuristicArithmeticPrm,
    PrmAdapter,
    PrmStepScore,
    PrmTrajectoryScore,
    StepLabel,
    default_prm_adapter,
)
from .subjective import SubjectiveResult, SubjectiveVerdict, verify_subjective
from .tdd_reward import (
    TddRewardComputer,
    TddRewardSignal,
    TddTestOutcome,
    compute_tdd_reward,
)
from .tool_audit import (
    AuditFindings,
    KnowingDoingGap,
    ToolAuditor,
    ToolCallRecord,
    ToolRemovalSuggestion,
)
from .trace_verifier import (
    MiscitedClaim,
    TraceClaim,
    TraceVerification,
    extract_claims,
    verify_trace,
)

__all__ = [
    "ARISStage",
    "ARISVerdict",
    "AdversarialReviewer",
    "AuditFindings",
    "CrossModelPairing",
    "CrossChannelFinding",
    "EvaluatorFamily",
    "EvidenceError",
    "HeuristicArithmeticPrm",
    "KnowingDoingGap",
    "MiscitedClaim",
    "ObjectiveEvidence",
    "ObjectiveVerdict",
    "PrmAdapter",
    "PrmStepScore",
    "PrmTrajectoryScore",
    "ReviewHistory",
    "StageResult",
    "StepLabel",
    "SubjectiveResult",
    "SubjectiveVerdict",
    "TddRewardComputer",
    "TddRewardSignal",
    "TddTestOutcome",
    "ToolAuditor",
    "ToolCallRecord",
    "ToolRemovalSuggestion",
    "TraceClaim",
    "TraceVerification",
    "compute_tdd_reward",
    "cross_channel_check",
    "default_prm_adapter",
    "detect_family",
    "extract_claims",
    "is_degraded_eval",
    "validate_file_line",
    "VerificationEvidence",
    "verify_objective",
    "verify_subjective",
    "verify_trace",
]
