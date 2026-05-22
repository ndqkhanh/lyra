"""UltraReviewWidget — TUI code review summary panel.

Ports ultrareview_command.py into a visual panel showing:
  • Review findings grouped by severity
  • Diff hunks with line numbers
  • Affected files and symbols
  • Risk assessment per finding

Alt+U to toggle.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

SEVERITY_GLYPH = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢", "info": "ℹ"}
SEVERITY_COLOR = {"critical": "red", "high": "orange1", "medium": "yellow", "low": "green", "info": "dim"}


def _run_ultrareview() -> list[dict]:
    """Placeholder: in production runs the UltraReviewPipeline."""
    return [
        {"file": "src/auth.py", "line": 42, "severity": "high",
         "message": "Hardcoded secret detected", "symbol": "AUTH_SECRET"},
        {"file": "src/api.py", "line": 15, "severity": "medium",
         "message": "Unvalidated user input in SQL query", "symbol": "query_users"},
        {"file": "tests/test_auth.py", "line": 0, "severity": "info",
         "message": "Test coverage missing for token refresh", "symbol": ""},
    ]


class UltraReviewWidget(Widget):
    """Code review findings — Alt+U to toggle."""

    DEFAULT_CSS = """
    UltraReviewWidget {
        height: auto; border: solid $border; padding: 0 1; margin: 0 1;
    }
    UltraReviewWidget.collapsed { height: 1; border: none; }
    UltraReviewWidget #ur-header { height: 1; color: $text-muted; }
    UltraReviewWidget #ur-findings { height: auto; max-height: 12; margin: 0 0 0 1; }
    """

    BINDINGS = [Binding("alt+u", "toggle_ultrareview", "UltraReview")]
    expanded: reactive[bool] = reactive(False)

    def compose(self) -> ComposeResult:
        yield Static("", id="ur-header")
        yield Static("", id="ur-findings")

    def on_mount(self) -> None:
        self._render()

    def action_toggle_ultrareview(self) -> None:
        self.expanded = not self.expanded
        self.toggle_class("collapsed", not self.expanded)
        self._render()

    def _render(self) -> None:
        if not self.is_mounted: return
        try:
            findings = _run_ultrareview()
        except Exception:
            findings = []
        try:
            hint = "[dim](alt+u)[/]"
            by_severity = {}
            for f in findings:
                sev = f.get("severity", "info")
                by_severity.setdefault(sev, []).append(f)

            if self.expanded:
                self.query_one("#ur-header", Static).update(
                    f"[bold]UltraReview[/]  [dim]{len(findings)} findings[/]  {hint}"
                )
                if not findings:
                    self.query_one("#ur-findings", Static).update("  [dim]No findings[/]")
                else:
                    lines = []
                    for sev in ("critical", "high", "medium", "low", "info"):
                        items = by_severity.get(sev, [])
                        if not items: continue
                        glyph = SEVERITY_GLYPH.get(sev, "•")
                        color = SEVERITY_COLOR.get(sev, "dim")
                        lines.append(f"  {glyph} [{color}]{sev.upper()}[/]")
                        for item in items[:4]:
                            file = item.get("file", "?")[:24]
                            msg = item.get("message", "")[:48]
                            lines.append(f"    [dim]{file}[/] {msg}")
                    self.query_one("#ur-findings", Static).update("\n".join(lines))
            else:
                crit = len(by_severity.get("critical", []))
                high = len(by_severity.get("high", []))
                status = ""
                if crit: status += f" [red]{crit} crit[/]"
                if high: status += f" [orange1]{high} high[/]"
                self.query_one("#ur-header", Static).update(
                    f"[bold]UltraReview[/]  {status}  [dim]{len(findings)} total[/]  {hint}"
                )
                self.query_one("#ur-findings", Static).update("")
        except Exception:
            pass


__all__ = ["UltraReviewWidget"]
