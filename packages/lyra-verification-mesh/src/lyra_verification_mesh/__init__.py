"""Lyra Verification Mesh — Multi-layer verification orchestrator.

Three-layer verification:
1. CPL (Continuous Prompt-Level) — Real-time prompt/output checking
2. Pseudo-Formal — Invariant, type, and contract verification
3. Runtime Behavior — Sandbox monitoring and OOD detection

Plus signed attestations, chain of trust, and tamper-evident audit trails.
"""

from __future__ import annotations

from .attestation import (
    Attestation,
    AttestationLevel,
    AttestationService,
    AuditEntry,
    ChainLink,
)
from .cpl_verifier import (
    CheckSeverity,
    CPLCorrection,
    CPLRule,
    CPLVerifier,
)
from .exceptions import (
    AttestationError,
    CPLVerificationError,
    FormalVerificationError,
    MeshConfigurationError,
    RuntimeVerificationError,
    VerificationError,
    VerificationFailedError,
)
from .formal_verifier import (
    ContractVerifier,
    FormalProofResult,
    FormalVerifier,
    Invariant,
    InvariantRegistry,
    PrePostCondition,
    TypeConstraint,
    TypeSafetyVerifier,
)
from .runtime_verifier import (
    ResourceLimits,
    RuntimeVerifier,
    SandboxMetrics,
    SideEffect,
)
from .verification_mesh import (
    ConfidenceAggregator,
    LayerReport,
    MeshReport,
    TemporalProperty,
    VerificationLayer,
    VerificationMesh,
    VerificationModule,
    VerificationResult,
    VerificationStatus,
)

__all__ = [
    # Core
    "VerificationLayer",
    "VerificationStatus",
    "VerificationResult",
    "TemporalProperty",
    "VerificationModule",
    "LayerReport",
    "MeshReport",
    "ConfidenceAggregator",
    "VerificationMesh",
    # CPL
    "CheckSeverity",
    "CPLRule",
    "CPLCorrection",
    "CPLVerifier",
    # Formal
    "Invariant",
    "PrePostCondition",
    "TypeConstraint",
    "FormalProofResult",
    "InvariantRegistry",
    "TypeSafetyVerifier",
    "ContractVerifier",
    "FormalVerifier",
    # Runtime
    "ResourceLimits",
    "SandboxMetrics",
    "SideEffect",
    "RuntimeVerifier",
    # Attestation
    "AttestationLevel",
    "Attestation",
    "ChainLink",
    "AuditEntry",
    "AttestationService",
    # Exceptions
    "VerificationError",
    "VerificationFailedError",
    "CPLVerificationError",
    "FormalVerificationError",
    "RuntimeVerificationError",
    "AttestationError",
    "MeshConfigurationError",
]
