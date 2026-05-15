"""Pin tests for the tinted/flat tool render module (Phase 1)."""
from __future__ import annotations

from typing import Any

from lyra_cli.interactive import tool_render
from lyra_cli.interactive.tool_render import (
    PREVIEW_LINES,
    format_tool_output,
    is_file_tool,
    paint_call,
    paint_denied,
    paint_file_call,
    paint_file_result,
    paint_limit,
    paint_result,
    tool_emoji,
)


# ── tool_emoji ──────────────────────────────────────────────────


def test_tool_emoji_known_tool() -> None:
    assert tool_emoji("Read") == "📖"
    assert tool_emoji("Bash") == "⚡"
    assert tool_emoji("Grep") == "🔍"


def test_tool_emoji_mcp_prefix_falls_through() -> None:
    """``mcp__server__Read`` should still get the Read emoji."""
    assert tool_emoji("mcp__github__Read") == "📖"


def test_tool_emoji_unknown_returns_wrench() -> None:
    assert tool_emoji("MysteriousFranchise") == "🔧"


# ── format_tool_output ──────────────────────────────────────────


def test_format_tool_output_collapses_past_max() -> None:
    text = "\n".join(f"line {i}" for i in range(20))
    collapsed, full = format_tool_output(text, max_lines=3)
    assert collapsed.count("\n") == 3  # 3 body + 1 footer
    assert "+17 lines (ctrl+o to expand)" in collapsed
    assert full == text


def test_format_tool_output_uses_default_8_lines_preview() -> None:
    """Default preview must be 8 lines (compromise vs OpenClaw's 12 / our old 3)."""
    assert PREVIEW_LINES == 8


def test_format_tool_output_clips_long_single_line() -> None:
    text = "x" * 500
    collapsed, _ = format_tool_output(text, max_line_width=50)
    first = collapsed.split("\n")[0]
    assert len(first) == 50
    assert first.endswith("…")


def test_format_tool_output_empty_falls_back_to_placeholder() -> None:
    collapsed, full = format_tool_output("")
    assert collapsed == "(empty)"
    assert full == ""


# ── style profile ──────────────────────────────────────────────


def test_default_style_is_tinted(monkeypatch: Any) -> None:
    monkeypatch.delenv("LYRA_TOOL_STYLE", raising=False)
    paint = paint_call("Read", "auth.py")
    # Tinted profile uses the gutter glyph + emoji; flat does not.
    rich = paint.rich_lines[0]
    plain = paint.plain_lines[0]
    assert "▎" in rich
    assert "📖" in plain


def test_flat_style_uses_claude_code_bullet(monkeypatch: Any) -> None:
    monkeypatch.setenv("LYRA_TOOL_STYLE", "flat")
    paint = paint_call("Read", "auth.py")
    rich = paint.rich_lines[0]
    assert "⏺" in rich
    # And no gutter
    assert "▎" not in rich


# ── paint_call ─────────────────────────────────────────────────


def test_paint_call_includes_tool_name(monkeypatch: Any) -> None:
    monkeypatch.delenv("LYRA_TOOL_STYLE", raising=False)
    paint = paint_call("Bash", "ls -la")
    assert "Bash" in paint.plain_lines[0]
    assert "ls -la" in paint.plain_lines[0]


def test_paint_call_handles_empty_args(monkeypatch: Any) -> None:
    """No double-space, no trailing parens — args truly empty."""
    monkeypatch.delenv("LYRA_TOOL_STYLE", raising=False)
    paint = paint_call("Read", "")
    assert paint.plain_lines[0].rstrip().endswith("Read")


# ── paint_result ────────────────────────────────────────────────


def test_paint_result_success_in_tinted_uses_accent_gutter(
    monkeypatch: Any,
) -> None:
    monkeypatch.delenv("LYRA_TOOL_STYLE", raising=False)
    paint, full = paint_result("hello world", is_error=False)
    # First line is the bare gutter, body lines follow with indent
    assert paint.plain_lines[0] == "▎"
    assert any("hello world" in line for line in paint.plain_lines[1:])
    assert full == "hello world"


def test_paint_result_error_appends_cross_marker(monkeypatch: Any) -> None:
    monkeypatch.delenv("LYRA_TOOL_STYLE", raising=False)
    paint, _ = paint_result("permission denied", is_error=True)
    assert any("✗ error" in line for line in paint.plain_lines)


def test_paint_result_flat_has_no_gutter(monkeypatch: Any) -> None:
    monkeypatch.setenv("LYRA_TOOL_STYLE", "flat")
    paint, _ = paint_result("ok\n", is_error=False)
    rich = "\n".join(paint.rich_lines)
    assert "▎" not in rich
    assert "⎿" in rich


def test_paint_result_returns_full_output_for_ctrl_o() -> None:
    """The Ctrl+O expand chord stashes the second tuple element."""
    body = "\n".join(f"l{i}" for i in range(50))
    _, full = paint_result(body, is_error=False)
    assert full == body


