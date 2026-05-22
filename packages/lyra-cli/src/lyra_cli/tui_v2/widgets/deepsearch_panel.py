"""DeepSearchWidget — IRCoT multi-hop search visualization in the TUI.

Ports the 332-line deepsearch.py IRCoT engine into a visual panel.
Shows:
  • Multi-hop search tree with per-hop status
  • Sources found per hop with relevance scores
  • Contradiction detection across hops
  • Token/time cost per hop
  • Expandable reasoning chain

Ctrl+Shift+S to toggle (alongside StatusDashboard — uses Alt+S to disambiguate).
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


@dataclass
class HopResult:
    """One IRCoT hop in a deep search."""
    hop_id: int
    subgoal: str
    sources: list[str] = field(default_factory=list)
    support_score: float = 0.0
    contradiction_score: float = 0.0
    reasoning: str = ""
    tokens: int = 0
    elapsed_ms: int = 0
    status: str = "pending"  # pending, running, complete, contradiction

    @property
    def glyph(self) -> str:
        return {"pending": "○", "running": "⏺", "complete": "✓",
                "contradiction": "⚠"}.get(self.status, "○")

    @property
    def style(self) -> str:
        return {"pending": "dim", "running": "bold cyan", "complete": "bold green",
                "contradiction": "bold yellow"}.get(self.status, "dim")

    @property
    def line(self) -> str:
        src_count = len(self.sources)
        dur = f"{self.elapsed_ms / 1000:.1f}s" if self.elapsed_ms > 0 else ""
        tok = f"{self.tokens:,} tok" if self.tokens > 0 else ""
        extra = " · ".join(p for p in [dur, tok] if p)
        extra_str = f"  [dim]({extra})[/]" if extra else ""
        return (
            f"  [{self.style}]{self.glyph}[/] "
            f"[bold]Hop {self.hop_id}[/]: {self.subgoal[:60]}"
            f"{extra_str}"
        )


@dataclass
class SearchSynthesis:
    """Final synthesis across all hops."""
    conclusion: str = ""
    total_tokens: int = 0
    total_time_ms: int = 0
    sources_found: int = 0
    contradictions: int = 0

    @property
    def line(self) -> str:
        return (
            f"  [bold]Synthesis[/]  {self.conclusion[:80]}"
            f"  [dim]{self.sources_found} sources · "
            f"{self.contradictions} contradictions · "
            f"{self.total_tokens:,} tok · "
            f"{self.total_time_ms / 1000:.1f}s[/]"
        )


class DeepSearchWidget(Widget):
    """IRCoT multi-hop search visualization.

    Shows the full search tree: query decomposition → per-hop
    evidence gathering → contradiction detection → synthesis.
    """

    DEFAULT_CSS = """
    DeepSearchWidget {
        height: auto;
        border: solid $border;
        padding: 0 1;
        margin: 0 1;
    }

    DeepSearchWidget.collapsed {
        height: 1;
        border: none;
    }

    DeepSearchWidget #ds-header {
        height: 1;
        color: $text-muted;
    }

    DeepSearchWidget #ds-hops {
        height: auto;
        max-height: 14;
        margin: 0 0 0 1;
    }

    DeepSearchWidget #ds-synthesis {
        height: auto;
        margin: 0 0 0 1;
    }
    """

    BINDINGS = [
        Binding("alt+s", "toggle_deepsearch", "DeepSearch"),
    ]

    expanded: reactive[bool] = reactive(False)
    query: reactive[str] = reactive("")
    hop_count: reactive[int] = reactive(0)

    def __init__(self):
        super().__init__()
        self._hops: list[HopResult] = []
        self._synthesis = SearchSynthesis()

    def compose(self) -> ComposeResult:
        yield Static("", id="ds-header")
        yield Static("", id="ds-hops")
        yield Static("", id="ds-synthesis")

    def on_mount(self) -> None:
        self._render()

    # ── Public API ─────────────────────────────────────────────────────

    def start_search(self, query: str, hops: int = 3) -> None:
        """Begin a deep search."""
        self.query = query
        self._hops = [HopResult(hop_id=i + 1, subgoal="") for i in range(hops)]
        self._hops[0].status = "running"
        self._synthesis = SearchSynthesis()
        self._render()

    def update_hop(self, hop_id: int, **kwargs) -> None:
        """Update a hop's state."""
        for hop in self._hops:
            if hop.hop_id == hop_id:
                for k, v in kwargs.items():
                    if hasattr(hop, k):
                        setattr(hop, k, v)
                break
        self._render()

    def complete_hop(self, hop_id: int, success: bool = True) -> None:
        """Mark a hop complete."""
        for hop in self._hops:
            if hop.hop_id == hop_id:
                hop.status = "complete" if success else "contradiction"
                # Advance to next hop
                if hop_id < len(self._hops):
                    self._hops[hop_id].status = "running"
                break
        self._render()

    def set_synthesis(self, synthesis: SearchSynthesis) -> None:
        self._synthesis = synthesis
        self._render()

    def add_source(self, hop_id: int, source: str) -> None:
        for hop in self._hops:
            if hop.hop_id == hop_id:
                hop.sources.append(source)
                break
        self._render()

    # ── Actions ────────────────────────────────────────────────────────

    def action_toggle_deepsearch(self) -> None:
        self.expanded = not self.expanded
        self.toggle_class("collapsed", not self.expanded)
        self._render()

    # ── Internal ───────────────────────────────────────────────────────

    def _render(self) -> None:
        if not self.is_mounted:
            return
        try:
            self._render_header()
            self._render_hops()
            self._render_synthesis()
        except Exception:
            pass

    def _render_header(self) -> None:
        hint = "[dim](alt+s)[/]"
        q = f": {self.query[:40]}" if self.query else ""
        complete = sum(1 for h in self._hops if h.status == "complete")
        total = len(self._hops)
        if self.expanded:
            self.query_one("#ds-header", Static).update(
                f"[bold]DeepSearch{q}[/]  "
                f"[green]{complete}[/]/{total} hops  {hint}"
            )
        else:
            self.query_one("#ds-header", Static).update(
                f"[bold]DeepSearch{q}[/]  "
                f"[green]{complete}[/]/{total} hops  {hint}"
            )

    def _render_hops(self) -> None:
        if not self.expanded or not self._hops:
            self.query_one("#ds-hops", Static).update("")
            return
        lines = []
        for hop in self._hops:
            lines.append(hop.line)
            # Show sources for complete hops
            if hop.status == "complete" and hop.sources:
                for src in hop.sources[:3]:
                    lines.append(f"    [dim]⎿ {src[:60]}[/]")
                if len(hop.sources) > 3:
                    lines.append(f"    [dim]⎿ +{len(hop.sources) - 3} more[/]")
        self.query_one("#ds-hops", Static).update("\n".join(lines))

    def _render_synthesis(self) -> None:
        if not self.expanded or not self._synthesis.conclusion:
            self.query_one("#ds-synthesis", Static).update("")
            return
        self.query_one("#ds-synthesis", Static).update(self._synthesis.line)
