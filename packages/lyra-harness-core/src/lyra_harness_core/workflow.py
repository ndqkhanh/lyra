"""Workflow.js Spec — Code-driven fan-out orchestration (P4-B1 CRITICAL).

Task decomposition into parallel sub-tasks with DAG-based dependency resolution.
No central orchestrator round-trip: intermediate results flow directly between agents
via pub/sub channels. Supports fan-out to parallel agent squads, adversarial verification
integration, and resumable checkpointing.

See: plan-phase4-swarm-investigations.md §4.13, Claude Code Dynamic Workflows
"""
from __future__ import annotations

import enum
import time
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SubTaskStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class IsolationMode(str, enum.Enum):
    WORKTREE = "worktree"
    PROCESS = "process"
    NONE = "none"


class ResumeStrategy(str, enum.Enum):
    SKIP_COMPLETED = "skip_completed"
    RETRY_FAILED = "retry_failed"
    RESTART_ALL = "restart_all"


class WorkflowStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Core Types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SubTask:
    """A single sub-task within a workflow DAG."""

    id: str
    agent_type: str
    query: str = ""
    repo: str = ""
    system: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class DecompositionResult:
    """Result of task decomposition — sub_tasks + dependency graph."""

    sub_tasks: tuple[SubTask, ...]
    dependencies: dict[str, tuple[str, ...]] = field(default_factory=dict)
    description: str = ""

    @property
    def subtask_count(self) -> int:
        return len(self.sub_tasks)


@dataclass(frozen=True)
class FanOutConfig:
    """Configuration for parallel fan-out execution."""

    max_concurrency: int = 12
    agent_types: tuple[str, ...] = ("research", "code", "architect", "security", "performance")
    isolation: IsolationMode = IsolationMode.WORKTREE


@dataclass(frozen=True)
class VerifyConfig:
    """Adversarial verification configuration per sub-task output."""

    attack_agents: int = 2
    convergence_threshold: float = 0.9
    max_rounds: int = 3
    enabled: bool = True


@dataclass(frozen=True)
class CheckpointConfig:
    """Checkpoint configuration for resumable execution."""

    after_each: str = "sub_task"
    retention: str = "30d"
    resume_strategy: ResumeStrategy = ResumeStrategy.SKIP_COMPLETED


@dataclass(frozen=True)
class WorkflowSpec:
    """Complete workflow specification (workflow.js equivalent)."""

    name: str
    description: str = ""
    decompose_config: DecompositionResult | None = None
    fan_out: FanOutConfig = field(default_factory=FanOutConfig)
    verify: VerifyConfig = field(default_factory=VerifyConfig)
    checkpoint: CheckpointConfig = field(default_factory=CheckpointConfig)

    def with_decomposition(self, result: DecompositionResult) -> WorkflowSpec:
        return WorkflowSpec(
            name=self.name,
            description=self.description,
            decompose_config=result,
            fan_out=self.fan_out,
            verify=self.verify,
            checkpoint=self.checkpoint,
        )


# ---------------------------------------------------------------------------
# SubTask Result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SubTaskResult:
    """Result of executing a single sub-task."""

    subtask_id: str
    status: SubTaskStatus
    output: str = ""
    agent_id: str = ""
    duration_ms: float = 0.0
    error: str = ""
    verified: bool = False
    verification_score: float = 0.0


# ---------------------------------------------------------------------------
# Workflow DAG
# ---------------------------------------------------------------------------


