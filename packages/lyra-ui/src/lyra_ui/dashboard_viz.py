"""
Dashboard Visualization - Rich visualizations for agent dashboard.

Features:
- Agent fleet table
- Task Kanban board
- Monitoring feed
- Performance charts
"""


from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from lyra_ui.agent_dashboard import (
    AgentFleetManager,
    AgentInfo,
    AgentStatus,
    MonitoringPanel,
    TaskBoard,
    TaskPriority,
    TaskStatus,
)


class DashboardVisualizer:
    """
    Dashboard visualizer.

    Features:
    - Agent fleet view
    - Task board view
    - Monitoring feed
    - Performance metrics
    """

    def __init__(self, console: Console | None = None):
        """
        Initialize dashboard visualizer.

        Args:
            console: Rich console (creates new if None)
        """
        self.console = console or Console()

    def render_agent_table(self, fleet: AgentFleetManager) -> Table:
        """
        Render agent fleet table.

        Args:
            fleet: Agent fleet manager

        Returns:
            Rich table
        """
        table = Table(title="Agent Fleet", show_header=True, header_style="bold cyan")

        table.add_column("ID", style="dim")
        table.add_column("Name", style="bold")
        table.add_column("Status")
        table.add_column("Current Task", style="italic")
        table.add_column("Tasks", justify="right")
        table.add_column("Tokens", justify="right")
        table.add_column("Errors", justify="right")

        agents = fleet.list_agents()
        for agent in agents:
            # Status with color
            status_color = self._get_status_color(agent.status)
            status_text = Text(agent.status.value, style=status_color)

            # Current task
            task_text = agent.current_task or "-"

            table.add_row(
                agent.id,
                agent.name,
                status_text,
                task_text,
                str(agent.tasks_completed),
                f"{agent.tokens_used:,}",
                str(agent.error_count),
            )

        return table

    def render_task_board(self, board: TaskBoard) -> Table:
        """
        Render task board (Kanban style).

        Args:
            board: Task board

        Returns:
            Rich table
        """
        table = Table(title="Task Board", show_header=True, header_style="bold magenta")

        table.add_column("ID", style="dim")
        table.add_column("Title", style="bold")
        table.add_column("Status")
        table.add_column("Priority")
        table.add_column("Assigned To", style="italic")
        table.add_column("Dependencies", style="dim")

        tasks = board.list_tasks()
        # Sort by priority and status
        tasks.sort(key=lambda t: (t.priority.value, t.status.value))

        for task in tasks:
            # Status with color
            status_color = self._get_task_status_color(task.status)
            status_text = Text(task.status.value, style=status_color)

            # Priority with color
            priority_color = self._get_priority_color(task.priority)
            priority_text = Text(task.priority.value, style=priority_color)

            # Assigned to
            assigned = task.assigned_to or "-"

            # Dependencies
            deps = ", ".join(task.dependencies) if task.dependencies else "-"

            table.add_row(
                task.id,
                task.title,
                status_text,
                priority_text,
                assigned,
                deps,
            )

        return table

    def render_monitoring_feed(
        self, monitor: MonitoringPanel, limit: int = 20
    ) -> Table:
        """
        Render monitoring feed.

        Args:
            monitor: Monitoring panel
            limit: Maximum events to show

        Returns:
            Rich table
        """
        table = Table(
            title="Monitoring Feed", show_header=True, header_style="bold yellow"
        )

        table.add_column("Time", style="dim")
        table.add_column("Agent", style="cyan")
        table.add_column("Event", style="bold")
        table.add_column("Message")

        events = monitor.get_recent_events(limit=limit)
        for event in events:
            # Format time
            time_str = event.timestamp.strftime("%H:%M:%S")

            # Event type with color
            level_color = self._get_level_color(event.level)
            event_text = Text(event.event_type, style=level_color)

            table.add_row(
                time_str,
                event.agent_id,
                event_text,
                event.message,
            )

        return table

    def render_metrics_table(self, fleet: AgentFleetManager) -> Table:
        """
        Render agent metrics table.

        Args:
            fleet: Agent fleet manager

        Returns:
            Rich table
        """
        table = Table(
            title="Agent Metrics", show_header=True, header_style="bold green"
        )

        table.add_column("Agent", style="bold")
        table.add_column("Total Tasks", justify="right")
        table.add_column("Success Rate", justify="right")
        table.add_column("Total Tokens", justify="right")
        table.add_column("Errors", justify="right")

        agents = fleet.list_agents()
        for agent in agents:
            metrics = fleet.get_metrics(agent.id)
            if metrics:
                # Success rate with color
                success_rate = metrics.success_rate * 100
                rate_color = "green" if success_rate >= 90 else "yellow"
                if success_rate < 70:
                    rate_color = "red"
                rate_text = Text(f"{success_rate:.1f}%", style=rate_color)

                table.add_row(
                    agent.name,
                    str(metrics.total_tasks),
                    rate_text,
                    f"{metrics.total_tokens:,}",
                    str(metrics.error_count),
                )

        return table

    def render_alerts(self, monitor: MonitoringPanel) -> Panel:
        """
        Render alerts panel.

        Args:
            monitor: Monitoring panel

        Returns:
            Rich panel
        """
        alerts = monitor.get_alerts()

        if not alerts:
            content = Text("No alerts", style="green")
        else:
            lines = []
            for alert in alerts[-10:]:  # Show last 10 alerts
                time_str = alert.timestamp.strftime("%H:%M:%S")
                level_color = self._get_level_color(alert.level)
                line = Text()
                line.append(f"[{time_str}] ", style="dim")
                line.append(f"{alert.level.upper()}: ", style=level_color)
                line.append(f"{alert.agent_id} - {alert.message}")
                lines.append(line)

            content = Text("\n").join(lines)

        return Panel(
            content,
            title=f"Alerts ({len(alerts)})",
            border_style="red" if alerts else "green",
        )

    def render_dashboard(
        self,
        fleet: AgentFleetManager,
        board: TaskBoard,
        monitor: MonitoringPanel,
    ) -> Layout:
        """
        Render complete dashboard layout.

        Args:
            fleet: Agent fleet manager
            board: Task board
            monitor: Monitoring panel

        Returns:
            Rich layout
        """
        layout = Layout()

        # Split into top and bottom
        layout.split_column(
            Layout(name="top", ratio=2),
            Layout(name="bottom", ratio=1),
        )

        # Top: agents and tasks
        layout["top"].split_row(
            Layout(self.render_agent_table(fleet), name="agents"),
            Layout(self.render_task_board(board), name="tasks"),
        )

        # Bottom: monitoring and alerts
        layout["bottom"].split_row(
            Layout(self.render_monitoring_feed(monitor), name="monitoring"),
            Layout(self.render_alerts(monitor), name="alerts"),
        )

        return layout

    def display_dashboard(
        self,
        fleet: AgentFleetManager,
        board: TaskBoard,
        monitor: MonitoringPanel,
    ):
        """
        Display dashboard (static).

        Args:
            fleet: Agent fleet manager
            board: Task board
            monitor: Monitoring panel
        """
        layout = self.render_dashboard(fleet, board, monitor)
        self.console.print(layout)

    def live_dashboard(
        self,
        fleet: AgentFleetManager,
        board: TaskBoard,
        monitor: MonitoringPanel,
        refresh_rate: float = 1.0,
    ) -> Live:
        """
        Create live dashboard (auto-refreshing).

        Args:
            fleet: Agent fleet manager
            board: Task board
            monitor: Monitoring panel
            refresh_rate: Refresh rate in seconds

        Returns:
            Rich Live display
        """
        layout = self.render_dashboard(fleet, board, monitor)
        return Live(layout, console=self.console, refresh_per_second=1 / refresh_rate)

    def _get_status_color(self, status: AgentStatus) -> str:
        """Get color for agent status."""
        colors = {
            AgentStatus.IDLE: "dim",
            AgentStatus.WORKING: "yellow",
            AgentStatus.SUCCESS: "green",
            AgentStatus.ERROR: "red",
            AgentStatus.PAUSED: "blue",
        }
        return colors.get(status, "white")

    def _get_task_status_color(self, status: TaskStatus) -> str:
        """Get color for task status."""
        colors = {
            TaskStatus.TODO: "dim",
            TaskStatus.IN_PROGRESS: "yellow",
            TaskStatus.DONE: "green",
            TaskStatus.BLOCKED: "red",
            TaskStatus.CANCELLED: "dim red",
        }
        return colors.get(status, "white")

    def _get_priority_color(self, priority: TaskPriority) -> str:
        """Get color for task priority."""
        colors = {
            TaskPriority.LOW: "dim",
            TaskPriority.MEDIUM: "yellow",
            TaskPriority.HIGH: "orange1",
            TaskPriority.CRITICAL: "red bold",
        }
        return colors.get(priority, "white")

    def _get_level_color(self, level: str) -> str:
        """Get color for event level."""
        colors = {
            "info": "cyan",
            "warning": "yellow",
            "error": "red",
        }
        return colors.get(level, "white")


