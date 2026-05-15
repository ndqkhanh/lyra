"""Phase 3 — Sub-task checklist renderer."""
from __future__ import annotations

from typing import Literal

from lyra_cli.interactive.status_source import TaskItem
from lyra_cli.interactive.task_list import render_checklist, render_checklist_text


def _make(n: int, state: Literal["pending", "running", "done"] = "pending") -> list[TaskItem]:
    return [TaskItem(id=str(i), description=f"Task {i}", state=state) for i in range(n)]


def test_empty_returns_empty_list():
    assert render_checklist([]) == []


def test_single_task_uses_connector_prefix():
    lines = render_checklist([TaskItem("1", "Do work")])
    assert len(lines) == 1
    assert lines[0].startswith("  ⎿  ")
    assert "◻ Do work" in lines[0]


def test_second_task_uses_indent_prefix():
    lines = render_checklist(_make(2))
    assert lines[1].startswith("     ")
    assert "⎿" not in lines[1]


def test_pending_glyph():
    lines = render_checklist([TaskItem("1", "X", state="pending")])
    assert "◻" in lines[0]


def test_running_glyph():
    lines = render_checklist([TaskItem("1", "X", state="running")])
    assert "◼" in lines[0]


def test_done_glyph():
    lines = render_checklist([TaskItem("1", "X", state="done")])
    assert "✓" in lines[0]


def test_max_5_visible_by_default():
    tasks = _make(8)
    lines = render_checklist(tasks)
    # 5 task lines + 1 collapse line
    assert len(lines) == 6


def test_collapse_shows_remaining_count():
    tasks = _make(8)
    lines = render_checklist(tasks)
    assert "+3 pending" in lines[-1]
    assert "…" in lines[-1]


def test_custom_max_visible():
    tasks = _make(10)
    lines = render_checklist(tasks, max_visible=3)
    assert len(lines) == 4  # 3 tasks + collapse
    assert "+7 pending" in lines[-1]


def test_no_collapse_when_fits():
    tasks = _make(5)
    lines = render_checklist(tasks, max_visible=5)
    assert len(lines) == 5
    assert "pending" not in lines[-1]


def test_render_checklist_text_joins():
    tasks = _make(2)
    text = render_checklist_text(tasks)
    assert "\n" in text
    assert "Task 0" in text
    assert "Task 1" in text
