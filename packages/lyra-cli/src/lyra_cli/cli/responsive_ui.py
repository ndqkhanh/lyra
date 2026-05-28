"""Responsive terminal UI that adapts to resize events"""

import os
import shutil
import signal
from collections.abc import Callable

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text


class ResponsiveUI:
    """Responsive UI that handles terminal resize events"""

    def __init__(self, console: Console):
        self.console = console
        self.width = console.width
        self.height = console.height
        self.resize_callbacks = []
        self._setup_resize_handler()

    def _setup_resize_handler(self):
        """Setup signal handler for terminal resize (SIGWINCH)"""
        def handle_resize(signum, frame):
            # Update terminal size
            old_width = self.width
            old_height = self.height

            # Get new size
            size = shutil.get_terminal_size()
            self.width = size.columns
            self.height = size.lines

            # Update console
            self.console._width = self.width
            self.console._height = self.height

            # Call all registered callbacks
            for callback in self.resize_callbacks:
                callback(old_width, old_height, self.width, self.height)

        # Register signal handler (Unix/Linux/Mac)
        try:
            signal.signal(signal.SIGWINCH, handle_resize)
        except AttributeError:
            # Windows doesn't have SIGWINCH
            pass

    def on_resize(self, callback: Callable):
        """Register a callback for resize events"""
        self.resize_callbacks.append(callback)

    def get_size(self):
        """Get current terminal size"""
        return self.width, self.height

    def responsive_banner(self, model: str = "Opus 4.7", user: str = None):
        """Responsive banner that adapts to terminal width"""

        if user is None:
            user = os.getenv("USER") or "user"

        width = self.console.width

        # Adaptive layout based on width
        if width < 80:
            # Narrow: Single column, compact
            return self._banner_narrow(model, user)
        elif width < 120:
            # Medium: Single column, full
            return self._banner_medium(model, user)
        else:
            # Wide: Two columns
            return self._banner_wide(model, user)

    def _banner_narrow(self, model: str, user: str):
        """Narrow banner for small terminals (<80 cols)"""
        banner = Text()
        banner.append(f"Lyra · {model}\n", style="bold cyan")
        banner.append(f"{user}\n", style="dim")

        cwd = self._get_short_path()
        banner.append(f"{cwd}\n", style="dim blue")

        panel = Panel(
            banner,
            border_style="cyan",
            padding=(0, 1),
        )

        self.console.print()
        self.console.print(panel)
        self.console.print()

    def _banner_medium(self, model: str, user: str):
        """Medium banner for medium terminals (80-120 cols)"""
        banner = Text()
        banner.append(f"Welcome back {user}!\n\n", style="bold")
        banner.append("    ╦  ╦ ╦ ╦═╗ ╔═╗\n", style="cyan")
        banner.append("    ║  ╚╦╝ ╠╦╝ ╠═╣\n", style="cyan")
        banner.append("    ╩═╝ ╩  ╩╚═ ╩ ╩\n\n", style="cyan")
        banner.append(f"{model}\n", style="bold magenta")

        cwd = self._get_short_path()
        banner.append(f"{cwd}\n", style="dim blue")

        panel = Panel(
            banner,
            title="[bold cyan]Lyra v0.1.0[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
        )

        self.console.print()
        self.console.print(panel)
        self.console.print()

    def _banner_wide(self, model: str, user: str):
        """Wide banner for large terminals (>120 cols)"""
        from rich.columns import Columns

        # Left column
        left = Text()
        left.append(f"Welcome back {user}!\n\n", style="bold")
        left.append("    ╦  ╦ ╦ ╦═╗ ╔═╗\n", style="cyan")
        left.append("    ║  ╚╦╝ ╠╦╝ ╠═╣\n", style="cyan")
        left.append("    ╩═╝ ╩  ╩╚═ ╩ ╩\n\n", style="cyan")
        left.append(f"{model}\n", style="bold magenta")

        cwd = self._get_short_path()
        left.append(f"{cwd}\n", style="dim blue")

        # Right column
        right = Text()
        right.append("Tips\n", style="bold")
        right.append("Run /help for commands\n", style="dim")
        right.append("─" * 20 + "\n", style="dim")
        right.append("What's new\n", style="bold")
        right.append("Beautiful responsive UI\n", style="dim")
        right.append("/release-notes for more\n", style="dim")

        columns = Columns([left, right], equal=False, expand=True)

        panel = Panel(
            columns,
            title="[bold cyan]Lyra v0.1.0[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
        )

        self.console.print()
        self.console.print(panel)
        self.console.print()

    def _get_short_path(self):
        """Get shortened path that fits terminal width"""
        cwd = os.getcwd()
        home = os.path.expanduser("~")
        if cwd.startswith(home):
            cwd = "~" + cwd[len(home):]

        max_len = self.width - 10
        if len(cwd) > max_len:
            parts = cwd.split("/")
            if len(parts) > 3:
                cwd = "/".join(parts[:2]) + "/…/" + "/".join(parts[-1:])

        return cwd

    def responsive_text(self, text: str, max_width: int | None = None):
        """Wrap text to fit terminal width"""
        if max_width is None:
            max_width = self.width - 4  # Leave margin

        from textwrap import wrap
        lines = []
        for line in text.split("\n"):
            if len(line) <= max_width:
                lines.append(line)
            else:
                wrapped = wrap(line, width=max_width, break_long_words=False)
                lines.extend(wrapped)

        return "\n".join(lines)

    def responsive_table(self, headers: list, rows: list):
        """Create table that adapts to terminal width"""
        from rich.table import Table

        width = self.width

        # Adjust table based on width
        if width < 80:
            # Narrow: Show fewer columns
            table = Table(show_header=True, header_style="bold cyan", box=None)
        else:
            # Wide: Show all columns with borders
            table = Table(show_header=True, header_style="bold cyan")

        # Add columns
        for header in headers:
            table.add_column(header)

        # Add rows
        for row in rows:
            table.add_row(*row)

        self.console.print(table)

    def responsive_menu(self, title: str, options: list, selected: int = 0):
        """Menu that adapts to terminal width"""
        width = self.width

        # Divider
        self.console.print("─" * width, style="dim")

        # Title
        self.console.print(f"  [bold]{title}[/bold]")

        if width < 80:
            # Narrow: Compact format
            for i, (label, desc) in enumerate(options):
                arrow = "❯" if i == selected else " "
                self.console.print(f"  {arrow} {i+1}. {label}")
        else:
            # Wide: Full format with descriptions
            for i, (label, desc) in enumerate(options):
                arrow = "❯" if i == selected else " "
                self.console.print(f"  {arrow} {i+1}. {label}  [dim]{desc}[/dim]")

        self.console.print()
        self.console.print("  [dim]Enter to confirm · Esc to cancel[/dim]")

    def responsive_divider(self, char: str = "─"):
        """Full-width divider that adapts to terminal width"""
        self.console.print(char * self.width, style="dim")

    def live_resize_demo(self):
        """Demo that shows live resize handling"""
        from rich.panel import Panel

        def make_panel():
            width, height = self.get_size()
            content = Text()
            content.append("Terminal Size\n\n", style="bold cyan")
            content.append(f"Width: {width} columns\n", style="green")
            content.append(f"Height: {height} lines\n", style="green")
            content.append("\nResize your terminal to see this update!\n", style="dim")

            return Panel(
                content,
                title="[bold cyan]Responsive UI Demo[/bold cyan]",
                border_style="cyan",
            )

        # Register resize callback
        def on_resize(old_w, old_h, new_w, new_h):
            # Live will auto-refresh
            pass

        self.on_resize(on_resize)

        # Live display
        with Live(make_panel(), console=self.console, refresh_per_second=4) as live:
            import time
            try:
                while True:
                    live.update(make_panel())
                    time.sleep(0.25)
            except KeyboardInterrupt:
                pass


