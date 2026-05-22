"""ECC-inspired /effort command — reasoning effort level picker.

Ports effort.py's five-level reasoning taxonomy into a usable command:
  /effort                — show current level
  /effort list           — list all levels with descriptions
  /effort <level>        — set reasoning effort
  /effort <n>            — set by number (1-5)

Levels match Claude Code's taxonomy:
  1 low     — fastest, cheapest
  2 medium  — default, Plan + Build
  3 high    — extra review passes
  4 xhigh   — deep reasoning + multi-pass verifier
  5 max     — full refute-or-promote loop

EffortWidget — TUI panel showing current level with bar, toggle via Alt+E.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

from ..commands.registry import CommandResult

# ── Effort levels (from effort.py) ─────────────────────────────────────

EFFORT_LEVELS = ("low", "medium", "high", "xhigh", "max")

EFFORT_BLURBS = {
    "low":    "fastest single-turn attempt; cheapest model",
    "medium": "default — Plan + Build with standard verification",
    "high":   "extra review passes (/review, /ultrareview)",
    "xhigh":  "deep reasoning + multi-pass verifier",
    "max":    "full refute-or-promote loop + cross-channel verifier",
}

EFFORT_GLYPH = {
    "low":    "⚡",
    "medium": "◆",
    "high":   "▲",
    "xhigh":  "◆◆",
    "max":    "★★",
}

EFFORT_COLOR = {
    "low":    "green",
    "medium": "cyan",
    "high":   "yellow",
    "xhigh":  "magenta",
    "max":    "red",
}

EFFORT_MAX_TOKENS = {
    "low":    2_000,
    "medium": 4_000,
    "high":   8_000,
    "xhigh":  12_000,
    "max":    16_000,
}

ENV_VAR = "HARNESS_REASONING_EFFORT"
CONFIG_FILE = Path.home() / ".lyra" / "effort.json"


def _current_level() -> str:
    """Get current effort level from env or config."""
    env = os.environ.get(ENV_VAR, "")
    if env in EFFORT_LEVELS:
        return env
    if CONFIG_FILE.exists():
        try:
            import json
            data = json.loads(CONFIG_FILE.read_text())
            level = data.get("level", "medium")
            if level in EFFORT_LEVELS:
                return level
        except Exception:
            pass
    return "medium"


def _set_level(level: str) -> None:
    """Persist effort level to env and config."""
    os.environ[ENV_VAR] = level
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    import json
    CONFIG_FILE.write_text(json.dumps({"level": level, "updated_at": __import__("time").time()}))


# ── Slash command ──────────────────────────────────────────────────────

def cmd_effort(session: Any, args: str) -> CommandResult:
    """Set or view reasoning effort level.

    Usage:
      /effort              — show current level
      /effort list         — list all levels
      /effort <level>      — set level by name
      /effort <n>          — set level by number (1-5)
    """
    parts = args.strip().split() if args.strip() else []
    subcmd = parts[0].lower() if parts else "show"

    if subcmd == "show":
        level = _current_level()
        glyph = EFFORT_GLYPH.get(level, "◆")
        color = EFFORT_COLOR.get(level, "cyan")
        blurb = EFFORT_BLURBS.get(level, "")
        max_tok = EFFORT_MAX_TOKENS.get(level, 4000)
        idx = EFFORT_LEVELS.index(level) + 1

        # Bar visualization
        bar_w = 20
        f = int(idx / len(EFFORT_LEVELS) * bar_w)
        bar = "█" * f + "░" * (bar_w - f)

        lines = [
            f"[bold]Effort[/]  [{color}]{glyph} {level}[/] (level {idx}/{len(EFFORT_LEVELS)})",
            f"  [{color}]{bar}[/]",
            f"  [dim]{blurb}[/]",
            f"  [dim]Max tokens: {max_tok:,}[/]",
        ]
        return CommandResult(
            output=f"Effort: {level} ({idx}/{len(EFFORT_LEVELS)})",
            renderable="\n".join(lines),
        )

    if subcmd == "list":
        lines = ["[bold]Effort Levels[/]"]
        for i, level in enumerate(EFFORT_LEVELS, 1):
            glyph = EFFORT_GLYPH.get(level, "◆")
            color = EFFORT_COLOR.get(level, "cyan")
            blurb = EFFORT_BLURBS.get(level, "")
            max_tok = EFFORT_MAX_TOKENS.get(level, 0)
            marker = "[green]●[/]" if level == _current_level() else " "
            lines.append(
                f"  {marker} [{color}]{glyph}[/] [{color}]{level:<8}[/]"
                f"  [dim]{blurb:50}[/]  [dim]{max_tok:,} tok[/]"
            )
        return CommandResult(
            output=f"Effort levels: {', '.join(EFFORT_LEVELS)}",
            renderable="\n".join(lines),
        )

    # Set by name or number
    target = subcmd
    if target.isdigit():
        idx = int(target) - 1
        if 0 <= idx < len(EFFORT_LEVELS):
            target = EFFORT_LEVELS[idx]
        else:
            return CommandResult(output=f"Invalid level {target}. Use 1-{len(EFFORT_LEVELS)}")

    if target in EFFORT_LEVELS:
        _set_level(target)
        glyph = EFFORT_GLYPH.get(target, "◆")
        color = EFFORT_COLOR.get(target, "cyan")
        return CommandResult(
            output=f"✓ Effort set to [{color}]{glyph} {target}[/]",
            renderable=(
                f"[bold]Effort set to {target}[/]\n"
                f"  [{color}]" + "█" * 20 + f"[/]\n"
                f"  {EFFORT_BLURBS.get(target, '')}"
            ),
        )

    return CommandResult(output=f"Unknown level '{target}'. Use: {', '.join(EFFORT_LEVELS)} or 1-{len(EFFORT_LEVELS)}")


# ── TUI Widget ─────────────────────────────────────────────────────────

class EffortWidget(Widget):
    """Reasoning effort level indicator — Alt+E to toggle.

    Shows a bar with current effort level and token budget.
    """

    DEFAULT_CSS = """
    EffortWidget {
        height: auto;
        border: solid $border;
        padding: 0 1;
        margin: 0 1;
    }

    EffortWidget.collapsed {
        height: 1;
        border: none;
    }

    EffortWidget #effort-header {
        height: 1;
        color: $text-muted;
    }

    EffortWidget #effort-content {
        height: auto;
        margin: 0 0 0 1;
    }
    """

    BINDINGS = [
        Binding("alt+e", "toggle_effort", "Effort"),
    ]

    expanded: reactive[bool] = reactive(False)
    level: reactive[str] = reactive("medium")

    def __init__(self):
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Static("", id="effort-header")
        yield Static("", id="effort-content")

    def on_mount(self) -> None:
        self.level = _current_level()
        self._render()

    def refresh_level(self) -> None:
        self.level = _current_level()
        self._render()

    def action_toggle_effort(self) -> None:
        self.expanded = not self.expanded
        self.toggle_class("collapsed", not self.expanded)
        self.refresh_level()

    def _render(self) -> None:
        if not self.is_mounted:
            return
        try:
            level = _current_level()
            color = EFFORT_COLOR.get(level, "cyan")
            glyph = EFFORT_GLYPH.get(level, "◆")
            max_tok = EFFORT_MAX_TOKENS.get(level, 4000)
            idx = EFFORT_LEVELS.index(level) + 1
            total = len(EFFORT_LEVELS)

            hint = "[dim](alt+e)[/]"
            if self.expanded:
                bar_w = 20
                f = int(idx / total * bar_w)
                bar = "█" * f + "░" * (bar_w - f)
                self.query_one("#effort-header", Static).update(
                    f"[bold]Effort[/]  [{color}]{glyph} {level}[/]  {hint}"
                )
                self.query_one("#effort-content", Static).update(
                    f"  [{color}]{bar}[/]  {idx}/{total}\n"
                    f"  [dim]{EFFORT_BLURBS.get(level, '')}[/]\n"
                    f"  [dim]Max tokens: {max_tok:,}[/]"
                )
            else:
                self.query_one("#effort-header", Static).update(
                    f"[bold]Effort[/]  [{color}]{glyph} {level}[/]  "
                    f"[dim]{idx}/{total}[/]  {hint}"
                )
                self.query_one("#effort-content", Static).update("")
        except Exception:
            pass


__all__ = ["cmd_effort", "EffortWidget", "EFFORT_LEVELS"]
