"""Lyra Integrity — Claims Verification + Tool Execution Integrity."""

from .models import (
    AttackPattern,
    AuditReport,
    Claim,
    ExecutionIntent,
    GapType,
    GateResult,
    IntegrityViolation,
    KnowingDoingGap,
    SourceMapping,
    ViolationSeverity,
)
from .claim_audit import ClaimAuditor
from .knowing_doing import KnowingDoingDetector
from .execution_integrity import ExecutionIntegrity
from .adversarial_gate import AdversarialQualityGate

__version__ = "0.1.0"

__all__ = [
    "Claim",
    "SourceMapping",
    "AuditReport",
    "AttackPattern",
    "GateResult",
    "GapType",
    "KnowingDoingGap",
    "ExecutionIntent",
    "IntegrityViolation",
    "ViolationSeverity",
    "ClaimAuditor",
    "KnowingDoingDetector",
    "ExecutionIntegrity",
    "AdversarialQualityGate",
]
