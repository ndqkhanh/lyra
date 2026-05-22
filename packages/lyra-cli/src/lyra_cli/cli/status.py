"""Status display with spinners and progress bars"""

from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn
)
from contextlib import contextmanager
from typing import Optional


class StatusDisplay:
    """Handles status display during operations"""

    def __init__(self, console: Console):
        self.console = console
        self._live: Optional[Live] = None
        self._progress: Optional[Progress] = None

    @contextmanager
    def spinner(self, message: str, spinner_style: str = "dots"):
        """Context manager for spinner display"""
        spinner = Spinner(spinner_style, text=message)
        with Live(spinner, console=self.console, refresh_per_second=10):
            yield

    @contextmanager
    def progress_bar(self):
        """Context manager for progress bar"""
        progress = Progress(
            SpinnerColumn(spinner_name="dots"),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=self.console
        )

        with progress:
            yield progress

    def show_working(self, message: str = "Working...") -> None:
        """Show working indicator"""
        self.console.print(f"⏺ {message}", style="cyan")

    def show_thinking(self, message: str = "Thinking...") -> None:
        """Show thinking indicator"""
        self.console.print(f"✶ {message}", style="blue")

    def show_processing(self, message: str = "Processing...") -> None:
        """Show processing indicator"""
        self.console.print(f"✻ {message}", style="yellow")
