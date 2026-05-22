"""OnboardingWidget — TUI first-run welcome wizard panel.

Ports onboarding.py's render_welcome into a TUI widget that shows:
  • Lyra wordmark, version, and quick-start guide
  • Provider connection status
  • Key help (how to set API keys)
  • Tip rotation

Shown at TUI startup, above the chat area. User can dismiss with Ctrl+W.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

# Provider env vars (aligned with onboarding.py)
_ENV_VAR_HINTS = (
    "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY",
    "GEMINI_API_KEY", "DEEPSEEK_API_KEY", "DASHSCOPE_API_KEY",
    "XAI_API_KEY", "GROQ_API_KEY", "CEREBRAS_API_KEY",
    "MISTRAL_API_KEY", "OPENROUTER_API_KEY",
)

_TIPS = [
    "Type / to see all commands",
    "Ctrl+K opens the command palette",
    "/keys list shows which providers are configured",
    "/recipe scaffolds new files from templates",
    "/workflow structures multi-step tasks",
]

_WORDMARK = (
    "▐▛███▜▌\n"
    "▝▜█████▛▘\n"
    " ▘▘ ▝▝"
)


class OnboardingWidget(Widget):
    """First-run welcome panel — shown at TUI startup.

    Ctrl+W to dismiss. Shows: wordmark, quick-start, provider status, tips.
    """

    DEFAULT_CSS = """
    OnboardingWidget {
        height: auto;
        padding: 1 2;
        margin: 0 1;
        border: dashed $accent;
    }
    OnboardingWidget.collapsed { height: 1; border: none; padding: 0 1; }
    OnboardingWidget #ob-wordmark { text-style: bold; color: $primary; }
    OnboardingWidget #ob-status { color: $text-muted; }
    OnboardingWidget #ob-tips { color: $text; }
    """

    BINDINGS = [Binding("ctrl+w", "dismiss", "Dismiss")]
    expanded: reactive[bool] = reactive(True)
    version: reactive[str] = reactive("3.14.0")

    def __init__(self):
        super().__init__()
        self._tip_index = 0

    def compose(self) -> ComposeResult:
        yield Static("", id="ob-wordmark")
        yield Static("", id="ob-status")
        yield Static("", id="ob-tips")

    def on_mount(self) -> None:
        self._render()

    def action_dismiss(self) -> None:
        self.expanded = False
        self.toggle_class("collapsed", True)
        self._render()

    def rotate_tip(self) -> None:
        self._tip_index = (self._tip_index + 1) % len(_TIPS)
        self._render()

    def _render(self) -> None:
        if not self.is_mounted:
            return
        try:
            if not self.expanded:
                self.query_one("#ob-wordmark", Static).update("")
                self.query_one("#ob-status", Static).update(
                    "[dim]Lyra ready — Ctrl+W for welcome[/]"
                )
                self.query_one("#ob-tips", Static).update("")
                return

            # Wordmark
            self.query_one("#ob-wordmark", Static).update(
                f"[bold $primary]{_WORDMARK}[/]  [bold]Lyra[/] [dim]{self.version}[/]"
            )

            # Provider status
            configured = []
            for var in _ENV_VAR_HINTS:
                if os.environ.get(var):
                    name = var.replace("_API_KEY", "").replace("_", " ").title()
                    configured.append(name)
            status_lines = ["[dim]Quick start:[/]"]
            if configured:
                status_lines.append(
                    f"  [green]✓[/] Providers: {', '.join(configured[:5])}"
                )
            else:
                status_lines.append(
                    "  [dim]○[/] No API keys configured — type [accent]/keys set <provider> <key>[/]"
                )
            status_lines.append(
                "  [dim]⎿[/] Type [accent]/keys list[/] to see available providers"
            )
            status_lines.append(
                "  [dim]⎿[/] Type [accent]/recipe list[/] to see workflow templates"
            )
            self.query_one("#ob-status", Static).update("\n".join(status_lines))

            # Tip
            tip = _TIPS[self._tip_index % len(_TIPS)]
            self.query_one("#ob-tips", Static).update(f"[dim]Tip:[/] {tip}")
        except Exception:
            pass


__all__ = ["OnboardingWidget"]
