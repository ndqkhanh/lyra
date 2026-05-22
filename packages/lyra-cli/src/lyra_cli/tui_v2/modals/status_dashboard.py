"""StatusDashboardModal — ECC-inspired consolidated /status view.

Shows the full snapshot of the current session in one screen:
  • Model / Mode / Provider info
  • Token usage breakdown (system/conversation/tools/memory)
  • Active agent fleet snapshot
  • Background tasks
  • Session timing and turn count
  • Compaction history
  • Resource health (memory, cache, GC)
  • Quick keyboard reference

ECC reference: mirrors ECC's /status command + everything-claude-code's
identity.json structured status surface.
"""
from __future__ import annotations

import time
from typing import Any, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Static, Label, Button


# ── Section rendering helpers ──────────────────────────────────────────

_BAR_WIDTH = 20


def _fill_bar(pct: float, color: str = "green") -> str:
    f = int(pct / 100 * _BAR_WIDTH)
    bar = "█" * f + "░" * (_BAR_WIDTH - f)
    return f"[{color}]{bar}[/]"


def _dur(secs: float) -> str:
    if secs < 60:
        return f"{secs:.0f}s"
    m, s = divmod(int(secs), 60)
    if m < 60:
        return f"{m}m {s:02d}s"
    h, m = divmod(m, 60)
    return f"{h}h {m:02d}m"


def _tok(n: int) -> str:
    if n < 1_000:
        return str(n)
    if n < 1_000_000:
        return f"{n / 1_000:.1f}K"
    return f"{n / 1_000_000:.1f}M"


# ── Modal ───────────────────────────────────────────────────────────────

