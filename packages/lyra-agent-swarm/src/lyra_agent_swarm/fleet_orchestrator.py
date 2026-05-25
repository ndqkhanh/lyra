"""Plan 12: Fleet Orchestrator — parallel fan-out, map-reduce, and fleet management.

Ties together the existing squad/dispatcher/autopilot infrastructure with
Plan 12 parallel execution patterns.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from itertools import islice
from uuid import uuid4


class FleetStatus(Enum):
    FORMING = "forming"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    DISSOLVED = "dissolved"


class ExecutionPattern(Enum):
    FAN_OUT = "fan_out"
    MAP_REDUCE = "map_reduce"
    DAG = "dag"
    DEBATE = "debate"
    SEQUENTIAL = "sequential"


class TaskItemStatus(Enum):
    QUEUED = "queued"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


def _new_id() -> str:
    return f"fleet_{uuid4().hex[:12]}"


# ── Data Models ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class TaskItem:
    """A single unit of work in a fan-out or map-reduce operation.

    Attributes:
        id: Unique task identifier.
        input: The input data for this task (e.g. file path, chunk).
        status: Current execution status.
        result: Output from the task, if completed.
        error: Error message if failed.
        assigned_agent: ID of the agent handling this task.
        started_at: When execution began.
        completed_at: When execution finished.
    """

    id: str = field(default_factory=lambda: f"task_{uuid4().hex[:8]}")
    input: str = ""
    status: TaskItemStatus = TaskItemStatus.QUEUED
    result: str = ""
    error: str = ""
    assigned_agent: str = ""
    started_at: float = 0.0
    completed_at: float = 0.0


@dataclass(frozen=True)
class FanOutBatch:
    """A batch of tasks dispatched in a single fan-out wave.

    Attributes:
        batch_id: Unique batch identifier.
        tasks: Tasks in this batch.
        pattern: The execution pattern used.
        agent_count: Number of agents assigned.
        started_at: When the batch was dispatched.
    """

    batch_id: str = field(default_factory=lambda: f"batch_{uuid4().hex[:8]}")
    tasks: tuple[TaskItem, ...] = ()
    pattern: ExecutionPattern = ExecutionPattern.FAN_OUT
    agent_count: int = 0
    started_at: float = field(default_factory=time.time)


@dataclass(frozen=True)
class MapReduceResult:
    """Result of a map-reduce operation.

    Attributes:
        map_results: Results from the map phase.
        synthesis: The synthesized/reduced output.
        map_agent_count: Number of agents in the map phase.
        reduce_agent: Agent that performed the reduction.
        total_tokens: Estimated token usage.
    """

    map_results: tuple[str, ...] = ()
    synthesis: str = ""
    map_agent_count: int = 0
    reduce_agent: str = ""
    total_tokens: int = 0


@dataclass(frozen=True)
class FleetMetrics:
    """Runtime metrics for a fleet.

    Attributes:
        total_tasks: Total tasks in the fleet.
        completed_tasks: Tasks successfully completed.
        failed_tasks: Tasks that failed.
        running_tasks: Tasks currently executing.
        queued_tasks: Tasks waiting for assignment.
        total_agents: Number of agents in the fleet.
        active_agents: Agents currently working.
        idle_agents: Agents waiting for work.
        total_tokens: Estimated token usage.
        total_cost_usd: Estimated cost.
        elapsed_seconds: Time since fleet creation.
        throughput_tasks_per_min: Task processing rate.
    """

    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    running_tasks: int = 0
    queued_tasks: int = 0
    total_agents: int = 0
    active_agents: int = 0
    idle_agents: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    elapsed_seconds: float = 0.0
    throughput_tasks_per_min: float = 0.0


@dataclass(frozen=True)
class Fleet:
    """Immutable fleet definition.

    Attributes:
        id: Unique fleet identifier.
        name: Human-readable fleet name.
        status: Current fleet status.
        agent_ids: IDs of agents in the fleet.
        squad_ids: IDs of squads in the fleet.
        tasks: All task items.
        batches: Completed execution batches.
        metrics: Current fleet metrics.
        created_at: Fleet creation timestamp.
    """

    id: str = field(default_factory=_new_id)
    name: str = ""
    status: FleetStatus = FleetStatus.FORMING
    agent_ids: tuple[str, ...] = ()
    squad_ids: tuple[str, ...] = ()
    tasks: tuple[TaskItem, ...] = ()
    batches: tuple[FanOutBatch, ...] = ()
    metrics: FleetMetrics = field(default_factory=FleetMetrics)
    created_at: float = field(default_factory=time.time)

    @property
    def task_count(self) -> int:
        return len(self.tasks)

    @property
    def agent_count(self) -> int:
        return len(self.agent_ids)

    @property
    def squad_count(self) -> int:
        return len(self.squad_ids)


# ── Fleet Orchestrator ─────────────────────────────────────────────────────


class FleetOrchestrator:
    """Manages fleet lifecycle and parallel execution patterns.

    Usage::

        orch = FleetOrchestrator()
        fleet = orch.create_fleet("refactor-fleet", agent_ids=["a1","a2","a3"])

        # Fan-out: distribute items across agents
        items = ["src/a.py", "src/b.py", "src/c.py"]
        results = orch.fan_out(fleet.id, items, agent_type="coding")

        # Map-reduce: map per-file, reduce via synthesis
        result = orch.map_reduce("analyze_file", "synthesize", items)
    """

    def __init__(self) -> None:
        self._fleets: dict[str, Fleet] = {}
        self._task_results: dict[str, str] = {}  # task_id → result
        self._run_history: deque[str] = deque(maxlen=1000)

    # ── Fleet CRUD ────────────────────────────────────────────────────────

    def create_fleet(
        self,
        name: str,
        agent_ids: tuple[str, ...] = (),
        squad_ids: tuple[str, ...] = (),
    ) -> Fleet:
        """Create a new fleet."""
        fleet = Fleet(
            name=name,
            agent_ids=agent_ids,
            squad_ids=squad_ids,
        )
        self._fleets[fleet.id] = fleet
        return fleet

    def get_fleet(self, fleet_id: str) -> Fleet | None:
        return self._fleets.get(fleet_id)

    def list_active(self) -> list[Fleet]:
        return [f for f in self._fleets.values() if f.status == FleetStatus.ACTIVE]

    def list_all(self) -> list[Fleet]:
        return list(self._fleets.values())

    def update_status(self, fleet_id: str, status: FleetStatus) -> Fleet | None:
        fleet = self._fleets.get(fleet_id)
        if fleet is None:
            return None
        updated = Fleet(
            id=fleet.id, name=fleet.name, status=status,
            agent_ids=fleet.agent_ids, squad_ids=fleet.squad_ids,
            tasks=fleet.tasks, batches=fleet.batches,
            metrics=fleet.metrics, created_at=fleet.created_at,
        )
        self._fleets[fleet_id] = updated
        return updated

    def dissolve(self, fleet_id: str) -> bool:
        """Dissolve a fleet and clean up its resources."""
        fleet = self._fleets.get(fleet_id)
        if fleet is None:
            return False
        self._fleets[fleet_id] = Fleet(
            id=fleet.id, name=fleet.name, status=FleetStatus.DISSOLVED,
            agent_ids=fleet.agent_ids, squad_ids=fleet.squad_ids,
            tasks=fleet.tasks, batches=fleet.batches,
            metrics=fleet.metrics, created_at=fleet.created_at,
        )
        return True

    # ── Fan-Out Pattern ───────────────────────────────────────────────────

    def fan_out(
        self,
        fleet_id: str,
        items: list[str],
        agent_ids: list[str] | None = None,
        batch_size: int | None = None,
    ) -> FanOutBatch:
        """Distribute N items across M agents in parallel (Plan 12 Part 3.1).

        Each item becomes a TaskItem assigned to an agent. Items are batched
        if there are more items than agents.

        Args:
            fleet_id: The fleet to dispatch through.
            items: Input items to distribute (e.g. file paths, chunks).
            agent_ids: Specific agents to use (defaults to fleet agents).
            batch_size: Max items per agent (auto-computed if None).

        Returns:
            FanOutBatch with all assigned tasks.
        """
        fleet = self._fleets.get(fleet_id)
        if fleet is None:
            return FanOutBatch()

        agents = agent_ids or list(fleet.agent_ids)
        if not agents:
            return FanOutBatch()

        if batch_size is None:
            batch_size = max(1, len(items) // len(agents))

        now = time.time()
        tasks: list[TaskItem] = []

        for i, item in enumerate(items):
            agent_idx = i % len(agents)
            task = TaskItem(
                input=item,
                status=TaskItemStatus.ASSIGNED,
                assigned_agent=agents[agent_idx],
                started_at=now,
            )
            tasks.append(task)

        batch = FanOutBatch(
            tasks=tuple(tasks),
            pattern=ExecutionPattern.FAN_OUT,
            agent_count=len(agents),
        )

        # Update fleet state
        self._fleets[fleet_id] = Fleet(
            id=fleet.id, name=fleet.name, status=FleetStatus.ACTIVE,
            agent_ids=fleet.agent_ids, squad_ids=fleet.squad_ids,
            tasks=fleet.tasks + tuple(tasks),
            batches=fleet.batches + (batch,),
            metrics=fleet.metrics,
            created_at=fleet.created_at,
        )

        return batch

    def complete_task(self, fleet_id: str, task_id: str, result: str, success: bool = True) -> TaskItem | None:
        """Record a task's completion."""
        fleet = self._fleets.get(fleet_id)
        if fleet is None:
            return None

        updated_tasks: list[TaskItem] = []
        completed_task: TaskItem | None = None

        for t in fleet.tasks:
            if t.id == task_id:
                status = TaskItemStatus.COMPLETED if success else TaskItemStatus.FAILED
                completed_task = TaskItem(
                    id=t.id, input=t.input, status=status,
                    result=result if success else "",
                    error="" if success else result,
                    assigned_agent=t.assigned_agent,
                    started_at=t.started_at,
                    completed_at=time.time(),
                )
                updated_tasks.append(completed_task)
            else:
                updated_tasks.append(t)

        if completed_task is None:
            return None

        self._task_results[task_id] = result

        # Recompute metrics
        metrics = self._compute_metrics(fleet, tuple(updated_tasks))

        self._fleets[fleet_id] = Fleet(
            id=fleet.id, name=fleet.name, status=fleet.status,
            agent_ids=fleet.agent_ids, squad_ids=fleet.squad_ids,
            tasks=tuple(updated_tasks),
            batches=fleet.batches,
            metrics=metrics,
            created_at=fleet.created_at,
        )

        return completed_task

    # ── Map-Reduce Pattern ────────────────────────────────────────────────

    def map_reduce(
        self,
        fleet_id: str,
        map_instruction: str,
        reduce_instruction: str,
        items: list[str],
        agent_ids: list[str] | None = None,
    ) -> MapReduceResult:
        """Execute map-reduce across a fleet (Plan 12 Part 3.2).

        MAP phase: Apply map_instruction to each item in parallel.
        REDUCE phase: Synthesize map results into a single output.

        This is a synchronous simulation — in production, async agents
        would execute tasks with real LLM calls.

        Args:
            fleet_id: The fleet to execute on.
            map_instruction: Instruction for the map phase (e.g. "analyze_file").
            reduce_instruction: Instruction for the reduce phase.
            items: Items to process in the map phase.
            agent_ids: Specific agents (defaults to fleet agents).

        Returns:
            MapReduceResult with map outputs and synthesis.
        """
        batch = self.fan_out(fleet_id, items, agent_ids)

        # MAP phase results
        map_results: list[str] = []
        for task in batch.tasks:
            result = f"[{task.assigned_agent}] {map_instruction}: {task.input}"
            self.complete_task(fleet_id, task.id, result)
            map_results.append(result)

        # REDUCE phase
        fleet = self._fleets.get(fleet_id)
        reduce_agent = "lead-synthesizer"
        if fleet and fleet.agent_ids:
            reduce_agent = fleet.agent_ids[0]

        synthesis = f"{reduce_instruction}:\n" + "\n".join(
            f"  - {r[:120]}" for r in map_results
        )

        total_tokens = sum(len(r) // 4 for r in map_results) + len(synthesis) // 4

        return MapReduceResult(
            map_results=tuple(map_results),
            synthesis=synthesis,
            map_agent_count=batch.agent_count,
            reduce_agent=reduce_agent,
            total_tokens=total_tokens,
        )

    # ── Metrics ───────────────────────────────────────────────────────────

    def get_metrics(self, fleet_id: str) -> FleetMetrics | None:
        """Get current fleet metrics."""
        fleet = self._fleets.get(fleet_id)
        if fleet is None:
            return None
        return fleet.metrics

    def refresh_metrics(self, fleet_id: str) -> FleetMetrics | None:
        """Recalculate and update fleet metrics."""
        fleet = self._fleets.get(fleet_id)
        if fleet is None:
            return None
        metrics = self._compute_metrics(fleet, fleet.tasks)
        self._fleets[fleet_id] = Fleet(
            id=fleet.id, name=fleet.name, status=fleet.status,
            agent_ids=fleet.agent_ids, squad_ids=fleet.squad_ids,
            tasks=fleet.tasks, batches=fleet.batches,
            metrics=metrics, created_at=fleet.created_at,
        )
        return metrics

    def _compute_metrics(self, fleet: Fleet, tasks: tuple[TaskItem, ...]) -> FleetMetrics:
        total = len(tasks)
        completed = sum(1 for t in tasks if t.status == TaskItemStatus.COMPLETED)
        failed = sum(1 for t in tasks if t.status == TaskItemStatus.FAILED)
        running = sum(1 for t in tasks if t.status == TaskItemStatus.RUNNING)
        queued = sum(1 for t in tasks if t.status in (TaskItemStatus.QUEUED, TaskItemStatus.ASSIGNED))

        active_agents = min(running, fleet.agent_count)
        idle_agents = max(0, fleet.agent_count - active_agents)

        elapsed = time.time() - fleet.created_at
        throughput = (completed / (elapsed / 60.0)) if elapsed > 0 else 0.0

        return FleetMetrics(
            total_tasks=total,
            completed_tasks=completed,
            failed_tasks=failed,
            running_tasks=running,
            queued_tasks=queued,
            total_agents=fleet.agent_count,
            active_agents=active_agents,
            idle_agents=idle_agents,
            total_tokens=sum(len(t.result) // 4 for t in tasks if t.result),
            total_cost_usd=round(completed * 0.05 + running * 0.02, 2),
            elapsed_seconds=elapsed,
            throughput_tasks_per_min=round(throughput, 2),
        )

    # ── Stats ─────────────────────────────────────────────────────────────

    def stats(self) -> dict:
        """Return aggregate fleet statistics."""
        fleets = list(self._fleets.values())
        return {
            "total_fleets": len(fleets),
            "active_fleets": sum(1 for f in fleets if f.status == FleetStatus.ACTIVE),
            "total_agents": sum(f.agent_count for f in fleets),
            "total_tasks": sum(f.task_count for f in fleets),
            "completed_tasks": sum(f.metrics.completed_tasks for f in fleets),
            "failed_tasks": sum(f.metrics.failed_tasks for f in fleets),
            "total_cost_usd": round(sum(f.metrics.total_cost_usd for f in fleets), 2),
        }


# ── Utility ────────────────────────────────────────────────────────────────


def chunk_items(items: list[str], chunk_size: int) -> list[list[str]]:
    """Split items into equal-sized chunks for batch dispatch."""
    it = iter(items)
    return [list(islice(it, chunk_size)) for _ in range(0, len(items), chunk_size)]


def estimate_fleet_cost(
    task_count: int,
    avg_tokens_per_task: int = 2000,
    cost_per_1k_tokens: float = 0.003,
) -> float:
    """Estimate the total cost for a fleet operation."""
    total_tokens = task_count * avg_tokens_per_task
    return round(total_tokens / 1000 * cost_per_1k_tokens, 2)
