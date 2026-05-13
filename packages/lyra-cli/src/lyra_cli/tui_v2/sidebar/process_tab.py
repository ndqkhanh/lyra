"""ProcessTab — live htop-style agent process grid for the Lyra sidebar.

Subscribes to ProcessRegistry updates via a polling interval.
Pure Textual widget; the data layer lives in lyra_core.transparency.
"""
from __future__ import annotations

from pathlib import Path

from textual.widgets import Static

from . import REFRESH_SECONDS


_STATE_ICONS: dict[str, str] = {
    "running": "[green]●[/]",
    "waiting": "[yellow]●[/]",
    "blocked": "[bold orange1]⚠[/]",
    "error": "[red]✗[/]",
    "done": "[dim]✓[/]",
    "idle": "[dim]○[/]",
}

_SPARKBAR_WIDTH = 10


def _spark(pct: float) -> str:
    filled = round(pct * _SPARKBAR_WIDTH)
    bar = "█" * filled + "░" * (_SPARKBAR_WIDTH - filled)
    color = "green" if pct < 0.7 else ("yellow" if pct < 0.9 else "red")
    return f"[{color}]{bar}[/] {pct * 100:.0f}%"


def _fmt_cost(usd: float) -> str:
    return f"${usd:.3f}" if usd >= 0.001 else "<$0.001"


def _fmt_elapsed(secs: float) -> str:
    m, s = divmod(int(secs), 60)
    return f"{m:02d}:{s:02d}"


def _render_processes(processes: list) -> str:
    """Render a list of AgentProcess into Rich-marked sidebar text."""
    if not processes:
        return "[bold]processes[/] [dim](0)[/]\n[dim](no agents running)[/]"

    running = [p for p in processes if p.state not in ("done", "idle")]
    done = [p for p in processes if p.state in ("done", "idle")]

    header = f"[bold]processes[/] [dim]({len(processes)} · {len(running)} active)[/]"
    lines = [header]

    for proc in running + done[:3]:
        icon = _STATE_ICONS.get(proc.state, "?")
        name = proc.session_id[-12:] if len(proc.session_id) > 12 else proc.session_id
        tool = f"[dim]{proc.current_tool[:10]}[/]" if proc.current_tool else "[dim]—[/]"
        bar = _spark(proc.context_pct)
        cost = _fmt_cost(proc.cost_usd)
        elapsed = _fmt_elapsed(proc.elapsed_s)
        lines.append(f"  {icon} [bold]{name}[/]")
        lines.append(f"    {bar}  {tool}  {cost}  {elapsed}")

    if len(done) > 3:
        lines.append(f"  [dim]+{len(done) - 3} done[/]")

    blocked = [p for p in processes if p.state == "blocked"]
    if blocked:
        lines.append(f"\n  [bold orange1]⚠ {len(blocked)} blocked — needs attention[/]")

    return "\n".join(lines)


class ProcessTab(Static):
    """Live process panel — polls ProcessRegistry every REFRESH_SECONDS."""

    DEFAULT_CSS = """
    ProcessTab {
        height: auto;
    }
    """

    def __init__(self, root: Path) -> None:
        super().__init__("")
        self._root = root
        self._registry = None

    def on_mount(self) -> None:
        self._init_registry()
        self.refresh_content()
        self.set_interval(REFRESH_SECONDS, self.refresh_content)

    def _init_registry(self) -> None:
        try:
            from lyra_core.transparency.event_store import EventStore
            from lyra_core.transparency.process_registry import ProcessRegistry
            store = EventStore()
            self._registry = ProcessRegistry(store=store)
        except Exception:
            self._registry = None

    def refresh_content(self) -> None:
        processes = []
        if self._registry is not None:
            try:
                self._registry.refresh()
                processes = self._registry.get_all()
            except Exception:
                pass
        self.update(_render_processes(processes))
