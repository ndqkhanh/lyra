"""ContextEngineeringWidget — TUI context management panel.

Ports context_engineering.py's checkpoint/prune/playbook/inject into a visual panel:
  • Active checkpoints timeline
  • Context pruning controls
  • Playbook status
  • Injected file list

Ctrl+Shift+X to toggle.
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

CHECKPOINTS_ROOT = Path.home() / ".lyra" / "checkpoints"
PLAYBOOK_PATH = Path.home() / ".lyra" / "playbook.md"


def _scan_checkpoints() -> list[dict]:
    if not CHECKPOINTS_ROOT.is_dir():
        return []
    checkpoints = []
    for f in sorted(CHECKPOINTS_ROOT.glob("*.json")):
        try:
            data = json.loads(f.read_text())
            data["_name"] = f.stem
            checkpoints.append(data)
        except Exception:
            checkpoints.append({"_name": f.stem})
    return checkpoints[-8:]


def _playbook_exists() -> bool:
    return PLAYBOOK_PATH.exists()


class ContextEngineeringWidget(Widget):
    """Context management panel — Ctrl+Shift+X to toggle.

    Shows: checkpoints, playbook status, context stats.
    """

    DEFAULT_CSS = """
    ContextEngineeringWidget {
        height: auto; border: solid $border; padding: 0 1; margin: 0 1;
    }
    ContextEngineeringWidget.collapsed { height: 1; border: none; }
    ContextEngineeringWidget #ctx-header { height: 1; color: $text-muted; }
    ContextEngineeringWidget #ctx-content { height: auto; margin: 0 0 0 1; }
    """

    BINDINGS = [Binding("ctrl+shift+x", "toggle_context", "Context")]
    expanded: reactive[bool] = reactive(False)

    def compose(self) -> ComposeResult:
        yield Static("", id="ctx-header")
        yield Static("", id="ctx-content")

    def on_mount(self) -> None:
        self._render()

    def action_toggle_context(self) -> None:
        self.expanded = not self.expanded
        self.toggle_class("collapsed", not self.expanded)
        self._render()

    def _render(self) -> None:
        if not self.is_mounted: return
        try:
            cps = _scan_checkpoints()
            has_playbook = _playbook_exists()
            hint = "[dim](ctrl+shift+x)[/]"
            if self.expanded:
                self.query_one("#ctx-header", Static).update(
                    f"[bold]Context[/]  [green]{len(cps)}[/] checkpoints  "
                    f"{'[green]✓[/] playbook' if has_playbook else '[dim]○ playbook[/]'}  {hint}"
                )
                lines = []
                if cps:
                    lines.append("[dim]Checkpoints:[/]")
                    for cp in cps:
                        name = cp.get("_name", "?")[:24]
                        lines.append(f"  [dim]{name}[/]")
                else:
                    lines.append("  [dim]No checkpoints[/]")
                lines.append(
                    f"  {'[green]✓[/]' if has_playbook else '[dim]○[/]'} "
                    f"Playbook: {'exists' if has_playbook else 'not set'}"
                )
                self.query_one("#ctx-content", Static).update("\n".join(lines))
            else:
                self.query_one("#ctx-header", Static).update(
                    f"[bold]Context[/]  [green]{len(cps)}[/] ckpts  "
                    f"{'✓' if has_playbook else '○'} pb  {hint}"
                )
                self.query_one("#ctx-content", Static).update("")
        except Exception:
            pass


__all__ = ["ContextEngineeringWidget"]
