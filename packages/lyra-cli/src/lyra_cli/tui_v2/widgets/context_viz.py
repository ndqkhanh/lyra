"""ContextVizWidget — live token breakdown with progress bars & compaction history.

Ports lyra-ui's context_viz.py into a Textual widget showing:
  • Token usage breakdown by component (system / conversation / tools / code / memory)
  • Context window fill bar with threshold coloring
  • Compaction history log
  • Expandable detail per component

ECC-inspired: mirrors the token-economy visibility that ECC provides
via its status-line and compaction reporting.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static, RichLog


# ── Data models ─────────────────────────────────────────────────────────

@dataclass
class ContextComponent:
    """One category of context usage."""
    name: str
    tokens: int = 0
    max_tokens: int = 200_000
    color: str = "cyan"

    @property
    def pct(self) -> float:
        return (self.tokens / self.max_tokens * 100) if self.max_tokens > 0 else 0.0

    @property
    def bar(self) -> str:
        w = 15
        f = int(self.pct / 100 * w)
        return "█" * f + "░" * (w - f)


@dataclass
class CompactionRecord:
    """A single compaction event."""
    timestamp: float = field(default_factory=time.time)
    before: int = 0
    after: int = 0
    reason: str = "auto"

    @property
    def saved(self) -> int:
        return self.before - self.after

    @property
    def label(self) -> str:
        ts = time.strftime("%H:%M", time.localtime(self.timestamp))
        saved_k = f"{self.saved / 1000:.1f}K"
        return f"[dim]{ts}[/] [green]✻[/] {saved_k} saved [dim]({self.reason})[/]"


# ── Widget ──────────────────────────────────────────────────────────────

FILL = "█"
EMPTY = "░"
BAR_W = 25

_COMPONENT_COLORS = {
    "system": "cyan",
    "conversation": "yellow",
    "tools": "magenta",
    "code": "green",
    "memory": "blue",
}


class ContextVizWidget(Widget):
    """Live context-window breakdown widget.

    Shows a stacked bar + per-component breakdown + compaction history.
    """

    DEFAULT_CSS = """
    ContextVizWidget {
        height: auto;
        border: solid $border;
        padding: 0 1;
        margin: 0 1;
    }

    ContextVizWidget.collapsed {
        height: 1;
        border: none;
    }

    ContextVizWidget #ctx-header {
        height: 1;
    }

    ContextVizWidget #ctx-components {
        height: auto;
        margin: 0 0 0 1;
    }

    ContextVizWidget #ctx-compaction-log {
        height: auto;
        max-height: 6;
        margin: 0 0 0 1;
    }

    ContextVizWidget .ctx-row {
        height: 1;
    }

    ContextVizWidget .ctx-total {
        text-style: bold;
    }
    """

    BINDINGS = [
        Binding("ctrl+v", "toggle_visibility", "Context"),
    ]

    # Reactive state
    total_used: reactive[int] = reactive(0)
    total_max: reactive[int] = reactive(200_000)
    expanded: reactive[bool] = reactive(False)
    components: reactive[dict] = reactive({})
    compaction_history: reactive[list] = reactive([])

    def __init__(self):
        super().__init__()
        self._components_data: dict[str, ContextComponent] = {}
        self._compaction_records: list[CompactionRecord] = []
        self._init_default_components()

    def _init_default_components(self) -> None:
        self._components_data = {
            name: ContextComponent(name=name, color=_COMPONENT_COLORS.get(name, "white"))
            for name in ["system", "conversation", "tools", "code", "memory"]
        }

    def compose(self) -> ComposeResult:
        """Compose the widget."""
        yield Static("", id="ctx-header")
        yield Vertical(id="ctx-components")
        yield Static("", id="ctx-compaction-log")

    def on_mount(self) -> None:
        self._refresh()

    # ── Public API ─────────────────────────────────────────────────────

    def set_component(self, name: str, tokens: int, max_tokens: int = 200_000) -> None:
        """Update one component's token count."""
        if name in self._components_data:
            self._components_data[name].tokens = tokens
            self._components_data[name].max_tokens = max_tokens
        self._update_aggregates()

    def add_compaction(self, before: int, after: int, reason: str = "auto") -> None:
        """Record a compaction event."""
        self._compaction_records.append(CompactionRecord(
            before=before, after=after, reason=reason,
        ))
        if len(self._compaction_records) > 20:
            self._compaction_records = self._compaction_records[-20:]
        self.compaction_history = [r.label for r in self._compaction_records[-5:]]

    def update_total(self, used: int, max_tokens: int = 200_000) -> None:
        """Update aggregate token usage."""
        self.total_used = used
        self.total_max = max_tokens
        self._update_aggregates()

    # ── Actions ────────────────────────────────────────────────────────

    def action_toggle_visibility(self) -> None:
        self.expanded = not self.expanded
        self.toggle_class("collapsed", not self.expanded)
        self._refresh()

    # ── Internal ───────────────────────────────────────────────────────

    def _update_aggregates(self) -> None:
        total = sum(c.tokens for c in self._components_data.values())
        self.total_used = total

        self.components = {
            name: {
                "tokens": c.tokens,
                "pct": c.pct,
                "bar": c.bar,
                "color": c.color,
            }
            for name, c in self._components_data.items()
        }
        self._refresh()

    def _refresh(self) -> None:
        if not self.is_mounted:
            return
        try:
            self._render_header()
            self._render_components()
            self._render_compaction_log()
        except Exception:
            pass

    def _render_header(self) -> None:
        pct = (self.total_used / self.total_max * 100) if self.total_max > 0 else 0
        f = int(pct / 100 * BAR_W)
        bar = "█" * f + "░" * (BAR_W - f)

        # colour by threshold
        style = "bold green"
        if pct >= 95:
            style = "bold red"
        elif pct >= 80:
            style = "bold orange1"
        elif pct >= 50:
            style = "bold yellow"

        header = (
            f"[{style}]{bar}[/]  "
            f"[{style}]{pct:>4.1f}%[/]  "
            f"[dim]{self._human(self.total_used)} / {self._human(self.total_max)}[/]"
        )
        if self.expanded:
            header += "  [dim](ctrl+v hide)[/]"
        else:
            header += "  [dim](ctrl+v show)[/]"

        try:
            self.query_one("#ctx-header", Static).update(header)
        except Exception:
            pass

    def _render_components(self) -> None:
        if not self.expanded:
            try:
                self.query_one("#ctx-components", Vertical).children = []
            except Exception:
                pass
            return

        lines = []
        for name, comp in self._components_data.items():
            if comp.tokens == 0:
                continue
            pct = comp.pct
            tokens_str = self._human(comp.tokens)
            lines.append(
                f"  [dim]{name}[/]  [{comp.color}]{comp.bar}[/]  "
                f"{pct:>4.1f}%  [dim]{tokens_str}[/]"
            )

        try:
            container = self.query_one("#ctx-components", Vertical)
            container.children = []
            for line in lines:
                container.mount(Static(line, classes="ctx-row"))
        except Exception:
            pass

    def _render_compaction_log(self) -> None:
        if not self.expanded or not self._compaction_records:
            try:
                self.query_one("#ctx-compaction-log", Static).update("")
            except Exception:
                pass
            return

        lines = ["[dim]Compactions:[/]"]
        for rec in self._compaction_records[-5:]:
            lines.append(f"  {rec.label}")

        try:
            self.query_one("#ctx-compaction-log", Static).update("\n".join(lines))
        except Exception:
            pass

    @staticmethod
    def _human(n: int) -> str:
        if n < 1_000:
            return str(n)
        if n < 1_000_000:
            return f"{n / 1_000:.1f}K"
        return f"{n / 1_000_000:.1f}M"
