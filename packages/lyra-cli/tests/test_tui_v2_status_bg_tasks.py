"""Phase 4 — Background task count in status segments."""
from __future__ import annotations

import pytest

from lyra_cli.tui_v2.status import format_bg_tasks_segment


def test_zero_returns_empty():
    assert format_bg_tasks_segment(0) == ""


def test_negative_returns_empty():
    assert format_bg_tasks_segment(-1) == ""


def test_singular_label():
    result = format_bg_tasks_segment(1)
    assert "1 background task" in result
    assert "tasks" not in result


def test_plural_label():
    result = format_bg_tasks_segment(5)
    assert "5 background tasks" in result


def test_includes_rich_markup():
    result = format_bg_tasks_segment(3)
    assert "[bold cyan]" in result or "cyan" in result


def test_includes_play_icon():
    result = format_bg_tasks_segment(2)
    assert "⏵⏵" in result


# --- status_bar.py footer integration ---

def test_footer_includes_bg_tasks_segment():
    from lyra_cli.interactive.status_bar import render_footer
    from lyra_cli.interactive.status_source import StatusSource

    src = StatusSource()
    src.update(bg_task_count=4, model="test-model")
    # term_cols=200 prevents the narrow-terminal drop logic from hiding the segment.
    result = render_footer(src, plain=True, term_cols=200)
    assert "4 background tasks" in result


def test_footer_hides_bg_tasks_when_zero():
    from lyra_cli.interactive.status_bar import render_footer
    from lyra_cli.interactive.status_source import StatusSource

    src = StatusSource()
    src.update(bg_task_count=0)
    result = render_footer(src, plain=True, term_cols=200)
    assert "background" not in result
