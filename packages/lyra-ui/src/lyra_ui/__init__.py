"""
Lyra UI - Beautiful terminal UI using Rich and Textual.

This package provides:
- Rich console with themes
- Progress indicators
- Textual TUI framework
- Status displays
"""

from lyra_ui.console import RichConsole, console
from lyra_ui.progress import ProgressManager, Spinner

__version__ = "0.1.0"

__all__ = [
    # Console
    "RichConsole",
    "console",
    # Progress
    "ProgressManager",
    "Spinner",
]
