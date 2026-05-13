"""Rich Live() transparency panel for Lyra (Phase 3).

Subscribes to the EventBus and renders a real-time process dashboard using
Rich ``Live()`` + ``Layout``.  Designed to work in two modes:
  - Static: render a one-shot snapshot from `.lyra/process_state.json`
  - Live: subscribe to EventBus and refresh at 4 Hz

Layout::

    ┌── header: session · model · mode · elapsed · health ────────────┐
    ├── agents: process table (role, status, step, tokens, cost) ──────┤
    ├── events: last 8 tool calls with status and duration ────────────┤
    └── stats:  token burn rate · cache hit · cost/budget bar ─────────┘

Research grounding: Claude-Code-Usage-Monitor (6.1k stars, Rich Live() + Layout
pattern), Claude-Code-Agent-Monitor composite health score, Rich Progress + Group
for multi-agent bars.
"""
from __future__ import annotations

import asyncio
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from rich import box
from rich.columns import Columns
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn
from rich.table import Table
from rich.text import Text

from lyra_core.observability.event_bus import (
    CronJobFired,
    DaemonIteration,
    EventBus,
    LLMCallFinished,
    LLMCallStarted,
    PermissionDecision,
    StopHookFired,
    SubagentFinished,
    SubagentSpawned,
    ToolCallBlocked,
    ToolCallFinished,
    ToolCallStarted,
    get_event_bus,
)

# ---------------------------------------------------------------------------
# Display state (pure data — no Rich, easily testable)
# ---------------------------------------------------------------------------

_STATUS_COLORS = {
    "running": "green",
    "verifying": "yellow",
    "stopped": "dim white",
    "done": "dim white",
    "failed": "red",
    "killed": "red",
    "pending": "dim blue",
    "spawning": "blue",
    "parked": "yellow",
}


@dataclass
class AgentRow:
    """One row in the live agent process table."""

    agent_id: str
    agent_role: str
    status: str = "running"
    current_step: int = 0
    token_in: int = 0
    token_out: int = 0
    cache_hit: int = 0
    cost_usd: float = 0.0
    last_tool: str = "—"
    started_at: float = field(default_factory=time.time)
    permission_mode: str = ""

    def elapsed_s(self) -> float:
        return time.time() - self.started_at


@dataclass
class EventEntry:
    """One row in the live event log."""

    ts: str
    event_type: str
    name: str
    status: str
    duration_ms: float | None = None

    def status_text(self) -> Text:
        color = {
            "done": "green",
            "running": "yellow",
            "blocked": "red",
            "error": "red",
        }.get(self.status, "white")
        return Text(self.status, style=color)


