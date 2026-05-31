"""Resumable Long Runs — Checkpoint-based pause/resume execution (P4-B6 HIGH×MED).

Checkpoint after each sub-task, skip-completed on resume, retry-failed on resume.
Implements the Claude Code checkpointing pattern for long-running workflows.

See: plan-phase4-swarm-investigations.md §4.14, Claude Code checkpointing
"""
from __future__ import annotations

import enum
import time
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class RunStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class CheckpointStrategy(str, enum.Enum):
    AFTER_EACH_SUBTASK = "after_each_subtask"
    AFTER_EACH_WAVE = "after_each_wave"
    MANUAL = "manual"


class ResumeAction(str, enum.Enum):
    SKIP = "skip"
    RETRY = "retry"
    EXECUTE = "execute"


# ---------------------------------------------------------------------------
# Core Types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RunCheckpoint:
    """A single checkpoint recording the state after a sub-task."""

    checkpoint_id: str
    subtask_id: str
    timestamp: float
    status: RunStatus
    output: str = ""
    error: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class CheckpointStore:
    """Stores checkpoints for a run. Supports query by subtask_id."""

    _checkpoints: dict[str, RunCheckpoint] = field(default_factory=dict)

    def save(self, checkpoint: RunCheckpoint) -> None:
        self._checkpoints[checkpoint.subtask_id] = checkpoint

    def get(self, subtask_id: str) -> RunCheckpoint | None:
        return self._checkpoints.get(subtask_id)

    def get_all(self) -> tuple[RunCheckpoint, ...]:
        return tuple(self._checkpoints.values())

    def subtask_ids(self) -> tuple[str, ...]:
        return tuple(self._checkpoints.keys())

    def completed_subtask_ids(self) -> tuple[str, ...]:
        return tuple(
            sid for sid, cp in self._checkpoints.items()
            if cp.status == RunStatus.COMPLETED
        )

    def failed_subtask_ids(self) -> tuple[str, ...]:
        return tuple(
            sid for sid, cp in self._checkpoints.items()
            if cp.status == RunStatus.FAILED
        )

    def clear(self) -> None:
        self._checkpoints.clear()

    @property
    def checkpoint_count(self) -> int:
        return len(self._checkpoints)


# ---------------------------------------------------------------------------
# Resume Planner
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResumePlan:
    """Plan for resuming a run: which tasks to skip, retry, or execute."""

    skip_ids: tuple[str, ...]
    retry_ids: tuple[str, ...]
    execute_ids: tuple[str, ...]

    @property
    def total_actions(self) -> int:
        return len(self.skip_ids) + len(self.retry_ids) + len(self.execute_ids)

    @property
    def has_work(self) -> bool:
        return len(self.retry_ids) + len(self.execute_ids) > 0


@dataclass
class ResumePlanner:
    """Plans which sub-tasks to skip, retry, or execute on resume."""

    strategy: CheckpointStrategy = CheckpointStrategy.AFTER_EACH_SUBTASK

    def plan(
        self,
        all_subtask_ids: tuple[str, ...],
        store: CheckpointStore,
    ) -> ResumePlan:
        """Build a resume plan given all expected subtask IDs and checkpoint store."""
        skip_ids: list[str] = []
        retry_ids: list[str] = []
        execute_ids: list[str] = []

        for sid in all_subtask_ids:
            cp = store.get(sid)
            if cp is None:
                execute_ids.append(sid)
            elif cp.status == RunStatus.COMPLETED:
                skip_ids.append(sid)
            elif cp.status == RunStatus.FAILED:
                retry_ids.append(sid)
            else:
                execute_ids.append(sid)

        return ResumePlan(
            skip_ids=tuple(skip_ids),
            retry_ids=tuple(retry_ids),
            execute_ids=tuple(execute_ids),
        )


