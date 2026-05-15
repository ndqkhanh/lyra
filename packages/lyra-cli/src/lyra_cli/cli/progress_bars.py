"""Progress Bar System for Lyra.

Implements Rich progress bars and alive-progress animations.
"""

from __future__ import annotations

from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeElapsedColumn,
    TaskProgressColumn,
)
from rich.console import Console


class ProgressBarManager:
    """Manages progress bars for various operations."""

    def __init__(self, console: Console = None):
        self.console = console or Console()

    def create_research_progress(self) -> Progress:
        """Create progress bar for research pipeline."""
        return Progress(
            SpinnerColumn("dots"),
            TextColumn("[bold cyan]{task.description}"),
            BarColumn(bar_width=40),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=self.console,
        )

    def create_team_progress(self) -> Progress:
        """Create progress bar for team execution."""
        return Progress(
            TextColumn("  ├─"),
            SpinnerColumn("simpleDots"),
            TextColumn("[bold magenta]{task.fields[action]}"),
            BarColumn(bar_width=30),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=self.console,
        )

    def create_simple_progress(self) -> Progress:
        """Create simple progress bar."""
        return Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console,
        )