@dataclass
class WorkflowDAG:
    """DAG builder and validator for sub-task dependencies.

    Supports topological ordering, cycle detection, and parallel-ready
    wave detection (groups of tasks that can run concurrently).
    """

    _tasks: dict[str, SubTask] = field(default_factory=dict)
    _dependencies: dict[str, set[str]] = field(default_factory=dict)
    _dependents: dict[str, set[str]] = field(default_factory=dict)

    def add_task(self, task: SubTask) -> None:
        self._tasks[task.id] = task
        if task.id not in self._dependencies:
            self._dependencies[task.id] = set()
        if task.id not in self._dependents:
            self._dependents[task.id] = set()

    def add_dependency(self, task_id: str, depends_on: str) -> None:
        if task_id not in self._dependencies:
            self._dependencies[task_id] = set()
        self._dependencies[task_id].add(depends_on)
        if depends_on not in self._dependents:
            self._dependents[depends_on] = set()
        self._dependents[depends_on].add(task_id)

    def has_cycles(self) -> bool:
        """Detect cycles using DFS with recursion stack."""
        visited: set[str] = set()
        rec_stack: set[str] = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            for dep in self._dependencies.get(node, set()):
                if dep not in visited:
                    if dfs(dep):
                        return True
                elif dep in rec_stack:
                    return True
            rec_stack.discard(node)
            return False

        for task_id in self._tasks:
            if task_id not in visited:
                if dfs(task_id):
                    return True
        return False

    def topological_order(self) -> tuple[tuple[str, ...], ...]:
        """Return waves of tasks that can run in parallel (Kahn's algorithm).

        Each inner tuple is a wave — tasks that can run concurrently.
        """
        in_degree: dict[str, int] = {t: len(self._dependencies.get(t, set())) for t in self._tasks}
        waves: list[tuple[str, ...]] = []
        remaining = set(self._tasks.keys())

        while remaining:
            ready = {t for t in remaining if in_degree[t] == 0}
            if not ready:
                break
            waves.append(tuple(sorted(ready)))
            for task_id in ready:
                remaining.discard(task_id)
                for dependent in self._dependents.get(task_id, set()):
                    if dependent in in_degree:
                        in_degree[dependent] -= 1

        return tuple(waves)

    def ready_tasks(self, completed: set[str]) -> tuple[str, ...]:
        """Tasks whose dependencies are all satisfied given the completed set."""
        ready: list[str] = []
        for task_id in self._tasks:
            if task_id in completed:
                continue
            deps = self._dependencies.get(task_id, set())
            if deps <= completed:
                ready.append(task_id)
        return tuple(ready)

    @classmethod
    def from_decomposition(cls, result: DecompositionResult) -> WorkflowDAG:
        """Build a DAG from a DecompositionResult."""
        dag = cls()
        for task in result.sub_tasks:
            dag.add_task(task)
        for task_id, deps in result.dependencies.items():
            for dep in deps:
                dag.add_dependency(task_id, dep)
        return dag

    @property
    def task_count(self) -> int:
        return len(self._tasks)

    @property
    def edge_count(self) -> int:
        return sum(len(deps) for deps in self._dependencies.values())


# ---------------------------------------------------------------------------
# Workflow Result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WorkflowResult:
    """Result of executing a complete workflow."""

    workflow_name: str
    status: WorkflowStatus
    subtask_results: tuple[SubTaskResult, ...]
    total_subtasks: int
    completed_count: int
    failed_count: int
    duration_ms: float
    verification_summary: str = ""

    @property
    def success_rate(self) -> float:
        if self.total_subtasks == 0:
            return 1.0
        return self.completed_count / self.total_subtasks

    @property
    def subtask_ids(self) -> tuple[str, ...]:
        return tuple(r.subtask_id for r in self.subtask_results)


# ---------------------------------------------------------------------------
# Workflow Engine
# ---------------------------------------------------------------------------


