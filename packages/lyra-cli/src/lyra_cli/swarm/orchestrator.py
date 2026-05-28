"""
Swarm Orchestrator for task decomposition and parallel work distribution.

Implements:
- Priority-based task queues
- Task decomposition into sub-tasks
- Work distribution across agent fleet
- Result aggregation and merging
"""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any
from uuid import uuid4


class PriorityLevel(Enum):
    """Priority levels for swarm tasks."""

    CRITICAL = auto()
    HIGH = auto()
    MEDIUM = auto()
    LOW = auto()
    BACKGROUND = auto()


@dataclass
class OrchestratorConfig:
    """Configuration for the swarm orchestrator."""

    max_concurrent_tasks: int = 10
    task_timeout_seconds: float = 300.0
    result_aggregation_timeout: float = 60.0
    max_retries_per_task: int = 3
    enable_task_decomposition: bool = True
    heartbeat_interval: float = 5.0


@dataclass
class SwarmTask:
    """A unit of work within the swarm."""

    task_id: str = field(default_factory=lambda: f"task_{uuid4().hex[:8]}")
    parent_id: str | None = None
    description: str = ""
    priority: PriorityLevel = PriorityLevel.MEDIUM
    dependencies: list[str] = field(default_factory=list)
    subtasks: list[str] = field(default_factory=list)
    status: str = "created"  # created, queued, running, completed, failed, cancelled
    assigned_agent: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    result: Any | None = None
    error: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: str | None = None
    completed_at: str | None = None
    retry_count: int = 0
    execution_func: Callable[[], Any] | None = None


@dataclass
class TaskResult:
    """Result of a completed swarm task."""

    task_id: str
    success: bool
    result: Any | None = None
    error: str | None = None
    duration_seconds: float = 0.0
    subtask_results: dict[str, Any] = field(default_factory=dict)


