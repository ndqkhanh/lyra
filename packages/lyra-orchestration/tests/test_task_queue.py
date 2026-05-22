"""Tests for task queue system."""

import asyncio

import pytest

from lyra_orchestration.task_queue import (
    TaskPriority,
    TaskQueue,
    TaskStatus,
)


@pytest.mark.asyncio
async def test_enqueue_task():
    """Test enqueuing a task."""
    queue = TaskQueue()

    task_id = await queue.enqueue(
        queue_name="processing",
        payload={"data": "test"},
        priority=TaskPriority.NORMAL,
    )

    assert task_id is not None

    task = queue.get_task(task_id)
    assert task is not None
    assert task.queue_name == "processing"
    assert task.payload["data"] == "test"


@pytest.mark.asyncio
async def test_register_worker():
    """Test registering a worker."""
    queue = TaskQueue()

    result = await queue.register_worker(
        worker_id="worker1",
        capabilities={"processing", "analysis"},
        max_concurrent=5,
    )

    assert result is True

    stats = queue.get_worker_stats("worker1")
    assert stats["worker_id"] == "worker1"
    assert "processing" in stats["capabilities"]
    assert stats["max_concurrent"] == 5


@pytest.mark.asyncio
async def test_task_assignment():
    """Test automatic task assignment to worker."""
    queue = TaskQueue()

    # Register worker
    await queue.register_worker(
        worker_id="worker1",
        capabilities={"processing"},
        max_concurrent=5,
    )

    # Enqueue task
    task_id = await queue.enqueue(
        queue_name="processing",
        payload={"data": "test"},
    )

    # Wait for assignment
    await asyncio.sleep(0.1)

    status = queue.get_task_status(task_id)
    assert status == TaskStatus.ASSIGNED


@pytest.mark.asyncio
async def test_task_completion():
    """Test task completion."""
    queue = TaskQueue()

    # Register worker
    await queue.register_worker(
        worker_id="worker1",
        capabilities={"processing"},
    )

    # Enqueue task
    task_id = await queue.enqueue(
        queue_name="processing",
        payload={"data": "test"},
    )

    # Wait for assignment
    await asyncio.sleep(0.1)

    # Complete task
    result = await queue.complete_task(
        task_id=task_id,
        worker_id="worker1",
        result={"output": "processed"},
    )

    assert result is True

    status = queue.get_task_status(task_id)
    assert status == TaskStatus.COMPLETED


@pytest.mark.asyncio
async def test_task_failure_and_retry():
    """Test task failure and retry."""
    queue = TaskQueue()

    # Register worker
    await queue.register_worker(
        worker_id="worker1",
        capabilities={"processing"},
    )

    # Enqueue task with retries
    task_id = await queue.enqueue(
        queue_name="processing",
        payload={"data": "test"},
        max_retries=3,
    )

    # Wait for assignment
    await asyncio.sleep(0.1)

    # Fail task
    result = await queue.fail_task(
        task_id=task_id,
        worker_id="worker1",
        error="Processing error",
    )

    assert result is True

    # Should be retrying
    status = queue.get_task_status(task_id)
    assert status == TaskStatus.RETRYING

    # Wait for reassignment
    await asyncio.sleep(0.1)

    status = queue.get_task_status(task_id)
    assert status == TaskStatus.ASSIGNED


@pytest.mark.asyncio
async def test_task_dead_letter_queue():
    """Test task moving to dead letter queue after max retries."""
    queue = TaskQueue()

    # Register worker
    await queue.register_worker(
        worker_id="worker1",
        capabilities={"processing"},
    )

    # Enqueue task with 1 retry
    task_id = await queue.enqueue(
        queue_name="processing",
        payload={"data": "test"},
        max_retries=1,
    )

    # Wait for assignment
    await asyncio.sleep(0.1)

    # Fail task twice
    await queue.fail_task(task_id, "worker1", "Error 1")
    await asyncio.sleep(0.1)
    await queue.fail_task(task_id, "worker1", "Error 2")

    # Should be in dead letter queue
    status = queue.get_task_status(task_id)
    assert status == TaskStatus.FAILED

    dead_letter = queue.get_dead_letter_queue()
    assert task_id in dead_letter


@pytest.mark.asyncio
async def test_priority_ordering():
    """Test priority-based task ordering."""
    queue = TaskQueue()

    # Enqueue tasks with different priorities
    low_id = await queue.enqueue(
        queue_name="processing",
        payload={"priority": "low"},
        priority=TaskPriority.LOW,
    )

    high_id = await queue.enqueue(
        queue_name="processing",
        payload={"priority": "high"},
        priority=TaskPriority.HIGH,
    )

    normal_id = await queue.enqueue(
        queue_name="processing",
        payload={"priority": "normal"},
        priority=TaskPriority.NORMAL,
    )

    # Register worker
    await queue.register_worker(
        worker_id="worker1",
        capabilities={"processing"},
        max_concurrent=1,  # Only 1 at a time
    )

    # Wait for assignment
    await asyncio.sleep(0.1)

    # High priority should be assigned first
    high_status = queue.get_task_status(high_id)
    assert high_status == TaskStatus.ASSIGNED

    normal_status = queue.get_task_status(normal_id)
    assert normal_status == TaskStatus.PENDING

    low_status = queue.get_task_status(low_id)
    assert low_status == TaskStatus.PENDING


