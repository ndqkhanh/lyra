"""Rich-based output formatting utilities"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from rich.text import Text
from typing import List, Dict, Any, Optional

# Global console instance
console = Console()


class OutputFormatter:
    """Handles all Rich-based output formatting"""

    def __init__(self, console_instance: Optional[Console] = None):
        self.console = console_instance or console

    def welcome_screen(
        self,
        user: str,
        model: str,
        cwd: str,
        organization: str = "Claude Max"
    ) -> None:
        """Display welcome screen with box drawing"""
        logo = """
              ▐▛███▜▌
             ▝▜█████▛▘
               ▘▘ ▝▝
        """

        content = Text()
        content.append(f"\n\nWelcome back {user}!\n\n", style="bold cyan")
        content.append(logo, style="magenta")
        content.append(f"\n{model} · {organization}\n", style="dim")
        content.append(f"  {cwd}\n", style="dim blue")

        panel = Panel(
            content,
            title="Lyra v0.1.0",
            border_style="cyan",
            padding=(1, 2),
        )
        self.console.print(panel)

        # Show tips
        self.console.print("\n[dim]Tips:[/dim]")
        self.console.print("  • Type your message to start chatting", style="dim")
        self.console.print("  • Use /help for available commands", style="dim")
        self.console.print("  • Press Ctrl+C to interrupt, Ctrl+D to exit", style="dim")
        self.console.print()

    def status_message(
        self,
        message: str,
        spinner: str = "⏺",
        style: str = "cyan"
    ) -> None:
        """Display status message with spinner"""
        self.console.print(f"{spinner} {message}", style=style)

    def success_message(self, message: str) -> None:
        """Display success message"""
        self.console.print(f"✓ {message}", style="green")

    def error_message(self, message: str) -> None:
        """Display error message"""
        self.console.print(f"✗ {message}", style="red")

    def warning_message(self, message: str) -> None:
        """Display warning message"""
        self.console.print(f"⚠ {message}", style="yellow")

    def info_message(self, message: str) -> None:
        """Display info message"""
        self.console.print(f"ℹ {message}", style="blue")

    def background_tasks(self, tasks: List[Dict[str, Any]]) -> None:
        """Display background task list"""
        if not tasks:
            return

        self.console.print("\n[bold]Background Tasks:[/bold]")
        tree = Tree("⏺ Active Tasks")

        for task in tasks:
            status = task.get("status", "running")
            name = task.get("name", "Unknown")
            progress = task.get("progress", 0)

            if status == "running":
                icon = "⏺"
                style = "cyan"
            elif status == "completed":
                icon = "✓"
                style = "green"
            elif status == "failed":
                icon = "✗"
                style = "red"
            else:
                icon = "⏳"
                style = "yellow"

            task_text = f"{icon} {name}"
            if progress > 0:
                task_text += f" ({progress}%)"

            tree.add(Text(task_text, style=style))

        self.console.print(tree)

    def agent_output(
        self,
        agent_name: str,
        tool_uses: int,
        tokens: int,
        duration: str
    ) -> None:
        """Display agent execution summary"""
        self.console.print(
            f"  ├ {agent_name} · {tool_uses} tool uses · {tokens:,} tokens · {duration}",
            style="dim"
        )

    def hierarchical_status(self, items: List[str], indent: int = 0) -> None:
        """Display hierarchical status output"""
        prefix = "  " * indent
        for item in items:
            self.console.print(f"{prefix}{item}")

    def status_table(
        self,
        title: str,
        headers: List[str],
        rows: List[List[str]]
    ) -> None:
        """Display status table"""
        table = Table(title=title, show_header=True, header_style="bold cyan")

        for header in headers:
            table.add_column(header)

        for row in rows:
            table.add_row(*row)

        self.console.print(table)

    def divider(self, char: str = "─", width: int = 80) -> None:
        """Display horizontal divider"""
        self.console.print(char * width, style="dim")
