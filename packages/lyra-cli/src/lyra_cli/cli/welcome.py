"""Welcome screen rendering"""

from rich.console import Console
from pathlib import Path
import os


def show_welcome(console: Console, model: str = "Opus 4.7") -> None:
    """Display welcome screen"""
    from lyra_cli.cli.output import OutputFormatter

    # Get user info
    user = os.getenv("USER", "User")
    cwd = str(Path.cwd())

    # Create formatter and show welcome
    formatter = OutputFormatter(console)
    formatter.welcome_screen(user=user, model=model, cwd=cwd)
