"""FleetTUIApp — Terminal dashboard for Lyra agent fleet supervision."""

from __future__ import annotations

from typing import ClassVar, Optional

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Input, Static

from lyra_fleet_tui.models import (
    AgentFilter,
    AgentState,
    FleetData,
    FleetSummary,
    ProcessLiveness,
    TaskState,
)
from lyra_fleet_tui.widgets import (
    AgentRow,
    FilterBar,
    FleetTable,
    PeekPane,
    ReplyBar,
    StatusBar,
)

CSS = """
Screen {
    background: #0f1117;
}

#main-layout {
    layout: grid;
    grid-size: 1 3;
    grid-rows: auto 1fr auto;
    height: 100%;
}

#filter-bar {
    dock: top;
    height: 1;
    background: #1a1c23;
    padding: 0 1;
}

#table-container {
    height: 100%;
    border: solid #2d2f3a;
}

#fleet-table {
    height: 100%;
}

FleetTable {
    background: #0f1117;
    color: #c0c4d0;
}

FleetTable > .datatable--header {
    background: #1a1c23;
    color: #7a7f8a;
    text-style: bold;
}

FleetTable > .datatable--cursor {
    background: #2d3a5c;
}

FleetTable > .datatable--odd-row {
    background: #12141c;
}

FleetTable > .datatable--even-row {
    background: #181a22;
}

#peek-pane {
    dock: right;
    width: 48;
    height: 100%;
    background: #161822;
    border-left: solid #2d2f3a;
    padding: 1 2;
    overflow-y: auto;
}

#reply-bar {
    dock: bottom;
    height: 3;
    background: #1a1c23;
    border-top: solid #3d3f4a;
    padding: 0 1;
}

#status-bar {
    dock: bottom;
    height: 1;
    background: #12141c;
    color: #7a7f8a;
}

StatusBar {
    background: #12141c;
    color: #7a7f8a;
}

PeekPane {
    background: #161822;
    color: #c0c4d0;
}

ReplyBar {
    background: #1a1c23;
    color: #c0c4d0;
}

FilterBar {
    background: #1a1c23;
    color: #7a7f8a;
}
"""


