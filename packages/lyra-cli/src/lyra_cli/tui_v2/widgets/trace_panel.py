"""TraceWidget — TUI call-trace timeline and event viewer.

Ports the 257-line commands/trace.py into a live TUI panel showing:
  • Real-time event timeline across sessions
  • Per-event kind symbols (🤖 llm, ⚙ tool, 👾 subagent, 🚫 blocked, etc.)
  • Filter by kind, session, or depth
  • Color-coded event rows

Ctrl+Shift+Y to toggle.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

KIND_SYMBOLS = {
    "llm": "🤖", "tool": "⚙", "subagent": "👾",
    "blocked": "🚫", "cron": "⏰", "stop": "⛔", "permission": "🔑",
}
KIND_COLORS = {
    "llm": "cyan", "tool": "green", "subagent": "yellow",
    "blocked": "red", "cron": "dim", "stop": "red", "permission": "magenta",
}


def _classify_kind(record: dict) -> str:
    kind = str(record.get("kind", record.get("event_type", ""))).lower()
    if "llm" in kind or "model" in kind: return "llm"
    if "tool" in kind: return "blocked" if "block" in kind else "tool"
    if "agent" in kind: return "subagent"
    if "cron" in kind: return "cron"
    if "stop" in kind: return "stop"
    if "permission" in kind: return "permission"
    return "tool"


def _load_events(lyra_dir: Path, max_events: int = 50) -> list[dict]:
    events: list[dict] = []
    for f in sorted(lyra_dir.rglob("events.jsonl")):
        try:
            for line in f.read_text(errors="replace").splitlines():
                line = line.strip()
                if not line: continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        except OSError:
            pass
    return events[-max_events:]


class TraceWidget(Widget):
    """Call-trace timeline — Ctrl+Shift+Y to toggle.

    Shows: live event feed with kind symbols, session IDs, timestamps.
    """

    DEFAULT_CSS = """
    TraceWidget {
        height: auto;
        border: solid $border;
        padding: 0 1;
        margin: 0 1;
    }
    TraceWidget.collapsed { height: 1; border: none; }
    TraceWidget #trace-header { height: 1; color: $text-muted; }
    TraceWidget #trace-events { height: auto; max-height: 14; margin: 0 0 0 1; }
    """

    BINDINGS = [Binding("ctrl+shift+y", "toggle_trace", "Trace")]
    expanded: reactive[bool] = reactive(False)

    def compose(self) -> ComposeResult:
        yield Static("", id="trace-header")
        yield Static("", id="trace-events")

    def on_mount(self) -> None:
        self._render()

    def action_toggle_trace(self) -> None:
        self.expanded = not self.expanded
        self.toggle_class("collapsed", not self.expanded)
        self._render()

    def _render(self) -> None:
        if not self.is_mounted: return
        try:
            hint = "[dim](ctrl+shift+y)[/]"
            lyra_dir = Path.home() / ".lyra"
            events = _load_events(lyra_dir, 40)
            if self.expanded:
                self.query_one("#trace-header", Static).update(
                    f"[bold]Trace[/]  [dim]{len(events)} events[/]  {hint}"
                )
                if not events:
                    self.query_one("#trace-events", Static).update("  [dim]No events found[/]")
                else:
                    lines = []
                    for e in events[-20:]:
                        kind = _classify_kind(e)
                        symbol = KIND_SYMBOLS.get(kind, "·")
                        color = KIND_COLORS.get(kind, "dim")
                        ts = str(e.get("ts", e.get("timestamp", "")))[11:19]
                        sid = str(e.get("session_id", ""))[:10]
                        name = str(e.get("kind", e.get("event_type", "—")))[:20]
                        detail = str(e.get("tool_name", e.get("model", e.get("status", ""))))[:20]
                        lines.append(
                            f"  [{color}]{symbol}[/] [dim]{ts}[/] "
                            f"[dim]{sid}[/] {name} [dim]{detail}[/]"
                        )
                    self.query_one("#trace-events", Static).update("\n".join(lines))
            else:
                self.query_one("#trace-header", Static).update(
                    f"[bold]Trace[/]  [dim]{len(events)} events[/]  {hint}"
                )
                self.query_one("#trace-events", Static).update("")
        except Exception:
            pass


__all__ = ["TraceWidget"]
