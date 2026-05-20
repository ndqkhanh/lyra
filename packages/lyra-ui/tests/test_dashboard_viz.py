"""Tests for dashboard visualization."""

from lyra_ui import (
    AgentFleetManager,
    AgentInfo,
    AgentStatus,
    AgentTaskPriority,
    AgentTaskStatus,
    DashboardVisualizer,
    MonitoringPanel,
    TaskBoard,
)

# Alias for convenience in tests
TaskPriority = AgentTaskPriority
TaskStatus = AgentTaskStatus


# Dashboard Visualizer Tests


def test_dashboard_visualizer_init():
    """Test dashboard visualizer initialization."""
    viz = DashboardVisualizer()
    assert viz.console is not None


def test_render_agent_table():
    """Test rendering agent table."""
    viz = DashboardVisualizer()
    fleet = AgentFleetManager()

    # Add agents
    agent1 = AgentInfo(id="agent1", name="Agent 1", status=AgentStatus.IDLE)
    agent2 = AgentInfo(id="agent2", name="Agent 2", status=AgentStatus.WORKING)
    fleet.register_agent(agent1)
    fleet.register_agent(agent2)

    table = viz.render_agent_table(fleet)
    assert table is not None
    assert table.title == "Agent Fleet"


def test_render_task_board():
    """Test rendering task board."""
    viz = DashboardVisualizer()
    board = TaskBoard()

    # Add tasks
    board.create_task("task1", "Task 1", "Description", priority=TaskPriority.HIGH)
    board.create_task("task2", "Task 2", "Description", priority=TaskPriority.LOW)

    table = viz.render_task_board(board)
    assert table is not None
    assert table.title == "Task Board"


def test_render_monitoring_feed():
    """Test rendering monitoring feed."""
    viz = DashboardVisualizer()
    monitor = MonitoringPanel()

    # Add events
    monitor.log_event("agent1", "task_start", "Started task")
    monitor.log_event("agent2", "task_complete", "Completed task")

    table = viz.render_monitoring_feed(monitor)
    assert table is not None
    assert table.title == "Monitoring Feed"


def test_render_metrics_table():
    """Test rendering metrics table."""
    viz = DashboardVisualizer()
    fleet = AgentFleetManager()

    # Add agent with metrics
    agent = AgentInfo(id="agent1", name="Agent 1", status=AgentStatus.IDLE)
    fleet.register_agent(agent)
    fleet.assign_task("agent1", "task1")
    fleet.complete_task("agent1", success=True)

    table = viz.render_metrics_table(fleet)
    assert table is not None
    assert table.title == "Agent Metrics"


def test_render_alerts_no_alerts():
    """Test rendering alerts panel with no alerts."""
    viz = DashboardVisualizer()
    monitor = MonitoringPanel()

    panel = viz.render_alerts(monitor)
    assert panel is not None
    assert panel.title == "Alerts (0)"


def test_render_alerts_with_alerts():
    """Test rendering alerts panel with alerts."""
    viz = DashboardVisualizer()
    monitor = MonitoringPanel()

    # Add alerts
    monitor.log_event("agent1", "error", "Error occurred", level="error")
    monitor.log_event("agent2", "warning", "Warning", level="warning")

    panel = viz.render_alerts(monitor)
    assert panel is not None
    assert panel.title == "Alerts (2)"


def test_render_dashboard():
    """Test rendering complete dashboard."""
    viz = DashboardVisualizer()
    fleet = AgentFleetManager()
    board = TaskBoard()
    monitor = MonitoringPanel()

    # Add data
    agent = AgentInfo(id="agent1", name="Agent 1", status=AgentStatus.IDLE)
    fleet.register_agent(agent)
    board.create_task("task1", "Task 1", "Description")
    monitor.log_event("agent1", "event", "Event")

    layout = viz.render_dashboard(fleet, board, monitor)
    assert layout is not None


def test_display_dashboard():
    """Test displaying dashboard."""
    viz = DashboardVisualizer()
    fleet = AgentFleetManager()
    board = TaskBoard()
    monitor = MonitoringPanel()

    # Should not raise error
    viz.display_dashboard(fleet, board, monitor)


def test_live_dashboard():
    """Test creating live dashboard."""
    viz = DashboardVisualizer()
    fleet = AgentFleetManager()
    board = TaskBoard()
    monitor = MonitoringPanel()

    live = viz.live_dashboard(fleet, board, monitor, refresh_rate=1.0)
    assert live is not None


