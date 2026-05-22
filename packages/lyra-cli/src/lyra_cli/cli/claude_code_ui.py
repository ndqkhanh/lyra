"""Claude Code-style UI components"""

from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich.align import Align
from typing import List, Tuple
import os


class ClaudeCodeUI:
    """UI components matching real Claude Code interface"""

    # Status symbols (from real Claude Code)
    ACTIVE = "⏺"      # Filled circle
    INACTIVE = "◯"    # Empty circle
    FORWARD = "⏵"     # Forward arrow
    MODE = "⏵⏵"       # Double forward (mode indicator)
    THINKING = "✶"    # Star (roosting/thinking)
    STATS = "✻"       # Asterisk (stats)
    TOOL = "⎿"        # Tool indicator
    SELECT = "❯"      # Selection arrow
    CHECK = "✔"       # Checkmark
    BULLET = "●"      # Bullet point

    # Box drawing characters
    BOX_TL = "╭"      # Top-left
    BOX_TR = "╮"      # Top-right
    BOX_BL = "╰"      # Bottom-left
    BOX_BR = "╯"      # Bottom-right
    BOX_H = "─"       # Horizontal
    BOX_V = "│"       # Vertical
    BOX_VR = "├"      # Vertical-right (tree)
    BOX_UR = "└"      # Up-right (tree end)

    def __init__(self, console: Console):
        self.console = console

    def welcome_banner(self, model: str = "Opus 4.7", user: str = None, org: str = "Claude Max"):
        """Two-column welcome banner (exact Claude Code style)"""

        if user is None:
            user = os.getenv("USER") or "user"

        # Get path
        cwd = os.getcwd()
        home = os.path.expanduser("~")
        if cwd.startswith(home):
            cwd = "~" + cwd[len(home):]
        # Truncate long paths
        if len(cwd) > 50:
            parts = cwd.split("/")
            cwd = "/".join(parts[:2]) + "/…/" + "/".join(parts[-2:])

        # Left column (main)
        left = Text()
        left.append("\n")
        left.append(f"Welcome back {user}!\n\n", style="bold")
        left.append("    ╦  ╦ ╦ ╦═╗ ╔═╗\n", style="cyan")
        left.append("    ║  ╚╦╝ ╠╦╝ ╠═╣\n", style="cyan")
        left.append("    ╩═╝ ╩  ╩╚═ ╩ ╩\n\n", style="cyan")
        left.append(f"{model} · {org}\n", style="bold")
        left.append(f"  {cwd}\n", style="dim")

        # Right column (tips)
        right = Text()
        right.append("Tips for getting\n", style="bold")
        right.append("started\n", style="bold")
        right.append("Run /help to see all\n", style="dim")
        right.append("commands\n", style="dim")
        right.append(self.BOX_H * 20 + "\n", style="dim")
        right.append("What's new\n", style="bold")
        right.append("Added beautiful UI\n", style="dim")
        right.append("Claude Code patterns\n", style="dim")
        right.append("/release-notes for more\n", style="dim")

        # Combine columns
        columns = Columns([left, right], equal=False, expand=True)

        # Create panel
        panel = Panel(
            columns,
            title="[bold cyan]Lyra v0.1.0[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
        )

        self.console.print()
        self.console.print(panel)
        self.console.print()

    def agent_tree(self, agents: List[Tuple[str, str, int, int]]):
        """Tree structure for running agents (Claude Code style)"""

        self.console.print(f"[cyan]{self.ACTIVE}[/cyan] Running {len(agents)} agents… [dim](ctrl+o to expand)[/dim]")

        for i, (name, task, tools, tokens) in enumerate(agents):
            is_last = i == len(agents) - 1
            branch = self.BOX_UR if is_last else self.BOX_VR

            self.console.print(f"   {branch} {name} · {tools} tool uses · {tokens/1000:.1f}k tokens")
            self.console.print(f"   {'  ' if is_last else self.BOX_V} {self.TOOL}  {task}")

    def interactive_menu(self, title: str, options: List[Tuple[str, str, str]], selected: int = 0, current: int = None):
        """Interactive menu with selection (Claude Code style)"""

        # Divider
        self.console.print(self.BOX_H * self.console.width, style="dim")

        # Title and description
        self.console.print(f"  [bold]{title}[/bold]")
        self.console.print(f"  [dim]Select an option below[/dim]\n")

        # Options
        for i, (label, name, desc) in enumerate(options):
            is_selected = i == selected
            is_current = i == current

            # Selection arrow
            arrow = self.SELECT if is_selected else " "

            # Checkmark for current
            check = f" {self.CHECK}" if is_current else ""

            # Format
            self.console.print(f"  {arrow} {i+1}. {label}{check}  [dim]{name} · {desc}[/dim]")

        # Footer
        self.console.print()
        self.console.print("  [dim]Enter to confirm · Esc to cancel[/dim]")

    def status_bar(self, mode: str = "default", shortcuts: str = ""):
        """Status bar at bottom (Claude Code style)"""

        # Divider
        self.console.print(self.BOX_H * self.console.width, style="dim")

        # Prompt
        self.console.print(f"[bold green]{self.SELECT}[/bold green]")

        # Divider
        self.console.print(self.BOX_H * self.console.width, style="dim")

        # Mode and shortcuts
        status = f"  {self.MODE} {mode}"
        if shortcuts:
            status += f" [dim]· {shortcuts}[/dim]"

        self.console.print(status)

    def background_tasks(self, tasks: List[Tuple[str, str]]):
        """Background tasks panel (Claude Code style)"""

        self.console.print(self.BOX_H * self.console.width, style="dim")
        self.console.print("  [bold]Background tasks[/bold]")
        self.console.print(f"  [dim]{len(tasks)} active shells[/dim]\n")

        for i, (command, status) in enumerate(tasks):
            is_selected = i == 0
            arrow = self.SELECT if is_selected else " "

            # Truncate long commands
            if len(command) > 60:
                command = command[:57] + "..."

            self.console.print(f"  {arrow} {command} [dim]({status})[/dim]")

        self.console.print()
        self.console.print("  [dim]↑/↓ to select · Enter to view · x to stop · ←/Esc to close[/dim]")

    def collapsible_section(self, title: str, items: List[str], expanded: bool = False):
        """Collapsible section (Claude Code style)"""

        self.console.print(f"\n[dim]{self.STATS} {title} [dim](ctrl+o for history)[/dim][/dim]")

        if expanded:
            for item in items:
                self.console.print(f"  {self.TOOL}  [dim]{item}[/dim]")

    def thinking_indicator(self, message: str, duration: str, tokens: int):
        """Thinking/roosting indicator (Claude Code style)"""

        self.console.print(f"[yellow]{self.THINKING}[/yellow] {message} [dim]({duration} · ↓ {tokens/1000:.1f}k tokens · almost done thinking)[/dim]")
        self.console.print(f"  {self.TOOL}  [dim]Tip: Use /btw to ask a quick side question[/dim]")

    def agent_list(self, agents: List[Tuple[str, str, str, int]]):
        """Agent list with status (Claude Code style)"""

        for i, (status, agent_type, task, time) in enumerate(agents):
            symbol = self.ACTIVE if status == "active" else self.INACTIVE
            is_selected = i == 0

            if is_selected:
                self.console.print(f"  {self.ACTIVE} [bold]main[/bold]  [dim]↑/↓ to select · Enter to view[/dim]")
            else:
                # Truncate long tasks
                if len(task) > 50:
                    task = task[:47] + "..."

                self.console.print(f"  {symbol} {agent_type}  {task}  [dim]{time}s[/dim]")

    def divider(self):
        """Full-width divider (Claude Code style)"""
        self.console.print(self.BOX_H * self.console.width, style="dim")

    def tool_use_compact(self, tool: str, args: str = ""):
        """Compact tool use indicator (Claude Code style)"""
        if args:
            self.console.print(f"  {self.TOOL}  [dim]{tool}: {args}[/dim]")
        else:
            self.console.print(f"  {self.TOOL}  [dim]{tool}[/dim]")
