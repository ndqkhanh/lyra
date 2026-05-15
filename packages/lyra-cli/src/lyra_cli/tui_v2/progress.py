"""Enhanced progress indicators with animations for Lyra TUI.

Provides nyan-cat style animated progress bars and spinners using alive-progress.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

try:
    from alive_progress import alive_bar
except ImportError:
    alive_bar = None  # type: ignore
from rich.console import Console
from rich.live import Live
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
)

console = Console()


@contextmanager
def animated_spinner(
    total: int = 100,
    bar: str = "smooth",
    spinner: str = "dots_waves",
    title: str = "Processing",
) -> Generator[callable, None, None]:
    """Create an animated progress bar with nyan-cat style animations.

    Args:
        total: Total number of steps
        bar: Bar style (smooth, classic, blocks, etc.)
        spinner: Spinner style (dots_waves, dots, classic, etc.)
        title: Progress bar title

    Yields:
        Callable to increment progress

    Example:
        >>> with animated_spinner(100, title="Researching") as bar:
        ...     for i in range(100):
        ...         time.sleep(0.05)
        ...         bar()
    """
    if alive_bar is None:
        # Fallback to simple progress if alive_progress not installed
        def noop():
            pass

        yield noop
        return

    with alive_bar(total, bar=bar, spinner=spinner, title=title) as bar:
        yield bar


class LyraProgress:
    """Rich-based progress tracker for multi-task operations."""

    def __init__(self) -> None:
        """Initialize progress tracker."""
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
        )
        self.tasks: dict[str, TaskID] = {}

    def __enter__(self) -> LyraProgress:
        """Enter context manager."""
        self.progress.__enter__()
        return self

    def __exit__(self, *args) -> None:
        """Exit context manager."""
        self.progress.__exit__(*args)

    def add_task(self, name: str, description: str, total: int = 100) -> TaskID:
        """Add a new task to track.

        Args:
            name: Task identifier
            description: Task description
            total: Total steps

        Returns:
            Task ID for updates
        """
        task_id = self.progress.add_task(description, total=total)
        self.tasks[name] = task_id
        return task_id

    def update(self, name: str, advance: int = 1) -> None:
        """Update task progress.

        Args:
            name: Task identifier
            advance: Steps to advance
        """
        if name in self.tasks:
            self.progress.update(self.tasks[name], advance=advance)

    def complete(self, name: str) -> None:
        """Mark task as complete.

        Args:
            name: Task identifier
        """
        if name in self.tasks:
            self.progress.update(self.tasks[name], completed=True)


@contextmanager
def streaming_output(refresh_per_second: int = 10) -> Generator[callable, None, None]:
    """Create a live-updating display for streaming content.

    Args:
        refresh_per_second: Update frequency

    Yields:
        Callable to update display content

    Example:
        >>> from rich.markdown import Markdown
        >>> with streaming_output() as update:
        ...     buffer = ""
        ...     for chunk in llm_stream():
        ...         buffer += chunk
        ...         update(Markdown(buffer))
    """
    with Live(console=console, refresh_per_second=refresh_per_second) as live:

        def update(content):
            live.update(content)

        yield update


__all__ = [
    "animated_spinner",
    "LyraProgress",
    "streaming_output",
    "console",
]
