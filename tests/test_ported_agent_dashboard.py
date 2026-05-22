"""Port of lyra-ui tests/test_agent_dashboard.py → tests TUI agent_dashboard.py.

Verifies AgentDashboardWidget, AgentInfo, TaskItem, MonitorEvent.
"""
from __future__ import annotations

import pytest

pytest.importorskip("textual", reason="requires textual")


def test_agent_info():
    from lyra_cli.tui_v2.widgets.agent_dashboard import AgentInfo, AgentStatus
    agent = AgentInfo(agent_id="a1", name="Worker-1", model="gpt-4o")
    assert agent.agent_id == "a1"
    assert agent.name == "Worker-1"
    assert agent.status == AgentStatus.IDLE
    assert "Worker-1" in agent.line


def test_agent_status_enum():
    from lyra_cli.tui_v2.widgets.agent_dashboard import AgentStatus
    for s in AgentStatus:
        assert s.glyph is not None
        assert s.style is not None


def test_task_item():
    from lyra_cli.tui_v2.widgets.agent_dashboard import TaskItem, TaskStatus
    task = TaskItem(task_id="t1", title="Build auth", status=TaskStatus.DOING)
    assert task.task_id == "t1"
    assert task.title == "Build auth"
    assert "Build auth" in task.line


def test_task_status_enum():
    from lyra_cli.tui_v2.widgets.agent_dashboard import TaskStatus
    for s in TaskStatus:
        assert s.glyph is not None


def test_monitor_event():
    from lyra_cli.tui_v2.widgets.agent_dashboard import MonitorEvent
    ev = MonitorEvent(level="error", message="Something broke")
    assert ev.level == "error"
    assert "broke" in ev.line


def test_dashboard_register_agent():
    from lyra_cli.tui_v2.widgets.agent_dashboard import AgentDashboardWidget
    dash = AgentDashboardWidget()
    dash.register_agent("a1", "Worker-1", model="gpt-4o", emoji="🤖")
    assert "a1" in dash._agent_data
    assert dash._agent_data["a1"].name == "Worker-1"


def test_dashboard_update_agent():
    from lyra_cli.tui_v2.widgets.agent_dashboard import (
        AgentDashboardWidget, AgentStatus,
    )
    dash = AgentDashboardWidget()
    dash.register_agent("a1", "Worker-1")
    dash.update_agent("a1", status=AgentStatus.DONE)
    assert dash._agent_data["a1"].status == AgentStatus.DONE


def test_dashboard_log_event():
    from lyra_cli.tui_v2.widgets.agent_dashboard import AgentDashboardWidget
    dash = AgentDashboardWidget()
    dash.log_event("info", "System started")
    assert len(dash._event_log) == 1
    assert "started" in dash._event_log[0].message


def test_dashboard_add_task():
    from lyra_cli.tui_v2.widgets.agent_dashboard import (
        AgentDashboardWidget, TaskStatus,
    )
    dash = AgentDashboardWidget()
    dash.add_task("t1", "Fix bug", status=TaskStatus.TODO)
    assert "t1" in dash._task_data
    assert dash._task_data["t1"].title == "Fix bug"


def test_dashboard_update_task():
    from lyra_cli.tui_v2.widgets.agent_dashboard import (
        AgentDashboardWidget, TaskStatus,
    )
    dash = AgentDashboardWidget()
    dash.add_task("t1", "Fix bug")
    dash.update_task("t1", TaskStatus.DONE)
    assert dash._task_data["t1"].status == TaskStatus.DONE


def test_dashboard_remove_agent():
    from lyra_cli.tui_v2.widgets.agent_dashboard import AgentDashboardWidget
    dash = AgentDashboardWidget()
    dash.register_agent("a1", "Worker-1")
    dash.remove_agent("a1")
    assert "a1" not in dash._agent_data
