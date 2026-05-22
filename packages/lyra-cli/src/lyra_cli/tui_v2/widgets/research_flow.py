"""ResearchFlowWidget — phase visualization for multi-agent research.

Ports ECC's research-playbook + lyra-research agent patterns into a
Textual widget showing the full research lifecycle:
  • Phase indicator (discovery → analysis → synthesis → audit → report)
  • Per-source progress (arxiv, github, semantic_scholar, web, huggingface)
  • Evidence trail with citation counts
  • Contradiction detection status
  • Falsification check status
  • Live token cost per phase

ECC reference: everything-claude-code-research-playbook.md's structured
flow (inspect → browse → summarize) and lyra-research's multi-agent
discovery/synthesis pipeline.

    ┌─ Research Pipeline ────────────────────────────────────┐
    │ ✶ Galloping… (32s · ↓ 20 tokens)                      │
    │                                                         │
    │  Sources tracked:                                       │
    │  ✓ arxiv (5 papers)           ◎ semantic_scholar (3)    │
    │  ✓ github (8 repos)           ○ web (searching…)       │
    │                                                         │
    │  Analysis: ✓ quality scored · ◎ contradictions found   │
    │  Synthesis: ◎ cross-referencing 3 sources              │
    │  Audit: pending                                         │
    └─────────────────────────────────────────────────────────┘
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Horizontal, Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static


# ── Phase model ─────────────────────────────────────────────────────────

class ResearchPhase(Enum):
    DISCOVERY = "discovery"
    ANALYSIS = "analysis"
    SYNTHESIS = "synthesis"
    AUDIT = "audit"
    REPORT = "report"

    @property
    def glyph(self) -> str:
        return {
            ResearchPhase.DISCOVERY: "🌐",
            ResearchPhase.ANALYSIS: "🔬",
            ResearchPhase.SYNTHESIS: "🧠",
            ResearchPhase.AUDIT: "✓",
            ResearchPhase.REPORT: "📋",
        }[self]

    @property
    def label(self) -> str:
        return self.value.capitalize()

    @property
    def order(self) -> int:
        return list(ResearchPhase).index(self)

    def __lt__(self, other):
        if not isinstance(other, ResearchPhase):
            return NotImplemented
        return self.order < other.order


@dataclass
class SourceProgress:
    """Progress of one research source."""
    name: str
    glyph: str = "○"
    items_found: int = 0
    status: str = "idle"  # idle, searching, complete, error
    tokens: int = 0
    duration_s: float = 0.0

    @property
    def line(self) -> str:
        status_glyph = {"idle": "○", "searching": "⏺", "complete": "✓", "error": "✗"}.get(self.status, "○")
        style = {
            "idle": "dim", "searching": "bold cyan",
            "complete": "bold green", "error": "bold red",
        }.get(self.status, "dim")
        items = f" ({self.items_found})" if self.items_found > 0 else ""
        return f"  [{style}]{status_glyph}[/] [bold]{self.name}[/]{items}"


@dataclass
class PhaseState:
    """State of one research phase."""
    phase: ResearchPhase
    status: str = "pending"  # pending, active, complete, error, skipped
    sources: list[SourceProgress] = field(default_factory=list)
    tokens: int = 0
    start_time: float = 0.0
    findings: int = 0
    contradictions: int = 0

    @property
    def duration_s(self) -> float:
        if self.start_time == 0:
            return 0.0
        return time.time() - self.start_time

    @property
    def glyph(self) -> str:
        return {
            "pending": "○", "active": "⏺",
            "complete": "✓", "error": "✗", "skipped": "—",
        }.get(self.status, "○")

    @property
    def style(self) -> str:
        return {
            "pending": "dim", "active": "bold cyan",
            "complete": "bold green", "error": "bold red", "skipped": "dim",
        }.get(self.status, "dim")


# ── Widget ──────────────────────────────────────────────────────────────

PHASE_COLORS = {
    ResearchPhase.DISCOVERY: "cyan",
    ResearchPhase.ANALYSIS: "yellow",
    ResearchPhase.SYNTHESIS: "magenta",
    ResearchPhase.AUDIT: "green",
    ResearchPhase.REPORT: "blue",
}


class ResearchFlowWidget(Widget):
    """Multi-phase research pipeline visualization.

    Shows the full ECC-inspired research lifecycle:
    discovery → analysis → synthesis → audit → report
    with per-source progress, contradiction tracking, and cost.
    """

    DEFAULT_CSS = """
    ResearchFlowWidget {
        height: auto;
        border: solid $border;
        padding: 0 1;
        margin: 0 1;
    }

    ResearchFlowWidget.collapsed {
        height: 1;
        border: none;
    }

    ResearchFlowWidget #rf-header {
        height: 1;
        text-style: bold;
    }

    ResearchFlowWidget #rf-phases {
        height: auto;
        margin: 0 0 1 1;
    }

    ResearchFlowWidget #rf-phases .rf-phase-row {
        height: auto;
    }

    ResearchFlowWidget #rf-sources {
        height: auto;
        margin: 0 0 0 1;
    }

    ResearchFlowWidget #rf-summary {
        height: auto;
        margin: 0 0 0 1;
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("ctrl+f6", "toggle_research", "Research"),
    ]

    # Reactive state
    active: reactive[bool] = reactive(False)
    expanded: reactive[bool] = reactive(True)
    current_phase_name: reactive[str] = reactive("")
    total_tokens: reactive[int] = reactive(0)
    total_findings: reactive[int] = reactive(0)
    total_contradictions: reactive[int] = reactive(0)

    def __init__(self):
        super().__init__()
        self._phases: dict[ResearchPhase, PhaseState] = {
            p: PhaseState(phase=p) for p in ResearchPhase
        }
        self._register_default_sources()

    def _register_default_sources(self) -> None:
        discovery = self._phases[ResearchPhase.DISCOVERY]
        discovery.sources = [
            SourceProgress(name="arxiv", glyph="📄"),
            SourceProgress(name="github", glyph="📦"),
            SourceProgress(name="semantic_scholar", glyph="🎓"),
            SourceProgress(name="web", glyph="🌐"),
            SourceProgress(name="huggingface", glyph="🤗"),
        ]

    def compose(self) -> ComposeResult:
        yield Static("", id="rf-header")
        yield Static("", id="rf-phases")
        yield Static("", id="rf-sources")
        yield Static("", id="rf-summary")

    def on_mount(self) -> None:
        self._render()

    # ── Public API ─────────────────────────────────────────────────────

    def start_research(self, topic: str = "") -> None:
        """Begin a new research flow."""
        self.active = True
        self._reset()
        self._phases[ResearchPhase.DISCOVERY].status = "active"
        self._phases[ResearchPhase.DISCOVERY].start_time = time.time()
        self.current_phase_name = ResearchPhase.DISCOVERY.value
        topic_display = f" [dim]· {topic[:40]}[/]" if topic else ""
        self._update_header(f"[bold cyan]🔍 Research Flow{topic_display}[/]")
        self._render()

    def set_source_status(self, source_name: str, status: str, items: int = 0) -> None:
        """Update a discovery source's status."""
        for source in self._phases[ResearchPhase.DISCOVERY].sources:
            if source.name == source_name:
                source.status = status
                if items:
                    source.items_found = items
                break
        self._render()

    def advance_to_phase(self, phase: ResearchPhase) -> None:
        """Move to the next research phase."""
        for p in ResearchPhase:
            state = self._phases[p]
            if p == phase:
                state.status = "active"
                state.start_time = time.time()
                self.current_phase_name = p.value
            elif p.order < phase.order and state.status == "active":
                state.status = "complete"
                state.tokens = self.total_tokens // max(1, (p.order + 1))
        self._render()

    def complete_phase(self, phase: ResearchPhase, findings: int = 0, contradictions: int = 0) -> None:
        """Mark a phase as complete."""
        state = self._phases[phase]
        state.status = "complete"
        state.findings = findings
        state.contradictions = contradictions
        self.total_findings += findings
        self.total_contradictions += contradictions
        self._render()

    def error_phase(self, phase: ResearchPhase, message: str = "") -> None:
        """Mark a phase as errored."""
        self._phases[phase].status = "error"
        self._render()

    def add_tokens(self, count: int) -> None:
        """Add tokens to the current phase."""
        self.total_tokens += count
        current = self._phases.get(
            next((p for p in ResearchPhase if self._phases[p].status == "active"), None)
        )
        if current:
            current.tokens += count
        self._render()

    def set_contradictions(self, count: int) -> None:
        """Set the contradiction count (from lyra-research's contradiction_detector)."""
        syn = self._phases[ResearchPhase.SYNTHESIS]
        syn.contradictions = count
        self.total_contradictions = count
        self._render()

    def end_research(self) -> None:
        """Complete the entire research flow."""
        for state in self._phases.values():
            if state.status == "active":
                state.status = "complete"
        self.active = False
        self._update_header(f"[bold green]✓[/] Research complete  [dim]{self.total_findings} findings · {self.total_tokens:,} tokens[/]")
        self._render()

    # ── Actions ────────────────────────────────────────────────────────

    def action_toggle_research(self) -> None:
        self.expanded = not self.expanded
        self.toggle_class("collapsed", not self.expanded)
        self._render()

    # ── Internal ───────────────────────────────────────────────────────

    def _reset(self) -> None:
        for state in self._phases.values():
            state.status = "pending"
            state.tokens = 0
            state.start_time = 0.0
            state.findings = 0
            state.contradictions = 0
            for source in state.sources:
                source.status = "idle"
                source.items_found = 0
                source.duration_s = 0.0
        self.total_tokens = 0
        self.total_findings = 0
        self.total_contradictions = 0

    def _update_header(self, text: str) -> None:
        try:
            self.query_one("#rf-header", Static).update(text)
        except Exception:
            pass

    def _render(self) -> None:
        if not self.is_mounted:
            return
        try:
            self._render_phases()
            self._render_sources()
            self._render_summary()
        except Exception:
            pass

    def _render_phases(self) -> None:
        if not self.expanded:
            self.query_one("#rf-phases", Static).update("")
            return

        lines = []
        for phase in ResearchPhase:
            state = self._phases[phase]
            color = PHASE_COLORS.get(phase, "white")
            glyph = state.glyph
            style = state.style

            parts = [f"  [{style}]{glyph}[/] [{color}]{phase.label}[/]"]
            if state.status == "active":
                parts.append(f"[dim]({state.duration_s:.0f}s · {state.tokens:,} tok)[/]")
            elif state.status == "complete":
                details = []
                if state.findings:
                    details.append(f"{state.findings} findings")
                if state.contradictions:
                    details.append(f"{state.contradictions} contradictions")
                if state.tokens:
                    details.append(f"{state.tokens:,} tok")
                if details:
                    parts.append(f"[dim]({' · '.join(details)})[/]")
            elif state.status == "error":
                parts.append("[red]✗ error[/]")

            lines.append(" ".join(parts))

        self.query_one("#rf-phases", Static).update("\n".join(lines) if lines else "")

    def _render_sources(self) -> None:
        if not self.expanded:
            self.query_one("#rf-sources", Static).update("")
            return

        discovery = self._phases[ResearchPhase.DISCOVERY]
        if not discovery.sources or discovery.status == "pending":
            self.query_one("#rf-sources", Static).update("")
            return

        lines = ["  [dim]Sources:[/]"]
        for source in discovery.sources:
            lines.append(source.line)

        self.query_one("#rf-sources", Static).update("\n".join(lines))

    def _render_summary(self) -> None:
        if not self.expanded or not any(s.status != "pending" for s in self._phases.values()):
            self.query_one("#rf-summary", Static).update("")
            return

        complete = sum(1 for s in self._phases.values() if s.status == "complete")
        total = len(self._phases)
        bar_w = 15
        f = int(complete / total * bar_w) if total > 0 else 0
        bar = "█" * f + "░" * (bar_w - f)

        summary = (
            f"  [dim]{bar}[/]  {complete}/{total} phases  ·  "
            f"{self.total_findings} findings  ·  "
            f"{self.total_contradictions} contradictions  ·  "
            f"{self.total_tokens:,} tokens"
        )
        self.query_one("#rf-summary", Static).update(summary)
