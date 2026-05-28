"""Tests for SwarmOrchestrator."""

from __future__ import annotations

import pytest
from lyra_cli.swarm.orchestrator import (
    OrchestratorConfig,
    SwarmOrchestrator,
    SwarmTask,
)


@pytest.mark.asyncio
async def test_submit_task_returns_task_id() -> None:
    """Submitting a task should return a valid task ID."""
    orch = SwarmOrchestrator()
    task = SwarmTask(description="test task")
    task_id = await orch.submit_task(task)
    assert task_id == task.task_id
    assert task.status == "queued"


@pytest.mark.asyncio
async def test_submit_and_wait_returns_result() -> None:
    """submit_and_wait should execute the task and return TaskResult."""
    orch = SwarmOrchestrator()
    await orch.start()

    async def dummy_work() -> str:
        return "done"

    task = SwarmTask(
        description="test",
        execution_func=dummy_work,
    )
    result = await orch.submit_and_wait(task)
    assert result.success is True
    assert result.result == "done"

    await orch.stop()


@pytest.mark.asyncio
async def test_submit_and_wait_with_failure_retries() -> None:
    """A failing task should be retried and eventually report failure."""
    orch = SwarmOrchestrator(OrchestratorConfig(max_retries_per_task=1, task_timeout_seconds=10.0))
    await orch.start()
    attempts = 0

    def failing_work() -> str:
        nonlocal attempts
        attempts += 1
        raise ValueError(f"Attempt {attempts} failed")

    task = SwarmTask(description="failing", execution_func=failing_work)
    result = await orch.submit_and_wait(task)
    assert result.success is False
    assert result.error is not None

    await orch.stop()


@pytest.mark.asyncio
async def test_decompose_task_creates_subtasks() -> None:
    """Decomposing a task should create sub-tasks with correct parent."""
    orch = SwarmOrchestrator()
    parent = SwarmTask(description="parent")
    parent_id = await orch.submit_task(parent)

    sub_ids = await orch.decompose_task(parent, ["sub1", "sub2"])
    assert len(sub_ids) == 2

    for sub_id in sub_ids:
        sub = orch.get_task(sub_id)
        assert sub is not None
        assert sub.parent_id == parent_id

    parent_task = orch.get_task(parent_id)
    assert parent_task is not None
    assert len(parent_task.subtasks) == 2


@pytest.mark.asyncio
async def test_aggregate_results_merges_subtasks() -> None:
    """Aggregate results should merge all sub-task results."""
    orch = SwarmOrchestrator()
    await orch.start()

    async def work_a() -> str:
        return "A"

    async def work_b() -> str:
        return "B"

    parent = SwarmTask(description="parent")
    parent_id = await orch.submit_task(parent)

    sub_ids = await orch.decompose_task(parent, ["sub_a", "sub_b"])
    sub_a = orch.get_task(sub_ids[0])
    sub_b = orch.get_task(sub_ids[1])
    assert sub_a is not None and sub_b is not None

    sub_a.execution_func = work_a
    sub_b.execution_func = work_b

    await orch.submit_task(sub_a)
    await orch.submit_task(sub_b)

    aggregated = await orch.aggregate_results(parent_id)
    assert aggregated is not None
    assert aggregated["total"] == 2
    assert aggregated["successful"] == 2

    await orch.stop()


@pytest.mark.asyncio
async def test_cancel_task() -> None:
    """Cancelling a task should mark it and its subtasks as cancelled."""
    orch = SwarmOrchestrator()
    task = SwarmTask(description="cancel me")
    task_id = await orch.submit_task(task)

    sub_ids = await orch.decompose_task(task, ["sub1"])
    cancelled = await orch.cancel_task(task_id)
    assert cancelled is True

    t = orch.get_task(task_id)
    assert t is not None
    assert t.status == "cancelled"

    sub = orch.get_task(sub_ids[0])
    assert sub is not None
    assert sub.status == "cancelled"


@pytest.mark.asyncio
async def test_start_stop_workers() -> None:
    """Starting and stopping the orchestrator should manage workers."""
    orch = SwarmOrchestrator(OrchestratorConfig(max_concurrent_tasks=2))
    assert orch.is_running is False

    await orch.start()
    assert orch.is_running is True

    await orch.stop()
    assert orch.is_running is False


@pytest.mark.asyncio
async def test_get_stats() -> None:
    """get_stats should return accurate counters."""
    orch = SwarmOrchestrator()
    task = SwarmTask(description="stats")
    await orch.submit_task(task)
    stats = orch.get_stats()
    assert stats["tasks_created"] == 1
