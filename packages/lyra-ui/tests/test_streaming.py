"""Tests for streaming and progress visualization."""

import asyncio

import pytest

from lyra_ui import (
    LiveStreamDisplay,
    MultiTaskProgress,
    ProgressState,
    ProgressStep,
    ProgressVisualizer,
    StreamHandler,
    StreamingProgress,
)


# Streaming Tests


def test_stream_handler_init():
    """Test stream handler initialization."""
    handler = StreamHandler()
    assert handler.is_cancelled is False
    assert handler.is_paused is False
    assert len(handler.buffer) == 0


@pytest.mark.asyncio
async def test_stream_handler_basic():
    """Test basic streaming."""

    async def mock_stream():
        for token in ["Hello", " ", "world"]:
            yield token

    handler = StreamHandler()
    result = await handler.stream_response(mock_stream())
    assert result == "Hello world"


@pytest.mark.asyncio
async def test_stream_handler_with_callback():
    """Test streaming with callback."""
    tokens_received = []

    def on_token(token):
        tokens_received.append(token)

    async def mock_stream():
        for token in ["a", "b", "c"]:
            yield token

    handler = StreamHandler()
    await handler.stream_response(mock_stream(), on_token=on_token)
    assert tokens_received == ["a", "b", "c"]


@pytest.mark.asyncio
async def test_stream_handler_cancel():
    """Test stream cancellation."""

    async def mock_stream():
        for i in range(10):
            yield str(i)
            await asyncio.sleep(0.01)

    handler = StreamHandler()

    async def cancel_after_delay():
        await asyncio.sleep(0.03)
        handler.cancel()

    asyncio.create_task(cancel_after_delay())
    result = await handler.stream_response(mock_stream())
    # Should be cancelled before completing all 10 tokens
    assert len(result) < 10


def test_stream_handler_pause_resume():
    """Test pause and resume."""
    handler = StreamHandler()
    handler.pause()
    assert handler.is_paused is True
    handler.resume()
    assert handler.is_paused is False


def test_stream_handler_buffer():
    """Test buffer operations."""
    handler = StreamHandler()
    handler.buffer = ["a", "b", "c"]
    assert handler.get_buffer() == "abc"
    handler.clear_buffer()
    assert len(handler.buffer) == 0


def test_live_stream_display_init():
    """Test live stream display initialization."""
    display = LiveStreamDisplay()
    assert display.live is None


def test_live_stream_display_start_stop():
    """Test starting and stopping display."""
    display = LiveStreamDisplay()
    display.start()
    assert display.live is not None
    display.stop()
    assert display.live is None


def test_live_stream_display_append():
    """Test appending tokens."""
    display = LiveStreamDisplay()
    display.start()
    display.append_token("Hello")
    display.append_token(" world")
    display.stop()


def test_streaming_progress_init():
    """Test streaming progress initialization."""
    progress = StreamingProgress()
    assert progress.token_count == 0
    assert progress.start_time is None


def test_streaming_progress_tracking():
    """Test progress tracking."""
    progress = StreamingProgress()
    progress.start()
    assert progress.start_time is not None

    progress.increment(10)
    assert progress.token_count == 10

    progress.increment(5)
    assert progress.token_count == 15

    progress.stop()
    assert progress.end_time is not None


def test_streaming_progress_rate():
    """Test streaming rate calculation."""
    import time

    progress = StreamingProgress()
    progress.start()
    progress.increment(100)
    time.sleep(0.1)
    progress.stop()

    rate = progress.get_rate()
    assert rate > 0


def test_streaming_progress_elapsed():
    """Test elapsed time calculation."""
    import time

    progress = StreamingProgress()
    progress.start()
    time.sleep(0.1)
    elapsed = progress.get_elapsed()
    assert elapsed >= 0.1


# Progress Visualization Tests


def test_progress_step_init():
    """Test progress step initialization."""
    step = ProgressStep(name="test", description="Test step")
    assert step.name == "test"
    assert step.state == ProgressState.PENDING
    assert step.progress == 0.0


def test_multi_task_progress_init():
    """Test multi-task progress initialization."""
    tracker = MultiTaskProgress()
    assert len(tracker.tasks) == 0


def test_multi_task_progress_add_task():
    """Test adding task."""
    tracker = MultiTaskProgress()
    tracker.add_task("task1", "Task 1", "First task", total=100)
    assert "task1" in tracker.tasks
    assert tracker.tasks["task1"].name == "Task 1"


def test_multi_task_progress_start_task():
    """Test starting task."""
    tracker = MultiTaskProgress()
    tracker.add_task("task1", "Task 1", "First task")
    tracker.start_task("task1")
    assert tracker.tasks["task1"].state == ProgressState.RUNNING
    assert tracker.tasks["task1"].started_at is not None


