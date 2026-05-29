"""
Progress Visualization - Enhanced progress displays with rich visualization.

Features:
- Multi-task progress
- Step-by-step progress
- Status indicators
- Time estimates
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    Progress,
    TaskID,
)
from rich.table import Table


class ProgressState(Enum):
    """Progress state."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ProgressStep:
    """Progress step."""

    name: str
    description: str
    state: ProgressState = ProgressState.PENDING
    progress: float = 0.0
    total: float = 100.0
    started_at: datetime | None = None
    completed_at: datetime | None = None


class MultiTaskProgress:
    """
    Multi-task progress tracker.

    Features:
    - Multiple parallel tasks
    - Step-by-step progress
    - Status indicators
    """

    def __init__(self):
        """Initialize multi-task progress."""
        self.tasks: dict[str, ProgressStep] = {}
        self.progress: Progress | None = None
        self.task_ids: dict[str, TaskID] = {}

    def add_task(
        self,
        task_id: str,
        name: str,
        description: str,
        total: float = 100.0,
    ):
        """
        Add task.

        Args:
            task_id: Task identifier
            name: Task name
            description: Task description
            total: Total progress units
        """
        self.tasks[task_id] = ProgressStep(
            name=name,
            description=description,
            total=total,
        )

    def start_task(self, task_id: str):
        """
        Start task.

        Args:
            task_id: Task identifier
        """
        if task_id in self.tasks:
            self.tasks[task_id].state = ProgressState.RUNNING
            self.tasks[task_id].started_at = datetime.now()

    def update_task(self, task_id: str, progress: float):
        """
        Update task progress.

        Args:
            task_id: Task identifier
            progress: Progress value
        """
        if task_id in self.tasks:
            self.tasks[task_id].progress = progress

    def complete_task(self, task_id: str, success: bool = True):
        """
        Complete task.

        Args:
            task_id: Task identifier
            success: Whether task succeeded
        """
        if task_id in self.tasks:
            self.tasks[task_id].state = (
                ProgressState.COMPLETED if success else ProgressState.FAILED
            )
            self.tasks[task_id].completed_at = datetime.now()

    def cancel_task(self, task_id: str):
        """
        Cancel task.

        Args:
            task_id: Task identifier
        """
        if task_id in self.tasks:
            self.tasks[task_id].state = ProgressState.CANCELLED

    def get_task(self, task_id: str) -> ProgressStep | None:
        """
        Get task.

        Args:
            task_id: Task identifier

        Returns:
            Progress step or None
        """
        return self.tasks.get(task_id)

    def get_all_tasks(self) -> list[ProgressStep]:
        """
        Get all tasks.

        Returns:
            List of progress steps
        """
        return list(self.tasks.values())

    def get_summary(self) -> dict[str, int]:
        """
        Get progress summary.

        Returns:
            Summary statistics
        """
        summary = {
            "total": len(self.tasks),
            "pending": 0,
            "running": 0,
            "completed": 0,
            "failed": 0,
            "cancelled": 0,
        }

        for task in self.tasks.values():
            summary[task.state.value] += 1

        return summary


class ProgressVisualizer:
    """
    Progress visualizer with Rich.

    Features:
    - Visual progress display
    - Status indicators
    - Time estimates
    """

    def __init__(self, console: Console | None = None):
        """Initialize progress visualizer."""
        self.console = console or Console()

    def render_task(self, step: ProgressStep) -> str:
        """
        Render task progress.

        Args:
            step: Progress step

        Returns:
            Rendered string
        """
        # Status icon
        status_icons = {
            ProgressState.PENDING: "⚪",
            ProgressState.RUNNING: "🟡",
            ProgressState.COMPLETED: "🟢",
            ProgressState.FAILED: "🔴",
            ProgressState.CANCELLED: "⚫",
        }
        icon = status_icons.get(step.state, "⚪")

        # Progress bar
        percentage = (step.progress / step.total * 100) if step.total > 0 else 0
        bar_width = 20
        filled = int((percentage / 100) * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)

        return f"{icon} {step.name}: [{bar}] {percentage:.1f}%"

    def render_summary(self, tracker: MultiTaskProgress) -> Panel:
        """
        Render progress summary.

        Args:
            tracker: Multi-task progress tracker

        Returns:
            Rich panel
        """
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Task", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Progress", style="yellow")

        for task in tracker.get_all_tasks():
            status_text = task.state.value.upper()
            progress_text = f"{task.progress:.0f}/{task.total:.0f}"
            table.add_row(task.name, status_text, progress_text)

        summary = tracker.get_summary()
        title = f"Progress: {summary['completed']}/{summary['total']} completed"

        return Panel(table, title=title, border_style="blue")

    def display_summary(self, tracker: MultiTaskProgress):
        """
        Display progress summary.

        Args:
            tracker: Multi-task progress tracker
        """
        panel = self.render_summary(tracker)
        self.console.print(panel)
