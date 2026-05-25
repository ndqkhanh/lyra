"""Lyra Verification Mesh — Multi-layer verification orchestrator.

Three-layer verification:
1. CPL (Continuous Prompt-Level) — Real-time prompt/output checking
2. Pseudo-Formal — Invariant, type, and contract verification
3. Runtime Behavior — Sandbox monitoring and OOD detection

Plus signed attestations, chain of trust, and tamper-evident audit trails.
"""

from __future__ import annotations

from .verification_mesh import (
    VerificationLayer,
    VerificationStatus,
    VerificationResult,
    TemporalProperty,
    VerificationModule,
    LayerReport,
    MeshReport,
    ConfidenceAggregator,
    VerificationMesh,
)

from .cpl_verifier import (
    CheckSeverity,
    CPLRule,
    CPLCorrection,
    CPLVerifier,
)

from .formal_verifier import (
    Invariant,
    PrePostCondition,
    TypeConstraint,
    FormalProofResult,
    InvariantRegistry,
    TypeSafetyVerifier,
    ContractVerifier,
    FormalVerifier,
)

from .runtime_verifier import (
    ResourceLimits,
    SandboxMetrics,
    SideEffect,
    RuntimeVerifier,
)

from .attestation import (
    AttestationLevel,
    Attestation,
    ChainLink,
    AuditEntry,
    AttestationService,
)

from .exceptions import (
    VerificationError,
    VerificationFailedError,
    CPLVerificationError,
    FormalVerificationError,
    RuntimeVerificationError,
    AttestationError,
    MeshConfigurationError,
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
