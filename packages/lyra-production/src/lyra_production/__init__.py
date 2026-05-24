"""
Lyra Production Hardening - Phase 7

Cell-based deployment, durable execution, database branching,
IETF AIMS agent identity, and AIBOM cryptographic provenance.

This package implements production hardening for Lyra AGI:
- Cell-Based Deployment: Isolated deployment cells with Galileo
  circuit breakers for cascade failure prevention
- Durable Execution: Long-running workflows with state persistence,
  exponential backoff retry, and Saga compensation
- Database Branching: Copy-on-write database forks for safe,
  isolated schema migrations and test environments
- IETF AIMS 8-Layer Agent Identity: Cryptographic identity,
  challenge-response verification, capability attestation,
  key rotation, and revocation
- AIBOM Cryptographic Provenance: Tamper-evident output tracking
  with Merkle-tree chains and machine-readable BOM export
"""

from lyra_production.branching import (
    BranchingConfig,
    BranchNotFoundError,
    DatabaseBranching,
    MigrationConflictError,
)
from lyra_production.cell import (
    CellManager,
    CellNotFoundError,
    CircuitBreakerOpenError,
)
from lyra_production.durable import (
    DurableExecutor,
    StepNotFoundError,
    WorkflowDefinition,
    WorkflowNotFoundError,
)
from lyra_production.identity import (
    AgentIdentityManager,
    IdentityNotFoundError,
    IdentityVerificationError,
)
from lyra_production.models import (
    AgentIdentity,
    AIBOMEntry,
    BranchStatus,
    CapabilityAttestation,
    CellStatus,
    CircuitBreakerState,
    DatabaseBranch,
    DeploymentCell,
    DeploymentConfig,
    HealthStatus,
    IdentityStatus,
    MigrationEntry,
    ProvenanceChain,
    ProvenanceStatus,
    WorkflowExecution,
    WorkflowState,
    WorkflowStep,
    compute_entry_hash,
    compute_merkle_root,
)
from lyra_production.provenance import (
    EntryNotFoundError,
    ProvenanceError,
    ProvenanceTracker,
)

__version__ = "0.1.0"

__all__ = [
    # Models
    "CircuitBreakerState",
    "HealthStatus",
    "CellStatus",
    "WorkflowState",
    "BranchStatus",
    "IdentityStatus",
    "ProvenanceStatus",
    "DeploymentConfig",
    "DeploymentCell",
    "WorkflowStep",
    "WorkflowExecution",
    "MigrationEntry",
    "DatabaseBranch",
    "CapabilityAttestation",
    "AgentIdentity",
    "AIBOMEntry",
    "ProvenanceChain",
    "compute_merkle_root",
    "compute_entry_hash",
    # Cell
    "CellManager",
    "CellNotFoundError",
    "CircuitBreakerOpenError",
    # Durable
    "DurableExecutor",
    "WorkflowDefinition",
    "WorkflowNotFoundError",
    "StepNotFoundError",
    # Branching
    "DatabaseBranching",
    "BranchingConfig",
    "BranchNotFoundError",
    "MigrationConflictError",
    # Identity
    "AgentIdentityManager",
    "IdentityNotFoundError",
    "IdentityVerificationError",
    # Provenance
    "ProvenanceTracker",
    "ProvenanceError",
    "EntryNotFoundError",
]
