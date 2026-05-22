"""StatusBarEnhancedWidget — live footer bar with all session context.

Ports status_source.py's session context into a rich TUI footer:
  • cwd (truncated path)
  • mode glyph + name
  • model name with provider
  • LSP/MCP server count
  • Budget status (if cap set)
  • Git branch + dirty count
  • Token usage bar
  • Turn counter
  • Agent state indicator

Shown at the bottom of the TUI shell, auto-collapsing when narrow.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static


# ── Mode glyphs ────────────────────────────────────────────────────────

_MODE_GLYPH = {
    "edit_automatically": "⚡",
    "edit": "✎",
    "plan": "📋",
    "ask": "💬",
    "debug": "🐛",
    "review": "🔬",
    "research": "🔍",
    "architect": "🏗",
}


class StatusBarEnhancedWidget(Widget):
    """Rich footer bar — session state at a glance.

    Shows: mode · model · budget · git · tokens · turn · agents
    """

    DEFAULT_CSS = """
    StatusBarEnhancedWidget {
        height: 1;
        background: $surface 80%;
        color: $text-muted;
        dock: bottom;
        padding: 0 1;
    }

    StatusBarEnhancedWidget .sb-segment {
        margin: 0 0 0 1;
    }

    StatusBarEnhancedWidget .sb-sep {
        color: $border;
    }
    """

    # Reactive state
    mode: reactive[str] = reactive("edit_automatically")
    model: reactive[str] = reactive("")
    provider: reactive[str] = reactive("")
    budget_pct: reactive[float] = reactive(0.0)
    budget_limit: reactive[float] = reactive(0.0)
    git_branch: reactive[str] = reactive("")
    git_dirty: reactive[int] = reactive(0)
    tokens_used: reactive[int] = reactive(0)
    tokens_max: reactive[int] = reactive(200_000)
    turn: reactive[int] = reactive(0)
    agent_count: reactive[int] = reactive(0)
    agent_running: reactive[int] = reactive(0)
    lsp_count: reactive[int] = reactive(0)
    mcp_count: reactive[int] = reactive(0)
    cwd: reactive[str] = reactive("")

    def __init__(self):
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Static("", id="sb-content")

    def on_mount(self) -> None:
        self._render()

    def watch_mode(self, _: str) -> None:
        self._render()

    def watch_model(self, _: str) -> None:
        self._render()

    def watch_git_branch(self, _: str) -> None:
        self._render()

    def watch_tokens_used(self, _: int) -> None:
        self._render()

    def watch_turn(self, _: int) -> None:
        self._render()

    # ── Public setters (called from app) ───────────────────────────────

    def update(self, **kwargs) -> None:
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)
        self._render()

    # ── Internal ───────────────────────────────────────────────────────

    def _render(self) -> None:
        if not self.is_mounted:
            return
        try:
            segments = self._build_segments()
            self.query_one("#sb-content", Static).update("  ".join(segments))
        except Exception:
            pass

    def _build_segments(self) -> list[str]:
        segs: list[str] = []

        # Mode
        glyph = _MODE_GLYPH.get(self.mode, "⚡")
        segs.append(f"[accent]{glyph}[/] [dim]{self.mode.replace('_', ' ')}[/]")

        # Model
        if self.model:
            model_display = self.model
            segs.append(f"[cyan]◆[/] {model_display}")

        # Budget
        if self.budget_limit > 0:
            pct = self.budget_pct
            if pct >= 100:
                color = "red"
            elif pct >= 80:
                color = "yellow"
            else:
                color = "green"
            segs.append(f"[{color}]$[/] [{color}]{pct:.0f}%[/]")

        # Git
        if self.git_branch:
            dirty_str = f"[yellow]✎{self.git_dirty}[/]" if self.git_dirty > 0 else ""
            branch_col = "yellow" if self.git_dirty > 0 else "dim"
            parts = [f"[{branch_col}]{self.git_branch}[/]"]
            if dirty_str:
                parts.append(dirty_str)
            segs.append(" ".join(parts))

        # Tokens
        if self.tokens_used > 0:
            pct = (self.tokens_used / self.tokens_max * 100) if self.tokens_max > 0 else 0
            t_color = "green" if pct < 50 else ("yellow" if pct < 80 else "red")
            tok_str = f"{self.tokens_used / 1000:.0f}K"
            max_str = f"{self.tokens_max / 1000:.0f}K"
            segs.append(f"[{t_color}]☰[/] [{t_color}]{tok_str}[/]/[dim]{max_str}[/]")

        # Turn
        if self.turn > 0:
            segs.append(f"[dim]T#{self.turn}[/]")

        # Agents
        if self.agent_running > 0:
            segs.append(f"[yellow]⏺[/] {self.agent_running}/{self.agent_count}")

        # LSP/MCP
        if self.lsp_count > 0 or self.mcp_count > 0:
            parts = []
            if self.lsp_count:
                parts.append(f"LSP:{self.lsp_count}")
            if self.mcp_count:
                parts.append(f"MCP:{self.mcp_count}")
            segs.append(f"[dim]{' '.join(parts)}[/]")

        # Cwd (truncated)
        if self.cwd:
            c = self._truncate(self.cwd, 25)
            segs.append(f"[dim]{c}[/]")

        return segs

    @staticmethod
    def _truncate(text: str, max_len: int) -> str:
        if len(text) <= max_len:
            return text
        return "…" + text[-(max_len - 1):]
