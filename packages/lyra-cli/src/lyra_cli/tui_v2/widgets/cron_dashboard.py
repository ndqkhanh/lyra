"""CronDashboardWidget — TUI panel for tracking scheduled cron jobs.

Reads ~/.lyra/cron.json to show active, paused, and completed jobs.
Ctrl+Shift+C to toggle.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

CRON_PATH = Path.home() / ".lyra" / "cron.json"
JOB_GLYPH = {"active": "✓", "paused": "⏸", "failed": "✗", "completed": "◼"}
JOB_COLOR = {"active": "green", "paused": "yellow", "failed": "red", "completed": "dim"}


def _load_cron_jobs() -> list[dict]:
    if not CRON_PATH.exists():
        return []
    try:
        data = json.loads(CRON_PATH.read_text())
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("jobs", data.get("schedules", []))
    except Exception:
        return []
    return []


class CronDashboardWidget(Widget):
    """Scheduled job dashboard — Ctrl+Shift+C to toggle."""

    DEFAULT_CSS = """
    CronDashboardWidget {
        height: auto; border: solid $border; padding: 0 1; margin: 0 1;
    }
    CronDashboardWidget.collapsed { height: 1; border: none; }
    CronDashboardWidget #cron-header { height: 1; color: $text-muted; }
    CronDashboardWidget #cron-jobs { height: auto; max-height: 12; margin: 0 0 0 1; }
    """

    BINDINGS = [Binding("ctrl+shift+c", "toggle_cron", "Cron")]
    expanded: reactive[bool] = reactive(False)
    job_count: reactive[int] = reactive(0)

    def compose(self) -> ComposeResult:
        yield Static("", id="cron-header")
        yield Static("", id="cron-jobs")

    def on_mount(self) -> None:
        self._refresh()

    def _refresh(self) -> None:
        self.job_count = len(_load_cron_jobs())
        self._render()

    def action_toggle_cron(self) -> None:
        self.expanded = not self.expanded
        self.toggle_class("collapsed", not self.expanded)
        if self.expanded:
            self._refresh()

    def _render(self) -> None:
        if not self.is_mounted:
            return
        try:
            jobs = _load_cron_jobs()
            hint = "[dim](ctrl+shift+c)[/]"
            if self.expanded:
                self.query_one("#cron-header", Static).update(
                    f"[bold]Cron[/]  [green]{len(jobs)}[/] jobs  {hint}"
                )
                if not jobs:
                    self.query_one("#cron-jobs", Static).update("  [dim]No scheduled jobs[/]")
                else:
                    lines = []
                    for j in jobs[:10]:
                        name = j.get("name", j.get("description", "?"))[:30]
                        schedule = str(j.get("schedule", j.get("cron", "?")))[:20]
                        status = j.get("status", "active")
                        glyph = JOB_GLYPH.get(status, "○")
                        color = JOB_COLOR.get(status, "dim")
                        lines.append(f"  [{color}]{glyph}[/] {name:<30} [dim]{schedule}[/]")
                    if len(jobs) > 10:
                        lines.append(f"  [dim]… +{len(jobs) - 10} more[/]")
                    self.query_one("#cron-jobs", Static).update("\n".join(lines))
            else:
                act = sum(1 for j in jobs if j.get("status", "active") == "active")
                self.query_one("#cron-header", Static).update(
                    f"[bold]Cron[/]  "
                    f"[green]{act}[/] active  "
                    f"[dim]{len(jobs)} total[/]  {hint}"
                )
                self.query_one("#cron-jobs", Static).update("")
        except Exception:
            pass


__all__ = ["CronDashboardWidget"]
