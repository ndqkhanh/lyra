"""Tests for ParallelExecutor."""

from __future__ import annotations

import pytest
from lyra_cli.swarm.parallel_executor import (
    ExecutorConfig,
    ParallelExecutor,
    WorkItem,
)


@pytest.mark.asyncio
async def test_submit_work_item_returns_id() -> None:
    """Submitting a work item should return its work ID."""
    ex = ParallelExecutor()

    def sync_work() -> str:
        return "ok"

    wid = await ex.submit_func(sync_work)
    assert wid.startswith("work_")


@pytest.mark.asyncio
async def test_submit_and_wait_returns_result() -> None:
    """submit_and_wait should complete and return a WorkResult."""
    ex = ParallelExecutor()
    await ex.start()

    async def work() -> str:
        return "hello"

    item = WorkItem(coro=work())
    result = await ex.submit_and_wait(item)
    assert result.success is True
    assert result.result == "hello"

    await ex.stop()


@pytest.mark.asyncio
async def test_submit_with_timeout() -> None:
    """A work item that times out should report timed_out status."""
    ex = ParallelExecutor(ExecutorConfig(default_timeout=0.1))
    await ex.start()

    async def slow_work() -> None:
        await __import__("asyncio").sleep(10.0)

    item = WorkItem(coro=slow_work(), timeout=0.1)
    result = await ex.submit_and_wait(item)
    assert result.success is False

    await ex.stop()


@pytest.mark.asyncio
async def test_executor_start_stop() -> None:
    """Starting and stopping the executor should manage workers."""
    ex = ParallelExecutor(ExecutorConfig(max_workers=2))
    await ex.start()
    assert len(ex._workers) == 2
    await ex.stop()
    assert len(ex._workers) == 0


@pytest.mark.asyncio
async def test_wait_all_collects_results() -> None:
    """wait_all should collect results for multiple work items."""
    ex = ParallelExecutor()
    await ex.start()

    async def a() -> str:
        return "A"

    async def b() -> str:
        return "B"

    id_a = await ex.submit_coro(a())
    id_b = await ex.submit_coro(b())
    results = await ex.wait_all([id_a, id_b])

    assert id_a in results
    assert id_b in results
    assert results[id_a].success is True
    assert results[id_b].success is True

    await ex.stop()


@pytest.mark.asyncio
async def test_cancel_pending_work() -> None:
    """Cancelling pending work should mark it as failed."""
    ex = ParallelExecutor()

    def never_run() -> str:
        return "never"

    wid = await ex.submit_func(never_run)
    cancelled = await ex.cancel(wid)
    assert cancelled is True

    work = ex.get_work(wid)
    assert work is not None
    assert work.status == "failed"


@pytest.mark.asyncio
async def test_submit_func_runs_sync_function() -> None:
    """submit_func should execute a synchronous function."""
    ex = ParallelExecutor()
    await ex.start()

    def sync_add() -> int:
        return 2 + 2

    wid = await ex.submit_func(sync_add)
    result = await ex.wait_for(wid)
    assert result.success is True
    assert result.result == 4

    await ex.stop()


@pytest.mark.asyncio
async def test_get_stats() -> None:
    """get_stats should return accurate counters."""
    ex = ParallelExecutor()

    def work() -> None:
        pass

    await ex.submit_func(work)
    stats = ex.get_stats()
    assert stats["items_submitted"] == 1
