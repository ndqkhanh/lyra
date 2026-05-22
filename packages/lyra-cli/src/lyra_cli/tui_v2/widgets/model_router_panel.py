"""ModelRouterWidget — TUI routing policy panel.

Ports model_router.py's 8-slot routing policy into a visual panel:
  • Intent → tier → model-class mapping grid
  • Current route-policy summary
  • Per-slot escalate-when conditions

Alt+R to toggle.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

POLICY_PATH = Path.home() / ".lyra" / "route-policy.json"

DEFAULTS: dict[str, tuple[str, str, str]] = {
    "intent":       ("fast",   "haiku-class",  "always"),
    "search":       ("fast",   "haiku-class",  "query-rewrite-fails"),
    "planning":     ("strong", "opus-class",   "multi-system change"),
    "execution":    ("mid",    "sonnet-class", "tool-failure"),
    "synthesis":    ("strong", "opus-class",   "multi-source contradiction"),
    "verification": ("mid",    "sonnet-class", "safety boundary"),
    "review":       ("mid",    "sonnet-class", "large blast radius"),
    "final":        ("strong", "opus-class",   "publishable artifact"),
}

TIER_GLYPH = {"fast": "⚡", "mid": "◆", "strong": "▲", "advisor": "★"}
TIER_COLOR = {"fast": "green", "mid": "yellow", "strong": "red", "advisor": "magenta"}


def _load_policy() -> dict[str, tuple[str, str, str]]:
    if POLICY_PATH.exists():
        try:
            data = json.loads(POLICY_PATH.read_text())
            return data
        except Exception:
            pass
    return dict(DEFAULTS)


class ModelRouterWidget(Widget):
    """Routing policy panel — Alt+R to toggle.

    Shows: 8-slot intent-to-model-class mapping with tier indicators.
    """

    DEFAULT_CSS = """
    ModelRouterWidget {
        height: auto; border: solid $border; padding: 0 1; margin: 0 1;
    }
    ModelRouterWidget.collapsed { height: 1; border: none; }
    ModelRouterWidget #mr-header { height: 1; color: $text-muted; }
    ModelRouterWidget #mr-content { height: auto; margin: 0 0 0 1; }
    """

    BINDINGS = [Binding("alt+r", "toggle_router", "Router")]
    expanded: reactive[bool] = reactive(False)

    def compose(self) -> ComposeResult:
        yield Static("", id="mr-header")
        yield Static("", id="mr-content")

    def on_mount(self) -> None:
        self._render()

    def action_toggle_router(self) -> None:
        self.expanded = not self.expanded
        self.toggle_class("collapsed", not self.expanded)
        self._render()

    def _render(self) -> None:
        if not self.is_mounted: return
        try:
            policy = _load_policy()
            hint = "[dim](alt+r)[/]"
            if self.expanded:
                self.query_one("#mr-header", Static).update(
                    f"[bold]Router[/]  [dim]{len(policy)} slots[/]  {hint}"
                )
                lines = ["[dim]Intent        Tier      Model          Escalate[/]"]
                for slot, (tier, cls, escalate) in policy.items():
                    glyph = TIER_GLYPH.get(tier, "◆")
                    color = TIER_COLOR.get(tier, "dim")
                    lines.append(
                        f"  [{color}]{glyph}[/] {slot:<13} "
                        f"[{color}]{tier:<8}[/] {cls:<14} [dim]{escalate[:20]}[/]"
                    )
                self.query_one("#mr-content", Static).update("\n".join(lines))
            else:
                tiers = set(t for t, _, _ in policy.values())
                summary = " ".join(f"[{TIER_COLOR.get(t,'dim')}]{t}[/]" for t in sorted(tiers))
                self.query_one("#mr-header", Static).update(
                    f"[bold]Router[/]  {summary}  {hint}"
                )
                self.query_one("#mr-content", Static).update("")
        except Exception:
            pass


__all__ = ["ModelRouterWidget"]
