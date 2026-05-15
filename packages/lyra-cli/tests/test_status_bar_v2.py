"""Tests for Wave 2 status_bar.py enhancements."""
from __future__ import annotations

from pathlib import Path

from lyra_cli.interactive.status_bar import render_footer
from lyra_cli.interactive.status_source import StatusSource


def _src(**kv) -> StatusSource:
    s = StatusSource(cwd=Path("/home/user/project"), model="sonnet-4.6", mode="agent")
    for k, v in kv.items():
        setattr(s, k, v)
    return s


# ---- shell_count -----------------------------------------------------------

def test_shell_count_single_shown():
    src = _src(shell_count=1)
    plain = render_footer(src, plain=True)
    assert "1 shell" in plain


def test_shell_count_plural():
    src = _src(shell_count=3)
    plain = render_footer(src, plain=True)
    assert "3 shells" in plain


def test_shell_count_zero_hidden():
    src = _src(shell_count=0)
    plain = render_footer(src, plain=True)
    assert "shell" not in plain


# ---- is_inferring ----------------------------------------------------------

def test_is_inferring_shows_hint():
    src = _src(is_inferring=True)
    plain = render_footer(src, plain=True)
    assert "esc to interrupt" in plain


def test_is_inferring_false_hidden():
    src = _src(is_inferring=False)
    plain = render_footer(src, plain=True)
    assert "esc to interrupt" not in plain


# ---- bg_tasks with ↓ to manage hint ----------------------------------------

def test_bg_tasks_shows_down_to_manage():
    src = _src(bg_task_count=2)
    plain = render_footer(src, plain=True)
    assert "↓ to manage" in plain or "background" in plain


def test_bg_tasks_zero_hidden():
    src = _src(bg_task_count=0)
    plain = render_footer(src, plain=True)
    assert "background" not in plain


# ---- yolo permission badge --------------------------------------------------

def test_yolo_shows_bypass_badge():
    src = _src(permissions="yolo")
    plain = render_footer(src, plain=True)
    assert "bypass permissions on" in plain


def test_strict_shows_triangle_badge():
    src = _src(permissions="strict")
    plain = render_footer(src, plain=True)
    assert "strict" in plain
    assert "bypass" not in plain


def test_normal_permission_shown():
    src = _src(permissions="normal")
    plain = render_footer(src, plain=True)
    assert "normal" in plain


# ---- StatusSource new fields default to zero/False --------------------------

def test_status_source_shell_count_default():
    s = StatusSource()
    assert s.shell_count == 0


def test_status_source_is_inferring_default():
    s = StatusSource()
    assert s.is_inferring is False


def test_status_source_update_shell_count():
    s = StatusSource()
    s.update(shell_count=2)
    assert s.shell_count == 2


def test_status_source_update_is_inferring():
    s = StatusSource()
    s.update(is_inferring=True)
    assert s.is_inferring is True
