"""Tool Orchestrator — parallel and conditional tool execution."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum


class ExecutionMode(StrEnum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"


@dataclass(frozen=True)
class ToolTask:
    task_id: str
    name: str
    fn: Callable[[], str]
    depends_on: tuple[str, ...] = ()
    condition: str = ""  # "if_prev_success", "if_prev_failed", "always"
    timeout_seconds: float = 30.0


@dataclass(frozen=True)
class TaskResult:
    task_id: str
    name: str
    output: str
    error: str = ""
    success: bool = True
    duration_ms: float = 0.0
    skipped: bool = False


@dataclass(frozen=True)
class OrchestrationResult:
    tasks: tuple[TaskResult, ...]
    success_count: int
    failure_count: int
    skipped_count: int
    total_duration_ms: float


class ToolOrchestrator:
    """Orchestrates tool execution with dependency resolution and parallelism.

    Usage::

        orch = ToolOrchestrator(max_parallel=4)
        orch.add_task(ToolTask("t1", "lint", lambda: run_lint()))
        orch.add_task(ToolTask("t2", "test", lambda: run_tests(), depends_on=("t1",)))
        result = orch.execute()
    """

    def __init__(self, max_parallel: int = 4) -> None:
        self._tasks: dict[str, ToolTask] = {}
        self._max_parallel = max_parallel

    @property
    def task_count(self) -> int:
        return len(self._tasks)

    def add_task(self, task: ToolTask) -> None:
        self._tasks[task.task_id] = task

    def remove_task(self, task_id: str) -> None:
        self._tasks.pop(task_id, None)

    def execute(self) -> OrchestrationResult:
        from concurrent.futures import ThreadPoolExecutor, as_completed

        started = time.monotonic()
        completed: dict[str, TaskResult] = {}
        pending = set(self._tasks.keys())

        while pending:
            ready = [
                tid for tid in pending
                if all(
                    dep in completed and completed[dep].success
                    for dep in self._tasks[tid].depends_on
                )
            ]

            if not ready:
                break

            batch = ready[: self._max_parallel]
            pending -= set(batch)

            with ThreadPoolExecutor(max_workers=len(batch)) as executor:
                futures = {}
                for tid in batch:
                    task = self._tasks[tid]
                    prev_success = all(
                        completed[dep].success
                        for dep in task.depends_on
                        if dep in completed
                    ) if task.depends_on else True

                    if task.condition == "if_prev_success" and not prev_success:
                        completed[tid] = TaskResult(
                            task_id=tid, name=task.name, output="",
                            success=False, skipped=True,
                        )
                        continue

                    futures[executor.submit(task.fn)] = tid

                for future in as_completed(futures):
                    tid = futures[future]
                    task = self._tasks[tid]
                    task_start = time.monotonic()
                    try:
                        output = future.result(timeout=task.timeout_seconds)
                        completed[tid] = TaskResult(
                            task_id=tid, name=task.name, output=output,
                            success=True,
                            duration_ms=(time.monotonic() - task_start) * 1000,
                        )
                    except Exception as exc:
                        completed[tid] = TaskResult(
                            task_id=tid, name=task.name, output="",
                            error=str(exc), success=False,
                            duration_ms=(time.monotonic() - task_start) * 1000,
                        )

        total_duration = (time.monotonic() - started) * 1000
        results = tuple(completed.get(tid) or TaskResult(
            task_id=tid, name=self._tasks.get(tid, ToolTask(tid, tid, lambda: "")).name,
            output="", success=False, skipped=True,
        ) for tid in self._tasks)

        return OrchestrationResult(
            tasks=results,
            success_count=sum(1 for r in results if r.success),
            failure_count=sum(1 for r in results if not r.success and not r.skipped),
            skipped_count=sum(1 for r in results if r.skipped),
            total_duration_ms=total_duration,
        )

    def clear(self) -> None:
        self._tasks.clear()
