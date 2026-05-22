"""ChatToolsWidget — ECC-style inline tool block renderer in the TUI.

Ports chat_tools.py's tool block rendering into a TUI widget that shows:
  • Inline tool calls as collapsed blocks (@thinking, @web, @file, @bash)
  • Expandable per-tool detail (output, duration, tokens)
  • Tool status indicators (⏺ running, ✓ done, ✗ error)
  • Sequential tool chain visualization

Ctrl+Shift+G to toggle (G for "gadgets" / tools).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

TOOL_GLYPH = {
    "web": "🌐", "file": "📄", "thinking": "🧠",
    "bash": "💻", "edit": "✎", "search": "🔍",
    "tool": "⚙", "agent": "👾",
}
TOOL_COLOR = {
    "web": "cyan", "file": "green", "thinking": "yellow",
    "bash": "blue", "edit": "magenta", "search": "cyan",
    "tool": "dim", "agent": "yellow",
}


@dataclass
class ToolBlock:
    """One tool call block in the conversation."""
    kind: str
    tool_name: str
    status: str = "running"
    duration_s: float = 0.0
    tokens: int = 0
    output_preview: str = ""

    @property
    def glyph(self) -> str:
        return TOOL_GLYPH.get(self.kind, TOOL_GLYPH.get(self.tool_name, "⚙"))

    @property
    def color(self) -> str:
        return TOOL_COLOR.get(self.kind, TOOL_COLOR.get(self.tool_name, "dim"))

    def line(self, expanded: bool = False) -> str:
        glyph = self.glyph
        color = self.color
        dur = f"[dim]{self.duration_s:.1f}s[/]" if self.duration_s > 0 else ""
        tok = f"[dim]{self.tokens}t[/]" if self.tokens > 0 else ""
        status_glyph = {"running": "⏺", "done": "✓", "error": "✗"}.get(self.status, "⏺")
        status_color = {"running": "yellow", "done": "green", "error": "red"}.get(self.status, "dim")
        meta = " · ".join(p for p in [dur, tok] if p)

        name = self.tool_name[:20]
        parts = [
            f"  [{color}]{glyph}[/] [{status_color}]{status_glyph}[/] [bold]{name}[/]"
        ]
        if meta:
            parts.append(meta)
        if expanded and self.output_preview:
            parts.append(f"\n    [dim]{self.output_preview[:120]}[/]")
        return " ".join(parts)


class ChatToolsWidget(Widget):
    """Inline tool block chain — Ctrl+Shift+G to toggle.

    Shows the sequence of tool calls in the current turn with
    collapse/expand per block.
    """

    DEFAULT_CSS = """
    ChatToolsWidget {
        height: auto; border: solid $border; padding: 0 1; margin: 0 1;
    }
    ChatToolsWidget.collapsed { height: 1; border: none; }
    ChatToolsWidget #ct-header { height: 1; color: $text-muted; }
    ChatToolsWidget #ct-blocks { height: auto; max-height: 16; margin: 0 0 0 1; }
    """

    BINDINGS = [Binding("ctrl+shift+g", "toggle_chatools", "ChatTools")]
    expanded: reactive[bool] = reactive(False)
    block_count: reactive[int] = reactive(0)

    def __init__(self):
        super().__init__()
        self._blocks: list[ToolBlock] = []
        self._show_detail = False

    def compose(self) -> ComposeResult:
        yield Static("", id="ct-header")
        yield Static("", id="ct-blocks")

    def on_mount(self) -> None:
        self._render()

    # ── Public API ─────────────────────────────────────────────────────

    def append(self, kind: str, tool_name: str) -> ToolBlock:
        block = ToolBlock(kind=kind, tool_name=tool_name, status="running")
        self._blocks.append(block)
        self.block_count = len(self._blocks)
        self._render()
        return block

    def complete(self, index: int, duration_s: float = 0.0, tokens: int = 0,
                 output_preview: str = "", success: bool = True) -> None:
        if 0 <= index < len(self._blocks):
            self._blocks[index].status = "done" if success else "error"
            self._blocks[index].duration_s = duration_s
            self._blocks[index].tokens = tokens
            self._blocks[index].output_preview = output_preview
            self._render()

    def clear(self) -> None:
        self._blocks.clear()
        self.block_count = 0
        self._render()

    # ── Actions ────────────────────────────────────────────────────────

    def action_toggle_chatools(self) -> None:
        self.expanded = not self.expanded
        self._show_detail = self.expanded
        self.toggle_class("collapsed", not self.expanded)
        self._render()

    # ── Internal ───────────────────────────────────────────────────────

    def _render(self) -> None:
        if not self.is_mounted: return
        try:
            hint = "[dim](ctrl+shift+g)[/]"
            running = sum(1 for b in self._blocks if b.status == "running")
            if self.expanded:
                status = f" [yellow]⏺ {running}[/]" if running else ""
                self.query_one("#ct-header", Static).update(
                    f"[bold]Tools[/]{status}  [dim]{len(self._blocks)} blocks[/]  {hint}"
                )
                if not self._blocks:
                    self.query_one("#ct-blocks", Static).update("  [dim]No tool calls yet[/]")
                else:
                    lines = []
                    for i, b in enumerate(self._blocks):
                        lines.append(b.line(expanded=self._show_detail))
                        # connection arrow between blocks
                        if i < len(self._blocks) - 1:
                            lines.append("    [dim]↓[/]")
                    self.query_one("#ct-blocks", Static).update("\n".join(lines))
            else:
                running = sum(1 for b in self._blocks if b.status == "running")
                status = f" [yellow]⏺ {running}[/]" if running else ""
                self.query_one("#ct-header", Static).update(
                    f"[bold]Tools[/]{status}  [dim]{len(self._blocks)} blocks[/]  {hint}"
                )
                self.query_one("#ct-blocks", Static).update("")
        except Exception:
            pass



__all__ = ["ChatToolsWidget", "ToolBlock"]
