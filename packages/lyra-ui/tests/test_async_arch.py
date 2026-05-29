"""Tests for async architecture."""

import asyncio

import pytest
from lyra_ui import (
    AsyncFileIO,
    BackgroundTaskQueue,
    ConnectionPool,
    RequestBatcher,
    TaskPriority,
    TaskStatus,
    WorkerPool,
)

# BackgroundTaskQueue Tests


@pytest.mark.asyncio
async def test_background_task_queue_init():
    """Test task queue initialization."""
    queue = BackgroundTaskQueue(max_workers=2)
    assert queue.max_workers == 2
    assert len(queue.tasks) == 0


@pytest.mark.asyncio
async def test_background_task_queue_submit():
    """Test submitting task."""
    queue = BackgroundTaskQueue(max_workers=2)
    await queue.start()

    def task_func():
        return "result"

    task_id = await queue.submit("task1", task_func)
    assert task_id == "task1"
    assert "task1" in queue.tasks

    await queue.stop()


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_background_task_queue_execution():
    """Test task execution."""
    queue = BackgroundTaskQueue(max_workers=2)
    await queue.start()

    result = []

    def task_func(value):
        result.append(value)

    await queue.submit("task1", task_func, "test")
    await asyncio.sleep(0.2)

    assert result == ["test"]
    task = queue.get_task("task1")
    assert task.status == TaskStatus.COMPLETED

    await queue.stop()


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_background_task_queue_priority():
    """Test task priority."""
    queue = BackgroundTaskQueue(max_workers=1)
    await queue.start()

    results = []

    def task_func(value):
        results.append(value)

    await queue.submit("low", task_func, "low", priority=TaskPriority.LOW)
    await queue.submit("high", task_func, "high", priority=TaskPriority.HIGH)
    await asyncio.sleep(0.3)

    # High priority should execute first
    assert results[0] == "high"

    await queue.stop()


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_background_task_queue_cancel():
    """Test task cancellation."""
    queue = BackgroundTaskQueue(max_workers=2)
    await queue.start()

    def task_func():
        pass

    await queue.submit("task1", task_func)
    queue.cancel_task("task1")

    task = queue.get_task("task1")
    assert task.status == TaskStatus.CANCELLED

    await queue.stop()


# WorkerPool Tests


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_worker_pool_init():
    """Test worker pool initialization."""
    pool = WorkerPool(max_workers=2)
    assert pool.executor is not None


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_worker_pool_submit():
    """Test submitting task to worker pool."""
    pool = WorkerPool(max_workers=2)

    def cpu_task(x):
        return x * 2

    result = await pool.submit(cpu_task, 5)
    assert result == 10

    pool.shutdown()


# AsyncFileIO Tests


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_async_file_io_read_write(tmp_path):
    """Test async file read/write."""
    file_path = tmp_path / "test.txt"
    content = "Hello, World!"

    await AsyncFileIO.write_file(file_path, content)
    read_content = await AsyncFileIO.read_file(file_path)

    assert read_content == content


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_async_file_io_read_files(tmp_path):
    """Test reading multiple files."""
    files = [tmp_path / f"file{i}.txt" for i in range(3)]

    for i, file in enumerate(files):
        await AsyncFileIO.write_file(file, f"content{i}")

    contents = await AsyncFileIO.read_files(files)
    assert contents == ["content0", "content1", "content2"]


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_async_file_io_write_files(tmp_path):
    """Test writing multiple files."""
    files = {
        tmp_path / "file1.txt": "content1",
        tmp_path / "file2.txt": "content2",
    }

    await AsyncFileIO.write_files(files)

    for path, expected_content in files.items():
        content = await AsyncFileIO.read_file(path)
        assert content == expected_content


# RequestBatcher Tests


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_request_batcher_init():
    """Test request batcher initialization."""
    batcher = RequestBatcher(batch_size=5, flush_interval=1.0)
    assert batcher.batch_size == 5
    assert batcher.flush_interval == 1.0


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_request_batcher_add():
    """Test adding requests."""
    batcher = RequestBatcher(batch_size=3, flush_interval=10.0)

    await batcher.add("req1")
    await batcher.add("req2")
    result = await batcher.add("req3")

    # Should flush when batch is full
    assert len(result) == 3


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_request_batcher_manual_flush():
    """Test manual flush."""
    batcher = RequestBatcher(batch_size=10, flush_interval=10.0)

    await batcher.add("req1")
    await batcher.add("req2")

    result = await batcher.flush()
    assert len(result) == 2


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_request_batcher_auto_flush():
    """Test auto flush."""
    batcher = RequestBatcher(batch_size=10, flush_interval=0.2)

    await batcher.add("req1")
    await asyncio.sleep(0.3)

    # Batch should be empty after auto-flush
    assert len(batcher.batch) == 0


# ConnectionPool Tests


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_connection_pool_init():
    """Test connection pool initialization."""
    pool = ConnectionPool(max_connections=5)
    assert pool.max_connections == 5
    assert len(pool.connections) == 0


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_connection_pool_acquire():
    """Test acquiring connection."""
    pool = ConnectionPool(max_connections=5)
    conn = await pool.acquire()
    assert conn is not None
    assert conn in pool.in_use


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_connection_pool_release():
    """Test releasing connection."""
    pool = ConnectionPool(max_connections=5)
    conn = await pool.acquire()
    await pool.release(conn)

    assert conn not in pool.in_use


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_connection_pool_reuse():
    """Test connection reuse."""
    pool = ConnectionPool(max_connections=5)

    conn1 = await pool.acquire()
    await pool.release(conn1)

    conn2 = await pool.acquire()
    assert conn1 == conn2


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_connection_pool_close_all():
    """Test closing all connections."""
    pool = ConnectionPool(max_connections=5)

    await pool.acquire()
    await pool.acquire()

    await pool.close_all()
    assert len(pool.connections) == 0


# Integration Tests


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_task_queue_with_async_io(tmp_path):
    """Test task queue with async file I/O."""
    queue = BackgroundTaskQueue(max_workers=2)
    await queue.start()

    file_path = tmp_path / "test.txt"

    async def write_task(path, content):
        await AsyncFileIO.write_file(path, content)

    await queue.submit("write", write_task, file_path, "test content")
    await asyncio.sleep(0.2)

    content = await AsyncFileIO.read_file(file_path)
    assert content == "test content"

    await queue.stop()


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_batcher_with_pool():
    """Test request batcher with connection pool."""
    batcher = RequestBatcher(batch_size=3, flush_interval=10.0)
    pool = ConnectionPool(max_connections=2)

    requests = []
    for i in range(3):
        result = await batcher.add(f"req{i}")
        if result:
            requests.extend(result)

    assert len(requests) == 3

    await pool.close_all()