@pytest.mark.asyncio
async def test_worker_max_concurrent():
    """Test worker max concurrent tasks limit."""
    queue = TaskQueue()

    # Register worker with max 2 concurrent
    await queue.register_worker(
        worker_id="worker1",
        capabilities={"processing"},
        max_concurrent=2,
    )

    # Enqueue 3 tasks
    task1 = await queue.enqueue("processing", {"id": 1})
    task2 = await queue.enqueue("processing", {"id": 2})
    task3 = await queue.enqueue("processing", {"id": 3})

    # Wait for assignment
    await asyncio.sleep(0.1)

    # First 2 should be assigned
    assert queue.get_task_status(task1) == TaskStatus.ASSIGNED
    assert queue.get_task_status(task2) == TaskStatus.ASSIGNED

    # Third should be pending
    assert queue.get_task_status(task3) == TaskStatus.PENDING

    # Complete one task
    await queue.complete_task(task1, "worker1", {"result": "done"})

    # Wait for reassignment
    await asyncio.sleep(0.1)

    # Third should now be assigned
    assert queue.get_task_status(task3) == TaskStatus.ASSIGNED


@pytest.mark.asyncio
async def test_unregister_worker():
    """Test unregistering a worker."""
    queue = TaskQueue()

    # Register two workers so task can be reassigned
    await queue.register_worker(
        worker_id="worker1",
        capabilities={"processing"},
    )
    await queue.register_worker(
        worker_id="worker2",
        capabilities={"processing"},
    )

    # Enqueue task
    task_id = await queue.enqueue("processing", {"data": "test"})

    # Wait for assignment
    await asyncio.sleep(0.1)

    # Task should be assigned to one of the workers
    status_before = queue.get_task_status(task_id)
    assert status_before == TaskStatus.ASSIGNED

    # Unregister worker1
    result = await queue.unregister_worker("worker1")
    assert result is True

    # Wait for potential reassignment
    await asyncio.sleep(0.2)

    # Task should still be assigned (to worker2 if it was on worker1, or still on worker2)
    status_after = queue.get_task_status(task_id)
    assert status_after in (TaskStatus.ASSIGNED, TaskStatus.PENDING)


@pytest.mark.asyncio
async def test_worker_heartbeat():
    """Test worker heartbeat."""
    queue = TaskQueue()

    # Register worker
    await queue.register_worker(
        worker_id="worker1",
        capabilities={"processing"},
    )

    # Send heartbeat
    result = await queue.heartbeat("worker1")
    assert result is True

    # Invalid worker
    result = await queue.heartbeat("worker2")
    assert result is False


@pytest.mark.asyncio
async def test_wait_for_completion():
    """Test waiting for task completion."""
    queue = TaskQueue()

    # Register worker
    await queue.register_worker(
        worker_id="worker1",
        capabilities={"processing"},
    )

    # Enqueue task
    task_id = await queue.enqueue("processing", {"data": "test"})

    # Complete task in background
    async def complete_later():
        await asyncio.sleep(0.2)
        await queue.complete_task(task_id, "worker1", {"output": "done"})

    asyncio.create_task(complete_later())

    # Wait for completion
    result = await queue.wait_for_completion(task_id, timeout=1)

    assert result is not None
    assert result["output"] == "done"


@pytest.mark.asyncio
async def test_wait_for_completion_timeout():
    """Test waiting for task completion with timeout."""
    queue = TaskQueue()

    # Register worker
    await queue.register_worker(
        worker_id="worker1",
        capabilities={"processing"},
    )

    # Enqueue task
    task_id = await queue.enqueue("processing", {"data": "test"})

    # Don't complete task, wait for timeout
    result = await queue.wait_for_completion(task_id, timeout=0.1)

    assert result is None


@pytest.mark.asyncio
async def test_queue_stats():
    """Test queue statistics."""
    queue = TaskQueue()

    # Register worker
    await queue.register_worker(
        worker_id="worker1",
        capabilities={"processing"},
        max_concurrent=1,
    )

    # Enqueue tasks
    await queue.enqueue("processing", {"id": 1})
    await queue.enqueue("processing", {"id": 2})

    # Wait for assignment
    await asyncio.sleep(0.1)

    stats = queue.get_queue_stats("processing")

    assert stats["queue_name"] == "processing"
    assert stats["assigned"] == 1
    assert stats["pending"] == 1


@pytest.mark.asyncio
async def test_multiple_workers():
    """Test multiple workers handling tasks."""
    queue = TaskQueue()

    # Register multiple workers
    await queue.register_worker("worker1", {"processing"}, max_concurrent=1)
    await queue.register_worker("worker2", {"processing"}, max_concurrent=1)

    # Enqueue tasks
    task1 = await queue.enqueue("processing", {"id": 1})
    task2 = await queue.enqueue("processing", {"id": 2})

    # Wait for assignment
    await asyncio.sleep(0.1)

    # Both should be assigned to different workers
    assert queue.get_task_status(task1) == TaskStatus.ASSIGNED
    assert queue.get_task_status(task2) == TaskStatus.ASSIGNED


@pytest.mark.asyncio
async def test_worker_capabilities():
    """Test worker capabilities filtering."""
    queue = TaskQueue()

    # Register worker with specific capabilities
    await queue.register_worker(
        worker_id="worker1",
        capabilities={"processing"},  # Only processing
    )

    # Enqueue task for different queue
    task_id = await queue.enqueue("analysis", {"data": "test"})

    # Wait
    await asyncio.sleep(0.1)

    # Should not be assigned (no capable worker)
    assert queue.get_task_status(task_id) == TaskStatus.PENDING

    # Register capable worker
    await queue.register_worker(
        worker_id="worker2",
        capabilities={"analysis"},
    )

    # Wait for assignment
    await asyncio.sleep(0.1)

    # Should now be assigned
    assert queue.get_task_status(task_id) == TaskStatus.ASSIGNED