@dataclass
class WorkflowEngine:
    """Orchestrates workflow execution: decompose → DAG → fan-out → collect → verify.

    Usage::

        spec = WorkflowSpec(name="deep-research")
        engine = WorkflowEngine(max_concurrency=8)
        result = engine.execute(spec, initial_context={"topic": "RLHF"})
    """

    max_concurrency: int = 12
    _results: dict[str, SubTaskResult] = field(default_factory=dict)

    def execute(
        self,
        spec: WorkflowSpec,
        initial_context: dict | None = None,
        *,
        agent_runner=None,
    ) -> WorkflowResult:
        """Execute a workflow specification.

        agent_runner: optional callable(subtask, context) -> str that runs a single
        sub-task. If not provided, sub-tasks are recorded as pending (dry-run mode).
        """
        self._results = {}
        start_time = time.time()
        context = dict(initial_context or {})

        # 1. Decompose
        if spec.decompose_config is None:
            return WorkflowResult(
                workflow_name=spec.name,
                status=WorkflowStatus.FAILED,
                subtask_results=(),
                total_subtasks=0,
                completed_count=0,
                failed_count=0,
                duration_ms=(time.time() - start_time) * 1000,
                verification_summary="No decomposition config provided",
            )

        decomposition = spec.decompose_config

        # 2. Build DAG
        dag = WorkflowDAG.from_decomposition(decomposition)
        if dag.has_cycles():
            return WorkflowResult(
                workflow_name=spec.name,
                status=WorkflowStatus.FAILED,
                subtask_results=(),
                total_subtasks=decomposition.subtask_count,
                completed_count=0,
                failed_count=0,
                duration_ms=(time.time() - start_time) * 1000,
                verification_summary="Cycle detected in task dependencies",
            )

        # 3. Fan-out: execute in topological waves
        completed: set[str] = set()
        failed: set[str] = set()
        running: set[str] = set()

        waves = dag.topological_order()
        for wave in waves:

            # Execute all tasks in this wave (respect max_concurrency)
            for i in range(0, len(wave), self.max_concurrency):
                batch = wave[i : i + self.max_concurrency]

                for task_id in batch:
                    task = dag._tasks.get(task_id)
                    if task is None:
                        continue

                    t0 = time.time()
                    running.add(task_id)

                    if agent_runner is None:
                        result = SubTaskResult(
                            subtask_id=task_id,
                            status=SubTaskStatus.PENDING,
                            agent_id=task.agent_type,
                        )
                    else:
                        try:
                            output = agent_runner(task, context)
                            result = SubTaskResult(
                                subtask_id=task_id,
                                status=SubTaskStatus.COMPLETED,
                                output=str(output),
                                agent_id=task.agent_type,
                                duration_ms=(time.time() - t0) * 1000,
                            )
                            completed.add(task_id)
                        except Exception as e:
                            result = SubTaskResult(
                                subtask_id=task_id,
                                status=SubTaskStatus.FAILED,
                                error=str(e),
                                duration_ms=(time.time() - t0) * 1000,
                            )
                            failed.add(task_id)

                    self._results[task_id] = result
                    context[task_id] = result.output if result.status == SubTaskStatus.COMPLETED else result.error
                    running.discard(task_id)

        # 4. Determine overall status
        total = decomposition.subtask_count
        if len(completed) == total:
            status = WorkflowStatus.COMPLETED
        elif len(failed) == total:
            status = WorkflowStatus.FAILED
        elif len(completed) > 0:
            status = WorkflowStatus.PARTIAL
        else:
            status = WorkflowStatus.PENDING

        return WorkflowResult(
            workflow_name=spec.name,
            status=status,
            subtask_results=tuple(self._results.values()),
            total_subtasks=total,
            completed_count=len(completed),
            failed_count=len(failed),
            duration_ms=(time.time() - start_time) * 1000,
        )

    @property
    def results(self) -> dict[str, SubTaskResult]:
        return dict(self._results)

    def reset(self) -> None:
        self._results.clear()


__all__ = [
    "CheckpointConfig",
    "DecompositionResult",
    "FanOutConfig",
    "IsolationMode",
    "ResumeStrategy",
    "SubTask",
    "SubTaskResult",
    "SubTaskStatus",
    "VerifyConfig",
    "WorkflowDAG",
    "WorkflowEngine",
    "WorkflowResult",
    "WorkflowSpec",
    "WorkflowStatus",
]