def test_paint_result_wraps_long_path_preserving_gutter(
    monkeypatch: Any,
) -> None:
    """Regression: long paths (e.g. .venv/site-packages) used to wrap
    in Rich and strip the leading ``▎`` on the wrapped continuation.
    Hard-wrap before render so every visual line has the gutter.
    """
    monkeypatch.delenv("LYRA_TOOL_STYLE", raising=False)
    # Force a narrow terminal so the hard-wrap path is exercised.
    # Patch the module-level helper, not shutil, so pytest's own
    # width detection keeps working.
    monkeypatch.setattr(tool_render, "_terminal_columns", lambda: 60)
    long_path = (
        "projects/aegis-ops/.venv/lib/python3.11/site-packages/"
        "fastapi/.agents/skills/fastapi/SKILL.md"
    )
    paint, _ = paint_result(long_path, is_error=False)
    # Every plain line after the leading gutter-only line must start with ▎.
    body_lines = paint.plain_lines[1:]
    assert body_lines, "expected at least one body line"
    for line in body_lines:
        assert line.startswith("▎"), f"line lost its gutter: {line!r}"
    # And the path was split across multiple body lines, not truncated.
    joined = "".join(line.removeprefix("▎    ") for line in body_lines)
    assert long_path in joined


# ── paint_denied + paint_limit ─────────────────────────────────


def test_paint_denied_includes_tool_and_reason() -> None:
    paint = paint_denied("Bash", "destructive")
    line = paint.plain_lines[0]
    assert "Bash" in line and "destructive" in line and "denied" in line


def test_paint_limit_includes_reason() -> None:
    paint = paint_limit("max-tool-calls")
    assert "max-tool-calls" in paint.plain_lines[0]


# ── is_file_tool ───────────────────────────────────────────────


def test_is_file_tool_edit_write_multiedit() -> None:
    assert is_file_tool("Edit")
    assert is_file_tool("Write")
    assert is_file_tool("MultiEdit")


def test_is_file_tool_false_for_read_bash() -> None:
    assert not is_file_tool("Read")
    assert not is_file_tool("Bash")
    assert not is_file_tool("Grep")


# ── paint_file_call ────────────────────────────────────────────


def test_paint_file_call_edit_uses_update_verb() -> None:
    paint = paint_file_call("Edit", "src/foo.py")
    line = paint.plain_lines[0]
    assert "Update" in line
    assert "src/foo.py" in line
    # Claude Code bullet
    assert "⏺" in line


def test_paint_file_call_write_uses_write_verb() -> None:
    paint = paint_file_call("Write", "src/new.py")
    assert "Write" in paint.plain_lines[0]
    assert "src/new.py" in paint.plain_lines[0]


def test_paint_file_call_multiedit_uses_update_verb() -> None:
    paint = paint_file_call("MultiEdit", "src/bar.py")
    assert "Update" in paint.plain_lines[0]


def test_paint_file_call_rich_contains_bullet() -> None:
    paint = paint_file_call("Edit", "src/foo.py")
    assert "⏺" in paint.rich_lines[0]


# ── paint_file_result ──────────────────────────────────────────


def test_paint_file_result_edit_stat_line_added() -> None:
    args = {"path": "src/foo.py", "old": "x = 1\n", "new": "x = 1\ny = 2\n"}
    paint, _ = paint_file_result("Edit", args, "edited src/foo.py (1 replacement)", is_error=False)
    stat_line = paint.plain_lines[0]
    assert "⎿" in stat_line
    assert "Added" in stat_line


def test_paint_file_result_edit_stat_line_removed() -> None:
    args = {"path": "src/foo.py", "old": "x = 1\ny = 2\n", "new": "x = 1\n"}
    paint, _ = paint_file_result("Edit", args, "edited src/foo.py (1 replacement)", is_error=False)
    stat_line = paint.plain_lines[0]
    assert "Removed" in stat_line


def test_paint_file_result_edit_shows_plus_lines() -> None:
    args = {"path": "src/foo.py", "old": "a\n", "new": "a\nb\n"}
    paint, _ = paint_file_result("Edit", args, "ok", is_error=False)
    body = "\n".join(paint.plain_lines[1:])
    assert "+" in body


def test_paint_file_result_edit_shows_minus_lines() -> None:
    args = {"path": "src/foo.py", "old": "a\nb\n", "new": "a\n"}
    paint, _ = paint_file_result("Edit", args, "ok", is_error=False)
    body = "\n".join(paint.plain_lines[1:])
    assert "-" in body


def test_paint_file_result_write_stat_says_wrote() -> None:
    args = {"path": "src/new.py", "content": "line1\nline2\nline3\n"}
    paint, _ = paint_file_result("Write", args, "wrote src/new.py (30 bytes)", is_error=False)
    stat_line = paint.plain_lines[0]
    assert "Wrote" in stat_line
    assert "3 lines" in stat_line


def test_paint_file_result_error_falls_through_to_paint_result() -> None:
    args = {"path": "src/foo.py", "old": "x", "new": "y"}
    paint, _ = paint_file_result("Edit", args, "edit failed: not found", is_error=True)
    # paint_result error format: has ✗ error marker
    assert any("✗ error" in ln for ln in paint.plain_lines)


def test_paint_file_result_no_change_shows_no_changes() -> None:
    args = {"path": "src/foo.py", "old": "same\n", "new": "same\n"}
    paint, _ = paint_file_result("Edit", args, "ok", is_error=False)
    assert "No changes" in paint.plain_lines[0]


def test_paint_file_result_truncates_at_preview_lines() -> None:
    big_new = "\n".join(f"line {i}" for i in range(50))
    args = {"path": "src/foo.py", "old": "", "new": big_new}
    paint, _ = paint_file_result("Edit", args, "ok", is_error=False, preview_lines=5)
    assert any("more lines" in ln for ln in paint.plain_lines)


def test_paint_file_result_returns_full_output_for_ctrl_o() -> None:
    args = {"path": "src/foo.py", "old": "x\n", "new": "y\n"}
    _, full = paint_file_result("Edit", args, "edited src/foo.py", is_error=False)
    assert isinstance(full, str)
