"""Task progress indicators with checkbox-style display.

Provides Claude Code-style task progress with ◻ (pending), ◼ (in progress), ✓ (completed).
"""
from __future__ import annotations

from typing import Literal


TaskStatus = Literal["pending", "in_progress", "completed"]


def format_task_checkbox(status: TaskStatus) -> str:
    """Get checkbox icon for task status.

    Args:
        status: Task status

    Returns:
        Unicode checkbox character
    """
    return {
        "pending": "◻",
        "in_progress": "◼",
        "completed": "✓",
    }[status]


def format_task_item(
    name: str,
    status: TaskStatus,
    depth: int = 0,
    show_glyph: bool = True,
) -> str:
    """Format a single task item with checkbox.

    Example outputs:
        ⎿  ◻ Phase 1: Setup
        ⎿  ◼ Phase 2: Implementation
        ⎿  ✓ Phase 3: Testing

    Args:
        name: Task name/description
        status: Task status
        depth: Indentation depth (0 = root)
        show_glyph: Whether to show the ⎿ glyph

    Returns:
        Formatted task line with Rich markup
    """
    indent = "  " * depth
    glyph = "⎿  " if show_glyph else ""
    checkbox = format_task_checkbox(status)

    # Color based on status
    color = {
        "pending": "dim",
        "in_progress": "yellow",
        "completed": "green",
    }[status]

    return f"{indent}{glyph}[{color}]{checkbox} {name}[/]"


def format_task_progress(
    tasks: list[dict],
    max_visible: int = 5,
    show_remaining: bool = True,
) -> str:
    """Format task progress list with checkboxes.

    Example output:
        ⎿  ◻ Phase 9: Production Readiness
           ◻ Phase 3: Implement Research Pipeline
           ◼ Phase 6: Interactive UI & Themes
           ✓ Phase 5: Memory Systems
           ✓ Phase 2: Integrate Real Agent Loop
            … +3 pending

    Args:
        tasks: List of task dicts with 'name', 'status', and optional 'depth'
        max_visible: Maximum number of tasks to show
        show_remaining: Whether to show "+N pending" for hidden tasks

    Returns:
        Multi-line formatted task list
    """
    lines = []

    for i, task in enumerate(tasks[:max_visible]):
        name = task.get("name", "Unknown task")
        status = task.get("status", "pending")
        depth = task.get("depth", 0)
        show_glyph = i == 0  # Only first item gets the glyph

        lines.append(format_task_item(name, status, depth, show_glyph))

    # Show remaining count
    remaining = len(tasks) - max_visible
    if show_remaining and remaining > 0:
        lines.append(f"     [dim]… +{remaining} pending[/]")

    return "\n".join(lines)


def format_task_summary(
    total: int,
    completed: int,
    in_progress: int,
) -> str:
    """Format task summary line.

    Example: "5 tasks: 2 done, 1 in progress, 2 pending"

    Args:
        total: Total number of tasks
        completed: Number of completed tasks
        in_progress: Number of in-progress tasks

    Returns:
        Formatted summary string
    """
    pending = total - completed - in_progress

    parts = [f"{total} tasks:"]

    if completed > 0:
        parts.append(f"[green]{completed} done[/]")
    if in_progress > 0:
        parts.append(f"[yellow]{in_progress} in progress[/]")
    if pending > 0:
        parts.append(f"[dim]{pending} pending[/]")

    return " ".join(parts)


__all__ = [
    "TaskStatus",
    "format_task_checkbox",
    "format_task_item",
    "format_task_progress",
    "format_task_summary",
]
