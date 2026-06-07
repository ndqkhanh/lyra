"""Core models for claims verification and execution integrity."""

from dataclasses import dataclass, field
from enum import Enum
from time import time


class ViolationSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class GapType(str, Enum):
    """Types of knowing-doing gaps."""

    MISSED_TOOL = "missed_tool"
    WRONG_TOOL = "wrong_tool"
    DELAYED_CALL = "delayed_call"
    INCOMPLETE_ARGS = "incomplete_args"
    HALLUCINATED_RESULT = "hallucinated_result"


class AttackPattern(str, Enum):
    """Adversarial quality gate attack patterns."""

    CONTRADICTION = "contradiction"
    AMBIGUITY = "ambiguity"
    EDGE_CASE = "edge_case"
    PROMPT_INJECTION = "prompt_injection"
    HALLUCINATION_TRAP = "hallucination_trap"


@dataclass(frozen=True)
class Claim:
    """A single verifiable claim extracted from output."""

    id: str
    text: str
    category: str = "general"
    confidence: float = 1.0
    extracted_at: float = field(default_factory=time)


@dataclass(frozen=True)
class SourceMapping:
    """Maps a claim to its verifiable source."""

    claim_id: str
    source_uri: str
    source_text: str
    match_score: float
    verified: bool = False
    verified_at: float | None = None


@dataclass(frozen=True)
class KnowingDoingGap:
    """Detected gap between knowing (tool exists) and doing (not calling it)."""

    id: str
    gap_type: GapType
    tool_name: str
    context: str
    expected_call: str
    actual_behavior: str
    severity: ViolationSeverity = ViolationSeverity.MEDIUM
    detected_at: float = field(default_factory=time)


@dataclass(frozen=True)
class ExecutionIntent:
    """Captured intent behind a tool execution."""

    id: str
    tool_name: str
    intent_description: str
    expected_args: tuple[str, ...]
    expected_outcome: str
    declared_at: float = field(default_factory=time)


@dataclass(frozen=True)
class IntegrityViolation:
    """Detected integrity violation in tool execution."""

    id: str
    tool_name: str
    violation_type: str
    description: str
    severity: ViolationSeverity = ViolationSeverity.HIGH
    args_provided: tuple[str, ...] = ()
    args_expected: tuple[str, ...] = ()
    detected_at: float = field(default_factory=time)


@dataclass(frozen=True)
class AuditReport:
    """Complete claims audit report."""

    claims: tuple[Claim, ...]
    mappings: tuple[SourceMapping, ...]
    faithfulness_score: float
    unverified_claims: int
    verified_claims: int
    generated_at: float = field(default_factory=time)

    @property
    def verification_rate(self) -> float:
        total = self.verified_claims + self.unverified_claims
        if total == 0:
            return 1.0
        return self.verified_claims / total


@dataclass(frozen=True)
class GateResult:
    """Result of an adversarial quality gate challenge."""

    pattern: AttackPattern
    passed: bool
    weaknesses_found: tuple[str, ...]
    resilience_score: float
    challenged_at: float = field(default_factory=time)
