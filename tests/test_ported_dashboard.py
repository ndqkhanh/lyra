"""Port of lyra-ui tests/test_dashboard_viz.py → tests TUI agent_dashboard.py.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.textual


def test_agent_status_enum_values():
    from lyra_cli.tui_v2.widgets.agent_dashboard import AgentStatus
    for s in AgentStatus:
        assert s.glyph is not None
        assert s.style is not None


def test_agent_status_glyph():
    from lyra_cli.tui_v2.widgets.agent_dashboard import AgentStatus
    assert AgentStatus.IDLE.glyph == "○"
    assert AgentStatus.WORKING.glyph == "⏺"
    assert AgentStatus.THINKING.glyph == "✶"
    assert AgentStatus.DONE.glyph == "✓"
    assert AgentStatus.ERROR.glyph == "✗"


def test_agent_status_style():
    from lyra_cli.tui_v2.widgets.agent_dashboard import AgentStatus
    assert "dim" in AgentStatus.IDLE.style
    assert "cyan" in AgentStatus.WORKING.style
    assert "yellow" in AgentStatus.THINKING.style
    assert "green" in AgentStatus.DONE.style
    assert "red" in AgentStatus.ERROR.style


def test_task_status_glyph():
    from lyra_cli.tui_v2.widgets.agent_dashboard import TaskStatus
    assert TaskStatus.TODO.glyph == "◻"
    assert TaskStatus.DOING.glyph == "⏳"
    assert TaskStatus.DONE.glyph == "◼"
    assert TaskStatus.BLOCKED.glyph == "⚠"


def test_agent_info():
    from lyra_cli.tui_v2.widgets.agent_dashboard import AgentInfo, AgentStatus
    agent = AgentInfo(agent_id="a1", name="Worker", model="gpt-4o", status=AgentStatus.IDLE)
    assert agent.agent_id == "a1"
    assert agent.name == "Worker"
    assert agent.model == "gpt-4o"
    assert agent.status == AgentStatus.IDLE


def test_agent_info_line():
    from lyra_cli.tui_v2.widgets.agent_dashboard import AgentInfo, AgentStatus
    agent = AgentInfo(agent_id="a1", name="Worker", status=AgentStatus.WORKING)
    line = agent.line
    assert "Worker" in line
    assert AgentStatus.WORKING.glyph in line


def test_agent_info_with_emoji():
    from lyra_cli.tui_v2.widgets.agent_dashboard import AgentInfo
    agent = AgentInfo(agent_id="a1", name="Worker", emoji="🤖")
    assert "🤖" in agent.line


def test_task_item():
    from lyra_cli.tui_v2.widgets.agent_dashboard import TaskItem, TaskStatus
    task = TaskItem(task_id="t1", title="Build", status=TaskStatus.DOING, assignee="alice")
    assert task.task_id == "t1"
    assert task.title == "Build"
    assert task.assignee == "alice"
    assert "alice" in task.line


def test_monitor_event():
    from lyra_cli.tui_v2.widgets.agent_dashboard import MonitorEvent
    ev = MonitorEvent(level="error", message="Failure")
    assert ev.level == "error"
    assert "Failure" in ev.line


def test_dashboard_agent_lifecycle():
    from lyra_cli.tui_v2.widgets.agent_dashboard import AgentDashboardWidget, AgentStatus
    dash = AgentDashboardWidget()
    dash.register_agent("a1", "Worker-1", model="gpt-4o", emoji="🤖")
    assert "a1" in dash._agent_data

    dash.update_agent("a1", status=AgentStatus.DONE, tokens=5000, tool_uses=10)
    assert dash._agent_data["a1"].status == AgentStatus.DONE
    assert dash._agent_data["a1"].tokens == 5000

    dash.remove_agent("a1")
    assert "a1" not in dash._agent_data


def test_dashboard_task_lifecycle():
    from lyra_cli.tui_v2.widgets.agent_dashboard import AgentDashboardWidget, TaskStatus
    dash = AgentDashboardWidget()
    dash.add_task("t1", "Fix bug", status=TaskStatus.TODO, assignee="bob")
    assert "t1" in dash._task_data

    dash.update_task("t1", TaskStatus.DONE)
    assert dash._task_data["t1"].status == TaskStatus.DONE


def test_dashboard_logging():
    from lyra_cli.tui_v2.widgets.agent_dashboard import AgentDashboardWidget
    dash = AgentDashboardWidget()
    dash.log_event("info", "System started")
    dash.log_event("error", "Disk full")
    assert len(dash._event_log) == 2
    assert dash._event_log[0].level == "info"
    assert dash._event_log[1].level == "error"
