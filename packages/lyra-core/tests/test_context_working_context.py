"""Tests for ``WORKING-CONTEXT.md`` (Phase CE.2, P1-4)."""
from __future__ import annotations

from pathlib import Path

import pytest

from lyra_core.context.working_context import (
    DEFAULT_CAP_BYTES,
    DEFAULT_RELATIVE_PATH,
    WorkingContext,
    read_working_context,
    render,
    render_for_context_layer,
    reset_working_context,
    resolve_path,
    write_working_context,
)


# ────────────────────────────────────────────────────────────────
# Roundtrip
# ────────────────────────────────────────────────────────────────


def test_roundtrip_through_markdown():
    wc = WorkingContext(
        current_task="ship Phase CE.2",
        plan_summary="walk the items; test each; ship.",
        todo_lines=["finish P1-4", "run full suite", "ship"],
        blocking_questions=["what should P1-3 do when distiller fails?"],
        last_commit="abc1234",
        branch="phase-ce-2",
    )
    md = wc.to_markdown()
    parsed = WorkingContext.from_markdown(md)
    assert parsed.current_task == wc.current_task
    assert parsed.plan_summary == wc.plan_summary
    assert parsed.todo_lines == wc.todo_lines
    assert parsed.blocking_questions == wc.blocking_questions
    assert parsed.last_commit == wc.last_commit
    assert parsed.branch == wc.branch


def test_empty_object_renders_minimal_header():
    md = WorkingContext().to_markdown()
    assert md.strip() == "# WORKING CONTEXT"


def test_from_markdown_handles_empty_string():
    wc = WorkingContext.from_markdown("")
    assert wc.current_task == ""
    assert wc.todo_lines == []


def test_from_markdown_ignores_unknown_section():
    md = "# WORKING CONTEXT\n\n## Mystery\n- a\n- b\n\n## Current task\nedit X\n"
    wc = WorkingContext.from_markdown(md)
    assert wc.current_task == "edit X"


# ────────────────────────────────────────────────────────────────
# Rendering and cap-trimming
# ────────────────────────────────────────────────────────────────


def test_render_under_cap_returns_full_body():
    wc = WorkingContext(
        current_task="small task",
        todo_lines=["one", "two"],
    )
    out = render(wc, cap_bytes=DEFAULT_CAP_BYTES)
    assert "small task" in out
    assert "one" in out and "two" in out


def test_render_trims_blocking_questions_first():
    wc = WorkingContext(
        current_task="keep me",
        todo_lines=["a", "b"],
        blocking_questions=[f"q-{i} " + "x" * 60 for i in range(20)],
    )
    out = render(wc, cap_bytes=320)
    assert "keep me" in out
    # At least some blocking questions got dropped.
    surviving = sum(1 for line in out.splitlines() if line.startswith("- q-"))
    assert surviving < 20


def test_render_trims_todos_after_blocking_exhausted():
    wc = WorkingContext(
        current_task="task",
        todo_lines=[f"todo-{i} " + "x" * 60 for i in range(20)],
        blocking_questions=[],
    )
    out = render(wc, cap_bytes=200)
    todo_lines = [line for line in out.splitlines() if line.startswith("- todo-")]
    assert len(todo_lines) < 20
    assert "task" in out


def test_render_truncates_plan_when_everything_else_gone():
    wc = WorkingContext(
        current_task="t",
        plan_summary="plan " * 500,
    )
    out = render(wc, cap_bytes=200)
    assert len(out.encode("utf-8")) <= 200
    assert "t" in out


def test_render_requires_positive_cap():
    with pytest.raises(ValueError):
        render(WorkingContext(current_task="x"), cap_bytes=0)


def test_render_for_context_layer_wraps_in_marker():
    out = render_for_context_layer(WorkingContext(current_task="x"))
    assert out.startswith("<working-context>")
    assert out.rstrip().endswith("</working-context>")


# ────────────────────────────────────────────────────────────────
# Disk I/O
# ────────────────────────────────────────────────────────────────


def test_resolve_path_default():
    assert resolve_path(Path("/tmp/repo")) == Path("/tmp/repo") / DEFAULT_RELATIVE_PATH


def test_read_missing_file_returns_empty(tmp_path: Path):
    wc = read_working_context(tmp_path)
    assert wc.current_task == ""
    assert wc.todo_lines == []


def test_write_and_read_round_trip(tmp_path: Path):
    wc = WorkingContext(
        current_task="ship feature X",
        todo_lines=["a", "b"],
        branch="feat/x",
    )
    written = write_working_context(tmp_path, wc)
    assert written.is_file()
    assert written.parent.name == ".lyra"
    loaded = read_working_context(tmp_path)
    assert loaded.current_task == wc.current_task
    assert loaded.todo_lines == wc.todo_lines
    assert loaded.branch == "feat/x"


def test_write_respects_cap(tmp_path: Path):
    wc = WorkingContext(
        current_task="t",
        plan_summary="x" * 4000,
    )
    write_working_context(tmp_path, wc, cap_bytes=200)
    body = (tmp_path / DEFAULT_RELATIVE_PATH).read_text(encoding="utf-8")
    assert len(body.encode("utf-8")) <= 200


def test_reset_removes_existing_file(tmp_path: Path):
    write_working_context(tmp_path, WorkingContext(current_task="x"))
    assert reset_working_context(tmp_path) is True
    assert reset_working_context(tmp_path) is False


def test_write_is_atomic_no_leftover_tmp(tmp_path: Path):
    write_working_context(tmp_path, WorkingContext(current_task="hi"))
    parent = tmp_path / DEFAULT_RELATIVE_PATH.parent
    tmps = list(parent.glob("*.tmp"))
    assert tmps == []