# ---------------------------------------------------------------------------
# Resumable Run
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RunResult:
    """Result of a (possibly resumable) run."""

    run_id: str
    status: RunStatus
    checkpoints: tuple[RunCheckpoint, ...]
    total_subtasks: int
    completed_count: int
    failed_count: int
    skipped_count: int
    duration_ms: float

    @property
    def success_rate(self) -> float:
        attempted = self.completed_count + self.failed_count
        if attempted == 0:
            return 1.0
        return self.completed_count / attempted


@dataclass
class ResumableRun:
    """Orchestrates a run with checkpoint-based pause/resume.

    Usage::

        run = ResumableRun(run_id="deep-research-001")
        # First run
        result = run.execute(["task-1", "task-2"], runner_fn)
        # Resume
        result = run.execute(["task-1", "task-2", "task-3"], runner_fn, resume=True)
    """

    run_id: str
    strategy: CheckpointStrategy = CheckpointStrategy.AFTER_EACH_SUBTASK
    _store: CheckpointStore = field(default_factory=CheckpointStore)
    _start_time: float = 0.0

    def execute(
        self,
        subtask_ids: tuple[str, ...],
        runner,
        *,
        resume: bool = False,
    ) -> RunResult:
        """Execute (or resume) all subtasks.

        runner: callable(subtask_id) -> str that executes a single subtask.
        resume: if True, skip completed and retry failed subtasks.
        """
        self._start_time = time.time()

        if resume:
            planner = ResumePlanner(strategy=self.strategy)
            plan = planner.plan(subtask_ids, self._store)
        else:
            plan = ResumePlan(
                skip_ids=(),
                retry_ids=(),
                execute_ids=subtask_ids,
            )

        completed = 0
        failed = 0
        skipped = 0

        # Count skipped tasks (already completed in store)
        for sid in plan.skip_ids:
            cp = self._store.get(sid)
            if cp and cp.status == RunStatus.COMPLETED:
                skipped += 1

        # Execute new tasks
        for sid in plan.execute_ids:
            try:
                output = runner(sid)
                self._store.save(RunCheckpoint(
                    checkpoint_id=f"{self.run_id}-{sid}",
                    subtask_id=sid,
                    timestamp=time.time(),
                    status=RunStatus.COMPLETED,
                    output=str(output),
                ))
                completed += 1
            except Exception as e:
                self._store.save(RunCheckpoint(
                    checkpoint_id=f"{self.run_id}-{sid}",
                    subtask_id=sid,
                    timestamp=time.time(),
                    status=RunStatus.FAILED,
                    error=str(e),
                ))
                failed += 1

        # Retry failed tasks
        for sid in plan.retry_ids:
            try:
                output = runner(sid)
                self._store.save(RunCheckpoint(
                    checkpoint_id=f"{self.run_id}-{sid}",
                    subtask_id=sid,
                    timestamp=time.time(),
                    status=RunStatus.COMPLETED,
                    output=str(output),
                ))
                completed += 1
            except Exception as e:
                self._store.save(RunCheckpoint(
                    checkpoint_id=f"{self.run_id}-{sid}",
                    subtask_id=sid,
                    timestamp=time.time(),
                    status=RunStatus.FAILED,
                    error=str(e),
                ))
                failed += 1

        # Determine overall status
        if failed == 0 and completed + skipped == len(subtask_ids):
            status = RunStatus.COMPLETED
        elif completed > 0 or skipped > 0:
            status = RunStatus.PAUSED
        else:
            status = RunStatus.FAILED

        return RunResult(
            run_id=self.run_id,
            status=status,
            checkpoints=self._store.get_all(),
            total_subtasks=len(subtask_ids),
            completed_count=completed,
            failed_count=failed,
            skipped_count=skipped,
            duration_ms=(time.time() - self._start_time) * 1000,
        )

    def reset(self) -> None:
        self._store.clear()

    @property
    def checkpoint_count(self) -> int:
        return self._store.checkpoint_count


__all__ = [
    "CheckpointStore",
    "CheckpointStrategy",
    "ResumeAction",
    "ResumePlan",
    "ResumePlanner",
    "ResumableRun",
    "RunCheckpoint",
    "RunResult",
    "RunStatus",
]
