"""
Rich Console - Styled terminal output with Rich.

Features:
- Singleton console instance
- Theme management
- Syntax highlighting
- Progress bars and spinners
"""

from typing import Optional

from rich.console import Console
from rich.theme import Theme


class RichConsole:
    """
    Singleton Rich console with theme support.

    Features:
    - Consistent styling across application
    - Theme switching
    - Syntax highlighting
    """

    _instance: Optional["RichConsole"] = None
    _console: Optional[Console] = None

    def __new__(cls):
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize Rich console."""
        if self._console is None:
            self.__class__._console = Console(theme=self._get_default_theme())

    @staticmethod
    def _get_default_theme() -> Theme:
        """
        Get default theme.

        Returns:
            Rich theme
        """
        return Theme(
            {
                # Status colors
                "success": "bold green",
                "error": "bold red",
                "warning": "bold yellow",
                "info": "bold blue",
                # UI elements
                "prompt": "bold cyan",
                "command": "bold magenta",
                "path": "bold blue underline",
                "code": "cyan",
                # Agent status
                "agent.idle": "dim white",
                "agent.working": "bold yellow",
                "agent.success": "bold green",
                "agent.error": "bold red",
                # Context indicators
                "context.low": "green",
                "context.medium": "yellow",
                "context.high": "red",
            }
        )

    @property
    def console(self) -> Console:
        """Get console instance."""
        if self._console is None:
            self.__class__._console = Console(theme=self._get_default_theme())
        return self._console

    def set_theme(self, theme: Theme):
        """
        Set console theme.

        Args:
            theme: Rich theme
        """
        self.__class__._console = Console(theme=theme)

    def print(self, *args, **kwargs):
        """Print to console."""
        self._console.print(*args, **kwargs)

    def print_success(self, message: str):
        """Print success message."""
        self._console.print(f"✓ {message}", style="success")

    def print_error(self, message: str):
        """Print error message."""
        self._console.print(f"✗ {message}", style="error")

    def print_warning(self, message: str):
        """Print warning message."""
        self._console.print(f"⚠ {message}", style="warning")

    def print_info(self, message: str):
        """Print info message."""
        self._console.print(f"ℹ {message}", style="info")


# Global console instance
console = RichConsole()
