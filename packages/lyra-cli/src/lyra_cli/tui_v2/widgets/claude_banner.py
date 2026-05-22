"""ClaudeStyleBannerWidget — ECC-inspired welcome banner for the TUI.

Ports banner_claude.py's two-column welcome layout into a TUI widget:
  • Left column: Lyra wordmark, version, model, working directory
  • Right column: tips, what's new, quick-start links
  • Collapsible (Ctrl+W alongside WelcomeCard)

Shown at TUI startup above the chat area.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

_MARK = (
    "▐▛███▜▌\n"
    "▝▜█████▛▘\n"
    " ▘▘ ▝▝"
)

TIPS = [
    "Type / to see all commands",
    "Ctrl+K opens the command palette",
    "Ctrl+R browses session history",
    "/workflow scaffolds structured tasks",
    "/recipe generates files from templates",
    "Ctrl+Shift+S opens the status dashboard",
]


class ClaudeStyleBannerWidget(Widget):
    """ECC-inspired welcome banner — shown at TUI startup."""

    DEFAULT_CSS = """
    ClaudeStyleBannerWidget {
        height: auto;
        padding: 1 2;
        margin: 0 1;
        border: dashed $accent;
    }

    ClaudeStyleBannerWidget.collapsed {
        height: 1;
        border: none;
        padding: 0 1;
    }

    ClaudeStyleBannerWidget #banner-wordmark {
        text-style: bold;
        color: $primary;
    }

    ClaudeStyleBannerWidget #banner-info {
        color: $text-muted;
    }

    ClaudeStyleBannerWidget #banner-tips {
        color: $text;
    }

    ClaudeStyleBannerWidget #banner-collapsed {
        height: 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+w", "toggle_banner", "Banner"),
    ]

    expanded: reactive[bool] = reactive(True)
    version: reactive[str] = reactive("")
    model: reactive[str] = reactive("")
    cwd: reactive[str] = reactive("")
    mode: reactive[str] = reactive("")

    def __init__(self):
        super().__init__()
        self._tip_index = 0

    def compose(self) -> ComposeResult:
        if self.expanded:
            yield Static("", id="banner-wordmark")
            yield Static("", id="banner-info")
            yield Static("", id="banner-tips")
        else:
            yield Static("", id="banner-collapsed")

    def on_mount(self) -> None:
        self._render()

    def action_toggle_banner(self) -> None:
        self.expanded = not self.expanded
        self.toggle_class("collapsed", not self.expanded)
        self._render()

    def _render(self) -> None:
        if not self.is_mounted: return
        try:
            if self.expanded:
                wordmark = f"[bold $primary]{_MARK}[/]"
                model_s = self.model or "auto"
                cwd_s = self._truncate(self.cwd or str(Path.cwd()), 40)
                mode_s = self.mode.replace("_", " ") if self.mode else "edit automatically"
                ver = self.version or ""
                info = (
                    f"[dim]Lyra[/] [bold]{ver}[/]  "
                    f"[dim]model[/] [italic]{model_s}[/]  "
                    f"[dim]mode[/] [italic]{mode_s}[/]  "
                    f"[dim]cwd[/] {cwd_s}"
                )

                tip = TIPS[self._tip_index % len(TIPS)]
                tips = f"[dim]Tip:[/] {tip}"

                self.query_one("#banner-wordmark", Static).update(wordmark)
                self.query_one("#banner-info", Static).update(info)
                self.query_one("#banner-tips", Static).update(tips)
            else:
                pass
        except Exception:
            pass

    def rotate_tip(self) -> None:
        self._tip_index += 1
        self._render()

    @staticmethod
    def _truncate(text: str, max_len: int) -> str:
        if len(text) <= max_len: return text
        return "…" + text[-(max_len - 1):]


__all__ = ["ClaudeStyleBannerWidget"]
