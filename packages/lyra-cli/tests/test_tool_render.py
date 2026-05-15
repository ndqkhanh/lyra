"""Pin tests for the tinted/flat tool render module (Phase 1)."""
from __future__ import annotations

from typing import Any

from lyra_cli.interactive import tool_render
from lyra_cli.interactive.tool_render import (
    PREVIEW_LINES,
    format_tool_output,
    paint_call,
    paint_denied,
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
