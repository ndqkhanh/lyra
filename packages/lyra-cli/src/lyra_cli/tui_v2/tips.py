"""Contextual tip system for Lyra TUI.

Provides helpful hints to users based on the current context or operation.
Tips are displayed in Claude Code style with the ⎿ glyph.
"""
from __future__ import annotations

import random
from typing import Literal

TipContext = Literal[
    "compaction",
    "long_operation",
    "background_task",
    "tool_execution",
    "error",
    "idle",
]

TIPS: dict[TipContext, list[str]] = {
    "compaction": [
        "Use /btw to add context for the next turn",
        "Press Ctrl+O to view full compaction history",
        "Context compaction preserves recent turns and summarizes older ones",
    ],
    "long_operation": [
        "Press Ctrl+B to move this operation to background",
        "Use /btw to ask a quick side question without interrupting",
        "Press Ctrl+C to cancel the current operation",
    ],
    "background_task": [
        "Press Ctrl+T to view all background tasks",
        "Background tasks continue while you work on other things",
        "You'll be notified when background tasks complete",
    ],
    "tool_execution": [
        "Press Ctrl+O to expand tool output details",
        "Tools are executed in isolated environments for safety",
        "Use /tools to see all available tools",
    ],
    "error": [
        "Use /debug mode for detailed error investigation",
        "Check /status for current session state",
        "Try /rollback to undo recent changes",
    ],
    "idle": [
        "Press Ctrl+K to open the command palette",
        "Use /help to see all available commands",
        "Press Shift+Tab to cycle between modes (agent/plan/debug/ask)",
    ],
}


def get_tip(context: TipContext = "idle") -> str:
    """Get a random tip for the given context.

    Args:
        context: The current context (compaction, long_operation, etc.)

    Returns:
        Formatted tip string with Rich markup
    """
    tips = TIPS.get(context, TIPS["idle"])
    tip_text = random.choice(tips)
    return f"[dim]⎿[/] Tip: {tip_text}"


__all__ = ["TipContext", "get_tip", "TIPS"]
