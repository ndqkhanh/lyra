"""Tests for lyra_fleet_tui widgets."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from textual.app import App, ComposeResult

from lyra_fleet_tui.models import (
    AgentFilter,
    AgentState,
    FleetData,
    FleetSummary,
    ProcessLiveness,
    TaskState,
)
from lyra_fleet_tui.widgets import (
    FilterBar,
    FleetTable,
    PeekPane,
    ReplyBar,
    StatusBar,
    TASK_COLORS,
    _format_cost,
    _format_tokens,
)

# ── Helper fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def sample_agent() -> AgentState:
    return AgentState(
        agent_id="ag-001",
        name="coder-alpha",
        task_state=TaskState.WORKING,
        liveness=ProcessLiveness.ACTIVE,
        model="claude-sonnet-4",
        tokens_used=15_000,
        cost_usd=0.75,
        current_task="Refactor database layer",
        last_active=datetime.now(timezone.utc),
        git_branch="feat/db-refactor",
        pr_label="PR #12",
        pane_id="pane-0",
    )


@pytest.fixture
def sample_data() -> FleetData:
    agents = [
        AgentState(
            agent_id="ag-001", name="coder-alpha",
            task_state=TaskState.WORKING, liveness=ProcessLiveness.ACTIVE,
            tokens_used=15000, cost_usd=0.75,
            current_task="Refactor DB", git_branch="feat/db",
        ),
        AgentState(
            agent_id="ag-002", name="researcher",
            task_state=TaskState.IDLE, liveness=ProcessLiveness.ACTIVE,
            tokens_used=500, cost_usd=0.02,
        ),
        AgentState(
            agent_id="ag-003", name="tester",
            task_state=TaskState.FAILED, liveness=ProcessLiveness.STOPPED,
            tokens_used=3000, cost_usd=0.15,
            current_task="Run integration tests",
        ),
    ]
    return FleetData(agents=agents)


# ── _format_tokens / _format_cost helpers ───────────────────────────────


class TestFormatHelpers:
    def test_format_tokens_zero(self) -> None:
        assert _format_tokens(0) == "0"

    def test_format_tokens_thousands(self) -> None:
        assert _format_tokens(1500) == "1.5K"

    def test_format_tokens_millions(self) -> None:
        assert _format_tokens(2_500_000) == "2.5M"

    def test_format_tokens_under_thousand(self) -> None:
        assert _format_tokens(999) == "999"

    def test_format_cost_dollars(self) -> None:
        result = _format_cost(5.0)
        assert result == "$5.00"

    def test_format_cost_cents(self) -> None:
        result = _format_cost(0.25)
        assert result == "$0.2500"

    def test_format_cost_subcent(self) -> None:
        result = _format_cost(0.001234)
        assert result.startswith("$0.001234")

    def test_format_cost_tiny(self) -> None:
        result = _format_cost(1e-5)
        assert result.startswith("$0.00001")


# ── TASK_COLORS constants ────────────────────────────────────────────────


class TestTaskColors:
    def test_all_task_states_have_colors(self) -> None:
        for state in TaskState:
            assert state in TASK_COLORS
            assert isinstance(TASK_COLORS[state], str)
            assert len(TASK_COLORS[state]) > 0

    def test_colors_are_reasonable(self) -> None:
        assert "cyan" in TASK_COLORS[TaskState.WORKING]
        assert "yellow" in TASK_COLORS[TaskState.NEEDS_INPUT]
        assert "green" in TASK_COLORS[TaskState.COMPLETED]
        assert "red" in TASK_COLORS[TaskState.FAILED]


# ── FleetTable (needs app context) ──────────────────────────────────────


class FleetTableTestApp(App):
    """Minimal app that hosts a FleetTable."""

    def compose(self) -> ComposeResult:
        yield FleetTable()


@pytest.mark.asyncio
async def test_fleet_table_initialized() -> None:
    """FleetTable can be mounted in an app and shows columns."""
    app = FleetTableTestApp()
    async with app.run_test() as pilot:
        table = app.query_one(FleetTable)
        assert table is not None
        assert table.cursor_type == "row"
        assert table.show_cursor is True
        assert len(table.columns) >= 8


@pytest.mark.asyncio
async def test_fleet_table_refresh_agents_empty() -> None:
    """refresh_agents with empty data results in zero rows."""
    app = FleetTableTestApp()
    async with app.run_test() as pilot:
        table = app.query_one(FleetTable)
        table.refresh_agents(FleetData())
        assert table.row_count == 0


@pytest.mark.asyncio
async def test_fleet_table_refresh_agents_with_data(sample_data: FleetData) -> None:
    """refresh_agents with data populates rows."""
    app = FleetTableTestApp()
    async with app.run_test() as pilot:
        table = app.query_one(FleetTable)
        table.refresh_agents(sample_data)
        assert table.row_count == 3


@pytest.mark.asyncio
async def test_fleet_table_clears_previous(sample_data: FleetData) -> None:
    """Repeated refresh_agents replaces rows."""
    app = FleetTableTestApp()
    async with app.run_test() as pilot:
        table = app.query_one(FleetTable)
        table.refresh_agents(sample_data)
        assert table.row_count == 3
        table.refresh_agents(FleetData())
        assert table.row_count == 0


@pytest.mark.asyncio
async def test_fleet_table_agent_cells_include_symbol(sample_data: FleetData) -> None:
    """Agent cells contain the liveness symbol."""
    app = FleetTableTestApp()
    async with app.run_test() as pilot:
        table = app.query_one(FleetTable)
        table.refresh_agents(sample_data)
        row_one = table.get_row_at(0)
        assert any("◉" in str(c) for c in row_one)


# ── PeekPane (needs app context) ────────────────────────────────────────


class PeekPaneTestApp(App):
    def compose(self) -> ComposeResult:
        yield PeekPane()


@pytest.mark.asyncio
async def test_peek_pane_initially_hidden() -> None:
    """PeekPane starts with no agent."""
    app = PeekPaneTestApp()
    async with app.run_test() as pilot:
        pane = app.query_one(PeekPane)
        assert pane.agent is None


@pytest.mark.asyncio
async def test_peek_pane_set_agent(sample_agent: AgentState) -> None:
    """Setting agent on PeekPane makes it visible and shows details."""
    app = PeekPaneTestApp()
    async with app.run_test() as pilot:
        pane = app.query_one(PeekPane)
        pane.agent = sample_agent
        await pilot.pause()
        assert pane.visible is True
        assert sample_agent.display_name in pane.border_title


@pytest.mark.asyncio
async def test_peek_pane_clear_agent(sample_agent: AgentState) -> None:
    """Setting agent to None hides the PeekPane."""
    app = PeekPaneTestApp()
    async with app.run_test() as pilot:
        pane = app.query_one(PeekPane)
        pane.agent = sample_agent
        await pilot.pause()
        pane.agent = None
        await pilot.pause()
        assert pane.visible is False


@pytest.mark.asyncio
async def test_peek_pane_renders_cost(sample_agent: AgentState) -> None:
    """PeekPane content includes cost when agent is set."""
    app = PeekPaneTestApp()
    async with app.run_test() as pilot:
        pane = app.query_one(PeekPane)
        pane.agent = sample_agent
        await pilot.pause()
        assert "0.75" in str(pane.render().plain)


# ── ReplyBar (needs app context) ────────────────────────────────────────


class ReplyBarTestApp(App):
    def compose(self) -> ComposeResult:
        yield ReplyBar()


@pytest.mark.asyncio
async def test_reply_bar_initially_hidden() -> None:
    """ReplyBar starts hidden."""
    app = ReplyBarTestApp()
    async with app.run_test() as pilot:
        bar = app.query_one(ReplyBar)
        assert bar.visible is False
        assert bar.active_agent is None


@pytest.mark.asyncio
async def test_reply_bar_activate(sample_agent: AgentState) -> None:
    """Activating ReplyBar makes it visible and stores the agent."""
    app = ReplyBarTestApp()
    async with app.run_test() as pilot:
        bar = app.query_one(ReplyBar)
        bar.activate(sample_agent)
        await pilot.pause()
        assert bar.visible is True
        assert bar.active_agent is sample_agent


@pytest.mark.asyncio
async def test_reply_bar_deactivate(sample_agent: AgentState) -> None:
    """Deactivating ReplyBar hides it and clears the agent."""
    app = ReplyBarTestApp()
    async with app.run_test() as pilot:
        bar = app.query_one(ReplyBar)
        bar.activate(sample_agent)
        await pilot.pause()
        bar.deactivate()
        assert bar.visible is False
        assert bar.active_agent is None


@pytest.mark.asyncio
async def test_reply_bar_content_shows_agent_name(sample_agent: AgentState) -> None:
    """ReplyBar content contains agent name when activated."""
    app = ReplyBarTestApp()
    async with app.run_test() as pilot:
        bar = app.query_one(ReplyBar)
        bar.activate(sample_agent)
        await pilot.pause()
        assert "coder-alpha" in bar.content


@pytest.mark.asyncio
async def test_reply_bar_content_empty_after_deactivate(sample_agent: AgentState) -> None:
    """ReplyBar content is empty after deactivation."""
    app = ReplyBarTestApp()
    async with app.run_test() as pilot:
        bar = app.query_one(ReplyBar)
        bar.activate(sample_agent)
        await pilot.pause()
        bar.deactivate()
        assert bar.content == ""


# ── StatusBar (needs app context) ───────────────────────────────────────


class StatusBarTestApp(App):
    def compose(self) -> ComposeResult:
        yield StatusBar()


@pytest.mark.asyncio
async def test_status_bar_initial_message() -> None:
    """StatusBar shows waiting message initially."""
    app = StatusBarTestApp()
    async with app.run_test() as pilot:
        bar = app.query_one(StatusBar)
        assert "Waiting" in bar.content


@pytest.mark.asyncio
async def test_status_bar_with_empty_summary() -> None:
    """StatusBar with empty summary shows zeros."""
    app = StatusBarTestApp()
    async with app.run_test() as pilot:
        bar = app.query_one(StatusBar)
        bar.summary = FleetSummary.from_fleet_data(FleetData())
        await pilot.pause()
        assert "0" in bar.content


@pytest.mark.asyncio
async def test_status_bar_with_data(sample_data: FleetData) -> None:
    """StatusBar shows correct counts from FleetData."""
    app = StatusBarTestApp()
    async with app.run_test() as pilot:
        bar = app.query_one(StatusBar)
        bar.summary = FleetSummary.from_fleet_data(sample_data)
        await pilot.pause()
        assert "3" in bar.content


# ── FilterBar (needs app context) ───────────────────────────────────────


class FilterBarTestApp(App):
    def compose(self) -> ComposeResult:
        yield FilterBar()


@pytest.mark.asyncio
async def test_filter_bar_init() -> None:
    """FilterBar shows 'no filter' initially."""
    app = FilterBarTestApp()
    async with app.run_test() as pilot:
        bar = app.query_one(FilterBar)
        rendered = bar.content
        assert "No filter" in rendered


@pytest.mark.asyncio
async def test_filter_bar_none() -> None:
    """Setting FilterBar filter to None shows 'no filter'."""
    app = FilterBarTestApp()
    async with app.run_test() as pilot:
        bar = app.query_one(FilterBar)
        bar.active_filter = None
        await pilot.pause()
        rendered = bar.content
        assert "No filter" in rendered


@pytest.mark.asyncio
async def test_filter_bar_empty_filter() -> None:
    """Setting FilterBar with empty filter shows 'no filter'."""
    app = FilterBarTestApp()
    async with app.run_test() as pilot:
        bar = app.query_one(FilterBar)
        bar.active_filter = AgentFilter()
        await pilot.pause()
        rendered = bar.content
        assert "No filter" in rendered


@pytest.mark.asyncio
async def test_filter_bar_by_state() -> None:
    """FilterBar displays the task state filter."""
    app = FilterBarTestApp()
    async with app.run_test() as pilot:
        bar = app.query_one(FilterBar)
        bar.active_filter = AgentFilter.from_task_state(TaskState.FAILED)
        await pilot.pause()
        rendered = bar.content
        assert "failed" in rendered.lower()


@pytest.mark.asyncio
async def test_filter_bar_by_search() -> None:
    """FilterBar displays the search query."""
    app = FilterBarTestApp()
    async with app.run_test() as pilot:
        bar = app.query_one(FilterBar)
        bar.active_filter = AgentFilter.from_search("agent-42")
        await pilot.pause()
        rendered = bar.content
        assert "agent-42" in rendered


@pytest.mark.asyncio
async def test_filter_bar_shows_clear_action() -> None:
    """FilterBar shows hint about clearing when filter is active."""
    app = FilterBarTestApp()
    async with app.run_test() as pilot:
        bar = app.query_one(FilterBar)
        bar.active_filter = AgentFilter.from_task_state(TaskState.WORKING)
        await pilot.pause()
        rendered = bar.content
        assert "Esc" in rendered or "clear" in rendered.lower()


@pytest.mark.asyncio
async def test_filter_bar_combined_search_and_state() -> None:
    """FilterBar displays both search and state filter simultaneously."""
    app = FilterBarTestApp()
    async with app.run_test() as pilot:
        bar = app.query_one(FilterBar)
        f = AgentFilter(task_state=TaskState.WORKING, search="db")
        bar.active_filter = f
        await pilot.pause()
        rendered = bar.content
        assert "working" in rendered
        assert "db" in rendered
