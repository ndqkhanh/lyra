"""
Rich Formatter for Beautiful Terminal Output

Provides beautiful formatting using the Rich library.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from lyra_ui.themes import ThemeManager


@dataclass
class FormatterColors:
    """Color configuration for formatter."""

    primary: str
    secondary: str
    accent: str
    success: str
    warning: str
    error: str
    info: str
    text_dim: str
    surface: str


class RichFormatter:
    """
    Rich formatter for beautiful terminal output.

    Provides methods for formatting messages, code, tables, and more.
    """

    def __init__(self):
        """Initialize formatter."""
        self.console = Console()
        self.theme_manager = ThemeManager()
        theme_colors = self.theme_manager.get_current_theme()

        # Map theme colors to formatter attributes
        self.colors = FormatterColors(
            primary=theme_colors.primary,
            secondary=theme_colors.secondary,
            accent=theme_colors.warning,  # Use warning as accent
            success=theme_colors.success,
            warning=theme_colors.warning,
            error=theme_colors.error,
            info=theme_colors.info,
            text_dim=theme_colors.dim,
            surface=theme_colors.background,
        )

    def print_message(
        self,
        message: str,
        role: str = "assistant",
        title: Optional[str] = None,
    ) -> None:
        """
        Print a message bubble.

        Args:
            message: Message content
            role: Message role (user, assistant, system)
            title: Optional title
        """
        # Role-specific styling
        role_config = {
            "user": {
                "icon": "👤",
                "color": self.colors.secondary,
                "title": title or "You",
            },
            "assistant": {
                "icon": "🤖",
                "color": self.colors.primary,
                "title": title or "Assistant",
            },
            "system": {
                "icon": "⚙️",
                "color": self.colors.text_dim,
                "title": title or "System",
            },
        }

        config = role_config.get(role, role_config["assistant"])

        # Create panel
        panel = Panel(
            message,
            title=f"{config['icon']} {config['title']}",
            border_style=config["color"],
            padding=(0, 1),
        )

        self.console.print(panel)

    def print_code(
        self,
        code: str,
        language: str = "python",
        title: Optional[str] = None,
    ) -> None:
        """
        Print syntax-highlighted code.

        Args:
            code: Code content
            language: Programming language
            title: Optional title
        """
        syntax = Syntax(
            code,
            language,
            theme="monokai",
            line_numbers=True,
            word_wrap=True,
        )

        if title:
            panel = Panel(syntax, title=f"📝 {title}", border_style=self.colors.accent)
            self.console.print(panel)
        else:
            self.console.print(syntax)

    def print_table(
        self,
        data: list[Dict[str, Any]],
        title: Optional[str] = None,
    ) -> None:
        """
        Print a beautiful table.

        Args:
            data: List of dictionaries
            title: Optional title
        """
        if not data:
            return

        # Create table
        table = Table(
            title=title,
            border_style=self.colors.surface,
            header_style=f"bold {self.colors.primary}",
        )

        # Add columns
        for key in data[0].keys():
            table.add_column(key.replace("_", " ").title())

        # Add rows
        for row in data:
            table.add_row(*[str(v) for v in row.values()])

        self.console.print(table)

    def print_status(
        self,
        message: str,
        status: str = "info",
    ) -> None:
        """
        Print a status message.

        Args:
            message: Status message
            status: Status type (success, warning, error, info)
        """
        status_config = {
            "success": {"icon": "✅", "color": self.colors.success},
            "warning": {"icon": "⚠️", "color": self.colors.warning},
            "error": {"icon": "❌", "color": self.colors.error},
            "info": {"icon": "ℹ️", "color": self.colors.info},
        }

        config = status_config.get(status, status_config["info"])

        text = Text()
        text.append(f"{config['icon']} ", style=config["color"])
        text.append(message)

        self.console.print(text)

    def print_markdown(self, markdown: str) -> None:
        """
        Print formatted markdown.

        Args:
            markdown: Markdown content
        """
        md = Markdown(markdown)
        self.console.print(md)

    def create_progress(self, description: str = "Processing...") -> Progress:
        """
        Create a progress indicator.

        Args:
            description: Progress description

        Returns:
            Progress object
        """
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        )
        progress.add_task(description)
        return progress

    def print_header(self, title: str, subtitle: Optional[str] = None) -> None:
        """
        Print a beautiful header.

        Args:
            title: Header title
            subtitle: Optional subtitle
        """
        text = Text()
        text.append("🌟 ", style=self.colors.accent)
        text.append(title, style=f"bold {self.colors.primary}")

        if subtitle:
            text.append(f"\n{subtitle}", style=self.colors.text_dim)

        panel = Panel(
            text,
            border_style=self.colors.primary,
            padding=(0, 2),
        )

        self.console.print(panel)

    def print_divider(self, char: str = "─") -> None:
        """Print a divider line."""
        width = self.console.width
        self.console.print(char * width, style=self.colors.surface)
