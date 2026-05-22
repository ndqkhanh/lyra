"""Port of lyra-ui tests/test_team.py → tests TUI orchestration/team patterns.

The original tested TeamManager, UserRole, team CRUD. Our equivalent
is the AgentDashboardWidget's multi-agent coordination and the
StatusBarEnhancedWidget's agent count display.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.textual


def test_dashboard_team_size():
    from lyra_cli.tui_v2.widgets.agent_dashboard import AgentDashboardWidget
    dash = AgentDashboardWidget()
    for i in range(3):
        dash.register_agent(f"a{i}", f"Member-{i}")
    assert len(dash._agent_data) == 3


def test_dashboard_team_roles():
    from lyra_cli.tui_v2.widgets.agent_dashboard import AgentDashboardWidget, AgentStatus
    dash = AgentDashboardWidget()
    dash.register_agent("lead", "Lead", model="gpt-4o", emoji="👑")
    dash.register_agent("worker1", "Worker-1", model="deepseek", emoji="⚡")
    dash.register_agent("worker2", "Worker-2", model="claude", emoji="⚡")

    dash.update_agent("lead", status=AgentStatus.THINKING)
    dash.update_agent("worker1", status=AgentStatus.WORKING, tokens=5000)
    dash.update_agent("worker2", status=AgentStatus.WORKING, tokens=3000)

    assert dash._agent_data["lead"].status == AgentStatus.THINKING
    assert dash._agent_data["worker1"].tokens == 5000


def test_status_bar_agent_display():
    from lyra_cli.tui_v2.widgets.status_bar_enhanced import StatusBarEnhancedWidget
    sb = StatusBarEnhancedWidget()
    sb.update(agent_count=5, agent_running=2)
    assert sb.agent_count == 5
    assert sb.agent_running == 2

    segments = sb._build_segments()
    agent_segs = [s for s in segments if "2/5" in s]
    assert len(agent_segs) > 0


def test_agent_dashboard_assign_task():
    from lyra_cli.tui_v2.widgets.agent_dashboard import AgentDashboardWidget, TaskStatus
    dash = AgentDashboardWidget()
    dash.add_task("t1", "Research topic", status=TaskStatus.TODO, assignee="alice")
    dash.add_task("t2", "Write code", status=TaskStatus.DOING, assignee="bob")
    dash.add_task("t3", "Review PR", status=TaskStatus.DONE, assignee="charlie")

    assert dash._task_data["t1"].assignee == "alice"
    assert dash._task_data["t2"].status == TaskStatus.DOING
    assert dash._task_data["t3"].status == TaskStatus.DONE


def test_dashboard_event_correlation():
    from lyra_cli.tui_v2.widgets.agent_dashboard import AgentDashboardWidget
    dash = AgentDashboardWidget()

    dash.log_event("info", "Team started")
    dash.log_event("success", "Research complete")
    dash.log_event("warning", "Rate limit approaching")
    dash.log_event("error", "Worker-2 failed")

    assert len(dash._event_log) == 4
    error_events = [e for e in dash._event_log if e.level == "error"]
    assert len(error_events) == 1
    assert "failed" in error_events[0].message
