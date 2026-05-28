"""Enhanced CLI output with Claude Code-inspired design"""


from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text


class OutputFormatter:
    """Format CLI output with Claude Code-inspired design"""

    def __init__(self, console: Console):
        self.console = console
        self.live: Live | None = None

    # Status indicators (Claude Code style)
    SPINNER_WORKING = "dots"
    SPINNER_THINKING = "dots12"

    # Symbols (Claude Code style)
    SYMBOL_SUCCESS = "✓"
    SYMBOL_ERROR = "✗"
    SYMBOL_WARNING = "⚠"
    SYMBOL_INFO = "ℹ"
    SYMBOL_TOOL = "⎿"
    SYMBOL_STATS = "✻"

    def success_message(self, message: str):
        """Display success message (Claude Code style)"""
        self.console.print(f"[green]{self.SYMBOL_SUCCESS}[/green] {message}")

    def error_message(self, message: str):
        """Display error message (Claude Code style)"""
        self.console.print(f"[red]{self.SYMBOL_ERROR}[/red] {message}")

    def warning_message(self, message: str):
        """Display warning message (Claude Code style)"""
        self.console.print(f"[yellow]{self.SYMBOL_WARNING}[/yellow] {message}")

    def info_message(self, message: str):
        """Display info message (Claude Code style)"""
        self.console.print(f"[cyan]{self.SYMBOL_INFO}[/cyan] {message}")

    def status_message(self, message: str, spinner: str = "dots", style: str = "cyan"):
        """Display status message with spinner (Claude Code style)"""
        text = Text()
        text.append(f"{message}", style=style)
        self.console.print(text)

    def tool_use(self, tool_name: str, collapsed: bool = False):
        """Display tool use (Claude Code style)"""
        if collapsed:
            self.console.print(f"  [dim]{self.SYMBOL_TOOL} {tool_name}[/dim]")
        else:
            self.console.print(f"  [cyan]{self.SYMBOL_TOOL}[/cyan] [dim]{tool_name}[/dim]")

    def stats_line(self, duration: str, tool_count: int, tokens: int):
        """Display stats line (Claude Code style)"""
        self.console.print(
            f"\n[dim]{self.SYMBOL_STATS} Worked for {duration} · "
            f"{tool_count} tool use{'s' if tool_count != 1 else ''} · "
            f"{tokens:,} tokens[/dim]"
        )

    def section_header(self, title: str):
        """Display section header (Claude Code style)"""
        self.console.print(f"\n[bold cyan]{title}[/bold cyan]")

    def divider(self, char: str = "─"):
        """Display divider line"""
        width = self.console.width
        self.console.print(f"[dim]{char * width}[/dim]")

    def command_list(self, commands: list[tuple[str, str]]):
        """Display command list (Claude Code style)"""
        for cmd, desc in commands:
            self.console.print(f"  [cyan]{cmd:20}[/cyan] [dim]{desc}[/dim]")

    def status_bar(self, left: str = "", center: str = "", right: str = ""):
        """Display status bar at bottom (Claude Code style)"""
        width = self.console.width

        # Calculate spacing
        left_len = len(left)
        right_len = len(right)
        center_len = len(center)

        # Calculate padding
        total_content = left_len + center_len + right_len
        if total_content >= width:
            # Truncate if too long
            status = f"{left[:width-3]}..."
        else:
            # Center the middle content
            left_padding = (width - total_content) // 2
            right_padding = width - total_content - left_padding

            status = f"{left}{' ' * left_padding}{center}{' ' * right_padding}{right}"

        self.console.print(f"[dim on black]{status}[/dim on black]")

    def thinking_indicator(self, show: bool = True):
        """Show/hide thinking indicator (Claude Code style)"""
        if show:
            self.console.print("[dim]Thinking...[/dim]", end="")
        else:
            # Clear the line
            self.console.print("\r" + " " * 20 + "\r", end="")

    def stream_text(self, text: str, end: str = ""):
        """Stream text output (Claude Code style)"""
        self.console.print(text, end=end, markup=False, highlight=False)

    def collapsed_section(self, title: str, content: str, expanded: bool = False):
        """Display collapsible section (Claude Code style)"""
        if expanded:
            self.console.print(f"\n[cyan]▼ {title}[/cyan]")
            self.console.print(f"[dim]{content}[/dim]")
        else:
            self.console.print(f"[dim]▶ {title}[/dim]")

    def permission_prompt(self, tool: str, args: str) -> bool:
        """Display permission prompt (Claude Code style)"""
        panel = Panel(
            f"[yellow]Tool:[/yellow] {tool}\n[yellow]Args:[/yellow] {args}",
            title="[bold yellow]Permission Required[/bold yellow]",
            border_style="yellow"
        )
        self.console.print(panel)

        response = self.console.input("[yellow]Allow?[/yellow] [dim](y/n/always/never)[/dim]: ")
        return response.lower() in ['y', 'yes', 'always']

    def progress_bar(self, current: int, total: int, description: str = ""):
        """Display progress bar (Claude Code style)"""
        percentage = (current / total) * 100 if total > 0 else 0
        bar_width = 30
        filled = int((current / total) * bar_width) if total > 0 else 0
        bar = "█" * filled + "░" * (bar_width - filled)

        self.console.print(
            f"[cyan]{description}[/cyan] [{bar}] {percentage:.0f}% ({current}/{total})"
        )

    def file_diff(self, filename: str, additions: int, deletions: int):
        """Display file diff stats (Claude Code style)"""
        self.console.print(
            f"  [dim]{filename}[/dim] "
            f"[green]+{additions}[/green] "
            f"[red]-{deletions}[/red]"
        )

    def clear_screen(self):
        """Clear the screen"""
        self.console.clear()

    def bell(self):
        """Ring terminal bell"""
        self.console.bell()
