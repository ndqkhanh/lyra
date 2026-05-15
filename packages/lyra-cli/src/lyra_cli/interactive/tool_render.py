"""Tool-call rendering for the chat loop (Phase 1, OpenClaw-style tinted).

Replaces the previous inline render in :mod:`session` with a small,
testable module. The "tinted" style the user picked layers four signals
on every tool block:

* a left-edge gutter (``▎``) in the accent colour,
* a per-tool emoji + tool name on the title line,
* the tool args dimmed on a second line (when present),
* the output indented under a state-coloured block (pending /
  success / error background tint), with a ``+N lines (ctrl+o to
  expand)`` footer when truncated past :data:`PREVIEW_LINES`.

The flat Claude-Code style remains available via
``LYRA_TOOL_STYLE=flat`` for users who prefer the older look.
"""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass

from . import glyphs
from .palette import PALETTE


__all__ = [
    "PREVIEW_LINES",
    "ToolPaint",
    "format_tool_output",
    "paint_call",
    "paint_denied",
    "paint_limit",
    "paint_result",
    "tool_emoji",
]


# OpenClaw uses 12; lyra had 3 (too aggressive — users hit ctrl+o
# constantly). 8 is the compromise.
PREVIEW_LINES = int(os.environ.get("LYRA_TOOL_PREVIEW_LINES", "8") or 8)
MAX_LINE_WIDTH = 200

# Width of the gutter prefix in the tinted profile: "▎" + 4 spaces.
_GUTTER_PREFIX_WIDTH = 5


def _terminal_columns() -> int:
    """Best-effort terminal width; falls back to 80 when undetectable."""
    try:
        return shutil.get_terminal_size(fallback=(80, 24)).columns
    except (OSError, ValueError):
        return 80


def _gutter_body_width() -> int:
    """Columns available for body content after the gutter prefix.

    Floors at 20 so a tiny terminal still produces something readable;
    margin of 1 keeps Rich from ever auto-wrapping the line we hand it.
    """
    return max(20, _terminal_columns() - _GUTTER_PREFIX_WIDTH - 1)


def _hard_wrap_for_gutter(line: str, width: int) -> list[str]:
    """Hard-wrap a line at fixed width without respecting word boundaries.

    Tool output is mostly paths, URLs and JSON — content that has no
    whitespace to break on. Slicing at the column boundary is the only
    move that keeps the gutter alignment honest.
    """
    if width <= 0:
        return [line]
    if not line:
        return [""]
    if len(line) <= width:
        return [line]
    return [line[i : i + width] for i in range(0, len(line), width)]


# ── per-tool emoji table ────────────────────────────────────────


_EMOJI: dict[str, str] = {
    "Read":       "📖",
    "Write":      "📝",
    "Edit":       "✏️",
    "MultiEdit":  "✏️",
    "Bash":       "⚡",
    "Glob":       "🔍",
    "Grep":       "🔍",
    "WebFetch":   "🌐",
    "WebSearch":  "🌐",
    "Task":       "🤖",
    "TodoWrite":  "✅",
    "NotebookEdit": "📓",
}


def tool_emoji(tool_name: str) -> str:
    """Return the emoji for *tool_name*, falling through MCP prefixes.

    MCP tools come over the wire as ``mcp__<server>__<tool>`` —
    strip the prefix and try the suffix; otherwise hand back a
    generic wrench.
    """
    if tool_name in _EMOJI:
        return _EMOJI[tool_name]
    if tool_name.startswith("mcp__"):
        suffix = tool_name.rsplit("__", 1)[-1]
        if suffix in _EMOJI:
            return _EMOJI[suffix]
    return "🔧"


# ── output collapsing ───────────────────────────────────────────


def format_tool_output(
    output: str,
    *,
    max_lines: int = PREVIEW_LINES,
    max_line_width: int = MAX_LINE_WIDTH,
) -> tuple[str, str]:
    """Return ``(collapsed, full)`` — the same shape session.py used to
    return inline. Kept here so the tests can pin both halves.
    """
    full = output or ""
    if not full:
        return "(empty)", full
    lines = full.rstrip("\n").split("\n")
    shown: list[str] = []
    for ln in lines[:max_lines]:
        if len(ln) > max_line_width:
            ln = ln[: max_line_width - 1] + "…"
        shown.append(ln)
    remainder = len(lines) - max_lines
    if remainder > 0:
        shown.append(f"… +{remainder} lines (ctrl+o to expand)")
    return "\n".join(shown), full


# ── style profile ───────────────────────────────────────────────


def _style_profile() -> str:
    """``"flat"`` (Claude Code) or ``"tinted"`` (OpenClaw, default)."""
    val = (os.environ.get("LYRA_TOOL_STYLE") or "tinted").strip().lower()
    return "flat" if val == "flat" else "tinted"


# ── render output as Rich-markup-ready strings ──────────────────


