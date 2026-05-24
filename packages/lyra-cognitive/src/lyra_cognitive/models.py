"""
Data models for the Lyra Cognitive Architecture.

Defines the core data structures used across the dual-system cognitive
engine, theater of mind workspace, and cognitive loop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4


class SystemMode(str, Enum):
    """Operating mode of the cognitive system."""

    SYSTEM1 = "system1"          # Fast, pattern-matched execution (<500ms)
    SYSTEM2 = "system2"          # Slow, deliberate reasoning (5-30s)
    META_COGNITIVE = "meta"      # Evaluating which mode to use
    IDLE = "idle"                # No active task


class ConfidenceLevel(str, Enum):
    """Confidence level for a thought, plan, or decision."""

    HIGH = "high"        # >0.8 confidence
    MEDIUM = "medium"    # 0.5-0.8 confidence
    LOW = "low"          # 0.2-0.5 confidence
    UNKNOWN = "unknown"  # <0.2 or not yet assessed

    @classmethod
    def from_score(cls, score: float) -> ConfidenceLevel:
        """Convert a numeric confidence score (0.0-1.0) to a ConfidenceLevel."""
        if score >= 0.8:
            return cls.HIGH
        elif score >= 0.5:
            return cls.MEDIUM
        elif score >= 0.2:
            return cls.LOW
        return cls.UNKNOWN


@dataclass(frozen=True)
class AttentionSignal:
    """
    A signal competing for attention in the global workspace.

    Attributes:
        id: Unique signal identifier.
        source: Origin module or agent that emitted the signal.
        content: The signal payload (text, observation, event).
        urgency: How time-critical the signal is (0.0-1.0).
        relevance: How pertinent to current task (0.0-1.0).
        novelty: How unexpected or new the signal is (0.0-1.0).
        timestamp: When the signal was created.
        metadata: Additional structured context.
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    source: str = ""
    content: str = ""
    urgency: float = 0.0
    relevance: float = 0.0
    novelty: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        for field_name in ("urgency", "relevance", "novelty"):
            value = getattr(self, field_name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"{field_name} must be between 0.0 and 1.0, got {value}"
                )

    @property
    def priority(self) -> float:
        """Composite priority score: urgency * relevance * novelty."""
        return self.urgency * self.relevance * self.novelty


@dataclass(frozen=True)
class Thought:
    """
    A single thought or observation in the theater of mind workspace.

    Attributes:
        id: Unique thought identifier.
        content: The thought text.
        source: Origin module or agent.
        confidence: Estimated confidence in the thought.
        tags: Categorization tags for pattern-matching subscriptions.
        timestamp: When the thought was created.
        attended_count: How many times this thought has been attended to.
        metadata: Additional structured data.
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    content: str = ""
    source: str = ""
    confidence: ConfidenceLevel = ConfidenceLevel.UNKNOWN
    tags: frozenset[str] = field(default_factory=frozenset)
    timestamp: datetime = field(default_factory=datetime.now)
    attended_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Plan:
    """
    A structured plan with ordered steps, dependencies, and cost estimates.

    Attributes:
        id: Unique plan identifier.
        goal: High-level goal description.
        steps: Ordered list of step descriptions.
        dependencies: Mapping of step_index -> set of step_indices it depends on.
        estimated_costs: Mapping of step_index -> estimated token/cost budget.
        confidence: Overall confidence in the plan.
        created_at: When the plan was generated.
        metadata: Additional structured data.
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    goal: str = ""
    steps: tuple[str, ...] = ()
    dependencies: dict[int, frozenset[int]] = field(default_factory=dict)
    estimated_costs: dict[int, float] = field(default_factory=dict)
    confidence: ConfidenceLevel = ConfidenceLevel.UNKNOWN
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def step_count(self) -> int:
        """Number of steps in the plan."""
        return len(self.steps)

    @property
    def total_estimated_cost(self) -> float:
        """Sum of all estimated step costs."""
        return sum(self.estimated_costs.values())

    def get_ready_steps(self, completed: frozenset[int]) -> list[int]:
        """Return step indices whose dependencies are all satisfied."""
        ready: list[int] = []
        for i in range(len(self.steps)):
            if i in completed:
                continue
            deps = self.dependencies.get(i, frozenset())
            if deps.issubset(completed):
                ready.append(i)
        return ready


@dataclass(frozen=True)
class CognitiveState:
    """
    Snapshot of the cognitive system's current state.

    Attributes:
        mode: Current operating mode (System 1, System 2, etc.).
        active_thoughts: Currently attended thought IDs.
        working_memory: Key-value store of active context.
        attention_budget: Remaining attention budget for this cycle.
        task_progress: Fraction of current task complete (0.0-1.0).
        cycle_count: Number of cognitive ticks executed.
        timestamp: When this state was captured.
    """

    mode: SystemMode = SystemMode.IDLE
    active_thoughts: frozenset[str] = field(default_factory=frozenset)
    working_memory: dict[str, Any] = field(default_factory=dict)
    attention_budget: float = 1.0
    task_progress: float = 0.0
    cycle_count: int = 0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class CognitiveTick:
    """
    One complete cycle of the cognitive loop: perceive -> attend -> reason -> decide -> act -> observe.

    Attributes:
        index: Tick sequence number.
        mode: System mode during this tick.
        perception: Observations gathered from environment.
        attended: Thought IDs that received attention this tick.
        reasoning: Reasoning output produced this tick.
        decision: Action or conclusion reached.
        action: Action that was executed.
        observation: Result observed from the action.
        timestamp: When the tick completed.
        metadata: Additional structured data.
    """

    index: int = 0
    mode: SystemMode = SystemMode.IDLE
    perception: tuple[str, ...] = ()
    attended: frozenset[str] = field(default_factory=frozenset)
    reasoning: str = ""
    decision: str = ""
    action: str = ""
    observation: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)