class AgentStatusWidget:
    """
    Agent status widget for status panel.

    Features:
    - Compact agent status display
    - Real-time updates
    - Color-coded status
    """

    def __init__(self, console: Console | None = None):
        """
        Initialize agent status widget.

        Args:
            console: Rich console
        """
        self.console = console or Console()

    def render(self, agents: list[AgentInfo]) -> Panel:
        """
        Render agent status widget.

        Args:
            agents: List of agents

        Returns:
            Rich panel
        """
        if not agents:
            content = Text("No agents", style="dim")
        else:
            lines = []
            for agent in agents:
                status_icon = self._get_status_icon(agent.status)
                status_color = self._get_status_color(agent.status)

                line = Text()
                line.append(f"{status_icon} ", style=status_color)
                line.append(f"{agent.name}", style="bold")

                if agent.current_task:
                    line.append(f" → {agent.current_task}", style="italic dim")

                lines.append(line)

            content = Text("\n").join(lines)

        return Panel(
            content,
            title="Agents",
            border_style="cyan",
        )

    def _get_status_icon(self, status: AgentStatus) -> str:
        """Get icon for agent status."""
        icons = {
            AgentStatus.IDLE: "○",
            AgentStatus.WORKING: "●",
            AgentStatus.SUCCESS: "✓",
            AgentStatus.ERROR: "✗",
            AgentStatus.PAUSED: "⏸",
        }
        return icons.get(status, "○")

    def _get_status_color(self, status: AgentStatus) -> str:
        """Get color for agent status."""
        colors = {
            AgentStatus.IDLE: "dim",
            AgentStatus.WORKING: "yellow",
            AgentStatus.SUCCESS: "green",
            AgentStatus.ERROR: "red",
            AgentStatus.PAUSED: "blue",
        }
        return colors.get(status, "white")


