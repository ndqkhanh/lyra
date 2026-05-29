"""
Core models for continual learning — MoLEM, skill packs, and metrics.

All dataclasses are frozen for immutability (functional-core pattern).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ── MoE Models ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class MoEExpert:
    """A single expert in a Mixture-of-Experts layer.

    Each expert specialises in a domain and tracks its usage for pruning
    decisions.
    """

    expert_id: str
    domain: str
    specialization_score: float = 0.5
    last_used: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    usage_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.specialization_score < 0.0 or self.specialization_score > 1.0:
            raise ValueError(
                f"specialization_score must be in [0.0, 1.0], got {self.specialization_score}"
            )

    def touch(self) -> MoEExpert:
        """Return a copy with usage counters updated."""
        return MoEExpert(
            expert_id=self.expert_id,
            domain=self.domain,
            specialization_score=self.specialization_score,
            last_used=datetime.now(timezone.utc),
            usage_count=self.usage_count + 1,
            metadata=self.metadata,
        )


@dataclass(frozen=True)
class MoELayer:
    """A Mixture-of-Experts layer with router weights.

    The router selects *active_count* experts from the pool for each
    forward pass. Weights determine how much each expert contributes.
    """

    experts: tuple[MoEExpert, ...]
    router_weights: tuple[float, ...]
    active_count: int = 2

    def __post_init__(self) -> None:
        if len(self.experts) != len(self.router_weights):
            raise ValueError(
                f"experts and router_weights must have same length; "
                f"got {len(self.experts)} vs {len(self.router_weights)}"
            )

    def top_k_experts(self, k: int | None = None) -> tuple[MoEExpert, ...]:
        """Return the top-k experts by router weight."""
        k = k if k is not None else self.active_count
        k = min(k, len(self.experts))
        sorted_pairs = sorted(
            zip(self.experts, self.router_weights, strict=False),
            key=lambda x: x[1],
            reverse=True,
        )
        return tuple(expert for expert, _ in sorted_pairs[:k])

    def update_expert(self, expert_id: str, updated: MoEExpert) -> MoELayer:
        """Return a new layer with one expert replaced."""
        new_experts = tuple(
            updated if e.expert_id == expert_id else e for e in self.experts
        )
        return MoELayer(
            experts=new_experts,
            router_weights=self.router_weights,
            active_count=self.active_count,
        )

    def update_weights(self, new_weights: tuple[float, ...]) -> MoELayer:
        """Return a new layer with updated router weights."""
        return MoELayer(
            experts=self.experts,
            router_weights=new_weights,
            active_count=self.active_count,
        )


# ── Continual Learning Models ─────────────────────────────────────────────────


@dataclass(frozen=True)
class ContinualEpisode:
    """One episode (task) in a continual learning stream.

    Captures what task was learned, the input distribution characteristics,
    and the resulting performance delta.
    """

    task: str
    input_distribution: str
    performance_delta: float = 0.0
    task_difficulty: float = 0.5
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SkillPack:
    """Compressed domain expertise — GraftLLM-style skill pack.

    Encodes expert weights in a compact form that can be decompressed
    on demand, fused with other skill packs, and transferred across
    model instances.
    """

    domain: str
    compressed_data: tuple[float, ...]
    original_size: int
    compressed_size: int
    compression_ratio: float = 0.0
    version: str = "1.0"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ForgettingMetrics:
    """Metrics for quantifying catastrophic forgetting in continual learning.

    Attributes:
        backward_transfer: How much learning task T+1 degrades performance on task T.
            Negative values indicate forgetting; positive values indicate improvement.
        forward_transfer: How much prior learning helps with new tasks.
        retention: Fraction of original performance retained after N tasks.
        task_count: Number of tasks evaluated.
        detailed_per_task: Per-task performance deltas keyed by task id.
    """

    backward_transfer: float = 0.0
    forward_transfer: float = 0.0
    retention: float = 1.0
    task_count: int = 0
    detailed_per_task: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.retention < 0.0 or self.retention > 1.0:
            raise ValueError(
                f"retention must be in [0.0, 1.0], got {self.retention}"
            )

    @property
    def forgetting_rate(self) -> float:
        """1 - retention: the fraction of performance lost."""
        return 1.0 - self.retention

    @property
    def is_catastrophic(self) -> bool:
        """True if backward transfer is significantly negative (< -0.1)."""
        return self.backward_transfer < -0.1


# ── Utility Models ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ExpertStats:
    """Aggregated statistics for one expert across training."""

    expert_id: str
    domain: str
    total_uses: int = 0
    avg_weight: float = 0.0
    last_weight: float = 0.0
    weight_trend: float = 0.0  # positive = increasing importance


# ── ECC v2 + MetaClaw Models ────────────────────────────────────────────────────


class SkillState(str, Enum):
    EMERGING = "emerging"
    STABLE = "stable"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


class PatternType(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    WORKAROUND = "workaround"
    OPTIMIZATION = "optimization"
    BUG = "bug"


@dataclass(frozen=True)
class SessionTrace:
    """A recorded session trace for pattern analysis."""

    id: str
    session_id: str
    events: tuple[dict[str, Any], ...]
    outcome: str
    duration_seconds: float
    recorded_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RecurringPattern:
    """A detected recurring pattern across session traces."""

    id: str
    pattern_type: PatternType
    description: str
    frequency: int
    sessions: tuple[str, ...]
    confidence: float
    first_seen: float
    last_seen: float

    @property
    def is_strong(self) -> bool:
        return self.confidence >= 0.7 and self.frequency >= 3


@dataclass(frozen=True)
class EvolvedSkill:
    """A skill evolved from detected patterns."""

    id: str
    name: str
    description: str
    source_pattern_ids: tuple[str, ...]
    state: SkillState = SkillState.EMERGING
    version: int = 1
    success_rate: float = 0.0
    usage_count: int = 0
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)

    def record_use(self, success: bool) -> EvolvedSkill:
        new_rate = (self.success_rate * self.usage_count + (1.0 if success else 0.0)) / (self.usage_count + 1)
        return EvolvedSkill(
            id=self.id, name=self.name, description=self.description,
            source_pattern_ids=self.source_pattern_ids, state=self.state,
            version=self.version, success_rate=new_rate,
            usage_count=self.usage_count + 1, last_used=time.time(),
        )


@dataclass(frozen=True)
class CrossRunInsight:
    """An insight that persists across multiple runs."""

    id: str
    insight: str
    category: str
    evidence_count: int
    run_ids: tuple[str, ...]
    confidence: float
    actionable: bool = False
    action_description: str = ""
    created_at: float = field(default_factory=time.time)
