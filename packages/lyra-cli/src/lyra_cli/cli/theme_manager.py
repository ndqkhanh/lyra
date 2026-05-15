"""Theme Manager for Lyra TUI.

Implements Tokyo Night and other themes with Rich integration.
"""

from __future__ import annotations

from typing import Dict
from rich.theme import Theme
from rich.console import Console


# Tokyo Night Theme (Most popular 2026)
TOKYO_NIGHT = {
    "info": "cyan",
    "warning": "yellow",
    "error": "red",
    "success": "green",
    "primary": "#7dcfff",
    "secondary": "#bb9af7",
    "accent": "#7aa2f7",
    "muted": "dim",
}

# Dracula Theme
DRACULA = {
    "info": "#8be9fd",
    "warning": "#f1fa8c",
    "error": "#ff5555",
    "success": "#50fa7b",
    "primary": "#bd93f9",
    "secondary": "#ff79c6",
    "accent": "#8be9fd",
    "muted": "dim",
}

# Nord Theme
NORD = {
    "info": "#88c0d0",
    "warning": "#ebcb8b",
    "error": "#bf616a",
    "success": "#a3be8c",
    "primary": "#88c0d0",
    "secondary": "#81a1c1",
    "accent": "#5e81ac",
    "muted": "dim",
}

# Gruvbox Theme
GRUVBOX = {
    "info": "#83a598",
    "warning": "#fabd2f",
    "error": "#fb4934",
    "success": "#b8bb26",
    "primary": "#fe8019",
    "secondary": "#d3869b",
    "accent": "#83a598",
    "muted": "dim",
}

THEMES = {
    "tokyo-night": TOKYO_NIGHT,
    "dracula": DRACULA,
    "nord": NORD,
    "gruvbox": GRUVBOX,
}


class ThemeManager:
    """Manages TUI themes."""

    def __init__(self, theme_name: str = "tokyo-night"):
        self.current_theme = theme_name
        self.console = self._create_console()

    def _create_console(self) -> Console:
        """Create Rich console with current theme."""
        theme_colors = THEMES.get(self.current_theme, TOKYO_NIGHT)
        theme = Theme(theme_colors)
        return Console(theme=theme)

    def set_theme(self, theme_name: str):
        """Switch to a different theme."""
        if theme_name not in THEMES:
            raise ValueError(f"Unknown theme: {theme_name}")

        self.current_theme = theme_name
        self.console = self._create_console()

    def get_available_themes(self) -> list[str]:
        """Get list of available themes."""
        return list(THEMES.keys())

    def print(self, text: str, style: str = None):
        """Print with theme styling."""
        self.console.print(text, style=style)

    def print_info(self, text: str):
        """Print info message."""
        self.console.print(text, style="info")

    def print_warning(self, text: str):
        """Print warning message."""
        self.console.print(text, style="warning")

    def print_error(self, text: str):
        """Print error message."""
        self.console.print(text, style="error")

    def print_success(self, text: str):
        """Print success message."""
        self.console.print(text, style="success")
