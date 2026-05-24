"""
Core models for ReflAct reasoning, GRPO training, and reasoning strategies.

Frozen dataclasses for immutability — consistent with Lyra's functional-core design.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


# ── ReflAct Models ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ReasoningStep:
    """A single step in a ReflAct reasoning trajectory.

    Combines the Reflexion (thought) and Acting (action/observation) phases
    into one atomic unit. Each step carries a confidence score so the reasoner
    can decide whether to continue or back-track.
    """

    step_number: int
    thought: str
    action: str
    observation: str
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.confidence < 0.0 or self.confidence > 1.0:
            raise ValueError(
                f"confidence must be in [0.0, 1.0], got {self.confidence}"
            )


@dataclass(frozen=True)
class ReasoningTrace:
    """Complete trace of a ReflAct reasoning session.

    Holds the ordered steps plus per-task metadata such as the originating
    task description, strategy label, and wall-clock duration.
    """

    task: str
    steps: Tuple[ReasoningStep, ...] = ()
    outcome: str = "pending"
    duration: float = 0.0
    token_count: int = 0
    strategy: str = "reflect"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_step(self, step: ReasoningStep) -> "ReasoningTrace":
        """Return a new trace with *step* appended (immutable update)."""
        return ReasoningTrace(
            task=self.task,
            steps=self.steps + (step,),
            outcome=self.outcome,
            duration=self.duration,
            token_count=self.token_count,
            strategy=self.strategy,
            created_at=self.created_at,
            metadata=self.metadata,
        )

    def with_outcome(self, outcome: str) -> "ReasoningTrace":
        """Return a new trace with *outcome* set."""
        return ReasoningTrace(
            task=self.task,
            steps=self.steps,
            outcome=outcome,
            duration=self.duration,
            token_count=self.token_count,
            strategy=self.strategy,
            created_at=self.created_at,
            metadata=self.metadata,
        )

    def final_step(self) -> Optional[ReasoningStep]:
        """Return the last step in the trace, if any."""
        return self.steps[-1] if self.steps else None

    @property
    def num_steps(self) -> int:
        return len(self.steps)


@dataclass(frozen=True)
class ReflActEpisode:
    """A completed ReflAct episode with task, trace, outcome, and lessons.

    Lessons are derived via reflection and used to adapt future reasoning.
    """

    task: str
    trace: ReasoningTrace
    outcome: str
    lessons_learned: Tuple[str, ...] = ()
    success: bool = False
    score: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ── GRPO / SPIRAL Models ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class GRPOTrajectory:
    """One training sample for Group Relative Policy Optimization.

    Holds the prompt, the set of generated responses, the corresponding
    rewards, and the computed advantages (response-level advantage over the
    group mean).
    """

    prompt: str
    responses: Tuple[str, ...]
    rewards: Tuple[float, ...]
    advantages: Tuple[float, ...] = ()
    group_mean: float = 0.0
    group_std: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if len(self.responses) != len(self.rewards):
            raise ValueError(
                f"responses and rewards must have same length; "
                f"got {len(self.responses)} vs {len(self.rewards)}"
            )

    @property
    def best_response(self) -> Optional[str]:
        """Return the response with the highest reward."""
        if not self.responses or not self.rewards:
            return None
        idx = max(range(len(self.rewards)), key=lambda i: self.rewards[i])
        return self.responses[idx]


@dataclass(frozen=True)
class SpiralSample:
    """One sample for SPIRAL (Synthetic Preference Iterative Refinement).

    Holds a prompt together with multiple candidate responses and their
    quality scores, so the trainer can construct preference pairs.
    """

    prompt: str
    candidate_responses: Tuple[str, ...]
    scores: Tuple[float, ...]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if len(self.candidate_responses) != len(self.scores):
            raise ValueError(
                f"candidate_responses and scores must have same length; "
                f"got {len(self.candidate_responses)} vs {len(self.scores)}"
            )

    def best_candidate(self) -> Optional[str]:
        """Return the highest-scored candidate."""
        if not self.candidate_responses or not self.scores:
            return None
        idx = max(range(len(self.scores)), key=lambda i: self.scores[i])
        return self.candidate_responses[idx]

    def worst_candidate(self) -> Optional[str]:
        """Return the lowest-scored candidate."""
        if not self.candidate_responses or not self.scores:
            return None
        idx = min(range(len(self.scores)), key=lambda i: self.scores[i])
        return self.candidate_responses[idx]

    def preference_pair(self) -> Tuple[Optional[str], Optional[str]]:
        """Return (chosen, rejected) pair for DPO-style training."""
        return self.best_candidate(), self.worst_candidate()


# ── Strategy Metadata Models ──────────────────────────────────────────────────


@dataclass(frozen=True)
class ThoughtNode:
    """A node in a tree-of-thoughts exploration."""

    id: str
    content: str
    score: float = 0.0
    depth: int = 0
    visits: int = 0
    parent_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AnaloguePair:
    """A source-target analogue pair for analogical reasoning."""

    source_domain: str
    target_domain: str
    structural_mapping: Dict[str, str] = field(default_factory=dict)
    similarity_score: float = 0.0
    transfer_confidence: float = 0.0
