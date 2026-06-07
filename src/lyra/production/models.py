"""Core models for production reliability and agent containment."""

from dataclasses import dataclass, field
from enum import Enum
from time import time


class FailureMode(str, Enum):
    RETRIEVAL_NOISE = "retrieval_noise"
    CONTEXT_OVERLOAD = "context_overload"
    HALLUCINATED_ARGS = "hallucinated_args"
    RECURSIVE_LOOP = "recursive_loop"
    POLLING_TAX = "polling_tax"
    GUARDRAIL_FAILURE = "guardrail_failure"
    BIAS_OVERRIDE = "bias_override"
    API_SCHEMA_CHANGE = "api_schema_change"
    INSTRUCTION_DRIFT = "instruction_drift"
    DESTRUCTIVE_CODE = "destructive_code"


class ReliabilityTier(str, Enum):
    """Conformal prediction reliability tiers."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ExecutionState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class EscapeVector(str, Enum):
    SELF_MODIFICATION = "self_modification"
    NETWORK_EGRESS = "network_egress"
    CODE_INJECTION = "code_injection"
    PROMPT_LEAKAGE = "prompt_leakage"
    RESOURCE_EXFILTRATION = "resource_exfiltration"


@dataclass(frozen=True)
class FailureSignal:
    """Detected failure signal from an agent execution."""

    id: str
    failure_mode: FailureMode
    description: str
    session_id: str
    turn_number: int
    severity: float
    detected_at: float = field(default_factory=time)


@dataclass(frozen=True)
class ReliabilitySnapshot:
    """Point-in-time reliability measurement."""

    total_executions: int
    successful: int
    failed: int
    retried: int
    failure_modes: dict[str, int]
    reliability_score: float
    snapshot_at: float = field(default_factory=time)


@dataclass(frozen=True)
class TrajectorySegment:
    """A segment of agent trajectory for optimization."""

    id: str
    content: str
    token_count: int
    relevance_score: float
    is_redundant: bool = False
    is_expired: bool = False


@dataclass(frozen=True)
class ConformalPrediction:
    """Conformal prediction with formal reliability guarantee."""

    tier: ReliabilityTier
    confidence: float
    prediction_set: tuple[str, ...]
    guarantee_level: float
    cost_estimate: float
    generated_at: float = field(default_factory=time)


@dataclass(frozen=True)
class ContainmentEvent:
    """A containment-related event for audit trail."""

    id: str
    escape_vector: EscapeVector
    description: str
    blocked: bool
    risk_level: float
    source_component: str = ""
    detected_at: float = field(default_factory=time)