def test_status_color_mapping():
    """Test status color mapping."""
    viz = DashboardVisualizer()

    assert viz._get_status_color(AgentStatus.IDLE) == "dim"
    assert viz._get_status_color(AgentStatus.WORKING) == "yellow"
    assert viz._get_status_color(AgentStatus.SUCCESS) == "green"
    assert viz._get_status_color(AgentStatus.ERROR) == "red"
    assert viz._get_status_color(AgentStatus.PAUSED) == "blue"


def test_task_status_color_mapping():
    """Test task status color mapping."""
    viz = DashboardVisualizer()

    assert viz._get_task_status_color(TaskStatus.TODO) == "dim"
    assert viz._get_task_status_color(TaskStatus.IN_PROGRESS) == "yellow"
    assert viz._get_task_status_color(TaskStatus.DONE) == "green"
    assert viz._get_task_status_color(TaskStatus.BLOCKED) == "red"
    assert viz._get_task_status_color(TaskStatus.CANCELLED) == "dim red"


def test_priority_color_mapping():
    """Test priority color mapping."""
    viz = DashboardVisualizer()

    assert viz._get_priority_color(TaskPriority.LOW) == "dim"
    assert viz._get_priority_color(TaskPriority.MEDIUM) == "yellow"
    assert viz._get_priority_color(TaskPriority.HIGH) == "orange1"
    assert viz._get_priority_color(TaskPriority.CRITICAL) == "red bold"


def test_level_color_mapping():
    """Test level color mapping."""
    viz = DashboardVisualizer()

    assert viz._get_level_color("info") == "cyan"
    assert viz._get_level_color("warning") == "yellow"
    assert viz._get_level_color("error") == "red"


# Agent Status Widget Tests


def test_agent_status_widget_init():
    """Test agent status widget initialization."""
    from lyra_ui import AgentStatusWidget

    widget = AgentStatusWidget()
    assert widget.console is not None


def test_agent_status_widget_render_empty():
    """Test rendering empty agent status widget."""
    from lyra_ui import AgentStatusWidget

    widget = AgentStatusWidget()
    panel = widget.render([])

    assert panel is not None
    assert panel.title == "Agents"


def test_agent_status_widget_render_with_agents():
    """Test rendering agent status widget with agents."""
    from lyra_ui import AgentStatusWidget

    widget = AgentStatusWidget()
    agents = [
        AgentInfo(id="agent1", name="Agent 1", status=AgentStatus.IDLE),
        AgentInfo(id="agent2", name="Agent 2", status=AgentStatus.WORKING),
    ]

    panel = widget.render(agents)
    assert panel is not None


def test_agent_status_widget_with_current_task():
    """Test rendering agent with current task."""
    from lyra_ui import AgentStatusWidget

    widget = AgentStatusWidget()
    agent = AgentInfo(
        id="agent1", name="Agent 1", status=AgentStatus.WORKING, current_task="task1"
    )

    panel = widget.render([agent])
    assert panel is not None


# Task Summary Widget Tests


def test_task_summary_widget_init():
    """Test task summary widget initialization."""
    from lyra_ui import TaskSummaryWidget

    widget = TaskSummaryWidget()
    assert widget.console is not None


def test_task_summary_widget_render_empty():
    """Test rendering empty task summary widget."""
    from lyra_ui import TaskSummaryWidget

    widget = TaskSummaryWidget()
    board = TaskBoard()

    panel = widget.render(board)
    assert panel is not None
    assert panel.title == "Tasks"


def test_task_summary_widget_render_with_tasks():
    """Test rendering task summary widget with tasks."""
    from lyra_ui import TaskSummaryWidget

    widget = TaskSummaryWidget()
    board = TaskBoard()

    # Add tasks
    board.create_task("task1", "Task 1", "Description")
    board.create_task("task2", "Task 2", "Description")
    board.update_task_status("task1", TaskStatus.DONE)

    panel = widget.render(board)
    assert panel is not None
    assert panel.title == "Tasks"


def test_task_summary_widget_progress():
    """Test task summary widget progress calculation."""
    from lyra_ui import TaskSummaryWidget

    widget = TaskSummaryWidget()
    board = TaskBoard()

    # Add tasks
    for i in range(10):
        board.create_task(f"task{i}", f"Task {i}", "Description")

    # Complete 5 tasks
    for i in range(5):
        board.update_task_status(f"task{i}", TaskStatus.DONE)

    panel = widget.render(board)
    assert panel is not None
    assert panel.title == "Tasks"
    # Verify 5 out of 10 tasks are done (50% progress)
    done_tasks = board.list_tasks(status=TaskStatus.DONE)
    assert len(done_tasks) == 5


