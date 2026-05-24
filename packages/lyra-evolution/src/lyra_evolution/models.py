"""Frozen dataclasses for the lyra-evolution package."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


def _utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(UTC)


def _new_id() -> str:
    """Generate a unique identifier."""
    return uuid4().hex[:12]


# ---------------------------------------------------------------------------
# Council Mode
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CouncilMember:
    """A member of the multi-agent council.

    Attributes:
        agent_id: Unique identifier for the agent.
        expertise: List of domain expertise tags.
        weight: Voting weight (higher = more influential).
        performance_history: Track record of correct decisions.
    """

    agent_id: str = field(default_factory=_new_id)
    expertise: tuple[str, ...] = ()
    weight: float = 1.0
    performance_history: tuple[float, ...] = ()

    def update_performance(self, new_score: float) -> CouncilMember:
        """Return a new member with an appended performance score."""
        return CouncilMember(
            agent_id=self.agent_id,
            expertise=self.expertise,
            weight=self.weight,
            performance_history=(*self.performance_history, new_score),
        )

    @property
    def average_performance(self) -> float:
        """Mean of historical scores, or 0.5 if no history."""
        if not self.performance_history:
            return 0.5
        return sum(self.performance_history) / len(self.performance_history)


@dataclass(frozen=True)
class CouncilVote:
    """A single vote cast by a council member.

    Attributes:
        member_id: The voting member's identifier.
        decision: The member's chosen option or verdict.
        confidence: 0.0 – 1.0 confidence score.
        reasoning: Free-text rationale for the vote.
        timestamp: When the vote was cast.
    """

    member_id: str
    decision: str
    confidence: float = 0.5
    reasoning: str = ""
    timestamp: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0, 1], got {self.confidence}")


@dataclass(frozen=True)
class CouncilDecision:
    """The aggregated outcome of a council vote.

    Attributes:
        final_decision: The winning option.
        votes: All votes cast during deliberation.
        consensus_level: 0.0 – 1.0 measure of agreement.
        dissenting_opinions: Minority rationales.
        metadata: Arbitrary extra context.
    """

    final_decision: str
    votes: tuple[CouncilVote, ...] = ()
    consensus_level: float = 0.0
    dissenting_opinions: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Escher-Loop Recursive Self-Improvement
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EscherSolver:
    """A single solution in the Escher-Loop population.

    Attributes:
        solution_id: Unique solution identifier.
        content: Raw solution data (text, code, plan, etc.).
        fitness_score: Objective quality score assigned by the critic.
        parent_ids: Lineage tracking (empty for initial population).
        generation: Which generation produced this solver.
    """

    solution_id: str = field(default_factory=_new_id)
    content: str = ""
    fitness_score: float = 0.0
    parent_ids: tuple[str, ...] = ()
    generation: int = 0


@dataclass(frozen=True)
class EscherGeneration:
    """A snapshot of one Escher-Loop generation.

    Attributes:
        solutions: All solutions in this generation.
        scores: Per-solution fitness scores (parallel to solutions).
        generation_number: Monotonic generation counter.
    """

    solutions: tuple[EscherSolver, ...] = ()
    scores: tuple[float, ...] = ()
    generation_number: int = 0

    @property
    def best_solution(self) -> EscherSolver | None:
        """Return the solution with the highest fitness, if any."""
        if not self.solutions:
            return None
        best_idx = max(range(len(self.scores)), key=lambda i: self.scores[i])
        return self.solutions[best_idx]

    @property
    def average_score(self) -> float:
        """Mean fitness across the generation."""
        if not self.scores:
            return 0.0
        return sum(self.scores) / len(self.scores)


# ---------------------------------------------------------------------------
# GEAR-Evolve Search
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GEARStrategy:
    """A search strategy registered in GEAR-Evolve.

    Attributes:
        strategy_id: Unique strategy identifier.
        problem_features: Features that describe problems this strategy is good for.
        success_rate: Historical success rate (0-1).
        exploration_weight: Current weight for exploration vs exploitation.
        total_uses: Number of times this strategy has been tried.
        last_used: Timestamp of most recent use.
    """

    strategy_id: str = field(default_factory=_new_id)
    problem_features: tuple[float, ...] = ()
    success_rate: float = 0.5
    exploration_weight: float = 0.5
    total_uses: int = 0
    last_used: datetime | None = None


# ---------------------------------------------------------------------------
# Self-Improvement
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EvolutionMetrics:
    """Aggregate metrics for one generation of self-improvement.

    Attributes:
        generation: Generation index.
        avg_fitness: Mean fitness of the population.
        best_fitness: Maximum fitness in the population.
        diversity: Population diversity (0-1, higher = more varied).
        improvement_rate: Delta from previous generation's best fitness.
        timestamp: When the metrics were recorded.
    """

    generation: int
    avg_fitness: float = 0.0
    best_fitness: float = 0.0
    diversity: float = 0.0
    improvement_rate: float = 0.0
    timestamp: datetime = field(default_factory=_utc_now)
