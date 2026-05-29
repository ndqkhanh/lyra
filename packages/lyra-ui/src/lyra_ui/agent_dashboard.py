"""
Agent Dashboard - Multi-agent orchestration and monitoring.

Features:
- Agent fleet view with status tracking
- Task orchestration with Kanban board
- Real-time monitoring and alerts
- Workflow automation
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class AgentStatus(Enum):
    """Agent status."""

    IDLE = "idle"
    WORKING = "working"
    SUCCESS = "success"
    ERROR = "error"
    PAUSED = "paused"


class TaskStatus(Enum):
    """Task status."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Task priority."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AgentInfo:
    """Agent information."""

    id: str
    name: str
    status: AgentStatus
    current_task: str | None = None
    tokens_used: int = 0
    tasks_completed: int = 0
    error_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)


@dataclass
class Task:
    """Task information."""

    id: str
    title: str
    description: str
    status: TaskStatus
    priority: TaskPriority
    assigned_to: str | None = None
    dependencies: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None


@dataclass
class AgentMetrics:
    """Agent performance metrics."""

    agent_id: str
    total_tokens: int = 0
    total_tasks: int = 0
    success_rate: float = 0.0
    avg_task_time: float = 0.0
    error_count: int = 0


class AgentFleetManager:
    """
    Manage fleet of agents.

    Features:
    - Register/unregister agents
    - Track agent status
    - Monitor agent resources
    - Agent health checks
    """

    def __init__(self):
        """Initialize agent fleet manager."""
        self.agents: dict[str, AgentInfo] = {}
        self.metrics: dict[str, AgentMetrics] = {}

    def register_agent(self, agent: AgentInfo):
        """
        Register new agent.

        Args:
            agent: Agent information
        """
        self.agents[agent.id] = agent
        self.metrics[agent.id] = AgentMetrics(agent_id=agent.id)

    def unregister_agent(self, agent_id: str):
        """
        Unregister agent.

        Args:
            agent_id: Agent ID
        """
        if agent_id in self.agents:
            del self.agents[agent_id]
        if agent_id in self.metrics:
            del self.metrics[agent_id]

    def update_agent_status(self, agent_id: str, status: AgentStatus):
        """
        Update agent status.

        Args:
            agent_id: Agent ID
            status: New status
        """
        if agent_id in self.agents:
            self.agents[agent_id].status = status
            self.agents[agent_id].last_active = datetime.now()

    def assign_task(self, agent_id: str, task_id: str):
        """
        Assign task to agent.

        Args:
            agent_id: Agent ID
            task_id: Task ID
        """
        if agent_id in self.agents:
            self.agents[agent_id].current_task = task_id
            self.agents[agent_id].status = AgentStatus.WORKING

    def complete_task(self, agent_id: str, success: bool = True):
        """
        Mark task as completed.

        Args:
            agent_id: Agent ID
            success: Whether task succeeded
        """
        if agent_id in self.agents:
            agent = self.agents[agent_id]
            agent.current_task = None
            agent.tasks_completed += 1
            agent.status = AgentStatus.SUCCESS if success else AgentStatus.ERROR

            if not success:
                agent.error_count += 1

            # Update metrics
            if agent_id in self.metrics:
                metrics = self.metrics[agent_id]
                metrics.total_tasks += 1
                if success:
                    metrics.success_rate = (
                        metrics.total_tasks - agent.error_count
                    ) / metrics.total_tasks

    def get_agent(self, agent_id: str) -> AgentInfo | None:
        """
        Get agent information.

        Args:
            agent_id: Agent ID

        Returns:
            Agent information or None
        """
        return self.agents.get(agent_id)

    def list_agents(self, status: AgentStatus | None = None) -> list[AgentInfo]:
        """
        List all agents.

        Args:
            status: Filter by status (None for all)

        Returns:
            List of agents
        """
        if status is None:
            return list(self.agents.values())
        return [a for a in self.agents.values() if a.status == status]

    def get_metrics(self, agent_id: str) -> AgentMetrics | None:
        """
        Get agent metrics.

        Args:
            agent_id: Agent ID

        Returns:
            Agent metrics or None
        """
        return self.metrics.get(agent_id)

    def get_idle_agents(self) -> list[AgentInfo]:
        """
        Get all idle agents.

        Returns:
            List of idle agents
        """
        return self.list_agents(status=AgentStatus.IDLE)


