"""
Worker pool for managing parallel subagent processes.

Provides ``WorkerPool`` as a concurrency manager that spawns isolated worker
sessions, dispatches sub-tasks, collects artifacts, and respects a
configurable ``max_concurrency`` cap.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from lyra.orchestrator.artifact import Artifact, CompressionLevel, compress_artifact


@dataclass
class WorkerConfig:
    """
    Configuration for the worker pool.

    Attributes:
        max_concurrency: Maximum number of workers running concurrently.
        default_timeout: Default timeout (seconds) per worker task.
        compression: Compression level for returned artifacts.
        artifact_dir: Directory for persisting artifacts to disk.
        max_retries: Maximum number of retries for failed workers.
    """

    max_concurrency: int = 4
    default_timeout: float = 120.0
    compression: CompressionLevel = CompressionLevel.FULL
    artifact_dir: str = "data/artifacts"
    max_retries: int = 2


class WorkerSession:
    """
    Represents an isolated worker session.

    Each ``WorkerSession`` has its own context (id, metadata) and can execute
    an arbitrary async task function, returning an ``Artifact``.
    """

    def __init__(self, worker_id: str = "", metadata: dict[str, Any] | None = None) -> None:
        """
        Initialize a worker session.

        Args:
            worker_id: Unique identifier. Auto-generated if empty.
            metadata: Optional metadata attached to this session.
        """
        self.worker_id = worker_id or f"worker_{uuid4().hex[:8]}"
        self.context: dict[str, Any] = {}
        self.metadata: dict[str, Any] = metadata or {}
        self._started_at: float | None = None
        self._finished_at: float | None = None

    @property
    def elapsed(self) -> float:
        """Return elapsed wall-clock time (0.0 if not started/finished)."""
        if self._started_at is None:
            return 0.0
        end = self._finished_at or time.monotonic()
        return end - self._started_at

    async def run(self, task_func: callable, **kwargs: Any) -> Artifact:
        """
        Execute a task function within this isolated session.

        Args:
            task_func: An async callable that receives ``worker_id`` and
                ``context`` as keyword arguments and returns an ``Artifact``.
            kwargs: Additional keyword arguments forwarded to ``task_func``.

        Returns:
            The ``Artifact`` produced by the task function.
        """
        self._started_at = time.monotonic()
        try:
            artifact = await task_func(worker_id=self.worker_id, context=self.context, **kwargs)
            artifact.worker_id = self.worker_id
            return artifact
        finally:
            self._finished_at = time.monotonic()

    def __repr__(self) -> str:
        return f"<WorkerSession id={self.worker_id} running={self._started_at is not None}>"


class WorkerPool:
    """
    Manages a pool of subagent worker sessions with configurable concurrency.

    Example usage::

        pool = WorkerPool(max_concurrency=4)

        async def my_task(worker_id, context, question):
            # ... do work ...
            return Artifact(task_id="t1", content="...", confidence=0.9)

        artifacts = await pool.run_batch(
            [("task1", my_task, {"question": "..."}),
             ("task2", my_task, {"question": "..."})]
        )
    """

    def __init__(self, config: WorkerConfig | None = None) -> None:
        """
        Initialize the worker pool.

        Args:
            config: Configuration for the pool. Defaults are used if None.
        """
        self.config = config or WorkerConfig()
        self._semaphore = asyncio.Semaphore(self.config.max_concurrency)
        self._active_sessions: dict[str, WorkerSession] = {}
        self._completed_count: int = 0
        self._failed_count: int = 0

    @property
    def active_count(self) -> int:
        """Return the number of currently active worker sessions."""
        return len(self._active_sessions)

    @property
    def completed_count(self) -> int:
        """Return the total number of completed tasks."""
        return self._completed_count

    @property
    def failed_count(self) -> int:
        """Return the total number of failed tasks."""
        return self._failed_count

    async def run_worker(
        self,
        task_func: callable,
        task_id: str = "",
        metadata: dict[str, Any] | None = None,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> Artifact:
        """
        Run a single worker task within the concurrency limit.

        Args:
            task_func: An async callable that takes ``worker_id`` and
                ``context`` as keyword arguments and returns an ``Artifact``.
            task_id: Identifier for the task. Used as the artifact's
                ``task_id``. Auto-generated if empty.
            metadata: Optional metadata for the worker session.
            timeout: Maximum wall-clock time (seconds) for this worker.
                Falls back to ``self.config.default_timeout`` if None.
            kwargs: Additional keyword arguments forwarded to ``task_func``.

        Returns:
            The ``Artifact`` produced by the worker.

        Raises:
            asyncio.TimeoutError: If the worker exceeds the timeout.
            Exception: Any exception raised by the worker task function.
        """
        worker_id = f"w_{task_id or uuid4().hex[:8]}"
        session = WorkerSession(worker_id=worker_id, metadata=metadata)
        effective_timeout = timeout if timeout is not None else self.config.default_timeout

        async with self._semaphore:
            self._active_sessions[worker_id] = session

            try:
                for attempt in range(1, self.config.max_retries + 2):
                    try:
                        artifact = await asyncio.wait_for(
                            session.run(task_func, **kwargs),
                            timeout=effective_timeout,
                        )
                        if task_id:
                            artifact.task_id = task_id

                        # Persist artifact to disk if configured
                        if self.config.artifact_dir:
                            path = f"{self.config.artifact_dir}/{task_id or worker_id}.json"
                            artifact.write_json(path)

                        self._completed_count += 1
                        return artifact

                    except Exception as exc:
                        if attempt <= self.config.max_retries:
                            # Re-create session for retry
                            session = WorkerSession(worker_id=worker_id, metadata=metadata)
                            continue
                        self._failed_count += 1
                        raise
            finally:
                self._active_sessions.pop(worker_id, None)

    async def run_batch(
        self,
        tasks: list[tuple[str, callable, dict[str, Any]]],
        timeout: float | None = None,
    ) -> list[Artifact]:
        """
        Run multiple worker tasks in parallel, respecting concurrency limits.

        Each task is a tuple of ``(task_id, task_func, kwargs)``.

        Args:
            tasks: List of (task_id, callable, kwargs) tuples.
            timeout: Per-worker timeout. Falls back to config default.

        Returns:
            List of ``Artifact`` instances, one per task, in input order.
        """
        if not tasks:
            return []

        async def _wrapped(task_id: str, func: callable, kwargs: dict[str, Any]) -> Artifact:
            return await self.run_worker(
                task_func=func,
                task_id=task_id,
                timeout=timeout,
                **kwargs,
            )

        coros = [_wrapped(tid, fn, kw) for tid, fn, kw in tasks]

        # Run concurrently via gather (semaphore inside run_worker controls actual concurrency)
        results: list[Artifact] = await asyncio.gather(*coros, return_exceptions=True)

        # Process results — convert exceptions into error artifacts
        artifacts: list[Artifact] = []
        for idx, result in enumerate(results):
            tid = tasks[idx][0]
            if isinstance(result, Exception):
                artifacts.append(
                    Artifact(
                        task_id=tid,
                        content=f"Worker failed: {result}",
                        summary="Task execution failed.",
                        confidence=0.0,
                        metadata={"error": str(result)},
                    )
                )
            else:
                artifacts.append(result)

        return artifacts

    async def shutdown(self, wait: bool = True) -> None:
        """
        Shut down the worker pool.

        Args:
            wait: If True, wait for all active workers to complete.
                If False, active workers are left to finish in the background.
        """
        if wait:
            while self._active_sessions:
                await asyncio.sleep(0.1)
        self._active_sessions.clear()

    def stats(self) -> dict[str, Any]:
        """Return pool statistics."""
        return {
            "max_concurrency": self.config.max_concurrency,
            "active": self.active_count,
            "completed": self._completed_count,
            "failed": self._failed_count,
            "compression": self.config.compression.value,
            "artifact_dir": self.config.artifact_dir,
        }

    def __repr__(self) -> str:
        return (
            f"<WorkerPool max={self.config.max_concurrency} "
            f"active={self.active_count} completed={self._completed_count}>"
        )
