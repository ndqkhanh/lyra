"""AgentDashboardWidget — fleet health, task Kanban, and monitoring feed.

Ports lyra-ui's agent_dashboard.py + dashboard_viz.py into a Textual widget.
Shows:
  • Agent fleet grid (id, status, model, tokens, duration)
  • Task Kanban board (todo / doing / done columns)
  • Live monitoring feed with timing and errors
  • ECC-style glyphs for agent status

Inspired by ECC's team-config + agent orchestration patterns.
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
from textual.widgets import Static, ListView, ListItem


# ── Enums ───────────────────────────────────────────────────────────────

class AgentStatus(Enum):
    IDLE = "idle"
    WORKING = "working"
    THINKING = "thinking"
    DONE = "done"
    ERROR = "error"

    @property
    def glyph(self) -> str:
        return {
            AgentStatus.IDLE: "○",
            AgentStatus.WORKING: "⏺",
            AgentStatus.THINKING: "✶",
            AgentStatus.DONE: "✓",
            AgentStatus.ERROR: "✗",
        }[self]

    @property
    def style(self) -> str:
        return {
            AgentStatus.IDLE: "dim",
            AgentStatus.WORKING: "bold cyan",
            AgentStatus.THINKING: "bold yellow",
            AgentStatus.DONE: "bold green",
            AgentStatus.ERROR: "bold red",
        }[self]


class TaskStatus(Enum):
    TODO = "todo"
    DOING = "doing"
    DONE = "done"
    BLOCKED = "blocked"

    @property
    def glyph(self) -> str:
        return {
            TaskStatus.TODO: "◻",
            TaskStatus.DOING: "⏳",
            TaskStatus.DONE: "◼",
            TaskStatus.BLOCKED: "⚠",
        }[self]


# ── Data models ─────────────────────────────────────────────────────────

@dataclass
class AgentInfo:
    """One agent in the fleet."""
    agent_id: str
    name: str
    model: str = ""
    status: AgentStatus = AgentStatus.IDLE
    tokens: int = 0
    tool_uses: int = 0
    started_at: float = 0.0
    phase: str = ""
    emoji: str = ""

    @property
    def duration_s(self) -> float:
        if self.started_at == 0:
            return 0.0
        return time.time() - self.started_at

    @property
    def line(self) -> str:
        glyph = f"[{self.status.style}]{self.status.glyph}[/]"
        emoji = f"{self.emoji} " if self.emoji else ""
        phase = f"[dim][{self.phase}][/] " if self.phase else ""
        dur = f"{self.duration_s:.0f}s" if self.duration_s > 0 else ""
        tok = f"· {self.tokens/1000:.1f}K tok" if self.tokens > 0 else ""
        model = f"· [dim]{self.model}[/]" if self.model else ""
        parts = [p for p in [dur, tok, model] if p]
        tail = f"  {' '.join(parts)}" if parts else ""
        return f"  {glyph} {emoji}{phase}{self.name}{tail}"


@dataclass
class TaskItem:
    """A task on the Kanban board."""
    task_id: str
    title: str
    status: TaskStatus = TaskStatus.TODO
    assignee: str = ""
    description: str = ""

    @property
    def line(self) -> str:
        glyph = f"[dim]{self.status.glyph}[/]"
        assignee = f" [dim]@{self.assignee}[/]" if self.assignee else ""
        return f"  {glyph} {self.title}{assignee}"


@dataclass
class MonitorEvent:
    """A monitoring feed event."""
    timestamp: float = field(default_factory=time.time)
    level: str = "info"  # info, success, warning, error
    message: str = ""

    @property
    def glyph(self) -> str:
        return {"info": "•", "success": "✓", "warning": "⚠", "error": "✗"}.get(self.level, "•")

    @property
    def style(self) -> str:
        return {"info": "dim", "success": "green", "warning": "yellow", "error": "red"}.get(self.level, "dim")

    @property
    def line(self) -> str:
        ts = time.strftime("%H:%M:%S", time.localtime(self.timestamp))
        return f"  [{self.style}]{self.glyph}[/] [dim]{ts}[/] {self.message}"


# ── Widget ──────────────────────────────────────────────────────────────

class AgentDashboardWidget(Widget):
    """Agent fleet dashboard with Kanban board and monitoring.

    Three sections in an accordion:
      1. Agent Fleet — grid of all agents with live status
      2. Task Board — Kanban (todo / doing / done)
      3. Monitoring — live event feed
    """

    DEFAULT_CSS = """
    AgentDashboardWidget {
        height: auto;
        border: solid $border;
        padding: 0 1;
        margin: 0 1;
    }

    AgentDashboardWidget.collapsed {
        height: 1;
        border: none;
    }

    AgentDashboardWidget #dash-header {
        height: 1;
        text-style: bold;
        color: $primary;
    }

    AgentDashboardWidget #dash-fleet {
        height: auto;
        margin: 0 0 0 1;
    }

    AgentDashboardWidget #dash-kanban {
        height: auto;
        margin: 0 0 0 1;
    }

    AgentDashboardWidget #dash-monitor {
        height: auto;
        max-height: 8;
        margin: 0 0 0 1;
    }

    AgentDashboardWidget .kanban-col {
        width: 1fr;
        border: solid $border;
    }

    AgentDashboardWidget .kanban-title {
        text-style: bold;
        color: $accent;
        height: 1;
    }

    AgentDashboardWidget .monitor-msg {
        height: 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+d", "toggle_dashboard", "Dashboard"),
    ]

    expanded: reactive[bool] = reactive(False)
    agents: reactive[dict] = reactive({})
    tasks: reactive[dict] = reactive({})
    events: reactive[list] = reactive([])

    def __init__(self):
        super().__init__()
        self._agent_data: dict[str, AgentInfo] = {}
        self._task_data: dict[str, TaskItem] = {}
        self._event_log: list[MonitorEvent] = []

    def compose(self) -> ComposeResult:
        yield Static("", id="dash-header")
        yield Static("", id="dash-fleet")
        yield Static("", id="dash-kanban")
        yield Static("", id="dash-monitor")

    def on_mount(self) -> None:
        self._render()

    # ── Public API ─────────────────────────────────────────────────────

    def register_agent(self, agent_id: str, name: str, model: str = "", emoji: str = "") -> None:
        self._agent_data[agent_id] = AgentInfo(
            agent_id=agent_id, name=name, model=model, emoji=emoji,
            status=AgentStatus.WORKING, started_at=time.time(),
        )
        self._sync_agents()

    def update_agent(
        self, agent_id: str, *,
        status: Optional[AgentStatus] = None,
        tokens: Optional[int] = None,
        tool_uses: Optional[int] = None,
        phase: Optional[str] = None,
    ) -> None:
        agent = self._agent_data.get(agent_id)
        if not agent:
            return
        if status:
            agent.status = status
        if tokens is not None:
            agent.tokens = tokens
        if tool_uses is not None:
            agent.tool_uses = tool_uses
        if phase is not None:
            agent.phase = phase
        self._sync_agents()

    def remove_agent(self, agent_id: str) -> None:
        self._agent_data.pop(agent_id, None)
        self._sync_agents()

    def add_task(self, task_id: str, title: str, status: TaskStatus = TaskStatus.TODO, assignee: str = "") -> None:
        self._task_data[task_id] = TaskItem(
            task_id=task_id, title=title, status=status, assignee=assignee,
        )
        self._sync_tasks()

    def update_task(self, task_id: str, status: TaskStatus) -> None:
        task = self._task_data.get(task_id)
        if task:
            task.status = status
            self._sync_tasks()

    def log_event(self, level: str, message: str) -> None:
        self._event_log.append(MonitorEvent(level=level, message=message))
        if len(self._event_log) > 50:
            self._event_log = self._event_log[-50:]
        self.events = [e.line for e in self._event_log[-10:]]

    # ── Actions ────────────────────────────────────────────────────────

    def action_toggle_dashboard(self) -> None:
        self.expanded = not self.expanded
        self.toggle_class("collapsed", not self.expanded)
        self._render()

    # ── Internal ───────────────────────────────────────────────────────

    def _sync_agents(self) -> None:
        self.agents = {aid: a.line for aid, a in self._agent_data.items()}
        self._render()

    def _sync_tasks(self) -> None:
        by_status = {}
        for t in self._task_data.values():
            by_status.setdefault(t.status, []).append(t.line)
        self.tasks = {s.name.lower(): items for s, items in by_status.items()}
        self._render()

    def _render(self) -> None:
        if not self.is_mounted:
            return
        try:
            self._render_header()
            self._render_fleet()
            self._render_kanban()
            self._render_monitor()
        except Exception:
            pass

    def _render_header(self) -> None:
        n = len(self._agent_data)
        n_working = sum(1 for a in self._agent_data.values() if a.status in (AgentStatus.WORKING, AgentStatus.THINKING))
        hint = "[dim](ctrl+d)[/]"
        status = f"[bold cyan]{n_working}[/] working · {n} total"
        if self.expanded:
            self.query_one("#dash-header", Static).update(f"⏺ Agents: {status}  {hint}")
        else:
            self.query_one("#dash-header", Static).update(f"⏺ Agents: {status}  {hint}")

    def _render_fleet(self) -> None:
        if not self.expanded or not self._agent_data:
            self.query_one("#dash-fleet", Static).update("")
            return
        lines = []
        for a in self._agent_data.values():
            lines.append(a.line)
        self.query_one("#dash-fleet", Static).update("\n".join(lines))

    def _render_kanban(self) -> None:
        if not self.expanded or not self._task_data:
            self.query_one("#dash-kanban", Static).update("")
            return

        cols = {TaskStatus.TODO: [], TaskStatus.DOING: [], TaskStatus.DONE: [], TaskStatus.BLOCKED: []}
        for t in self._task_data.values():
            cols.setdefault(t.status, []).append(t.line)

        sections = []
        for status, items in cols.items():
            if not items:
                continue
            glyph = status.glyph
            label = f"{glyph} {status.name}"
            section = f"  [bold]{label}[/] ({len(items)})"
            for item in items:
                section += f"\n{item}"
            sections.append(section)

        self.query_one("#dash-kanban", Static).update("\n\n".join(sections) if sections else "")

    def _render_monitor(self) -> None:
        if not self.expanded or not self._event_log:
            self.query_one("#dash-monitor", Static).update("")
            return
        lines = ["[dim]Monitor:[/]"]
        for e in self._event_log[-10:]:
            lines.append(e.line)
        self.query_one("#dash-monitor", Static).update("\n".join(lines))
