"""ProgressVizWidget — multi-step progress visualization.

Ports lyra_ui/progress_viz.py into the TUI as a widget showing:
  • Multi-step progress chains with ETA estimates
  • Per-step status (pending/running/done/failed/cancelled)
  • Timing breakdown (started, duration, ETA for running steps)
  • Overall progress bar with percentage
  • Expandable detail per step

ECC reference: research-playbook's structured phase tracking.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static


class StepState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def glyph(self) -> str:
        return {
            StepState.PENDING: "◻",
            StepState.RUNNING: "⏺",
            StepState.DONE: "✓",
            StepState.FAILED: "✗",
            StepState.CANCELLED: "—",
        }[self]

    @property
    def style(self) -> str:
        return {
            StepState.PENDING: "dim",
            StepState.RUNNING: "bold cyan",
            StepState.DONE: "bold green",
            StepState.FAILED: "bold red",
            StepState.CANCELLED: "dim",
        }[self]


@dataclass
class ProgressStep:
    """One step in a progress chain."""
    name: str
    description: str = ""
    state: StepState = StepState.PENDING
    progress: float = 0.0  # 0.0–1.0
    started_at: float = 0.0
    completed_at: float = 0.0
    total: int = 100
    current: int = 0

    @property
    def duration_s(self) -> float:
        if self.started_at == 0:
            return 0.0
        end = self.completed_at or time.time()
        return end - self.started_at

    @property
    def pct(self) -> float:
        return (self.current / self.total * 100) if self.total > 0 else 0.0

    @property
    def bar(self, width: int = 12) -> str:
        f = int(self.pct / 100 * width)
        return "█" * f + "░" * (width - f)

    @property
    def line(self) -> str:
        g = f"[{self.state.style}]{self.state.glyph}[/]"
        dur = f"[dim]{self.duration_s:.0f}s[/]" if self.duration_s > 1 else ""
        bar = f" {self.bar} {self.pct:.0f}%" if self.state == StepState.RUNNING else ""
        desc = f" [dim]— {self.description[:50]}[/]" if self.description else ""
        return f"  {g} [bold]{self.name}[/]{desc} {bar} {dur}"


class ProgressVizWidget(Widget):
    """Multi-step progress visualization panel.

    Shows a chain of steps with status glyphs, progress bars, and timing.
    """

    DEFAULT_CSS = """
    ProgressVizWidget {
        height: auto;
        border: solid $border;
        padding: 0 1;
        margin: 0 1;
    }

    ProgressVizWidget.collapsed {
        height: 1;
        border: none;
    }

    ProgressVizWidget #pv-header {
        height: 1;
        color: $text-muted;
    }

    ProgressVizWidget #pv-steps {
        height: auto;
        margin: 0 0 0 1;
    }

    ProgressVizWidget #pv-summary {
        height: 1;
        color: $text-muted;
        margin: 0 0 0 1;
    }

    ProgressVizWidget .pv-row {
        height: 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+shift+p", "toggle_progress_viz", "Progress Viz"),
    ]

    expanded: reactive[bool] = reactive(False)
    steps: reactive[list] = reactive([])
    chain_name: reactive[str] = reactive("")

    def __init__(self):
        super().__init__()
        self._step_data: list[ProgressStep] = []

    def compose(self) -> ComposeResult:
        yield Static("", id="pv-header")
        yield Static("", id="pv-steps")
        yield Static("", id="pv-summary")

    def on_mount(self) -> None:
        self._render()

    # ── Public API ─────────────────────────────────────────────────────

    def start_chain(self, name: str) -> None:
        """Start a new progress chain, clearing previous."""
        self._step_data = []
        self.chain_name = name
        self._render()

    def add_step(self, name: str, description: str = "", total: int = 100) -> None:
        """Add a step to the chain."""
        self._step_data.append(ProgressStep(
            name=name, description=description, total=total,
        ))
        self._sync_steps()

    def start_step(self, idx: int) -> None:
        """Mark step at index as running."""
        if 0 <= idx < len(self._step_data):
            self._step_data[idx].state = StepState.RUNNING
            self._step_data[idx].started_at = time.time()
            self._sync_steps()

    def update_step(self, idx: int, current: int) -> None:
        """Update step progress."""
        if 0 <= idx < len(self._step_data):
            self._step_data[idx].current = current
            self._sync_steps()

    def complete_step(self, idx: int, success: bool = True) -> None:
        """Mark step as completed or failed."""
        if 0 <= idx < len(self._step_data):
            self._step_data[idx].state = StepState.DONE if success else StepState.FAILED
            self._step_data[idx].completed_at = time.time()
            self._sync_steps()

    def fail_step(self, idx: int, reason: str = "") -> None:
        """Mark step as failed with reason."""
        if 0 <= idx < len(self._step_data):
            self._step_data[idx].state = StepState.FAILED
            self._step_data[idx].completed_at = time.time()
            self._step_data[idx].description = reason
            self._sync_steps()

    # ── Actions ────────────────────────────────────────────────────────

    def action_toggle_progress_viz(self) -> None:
        self.expanded = not self.expanded
        self.toggle_class("collapsed", not self.expanded)
        self._render()

    # ── Internal ───────────────────────────────────────────────────────

    def _sync_steps(self) -> None:
        self.steps = [s.line for s in self._step_data]
        self._render()

    def _render(self) -> None:
        if not self.is_mounted:
            return
        try:
            self._render_header()
            self._render_steps()
            self._render_summary()
        except Exception:
            pass

    def _render_header(self) -> None:
        hint = "[dim](ctrl+shift+p)[/]"
        name = f"[bold]{self.chain_name}[/]" if self.chain_name else "[bold]Progress[/]"
        done = sum(1 for s in self._step_data if s.state == StepState.DONE)
        total = len(self._step_data)
        pct = (done / total * 100) if total > 0 else 0

        if self.expanded:
            self.query_one("#pv-header", Static).update(
                f"{name}  [green]{done}[/]/{total}  {pct:.0f}%  {hint}"
            )
        else:
            self.query_one("#pv-header", Static).update(
                f"{name}  [green]{done}[/]/{total}  {pct:.0f}%  {hint}"
            )

    def _render_steps(self) -> None:
        if not self.expanded or not self._step_data:
            self.query_one("#pv-steps", Static).update("")
            return

        lines = [s.line for s in self._step_data]
        self.query_one("#pv-steps", Static).update("\n".join(lines))

    def _render_summary(self) -> None:
        if not self.expanded or not self._step_data:
            self.query_one("#pv-summary", Static).update("")
            return

        done = sum(1 for s in self._step_data if s.state == StepState.DONE)
        failed = sum(1 for s in self._step_data if s.state == StepState.FAILED)
        total = len(self._step_data)
        total_time = sum(s.duration_s for s in self._step_data)

        bar_w = 20
        f = int(done / total * bar_w) if total > 0 else 0
        bar = "█" * f + "░" * (bar_w - f)
        fail_str = f" [red]{failed} failed[/]" if failed else ""
        self.query_one("#pv-summary", Static).update(
            f"  {bar}  {done}/{total}  "
            f"[dim]{total_time:.0f}s total[/]{fail_str}"
        )
