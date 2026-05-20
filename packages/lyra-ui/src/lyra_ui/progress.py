"""
Progress Indicators - Rich progress bars and spinners.

Features:
- Progress bars for long operations
- Spinners for async tasks
- Multi-task progress tracking
"""

from typing import Optional

from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)


class ProgressManager:
    """
    Progress indicator manager.

    Features:
    - Multiple progress bars
    - Spinners for indeterminate tasks
    - Time tracking
    """

    def __init__(self):
        """Initialize progress manager."""
        self.progress: Optional[Progress] = None
        self.tasks: dict[str, TaskID] = {}

    def start(self):
        """Start progress display."""
        if self.progress is None:
            self.progress = Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
                TimeRemainingColumn(),
            )
            self.progress.start()

    def stop(self):
        """Stop progress display."""
        if self.progress:
            self.progress.stop()
            self.progress = None
            self.tasks.clear()

    def add_task(
        self, name: str, description: str, total: Optional[float] = None
    ) -> str:
        """
        Add progress task.

        Args:
            name: Task identifier
            description: Task description
            total: Total units (None for indeterminate)

        Returns:
            Task name
        """
        if not self.progress:
            self.start()

        task_id = self.progress.add_task(description, total=total)
        self.tasks[name] = task_id
        return name

    def update_task(self, name: str, advance: float = 1.0, description: Optional[str] = None):
        """
        Update task progress.

        Args:
            name: Task identifier
            advance: Amount to advance
            description: New description
        """
        if name in self.tasks and self.progress:
            kwargs = {"advance": advance}
            if description:
                kwargs["description"] = description
            self.progress.update(self.tasks[name], **kwargs)

    def complete_task(self, name: str):
        """
        Mark task as complete.

        Args:
            name: Task identifier
        """
        if name in self.tasks and self.progress:
            self.progress.update(self.tasks[name], completed=True)

    def remove_task(self, name: str):
        """
        Remove task.

        Args:
            name: Task identifier
        """
        if name in self.tasks and self.progress:
            self.progress.remove_task(self.tasks[name])
            del self.tasks[name]


class Spinner:
    """
    Simple spinner for async operations.

    Features:
    - Indeterminate progress
    - Status messages
    """

    def __init__(self, description: str = "Working..."):
        """Initialize spinner."""
        self.description = description
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
        )
        self.task_id: Optional[TaskID] = None

    def __enter__(self):
        """Start spinner."""
        self.progress.start()
        self.task_id = self.progress.add_task(self.description)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop spinner."""
        self.progress.stop()

    def update(self, description: str):
        """Update spinner description."""
        if self.task_id is not None:
            self.progress.update(self.task_id, description=description)
