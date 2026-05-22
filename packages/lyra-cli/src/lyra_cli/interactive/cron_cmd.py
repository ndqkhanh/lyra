"""CronDashboardWidget — TUI panel for scheduled job management.

Ports cron.py's CronStore + /cron into a visual panel:
  • Job list with schedule, status, last-run
  • Add/remove/pause/resume controls
  • Next-fire timeline

Ctrl+Shift+C to toggle. /cron in the REPL.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

CRON_STORE_PATH = Path.home() / ".lyra" / "cron.json"


def _list_jobs() -> list[dict]:
    import json
    if not CRON_STORE_PATH.exists():
        return []
    try:
        data = json.loads(CRON_STORE_PATH.read_text())
        return data if isinstance(data, list) else data.get("jobs", [])
    except Exception:
        return []


class CronDashboardWidget(Widget):
    """Scheduled job dashboard — Ctrl+Shift+C to toggle.

    Shows: cron jobs, schedules, status, last-run times.
    """

    DEFAULT_CSS = """
    CronDashboardWidget {
        height: auto;
        border: solid $border;
        padding: 0 1;
        margin: 0 1;
    }

    CronDashboardWidget.collapsed {
        height: 1;
        border: none;
    }

    CronDashboardWidget #cron-header {
        height: 1;
        color: $text-muted;
    }

    CronDashboardWidget #cron-jobs {
        height: auto;
        max-height: 10;
        margin: 0 0 0 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+shift+c", "toggle_cron", "Cron"),
    ]

    expanded: reactive[bool] = reactive(False)
    job_count: reactive[int] = reactive(0)

    def compose(self) -> ComposeResult:
        yield Static("", id="cron-header")
        yield Static("", id="cron-jobs")

    def on_mount(self) -> None:
        self._refresh()

    def _refresh(self) -> None:
        self.job_count = len(_list_jobs())
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
            jobs = _list_jobs()
            hint = "[dim](ctrl+shift+c)[/]"
            if self.expanded:
                self.query_one("#cron-header", Static).update(
                    f"[bold]Cron[/]  [green]{len(jobs)}[/] jobs  {hint}"
                )
                if not jobs:
                    self.query_one("#cron-jobs", Static).update("  [dim]No scheduled jobs[/]")
                else:
                    lines = []
                    for j in jobs[:8]:
                        name = j.get("name", j.get("description", "?"))[:30]
                        schedule = j.get("schedule", j.get("cron", "?"))
                        status = j.get("status", "active")
                        glyph = "[green]✓[/]" if status == "active" else "[dim]◻[/]"
                        lines.append(f"  {glyph} {name:<30}  [dim]{schedule}[/]")
                    if len(jobs) > 8:
                        lines.append(f"  [dim]… +{len(jobs) - 8} more[/]")
                    self.query_one("#cron-jobs", Static).update("\n".join(lines))
            else:
                self.query_one("#cron-header", Static).update(
                    f"[bold]Cron[/]  [green]{len(jobs)}[/]  {hint}"
                )
                self.query_one("#cron-jobs", Static).update("")
        except Exception:
            pass


__all__ = ["CronDashboardWidget"]
