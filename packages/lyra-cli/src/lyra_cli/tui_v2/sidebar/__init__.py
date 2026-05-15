"""Lyra-specific sidebar tabs for the harness-tui shell.

harness-tui's Sidebar ships three defaults (Sessions, Todos, Agents);
Lyra adds Plans, Skills, MCP, Memory — surfaces a user wants visible
without typing a slash command. Each tab is a small ``Static`` widget
backed by a pure helper, so the data layer is unit-testable without
mounting Textual.

Tabs auto-refresh every ``REFRESH_SECONDS`` so filesystem changes
(``lyra plan``, ``/skill`` edits, MCP config tweaks) appear without
the user toggling the sidebar.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

REFRESH_SECONDS = 5.0


__all__ = [
    "REFRESH_SECONDS",
    "build_lyra_sidebar_tabs",
]


def build_lyra_sidebar_tabs(working_dir: str | Path) -> list[tuple[str, Any]]:
    """Return ``(label, widget)`` pairs for the four Lyra sidebar tabs.

    Constructed lazily — importing this package does NOT instantiate
    Textual widgets, so the surface is safe to import from non-TUI
    callers (CLI smoke tests, type checkers, doctor probes).
    """
    from .agents_tab import AgentsTab
    from .tabs import McpTab, MemoryTab, PlansTab, SkillsTab

    root = Path(working_dir).resolve()
    return [
        ("Plans", PlansTab(root)),
        ("Skills", SkillsTab(root)),
        ("MCP", McpTab(root)),
        ("Memory", MemoryTab(root)),
        ("Agents", AgentsTab()),
    ]