class ResponsiveChatUI:
    """Responsive chat interface"""

    def __init__(self, console: Console):
        self.console = console
        self.responsive = ResponsiveUI(console)

    def show_message(self, role: str, content: str):
        """Show message with responsive wrapping"""
        width = self.responsive.width

        # Wrap content
        wrapped = self.responsive.responsive_text(content, max_width=width - 10)

        # Role indicator
        if role == "user":
            self.console.print(f"\n[bold green]❯[/bold green] {wrapped}")
        else:
            self.console.print(f"\n{wrapped}")

    def show_thinking(self, message: str):
        """Show thinking indicator"""
        self.console.print(f"\n[yellow]✶[/yellow] {message} [dim](thinking...)[/dim]")

    def show_tool_use(self, tool: str, args: str = ""):
        """Show tool use"""
        width = self.responsive.width

        if width < 80:
            # Compact
            self.console.print(f"  [dim]⎿ {tool}[/dim]")
        else:
            # Full
            if args:
                wrapped = self.responsive.responsive_text(args, max_width=width - 20)
                self.console.print(f"  [cyan]⎿[/cyan] [dim]{tool}: {wrapped}[/dim]")
            else:
                self.console.print(f"  [cyan]⎿[/cyan] [dim]{tool}[/dim]")

    def show_stats(self, duration: str, tools: int, tokens: int):
        """Show stats line"""
        self.console.print(f"\n[dim]✻ {duration} · {tools} tools · {tokens:,} tokens[/dim]")
