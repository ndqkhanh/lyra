"""CISuggestionsWidget — ECC-style inline next-step suggestions in the TUI.

Shows contextual suggestions below the chat area — like TryGram from
ECC — suggesting what the user might do next based on current state.

ECC reference: the SKILL.md Common Workflows show structured procedures
with frequency labels (e.g., "~2 times per month"). This widget brings
that awareness into the TUI as inline suggestions.

Examples:
  "Has uncommitted changes → /git commit"
  "No API keys → /keys list"
  "New to Lyra? → /help, /workflow list"
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static


def _detect_context() -> list[tuple[str, str, str]]:
    """Detect suggestions from current context.

    Returns list of (emoji, suggestion, command) tuples.
    """
    suggestions: list[tuple[str, str, str]] = []

    # Git state
    try:
        r = subprocess.run(["git", "status", "--porcelain"],
                          capture_output=True, text=True, timeout=5)
        dirty = len([l for l in r.stdout.split("\n") if l.strip()])
        if dirty > 0:
            suggestions.append(("📝", f"{dirty} uncommitted file(s)", "/git commit"))
            suggestions.append(("🔄", "Preview changes", "/diff"))
    except Exception:
        pass

    # API keys
    key_vars = ["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "DEEPSEEK_API_KEY"]
    configured = sum(1 for v in key_vars if __import__("os").environ.get(v))
    if configured == 0:
        suggestions.append(("🔑", "Configure an API provider", "/keys list"))

    # First run
    lyra_dir = Path.home() / ".lyra"
    if not lyra_dir.is_dir() or not list(lyra_dir.iterdir()):
        suggestions.append(("🚀", "Get started with Lyra", "/help --quick"))
        suggestions.append(("📋", "Try a structured workflow", "/workflow start feature"))

    return suggestions


class CISuggestionsWidget(Widget):
    """Context-aware inline suggestions — Ctrl+Shift+F to toggle.

    Shows 2-4 contextual suggestions like TryGram. Each suggestion is
    clickable via its associated slash command.
    """

    DEFAULT_CSS = """
    CISuggestionsWidget {
        height: auto;
        border: solid $border 30%;
        padding: 0 1;
        margin: 0 1;
    }
    CISuggestionsWidget.collapsed { height: 1; border: none; }
    CISuggestionsWidget #ci-header { height: 1; color: $text-muted; }
    CISuggestionsWidget #ci-items { height: auto; margin: 0 0 0 1; max-height: 6; }
    CISuggestionsWidget .ci-item { height: 1; }
    """

    BINDINGS = [Binding("ctrl+shift+f", "toggle_suggestions", "Suggestions")]

    expanded: reactive[bool] = reactive(False)

    def compose(self) -> ComposeResult:
        yield Static("", id="ci-header")
        yield Static("", id="ci-items")

    def on_mount(self) -> None:
        self._render()

    def refresh_suggestions(self) -> None:
        self._render()

    def action_toggle_suggestions(self) -> None:
        self.expanded = not self.expanded
        self.toggle_class("collapsed", not self.expanded)
        if self.expanded:
            self._render()

    def _render(self) -> None:
        if not self.is_mounted: return
        try:
            hint = "[dim](ctrl+shift+f)[/]"
            suggestions = _detect_context()

            if self.expanded:
                self.query_one("#ci-header", Static).update(
                    f"[bold]Suggestions[/]  [dim]({len(suggestions)})[/]  {hint}"
                )
                if not suggestions:
                    self.query_one("#ci-items", Static).update(
                        "  [green]✓[/] Everything looks good"
                    )
                else:
                    lines = []
                    for emoji, suggestion, cmd in suggestions[:5]:
                        lines.append(
                            f"  {emoji} {suggestion}  [accent]{cmd}[/]"
                        )
                    self.query_one("#ci-items", Static).update("\n".join(lines))
            else:
                counts = {"📝": 0, "🔑": 0, "🚀": 0, "🔄": 0}
                for emoji, _, _ in suggestions:
                    counts[emoji] = counts.get(emoji, 0) + 1
                status = " · ".join(
                    f"{emoji} {n}" for emoji, n in counts.items() if n > 0
                ) or "[green]✓[/]"
                self.query_one("#ci-header", Static).update(
                    f"[bold]Suggestions[/]  {status}  {hint}"
                )
                self.query_one("#ci-items", Static).update("")
        except Exception:
            pass


__all__ = ["CISuggestionsWidget"]
