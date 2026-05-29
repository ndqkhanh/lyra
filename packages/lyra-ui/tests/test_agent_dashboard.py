"""Tests for agent dashboard."""

from lyra_ui import (
    AgentFleetManager,
    AgentInfo,
    AgentStatus,
    AgentTaskPriority,
    AgentTaskStatus,
    MonitoringPanel,
    TaskBoard,
    WorkflowManager,
)

# Alias for convenience in tests
TaskPriority = AgentTaskPriority
TaskStatus = AgentTaskStatus


# Agent Fleet Manager Tests


def test_agent_fleet_manager_init():
    """Test agent fleet manager initialization."""
    fleet = AgentFleetManager()
    assert len(fleet.agents) == 0
    assert len(fleet.metrics) == 0


def test_register_agent():
    """Test registering agent."""
    fleet = AgentFleetManager()
    agent = AgentInfo(id="agent1", name="Test Agent", status=AgentStatus.IDLE)
    fleet.register_agent(agent)

    assert "agent1" in fleet.agents
    assert "agent1" in fleet.metrics
    assert fleet.agents["agent1"].name == "Test Agent"


def test_unregister_agent():
    """Test unregistering agent."""
    fleet = AgentFleetManager()
    agent = AgentInfo(id="agent1", name="Test Agent", status=AgentStatus.IDLE)
    fleet.register_agent(agent)
    fleet.unregister_agent("agent1")

    assert "agent1" not in fleet.agents
    assert "agent1" not in fleet.metrics


def test_update_agent_status():
    """Test updating agent status."""
    fleet = AgentFleetManager()
    agent = AgentInfo(id="agent1", name="Test Agent", status=AgentStatus.IDLE)
    fleet.register_agent(agent)

    fleet.update_agent_status("agent1", AgentStatus.WORKING)
    assert fleet.agents["agent1"].status == AgentStatus.WORKING


def test_assign_task_to_agent():
    """Test assigning task to agent."""
    fleet = AgentFleetManager()
    agent = AgentInfo(id="agent1", name="Test Agent", status=AgentStatus.IDLE)
    fleet.register_agent(agent)

    fleet.assign_task("agent1", "task1")
    assert fleet.agents["agent1"].current_task == "task1"
    assert fleet.agents["agent1"].status == AgentStatus.WORKING


def test_complete_task_success():
    """Test completing task successfully."""
    fleet = AgentFleetManager()
    agent = AgentInfo(id="agent1", name="Test Agent", status=AgentStatus.IDLE)
    fleet.register_agent(agent)

    fleet.assign_task("agent1", "task1")
    fleet.complete_task("agent1", success=True)

    assert fleet.agents["agent1"].current_task is None
    assert fleet.agents["agent1"].status == AgentStatus.SUCCESS
    assert fleet.agents["agent1"].tasks_completed == 1
    assert fleet.metrics["agent1"].total_tasks == 1


def test_complete_task_failure():
    """Test completing task with failure."""
    fleet = AgentFleetManager()
    agent = AgentInfo(id="agent1", name="Test Agent", status=AgentStatus.IDLE)
    fleet.register_agent(agent)

    fleet.assign_task("agent1", "task1")
    fleet.complete_task("agent1", success=False)

    assert fleet.agents["agent1"].status == AgentStatus.ERROR
    assert fleet.agents["agent1"].error_count == 1


def test_get_agent():
    """Test getting agent."""
    fleet = AgentFleetManager()
    agent = AgentInfo(id="agent1", name="Test Agent", status=AgentStatus.IDLE)
    fleet.register_agent(agent)

    retrieved = fleet.get_agent("agent1")
    assert retrieved is not None
    assert retrieved.id == "agent1"


def test_list_agents():
    """Test listing agents."""
    fleet = AgentFleetManager()
    agent1 = AgentInfo(id="agent1", name="Agent 1", status=AgentStatus.IDLE)
    agent2 = AgentInfo(id="agent2", name="Agent 2", status=AgentStatus.WORKING)
    fleet.register_agent(agent1)
    fleet.register_agent(agent2)

    all_agents = fleet.list_agents()
    assert len(all_agents) == 2

    idle_agents = fleet.list_agents(status=AgentStatus.IDLE)
    assert len(idle_agents) == 1
    assert idle_agents[0].id == "agent1"


