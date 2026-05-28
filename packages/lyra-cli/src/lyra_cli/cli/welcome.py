"""Enhanced welcome screen with Claude Code-inspired design"""

import os

from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.text import Text


def show_welcome(console: Console, model: str = "Auto", user: str = None):
    """Show welcome screen (Claude Code-inspired minimal design)"""

    # Get user info
    if user is None:
        user = os.getenv("USER") or os.getenv("USERNAME") or "user"

    # Get current directory (shortened)
    cwd = os.getcwd()
    home = os.path.expanduser("~")
    if cwd.startswith(home):
        cwd = "~" + cwd[len(home):]

    # Create welcome content with minimal design
    welcome_text = Text()

    # Simple header
    welcome_text.append("Lyra\n", style="bold cyan")
    welcome_text.append(f"{model}\n\n", style="dim")

    # Current directory
    welcome_text.append(f"{cwd}\n", style="dim")

    # Create panel with minimal border
    panel = Panel(
        Align.center(welcome_text),
        border_style="dim",
        padding=(1, 2),
    )

    console.print(panel)

    # Tips below (Claude Code style)
    console.print("[dim]Type your message to start, /help for commands, Ctrl+D to exit[/dim]\n")


def show_welcome_detailed(console: Console, model: str = "Auto", organization: str = "Claude Max"):
    """Show detailed welcome screen (original Lyra style)"""

    user = os.getenv("USER") or os.getenv("USERNAME") or "user"
    cwd = os.getcwd()
    home = os.path.expanduser("~")
    if cwd.startswith(home):
        cwd = "~" + cwd[len(home):]

    # Create welcome content
    welcome_text = Text()
    welcome_text.append("\n\n\n", style="")
    welcome_text.append(f"Welcome back {user}!\n\n\n", style="cyan")

    # Lyra logo (ASCII art)
    welcome_text.append("            ▐▛███▜▌\n", style="cyan")
    welcome_text.append("           ▝▜█████▛▘\n", style="cyan")
    welcome_text.append("             ▘▘ ▝▝\n\n", style="cyan")

    # Model and org info
    welcome_text.append(f"{model} · {organization}\n", style="bold")
    welcome_text.append(f"  {cwd}\n\n\n", style="dim")

    # Create panel
    panel = Panel(
        Align.center(welcome_text),
        title="[bold cyan]Lyra v0.1.0[/bold cyan]",
        border_style="cyan",
        padding=(0, 2),
    )

    console.print(panel)

    # Tips
    console.print("\n[bold cyan]Tips:[/bold cyan]")
    console.print("  • Type your message to start chatting")
    console.print("  • Use /help for available commands")
    console.print("  • Press Ctrl+C to interrupt, Ctrl+D to exit")
    console.print()


def show_welcome_claude_code_style(console: Console, model: str = "Auto"):
    """Show welcome screen with beautiful banner"""
    from lyra_cli.cli.banner import show_banner_gradient
    show_banner_gradient(console, model)
