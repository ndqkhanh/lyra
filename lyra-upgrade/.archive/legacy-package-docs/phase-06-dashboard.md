# Phase 6 — Multi-Agent Orchestration Dashboard

Modules: `agent_dashboard.py`, `dashboard_viz.py`

> Note: this module's `TaskPriority` / `TaskStatus` enums are re-exported as
> `AgentTaskPriority` / `AgentTaskStatus` from `lyra_ui` to avoid collision with
> the task primitives in `async_arch.py`. Import the renamed symbols, then alias
> locally if you prefer the shorter names.

## Agent Dashboard (`agent_dashboard.py`)

Multi-agent fleet management and task orchestration.

```python
from lyra_ui import (
    AgentFleetManager,
    AgentInfo,
    AgentStatus,
    TaskBoard,
    AgentTaskPriority,
    MonitoringPanel,
    WorkflowManager,
)

TaskPriority = AgentTaskPriority  # local alias for readability

# Fleet management
fleet = AgentFleetManager()
agent = AgentInfo(id="agent1", name="Research Agent", status=AgentStatus.IDLE)
fleet.register_agent(agent)

fleet.assign_task("agent1", "task1")
fleet.complete_task("agent1", success=True)

metrics = fleet.get_metrics("agent1")
print(f"Success rate: {metrics.success_rate * 100}%")

# Kanban-style task board
board = TaskBoard()
task = board.create_task(
    task_id="task1",
    title="Research AI agents",
    description="Survey open-source AI agent frameworks",
    priority=TaskPriority.HIGH,
)

# Dependencies
board.add_dependency("task2", "task1")
ready_tasks = board.get_ready_tasks()

# Monitoring
monitor = MonitoringPanel()
monitor.log_event("agent1", "task_start", "Started research task")
monitor.add_cost(0.05)
alerts = monitor.get_alerts(level="error")

# Workflow automation
workflow_mgr = WorkflowManager()
tasks = [
    {"title": "Research", "description": "Research phase", "priority": "high"},
    {"title": "Implement", "description": "Implementation phase", "priority": "medium"},
]
workflow_mgr.create_template("research_workflow", "Research Workflow", "Description", tasks)
workflow_mgr.start_workflow("workflow1", "research_workflow", board)
```

**Features**

- Agent fleet management (register, status tracking, metrics)
- Kanban-style task board
- Task dependencies and blocking
- Real-time monitoring and event logging
- Cost tracking
- Alert system (warnings, errors)
- Workflow templates and automation

## Dashboard Visualization (`dashboard_viz.py`)

Rich visualizations for the agent dashboard.

```python
from lyra_ui import DashboardVisualizer, AgentStatusWidget, TaskSummaryWidget

viz = DashboardVisualizer()

agent_table = viz.render_agent_table(fleet)
task_table = viz.render_task_board(board)
feed = viz.render_monitoring_feed(monitor, limit=20)

# Complete dashboard
layout = viz.render_dashboard(fleet, board, monitor)
viz.display_dashboard(fleet, board, monitor)

# Live auto-refreshing dashboard
with viz.live_dashboard(fleet, board, monitor, refresh_rate=1.0) as live:
    pass

# Status widgets
agent_widget = AgentStatusWidget()
agent_panel = agent_widget.render(fleet.list_agents())

task_widget = TaskSummaryWidget()
task_panel = task_widget.render(board)
```

**Features**

- Agent fleet table with status indicators
- Task board visualization (Kanban-style)
- Real-time monitoring feed
- Performance metrics table
- Alert panel with color coding
- Complete dashboard layout
- Live auto-refreshing dashboard
- Compact status widgets

## Components

- `AgentFleetManager` — Manage fleet of agents
- `TaskBoard` — Kanban-style task management
- `MonitoringPanel` — Real-time event logging and alerts
- `WorkflowManager` — Workflow templates and automation
- `DashboardVisualizer` — Rich dashboard visualizations
- `AgentStatusWidget` — Compact agent status display
- `TaskSummaryWidget` — Task progress summary