def test_get_idle_agents():
    """Test getting idle agents."""
    fleet = AgentFleetManager()
    agent1 = AgentInfo(id="agent1", name="Agent 1", status=AgentStatus.IDLE)
    agent2 = AgentInfo(id="agent2", name="Agent 2", status=AgentStatus.WORKING)
    fleet.register_agent(agent1)
    fleet.register_agent(agent2)

    idle = fleet.get_idle_agents()
    assert len(idle) == 1
    assert idle[0].id == "agent1"


# Task Board Tests


def test_task_board_init():
    """Test task board initialization."""
    board = TaskBoard()
    assert len(board.tasks) == 0


def test_create_task():
    """Test creating task."""
    board = TaskBoard()
    task = board.create_task(
        task_id="task1",
        title="Test Task",
        description="Test description",
        priority=TaskPriority.HIGH,
    )

    assert task.id == "task1"
    assert task.title == "Test Task"
    assert task.status == TaskStatus.TODO
    assert task.priority == TaskPriority.HIGH


def test_update_task_status():
    """Test updating task status."""
    board = TaskBoard()
    board.create_task("task1", "Test Task", "Description")
    board.update_task_status("task1", TaskStatus.IN_PROGRESS)

    assert board.tasks["task1"].status == TaskStatus.IN_PROGRESS


def test_update_task_status_done():
    """Test updating task status to done."""
    board = TaskBoard()
    board.create_task("task1", "Test Task", "Description")
    board.update_task_status("task1", TaskStatus.DONE)

    task = board.tasks["task1"]
    assert task.status == TaskStatus.DONE
    assert task.completed_at is not None


def test_assign_task():
    """Test assigning task."""
    board = TaskBoard()
    board.create_task("task1", "Test Task", "Description")
    board.assign_task("task1", "agent1")

    task = board.tasks["task1"]
    assert task.assigned_to == "agent1"
    assert task.status == TaskStatus.IN_PROGRESS


def test_add_dependency():
    """Test adding task dependency."""
    board = TaskBoard()
    board.create_task("task1", "Task 1", "Description")
    board.create_task("task2", "Task 2", "Description")
    board.add_dependency("task2", "task1")

    assert "task1" in board.tasks["task2"].dependencies


def test_remove_dependency():
    """Test removing task dependency."""
    board = TaskBoard()
    board.create_task("task1", "Task 1", "Description")
    board.create_task("task2", "Task 2", "Description")
    board.add_dependency("task2", "task1")
    board.remove_dependency("task2", "task1")

    assert "task1" not in board.tasks["task2"].dependencies


def test_get_task():
    """Test getting task."""
    board = TaskBoard()
    board.create_task("task1", "Test Task", "Description")

    task = board.get_task("task1")
    assert task is not None
    assert task.id == "task1"


def test_list_tasks():
    """Test listing tasks."""
    board = TaskBoard()
    board.create_task("task1", "Task 1", "Description", priority=TaskPriority.HIGH)
    board.create_task("task2", "Task 2", "Description", priority=TaskPriority.LOW)

    all_tasks = board.list_tasks()
    assert len(all_tasks) == 2

    high_priority = board.list_tasks(priority=TaskPriority.HIGH)
    assert len(high_priority) == 1
    assert high_priority[0].id == "task1"


def test_list_tasks_by_status():
    """Test listing tasks by status."""
    board = TaskBoard()
    board.create_task("task1", "Task 1", "Description")
    board.create_task("task2", "Task 2", "Description")
    board.update_task_status("task1", TaskStatus.DONE)

    todo_tasks = board.list_tasks(status=TaskStatus.TODO)
    assert len(todo_tasks) == 1
    assert todo_tasks[0].id == "task2"


def test_list_tasks_by_assigned():
    """Test listing tasks by assigned agent."""
    board = TaskBoard()
    board.create_task("task1", "Task 1", "Description")
    board.create_task("task2", "Task 2", "Description")
    board.assign_task("task1", "agent1")

    agent_tasks = board.list_tasks(assigned_to="agent1")
    assert len(agent_tasks) == 1
    assert agent_tasks[0].id == "task1"


def test_get_blocked_tasks():
    """Test getting blocked tasks."""
    board = TaskBoard()
    board.create_task("task1", "Task 1", "Description")
    board.create_task("task2", "Task 2", "Description")
    board.add_dependency("task2", "task1")

    blocked = board.get_blocked_tasks()
    assert len(blocked) == 1
    assert blocked[0].id == "task2"