def test_task_summary_widget_blocked_tasks():
    """Test task summary widget with blocked tasks."""
    from lyra_ui import TaskSummaryWidget

    widget = TaskSummaryWidget()
    board = TaskBoard()

    # Add tasks
    board.create_task("task1", "Task 1", "Description")
    board.create_task("task2", "Task 2", "Description")
    board.update_task_status("task2", TaskStatus.BLOCKED)

    panel = widget.render(board)
    assert panel is not None
    assert panel.title == "Tasks"
    # Verify 1 task is blocked
    blocked_tasks = board.list_tasks(status=TaskStatus.BLOCKED)
    assert len(blocked_tasks) == 1


# Integration Tests


def test_complete_dashboard_workflow():
    """Test complete dashboard workflow."""
    viz = DashboardVisualizer()
    fleet = AgentFleetManager()
    board = TaskBoard()
    monitor = MonitoringPanel()

    # Register agents
    agent1 = AgentInfo(id="agent1", name="Agent 1", status=AgentStatus.IDLE)
    agent2 = AgentInfo(id="agent2", name="Agent 2", status=AgentStatus.IDLE)
    fleet.register_agent(agent1)
    fleet.register_agent(agent2)

    # Create tasks
    board.create_task("task1", "Task 1", "Description", priority=TaskPriority.HIGH)
    board.create_task("task2", "Task 2", "Description", priority=TaskPriority.MEDIUM)

    # Assign tasks
    fleet.assign_task("agent1", "task1")
    board.assign_task("task1", "agent1")
    monitor.log_event("agent1", "task_start", "Started task 1")

    # Render dashboard
    layout = viz.render_dashboard(fleet, board, monitor)
    assert layout is not None

    # Complete task
    fleet.complete_task("agent1", success=True)
    board.update_task_status("task1", TaskStatus.DONE)
    monitor.log_event("agent1", "task_complete", "Completed task 1")

    # Render updated dashboard
    layout = viz.render_dashboard(fleet, board, monitor)
    assert layout is not None


def test_dashboard_with_errors():
    """Test dashboard with error states."""
    viz = DashboardVisualizer()
    fleet = AgentFleetManager()
    board = TaskBoard()
    monitor = MonitoringPanel()

    # Register agent
    agent = AgentInfo(id="agent1", name="Agent 1", status=AgentStatus.IDLE)
    fleet.register_agent(agent)

    # Create task
    board.create_task("task1", "Task 1", "Description")

    # Assign and fail task
    fleet.assign_task("agent1", "task1")
    board.assign_task("task1", "agent1")
    monitor.log_event("agent1", "error", "Task failed", level="error")
    fleet.complete_task("agent1", success=False)
    board.update_task_status("task1", TaskStatus.CANCELLED)

    # Render dashboard
    layout = viz.render_dashboard(fleet, board, monitor)
    assert layout is not None

    # Check alerts
    alerts = monitor.get_alerts()
    assert len(alerts) == 1


def test_dashboard_multi_agent_coordination():
    """Test dashboard with multiple agents."""
    viz = DashboardVisualizer()
    fleet = AgentFleetManager()
    board = TaskBoard()
    monitor = MonitoringPanel()

    # Register multiple agents
    for i in range(5):
        agent = AgentInfo(id=f"agent{i}", name=f"Agent {i}", status=AgentStatus.IDLE)
        fleet.register_agent(agent)

    # Create multiple tasks
    for i in range(10):
        board.create_task(
            f"task{i}", f"Task {i}", "Description", priority=TaskPriority.MEDIUM
        )

    # Assign tasks to agents
    for i in range(5):
        fleet.assign_task(f"agent{i}", f"task{i}")
        board.assign_task(f"task{i}", f"agent{i}")
        monitor.log_event(f"agent{i}", "task_start", f"Started task {i}")

    # Render dashboard
    layout = viz.render_dashboard(fleet, board, monitor)
    assert layout is not None

    # Verify state
    working_agents = fleet.list_agents(status=AgentStatus.WORKING)
    assert len(working_agents) == 5

    in_progress_tasks = board.list_tasks(status=TaskStatus.IN_PROGRESS)
    assert len(in_progress_tasks) == 5
