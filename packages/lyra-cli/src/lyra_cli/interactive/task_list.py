"""Sub-task checklist renderer — Claude Code style.

Renders the ``⎿ ◻ Phase N: description`` checklist that appears below
the spinner during multi-step agent work. Pure functions — no I/O, no
Textual dependency — so they can feed both the REPL bottom_toolbar and
the TUI status widget.

Layout:
    ⎿  ◻ Phase 3: Implement Research Pipeline  ← first item (connector)
       ◻ Phase 6: Interactive UI & Themes       ← subsequent items
       ◼ Phase 2: Integrate Real Agent Loop     ← running (filled square)
       ✓ Phase 1: Setup                         ← done
        … +3 pending                            ← overflow collapse
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .status_source import TaskItem

_MAX_VISIBLE: int = 5

_STATE_GLYPH: dict[str, str] = {
    "pending": "◻",
    "running": "◼",
    "done":    "✓",
}

_INDENT_FIRST = "  ⎿  "
_INDENT_REST  = "     "


def render_checklist(tasks: "list[TaskItem]", *, max_visible: int = _MAX_VISIBLE) -> list[str]:
    """Return plain-text lines for the task checklist.

    Args:
        tasks: Snapshot of the current task list (use ``StatusSource.snapshot_tasks()``).
        max_visible: Maximum number of task lines to show before collapsing.

    Returns:
        List of strings, one per display line (no trailing newlines).
        Returns ``[]`` when ``tasks`` is empty.
    """
    if not tasks:
        return []

    visible = tasks[:max_visible]
    hidden = len(tasks) - len(visible)

    lines: list[str] = []
    for i, task in enumerate(visible):
        glyph = _STATE_GLYPH.get(task.state, "◻")
        prefix = _INDENT_FIRST if i == 0 else _INDENT_REST
        lines.append(f"{prefix}{glyph} {task.description}")

    if hidden > 0:
        lines.append(f"{_INDENT_REST} … +{hidden} pending")

    return lines


def render_checklist_text(tasks: "list[TaskItem]", *, max_visible: int = _MAX_VISIBLE) -> str:
    """Convenience wrapper — join ``render_checklist`` output into a single string."""
    return "\n".join(render_checklist(tasks, max_visible=max_visible))


__all__ = ["render_checklist", "render_checklist_text"]