@dataclass
class DisplayState:
    """All mutable state for the live display, updated by event handlers."""

    session_id: str = ""
    model: str = "—"
    permission_mode: str = "—"
    started_at: float = field(default_factory=time.time)

    agents: dict[str, AgentRow] = field(default_factory=dict)
    events: list[EventEntry] = field(default_factory=list)

    # Token / cost stats
    token_in_total: int = 0
    token_out_total: int = 0
    cache_hit_total: int = 0
    cost_total: float = 0.0
    budget_usd: float = 0.0

    # Daemon
    daemon_iteration: int = 0
    cron_last_job: str = "—"

    # Health axes (0–1)
    tool_error_count: int = 0
    tool_total_count: int = 0
    hook_block_count: int = 0

    MAX_EVENTS = 8

    def on_event(self, event: Any) -> None:
        """Update state from one EventBus event."""
        if isinstance(event, LLMCallStarted):
            self.model = event.model
            self.session_id = self.session_id or event.session_id
            row = self.agents.setdefault(
                event.session_id,
                AgentRow(agent_id=event.session_id, agent_role="root"),
            )
            row.current_step = event.turn

        elif isinstance(event, LLMCallFinished):
            self.token_in_total += event.input_tokens
            self.token_out_total += event.output_tokens
            self.cache_hit_total += event.cache_read_tokens
            row = self.agents.get(event.session_id)
            if row:
                row.token_in += event.input_tokens
                row.token_out += event.output_tokens
                row.cache_hit += event.cache_read_tokens

        elif isinstance(event, ToolCallStarted):
            self.tool_total_count += 1
            self._add_event(EventEntry(
                ts=_short_ts(),
                event_type="tool",
                name=event.tool_name,
                status="running",
            ))
            row = self.agents.get(event.session_id)
            if row:
                row.last_tool = event.tool_name

        elif isinstance(event, ToolCallFinished):
            self._update_last_event(event.tool_name, "error" if event.is_error else "done",
                                    event.duration_ms)
            if event.is_error:
                self.tool_error_count += 1

        elif isinstance(event, ToolCallBlocked):
            self.hook_block_count += 1
            self._add_event(EventEntry(
                ts=_short_ts(), event_type="blocked",
                name=event.tool_name, status="blocked",
            ))

        elif isinstance(event, SubagentSpawned):
            self.agents[event.agent_id] = AgentRow(
                agent_id=event.agent_id,
                agent_role=event.agent_role,
                status="running",
            )

        elif isinstance(event, SubagentFinished):
            row = self.agents.get(event.agent_id)
            if row:
                row.status = event.status
                row.cost_usd += event.cost_usd

        elif isinstance(event, StopHookFired):
            row = self.agents.get(event.session_id)
            if row:
                row.status = "stopped"

        elif isinstance(event, PermissionDecision):
            self.permission_mode = event.mode or self.permission_mode
            row = self.agents.get(event.session_id)
            if row:
                row.permission_mode = event.mode

        elif isinstance(event, DaemonIteration):
            self.daemon_iteration = event.iteration

        elif isinstance(event, CronJobFired):
            self.cron_last_job = event.job_name

    def health_score(self) -> float:
        """0–1 composite health.  Green > 0.7, Yellow > 0.4, Red ≤ 0.4."""
        error_rate = self.tool_error_count / max(1, self.tool_total_count)
        cached = self.cache_hit_total / max(1, self.token_in_total)
        block_rate = self.hook_block_count / max(1, self.tool_total_count)
        return (
            0.35 * (1 - error_rate)
            + 0.25 * cached
            + 0.25 * max(0.0, 1.0 - (self.token_in_total / max(1, _token_budget())))
            + 0.15 * (1 - block_rate)
        )

    def burn_rate_per_min(self) -> float:
        elapsed = max(1, time.time() - self.started_at)
        return (self.token_in_total + self.token_out_total) / elapsed * 60

    def _add_event(self, entry: EventEntry) -> None:
        self.events.append(entry)
        if len(self.events) > self.MAX_EVENTS:
            self.events.pop(0)

    def _update_last_event(self, name: str, status: str, duration_ms: float) -> None:
        for entry in reversed(self.events):
            if entry.name == name and entry.status == "running":
                entry.status = status
                entry.duration_ms = duration_ms
                return


def _short_ts() -> str:
    return datetime.now(tz=timezone.utc).strftime("%H:%M:%S")


def _token_budget() -> int:
    return 200_000  # default Claude budget


# ---------------------------------------------------------------------------
# Rich rendering helpers
# ---------------------------------------------------------------------------


def _health_color(score: float) -> str:
    if score >= 0.7:
        return "green"
    if score >= 0.4:
        return "yellow"
    return "red"


def render_header(state: DisplayState) -> Panel:
    elapsed = int(time.time() - state.started_at)
    h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
    elapsed_str = f"{h:02d}:{m:02d}:{s:02d}"
    score = state.health_score()
    color = _health_color(score)
    text = Text()
    text.append(f"  {state.session_id or 'no session'}  ", style="bold")
    text.append(f"model={state.model}  ")
    text.append(f"mode={state.permission_mode}  ")
    text.append(f"elapsed={elapsed_str}  ")
    text.append(f"health={score:.0%}", style=f"bold {color}")
    if state.daemon_iteration:
        text.append(f"  ⊙ daemon iter={state.daemon_iteration}", style="dim")
    return Panel(text, box=box.SIMPLE)


def render_agent_table(state: DisplayState) -> Panel:
    table = Table(box=box.SIMPLE, expand=True, show_header=True)
    table.add_column("Role", width=12)
    table.add_column("Status", width=10)
    table.add_column("Mode", width=8)
    table.add_column("Step", justify="right", width=6)
    table.add_column("Tok in", justify="right", width=8)
    table.add_column("Cache%", justify="right", width=7)
    table.add_column("Last tool", overflow="fold")

    for row in state.agents.values():
        color = _STATUS_COLORS.get(row.status, "white")
        cache_pct = row.cache_hit / max(1, row.token_in)
        table.add_row(
            row.agent_role or "root",
            f"[{color}]{row.status}[/{color}]",
            row.permission_mode or "—",
            str(row.current_step),
            f"{row.token_in:,}",
            f"{cache_pct:.0%}",
            row.last_tool,
        )

    if not state.agents:
        table.add_row("—", "—", "—", "—", "—", "—", "—")

    return Panel(table, title="Agents", box=box.ROUNDED)


