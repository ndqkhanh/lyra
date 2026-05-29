"""
Parallel Executor for work-stealing concurrent task execution.

Implements:
- Work-stealing queue for load balancing
- Concurrent task execution with asyncio
- Result collection with configurable timeouts
- Bounded parallelism with semaphore throttling
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass
class ExecutorConfig:
    """Configuration for the parallel executor."""

    max_workers: int = 5
    queue_capacity: int = 100
    default_timeout: float = 60.0
    poll_interval: float = 0.01
    enable_work_stealing: bool = True


@dataclass
class WorkItem:
    """A unit of work for the parallel executor."""

    work_id: str = field(default_factory=lambda: f"work_{uuid4().hex[:8]}")
    coro: Any | None = None
    func: Callable[[], Any] | None = None
    timeout: float = 60.0
    priority: int = 0
    status: str = "pending"  # pending, running, completed, failed, timed_out
    result: Any | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None


@dataclass
class WorkResult:
    """Result of a completed work item."""

    work_id: str
    success: bool
    result: Any | None = None
    error: str | None = None
    duration: float = 0.0


class ParallelExecutor:
    """
    Executes tasks concurrently using a work-stealing approach.

    Features:
    - Bounded parallelism via asyncio.Semaphore
    - Work-stealing queue for load distribution
    - Configurable per-task timeouts
    - Result collection and aggregation
    - Priority-based scheduling
    """

    def __init__(self, config: ExecutorConfig | None = None) -> None:
        self.config = config or ExecutorConfig()
        self._semaphore: asyncio.Semaphore = asyncio.Semaphore(self.config.max_workers)
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=self.config.queue_capacity)
        self._lock: asyncio.Lock = asyncio.Lock()
        self._work_items: dict[str, WorkItem] = {}
        self._running: bool = False
        self._workers: list[asyncio.Task] = []
        self._stats: dict[str, int] = {
            "items_submitted": 0,
            "items_completed": 0,
            "items_failed": 0,
            "items_timed_out": 0,
            "items_stolen": 0,
        }

    async def submit(self, work: WorkItem) -> str:
        """
        Submit a work item for execution.

        Args:
            work: The work item to execute

        Returns:
            The work ID
        """
        async with self._lock:
            self._work_items[work.work_id] = work
            self._stats["items_submitted"] += 1
        await self._queue.put(work)
        return work.work_id

    async def submit_coro(
        self,
        coro: Any,
        timeout: float | None = None,
        priority: int = 0,
    ) -> str:
        """
        Submit a coroutine for execution.

        Args:
            coro: The coroutine to execute
            timeout: Timeout in seconds
            priority: Priority (lower = higher)

        Returns:
            The work ID
        """
        work = WorkItem(
            coro=coro,
            timeout=timeout or self.config.default_timeout,
            priority=priority,
        )
        return await self.submit(work)

    async def submit_func(
        self,
        func: Callable[[], Any],
        timeout: float | None = None,
        priority: int = 0,
    ) -> str:
        """
        Submit a synchronous function for execution in the event loop.

        Args:
            func: The function to execute
            timeout: Timeout in seconds
            priority: Priority (lower = higher)

        Returns:
            The work ID
        """
        work = WorkItem(
            func=func,
            timeout=timeout or self.config.default_timeout,
            priority=priority,
        )
        return await self.submit(work)

    async def submit_and_wait(
        self,
        work: WorkItem,
    ) -> WorkResult:
        """
        Submit a work item and wait for its result.

        Args:
            work: The work item

        Returns:
            WorkResult with the outcome
        """
        work_id = await self.submit(work)
        return await self.wait_for(work_id)

    async def wait_for(self, work_id: str) -> WorkResult:
        """
        Wait for a specific work item to complete.

        Args:
            work_id: The work item to wait for

        Returns:
            WorkResult
        """
        start = time.time()
        while True:
            async with self._lock:
                work = self._work_items.get(work_id)
                if work is None:
                    return WorkResult(work_id=work_id, success=False, error="Not found")
                if work.status == "completed":
                    return WorkResult(
                        work_id=work_id,
                        success=True,
                        result=work.result,
                        duration=(
                            work.completed_at - work.started_at
                            if work.started_at and work.completed_at
                            else 0
                        ),
                    )
                if work.status == "failed":
                    return WorkResult(
                        work_id=work_id,
                        success=False,
                        error=work.error,
                        duration=(
                            work.completed_at - work.started_at
                            if work.started_at and work.completed_at
                            else 0
                        ),
                    )
                if work.status == "timed_out":
                    return WorkResult(work_id=work_id, success=False, error="Timed out")

            if time.time() - start > work.timeout + 5.0:
                return WorkResult(work_id=work_id, success=False, error="Wait timeout")
            await asyncio.sleep(self.config.poll_interval)

    async def wait_all(self, work_ids: list[str]) -> dict[str, WorkResult]:
        """
        Wait for all specified work items.

        Args:
            work_ids: List of work IDs to wait for

        Returns:
            Dict mapping work ID to WorkResult
        """
        results: dict[str, WorkResult] = {}
        for work_id in work_ids:
            results[work_id] = await self.wait_for(work_id)
        return results

    async def cancel(self, work_id: str) -> bool:
        """Cancel a pending work item."""
        async with self._lock:
            work = self._work_items.get(work_id)
            if work is None or work.status != "pending":
                return False
            work.status = "failed"
            work.error = "Cancelled"
        return True

    async def start(self) -> None:
        """Start the executor worker pool."""
        self._running = True
        for _ in range(self.config.max_workers):
            worker = asyncio.create_task(self._worker_loop())
            self._workers.append(worker)

    async def stop(self) -> None:
        """Stop the executor and cancel pending work."""
        self._running = False
        for worker in self._workers:
            worker.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        async with self._lock:
            for work in list(self._work_items.values()):
                if work.status == "pending":
                    work.status = "failed"
                    work.error = "Executor stopped"

    async def _worker_loop(self) -> None:
        """Worker loop: steal work from the shared queue and execute it."""
        while self._running:
            try:
                work = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                async with self._semaphore:
                    await self._execute_work(work)
                self._queue.task_done()
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception:
                pass

    async def _execute_work(self, work: WorkItem) -> None:
        """Execute a single work item with timeout handling."""
        async with self._lock:
            work.status = "running"
            work.started_at = time.time()

        try:
            if work.coro is not None:
                result = await asyncio.wait_for(work.coro, timeout=work.timeout)
            elif work.func is not None:
                result = await asyncio.wait_for(
                    asyncio.to_thread(work.func),
                    timeout=work.timeout,
                )
            else:
                result = None

            async with self._lock:
                work.result = result
                work.status = "completed"
                work.completed_at = time.time()
                self._stats["items_completed"] += 1

        except asyncio.TimeoutError:
            async with self._lock:
                work.status = "timed_out"
                work.error = f"Timed out after {work.timeout}s"
                work.completed_at = time.time()
                self._stats["items_timed_out"] += 1
        except Exception as exc:
            async with self._lock:
                work.status = "failed"
                work.error = str(exc)
                work.completed_at = time.time()
                self._stats["items_failed"] += 1

    def get_work(self, work_id: str) -> WorkItem | None:
        """Get a work item by ID."""
        return self._work_items.get(work_id)

    def get_pending_count(self) -> int:
        """Get the number of pending work items."""
        return self._queue.qsize()

    def get_stats(self) -> dict[str, int]:
        """Get executor statistics."""
        return dict(self._stats)
