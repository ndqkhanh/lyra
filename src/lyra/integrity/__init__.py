"""Lyra Integrity — Claims Verification + Tool Execution Integrity."""

from .adversarial_gate import AdversarialQualityGate
from .claim_audit import ClaimAuditor
from .execution_integrity import ExecutionIntegrity
from .knowing_doing import KnowingDoingDetector
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
