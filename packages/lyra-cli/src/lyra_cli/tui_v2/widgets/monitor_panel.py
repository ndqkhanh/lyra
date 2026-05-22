"""TUI Monitor Widget — operator fleet view with attention priority.

Bridges the REPL's ``/monitor`` command (``monitor.py``) into a TUI panel.
Shows active sessions grouped by attention priority (P0–P3), with live
status, model info, turn count, and cost.

Pairs with Ctrl+M for quick fleet health checks.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

# Priority definitions (from interactive/monitor.py)
_PRIORITY_GROUPS: list[tuple[str, str, str, frozenset[str]]] = [
    ("P0 Needs Attention",  "🔴", "red",    frozenset({"needs_input", "failed"})),
    ("P1 Ready for Review", "🟡", "yellow", frozenset({"ready_for_review"})),
    ("P2 Working",          "🔵", "cyan",   frozenset({"working"})),
    ("P3 Completed",        "✅", "green",  frozenset({"completed"})),
]


def _priority_for(state: str) -> tuple[str, str, str]:
    for label, emoji, color, states in _PRIORITY_GROUPS:
        if state in states:
            return label, emoji, color
    return "Unknown", "❓", "dim"


class MonitorWidget(Widget):
    """Operator fleet view — sessions grouped by attention priority.

    Ctrl+M to toggle. Shows all tracked sessions with their current
    state, model, turn count, and cost.
    """

    DEFAULT_CSS = """
    MonitorWidget {
        height: auto;
        border: solid $border;
        padding: 0 1;
        margin: 0 1;
    }

    MonitorWidget.collapsed {
        height: 1;
        border: none;
    }

    MonitorWidget #mon-header {
        height: 1;
        color: $text-muted;
    }

    MonitorWidget #mon-content {
        height: auto;
        max-height: 16;
        margin: 0 0 0 1;
    }

    MonitorWidget .mon-priority {
        text-style: bold;
        margin: 0 0 1 0;
    }

    MonitorWidget .mon-session {
        height: 1;
    }

    MonitorWidget .mon-empty {
        color: dim;
    }
    """

    BINDINGS = [
        Binding("ctrl+m", "toggle_monitor", "Monitor"),
    ]

    expanded: reactive[bool] = reactive(False)
    session_count: reactive[int] = reactive(0)

    def __init__(self):
        super().__init__()
        self._sessions_dir = Path.home() / ".lyra" / "sessions"

    def compose(self) -> ComposeResult:
        yield Static("", id="mon-header")
        yield Static("", id="mon-content")

    def on_mount(self) -> None:
        self._render()

    # ── Public API ─────────────────────────────────────────────────────

    def refresh_sessions(self) -> None:
        """Re-read session files from disk."""
        self._render()

    @property
    def sessions(self) -> list[dict[str, Any]]:
        if not self._sessions_dir.is_dir():
            return []
        sessions: list[dict[str, Any]] = []
        for f in sorted(self._sessions_dir.glob("*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    sessions.append(data)
            except Exception:
                pass
        return sessions

    # ── Actions ────────────────────────────────────────────────────────

    def action_toggle_monitor(self) -> None:
        self.expanded = not self.expanded
        self.toggle_class("collapsed", not self.expanded)
        self._render()

    # ── Internal ───────────────────────────────────────────────────────

    def _render(self) -> None:
        if not self.is_mounted:
            return
        try:
            self._render_header()
            self._render_content()
        except Exception:
            pass

    def _render_header(self) -> None:
        all_sessions = self.sessions
        self.session_count = len(all_sessions)

        hint = "[dim](ctrl+m)[/]"
        if self.expanded:
            self.query_one("#mon-header", Static).update(
                f"[bold]Monitor[/]  [dim]{len(all_sessions)} sessions[/]  {hint}"
            )
        else:
            # Count by priority for collapsed state
            by_priority: dict[str, int] = {}
            for s in all_sessions:
                state = str(s.get("state", s.get("status", "")))
                label, _, _ = _priority_for(state)
                by_priority[label] = by_priority.get(label, 0) + 1

            status_parts = []
            for label, emoji, _, states in _PRIORITY_GROUPS:
                count = by_priority.get(label, 0)
                if count > 0:
                    status_parts.append(f"{emoji} {count}")
            status_str = " ".join(status_parts) if status_parts else "[dim]no sessions[/]"

            self.query_one("#mon-header", Static).update(
                f"[bold]Monitor[/]  {status_str}  {hint}"
            )

    def _render_content(self) -> None:
        if not self.expanded:
            self.query_one("#mon-content", Static).update("")
            return

        all_sessions = self.sessions
        if not all_sessions:
            self.query_one("#mon-content", Static).update(
                "  [dim]No sessions tracked yet.[/]"
            )
            return

        # Group by priority
        grouped: list[list[dict[str, Any]]] = [[] for _ in _PRIORITY_GROUPS]
        for s in all_sessions:
            state = str(s.get("state", s.get("status", "")))
            for idx, (_, _, _, states) in enumerate(_PRIORITY_GROUPS):
                if state in states:
                    grouped[idx].append(s)
                    break
            else:
                grouped.append([s])  # uncategorized

        lines: list[str] = []
        for idx, (label, emoji, color, _) in enumerate(_PRIORITY_GROUPS):
            group = grouped[idx]
            if not group:
                continue
            lines.append(f"  [{color}]{emoji} {label}[/] ({len(group)})")
            for s in group[:5]:  # max 5 per group
                sid = str(s.get("session_id", "?"))[:12]
                model = str(s.get("model", "?"))[:16]
                turns = s.get("turn", s.get("turns", "?"))
                cost = float(s.get("cost_usd", 0))
                state = str(s.get("state", s.get("status", "")))
                lines.append(
                    f"    [dim]{sid}[/]  {model}  "
                    f"[dim]T#{turns}[/]  [dim]${cost:.4f}[/]  "
                    f"[dim]{state}[/]"
                )
            if len(group) > 5:
                lines.append(f"    [dim]… +{len(group) - 5} more[/]")
            lines.append("")

        self.query_one("#mon-content", Static).update("\n".join(lines))