def test_get_ready_tasks():
    """Test getting ready tasks."""
    board = TaskBoard()
    board.create_task("task1", "Task 1", "Description")
    board.create_task("task2", "Task 2", "Description")
    board.add_dependency("task2", "task1")

    ready = board.get_ready_tasks()
    assert len(ready) == 1
    assert ready[0].id == "task1"

    # Complete task1, task2 should become ready
    board.update_task_status("task1", TaskStatus.DONE)
    ready = board.get_ready_tasks()
    assert len(ready) == 1
    assert ready[0].id == "task2"


# Monitoring Panel Tests


def test_monitoring_panel_init():
    """Test monitoring panel initialization."""
    monitor = MonitoringPanel()
    assert len(monitor.events) == 0
    assert len(monitor.alerts) == 0
    assert monitor.total_cost == 0.0


def test_log_event():
    """Test logging event."""
    monitor = MonitoringPanel()
    monitor.log_event("agent1", "task_start", "Started task", level="info")

    assert len(monitor.events) == 1
    assert monitor.events[0].agent_id == "agent1"
    assert monitor.events[0].event_type == "task_start"


def test_log_event_alert():
    """Test logging event creates alert."""
    monitor = MonitoringPanel()
    monitor.log_event("agent1", "error", "Error occurred", level="error")

    assert len(monitor.alerts) == 1
    assert monitor.alerts[0].level == "error"


def test_get_recent_events():
    """Test getting recent events."""
    monitor = MonitoringPanel()
    for i in range(10):
        monitor.log_event(f"agent{i}", "event", f"Event {i}")

    recent = monitor.get_recent_events(limit=5)
    assert len(recent) == 5


def test_get_events_by_agent():
    """Test getting events by agent."""
    monitor = MonitoringPanel()
    monitor.log_event("agent1", "event1", "Event 1")
    monitor.log_event("agent2", "event2", "Event 2")
    monitor.log_event("agent1", "event3", "Event 3")

    agent1_events = monitor.get_events_by_agent("agent1")
    assert len(agent1_events) == 2


def test_get_alerts():
    """Test getting alerts."""
    monitor = MonitoringPanel()
    monitor.log_event("agent1", "warning", "Warning", level="warning")
    monitor.log_event("agent2", "error", "Error", level="error")

    all_alerts = monitor.get_alerts()
    assert len(all_alerts) == 2

    errors = monitor.get_alerts(level="error")
    assert len(errors) == 1


def test_clear_alerts():
    """Test clearing alerts."""
    monitor = MonitoringPanel()
    monitor.log_event("agent1", "error", "Error", level="error")
    monitor.clear_alerts()

    assert len(monitor.alerts) == 0


def test_add_cost():
    """Test adding cost."""
    monitor = MonitoringPanel()
    monitor.add_cost(10.5)
    monitor.add_cost(5.25)

    assert monitor.get_total_cost() == 15.75


def test_max_events_limit():
    """Test max events limit."""
    monitor = MonitoringPanel(max_events=10)
    for i in range(20):
        monitor.log_event(f"agent{i}", "event", f"Event {i}")

    assert len(monitor.events) == 10


# Workflow Manager Tests


def test_workflow_manager_init():
    """Test workflow manager initialization."""
    manager = WorkflowManager()
    assert len(manager.templates) == 0
    assert len(manager.active_workflows) == 0


def test_create_template():
    """Test creating workflow template."""
    manager = WorkflowManager()
    tasks = [
        {"title": "Task 1", "description": "First task", "priority": "high"},
        {"title": "Task 2", "description": "Second task", "priority": "medium"},
    ]

    template = manager.create_template(
        "template1", "Test Workflow", "Test description", tasks
    )

    assert template.id == "template1"
    assert template.name == "Test Workflow"
    assert len(template.tasks) == 2


def test_get_template():
    """Test getting workflow template."""
    manager = WorkflowManager()
    tasks = [{"title": "Task 1", "description": "First task"}]
    manager.create_template("template1", "Test Workflow", "Description", tasks)

    template = manager.get_template("template1")
    assert template is not None
    assert template.id == "template1"


def test_list_templates():
    """Test listing templates."""
    manager = WorkflowManager()
    tasks = [{"title": "Task 1", "description": "First task"}]
    manager.create_template("template1", "Workflow 1", "Description", tasks)
    manager.create_template("template2", "Workflow 2", "Description", tasks)

    templates = manager.list_templates()
    assert len(templates) == 2


def test_delete_template():
    """Test deleting template."""
    manager = WorkflowManager()
    tasks = [{"title": "Task 1", "description": "First task"}]
    manager.create_template("template1", "Test Workflow", "Description", tasks)
    manager.delete_template("template1")

    assert manager.get_template("template1") is None


