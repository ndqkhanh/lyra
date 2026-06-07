"""Tests for the WorkerPool module."""

import asyncio

import pytest

from src.orchestrator.artifact import Artifact
from src.orchestrator.worker_pool import WorkerConfig, WorkerPool, WorkerSession


@pytest.fixture
def pool() -> WorkerPool:
    """Return a fresh WorkerPool with max_concurrency=4."""
    return WorkerPool(config=WorkerConfig(max_concurrency=4))


class TestWorkerSession:
    """Tests for WorkerSession."""

    @pytest.mark.asyncio
    async def test_run_returns_artifact(self) -> None:
        """Test running a task function returns an Artifact."""
        async def task(worker_id: str, context: dict) -> Artifact:
            return Artifact(task_id="t1", content=f"result from {worker_id}")

        session = WorkerSession()
        artifact = await session.run(task)
        assert artifact.worker_id == session.worker_id
        assert "result from" in artifact.content

    @pytest.mark.asyncio
    async def test_elapsed_time(self) -> None:
        """Test elapsed returns correct time after run."""

        async def task(worker_id: str, context: dict) -> Artifact:
            await asyncio.sleep(0.01)
            return Artifact(task_id="t1", content="done")

        session = WorkerSession()
        await session.run(task)
        assert session.elapsed >= 0.01

    @pytest.mark.asyncio
    async def test_elapsed_before_run(self) -> None:
        """Test elapsed is 0 before run."""
        session = WorkerSession()
        assert session.elapsed == 0.0

    def test_custom_worker_id(self) -> None:
        """Test custom worker ID is used."""
        session = WorkerSession(worker_id="my_worker")
        assert session.worker_id == "my_worker"

    def test_auto_worker_id(self) -> None:
        """Test auto-generated worker ID."""
        session = WorkerSession()
        assert session.worker_id.startswith("worker_")
        assert len(session.worker_id) > 7


class TestWorkerPool:
    """Tests for WorkerPool."""

    @pytest.mark.asyncio
    async def test_run_single_worker(self, pool: WorkerPool) -> None:
        """Test running a single worker task."""

        async def task(worker_id: str, context: dict) -> Artifact:
            return Artifact(task_id="single", content=f"ok from {worker_id}")

        artifact = await pool.run_worker(task, task_id="single")
        assert artifact.task_id == "single"
        assert artifact.worker_id.startswith("w_single")
        assert pool.completed_count == 1

    @pytest.mark.asyncio
    async def test_run_multiple_workers(self, pool: WorkerPool) -> None:
        """Test running multiple worker tasks concurrently."""

        async def task(worker_id: str, context: dict, label: str = "") -> Artifact:
            return Artifact(task_id=label, content=f"result {label}")

        artifacts = await pool.run_batch([
            ("a", task, {"label": "A"}),
            ("b", task, {"label": "B"}),
            ("c", task, {"label": "C"}),
        ])
        assert len(artifacts) == 3
        assert artifacts[0].task_id == "a"
        assert artifacts[1].task_id == "b"
        assert artifacts[2].task_id == "c"
        assert pool.completed_count == 3

    @pytest.mark.asyncio
    async def test_empty_batch(self, pool: WorkerPool) -> None:
        """Test running an empty batch returns empty list."""
        artifacts = await pool.run_batch([])
        assert artifacts == []

    @pytest.mark.asyncio
    async def test_concurrency_limit(self) -> None:
        """Test concurrency limit is respected."""
        pool = WorkerPool(config=WorkerConfig(max_concurrency=2))
        concurrency_tracker: int = 0
        max_seen: int = 0

        async def task(worker_id: str, context: dict) -> Artifact:
            nonlocal concurrency_tracker, max_seen
            concurrency_tracker += 1
            max_seen = max(max_seen, concurrency_tracker)
            await asyncio.sleep(0.05)
            concurrency_tracker -= 1
            return Artifact(task_id="t", content="ok")

        async def worker_wrapper(worker_id: str, context: dict, idx: int = 0) -> Artifact:
            return await task(worker_id=worker_id, context=context)

        await pool.run_batch([
            (f"t{i}", worker_wrapper, {"idx": i}) for i in range(6)
        ])
        assert max_seen <= 2, f"Max concurrency was {max_seen}, expected <= 2"

    @pytest.mark.asyncio
    async def test_timeout_raises(self, pool: WorkerPool) -> None:
        """Test worker timeout raises TimeoutError."""

        async def slow_task(worker_id: str, context: dict) -> Artifact:
            await asyncio.sleep(10.0)
            return Artifact(task_id="t1", content="never")

        with pytest.raises(asyncio.TimeoutError):
            await pool.run_worker(slow_task, task_id="slow", timeout=0.01)

    @pytest.mark.asyncio
    async def test_failed_worker_returns_error_artifact(self, pool: WorkerPool) -> None:
        """Test a failing worker returns an error artifact in batch mode."""

        async def failing_task(worker_id: str, context: dict) -> Artifact:
            raise RuntimeError("worker crashed")

        artifacts = await pool.run_batch([
            ("fail1", failing_task, {}),
            ("ok1", lambda wi, ctx: success_task(wi, ctx), {}),
        ])

        assert len(artifacts) == 2
        assert artifacts[0].confidence == 0.0
        assert "failed" in artifacts[0].content.lower()

    @pytest.mark.asyncio
    async def test_retry_on_failure(self) -> None:
        """Test retry logic re-executes on transient failure."""
        config = WorkerConfig(max_concurrency=2, max_retries=2)
        pool = WorkerPool(config=config)
        call_count: int = 0

        async def flaky_task(worker_id: str, context: dict) -> Artifact:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError(f"Attempt {call_count} failed")
            return Artifact(task_id="flaky", content="success after retry")

        artifact = await pool.run_worker(flaky_task, task_id="flaky")
        assert artifact.content == "success after retry"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_pool_stats(self, pool: WorkerPool) -> None:
        """Test pool stats returns expected keys."""
        stats = pool.stats()
        assert stats["max_concurrency"] == 4
        assert stats["active"] == 0
        assert stats["completed"] == 0
        assert stats["failed"] == 0
        assert "compression" in stats

    @pytest.mark.asyncio
    async def test_shutdown(self, pool: WorkerPool) -> None:
        """Test shutdown clears active sessions."""
        async def task(worker_id: str, context: dict) -> Artifact:
            await asyncio.sleep(0.1)
            return Artifact(task_id="t1", content="ok")

        # Start a task in background
        run_task = asyncio.create_task(pool.run_worker(task, task_id="bg"))
        await asyncio.sleep(0.01)  # let it start
        await pool.shutdown(wait=True)
        result = await run_task
        assert result.content == "ok"
        assert pool.active_count == 0


async def success_task(worker_id: str, context: dict) -> Artifact:
    """Simple success task for testing."""
    return Artifact(task_id="ok", content="success")
