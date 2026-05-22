"""MemoryDashboardWidget — TUI panel for memory lifecycle management.

Ports memory_lifecycle.py into a visual panel showing:
  • Memory store stats (episodes, strategies, semantic summaries)
  • Recent consolidations timeline
  • Per-file sizes and ages
  • Quick distill/audit triggers

Ctrl+Shift+M to toggle.
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

MEMORY_ROOT = Path.home() / ".lyra" / "memory"
STRATEGIES_DIR = MEMORY_ROOT / "strategies"
EPISODES_DIR = MEMORY_ROOT / "episodes"


def _scan_memory() -> dict[str, Any]:
    stats = {
        "strategies": 0,
        "episodes": 0,
        "total_files": 0,
        "total_size_kb": 0,
        "recent": [],
    }
    for root in [STRATEGIES_DIR, EPISODES_DIR, MEMORY_ROOT]:
        if not root.is_dir():
            continue
        for f in root.rglob("*.md"):
            try:
                size = f.stat().st_size
                mtime = f.stat().st_mtime
                stats["total_files"] += 1
                stats["total_size_kb"] += size / 1024
                parent = f.parent.name
                if parent == "strategies":
                    stats["strategies"] += 1
                elif parent == "episodes":
                    stats["episodes"] += 1
                stats["recent"].append((mtime, f.name, size))
            except Exception:
                pass

    if not MEMORY_ROOT.is_dir():
        MEMORY_ROOT.mkdir(parents=True, exist_ok=True)

    stats["recent"].sort(reverse=True)
    stats["recent"] = stats["recent"][:8]
    return stats


class MemoryDashboardWidget(Widget):
    """Memory store dashboard — Ctrl+Shift+M to toggle.

    Shows: store stats, recent consolidations, file sizes.
    """

    DEFAULT_CSS = """
    MemoryDashboardWidget {
        height: auto;
        border: solid $border;
        padding: 0 1;
        margin: 0 1;
    }

    MemoryDashboardWidget.collapsed {
        height: 1;
        border: none;
    }

    MemoryDashboardWidget #mem-header {
        height: 1;
        color: $text-muted;
    }

    MemoryDashboardWidget #mem-stats {
        height: auto;
        margin: 0 0 0 1;
    }

    MemoryDashboardWidget #mem-recent {
        height: auto;
        max-height: 8;
        margin: 0 0 0 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+shift+m", "toggle_memory", "Memory"),
    ]

    expanded: reactive[bool] = reactive(False)

    def compose(self) -> ComposeResult:
        yield Static("", id="mem-header")
        yield Static("", id="mem-stats")
        yield Static("", id="mem-recent")

    def on_mount(self) -> None:
        self._render()

    def action_toggle_memory(self) -> None:
        self.expanded = not self.expanded
        self.toggle_class("collapsed", not self.expanded)
        self._render()

    def _render(self) -> None:
        if not self.is_mounted:
            return
        try:
            stats = _scan_memory()
            hint = "[dim](ctrl+shift+m)[/]"
            total_kb = stats.get("total_size_kb", 0)
            if self.expanded:
                self.query_one("#mem-header", Static).update(
                    f"[bold]Memory[/]  "
                    f"[green]{stats['strategies']}[/] strategies  "
                    f"[green]{stats['episodes']}[/] episodes  "
                    f"[dim]{stats['total_files']} files · {total_kb:.0f}KB[/]  {hint}"
                )
                lines = [
                    f"  [dim]Strategies:[/]  [green]{stats['strategies']}[/]",
                    f"  [dim]Episodes:[/]   [green]{stats['episodes']}[/]",
                    f"  [dim]Files:[/]      {stats['total_files']}",
                    f"  [dim]Size:[/]       {total_kb:.0f} KB",
                ]
                self.query_one("#mem-stats", Static).update("\n".join(lines))
                recent_lines = ["[dim]Recent:[/]"]
                for mtime, name, size in stats["recent"][:6]:
                    ts = time.strftime("%H:%M", time.localtime(mtime))
                    recent_lines.append(f"  [dim]{ts}[/] {name[:30]:<30}  {size:>6}B")
                self.query_one("#mem-recent", Static).update("\n".join(recent_lines))
            else:
                self.query_one("#mem-header", Static).update(
                    f"[bold]Memory[/]  "
                    f"[green]{stats['strategies']}[/] strat  "
                    f"[green]{stats['episodes']}[/] ep  "
                    f"[dim]{total_kb:.0f}KB[/]  {hint}"
                )
                self.query_one("#mem-stats", Static).update("")
                self.query_one("#mem-recent", Static).update("")
        except Exception:
            pass


__all__ = ["MemoryDashboardWidget"]
