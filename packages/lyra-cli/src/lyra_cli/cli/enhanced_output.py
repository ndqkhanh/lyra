"""Enhanced output with best AI agent UI patterns"""


from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.syntax import Syntax
from rich.table import Table
from rich.tree import Tree


class EnhancedOutputFormatter:
    """Output formatter with patterns from top AI agents (Claude Code, Aider, Continue)"""

    def __init__(self, console: Console):
        self.console = console
        self.live: Live | None = None

    # Status indicators (Claude Code + Continue patterns)
    SYMBOL_SUCCESS = "✓"
    SYMBOL_ERROR = "✗"
    SYMBOL_WARNING = "⚠"
    SYMBOL_INFO = "ℹ"
    SYMBOL_TOOL = "⎿"
    SYMBOL_STATS = "✻"
    SYMBOL_ARROW = "→"
    SYMBOL_EXPAND = "▶"
    SYMBOL_COLLAPSE = "▼"

    def success(self, message: str):
        """Success message (green check)"""
        self.console.print(f"[green]{self.SYMBOL_SUCCESS}[/green] {message}")

    def error(self, message: str):
        """Error message (red X)"""
        self.console.print(f"[red]{self.SYMBOL_ERROR}[/red] [bold]{message}[/bold]")

    def warning(self, message: str):
        """Warning message (yellow triangle)"""
        self.console.print(f"[yellow]{self.SYMBOL_WARNING}[/yellow] {message}")

    def info(self, message: str):
        """Info message (cyan i)"""
        self.console.print(f"[cyan]{self.SYMBOL_INFO}[/cyan] [dim]{message}[/dim]")

    def tool_use(self, tool_name: str, args: str = "", collapsed: bool = False):
        """Tool use indicator (Claude Code pattern)"""
        if collapsed:
            self.console.print(f"[dim]{self.SYMBOL_TOOL} {tool_name}[/dim]")
        else:
            self.console.print(f"[cyan]{self.SYMBOL_TOOL}[/cyan] [dim]{tool_name}[/dim]")
            if args:
                self.console.print(f"  [dim blue]{args}[/dim blue]")

    def stats_line(self, duration: str, tool_count: int, tokens: int, cost: float = 0.0):
        """Stats line (Claude Code pattern)"""
        parts = [f"{duration}", f"{tool_count} tool{'s' if tool_count != 1 else ''}", f"{tokens:,} tokens"]
        if cost > 0:
            parts.append(f"${cost:.4f}")
        self.console.print(f"\n[dim]{self.SYMBOL_STATS} {' · '.join(parts)}[/dim]")

    def progress_bar(self, description: str = "Processing"):
        """Create a progress bar (Aider + Rich pattern)"""
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console,
        )

    def spinner(self, description: str = "Working"):
        """Create a spinner for indeterminate tasks (Continue pattern)"""
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        )

    def step_indicator(self, current: int, total: int, description: str):
        """Step indicator (OpenClaw pattern)"""
        self.console.print(f"\n[bold cyan]Step {current}/{total}:[/bold cyan] {description}")

    def collapsible_section(self, title: str, content: str, expanded: bool = False):
        """Collapsible section (Cline pattern)"""
        if expanded:
            self.console.print(f"[cyan]{self.SYMBOL_COLLAPSE} {title}[/cyan]")
            self.console.print(f"[dim]{content}[/dim]")
        else:
            self.console.print(f"[dim]{self.SYMBOL_EXPAND} {title}[/dim]")

    def diff_preview(self, filename: str, additions: int, deletions: int):
        """Diff preview (Aider pattern)"""
        self.console.print(f"  [dim]{filename}[/dim] [green]+{additions}[/green] [red]-{deletions}[/red]")

    def file_tree(self, files: list[str]):
        """File tree display (Cursor pattern)"""
        tree = Tree("[bold cyan]Files[/bold cyan]")
        for file in files:
            tree.add(f"[dim]{file}[/dim]")
        self.console.print(tree)

    def code_block(self, code: str, language: str = "python"):
        """Syntax highlighted code block"""
        syntax = Syntax(code, language, theme="monokai", line_numbers=True)
        self.console.print(syntax)

    def table(self, title: str, headers: list[str], rows: list[list[str]]):
        """Table display"""
        table = Table(title=title, show_header=True, header_style="bold cyan")
        for header in headers:
            table.add_column(header)
        for row in rows:
            table.add_row(*row)
        self.console.print(table)

    def panel(self, content: str, title: str = "", border_style: str = "cyan"):
        """Panel with border"""
        self.console.print(Panel(content, title=title, border_style=border_style))

    def error_with_suggestions(self, error: str, suggestions: list[str]):
        """Error with actionable suggestions (Continue pattern)"""
        self.console.print(f"[red]{self.SYMBOL_ERROR}[/red] [bold]{error}[/bold]")
        self.console.print()
        self.console.print("[bold]Suggested fixes:[/bold]")
        for i, suggestion in enumerate(suggestions, 1):
            self.console.print(f"  {i}. {suggestion}")
        self.console.print()

    def status_update(self, message: str, status: str = "working"):
        """Real-time status update"""
        colors = {
            "working": "cyan",
            "success": "green",
            "error": "red",
            "warning": "yellow",
        }
        color = colors.get(status, "cyan")
        self.console.print(f"[{color}]{self.SYMBOL_ARROW}[/{color}] {message}")

    def token_counter(self, tokens: int, max_tokens: int = 200000):
        """Token usage display with progress"""
        percentage = (tokens / max_tokens) * 100
        bar_width = 20
        filled = int((tokens / max_tokens) * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)

        color = "green" if percentage < 50 else "yellow" if percentage < 80 else "red"
        self.console.print(f"[{color}]{bar}[/{color}] {tokens:,}/{max_tokens:,} tokens ({percentage:.1f}%)")

    def cost_tracker(self, cost: float, budget: float = 10.0):
        """Cost tracking display"""
        percentage = (cost / budget) * 100
        color = "green" if percentage < 50 else "yellow" if percentage < 80 else "red"
        self.console.print(f"[{color}]${cost:.4f}[/{color}] / ${budget:.2f} ({percentage:.1f}%)")

    def git_commit(self, message: str, files: int):
        """Git commit display (Aider pattern)"""
        self.console.print(f"[green]{self.SYMBOL_SUCCESS}[/green] Committed: [bold]{message}[/bold]")
        self.console.print(f"  [dim]{files} file{'s' if files != 1 else ''} changed[/dim]")

    def clear_line(self):
        """Clear current line"""
        self.console.print("\r" + " " * self.console.width + "\r", end="")

    def divider(self, char: str = "─"):
        """Horizontal divider"""
        self.console.print(f"[dim]{char * self.console.width}[/dim]")
