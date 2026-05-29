"""
Task Queue System - Distributed task queue for work distribution.

Features:
- Priority-based task scheduling
- Task assignment to available agents
- Task retry and failure handling
- Dead letter queue for failed tasks
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4


class TaskPriority(Enum):
    """Task priority levels."""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class TaskStatus(Enum):
    """Task status."""

    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass(frozen=True)
class Task:
    """Task definition."""

    task_id: str
    queue_name: str
    payload: dict[str, Any]
    priority: TaskPriority = TaskPriority.NORMAL
    max_retries: int = 3
    timeout: int = 300  # Seconds
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class TaskState:
    """Mutable task state."""

    task: Task
    status: TaskStatus = TaskStatus.PENDING
    assigned_to: str | None = None
    assigned_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    retry_count: int = 0


@dataclass
class Worker:
    """Worker registration."""

    worker_id: str
    capabilities: set[str]
    max_concurrent: int = 5
    active_tasks: set[str] = field(default_factory=set)
    last_heartbeat: datetime = field(default_factory=datetime.now)


class TaskQueue:
    """
    Distributed task queue for work distribution.

    Features:
    - Priority-based scheduling
    - Worker assignment
    - Retry logic
    - Dead letter queue
    - Task timeout handling
    """

    def __init__(self):
        """Initialize task queue."""
        self._queues: dict[str, list[str]] = {}  # queue_name -> [task_ids]
        self._tasks: dict[str, TaskState] = {}  # task_id -> TaskState
        self._workers: dict[str, Worker] = {}  # worker_id -> Worker
        self._dead_letter: list[str] = []  # Failed task IDs
        self._completion_events: dict[str, asyncio.Event] = {}

    async def enqueue(
        self,
        queue_name: str,
        payload: dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
        max_retries: int = 3,
        timeout: int = 300,
    ) -> str:
        """
        Enqueue a new task.

        Args:
            queue_name: Queue name
            payload: Task payload
            priority: Task priority
            max_retries: Maximum retry attempts
            timeout: Task timeout in seconds

        Returns:
            Task ID
        """
        task_id = str(uuid4())

        task = Task(
            task_id=task_id,
            queue_name=queue_name,
            payload=payload,
            priority=priority,
            max_retries=max_retries,
            timeout=timeout,
        )

        state = TaskState(task=task)
        self._tasks[task_id] = state
        self._completion_events[task_id] = asyncio.Event()

        # Add to queue
        if queue_name not in self._queues:
            self._queues[queue_name] = []
        self._queues[queue_name].append(task_id)

        # Sort by priority
        self._sort_queue(queue_name)

        # Trigger assignment
        asyncio.create_task(self._try_assign_tasks(queue_name))

        return task_id

    async def register_worker(
        self,
        worker_id: str,
        capabilities: set[str],
        max_concurrent: int = 5,
    ) -> bool:
        """
        Register a worker.

        Args:
            worker_id: Worker ID
            capabilities: Set of queue names worker can handle
            max_concurrent: Maximum concurrent tasks

        Returns:
            True if registered successfully
        """
        if worker_id in self._workers:
            return False

        worker = Worker(
            worker_id=worker_id,
            capabilities=capabilities,
            max_concurrent=max_concurrent,
        )

        self._workers[worker_id] = worker

        # Try to assign tasks
        for queue_name in capabilities:
            asyncio.create_task(self._try_assign_tasks(queue_name))

        return True

    async def unregister_worker(self, worker_id: str) -> bool:
        """
        Unregister a worker.

        Args:
            worker_id: Worker ID

        Returns:
            True if unregistered successfully
        """
        if worker_id not in self._workers:
            return False

        worker = self._workers[worker_id]

        # Reassign active tasks
        for task_id in worker.active_tasks.copy():
            await self._reassign_task(task_id)

        del self._workers[worker_id]
        return True

    async def heartbeat(self, worker_id: str) -> bool:
        """
        Update worker heartbeat.

        Args:
            worker_id: Worker ID

        Returns:
            True if heartbeat recorded
        """
        if worker_id not in self._workers:
            return False

        self._workers[worker_id].last_heartbeat = datetime.now()
        return True

    async def complete_task(
        self,
        task_id: str,
        worker_id: str,
        result: dict[str, Any],
    ) -> bool:
        """
        Mark task as completed.

        Args:
            task_id: Task ID
            worker_id: Worker ID
            result: Task result

        Returns:
            True if completed successfully
        """
        if task_id not in self._tasks:
            return False

        state = self._tasks[task_id]

        # Verify assignment
        if state.assigned_to != worker_id:
            return False

        # Update state
        state.status = TaskStatus.COMPLETED
        state.completed_at = datetime.now()
        state.result = result

        # Remove from worker
        if worker_id in self._workers:
            self._workers[worker_id].active_tasks.discard(task_id)
            # Try to assign more tasks to this worker
            for queue_name in self._workers[worker_id].capabilities:
                asyncio.create_task(self._try_assign_tasks(queue_name))

        # Signal completion
        if task_id in self._completion_events:
            self._completion_events[task_id].set()

        return True

    async def fail_task(
        self,
        task_id: str,
        worker_id: str,
        error: str,
    ) -> bool:
        """
        Mark task as failed.

        Args:
            task_id: Task ID
            worker_id: Worker ID
            error: Error message

        Returns:
            True if failed successfully
        """
        if task_id not in self._tasks:
            return False

        state = self._tasks[task_id]

        # Verify assignment
        if state.assigned_to != worker_id:
            return False

        # Update state
        state.error = error
        state.retry_count += 1

        # Remove from worker
        if worker_id in self._workers:
            self._workers[worker_id].active_tasks.discard(task_id)

        # Check retry
        if state.retry_count < state.task.max_retries:
            # Retry
            state.status = TaskStatus.RETRYING
            state.assigned_to = None
            state.assigned_at = None

            # Re-enqueue
            queue_name = state.task.queue_name
            if queue_name in self._queues:
                self._queues[queue_name].append(task_id)
                self._sort_queue(queue_name)
                asyncio.create_task(self._try_assign_tasks(queue_name))
        else:
            # Move to dead letter queue
            state.status = TaskStatus.FAILED
            self._dead_letter.append(task_id)

            # Signal completion (with failure)
            if task_id in self._completion_events:
                self._completion_events[task_id].set()

        return True

    async def wait_for_completion(
        self,
        task_id: str,
        timeout: int | None = None,
    ) -> dict[str, Any] | None:
        """
        Wait for task completion.

        Args:
            task_id: Task ID
            timeout: Optional timeout in seconds

        Returns:
            Task result or None if timeout/failed
        """
        if task_id not in self._tasks:
            return None

        event = self._completion_events[task_id]

        try:
            if timeout:
                await asyncio.wait_for(event.wait(), timeout=timeout)
            else:
                await event.wait()

            state = self._tasks[task_id]
            if state.status == TaskStatus.COMPLETED:
                return state.result
            return None
        except TimeoutError:
            return None

    async def _try_assign_tasks(self, queue_name: str):
        """
        Try to assign tasks from queue to available workers.

        Args:
            queue_name: Queue name
        """
        if queue_name not in self._queues:
            return

        queue = self._queues[queue_name]

        # Find available workers
        available_workers = [
            w
            for w in self._workers.values()
            if queue_name in w.capabilities and len(w.active_tasks) < w.max_concurrent
        ]

        if not available_workers:
            return

        # Assign tasks
        for task_id in queue.copy():
            if task_id not in self._tasks:
                queue.remove(task_id)
                continue

            state = self._tasks[task_id]

            if state.status not in (TaskStatus.PENDING, TaskStatus.RETRYING):
                queue.remove(task_id)
                continue

            # Find worker with least load
            worker = min(available_workers, key=lambda w: len(w.active_tasks))

            if len(worker.active_tasks) >= worker.max_concurrent:
                break

            # Assign task
            state.status = TaskStatus.ASSIGNED
            state.assigned_to = worker.worker_id
            state.assigned_at = datetime.now()
            worker.active_tasks.add(task_id)

            # Remove from queue
            queue.remove(task_id)

            # Start timeout task
            asyncio.create_task(self._handle_timeout(task_id))

    async def _reassign_task(self, task_id: str):
        """
        Reassign task to another worker.

        Args:
            task_id: Task ID
        """
        if task_id not in self._tasks:
            return

        state = self._tasks[task_id]

        # Reset assignment
        state.status = TaskStatus.PENDING
        state.assigned_to = None
        state.assigned_at = None

        # Re-enqueue
        queue_name = state.task.queue_name
        if queue_name not in self._queues:
            self._queues[queue_name] = []
        self._queues[queue_name].append(task_id)
        self._sort_queue(queue_name)

        # Try to assign
        await self._try_assign_tasks(queue_name)

    async def _handle_timeout(self, task_id: str):
        """
        Handle task timeout.

        Args:
            task_id: Task ID
        """
        if task_id not in self._tasks:
            return

        state = self._tasks[task_id]
        timeout = state.task.timeout

        await asyncio.sleep(timeout)

        # Check if still in progress
        if state.status in (TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS):
            # Timeout - fail task
            worker_id = state.assigned_to or "unknown"
            await self.fail_task(task_id, worker_id, "Task timeout")

    def _sort_queue(self, queue_name: str):
        """
        Sort queue by priority.

        Args:
            queue_name: Queue name
        """
        if queue_name not in self._queues:
            return

        queue = self._queues[queue_name]

        # Sort by priority (descending)
        queue.sort(
            key=lambda tid: self._tasks[tid].task.priority.value if tid in self._tasks else 0,
            reverse=True,
        )

    def get_task(self, task_id: str) -> Task | None:
        """
        Get task by ID.

        Args:
            task_id: Task ID

        Returns:
            Task or None
        """
        if task_id not in self._tasks:
            return None
        return self._tasks[task_id].task

    def get_task_status(self, task_id: str) -> TaskStatus | None:
        """
        Get task status.

        Args:
            task_id: Task ID

        Returns:
            Task status or None
        """
        if task_id not in self._tasks:
            return None
        return self._tasks[task_id].status

    def get_queue_stats(self, queue_name: str) -> dict[str, Any]:
        """
        Get queue statistics.

        Args:
            queue_name: Queue name

        Returns:
            Statistics dictionary
        """
        stats = {
            "queue_name": queue_name,
            "pending": 0,
            "assigned": 0,
            "in_progress": 0,
            "completed": 0,
            "failed": 0,
        }

        # Count tasks in queue
        if queue_name in self._queues:
            for task_id in self._queues[queue_name]:
                if task_id in self._tasks:
                    status = self._tasks[task_id].status
                    if status == TaskStatus.PENDING:
                        stats["pending"] += 1

        # Count all tasks for this queue
        for task_id, state in self._tasks.items():
            if state.task.queue_name == queue_name:
                status = state.status
                if status == TaskStatus.ASSIGNED:
                    stats["assigned"] += 1
                elif status == TaskStatus.IN_PROGRESS:
                    stats["in_progress"] += 1
                elif status == TaskStatus.COMPLETED:
                    stats["completed"] += 1
                elif status == TaskStatus.FAILED:
                    stats["failed"] += 1

        return stats

    def get_worker_stats(self, worker_id: str) -> dict[str, Any]:
        """
        Get worker statistics.

        Args:
            worker_id: Worker ID

        Returns:
            Statistics dictionary
        """
        if worker_id not in self._workers:
            return {}

        worker = self._workers[worker_id]

        return {
            "worker_id": worker_id,
            "capabilities": list(worker.capabilities),
            "max_concurrent": worker.max_concurrent,
            "active_tasks": len(worker.active_tasks),
            "last_heartbeat": worker.last_heartbeat.isoformat(),
        }

    def get_dead_letter_queue(self) -> list[str]:
        """
        Get dead letter queue.

        Returns:
            List of failed task IDs
        """
        return self._dead_letter.copy()
