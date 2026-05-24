"""
Frozen dataclasses and enums for production hardening.

Defines the core data types used across cell-based deployment,
durable execution, database branching, agent identity, and
AIBOM cryptographic provenance.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any


class CircuitBreakerState(Enum):
    """Galileo circuit breaker state machine."""

    CLOSED = auto()
    """Normal operation - requests pass through."""

    OPEN = auto()
    """Tripped - requests are blocked to prevent cascade failure."""

    HALF_OPEN = auto()
    """Testing - limited requests allowed to probe recovery."""


class HealthStatus(Enum):
    """Health status for deployment cells."""

    HEALTHY = auto()
    """Cell is operating normally."""

    DEGRADED = auto()
    """Cell is operational but experiencing issues."""

    UNHEALTHY = auto()
    """Cell is not functioning correctly."""

    UNKNOWN = auto()
    """Cell health cannot be determined."""


class CellStatus(Enum):
    """Deployment lifecycle status for a cell."""

    PENDING = auto()
    """Cell is being deployed."""

    ACTIVE = auto()
    """Cell is running and accepting traffic."""

    DRAINING = auto()
    """Cell is winding down connections."""

    FAILED = auto()
    """Cell deployment failed."""

    TERMINATED = auto()
    """Cell has been shut down."""


class WorkflowState(Enum):
    """Execution state for durable workflows."""

    PENDING = auto()
    """Workflow is queued but not yet started."""

    RUNNING = auto()
    """Workflow is actively executing."""

    COMPLETED = auto()
    """Workflow finished successfully."""

    FAILED = auto()
    """Workflow terminated with an error."""

    COMPENSATING = auto()
    """Saga compensation is running."""

    COMPENSATED = auto()
    """Saga compensation completed."""

    SUSPENDED = auto()
    """Workflow is paused awaiting external input."""


class BranchStatus(Enum):
    """Status of a database branch."""

    ACTIVE = auto()
    """Branch is active and accepting changes."""

    MERGED = auto()
    """Branch has been successfully merged."""

    CONFLICT = auto()
    """Branch has merge conflicts."""

    ROLLED_BACK = auto()
    """Branch changes have been discarded."""

    STALE = auto()
    """Branch is outdated relative to parent."""


class IdentityStatus(Enum):
    """Status of an agent identity."""

    ACTIVE = auto()
    """Identity is valid and operational."""

    REVOKED = auto()
    """Identity has been revoked."""

    EXPIRED = auto()
    """Identity has passed its valid_until date."""

    ROTATING = auto()
    """Keys are being rotated with grace period."""


class ProvenanceStatus(Enum):
    """Verification status of a provenance chain."""

    VERIFIED = auto()
    """Chain is intact and all entries are valid."""

    TAMPERED = auto()
    """Chain has been modified or contains invalid entries."""

    INCOMPLETE = auto()
    """Chain is missing expected entries."""

    UNVERIFIED = auto()
    """Chain has not been verified."""


@dataclass(frozen=True)
class DeploymentConfig:
    """Configuration for a deployment cell."""

    replicas: int = 1
    """Number of replicas for this cell."""

    max_retries: int = 3
    """Maximum retries for health check failures."""

    health_check_interval_sec: float = 30.0
    """How often to run health checks."""

    circuit_breaker_threshold: int = 5
    """Number of failures before circuit breaker opens."""

    circuit_breaker_timeout_sec: float = 60.0
    """How long circuit breaker stays open before half-open."""

    resources: dict[str, str] = field(default_factory=dict)
    """Resource limits (cpu, memory, etc.)."""

    labels: dict[str, str] = field(default_factory=dict)
    """Arbitrary labels for the cell."""

    env_vars: dict[str, str] = field(default_factory=dict)
    """Environment variables for the cell."""


@dataclass(frozen=True)
class DeploymentCell:
    """A single isolated deployment cell."""

    cell_id: str
    """Unique identifier for this cell."""

    version: str
    """Software version deployed in this cell."""

    status: CellStatus
    """Current lifecycle status."""

    health: HealthStatus
    """Current health status."""

    circuit_state: CircuitBreakerState
    """Current circuit breaker state."""

    config: DeploymentConfig
    """Deployment configuration."""

    failure_count: int = 0
    """Consecutive failure count for circuit breaker."""

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    """When this cell was created."""

    last_health_check: datetime | None = None
    """Timestamp of the last health check."""


@dataclass(frozen=True)
class WorkflowStep:
    """A single step within a durable workflow."""

    step_id: str
    """Unique identifier for this step."""

    name: str
    """Human-readable step name."""

    attempt: int = 0
    """Current attempt number."""

    max_attempts: int = 3
    """Maximum retry attempts."""

    status: str = "pending"
    """Step status: pending, running, completed, failed."""

    result: Any = None
    """Step execution result."""

    error: str | None = None
    """Error message if step failed."""

    started_at: datetime | None = None
    """When this step started executing."""

    completed_at: datetime | None = None
    """When this step finished."""


@dataclass(frozen=True)
class WorkflowExecution:
    """A durable workflow execution."""

    workflow_id: str
    """Unique identifier for this execution."""

    name: str
    """Human-readable workflow name."""

    state: WorkflowState
    """Current execution state."""

    attempts: int = 0
    """Total retry attempts across all steps."""

    input: dict[str, Any] = field(default_factory=dict)
    """Workflow input parameters."""

    result: Any = None
    """Final workflow result."""

    history: list[WorkflowStep] = field(default_factory=list)
    """Ordered list of completed steps."""

    error: str | None = None
    """Error message if workflow failed."""

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    """When this workflow was created."""

    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    """When this workflow was last updated."""


@dataclass(frozen=True)
class MigrationEntry:
    """A single database migration."""

    migration_id: str
    """Unique identifier for this migration."""

    description: str
    """Human-readable description."""

    sql_up: str
    """Forward migration SQL."""

    sql_down: str
    """Rollback migration SQL."""

    applied_at: datetime | None = None
    """When this migration was applied."""

    checksum: str = ""
    """SHA-256 checksum of the SQL."""


@dataclass(frozen=True)
class DatabaseBranch:
    """A copy-on-write database fork."""

    branch_id: str
    """Unique identifier for this branch."""

    name: str
    """Human-readable branch name."""

    parent_commit: str
    """Commit hash this branch was created from."""

    status: BranchStatus
    """Current branch status."""

    changes: list[MigrationEntry] = field(default_factory=list)
    """Migrations applied on this branch."""

    head_commit: str = ""
    """Latest commit hash on this branch."""

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    """When this branch was created."""

    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    """When this branch was last modified."""


@dataclass(frozen=True)
class CapabilityAttestation:
    """Attestation that an agent has a specific capability."""

    capability: str
    """Name of the attested capability."""

    attested_by: str
    """Agent ID of the attester."""

    attested_at: datetime
    """When this attestation was created."""

    signature: str
    """Cryptographic signature of the attestation."""

    valid_until: datetime
    """When this attestation expires."""


@dataclass(frozen=True)
class AgentIdentity:
    """IETF AIMS 8-layer agent identity."""

    agent_id: str
    """Unique agent identifier."""

    public_key: str
    """Public key for cryptographic verification."""

    capabilities: frozenset[str]
    """Set of capabilities this agent possesses."""

    attestations: tuple[CapabilityAttestation, ...] = ()
    """Third-party capability attestations."""

    status: IdentityStatus = IdentityStatus.ACTIVE
    """Current identity status."""

    valid_until: datetime | None = None
    """When this identity expires."""

    identity_layer: int = 8
    """IETF AIMS identity layer (1-8)."""

    revocation_reason: str | None = None
    """Reason for revocation, if applicable."""

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    """When this identity was created."""

    rotated_from: str | None = None
    """Previous public key, if rotated."""


@dataclass(frozen=True)
class AIBOMEntry:
    """A single entry in the AI Bill of Materials."""

    entry_id: str
    """Unique identifier for this entry."""

    output_hash: str
    """SHA-256 hash of the agent output."""

    model_info: dict[str, Any]
    """Model identifier, version, provider."""

    prompt_hash: str
    """SHA-256 hash of the prompt."""

    tool_calls: tuple[dict[str, Any], ...] = ()
    """Tool calls made during generation."""

    data_sources: tuple[dict[str, Any], ...] = ()
    """Data sources used in the output."""

    parent_entry: str | None = None
    """Entry ID of the parent output, if chained."""

    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    """When this output was generated."""


@dataclass(frozen=True)
class ProvenanceChain:
    """A Merkle-chain of AIBOM entries for tamper-evident provenance."""

    chain_id: str
    """Unique identifier for this chain."""

    entries: tuple[AIBOMEntry, ...]
    """Ordered entries forming the chain."""

    root_hash: str
    """Merkle root hash of all entries."""

    verification_status: ProvenanceStatus = ProvenanceStatus.UNVERIFIED
    """Current verification status."""

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    """When this chain was created."""


def _sha256(data: str) -> str:
    """Compute SHA-256 hex digest of a string."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def compute_merkle_root(entries: tuple[AIBOMEntry, ...]) -> str:
    """Compute the Merkle root hash for a sequence of AIBOM entries.

    Each leaf is the SHA-256 of the entry's output_hash concatenated
    with its entry_id. Interior nodes combine child hashes.
    """
    if not entries:
        return _sha256("empty")

    leaves = [_sha256(f"{e.entry_id}:{e.output_hash}") for e in entries]

    while len(leaves) > 1:
        if len(leaves) % 2 == 1:
            leaves.append(leaves[-1])
        leaves = [
            _sha256(f"{leaves[i]}{leaves[i + 1]}")
            for i in range(0, len(leaves), 2)
        ]

    return leaves[0]


def compute_entry_hash(entry: AIBOMEntry) -> str:
    """Compute a deterministic hash for an AIBOM entry."""
    payload = json.dumps(
        {
            "entry_id": entry.entry_id,
            "output_hash": entry.output_hash,
            "model_info": entry.model_info,
            "prompt_hash": entry.prompt_hash,
            "tool_calls": list(entry.tool_calls),
            "data_sources": list(entry.data_sources),
            "parent_entry": entry.parent_entry,
            "timestamp": entry.timestamp.isoformat(),
        },
        sort_keys=True,
        default=str,
    )
    return _sha256(payload)


__all__ = [
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
]
