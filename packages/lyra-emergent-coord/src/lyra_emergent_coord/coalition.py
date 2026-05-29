"""Coalition formation engine with bidding, Shapley value computation, and dynamic restructuring."""

from __future__ import annotations

import itertools
import logging
import math
import time
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class CoalitionError(Exception):
    """Base exception for coalition formation errors."""


class NoValidCoalitionError(CoalitionError):
    """Raised when no valid coalition can be formed for a task."""


class InsufficientCapabilitiesError(CoalitionError):
    """Raised when no agents possess the required capabilities."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _new_id() -> str:
    return uuid4().hex[:12]


def _now() -> float:
    return time.monotonic()


# ---------------------------------------------------------------------------
# Dataclass models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TaskAdvertisement:
    """A task broadcast to solicit bids from agents.

    Attributes:
        task_id: Unique task identifier.
        task_type: Category of the task.
        complexity: 0.0-1.0 measure of task difficulty.
        required_capabilities: Capabilities needed to execute.
        min_coalition_size: Minimum number of agents required.
        max_coalition_size: Maximum coalition size (-1 for unlimited).
        deadline: Absolute deadline (monotonic seconds).
        reward: Value distributed among coalition members.
    """

    task_id: str = field(default_factory=_new_id)
    task_type: str = "general"
    complexity: float = 0.5
    required_capabilities: tuple[str, ...] = ()
    min_coalition_size: int = 1
    max_coalition_size: int = -1
    deadline: float | None = None
    reward: float = 1.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.complexity <= 1.0:
            raise CoalitionError("complexity must be in [0.0, 1.0]")
        if self.min_coalition_size < 1:
            raise CoalitionError("min_coalition_size must be >= 1")


@dataclass(frozen=True)
class Bid:
    """A bid from an agent for a task.

    Attributes:
        agent_id: The bidding agent.
        task_id: The task being bid on.
        capability_score: How well the agent's capabilities match (0.0-1.0).
        current_load: Current load of the agent (0.0-1.0).
        bid_value: The agent's offered contribution value.
        total_score: Composite score used for ranking.
    """

    agent_id: str
    task_id: str
    capability_score: float = 0.0
    current_load: float = 0.0
    bid_value: float = 0.5
    total_score: float = 0.0

    def __post_init__(self) -> None:
        # Compute total_score if not provided
        if self.total_score == 0.0:
            object.__setattr__(
                self,
                "total_score",
                self.capability_score * 0.5 + (1.0 - self.current_load) * 0.3 + self.bid_value * 0.2,
            )


@dataclass(frozen=True)
class Coalition:
    """A formed coalition of agents for a specific task.

    Attributes:
        id: Unique coalition identifier.
        task_id: The task this coalition addresses.
        leader_id: The elected leader of the coalition.
        member_ids: All agent IDs in the coalition.
        formation_time: When the coalition was formed.
        shapley_values: Computed Shapley value for each member.
        capability_coverage: Fraction of required capabilities covered.
        expected_performance: Predicted performance score.
    """

    id: str = field(default_factory=_new_id)
    task_id: str = ""
    leader_id: str = ""
    member_ids: tuple[str, ...] = ()
    formation_time: float = field(default_factory=_now)
    shapley_values: dict[str, float] = field(default_factory=dict)
    capability_coverage: float = 0.0
    expected_performance: float = 0.0

    @property
    def size(self) -> int:
        return len(self.member_ids)

    @property
    def avg_shapley(self) -> float:
        if not self.shapley_values:
            return 0.0
        return sum(self.shapley_values.values()) / len(self.shapley_values)


# ---------------------------------------------------------------------------
# Coalition Formation Engine
# ---------------------------------------------------------------------------


class CoalitionFormationEngine:
    """Engine for forming coalitions via bidding, Shapley-based value computation,
    and dynamic restructuring.

    Supports:
    - Agent registration with capabilities and load tracking
    - Task advertisements and bidding rounds
    - Optimal coalition selection using Shapley value maximization
    - Dynamic coalition restructuring on membership changes
    - Coalition performance tracking
    """

    def __init__(
        self,
        *,
        max_coalition_search: int = 50,
        capability_weight: float = 0.5,
        load_weight: float = 0.3,
        shapley_weight: float = 0.2,
    ) -> None:
        self._max_coalition_search = max_coalition_search
        self._capability_weight = capability_weight
        self._load_weight = load_weight
        self._shapley_weight = shapley_weight

        # Agent registry
        self._agent_capabilities: dict[str, set[str]] = {}
        self._agent_load: dict[str, float] = {}
        self._agent_performance: dict[str, list[float]] = defaultdict(list)
        self._agent_contribution: dict[str, float] = defaultdict(float)

        # Coalition state
        self._coalitions: dict[str, Coalition] = {}
        self._active_tasks: dict[str, TaskAdvertisement] = {}
        self._coalition_history: list[Coalition] = []

        # Performance tracking
        self._coalition_outcomes: dict[str, list[float]] = defaultdict(list)

    # ------------------------------------------------------------------
    # Agent registration
    # ------------------------------------------------------------------

    def register_agent(
        self,
        agent_id: str,
        capabilities: Sequence[str],
        initial_load: float = 0.0,
    ) -> None:
        """Register an agent for coalition formation."""
        self._agent_capabilities[agent_id] = set(capabilities)
        self._agent_load[agent_id] = initial_load
        logger.debug("Registered agent %s with %d capabilities", agent_id, len(capabilities))

    def unregister_agent(self, agent_id: str) -> None:
        """Remove an agent and restructure affected coalitions."""
        self._agent_capabilities.pop(agent_id, None)
        self._agent_load.pop(agent_id, None)
        self._agent_performance.pop(agent_id, None)
        # Remove from any active coalitions and trigger restructuring
        affected = [
            cid for cid, c in self._coalitions.items() if agent_id in c.member_ids
        ]
        for cid in affected:
            self._coalitions.pop(cid, None)
        logger.debug("Unregistered agent %s (affected %d coalitions)", agent_id, len(affected))

    def update_agent_load(self, agent_id: str, load: float) -> None:
        """Update an agent's current load."""
        self._agent_load[agent_id] = load

    def record_contribution(self, agent_id: str, score: float) -> None:
        """Record a performance contribution for an agent."""
        self._agent_performance[agent_id].append(score)
        # Keep last 100 entries
        if len(self._agent_performance[agent_id]) > 100:
            self._agent_performance[agent_id] = self._agent_performance[agent_id][-100:]

    def get_agent_performance(self, agent_id: str) -> float:
        """Return average performance score for an agent."""
        scores = self._agent_performance.get(agent_id, [])
        return sum(scores) / len(scores) if scores else 0.5

    # ------------------------------------------------------------------
    # Bidding
    # ------------------------------------------------------------------

    async def advertise_task(self, advertisement: TaskAdvertisement) -> None:
        """Register a task advertisement for bidding."""
        self._active_tasks[advertisement.task_id] = advertisement

    async def collect_bids(self, task_id: str) -> list[Bid]:
        """Collect bids from all registered agents for a given task."""
        advertisement = self._active_tasks.get(task_id)
        if advertisement is None:
            raise CoalitionError(f"No advertisement for task {task_id}")

        bids: list[Bid] = []
        required = set(advertisement.required_capabilities)

        for agent_id, caps in self._agent_capabilities.items():
            if required and not caps.intersection(required):
                continue

            overlap = len(caps & required)
            cap_score = overlap / max(len(required), 1) if required else 0.5

            load = self._agent_load.get(agent_id, 0.0)
            perf = self.get_agent_performance(agent_id)

            bid = Bid(
                agent_id=agent_id,
                task_id=task_id,
                capability_score=cap_score,
                current_load=load,
                bid_value=perf,
            )
            bids.append(bid)

        # Sort by total_score descending
        bids.sort(key=lambda b: b.total_score, reverse=True)
        logger.debug("Collected %d bids for task %s", len(bids), task_id)
        return bids

    # ------------------------------------------------------------------
    # Coalition formation
    # ------------------------------------------------------------------

    async def form_coalition(self, task_id: str) -> Coalition:
        """Form the optimal coalition for a task using Shapley value maximization."""
        advertisement = self._active_tasks.get(task_id)
        if advertisement is None:
            raise CoalitionError(f"No advertisement for task {task_id}")

        bids = await self.collect_bids(task_id)
        if not bids:
            raise NoValidCoalitionError(f"No agents available for task {task_id}")

        max_size = advertisement.max_coalition_size if advertisement.max_coalition_size > 0 else min(len(bids), self._max_coalition_search)
        min_size = advertisement.min_coalition_size

        best_coalition: Coalition | None = None
        best_value = -float("inf")

        # Search coalition sizes from min to max
        for size in range(min_size, min(max_size, len(bids)) + 1):
            # Try top N combinations based on bids
            top_bids = bids[:min(size * 2, len(bids))]
            for combo in itertools.combinations(top_bids, size):
                member_ids = tuple(b.agent_id for b in combo)
                covered_caps = self._compute_capability_coverage(member_ids, set(advertisement.required_capabilities))
                shapley = self._compute_shapley_values(member_ids)

                coalition_value = (
                    covered_caps * self._capability_weight
                    + sum(shapley.values()) / max(len(shapley), 1) * self._shapley_weight
                    - self._compute_load_penalty(member_ids) * self._load_weight
                )

                if coalition_value > best_value:
                    best_value = coalition_value
                    leader = self._elect_leader_id(member_ids)
                    best_coalition = Coalition(
                        task_id=task_id,
                        leader_id=leader,
                        member_ids=member_ids,
                        shapley_values=shapley,
                        capability_coverage=covered_caps,
                        expected_performance=coalition_value,
                    )

            if len(bids) > size * 2:
                break

        if best_coalition is None:
            raise NoValidCoalitionError(f"Could not form valid coalition for task {task_id}")

        self._coalitions[best_coalition.id] = best_coalition
        self._coalition_history.append(best_coalition)
        logger.info(
            "Formed coalition %s: %d members, leader=%s, coverage=%.2f",
            best_coalition.id,
            best_coalition.size,
            best_coalition.leader_id,
            best_coalition.capability_coverage,
        )
        return best_coalition

    # ------------------------------------------------------------------
    # Shapley value computation
    # ------------------------------------------------------------------

    def _compute_shapley_values(self, member_ids: tuple[str, ...]) -> dict[str, float]:
        """Compute approximate Shapley values for coalition members.

        Uses a sampling-based approximation for large coalitions.
        """
        n = len(member_ids)
        if n == 0:
            return {}
        if n == 1:
            return {member_ids[0]: 1.0}

        # For small coalitions, compute exact Shapley
        if n <= 5:
            return self._exact_shapley(member_ids)

        # For larger, use monte carlo approximation
        return self._approx_shapley(member_ids, samples=100)

    def _exact_shapley(self, member_ids: tuple[str, ...]) -> dict[str, float]:
        """Exact Shapley value computation via all permutations."""
        n = len(member_ids)
        shapley: dict[str, float] = defaultdict(float)

        for perm in itertools.permutations(member_ids):
            prev_value = 0.0
            for i, agent in enumerate(perm):
                current = self._coalition_value(perm[: i + 1])
                marginal = current - prev_value
                shapley[agent] += marginal
                prev_value = current

        factorial = math.factorial(n)
        return {k: v / factorial for k, v in shapley.items()}

    def _approx_shapley(self, member_ids: tuple[str, ...], samples: int = 100) -> dict[str, float]:
        """Monte Carlo approximation of Shapley values."""
        import random
        shapley: dict[str, float] = defaultdict(float)

        for _ in range(samples):
            perm = list(member_ids)
            random.shuffle(perm)
            prev_value = 0.0
            for i, agent in enumerate(perm):
                current = self._coalition_value(perm[: i + 1])
                shapley[agent] += current - prev_value
                prev_value = current

        return {k: v / samples for k, v in shapley.items()}

    def _coalition_value(self, members: list[str] | tuple[str, ...]) -> float:
        """Compute the value of a coalition subset."""
        if not members:
            return 0.0
        total = 0.0
        for agent_id in members:
            perf = self.get_agent_performance(agent_id)
            caps = len(self._agent_capabilities.get(agent_id, set()))
            total += perf * (1.0 + caps * 0.1)
        return total

    # ------------------------------------------------------------------
    # Coverage and utility
    # ------------------------------------------------------------------

    def _compute_capability_coverage(
        self,
        member_ids: tuple[str, ...],
        required: set[str],
    ) -> float:
        if not required:
            return 1.0
        covered: set[str] = set()
        for aid in member_ids:
            covered.update(self._agent_capabilities.get(aid, set()))
        return len(covered & required) / len(required)

    def _compute_load_penalty(self, member_ids: tuple[str, ...]) -> float:
        return sum(self._agent_load.get(aid, 0.0) for aid in member_ids) / max(len(member_ids), 1)

    def _elect_leader_id(self, member_ids: tuple[str, ...]) -> str:
        """Elect the best leader from member IDs."""
        if not member_ids:
            return "unknown"
        best = member_ids[0]
        best_score = self.get_agent_performance(best)
        for aid in member_ids[1:]:
            score = self.get_agent_performance(aid)
            if score > best_score:
                best_score = score
                best = aid
        return best

    # ------------------------------------------------------------------
    # Dynamic restructuring
    # ------------------------------------------------------------------

    async def restructure_coalition(self, coalition_id: str) -> Coalition:
        """Restructure a coalition after member changes."""
        coalition = self._coalitions.get(coalition_id)
        if coalition is None:
            raise CoalitionError(f"Coalition {coalition_id} not found")

        # Remove departed members
        current = tuple(
            aid for aid in coalition.member_ids if aid in self._agent_capabilities
        )

        if len(current) < 1:
            # Reform from scratch
            task_id = coalition.task_id
            del self._coalitions[coalition_id]
            return await self.form_coalition(task_id)

        # Recompute with current members
        shapley = self._compute_shapley_values(current)
        new_coalition = Coalition(
            task_id=coalition.task_id,
            leader_id=self._elect_leader_id(current),
            member_ids=current,
            shapley_values=shapley,
            capability_coverage=coalition.capability_coverage,
            expected_performance=coalition.expected_performance,
        )
        self._coalitions[coalition_id] = new_coalition
        logger.info("Restructured coalition %s (%d members)", coalition_id, len(current))
        return new_coalition

    # ------------------------------------------------------------------
    # Performance tracking
    # ------------------------------------------------------------------

    def record_coalition_outcome(self, coalition_id: str, score: float) -> None:
        """Record the outcome/performance of a coalition."""
        self._coalition_outcomes[coalition_id].append(score)
        if coalition_id in self._coalitions:
            coalition = self._coalitions[coalition_id]
            for member_id in coalition.member_ids:
                self.record_contribution(member_id, score / coalition.size)

    def get_coalition_performance(self, coalition_id: str) -> float:
        """Average performance of a coalition."""
        outcomes = self._coalition_outcomes.get(coalition_id, [])
        return sum(outcomes) / len(outcomes) if outcomes else 0.0

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_coalition(self, coalition_id: str) -> Coalition | None:
        """Retrieve a coalition by ID."""
        return self._coalitions.get(coalition_id)

    def get_coalitions_for_agent(self, agent_id: str) -> list[Coalition]:
        """Get all active coalitions containing an agent."""
        return [c for c in self._coalitions.values() if agent_id in c.member_ids]

    def get_coalitions_for_task(self, task_id: str) -> list[Coalition]:
        """Get all coalitions formed for a specific task."""
        return [c for c in self._coalitions.values() if c.task_id == task_id]

    def dissolve_coalition(self, coalition_id: str) -> bool:
        """Dissolve a coalition. Returns True if it existed."""
        return self._coalitions.pop(coalition_id, None) is not None

    @property
    def active_coalition_count(self) -> int:
        return len(self._coalitions)

    def snapshot(self) -> dict[str, Any]:
        """Return a state snapshot for monitoring."""
        return {
            "active_coalitions": len(self._coalitions),
            "registered_agents": len(self._agent_capabilities),
            "active_tasks": len(self._active_tasks),
            "coalitions": [
                {
                    "id": c.id,
                    "task_id": c.task_id,
                    "size": c.size,
                    "leader": c.leader_id,
                    "coverage": c.capability_coverage,
                    "performance": c.expected_performance,
                }
                for c in self._coalitions.values()
            ],
        }