def render_event_log(state: DisplayState) -> Panel:
    table = Table(box=box.SIMPLE, expand=True, show_header=True)
    table.add_column("Time", width=9, style="dim")
    table.add_column("Type", width=8)
    table.add_column("Name", overflow="fold")
    table.add_column("Status", width=8)
    table.add_column("ms", justify="right", width=7)

    for entry in reversed(state.events):
        dur = f"{entry.duration_ms:.0f}" if entry.duration_ms is not None else "—"
        table.add_row(entry.ts, entry.event_type, entry.name,
                      entry.status_text(), dur)

    if not state.events:
        table.add_row("—", "—", "—", "—", "—")

    return Panel(table, title="Tool Events (last 8)", box=box.ROUNDED)


def render_stats(state: DisplayState) -> Panel:
    burn = state.burn_rate_per_min()
    total_tokens = state.token_in_total + state.token_out_total
    cache_pct = state.cache_hit_total / max(1, state.token_in_total)

    prog = Progress(
        TextColumn("[dim]{task.description}"),
        BarColumn(bar_width=20),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        expand=False,
    )
    budget = _token_budget()
    prog.add_task("tokens", total=budget, completed=total_tokens)

    lines = Text()
    lines.append(f"burn rate: {burn:,.0f} tok/min\n", style="dim")
    lines.append(f"cache hit: {cache_pct:.1%}  ", style="green" if cache_pct >= 0.7 else "yellow")
    lines.append(f"total cost: ${state.cost_total:.4f}\n", style="dim")
    if state.cron_last_job != "—":
        lines.append(f"last cron: {state.cron_last_job}\n", style="dim")

    return Panel(Columns([lines, prog]), title="Stats", box=box.ROUNDED)


def build_layout(state: DisplayState) -> Layout:
    layout = Layout(name="root")
    layout.split_column(
        Layout(render_header(state), name="header", size=3),
        Layout(name="body", ratio=1),
    )
    layout["body"].split_row(
        Layout(render_agent_table(state), name="agents", ratio=2),
        Layout(name="right", ratio=1),
    )
    layout["right"].split_column(
        Layout(render_event_log(state), name="events", ratio=2),
        Layout(render_stats(state), name="stats", ratio=1),
    )
    return layout


# ---------------------------------------------------------------------------
# LiveDisplay — orchestrates the Live() loop
# ---------------------------------------------------------------------------


class LiveDisplay:
    """Rich Live() dashboard subscribed to the EventBus.

    Usage::
        display = LiveDisplay(bus=get_event_bus(), session_id="my-session")
        display.run()   # blocks; Ctrl-C to stop
    """

    def __init__(
        self,
        bus: EventBus | None = None,
        session_id: str = "",
        refresh_per_second: int = 4,
    ) -> None:
        self._bus = bus or get_event_bus()
        self._state = DisplayState(session_id=session_id)
        self._refresh = refresh_per_second
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=256)
        self._stop_event = threading.Event()

    def run(self) -> None:
        """Block and render until KeyboardInterrupt."""
        self._bus.subscribe(self._queue)
        console = Console()
        try:
            with Live(
                build_layout(self._state),
                console=console,
                refresh_per_second=self._refresh,
                screen=False,
            ) as live:
                while not self._stop_event.is_set():
                    self._drain_queue()
                    live.update(build_layout(self._state))
                    time.sleep(1 / self._refresh)
        except KeyboardInterrupt:
            pass
        finally:
            self._bus.unsubscribe(self._queue)

    def _drain_queue(self) -> None:
        while True:
            try:
                event = self._queue.get_nowait()
                self._state.on_event(event)
            except asyncio.QueueEmpty:
                break

    def stop(self) -> None:
        self._stop_event.set()

    @property
    def state(self) -> DisplayState:
        return self._state


__all__ = [
    "AgentRow",
    "DisplayState",
    "EventEntry",
    "LiveDisplay",
    "build_layout",
    "render_agent_table",
    "render_event_log",
    "render_header",
    "render_stats",
]