class TaskSummaryWidget:
    """
    Task summary widget for status panel.

    Features:
    - Task count by status
    - Progress indicator
    - Priority breakdown
    """

    def __init__(self, console: Console | None = None):
        """
        Initialize task summary widget.

        Args:
            console: Rich console
        """
        self.console = console or Console()

    def render(self, board: TaskBoard) -> Panel:
        """
        Render task summary widget.

        Args:
            board: Task board

        Returns:
            Rich panel
        """
        tasks = board.list_tasks()

        if not tasks:
            content = Text("No tasks", style="dim")
        else:
            # Count by status
            todo = len([t for t in tasks if t.status == TaskStatus.TODO])
            in_progress = len([t for t in tasks if t.status == TaskStatus.IN_PROGRESS])
            done = len([t for t in tasks if t.status == TaskStatus.DONE])
            blocked = len([t for t in tasks if t.status == TaskStatus.BLOCKED])

            # Progress percentage
            total = len(tasks)
            progress = (done / total * 100) if total > 0 else 0

            lines = []
            lines.append(Text(f"Total: {total}", style="bold"))
            lines.append(Text(f"✓ Done: {done}", style="green"))
            lines.append(Text(f"● In Progress: {in_progress}", style="yellow"))
            lines.append(Text(f"○ Todo: {todo}", style="dim"))
            if blocked > 0:
                lines.append(Text(f"✗ Blocked: {blocked}", style="red"))
            lines.append(Text(f"\nProgress: {progress:.1f}%", style="cyan"))

            content = Text("\n").join(lines)

        return Panel(
            content,
            title="Tasks",
            border_style="magenta",
        )