class StatusDashboardModal(ModalScreen[None]):
    """Full-screen consolidated /status view.

    Activated via Ctrl+Shift+S or /status command.
    Shows: model info, token economy, agents, tasks, resources, keyboard.
    """

    DEFAULT_CSS = """
    StatusDashboardModal {
        align: center middle;
    }

    StatusDashboardModal > Vertical {
        width: 88;
        height: 85%;
        min-height: 30;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    StatusDashboardModal #sd-header {
        height: 2;
        content-align: center middle;
        border-bottom: solid $border;
        text-style: bold;
    }

    StatusDashboardModal #sd-body {
        height: 1fr;
        overflow-y: auto;
        margin: 1 0;
    }

    StatusDashboardModal #sd-body Grid {
        grid-size: 2;
        grid-columns: 1fr 1fr;
        grid-gutter: 1;
    }

    StatusDashboardModal .section {
        border: solid $border;
        padding: 0 1;
        height: auto;
    }

    StatusDashboardModal .section-title {
        text-style: bold;
        color: $accent;
        height: 1;
    }

    StatusDashboardModal .stat-row {
        height: 1;
    }

    StatusDashboardModal #sd-footer {
        dock: bottom;
        height: 2;
        content-align: center middle;
        border-top: solid $border;
    }

    StatusDashboardModal .kb-grid {
        grid-size: 2;
        grid-columns: 1fr 1fr;
        height: auto;
    }

    StatusDashboardModal .kb-key {
        color: $accent;
        text-style: bold;
    }

    StatusDashboardModal .kb-action {
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss(None)", "Close", show=False),
        Binding("q", "dismiss(None)", "Close", show=False),
        Binding("r", "refresh", "Refresh", show=True),
    ]

    # Data to display (set externally by the app)
    model_name: reactive[str] = reactive("")
    mode_name: reactive[str] = reactive("")
    provider_name: reactive[str] = reactive("")
    token_used: reactive[int] = reactive(0)
    token_max: reactive[int] = reactive(200_000)
    turn_count: reactive[int] = reactive(0)
    session_duration: reactive[float] = reactive(0.0)
    agent_count: reactive[int] = reactive(0)
    agent_running: reactive[int] = reactive(0)
    bg_task_count: reactive[int] = reactive(0)
    memory_mb: reactive[float] = reactive(0.0)
    version: reactive[str] = reactive("3.14.0")
    compaction_count: reactive[int] = reactive(0)
    a11y_mode: reactive[str] = reactive("normal")

    def __init__(
        self,
        snapshot: Optional[dict[str, Any]] = None,
    ):
        super().__init__()
        if snapshot:
            for k, v in snapshot.items():
                if hasattr(self, k):
                    setattr(self, k, v)

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("[bold]Status Dashboard[/]", id="sd-header")
            yield Static("", id="sd-body")
            yield Label("", id="sd-footer")

    def on_mount(self) -> None:
        self._render()

    def action_refresh(self) -> None:
        self._render()

    def _render(self) -> None:
        if not self.is_mounted:
            return
        try:
            body = self.query_one("#sd-body", Static)
            body.update(self._build_markup())
            self.query_one("#sd-footer", Label).update(
                "[dim]q=close · r=refresh · esc=dismiss[/]"
            )
        except Exception:
            pass

    def _build_markup(self) -> str:
        pct = (self.token_used / self.token_max * 100) if self.token_max > 0 else 0
        t_color = "green" if pct < 50 else ("yellow" if pct < 80 else ("orange1" if pct < 95 else "red"))

        sections = []

        # ── Session Info ───────────────────────────────────────────────
        session_info = (
            f"[bold]Session Info[/]\n"
            f"  Version:    [bold]{self.version}[/]\n"
            f"  Mode:       {self.mode_name}\n"
            f"  Model:      {self.model_name}\n"
            f"  Provider:   {self.provider_name}\n"
            f"  Turn:       #{self.turn_count}\n"
            f"  Duration:   {_dur(self.session_duration)}\n"
            f"  A11y:       {self.a11y_mode}\n"
        )
        sections.append(("info", session_info))

        # ── Token Economy ──────────────────────────────────────────────
        token_info = (
            f"[bold]Token Economy[/]\n"
            f"  {_fill_bar(pct, t_color)}  {pct:.1f}%\n"
            f"  Used:  {_tok(self.token_used)} / {_tok(self.token_max)}\n"
            f"  Compactions: {self.compaction_count}\n"
        )
        sections.append(("tokens", token_info))

        # ── Agents ─────────────────────────────────────────────────────
        agent_info = (
            f"[bold]Agents[/]\n"
            f"  Running: [bold cyan]{self.agent_running}[/] / {self.agent_count}\n"
            f"  Background: {self.bg_task_count}\n"
        )
        sections.append(("agents", agent_info))

        # ── Resources ──────────────────────────────────────────────────
        mem_pct = min(100, self.memory_mb / 500.0 * 100) if self.memory_mb > 0 else 0
        m_color = "green" if mem_pct < 60 else ("yellow" if mem_pct < 90 else "red")
        res_info = (
            f"[bold]Resources[/]\n"
            f"  Memory: {_fill_bar(mem_pct, m_color)}  {self.memory_mb:.0f}MB\n"
        )
        sections.append(("resources", res_info))

        # ── Keyboard Reference ─────────────────────────────────────────
        kb = [
            ("ctrl+k", "Command palette"),
            ("ctrl+r", "Session manager"),
            ("ctrl+n", "Notifications"),
            ("ctrl+d", "Agent dashboard"),
            ("ctrl+v", "Context viz"),
            ("ctrl+o", "Expand output"),
            ("ctrl+b", "Background tasks"),
            ("ctrl+w", "Toggle welcome"),
            ("ctrl+f6", "Research flow"),
            ("ctrl+shift+h", "High contrast"),
            ("ctrl+shift+r", "Resource monitor"),
            ("ctrl+shift+d", "Performance"),
            ("/model", "Switch model"),
            ("/theme", "Switch theme"),
        ]

        kb_lines = ["[bold]Quick Keys[/]"]
        for key, action in kb:
            kb_lines.append(f"  [accent]{key:<17}[/]  {action}")
        sections.append(("keys", "\n".join(kb_lines)))

        # Render two-column grid
        col1 = "\n\n".join(m for i, (name, m) in enumerate(sections) if i % 2 == 0)
        col2 = "\n\n".join(m for i, (name, m) in enumerate(sections) if i % 2 == 1)

        return (
            "[dim]──────────────────────────────────┬──────────────────────────────────[/]\n"
            f"{col1:<42}│ {col2}\n"
            "[dim]──────────────────────────────────┴──────────────────────────────────[/]"
        )
