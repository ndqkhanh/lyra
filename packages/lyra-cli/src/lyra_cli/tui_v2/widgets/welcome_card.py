"""Enhanced Welcome Card — ECC-inspired command grid & session overview.

Ports the command-grid + quick-reference design from ECC's
everything-claude-code welcome surface into Lyra's WelcomeCard.
Shows: Lyra branding, quick commands grid, recent sessions,
current model/mode/repo, and contextual tips.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Horizontal, Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static


class WelcomeCard(Widget):
    """Collapsible welcome card with command grid & session overview."""

    BINDINGS = [
        Binding("ctrl+w", "toggle_expand", "Toggle Welcome"),
    ]

    DEFAULT_CSS = """
    WelcomeCard {
        height: auto;
        margin: 0 1;
        padding: 1;
        border: dashed $accent;
    }

    WelcomeCard.collapsed {
        height: 1;
        border: none;
        padding: 0 1;
    }

    WelcomeCard Grid#command-grid {
        grid-size: 4;
        grid-columns: 1fr 1fr 1fr 1fr;
        grid-gutter: 1;
        height: auto;
        margin: 1 0;
    }

    WelcomeCard Grid#session-grid {
        grid-size: 2;
        grid-columns: 1fr 1fr;
        grid-gutter: 1;
        height: auto;
        margin: 1 0;
    }

    WelcomeCard .cmd-card {
        padding: 0 1;
        background: $surface 50%;
        border: tall $border;
        text-align: center;
    }

    WelcomeCard .cmd-card:hover {
        background: $accent 25%;
    }

    WelcomeCard .cmd-key {
        color: $accent;
        text-style: bold;
    }

    WelcomeCard .cmd-desc {
        color: $text-muted;
    }

    WelcomeCard .section-title {
        text-style: bold;
        color: $primary;
        margin: 1 0 0 0;
    }

    WelcomeCard .info-row {
        height: 1;
    }

    /* Collapsed state */
    WelcomeCard.collapsed Grid {
        display: none;
    }

    /* Narrow-width responsive layout (toggled by on_resize when width < 80) */
    WelcomeCard.narrow Grid#command-grid {
        grid-size: 2;
        grid-columns: 1fr 1fr;
    }
    WelcomeCard.narrow Grid#session-grid {
        grid-size: 1;
        grid-columns: 1fr;
    }
    """

    model: reactive[str] = reactive("claude-sonnet-4-6")
    mode: reactive[str] = reactive("default")
    cwd: reactive[str] = reactive("")
    account: reactive[str] = reactive("")
    expanded: reactive[bool] = reactive(True)
    version: reactive[str] = reactive("3.14.0")
    recent_sessions: reactive[list] = reactive([])

    # ── Command grid definition (ECC-inspired) ──────────────────────

    COMMANDS = [
        ("/plan", "Design & architect"),
        ("/research", "Deep research"),
        ("/code", "Write / implement"),
        ("/review", "Review code"),
        ("/test", "Write tests"),
        ("/debug", "Fix issues"),
        ("/model", "Switch models"),
        ("/help", "All commands"),
    ]

    def compose(self) -> ComposeResult:
        if self.expanded:
            yield Vertical(
                self._render_branding(),
                Static("Quick Commands", classes="section-title"),
                Grid(*self._render_command_grid(), id="command-grid"),
                Static("Session Info", classes="section-title"),
                Grid(*self._render_session_grid(), id="session-grid"),
                Static("", id="welcome-tips"),
            )
        else:
            yield Static("", id="welcome-collapsed")

    def on_mount(self) -> None:
        self._apply_narrow_class()
        self._refresh()

    def on_resize(self) -> None:
        self._apply_narrow_class()

    _NARROW_BREAKPOINT = 80

    def _apply_narrow_class(self) -> None:
        try:
            width = self.app.size.width
        except Exception:
            return
        self.set_class(width < self._NARROW_BREAKPOINT, "narrow")

    def watch_model(self, _: str) -> None:
        self._refresh()

    def watch_mode(self, _: str) -> None:
        self._refresh()

    def watch_cwd(self, _: str) -> None:
        self._refresh()

    def _refresh(self) -> None:
        self.refresh(layout=True)

    # ── Renderers ─────────────────────────────────────────────────────

    def _render_branding(self) -> Static:
        cwd_s = self._truncate(self.cwd, 35)
        return Static(
            "[bold #FACC15]✦  Lyra[/]  [dim]v{}[/]    "
            "[dim]model=[/][italic]{}[/]  "
            "[dim]mode=[/][italic]{}[/]  "
            "[dim]repo=[/][italic]{}[/]".format(
                self.version, self.model, self.mode, cwd_s,
            )
        )

    def _render_command_grid(self) -> list[Static]:
        cards = []
        for cmd, desc in self.COMMANDS:
            cards.append(
                Static(
                    f"[dim]\[/][bold]$accent[/]{cmd}[dim]][/]\n"
                    f"[dim]{desc}[/]",
                    classes="cmd-card",
                )
            )
        return cards

    def _render_session_grid(self) -> list[Widget]:
        items = []

        # Left column: welcome + stats
        left_lines = [
            f"[dim]User:[/]  {self.account or 'anon'}",
            f"[dim]Turn:[/]  #—",
            f"[dim]Agent:[/]  ready",
        ]
        left = Static("\n".join(left_lines), id="info-left")

        # Right column: recent sessions
        right_lines = ["[dim]Recent Sessions:[/]"]
        if self.recent_sessions:
            for s in self.recent_sessions[:3]:
                title = s.get("title", "Untitled")[:28]
                right_lines.append(f"  [dim]•[/] {title}")
        else:
            right_lines.append("  [dim](no history)[/]")
        right_lines.append("")
        right = Static("\n".join(right_lines), id="info-right")

        items.append(left)
        items.append(right)
        return items

    def _render_collapsed(self) -> str:
        cwd_s = self._truncate(self.cwd, 30)
        return (
            f"[bold #FACC15]✦[/] Lyra v{self.version}  "
            f"[dim]|[/] {self.model}  "
            f"[dim]|[/] {cwd_s}  "
            f"[dim]|[/] [italic]ctrl+w to expand[/]"
        )

    # ── Actions ───────────────────────────────────────────────────────

    def action_toggle_expand(self) -> None:
        self.expanded = not self.expanded

    # ── Helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _truncate(text: str, max_len: int) -> str:
        if len(text) <= max_len:
            return text
        return text[: max_len - 3] + "..."

    def set_tip(self, tip: str) -> None:
        try:
            widget = self.query_one("#welcome-tips", Static)
            widget.update(f"[dim]⎿[/] Tip: {tip}")
        except Exception:
            pass
