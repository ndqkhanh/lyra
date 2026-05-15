"""Output formatting for Lyra CLI - Claude Code style.

Provides clean, readable output formatting for:
- Markdown rendering
- Tool execution status
- Error messages
- Status updates
"""

from __future__ import annotations

import sys
from typing import TextIO

try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.syntax import Syntax

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class CLIFormatter:
    """Format CLI output with optional Rich styling."""

    def __init__(self, use_rich: bool = True, file: TextIO | None = None):
        self.use_rich = use_rich and RICH_AVAILABLE
        self.file = file or sys.stdout
        if self.use_rich:
            self.console = Console(force_terminal=True)

    def print(self, text: str, end: str = "\n", flush: bool = False) -> None:
        """Print plain text."""
        print(text, end=end, flush=flush, file=self.file)

    def print_markdown(self, text: str) -> None:
        """Print markdown-formatted text."""
        if self.use_rich and RICH_AVAILABLE:
            md = Markdown(text)
            self.console.print(md)
        else:
            self.print(text)

    def print_tool_start(self, tool_name: str) -> None:
        """Print tool execution start indicator."""
        if self.use_rich:
            self.console.print(f"[dim][Using {tool_name}...][/dim]", end="")
        else:
            self.print(f"[Using {tool_name}...]", end="", flush=True)

    def print_tool_end(self, success: bool = True) -> None:
        """Print tool execution end indicator."""
        if self.use_rich:
            if success:
                self.console.print(" [green]done[/green]")
            else:
                self.console.print(" [red]error[/red]")
        else:
            self.print(" done" if success else " error")

    def print_thinking(self, text: str) -> None:
        """Print extended thinking output (dimmed)."""
        if self.use_rich:
            self.console.print(f"[dim]{text}[/dim]", end="")
        else:
            self.print(text, end="", flush=True)

    def print_error(self, message: str) -> None:
        """Print error message."""
        if self.use_rich:
            self.console.print(f"[bold red]Error:[/bold red] {message}")
        else:
            self.print(f"Error: {message}", file=sys.stderr)

    def print_warning(self, message: str) -> None:
        """Print warning message."""
        if self.use_rich:
            self.console.print(f"[bold yellow]Warning:[/bold yellow] {message}")
        else:
            self.print(f"Warning: {message}")

    def print_info(self, message: str) -> None:
        """Print info message."""
        if self.use_rich:
            self.console.print(f"[bold blue]Info:[/bold blue] {message}")
        else:
            self.print(f"Info: {message}")

    def print_success(self, message: str) -> None:
        """Print success message."""
        if self.use_rich:
            self.console.print(f"[bold green]✓[/bold green] {message}")
        else:
            self.print(f"✓ {message}")

    def print_status(self, message: str) -> None:
        """Print status update."""
        if self.use_rich:
            self.console.print(f"[dim]{message}[/dim]")
        else:
            self.print(message)

    def print_code(self, code: str, language: str = "python") -> None:
        """Print syntax-highlighted code."""
        if self.use_rich and RICH_AVAILABLE:
            syntax = Syntax(code, language, theme="monokai", line_numbers=False)
            self.console.print(syntax)
        else:
            self.print(code)

    def print_panel(self, content: str, title: str | None = None) -> None:
        """Print content in a panel."""
        if self.use_rich and RICH_AVAILABLE:
            panel = Panel(content, title=title, border_style="blue")
            self.console.print(panel)
        else:
            if title:
                self.print(f"\n=== {title} ===")
            self.print(content)
            if title:
                self.print("=" * (len(title) + 8))

    def print_welcome(
        self, version: str, model: str, repo: str, session_id: str
    ) -> None:
        """Print welcome banner."""
        welcome = f"""
# Lyra v{version}

**Model:** {model}
**Repo:** {repo}
**Session:** {session_id}

Type `/help` for commands, `/status` for session info, or start chatting.
"""
        self.print_markdown(welcome.strip())
        self.print("")  # Empty line after welcome

    def print_result(
        self, cost_usd: float, tokens_in: int, tokens_out: int, duration_ms: int
    ) -> None:
        """Print turn result summary."""
        duration_s = duration_ms / 1000
        if self.use_rich:
            self.console.print(
                f"[dim]Cost: ${cost_usd:.4f} | "
                f"Tokens: {tokens_in:,} in / {tokens_out:,} out | "
                f"Time: {duration_s:.1f}s[/dim]"
            )
        else:
            self.print(
                f"Cost: ${cost_usd:.4f} | "
                f"Tokens: {tokens_in:,} in / {tokens_out:,} out | "
                f"Time: {duration_s:.1f}s"
            )


# Global formatter instance
_formatter: CLIFormatter | None = None


def get_formatter() -> CLIFormatter:
    """Get or create global formatter instance."""
    global _formatter
    if _formatter is None:
        _formatter = CLIFormatter()
    return _formatter


def set_formatter(formatter: CLIFormatter) -> None:
    """Set global formatter instance."""
    global _formatter
    _formatter = formatter