class SwarmOrchestrator:
    """
    Orchestrates task decomposition and parallel execution across the swarm.

    Features:
    - Priority-based task queues for differentiated service
    - Task decomposition into parallel sub-tasks
    - Work distribution to available agents
    - Result aggregation with configurable merging strategy
    - Automatic retry on failure
    """

    def __init__(self, config: OrchestratorConfig | None = None) -> None:
        self.config = config or OrchestratorConfig()
        self.tasks: dict[str, SwarmTask] = {}
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._lock: asyncio.Lock = asyncio.Lock()
        self._running: bool = False
        self._workers: list[asyncio.Task] = []
        self._stats: dict[str, int] = {
            "tasks_created": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "tasks_decomposed": 0,
        }

    async def submit_task(self, task: SwarmTask) -> str:
        """
        Submit a task to the orchestrator for execution.

        Args:
            task: The task to submit

        Returns:
            The task ID
        """
        async with self._lock:
            task.status = "queued"
            self.tasks[task.task_id] = task
            self._stats["tasks_created"] += 1
            priority_value = self._priority_to_int(task.priority)
            await self._queue.put((priority_value, task.task_id))
        return task.task_id

    async def submit_and_wait(self, task: SwarmTask) -> TaskResult:
        """
        Submit a task and wait for its result.

        Args:
            task: The task to submit

        Returns:
            TaskResult with the outcome
        """
        task_id = await self.submit_task(task)
        return await self.await_result(task_id)

    async def await_result(self, task_id: str) -> TaskResult:
        """
        Wait for a specific task to complete and return its result.

        Args:
            task_id: The task to wait for

        Returns:
            TaskResult
        """
        start = datetime.now()
        while True:
            async with self._lock:
                task = self.tasks.get(task_id)
                if task is None:
                    return TaskResult(
                        task_id=task_id,
                        success=False,
                        error=f"Task {task_id} not found",
                    )
                if task.status in ("completed", "failed", "cancelled"):
                    duration = (datetime.now() - datetime.fromisoformat(task.created_at)).total_seconds()
                    return TaskResult(
                        task_id=task_id,
                        success=task.status == "completed",
                        result=task.result,
                        error=task.error,
                        duration_seconds=duration,
                    )
            elapsed = (datetime.now() - start).total_seconds()
            if elapsed > self.config.task_timeout_seconds:
                return TaskResult(
                    task_id=task_id,
                    success=False,
                    error=f"Timeout waiting for task {task_id}",
                )
            await asyncio.sleep(0.1)

    async def decompose_task(
        self,
        task: SwarmTask,
        sub_descriptions: list[str],
    ) -> list[str]:
        """
        Decompose a task into parallel sub-tasks.

        Args:
            task: The parent task to decompose
            sub_descriptions: List of descriptions for sub-tasks

        Returns:
            List of sub-task IDs
        """
        sub_ids: list[str] = []
        async with self._lock:
            self._stats["tasks_decomposed"] += 1
            for desc in sub_descriptions:
                sub_task = SwarmTask(
                    parent_id=task.task_id,
                    description=desc,
                    priority=task.priority,
                    payload=task.payload.copy(),
                )
                self.tasks[sub_task.task_id] = sub_task
                sub_ids.append(sub_task.task_id)
                task.subtasks.append(sub_task.task_id)
                priority_value = self._priority_to_int(sub_task.priority)
                await self._queue.put((priority_value, sub_task.task_id))
                self._stats["tasks_created"] += 1
        return sub_ids

    async def aggregate_results(
        self,
        task_id: str,
        merge_func: Callable[[list[TaskResult]], Any] | None = None,
    ) -> Any | None:
        """
        Aggregate results from all completed sub-tasks.

        Args:
            task_id: The parent task ID
            merge_func: Optional custom merge function

        Returns:
            Merged result, or None on failure
        """
        async with self._lock:
            task = self.tasks.get(task_id)
            if task is None:
                return None
            sub_ids = list(task.subtasks)

        sub_results: list[TaskResult] = []
        for sub_id in sub_ids:
            result = await self.await_result(sub_id)
            sub_results.append(result)

        if merge_func is not None:
            return merge_func(sub_results)

        successes = [r for r in sub_results if r.success]
        failures = [r for r in sub_results if not r.success]

        return {
            "total": len(sub_results),
            "successful": len(successes),
            "failed": len(failures),
            "results": [r.result for r in successes],
            "errors": [r.error for r in failures],
        }

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending or running task."""
        async with self._lock:
            task = self.tasks.get(task_id)
            if task is None or task.status in ("completed", "failed", "cancelled"):
                return False
            task.status = "cancelled"
            for sub_id in task.subtasks:
                sub = self.tasks.get(sub_id)
                if sub and sub.status not in ("completed", "failed", "cancelled"):
                    sub.status = "cancelled"
            return True

    async def start(self) -> None:
        """Start the orchestrator worker pool."""
        self._running = True
        for _ in range(self.config.max_concurrent_tasks):
            worker = asyncio.create_task(self._worker_loop())
            self._workers.append(worker)

    async def stop(self) -> None:
        """Stop the orchestrator worker pool."""
        self._running = False
        for worker in self._workers:
            worker.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()

    async def _worker_loop(self) -> None:
        """Main worker loop that processes tasks from the queue."""
        while self._running:
            try:
                _, task_id = await self._queue.get()
                await self._process_task(task_id)
                self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception:
                async with self._lock:
                    self._stats["tasks_failed"] += 1

    async def _process_task(self, task_id: str) -> None:
        """Process a single task with retry logic."""
        task = self.tasks.get(task_id)
        if task is None:
            return

        async with self._lock:
            task.status = "running"
            task.started_at = datetime.now().isoformat()

        for attempt in range(self.config.max_retries_per_task + 1):
            try:
                if task.execution_func is not None:
                    if inspect.iscoroutinefunction(task.execution_func):
                        result = await task.execution_func()
                    else:
                        result = task.execution_func()
                else:
                    result = f"Task {task_id} executed: {task.description}"

                async with self._lock:
                    task.result = result
                    task.status = "completed"
                    task.completed_at = datetime.now().isoformat()
                    self._stats["tasks_completed"] += 1
                return

            except Exception as exc:
                task.retry_count = attempt + 1
                if attempt < self.config.max_retries_per_task:
                    await asyncio.sleep(0.5 * (attempt + 1))
                else:
                    async with self._lock:
                        task.status = "failed"
                        task.error = str(exc)
                        task.completed_at = datetime.now().isoformat()
                        self._stats["tasks_failed"] += 1

    def _priority_to_int(self, priority: PriorityLevel) -> int:
        """Convert priority enum to integer for queue ordering (lower = higher priority)."""
        mapping: dict[PriorityLevel, int] = {
            PriorityLevel.CRITICAL: 0,
            PriorityLevel.HIGH: 1,
            PriorityLevel.MEDIUM: 2,
            PriorityLevel.LOW: 3,
            PriorityLevel.BACKGROUND: 4,
        }
        return mapping.get(priority, 2)

    def get_task(self, task_id: str) -> SwarmTask | None:
        """Get a task by ID."""
        return self.tasks.get(task_id)

    def get_stats(self) -> dict[str, int]:
        """Get orchestrator statistics."""
        return dict(self._stats)

    @property
    def queue_size(self) -> int:
        """Get the current queue size."""
        return self._queue.qsize()

    @property
    def is_running(self) -> bool:
        """Check if the orchestrator is running."""
        return self._running
