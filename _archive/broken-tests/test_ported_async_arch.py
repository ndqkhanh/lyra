"""Port of lyra-ui tests/test_async_arch.py → tests TUI async_bridge.py.
"""
from __future__ import annotations


def test_task_priority_enum():
    from lyra_cli.tui_v2.widgets.async_bridge import TaskPriority
    assert TaskPriority.LOW.value == 1
    assert TaskPriority.NORMAL.value == 2
    assert TaskPriority.HIGH.value == 3
    assert TaskPriority.CRITICAL.value == 4


def test_task_priority_glyph():
    from lyra_cli.tui_v2.widgets.async_bridge import TaskPriority
    assert TaskPriority.LOW.glyph == "↓"
    assert TaskPriority.NORMAL.glyph == "•"
    assert TaskPriority.HIGH.glyph == "↑"
    assert TaskPriority.CRITICAL.glyph == "⚡"


def test_task_status_enum():
    from lyra_cli.tui_v2.widgets.async_bridge import TaskStatus
    assert TaskStatus.PENDING.glyph == "◻"
    assert TaskStatus.RUNNING.glyph == "⏺"
    assert TaskStatus.DONE.glyph == "✓"
    assert TaskStatus.FAILED.glyph == "✗"
    assert TaskStatus.CANCELLED.glyph == "—"


def test_task_entry():
    from lyra_cli.tui_v2.widgets.async_bridge import TaskEntry, TaskStatus
    entry = TaskEntry(name="Test Task", priority=2)
    assert entry.name == "Test Task"
    assert entry.status == TaskStatus.PENDING
    assert len(entry.id) == 12


def test_task_entry_line():
    from lyra_cli.tui_v2.widgets.async_bridge import TaskEntry
    entry = TaskEntry(name="Test")
    line = entry.line
    assert "Test" in line


def test_task_queue_singleton():
    from lyra_cli.tui_v2.widgets.async_bridge import get_task_queue
    q1 = get_task_queue()
    q2 = get_task_queue()
    assert q1 is q2


def test_task_queue_init():
    from lyra_cli.tui_v2.widgets.async_bridge import BackgroundTaskQueue
    q = BackgroundTaskQueue(max_workers=2)
    assert q.max_workers == 2
    assert len(q._tasks) == 0


def test_task_queue_summary():
    from lyra_cli.tui_v2.widgets.async_bridge import BackgroundTaskQueue
    q = BackgroundTaskQueue()
    summary = q.summary()
    assert isinstance(summary, dict)
