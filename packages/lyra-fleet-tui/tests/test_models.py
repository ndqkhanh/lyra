"""Tests for lyra_fleet_tui models."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from lyra_fleet_tui.models import (
    AgentFilter,
    AgentState,
    FleetData,
    FleetSummary,
    ProcessLiveness,
    TaskState,
)


class TestTaskState:
    def test_enum_values(self) -> None:
        assert TaskState.WORKING.value == "working"
        assert TaskState.NEEDS_INPUT.value == "needs_input"
        assert TaskState.IDLE.value == "idle"
        assert TaskState.COMPLETED.value == "completed"
        assert TaskState.FAILED.value == "failed"
        assert TaskState.STOPPED.value == "stopped"

    def test_enum_membership(self) -> None:
        assert set(TaskState) == {
            TaskState.WORKING,
            TaskState.NEEDS_INPUT,
            TaskState.IDLE,
            TaskState.COMPLETED,
            TaskState.FAILED,
            TaskState.STOPPED,
        }


class TestProcessLiveness:
    def test_enum_values(self) -> None:
        assert ProcessLiveness.ACTIVE.value == "active"
        assert ProcessLiveness.PAUSED.value == "paused"
        assert ProcessLiveness.STOPPED.value == "stopped"

    def test_symbol_active(self) -> None:
        assert ProcessLiveness.ACTIVE.symbol == "◉"

    def test_symbol_paused(self) -> None:
        assert ProcessLiveness.PAUSED.symbol == "•"

    def test_symbol_stopped(self) -> None:
        assert ProcessLiveness.STOPPED.symbol == "◎"

    def test_symbol_all_have_symbols(self) -> None:
        for pl in ProcessLiveness:
            assert isinstance(pl.symbol, str)
            assert len(pl.symbol) >= 1


class TestAgentState:
    def test_frozen_dataclass(self) -> None:
        agent = AgentState(agent_id="ag-001", name="coder-alpha")
        assert agent.agent_id == "ag-001"
        assert agent.name == "coder-alpha"
        with pytest.raises(AttributeError):
            agent.name = "other"  # type: ignore[misc]

    def test_defaults(self) -> None:
        agent = AgentState(agent_id="ag-001", name="coder-alpha")
        assert agent.task_state is TaskState.IDLE
        assert agent.liveness is ProcessLiveness.STOPPED
        assert agent.model == ""
        assert agent.tokens_used == 0
        assert agent.cost_usd == 0.0
        assert agent.current_task == ""
        assert agent.last_active is None
        assert agent.git_branch == ""
        assert agent.pr_label == ""
        assert agent.pane_id == ""

    def test_display_name_uses_name(self) -> None:
        agent = AgentState(agent_id="ag-001", name="coder-alpha")
        assert agent.display_name == "coder-alpha"

    def test_display_name_falls_back_to_agent_id(self) -> None:
        agent = AgentState(agent_id="very-long-agent-id-12345", name="")
        assert agent.display_name == "very-long-agent-"

    def test_display_name_truncated(self) -> None:
        agent = AgentState(agent_id="ag-001", name="x" * 30)
        assert len(agent.display_name) == 16

    def test_with_all_fields(self) -> None:
        now = datetime.now(timezone.utc)
        agent = AgentState(
            agent_id="ag-999",
            name="researcher",
            task_state=TaskState.WORKING,
            liveness=ProcessLiveness.ACTIVE,
            model="claude-sonnet-4",
            tokens_used=15000,
            cost_usd=0.75,
            current_task="Analyze logs",
            last_active=now,
            git_branch="fix/log-analysis",
            pr_label="PR #42",
            pane_id="pane-3",
        )
        assert agent.cost_usd == 0.75
        assert agent.last_active is now
        assert agent.pr_label == "PR #42"


class TestFleetData:
    def test_empty_default(self) -> None:
        data = FleetData()
        assert data.agents == []
        assert data.totals == {}
        assert data.total_count == 0
        assert data.active_count == 0
        assert data.working_count == 0

    def test_counts(self) -> None:
        agents = [
            AgentState(agent_id="a1", name="one", liveness=ProcessLiveness.ACTIVE, task_state=TaskState.WORKING),
            AgentState(agent_id="a2", name="two", liveness=ProcessLiveness.ACTIVE, task_state=TaskState.IDLE),
            AgentState(agent_id="a3", name="three", liveness=ProcessLiveness.PAUSED, task_state=TaskState.COMPLETED),
        ]
        data = FleetData(agents=agents)
        assert data.total_count == 3
        assert data.active_count == 2
        assert data.working_count == 1


class TestFleetSummary:
    def test_from_empty_data(self) -> None:
        summary = FleetSummary.from_fleet_data(FleetData())
        assert summary.total_agents == 0
        assert summary.total_tokens == 0
        assert summary.total_cost == 0.0

    def test_from_data_with_agents(self) -> None:
        agents = [
            AgentState(
                agent_id="a1", name="one",
                task_state=TaskState.WORKING,
                liveness=ProcessLiveness.ACTIVE,
                tokens_used=1000,
                cost_usd=0.05,
            ),
            AgentState(
                agent_id="a2", name="two",
                task_state=TaskState.FAILED,
                liveness=ProcessLiveness.STOPPED,
                tokens_used=500,
                cost_usd=0.02,
            ),
            AgentState(
                agent_id="a3", name="three",
                task_state=TaskState.NEEDS_INPUT,
                liveness=ProcessLiveness.ACTIVE,
                tokens_used=2000,
                cost_usd=0.10,
            ),
        ]
        data = FleetData(agents=agents)
        summary = FleetSummary.from_fleet_data(data)
        assert summary.total_agents == 3
        assert summary.working == 1
        assert summary.failed == 1
        assert summary.needs_input == 1
        assert summary.active == 2
        assert summary.stopped == 1
        assert summary.total_tokens == 3500
        assert summary.total_cost == 0.17

    def test_by_liveness_and_task_state(self) -> None:
        agents = [
            AgentState(agent_id="a1", name="one", task_state=TaskState.WORKING, liveness=ProcessLiveness.ACTIVE),
            AgentState(agent_id="a2", name="two", task_state=TaskState.IDLE, liveness=ProcessLiveness.ACTIVE),
            AgentState(agent_id="a3", name="three", task_state=TaskState.STOPPED, liveness=ProcessLiveness.STOPPED),
        ]
        data = FleetData(agents=agents)
        summary = FleetSummary.from_fleet_data(data)
        assert summary.by_liveness.get("active", 0) == 2
        assert summary.by_liveness.get("stopped", 0) == 1
        assert summary.by_liveness.get("paused", 0) == 0
        assert summary.by_task_state.get("working", 0) == 1
        assert summary.by_task_state.get("idle", 0) == 1
        assert summary.by_task_state.get("stopped", 0) == 1


class TestAgentFilter:
    def test_no_filter_matches_all(self) -> None:
        f = AgentFilter()
        agent = AgentState(agent_id="a1", name="anything")
        assert f.matches(agent) is True

    def test_filter_by_task_state(self) -> None:
        f = AgentFilter.from_task_state(TaskState.WORKING)
        working = AgentState(agent_id="a1", name="w", task_state=TaskState.WORKING)
        idle = AgentState(agent_id="a2", name="i", task_state=TaskState.IDLE)
        assert f.matches(working) is True
        assert f.matches(idle) is False

    def test_filter_by_liveness(self) -> None:
        f = AgentFilter.from_liveness(ProcessLiveness.ACTIVE)
        active = AgentState(agent_id="a1", name="a", liveness=ProcessLiveness.ACTIVE)
        stopped = AgentState(agent_id="a2", name="s", liveness=ProcessLiveness.STOPPED)
        assert f.matches(active) is True
        assert f.matches(stopped) is False

    def test_filter_by_search_name(self) -> None:
        f = AgentFilter.from_search("coder")
        match = AgentState(agent_id="a1", name="coder-alpha")
        no = AgentState(agent_id="a2", name="helper-bot")
        assert f.matches(match) is True
        assert f.matches(no) is False

    def test_filter_by_search_agent_id(self) -> None:
        f = AgentFilter.from_search("ag-99")
        match = AgentState(agent_id="ag-99", name="bot")
        assert f.matches(match) is True

    def test_filter_by_search_current_task(self) -> None:
        f = AgentFilter.from_search("analyze")
        match = AgentState(agent_id="a1", name="bot", current_task="Analyze logs")
        assert f.matches(match) is True

    def test_filter_combined(self) -> None:
        f = AgentFilter(task_state=TaskState.WORKING, search="coder")
        good = AgentState(agent_id="a1", name="coder-alpha", task_state=TaskState.WORKING)
        wrong_state = AgentState(agent_id="a2", name="coder-beta", task_state=TaskState.IDLE)
        wrong_name = AgentState(agent_id="a3", name="helper", task_state=TaskState.WORKING)
        assert f.matches(good) is True
        assert f.matches(wrong_state) is False
        assert f.matches(wrong_name) is False

    def test_clone(self) -> None:
        f = AgentFilter(task_state=TaskState.WORKING, search="bot")
        clone = f.clone()
        assert clone.task_state is TaskState.WORKING
        assert clone.search == "bot"
        assert clone is not f

    def test_from_task_state_classmethod(self) -> None:
        f = AgentFilter.from_task_state(TaskState.FAILED)
        assert f.task_state is TaskState.FAILED
        assert f.liveness is None
        assert f.search == ""

    def test_from_liveness_classmethod(self) -> None:
        f = AgentFilter.from_liveness(ProcessLiveness.PAUSED)
        assert f.liveness is ProcessLiveness.PAUSED
        assert f.task_state is None

    def test_from_search_classmethod(self) -> None:
        f = AgentFilter.from_search("query")
        assert f.search == "query"
        assert f.task_state is None
