"""Two-phase verifier + cross-channel evidence (Phase 5)."""
from __future__ import annotations

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
from .trace_verifier import (
    MiscitedClaim,
    TraceClaim,
    TraceVerification,
    extract_claims,
    verify_trace,
)
from .tdd_reward import (
    TddRewardComputer,
    TddRewardSignal,
    TddTestOutcome,
    compute_tdd_reward,
)

__all__ = [
    "CrossChannelFinding",
    "EvaluatorFamily",
    "EvidenceError",
    "HeuristicArithmeticPrm",
    "MiscitedClaim",
    "ObjectiveEvidence",
    "ObjectiveVerdict",
    "PrmAdapter",
    "PrmStepScore",
    "PrmTrajectoryScore",
    "StepLabel",
    "SubjectiveResult",
    "SubjectiveVerdict",
    "TddRewardComputer",
    "TddRewardSignal",
    "TddTestOutcome",
    "TraceClaim",
    "TraceVerification",
    "compute_tdd_reward",
    "cross_channel_check",
    "default_prm_adapter",
    "detect_family",
    "extract_claims",
    "is_degraded_eval",
    "validate_file_line",
    "verify_objective",
    "verify_subjective",
    "verify_trace",
]