class FleetTUIApp(App):
    """Terminal UI for monitoring and interacting with a Lyra agent fleet."""

    CSS = CSS

    TITLE = "Lyra Fleet TUI"
    SUB_TITLE = "Agent Fleet Supervisor"

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down", show=True),
        Binding("up", "cursor_up", "Up", show=True),
        Binding("enter", "peek_agent", "Peek", show=True),
        Binding("escape", "close_peek", "Close", show=True),
        Binding("r", "reply_agent", "Reply", show=True),
        Binding("f", "toggle_filter", "Filter", show=True),
        Binding("q", "quit_app", "Quit", show=True),
        Binding("slash", "search", "Search", show=True),
        Binding("1", "filter_working", "Working", show=False),
        Binding("2", "filter_needs_input", "Needs Input", show=False),
        Binding("3", "filter_idle", "Idle", show=False),
        Binding("4", "filter_completed", "Completed", show=False),
        Binding("5", "filter_failed", "Failed", show=False),
        Binding("6", "filter_stopped", "Stopped", show=False),
    ]

    def __init__(self, fleet_data: Optional[FleetData] = None) -> None:
        super().__init__()
        self._fleet_data = fleet_data or FleetData()
        self._summary = FleetSummary.from_fleet_data(self._fleet_data)
        self._filter: AgentFilter = AgentFilter()
        self._filtered_agents: list[AgentState] = list(self._fleet_data.agents)
        self._peeked_agent: Optional[AgentState] = None
        self._reply_active: bool = False
        self._search_active: bool = False
        self._filter_by_state: Optional[TaskState] = None

    def compose(self) -> ComposeResult:
        with Container(id="main-layout"):
            yield FilterBar(id="filter-bar")
            with Container(id="table-container"):
                yield FleetTable(id="fleet-table")
            with Container(id="peek-pane"):
                yield PeekPane(id="peek-pane")
            with Container(id="reply-bar"):
                yield ReplyBar(id="reply-bar")
            yield StatusBar(id="status-bar")

    def on_mount(self) -> None:
        self._refresh_display()

    # ---- Data updates ----

    def update_fleet(self, data: FleetData) -> None:
        """Called by the supervisor to push a new fleet snapshot."""
        self._fleet_data = data
        self._summary = FleetSummary.from_fleet_data(data)
        self._refresh_display()

    def _refresh_display(self) -> None:
        self._apply_filter()
        self.query_one(FleetTable).refresh_agents(
            FleetData(agents=self._filtered_agents)
        )
        self.query_one(StatusBar).summary = self._summary
        self.query_one(FilterBar).active_filter = (
            self._filter if self._filter.task_state or self._filter.search else None
        )

    def _apply_filter(self) -> None:
        if self._filter.task_state is None and not self._filter.search:
            self._filtered_agents = list(self._fleet_data.agents)
        else:
            self._filtered_agents = [
                a for a in self._fleet_data.agents if self._filter.matches(a)
            ]

    # ---- Actions ----

    def action_cursor_down(self) -> None:
        table = self.query_one(FleetTable)
        row, _ = table.cursor_coordinate
        if row < table.row_count - 1:
            table.move_cursor(row=row + 1)

    def action_cursor_up(self) -> None:
        table = self.query_one(FleetTable)
        row, _ = table.cursor_coordinate
        if row > 0:
            table.move_cursor(row=row - 1)

    def _selected_agent(self) -> Optional[AgentState]:
        table = self.query_one(FleetTable)
        row, _ = table.cursor_coordinate
        agents = self._filtered_agents
        if 0 <= row < len(agents):
            return agents[row]
        return None

    def action_peek_agent(self) -> None:
        agent = self._selected_agent()
        if agent:
            self._peeked_agent = agent
            self.query_one(PeekPane).agent = agent

    def action_close_peek(self) -> None:
        self._peeked_agent = None
        self.query_one(PeekPane).agent = None
        self.query_one(ReplyBar).deactivate()
        self._reply_active = False
        self._search_active = False

    def action_reply_agent(self) -> None:
        if not self._reply_active:
            agent = self._selected_agent()
            if agent and agent.task_state is TaskState.NEEDS_INPUT:
                self._reply_active = True
                self.query_one(ReplyBar).activate(agent)
            elif agent:
                self.query_one(PeekPane).agent = agent
                self.query_one(PeekPane).update(
                    self.query_one(PeekPane).render + "\n\n[bold yellow](Agent does not need input — reply ignored)[/]"
                )

    def action_toggle_filter(self) -> None:
        """Cycle through quick filter states or clear if already filtering."""
        if self._filter_by_state is not None:
            self._filter = AgentFilter()
            self._filter_by_state = None
        else:
            self._filter = AgentFilter.from_task_state(TaskState.WORKING)
            self._filter_by_state = TaskState.WORKING
        self._refresh_display()

    def action_search(self) -> None:
        """Placeholder: in a full implementation this would open a search Input."""
        pass

    def action_quit_app(self) -> None:
        self.exit()

    def action_filter_working(self) -> None:
        self._set_filter(TaskState.WORKING)

    def action_filter_needs_input(self) -> None:
        self._set_filter(TaskState.NEEDS_INPUT)

    def action_filter_idle(self) -> None:
        self._set_filter(TaskState.IDLE)

    def action_filter_completed(self) -> None:
        self._set_filter(TaskState.COMPLETED)

    def action_filter_failed(self) -> None:
        self._set_filter(TaskState.FAILED)

    def action_filter_stopped(self) -> None:
        self._set_filter(TaskState.STOPPED)

    def _set_filter(self, state: TaskState) -> None:
        if self._filter_by_state == state:
            self._filter = AgentFilter()
            self._filter_by_state = None
        else:
            self._filter = AgentFilter.from_task_state(state)
            self._filter_by_state = state
        self._refresh_display()

    def set_search_filter(self, query: str) -> None:
        self._filter = AgentFilter.from_search(query)
        self._filter_by_state = None
        self._refresh_display()