class TaskBoard:
    """
    Kanban-style task board.

    Features:
    - Task creation and management
    - Task assignment
    - Task dependencies
    - Task filtering and search
    """

    def __init__(self):
        """Initialize task board."""
        self.tasks: dict[str, Task] = {}

    def create_task(
        self,
        task_id: str,
        title: str,
        description: str,
        priority: TaskPriority = TaskPriority.MEDIUM,
    ) -> Task:
        """
        Create new task.

        Args:
            task_id: Task ID
            title: Task title
            description: Task description
            priority: Task priority

        Returns:
            Created task
        """
        task = Task(
            id=task_id,
            title=title,
            description=description,
            status=TaskStatus.TODO,
            priority=priority,
        )
        self.tasks[task_id] = task
        return task

    def update_task_status(self, task_id: str, status: TaskStatus):
        """
        Update task status.

        Args:
            task_id: Task ID
            status: New status
        """
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.status = status
            task.updated_at = datetime.now()

            if status == TaskStatus.DONE:
                task.completed_at = datetime.now()

    def assign_task(self, task_id: str, agent_id: str):
        """
        Assign task to agent.

        Args:
            task_id: Task ID
            agent_id: Agent ID
        """
        if task_id in self.tasks:
            self.tasks[task_id].assigned_to = agent_id
            self.tasks[task_id].status = TaskStatus.IN_PROGRESS
            self.tasks[task_id].updated_at = datetime.now()

    def add_dependency(self, task_id: str, depends_on: str):
        """
        Add task dependency.

        Args:
            task_id: Task ID
            depends_on: Task ID this task depends on
        """
        if task_id in self.tasks:
            if depends_on not in self.tasks[task_id].dependencies:
                self.tasks[task_id].dependencies.append(depends_on)

    def remove_dependency(self, task_id: str, depends_on: str):
        """
        Remove task dependency.

        Args:
            task_id: Task ID
            depends_on: Task ID to remove from dependencies
        """
        if task_id in self.tasks:
            if depends_on in self.tasks[task_id].dependencies:
                self.tasks[task_id].dependencies.remove(depends_on)

    def get_task(self, task_id: str) -> Task | None:
        """
        Get task.

        Args:
            task_id: Task ID

        Returns:
            Task or None
        """
        return self.tasks.get(task_id)

    def list_tasks(
        self,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
        assigned_to: str | None = None,
    ) -> list[Task]:
        """
        List tasks with filters.

        Args:
            status: Filter by status
            priority: Filter by priority
            assigned_to: Filter by assigned agent

        Returns:
            List of tasks
        """
        tasks = list(self.tasks.values())

        if status is not None:
            tasks = [t for t in tasks if t.status == status]

        if priority is not None:
            tasks = [t for t in tasks if t.priority == priority]

        if assigned_to is not None:
            tasks = [t for t in tasks if t.assigned_to == assigned_to]

        return tasks

    def get_blocked_tasks(self) -> list[Task]:
        """
        Get all blocked tasks.

        Returns:
            List of blocked tasks
        """
        blocked = []
        for task in self.tasks.values():
            if task.dependencies:
                # Check if any dependency is not done
                for dep_id in task.dependencies:
                    dep = self.tasks.get(dep_id)
                    if dep and dep.status != TaskStatus.DONE:
                        blocked.append(task)
                        break
        return blocked

    def get_ready_tasks(self) -> list[Task]:
        """
        Get tasks ready to be worked on (no blocking dependencies).

        Returns:
            List of ready tasks
        """
        ready = []
        for task in self.tasks.values():
            if task.status == TaskStatus.TODO:
                # Check if all dependencies are done
                all_done = True
                for dep_id in task.dependencies:
                    dep = self.tasks.get(dep_id)
                    if not dep or dep.status != TaskStatus.DONE:
                        all_done = False
                        break
                if all_done:
                    ready.append(task)
        return ready


@dataclass
class MonitoringEvent:
    """Monitoring event."""

    timestamp: datetime
    agent_id: str
    event_type: str
    message: str
    level: str = "info"  # info, warning, error


