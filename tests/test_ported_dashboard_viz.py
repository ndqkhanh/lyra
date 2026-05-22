"""Port of lyra-ui tests/test_dashboard_viz.py → tests TUI agent_dashboard.py.

The original tested AgentFleetManager, TaskBoard, MonitoringPanel as
separate classes. In our TUI, all of these are rolled into
AgentDashboardWidget — so tests target the widget's internal API.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.textual


def test_dashboard_widget_init():
    from lyra_cli.tui_v2.widgets.agent_dashboard import AgentDashboardWidget
    dash = AgentDashboardWidget()
    assert dash is not None
    assert len(dash._agent_data) == 0
    assert len(dash._task_data) == 0
    assert len(dash._event_log) == 0


def test_agent_lifecycle():
    from lyra_cli.tui_v2.widgets.agent_dashboard import AgentDashboardWidget, AgentStatus
    dash = AgentDashboardWidget()
    dash.register_agent("a1", "Agent-1", model="gpt-4o", emoji="🤖")
    assert "a1" in dash._agent_data

    dash.update_agent("a1", status=AgentStatus.WORKING, tokens=1000, tool_uses=5)
    assert dash._agent_data["a1"].status == AgentStatus.WORKING
    assert dash._agent_data["a1"].tokens == 1000

    dash.remove_agent("a1")
    assert "a1" not in dash._agent_data


def test_task_lifecycle():
    from lyra_cli.tui_v2.widgets.agent_dashboard import AgentDashboardWidget, TaskStatus
    dash = AgentDashboardWidget()
    dash.add_task("t1", "Build feature", status=TaskStatus.TODO, assignee="alice")
    assert "t1" in dash._task_data

    dash.update_task("t1", TaskStatus.DOING)
    assert dash._task_data["t1"].status == TaskStatus.DOING


def test_monitoring_feed():
    from lyra_cli.tui_v2.widgets.agent_dashboard import AgentDashboardWidget
    dash = AgentDashboardWidget()
    dash.log_event("info", "System started")
    dash.log_event("success", "Task completed")
    dash.log_event("error", "Task failed")

    assert len(dash._event_log) == 3
    levels = [e.level for e in dash._event_log]
    assert "info" in levels
    assert "error" in levels


def test_agent_status_enum():
    from lyra_cli.tui_v2.widgets.agent_dashboard import AgentStatus
    assert AgentStatus.IDLE.glyph == "○"
    assert AgentStatus.WORKING.glyph == "⏺"
    assert AgentStatus.DONE.glyph == "✓"
    assert AgentStatus.ERROR.glyph == "✗"
    assert "dim" in AgentStatus.IDLE.style
    assert "green" in AgentStatus.DONE.style


def test_task_status_enum():
    from lyra_cli.tui_v2.widgets.agent_dashboard import TaskStatus
    assert TaskStatus.TODO.glyph == "◻"
    assert TaskStatus.DOING.glyph == "⏳"
    assert TaskStatus.DONE.glyph == "◼"
    assert TaskStatus.BLOCKED.glyph == "⚠"


def test_agent_info():
    from lyra_cli.tui_v2.widgets.agent_dashboard import AgentInfo, AgentStatus
    agent = AgentInfo(agent_id="a1", name="Worker", model="deepseek", status=AgentStatus.WORKING, emoji="🤖")
    line = agent.line
    assert "Worker" in line
    assert "🤖" in line
    assert "deepseek" in line


def test_task_item():
    from lyra_cli.tui_v2.widgets.agent_dashboard import TaskItem, TaskStatus
    task = TaskItem(task_id="t1", title="Fix bug", status=TaskStatus.DOING, assignee="bob")
    assert "Fix bug" in task.line
    assert "@bob" in task.line


def test_monitor_event():
    from lyra_cli.tui_v2.widgets.agent_dashboard import MonitorEvent
    ev = MonitorEvent(level="warning", message="Disk usage high")
    assert "Disk" in ev.line
    assert "⚠" in ev.line


def test_dashboard_multiple_agents():
    from lyra_cli.tui_v2.widgets.agent_dashboard import AgentDashboardWidget, AgentStatus
    dash = AgentDashboardWidget()
    for i in range(5):
        dash.register_agent(f"a{i}", f"Agent-{i}", model="gpt-4o")
    assert len(dash._agent_data) == 5

    # Update some
    dash.update_agent("a0", status=AgentStatus.DONE)
    dash.update_agent("a1", status=AgentStatus.ERROR)
    assert dash._agent_data["a0"].status == AgentStatus.DONE
    assert dash._agent_data["a1"].status == AgentStatus.ERROR


def test_dashboard_multiple_tasks():
    from lyra_cli.tui_v2.widgets.agent_dashboard import AgentDashboardWidget, TaskStatus
    dash = AgentDashboardWidget()
    for i in range(8):
        dash.add_task(f"t{i}", f"Task {i}", status=TaskStatus.TODO)
    assert len(dash._task_data) == 8
