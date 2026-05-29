"""Colony task scheduler with priority queuing, load balancing, and deadline awareness."""

from __future__ import annotations

import asyncio
import heapq
import logging
import time
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class SchedulingError(Exception):
    """Base exception for scheduling errors."""


class NoAvailableAgentError(SchedulingError):
    """Raised when no agent can be assigned to a task."""


class DeadlineExceededError(SchedulingError):
    """Raised when a task would miss its deadline."""


class DuplicateTaskError(SchedulingError):
    """Raised when a task with the same ID is already scheduled."""


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TaskState(Enum):
    PENDING = auto()
    QUEUED = auto()
    ASSIGNED = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()
    EXPIRED = auto()


class SchedulingStrategy(Enum):
    """Load-balancing strategies."""

    ROUND_ROBIN = auto()
    LEAST_CONNECTIONS = auto()
    WEIGHTED = auto()
    AFFINITY = auto()
    DEADLINE_FIRST = auto()


# ---------------------------------------------------------------------------
# Dataclass models
# ---------------------------------------------------------------------------


def _new_id() -> str:
    return uuid4().hex[:12]


def _now() -> float:
    return time.monotonic()


@dataclass(order=True)
class _PrioritizedTask:
    """Internal heap entry for priority queue."""

    priority: float
    created_at: float
    deadline: float
    task_id: str = field(compare=False)
    data: Any = field(compare=False)


@dataclass(frozen=True)
class Task:
    """A scheduled task in the colony.

    Attributes:
        task_id: Unique task identifier.
        task_type: Category / type of the task.
        priority: Base priority (higher = more urgent).
        deadline: Absolute deadline timestamp (monotonic seconds).
        required_capabilities: Capabilities needed to execute.
        affinity_labels: Preferred agent labels for assignment.
        payload: Task-specific data.
        max_retries: Maximum retry attempts on failure.
        timeout_seconds: Maximum execution time before forced termination.
    """

    task_id: str = field(default_factory=_new_id)
    task_type: str = "general"
    priority: int = 5
    deadline: float | None = None
    required_capabilities: tuple[str, ...] = ()
    affinity_labels: dict[str, str] = field(default_factory=dict)
    payload: dict[str, Any] = field(default_factory=dict)
    max_retries: int = 3
    timeout_seconds: float = 300.0

    def __post_init__(self) -> None:
        if self.priority < 1 or self.priority > 10:
            raise SchedulingError("priority must be in [1, 10]")
        if self.max_retries < 0:
            raise SchedulingError("max_retries must be >= 0")


@dataclass(frozen=True)
class TaskAssignment:
    """Records an assignment of a task to an agent.

    Attributes:
        assignment_id: Unique assignment identifier.
        task_id: The assigned task.
        agent_id: The agent that received the task.
        assigned_at: Monotonic timestamp of assignment.
        strategy: Which scheduling strategy was used.
    """

    assignment_id: str = field(default_factory=_new_id)
    task_id: str = ""
    agent_id: str = ""
    assigned_at: float = field(default_factory=_now)
    strategy: SchedulingStrategy = SchedulingStrategy.ROUND_ROBIN


@dataclass
class SchedulerMetrics:
    """Operational metrics for the scheduler."""

    tasks_submitted: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    tasks_expired: int = 0
    tasks_cancelled: int = 0
    avg_wait_time: float = 0.0
    avg_execution_time: float = 0.0
    current_queue_depth: int = 0
    deadline_misses: int = 0

    @property
    def throughput(self) -> float:
        """Tasks completed per metric snapshot."""
        return float(self.tasks_completed)

    @property
    def failure_rate(self) -> float:
        total = self.tasks_completed + self.tasks_failed
        if total == 0:
            return 0.0
        return self.tasks_failed / total


# ---------------------------------------------------------------------------
# Colony Scheduler
# ---------------------------------------------------------------------------


