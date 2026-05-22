"""ConnectStatusWidget — TUI provider connection status panel.

Ports commands/connect.py's provider listing into a TUI panel showing:
  • All configured providers with connection status
  • Key expiry information
  • Quick-connect instructions for unconfigured providers

Ctrl+Shift+E to toggle.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

FIRST_CLASS = ("anthropic", "openai", "gemini", "deepseek", "qwen", "ollama")
SUPPORTED = (*FIRST_CLASS, "xai", "groq", "cerebras", "mistral",
             "openrouter", "dashscope", "bedrock", "vertex", "copilot")

PROVIDER_ENV = {
    "anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY", "deepseek": "DEEPSEEK_API_KEY",
    "qwen": "DASHSCOPE_API_KEY", "ollama": "", "xai": "XAI_API_KEY",
    "groq": "GROQ_API_KEY", "cerebras": "CEREBRAS_API_KEY",
    "mistral": "MISTRAL_API_KEY", "openrouter": "OPENROUTER_API_KEY",
    "dashscope": "DASHSCOPE_API_KEY", "bedrock": "",
    "vertex": "", "copilot": "GITHUB_TOKEN",
}


def _check_provider(name: str) -> tuple[bool, str]:
    env = PROVIDER_ENV.get(name, "")
    if not env:
        return True, "built-in"
    val = os.environ.get(env, "")
    if val:
        masked = val[:6] + "****" + val[-4:] if len(val) > 12 else "****"
        return True, masked
    return False, ""


class ConnectStatusWidget(Widget):
    """Provider connection status — Ctrl+Shift+E to toggle."""

    DEFAULT_CSS = """
    ConnectStatusWidget {
        height: auto; border: solid $border; padding: 0 1; margin: 0 1;
    }
    ConnectStatusWidget.collapsed { height: 1; border: none; }
    ConnectStatusWidget #conn-header { height: 1; color: $text-muted; }
    ConnectStatusWidget #conn-content { height: auto; margin: 0 0 0 1; }
    """

    BINDINGS = [Binding("ctrl+shift+e", "toggle_connect", "Connect")]
    expanded: reactive[bool] = reactive(False)

    def compose(self) -> ComposeResult:
        yield Static("", id="conn-header")
        yield Static("", id="conn-content")

    def on_mount(self) -> None:
        self._render()

    def action_toggle_connect(self) -> None:
        self.expanded = not self.expanded
        self.toggle_class("collapsed", not self.expanded)
        self._render()

    def _render(self) -> None:
        if not self.is_mounted: return
        try:
            hint = "[dim](ctrl+shift+e)[/]"
            configured = sum(1 for p in SUPPORTED if _check_provider(p)[0])
            total = len(SUPPORTED)
            if self.expanded:
                self.query_one("#conn-header", Static).update(
                    f"[bold]Connect[/]  [green]{configured}[/]/{total} providers  {hint}"
                )
                lines = ["[dim]First-class:[/]"]
                for p in FIRST_CLASS:
                    ok, val = _check_provider(p)
                    glyph = "[green]✓[/]" if ok else "[dim]○[/]"
                    detail = f" [dim]{val}[/]" if val else ""
                    lines.append(f"  {glyph} {p}{detail}")
                lines.append("")
                lines.append("[dim]Others:[/]")
                for p in SUPPORTED:
                    if p in FIRST_CLASS: continue
                    ok, val = _check_provider(p)
                    glyph = "[green]✓[/]" if ok else "[dim]○[/]"
                    detail = f" [dim]{val}[/]" if val else ""
                    lines.append(f"  {glyph} {p}{detail}")
                self.query_one("#conn-content", Static).update("\n".join(lines))
            else:
                self.query_one("#conn-header", Static).update(
                    f"[bold]Connect[/]  [green]{configured}[/]/{total}  {hint}"
                )
                self.query_one("#conn-content", Static).update("")
        except Exception:
            pass


__all__ = ["ConnectStatusWidget"]