@dataclass(frozen=True)
class ToolPaint:
    """A render product — a list of (Rich-markup, plain) line pairs.

    The chat loop prints the Rich-markup variant when a Console is
    available, and the plain variant otherwise (piped / test runs).
    Returning both pre-formatted keeps session.py free of palette-
    aware branching.
    """

    rich_lines: list[str]
    plain_lines: list[str]


def paint_call(tool_name: str, arg_preview: str) -> ToolPaint:
    """Render a tool-call header.

    Tinted: ``▎ <emoji> <Tool>  <args>``
    Flat:    ``⏺ <Tool>(<args>)``
    """
    accent = PALETTE["accent"]
    meta = PALETTE["meta"]

    if _style_profile() == "flat":
        rich = (
            f"[bold {accent}]{glyphs.ASSISTANT}[/] [bold]{tool_name}[/]"
            f"[{meta}]([/]{arg_preview}[{meta}])[/]"
        )
        plain = f"{glyphs.ASSISTANT} {tool_name}({arg_preview})"
        return ToolPaint(rich_lines=[rich], plain_lines=[plain])

    emoji = tool_emoji(tool_name)
    title = (
        f"[bold {accent}]▎[/] {emoji} [bold]{tool_name}[/]"
        + (f"  [{meta}]{arg_preview}[/]" if arg_preview else "")
    )
    plain_title = f"▎ {emoji} {tool_name}" + (
        f"  {arg_preview}" if arg_preview else ""
    )
    return ToolPaint(rich_lines=[title], plain_lines=[plain_title])


def paint_result(
    output: str,
    *,
    is_error: bool,
) -> tuple[ToolPaint, str]:
    """Render a tool-call result block. Returns ``(paint, full_output)``
    where ``full_output`` is the un-truncated string (so the caller can
    stash it for the ``Ctrl+O`` expand chord).
    """
    accent = PALETTE["accent"]
    meta = PALETTE["meta"]
    success_col = PALETTE["success"]
    error_col = PALETTE["error"]

    collapsed, full = format_tool_output(output)
    body_lines = collapsed.split("\n")

    if _style_profile() == "flat":
        if is_error:
            lead_rich = f"  [{error_col}]{glyphs.OUTPUT}[/]  [{error_col}]{glyphs.CROSS}[/] "
            lead_plain = f"  {glyphs.OUTPUT}  ✗ "
        else:
            lead_rich = f"  [{success_col}]{glyphs.OUTPUT}[/]  "
            lead_plain = f"  {glyphs.OUTPUT}  "
        first_rich = (
            f"{lead_rich}{body_lines[0]}"
            if is_error
            else f"{lead_rich}[{meta}]{body_lines[0]}[/]"
        )
        rich_lines = [first_rich]
        plain_lines = [f"{lead_plain}{body_lines[0]}"]
        for cont in body_lines[1:]:
            rich_lines.append(f"     [{meta}]{cont}[/]")
            plain_lines.append(f"     {cont}")
        return ToolPaint(rich_lines=rich_lines, plain_lines=plain_lines), full

    # Tinted profile — gutter on every line + status-coloured gutter
    gutter_color = error_col if is_error else accent
    gutter_rich = f"[bold {gutter_color}]▎[/]"
    gutter_plain = "▎"
    rich_lines: list[str] = [gutter_rich]
    plain_lines: list[str] = [gutter_plain]
    body_width = _gutter_body_width()
    for line in body_lines:
        for piece in _hard_wrap_for_gutter(line, body_width):
            rich_lines.append(f"{gutter_rich}    [{meta}]{piece}[/]")
            plain_lines.append(f"{gutter_plain}    {piece}")
    if is_error:
        rich_lines.append(
            f"{gutter_rich}    [bold {error_col}]{glyphs.CROSS} error[/]"
        )
        plain_lines.append(f"{gutter_plain}    {glyphs.CROSS} error")
    return ToolPaint(rich_lines=rich_lines, plain_lines=plain_lines), full


def paint_denied(tool_name: str, reason: str) -> ToolPaint:
    """One-line denial notice — same in both profiles."""
    warn = PALETTE["accent_warm"]
    rich = (
        f"  [{warn}]{glyphs.OUTPUT}[/]  [{warn}]denied:[/] {tool_name}"
        + (f" ({reason})" if reason else "")
    )
    plain = (
        f"  {glyphs.OUTPUT}  denied: {tool_name}"
        + (f" ({reason})" if reason else "")
    )
    return ToolPaint(rich_lines=[rich], plain_lines=[plain])


def paint_limit(reason: str) -> ToolPaint:
    """One-line tool-loop limit notice — same in both profiles."""
    warn = PALETTE["accent_warm"]
    rich = (
        f"  [{warn}]{glyphs.OUTPUT}[/]  [{warn}]tool-loop budget reached:[/] {reason}"
    )
    plain = f"  {glyphs.OUTPUT}  tool-loop budget reached: {reason}"
    return ToolPaint(rich_lines=[rich], plain_lines=[plain])