def test_start_workflow():
    """Test starting workflow."""
    manager = WorkflowManager()
    board = TaskBoard()

    tasks = [
        {"title": "Task 1", "description": "First task", "priority": "high"},
        {"title": "Task 2", "description": "Second task", "priority": "medium"},
    ]
    manager.create_template("template1", "Test Workflow", "Description", tasks)

    task_ids = manager.start_workflow("workflow1", "template1", board)

    assert len(task_ids) == 2
    assert "workflow1" in manager.active_workflows
    assert len(board.tasks) == 2


def test_get_workflow_tasks():
    """Test getting workflow tasks."""
    manager = WorkflowManager()
    board = TaskBoard()

    tasks = [{"title": "Task 1", "description": "First task"}]
    manager.create_template("template1", "Test Workflow", "Description", tasks)
    task_ids = manager.start_workflow("workflow1", "template1", board)

    workflow_tasks = manager.get_workflow_tasks("workflow1")
    assert workflow_tasks == task_ids


def test_complete_workflow():
    """Test completing workflow."""
    manager = WorkflowManager()
    board = TaskBoard()

    tasks = [{"title": "Task 1", "description": "First task"}]
    manager.create_template("template1", "Test Workflow", "Description", tasks)
    manager.start_workflow("workflow1", "template1", board)
    manager.complete_workflow("workflow1")

    assert "workflow1" not in manager.active_workflows


# Integration Tests


def test_full_agent_workflow():
    """Test complete agent workflow."""
    fleet = AgentFleetManager()
    board = TaskBoard()
    monitor = MonitoringPanel()

    # Register agent
    agent = AgentInfo(id="agent1", name="Test Agent", status=AgentStatus.IDLE)
    fleet.register_agent(agent)

    # Create task
    board.create_task("task1", "Test Task", "Description")

    # Assign task to agent
    fleet.assign_task("agent1", "task1")
    board.assign_task("task1", "agent1")

    # Log event
    monitor.log_event("agent1", "task_start", "Started task")

    # Complete task
    fleet.complete_task("agent1", success=True)
    board.update_task_status("task1", TaskStatus.DONE)

    # Verify
    assert fleet.agents["agent1"].status == AgentStatus.SUCCESS
    assert board.tasks["task1"].status == TaskStatus.DONE
    assert len(monitor.events) == 1


def test_multi_agent_task_distribution():
    """Test distributing tasks to multiple agents."""
    fleet = AgentFleetManager()
    board = TaskBoard()

    # Register agents
    for i in range(3):
        agent = AgentInfo(id=f"agent{i}", name=f"Agent {i}", status=AgentStatus.IDLE)
        fleet.register_agent(agent)

    # Create tasks
    for i in range(5):
        board.create_task(f"task{i}", f"Task {i}", "Description")

    # Assign tasks to idle agents
    idle_agents = fleet.get_idle_agents()
    ready_tasks = board.get_ready_tasks()

    for agent, task in zip(idle_agents, ready_tasks, strict=False):
        fleet.assign_task(agent.id, task.id)
        board.assign_task(task.id, agent.id)

    # Verify
    working_agents = fleet.list_agents(status=AgentStatus.WORKING)
    assert len(working_agents) == 3

    in_progress_tasks = board.list_tasks(status=TaskStatus.IN_PROGRESS)
    assert len(in_progress_tasks) == 3


def test_workflow_execution():
    """Test complete workflow execution."""
    manager = WorkflowManager()
    board = TaskBoard()
    fleet = AgentFleetManager()

    # Register agent
    agent = AgentInfo(id="agent1", name="Test Agent", status=AgentStatus.IDLE)
    fleet.register_agent(agent)

    # Create workflow template
    tasks = [
        {"title": "Task 1", "description": "First task", "priority": "high"},
        {"title": "Task 2", "description": "Second task", "priority": "medium"},
    ]
    manager.create_template("template1", "Test Workflow", "Description", tasks)

    # Start workflow
    task_ids = manager.start_workflow("workflow1", "template1", board)

    # Assign first task
    first_task_id = task_ids[0]
    fleet.assign_task("agent1", first_task_id)
    board.assign_task(first_task_id, "agent1")

    # Complete first task
    fleet.complete_task("agent1", success=True)
    board.update_task_status(first_task_id, TaskStatus.DONE)

    # Verify
    assert board.tasks[task_ids[0]].status == TaskStatus.DONE
    assert fleet.agents["agent1"].tasks_completed == 1