class ColonyScheduler:
    """Priority-queue scheduler with affinity, load balancing, and deadline awareness.

    Supports multiple scheduling strategies: round-robin, least-connections,
    weighted, affinity-based, and deadline-first.
    """

    def __init__(
        self,
        strategy: SchedulingStrategy = SchedulingStrategy.AFFINITY,
        *,
        aging_factor: float = 1.1,
        max_queue_size: int = 10_000,
        coalesce_window: float = 0.5,
    ) -> None:
        self._strategy = strategy
        self._aging_factor = aging_factor
        self._max_queue_size = max_queue_size
        self._coalesce_window = coalesce_window

        # Internal state
        self._heap: list[_PrioritizedTask] = []
        self._task_registry: dict[str, Task] = {}
        self._agent_load: dict[str, int] = defaultdict(int)
        self._agent_capabilities: dict[str, set[str]] = {}
        self._agent_labels: dict[str, dict[str, str]] = {}
        self._pending_assignments: dict[str, TaskAssignment] = {}
        self._task_state: dict[str, TaskState] = {}
        self._rr_index: int = 0
        self._wait_times: list[float] = []
        self._execution_times: list[float] = []
        self._completed: list[TaskAssignment] = []
        self.metrics = SchedulerMetrics()

        # Coalescing buffer
        self._coalesce_buffer: dict[str, list[Task]] = defaultdict(list)
        self._coalesce_lock = asyncio.Lock()

        # Event loop integration
        self._running = False
        self._drain_task: asyncio.Task[Any] | None = None

    # ------------------------------------------------------------------
    # Agent registration
    # ------------------------------------------------------------------

    def register_agent(
        self,
        agent_id: str,
        capabilities: Sequence[str],
        labels: dict[str, str] | None = None,
    ) -> None:
        """Register an agent with the scheduler for task assignment."""
        self._agent_capabilities[agent_id] = set(capabilities)
        self._agent_labels[agent_id] = labels or {}
        self._agent_load.setdefault(agent_id, 0)
        logger.debug("Registered agent %s with capabilities: %s", agent_id, capabilities)

    def unregister_agent(self, agent_id: str) -> None:
        """Remove an agent from scheduling consideration."""
        self._agent_capabilities.pop(agent_id, None)
        self._agent_labels.pop(agent_id, None)
        self._agent_load.pop(agent_id, None)
        # Reassign any pending tasks for this agent
        orphaned = [a for a in self._pending_assignments.values() if a.agent_id == agent_id]
        for assignment in orphaned:
            self._task_state[assignment.task_id] = TaskState.QUEUED
            self._pending_assignments.pop(assignment.assignment_id, None)

    # ------------------------------------------------------------------
    # Task submission
    # ------------------------------------------------------------------

    def submit(self, task: Task) -> str:
        """Submit a task for scheduling. Returns the task ID."""
        if task.task_id in self._task_registry:
            raise DuplicateTaskError(f"Task {task.task_id} already submitted")
        if len(self._heap) >= self._max_queue_size:
            raise SchedulingError("Scheduler queue is full")

        self._task_registry[task.task_id] = task
        self._task_state[task.task_id] = TaskState.PENDING
        self.metrics.tasks_submitted += 1

        # Age the priority slightly to give older tasks an edge
        aged_priority = task.priority * self._aging_factor
        deadline = task.deadline if task.deadline is not None else float("inf")

        entry = _PrioritizedTask(
            priority=-aged_priority,  # negative for max-heap via min-heap
            created_at=_now(),
            deadline=deadline,
            task_id=task.task_id,
            data=task,
        )
        heapq.heappush(self._heap, entry)
        self._task_state[task.task_id] = TaskState.QUEUED
        self.metrics.current_queue_depth = len(self._heap)

        logger.debug(
            "Submitted task %s (priority=%d, type=%s)", task.task_id, task.priority, task.task_type
        )
        return task.task_id

    def submit_batch(self, tasks: Sequence[Task]) -> list[str]:
        """Submit multiple tasks at once. Returns their task IDs."""
        return [self.submit(t) for t in tasks]

    # ------------------------------------------------------------------
    # Task coalescing
    # ------------------------------------------------------------------

    async def coalesce_tasks(self, task_type: str) -> list[Task]:
        """Coalesce tasks of the same type within the coalesce window.

        Returns a batch of tasks that can be executed together.
        """
        async with self._coalesce_lock:
            batch = list(self._coalesce_buffer.pop(task_type, []))
            logger.debug("Coalesced %d tasks of type %s", len(batch), task_type)
            return batch

    async def add_to_coalesce(self, task: Task) -> None:
        """Buffer a task for potential coalescing."""
        async with self._coalesce_lock:
            self._coalesce_buffer[task.task_type].append(task)
            if len(self._coalesce_buffer[task.task_type]) >= 10:
                logger.info(
                    "Coalesce buffer for %s has %d items",
                    task.task_type,
                    len(self._coalesce_buffer[task.task_type]),
                )

    # ------------------------------------------------------------------
    # Scheduling strategies
    # ------------------------------------------------------------------

    async def assign_next(self) -> TaskAssignment | None:
        """Pick the next task from the queue and assign via the current strategy."""
        if not self._heap:
            return None
        if not self._agent_capabilities:
            logger.debug("No agents registered for scheduling")
            return None

        entry = heapq.heappop(self._heap)
        task = self._task_registry[entry.task_id]

        # Check deadline expiry
        if task.deadline is not None and _now() > task.deadline:
            self._task_state[task.task_id] = TaskState.EXPIRED
            self.metrics.tasks_expired += 1
            self.metrics.deadline_misses += 1
            logger.warning("Task %s expired (deadline passed)", task.task_id)
            return None

        agent_id = self._select_agent(task)
        if agent_id is None:
            # Re-queue with boosted priority
            entry.priority -= 1
            heapq.heappush(self._heap, entry)
            raise NoAvailableAgentError(f"No agent for task {task.task_id}")

        assignment = TaskAssignment(
            task_id=task.task_id,
            agent_id=agent_id,
            strategy=self._strategy,
        )
        self._agent_load[agent_id] += 1
        self._pending_assignments[assignment.assignment_id] = assignment
        self._task_state[task.task_id] = TaskState.ASSIGNED
        self.metrics.current_queue_depth = len(self._heap)

        return assignment

    def _select_agent(self, task: Task) -> str | None:
        """Apply the current scheduling strategy to select an agent."""
        candidates = self._filter_candidates(task)
        if not candidates:
            return None

        if self._strategy == SchedulingStrategy.ROUND_ROBIN:
            return self._round_robin(candidates)
        elif self._strategy == SchedulingStrategy.LEAST_CONNECTIONS:
            return self._least_connections(candidates)
        elif self._strategy == SchedulingStrategy.WEIGHTED:
            return self._weighted(candidates)
        elif self._strategy == SchedulingStrategy.AFFINITY:
            return self._affinity(candidates, task)
        elif self._strategy == SchedulingStrategy.DEADLINE_FIRST:
            return self._deadline_first(candidates, task)
        return candidates[0]

    def _filter_candidates(self, task: Task) -> list[str]:
        """Return agent IDs that satisfy the task's requirements."""
        candidates: list[str] = []
        required = set(task.required_capabilities)

        for agent_id, caps in self._agent_capabilities.items():
            if required and not required.issubset(caps):
                continue
            # Affinity check: all labels must match
            labels = self._agent_labels.get(agent_id, {})
            if task.affinity_labels:
                match = all(labels.get(k) == v for k, v in task.affinity_labels.items())
                if not match:
                    continue
            candidates.append(agent_id)

        return candidates

    def _round_robin(self, candidates: list[str]) -> str:
        if not candidates:
            raise NoAvailableAgentError("No candidates for round-robin")
        idx = self._rr_index % len(candidates)
        self._rr_index += 1
        return candidates[idx]

    def _least_connections(self, candidates: list[str]) -> str:
        return min(candidates, key=lambda aid: self._agent_load.get(aid, 0))

    def _weighted(self, candidates: list[str]) -> str:
        # Weight by inverse load: lower load gets higher chance
        total = 0.0
        weights: list[tuple[str, float]] = []
        for aid in candidates:
            load = self._agent_load.get(aid, 0)
            w = 1.0 / (load + 1)
            weights.append((aid, w))
            total += w

        if total == 0:
            return candidates[0]

        import random

        r = random.random() * total
        cumulative = 0.0
        for aid, w in weights:
            cumulative += w
            if r <= cumulative:
                return aid
        return candidates[-1]

    def _affinity(self, candidates: list[str], task: Task) -> str:
        """Select candidate with best label affinity match."""
        if not task.affinity_labels:
            return self._least_connections(candidates)

        best_score = -1.0
        best_agent = candidates[0]
        for aid in candidates:
            score = self._affinity_score(aid, task)
            if score > best_score:
                best_score = score
                best_agent = aid
            elif score == best_score:
                # Tie-break by load
                if self._agent_load.get(aid, 0) < self._agent_load.get(best_agent, 0):
                    best_agent = aid
        return best_agent

    def _affinity_score(self, agent_id: str, task: Task) -> float:
        labels = self._agent_labels.get(agent_id, {})
        if not task.affinity_labels:
            return 0.0
        matches = sum(1 for k, v in task.affinity_labels.items() if labels.get(k) == v)
        return matches / len(task.affinity_labels)

    def _deadline_first(self, candidates: list[str], task: Task) -> str:
        """When deadline-first, just pick least-loaded. The heap already sorts by deadline."""
        return self._least_connections(candidates)

    # ------------------------------------------------------------------
    # Task completion / lifecycle
    # ------------------------------------------------------------------

    def mark_completed(self, assignment: TaskAssignment) -> None:
        """Mark a task as completed."""
        self._task_state[assignment.task_id] = TaskState.COMPLETED
        self._agent_load[assignment.agent_id] = max(
            0, self._agent_load.get(assignment.agent_id, 1) - 1
        )
        self._pending_assignments.pop(assignment.assignment_id, None)
        self._completed.append(assignment)
        self.metrics.tasks_completed += 1

        elapsed = _now() - assignment.assigned_at
        self._execution_times.append(elapsed)

    def mark_failed(self, assignment: TaskAssignment) -> None:
        """Mark a task as failed."""
        self._task_state[assignment.task_id] = TaskState.FAILED
        self._agent_load[assignment.agent_id] = max(
            0, self._agent_load.get(assignment.agent_id, 1) - 1
        )
        self._pending_assignments.pop(assignment.assignment_id, None)
        self.metrics.tasks_failed += 1

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a queued or assigned task."""
        if task_id not in self._task_state:
            return False
        self._task_state[task_id] = TaskState.CANCELLED
        self.metrics.tasks_cancelled += 1
        return True

    # ------------------------------------------------------------------
    # Background drain loop
    # ------------------------------------------------------------------

    async def start_draining(self, interval: float = 0.1) -> None:
        """Start the background drain loop that assigns tasks periodically."""
        self._running = True
        self._drain_task = asyncio.create_task(self._drain_loop(interval))

    async def stop_draining(self) -> None:
        """Stop the background drain loop."""
        self._running = False
        if self._drain_task:
            self._drain_task.cancel()
            try:
                await self._drain_task
            except asyncio.CancelledError:
                pass

    async def _drain_loop(self, interval: float) -> None:
        while self._running:
            try:
                while self._heap:
                    try:
                        await self.assign_next()
                    except NoAvailableAgentError:
                        break  # wait for agents
                await asyncio.sleep(interval)
            except Exception:
                logger.exception("Error in scheduler drain loop")
                await asyncio.sleep(interval)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_queue_depth(self) -> int:
        return len(self._heap)

    def get_pending_count(self) -> int:
        return len(self._pending_assignments)

    def get_agent_load(self, agent_id: str) -> int:
        return self._agent_load.get(agent_id, 0)

    def get_task_state(self, task_id: str) -> TaskState | None:
        return self._task_state.get(task_id)

    def get_load_distribution(self) -> dict[str, int]:
        return dict(self._agent_load)

    @property
    def strategy(self) -> SchedulingStrategy:
        return self._strategy

    @strategy.setter
    def strategy(self, value: SchedulingStrategy) -> None:
        self._strategy = value

    # ------------------------------------------------------------------
    # Snapshots
    # ------------------------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        """Return a current state snapshot for monitoring."""
        return {
            "queue_depth": len(self._heap),
            "pending_assignments": len(self._pending_assignments),
            "registered_agents": len(self._agent_capabilities),
            "strategy": self._strategy.name,
            "metrics": {
                "submitted": self.metrics.tasks_submitted,
                "completed": self.metrics.tasks_completed,
                "failed": self.metrics.tasks_failed,
                "expired": self.metrics.tasks_expired,
                "cancelled": self.metrics.tasks_cancelled,
                "deadline_misses": self.metrics.deadline_misses,
            },
        }
