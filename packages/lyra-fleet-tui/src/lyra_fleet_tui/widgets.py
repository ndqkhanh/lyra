"""Textual widgets for the Lyra Fleet TUI."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from textual import events
from textual.reactive import reactive
from textual.widgets import DataTable, Static

from lyra_fleet_tui.models import (
    AgentFilter,
    AgentState,
    FleetData,
    FleetSummary,
    ProcessLiveness,
    TaskState,
)

# ── Colour palette for task states ──────────────────────────────────────

TASK_COLORS: dict[TaskState, str] = {
    TaskState.WORKING: "bold cyan",
    TaskState.NEEDS_INPUT: "bold yellow",
    TaskState.IDLE: "grey62",
    TaskState.COMPLETED: "bold green",
    TaskState.FAILED: "bold red",
    TaskState.STOPPED: "grey35",
}

LIVENESS_COLORS: dict[ProcessLiveness, str] = {
    ProcessLiveness.ACTIVE: "cyan",
    ProcessLiveness.PAUSED: "yellow",
    ProcessLiveness.STOPPED: "grey35",
}


# ── AgentRow (single-line widget for list-view) ─────────────────────────


class AgentRow(Static):
    """A single agent summary row rendered with Rich markup."""

    agent: reactive[Optional[AgentState]] = reactive(None)

    def __init__(self, agent: Optional[AgentState] = None) -> None:
        super().__init__("")
        self.agent = agent

    def watch_agent(self, agent: Optional[AgentState]) -> None:
        if agent is None:
            self.update("")
            return
        ts = agent.task_state
        lv = agent.liveness
        color = TASK_COLORS.get(ts, "white")
        symbol = lv.symbol if lv else "?"
        tokens_fmt = _format_tokens(agent.tokens_used)
        cost_fmt = _format_cost(agent.cost_usd)
        name_trunc = agent.display_name[:20].ljust(20)
        task_trunc = (agent.current_task or "")[:30].ljust(30)
        branch_trunc = (agent.git_branch or "")[:12].ljust(12)
        lines = [
            f"[{color}]{symbol}[/] [{color}]{name_trunc}[/]",
            f"[grey62]{tokens_fmt:>10}  {cost_fmt:>8}[/]",
            f"[{color}]{task_trunc}[/]",
            f"[grey46]{branch_trunc}[/]",
            f"[grey46]{agent.model or '':>14}[/]",
        ]
        self.update(" │ ".join(lines))

    def on_click(self) -> None:
        if self.agent:
            self.post_message(self.SelectAgent(self.agent))

    class SelectAgent(events.Message):
        def __init__(self, agent: AgentState) -> None:
            super().__init__()
            self.agent = agent


# ── StatusBar ───────────────────────────────────────────────────────────


class StatusBar(Static):
    """Bottom status bar showing fleet summary counts."""

    summary: reactive[Optional[FleetSummary]] = reactive(None)

    def __init__(self) -> None:
        super().__init__("")

    def watch_summary(self, summary: Optional[FleetSummary]) -> None:
        if summary is None:
            self.update("[grey35]Waiting for fleet data...[/]")
            return
        parts = [
            f"Agents: [bold white]{summary.total_agents}[/]",
            f"Active: [bold cyan]{summary.active}[/]",
            f"Working: [bold cyan]{summary.working}[/]",
            f"Idle: [grey62]{summary.idle}[/]",
            f"Need Input: [bold yellow]{summary.needs_input}[/]",
            f"Completed: [bold green]{summary.completed}[/]",
            f"Failed: [bold red]{summary.failed}[/]",
            f"Stopped: [grey35]{summary.stopped}[/]",
            f"Tokens: [grey62]{_format_tokens(summary.total_tokens)}[/]",
            f"Cost: [grey62]${summary.total_cost:.2f}[/]",
        ]
        self.update("  │  ".join(parts))


# ── FleetTable ──────────────────────────────────────────────────────────


class FleetTable(DataTable):
    """DataTable of all fleet agents with rich column formatting."""

    def __init__(self) -> None:
        super().__init__()
        self.cursor_type = "row"
        self.show_cursor = True
        self.zebra_stripes = True
        self._build_columns()

    def _build_columns(self) -> None:
        self.add_column(" ", width=2)  # liveness symbol
        self.add_column("Agent", width=22)
        self.add_column("State", width=14)
        self.add_column("Tokens", width=10)
        self.add_column("Cost", width=8)
        self.add_column("Task", width=34)
        self.add_column("Branch", width=14)
        self.add_column("Model", width=16)
        self.add_column("Last Active", width=18)
        self.add_column("PR", width=14)

    def refresh_agents(self, data: FleetData) -> None:
        self.clear()
        for agent in data.agents:
            self.add_row(*self._agent_cells(agent))

    def _agent_cells(self, agent: AgentState) -> list[str]:
        color = TASK_COLORS.get(agent.task_state, "white")
        lv_color = LIVENESS_COLORS.get(agent.liveness, "grey35")
        symbol = agent.liveness.symbol if agent.liveness else "?"
        ts_label = agent.task_state.value.replace("_", " ").title()
        last_active_str = ""
        if agent.last_active:
            now = datetime.now(timezone.utc)
            delta = now - agent.last_active
            if delta.total_seconds() < 60:
                last_active_str = "just now"
            elif delta.total_seconds() < 3600:
                last_active_str = f"{int(delta.total_seconds() // 60)}m ago"
            elif delta.total_seconds() < 86400:
                last_active_str = f"{int(delta.total_seconds() // 3600)}h ago"
            else:
                last_active_str = f"{int(delta.total_seconds() // 86400)}d ago"
        return [
            f"[{lv_color}]{symbol}[/]",
            f"[{color}]{agent.display_name}[/]",
            f"[{color}]{ts_label}[/]",
            f"[grey62]{_format_tokens(agent.tokens_used)}[/]",
            f"[grey62]{_format_cost(agent.cost_usd)}[/]",
            f"[{color}]{(agent.current_task or '')[:34]}[/]",
            f"[grey46]{(agent.git_branch or '')[:14]}[/]",
            f"[grey46]{agent.model or ''}[/]",
            f"[grey46]{last_active_str}[/]",
            f"[grey46]{(agent.pr_label or '')[:14]}[/]",
        ]


# ── PeekPane ────────────────────────────────────────────────────────────


class PeekPane(Static):
    """Detail pane shown when an agent is selected / peeked."""

    agent: reactive[Optional[AgentState]] = reactive(None)

    def __init__(self) -> None:
        super().__init__("")
        self.border_title = "Agent Detail"
        self.visible = False

    def watch_agent(self, agent: Optional[AgentState]) -> None:
        if agent is None:
            self.visible = False
            self.update("")
            return
        self.visible = True
        color = TASK_COLORS.get(agent.task_state, "white")
        lv = agent.liveness
        symbol = lv.symbol if lv else "?"
        lines = [
            f"[bold]Agent:[/] [{color}]{agent.display_name}[/]",
            f"[bold]ID:[/]     {agent.agent_id}",
            f"[bold]State:[/]  [{color}]{agent.task_state.value.replace('_', ' ').title()}[/]   Liveness: [{LIVENESS_COLORS.get(agent.liveness, 'grey35')}]{agent.liveness.value.title()}[/] {symbol}",
            f"[bold]Model:[/]  {agent.model or '—'}",
            "",
            f"[bold]Current Task:[/]",
            f"  {agent.current_task or '—'}",
            "",
            f"[bold]Usage:[/]",
            f"  Tokens: {_format_tokens(agent.tokens_used)}   Cost: [yellow]${agent.cost_usd:.4f}[/]",
            "",
            f"[bold]Git:[/]",
            f"  Branch: {agent.git_branch or '—'}",
            f"  PR:     {agent.pr_label or '—'}",
            "",
            f"[bold]Last Active:[/] {agent.last_active.isoformat() if agent.last_active else '—'}",
            f"[bold]Pane ID:[/]     {agent.pane_id or '—'}",
        ]
        self.update("\n".join(lines))
        self.border_title = f"Agent: {agent.display_name}"


# ── ReplyBar ────────────────────────────────────────────────────────────


class ReplyBar(Static):
    """Minimal text input bar for replying to an agent with needs-input."""

    visible = False

    def __init__(self) -> None:
        super().__init__("")
        self.border_title = "Reply"
        self._active_agent: Optional[AgentState] = None

    def activate(self, agent: AgentState) -> None:
        self._active_agent = agent
        self.visible = True
        self.update(
            f"[bold yellow]Reply to {agent.display_name}:[/] type message and press Enter"
        )

    def deactivate(self) -> None:
        self._active_agent = None
        self.visible = False
        self.update("")

    @property
    def active_agent(self) -> Optional[AgentState]:
        return self._active_agent


# ── FilterBar ───────────────────────────────────────────────────────────


class FilterBar(Static):
    """Top filter bar showing the active AgentFilter with clear action."""

    active_filter: reactive[Optional[AgentFilter]] = reactive(None)

    def __init__(self) -> None:
        super().__init__("")

    def watch_active_filter(self, f: Optional[AgentFilter]) -> None:
        if f is None or (f.task_state is None and f.liveness is None and not f.search):
            self.update(
                "[grey35]No filter — showing all agents[/]"
            )
            return
        parts: list[str] = []
        if f.task_state is not None:
            color = TASK_COLORS.get(f.task_state, "white")
            parts.append(f"[{color}]state={f.task_state.value}[/]")
        if f.liveness is not None:
            lc = LIVENESS_COLORS.get(f.liveness, "grey35")
            parts.append(f"[{lc}]liveness={f.liveness.value}[/]")
        if f.search:
            parts.append(f"[grey62]search=\"[white]{f.search}[/]\"[/]")
        self.update(
            f"[bold]Filter:[/]  {'  '.join(parts)}   [grey35](Esc to clear)[/]"
        )


# ── Helpers ─────────────────────────────────────────────────────────────


def _format_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def _format_cost(c: float) -> str:
    if c >= 1:
        return f"${c:.2f}"
    if c >= 0.01:
        return f"${c:.4f}"
    return f"${c:.6f}"