def test_multi_task_progress_update_task():
    """Test updating task progress."""
    tracker = MultiTaskProgress()
    tracker.add_task("task1", "Task 1", "First task", total=100)
    tracker.update_task("task1", 50)
    assert tracker.tasks["task1"].progress == 50


def test_multi_task_progress_complete_task():
    """Test completing task."""
    tracker = MultiTaskProgress()
    tracker.add_task("task1", "Task 1", "First task")
    tracker.complete_task("task1", success=True)
    assert tracker.tasks["task1"].state == ProgressState.COMPLETED
    assert tracker.tasks["task1"].completed_at is not None


def test_multi_task_progress_fail_task():
    """Test failing task."""
    tracker = MultiTaskProgress()
    tracker.add_task("task1", "Task 1", "First task")
    tracker.complete_task("task1", success=False)
    assert tracker.tasks["task1"].state == ProgressState.FAILED


def test_multi_task_progress_cancel_task():
    """Test cancelling task."""
    tracker = MultiTaskProgress()
    tracker.add_task("task1", "Task 1", "First task")
    tracker.cancel_task("task1")
    assert tracker.tasks["task1"].state == ProgressState.CANCELLED


def test_multi_task_progress_get_task():
    """Test getting task."""
    tracker = MultiTaskProgress()
    tracker.add_task("task1", "Task 1", "First task")
    task = tracker.get_task("task1")
    assert task is not None
    assert task.name == "Task 1"


def test_multi_task_progress_get_all_tasks():
    """Test getting all tasks."""
    tracker = MultiTaskProgress()
    tracker.add_task("task1", "Task 1", "First task")
    tracker.add_task("task2", "Task 2", "Second task")
    tasks = tracker.get_all_tasks()
    assert len(tasks) == 2


def test_multi_task_progress_summary():
    """Test progress summary."""
    tracker = MultiTaskProgress()
    tracker.add_task("task1", "Task 1", "First task")
    tracker.add_task("task2", "Task 2", "Second task")
    tracker.add_task("task3", "Task 3", "Third task")

    tracker.start_task("task1")
    tracker.complete_task("task2", success=True)

    summary = tracker.get_summary()
    assert summary["total"] == 3
    assert summary["pending"] == 1
    assert summary["running"] == 1
    assert summary["completed"] == 1


def test_progress_visualizer_init():
    """Test progress visualizer initialization."""
    viz = ProgressVisualizer()
    assert viz.console is not None


def test_progress_visualizer_render_task():
    """Test rendering task."""
    viz = ProgressVisualizer()
    step = ProgressStep(name="Test", description="Test step", progress=50, total=100)
    rendered = viz.render_task(step)
    assert "Test" in rendered
    assert "50.0%" in rendered


def test_progress_visualizer_render_summary():
    """Test rendering summary."""
    viz = ProgressVisualizer()
    tracker = MultiTaskProgress()
    tracker.add_task("task1", "Task 1", "First task")
    tracker.add_task("task2", "Task 2", "Second task")

    panel = viz.render_summary(tracker)
    assert panel is not None


# Integration Tests


@pytest.mark.asyncio
async def test_streaming_with_progress():
    """Test streaming with progress tracking."""

    async def mock_stream():
        for i in range(10):
            yield str(i)

    handler = StreamHandler()
    progress = StreamingProgress()

    progress.start()

    tokens = []

    def on_token(token):
        tokens.append(token)
        progress.increment()

    await handler.stream_response(mock_stream(), on_token=on_token)
    progress.stop()

    assert len(tokens) == 10
    assert progress.token_count == 10


def test_multi_task_workflow():
    """Test complete multi-task workflow."""
    tracker = MultiTaskProgress()

    # Add tasks
    tracker.add_task("task1", "Download", "Downloading files", total=100)
    tracker.add_task("task2", "Process", "Processing data", total=50)
    tracker.add_task("task3", "Upload", "Uploading results", total=75)

    # Start and update tasks
    tracker.start_task("task1")
    tracker.update_task("task1", 50)
    tracker.update_task("task1", 100)
    tracker.complete_task("task1")

    tracker.start_task("task2")
    tracker.update_task("task2", 25)
    tracker.update_task("task2", 50)
    tracker.complete_task("task2")

    tracker.start_task("task3")
    tracker.update_task("task3", 75)
    tracker.complete_task("task3")

    # Check summary
    summary = tracker.get_summary()
    assert summary["completed"] == 3
    assert summary["running"] == 0