class MonitoringPanel:
    """
    Real-time monitoring panel.

    Features:
    - Live activity feed
    - Cost tracking
    - Performance metrics
    - Alert system
    """

    def __init__(self, max_events: int = 1000):
        """
        Initialize monitoring panel.

        Args:
            max_events: Maximum events to keep in history
        """
        self.events: list[MonitoringEvent] = []
        self.max_events = max_events
        self.total_cost: float = 0.0
        self.alerts: list[MonitoringEvent] = []

    def log_event(
        self,
        agent_id: str,
        event_type: str,
        message: str,
        level: str = "info",
    ):
        """
        Log monitoring event.

        Args:
            agent_id: Agent ID
            event_type: Event type
            message: Event message
            level: Event level (info, warning, error)
        """
        event = MonitoringEvent(
            timestamp=datetime.now(),
            agent_id=agent_id,
            event_type=event_type,
            message=message,
            level=level,
        )

        self.events.append(event)

        # Keep only recent events
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events :]

        # Add to alerts if warning or error
        if level in ["warning", "error"]:
            self.alerts.append(event)

    def get_recent_events(self, limit: int = 100) -> list[MonitoringEvent]:
        """
        Get recent events.

        Args:
            limit: Maximum number of events

        Returns:
            List of recent events
        """
        return self.events[-limit:]

    def get_events_by_agent(self, agent_id: str) -> list[MonitoringEvent]:
        """
        Get events for specific agent.

        Args:
            agent_id: Agent ID

        Returns:
            List of events
        """
        return [e for e in self.events if e.agent_id == agent_id]

    def get_alerts(self, level: str | None = None) -> list[MonitoringEvent]:
        """
        Get alerts.

        Args:
            level: Filter by level (None for all)

        Returns:
            List of alerts
        """
        if level is None:
            return self.alerts
        return [a for a in self.alerts if a.level == level]

    def clear_alerts(self):
        """Clear all alerts."""
        self.alerts.clear()

    def add_cost(self, amount: float):
        """
        Add to total cost.

        Args:
            amount: Cost amount
        """
        self.total_cost += amount

    def get_total_cost(self) -> float:
        """
        Get total cost.

        Returns:
            Total cost
        """
        return self.total_cost


@dataclass
class WorkflowTemplate:
    """Workflow template."""

    id: str
    name: str
    description: str
    tasks: list[dict[str, str]]  # List of task definitions
    created_at: datetime = field(default_factory=datetime.now)


class WorkflowManager:
    """
    Workflow automation manager.

    Features:
    - Workflow templates
    - Workflow scheduling
    - Workflow execution
    """

    def __init__(self):
        """Initialize workflow manager."""
        self.templates: dict[str, WorkflowTemplate] = {}
        self.active_workflows: dict[str, list[str]] = {}  # workflow_id -> task_ids

    def create_template(
        self,
        template_id: str,
        name: str,
        description: str,
        tasks: list[dict[str, str]],
    ) -> WorkflowTemplate:
        """
        Create workflow template.

        Args:
            template_id: Template ID
            name: Template name
            description: Template description
            tasks: List of task definitions

        Returns:
            Created template
        """
        template = WorkflowTemplate(
            id=template_id,
            name=name,
            description=description,
            tasks=tasks,
        )
        self.templates[template_id] = template
        return template

    def get_template(self, template_id: str) -> WorkflowTemplate | None:
        """
        Get workflow template.

        Args:
            template_id: Template ID

        Returns:
            Template or None
        """
        return self.templates.get(template_id)

    def list_templates(self) -> list[WorkflowTemplate]:
        """
        List all templates.

        Returns:
            List of templates
        """
        return list(self.templates.values())

    def delete_template(self, template_id: str):
        """
        Delete workflow template.

        Args:
            template_id: Template ID
        """
        if template_id in self.templates:
            del self.templates[template_id]

    def start_workflow(
        self,
        workflow_id: str,
        template_id: str,
        task_board: TaskBoard,
    ) -> list[str]:
        """
        Start workflow from template.

        Args:
            workflow_id: Workflow instance ID
            template_id: Template ID
            task_board: Task board to create tasks on

        Returns:
            List of created task IDs
        """
        template = self.templates.get(template_id)
        if not template:
            return []

        task_ids = []
        for i, task_def in enumerate(template.tasks):
            task_id = f"{workflow_id}_task_{i}"
            task_board.create_task(
                task_id=task_id,
                title=task_def.get("title", f"Task {i}"),
                description=task_def.get("description", ""),
                priority=TaskPriority[task_def.get("priority", "MEDIUM").upper()],
            )
            task_ids.append(task_id)

        self.active_workflows[workflow_id] = task_ids
        return task_ids

    def get_workflow_tasks(self, workflow_id: str) -> list[str]:
        """
        Get tasks for workflow.

        Args:
            workflow_id: Workflow ID

        Returns:
            List of task IDs
        """
        return self.active_workflows.get(workflow_id, [])

    def complete_workflow(self, workflow_id: str):
        """
        Mark workflow as complete.

        Args:
            workflow_id: Workflow ID
        """
        if workflow_id in self.active_workflows:
            del self.active_workflows[workflow_id]
