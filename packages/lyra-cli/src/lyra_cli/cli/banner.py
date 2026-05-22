"""Beautiful responsive banner for Lyra CLI"""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
import os


def show_banner(console: Console, model: str = "Auto", show_full: bool = True):
    """Show beautiful responsive banner (inspired by top AI agents)"""

    if show_full:
        # Full banner with ASCII art
        banner = Text()

        # Lyra ASCII art logo
        banner.append("    ╦  ╦ ╦ ╦═╗ ╔═╗\n", style="bold cyan")
        banner.append("    ║  ╚╦╝ ╠╦╝ ╠═╣\n", style="bold cyan")
        banner.append("    ╩═╝ ╩  ╩╚═ ╩ ╩\n", style="bold cyan")
        banner.append("\n")
        banner.append("    AI Coding Assistant\n", style="dim")
        banner.append(f"    {model}\n", style="bold magenta")

        # Create panel
        panel = Panel(
            Align.center(banner),
            border_style="cyan",
            padding=(1, 2),
        )

        console.print()
        console.print(panel)
        console.print()
    else:
        # Minimal banner
        console.print()
        console.print(f"[bold cyan]Lyra[/bold cyan] [dim]·[/dim] [bold magenta]{model}[/bold magenta]")

        # Show path
        cwd = os.getcwd()
        home = os.path.expanduser("~")
        if cwd.startswith(home):
            cwd = "~" + cwd[len(home):]
        console.print(f"[dim blue]{cwd}[/dim blue]")
        console.print()


def show_banner_with_stats(console: Console, model: str = "Auto", tokens: int = 0, cost: float = 0.0):
    """Show banner with stats (Continue pattern)"""

    banner = Text()

    # Logo
    banner.append("╦  ╦ ╦ ╦═╗ ╔═╗\n", style="bold cyan")
    banner.append("║  ╚╦╝ ╠╦╝ ╠═╣\n", style="bold cyan")
    banner.append("╩═╝ ╩  ╩╚═ ╩ ╩\n", style="bold cyan")
    banner.append("\n")

    # Model
    banner.append(f"{model}\n", style="bold magenta")

    # Stats
    if tokens > 0:
        banner.append(f"{tokens:,} tokens", style="dim")
        if cost > 0:
            banner.append(f" · ${cost:.4f}", style="dim")
        banner.append("\n", style="dim")

    # Path
    cwd = os.getcwd()
    home = os.path.expanduser("~")
    if cwd.startswith(home):
        cwd = "~" + cwd[len(home):]
    banner.append(f"\n{cwd}", style="dim blue")

    panel = Panel(
        Align.center(banner),
        border_style="cyan",
        padding=(1, 2),
    )

    console.print()
    console.print(panel)
    console.print()


def show_banner_gradient(console: Console, model: str = "Auto"):
    """Show banner with gradient effect (Aider-inspired)"""

    console.print()

    # Gradient ASCII art
    lines = [
        ("    ╦  ╦ ╦ ╦═╗ ╔═╗", "cyan"),
        ("    ║  ╚╦╝ ╠╦╝ ╠═╣", "bright_cyan"),
        ("    ╩═╝ ╩  ╩╚═ ╩ ╩", "blue"),
    ]

    for line, color in lines:
        console.print(f"[bold {color}]{line}[/bold {color}]")

    console.print()
    console.print(f"    [dim]AI Coding Assistant ·[/dim] [bold magenta]{model}[/bold magenta]")

    # Path
    cwd = os.getcwd()
    home = os.path.expanduser("~")
    if cwd.startswith(home):
        cwd = "~" + cwd[len(home):]
    console.print(f"    [dim blue]{cwd}[/dim blue]")
    console.print()


def show_banner_compact(console: Console, model: str = "Auto"):
    """Show compact banner (Claude Code style)"""

    console.print()
    console.print("[bold cyan]╦  ╦ ╦ ╦═╗ ╔═╗[/bold cyan]  [bold magenta]" + model + "[/bold magenta]")
    console.print("[bold cyan]║  ╚╦╝ ╠╦╝ ╠═╣[/bold cyan]  [dim]AI Coding Assistant[/dim]")
    console.print("[bold cyan]╩═╝ ╩  ╩╚═ ╩ ╩[/bold cyan]")

    # Path
    cwd = os.getcwd()
    home = os.path.expanduser("~")
    if cwd.startswith(home):
        cwd = "~" + cwd[len(home):]
    console.print(f"\n[dim blue]{cwd}[/dim blue]")
    console.print()


def show_banner_animated(console: Console, model: str = "Auto"):
    """Show banner with animation effect"""
    import time

    console.print()

    # Animate each line
    lines = [
        "[bold cyan]    ╦  ╦ ╦ ╦═╗ ╔═╗[/bold cyan]",
        "[bold cyan]    ║  ╚╦╝ ╠╦╝ ╠═╣[/bold cyan]",
        "[bold cyan]    ╩═╝ ╩  ╩╚═ ╩ ╩[/bold cyan]",
        "",
        f"    [dim]AI Coding Assistant ·[/dim] [bold magenta]{model}[/bold magenta]",
    ]

    for line in lines:
        console.print(line)
        time.sleep(0.05)

    # Path
    cwd = os.getcwd()
    home = os.path.expanduser("~")
    if cwd.startswith(home):
        cwd = "~" + cwd[len(home):]
    console.print(f"    [dim blue]{cwd}[/dim blue]")
    console.print()


def show_banner_boxed(console: Console, model: str = "Auto"):
    """Show banner in a beautiful box (OpenClaw style)"""

    banner = Text()

    # Logo with spacing
    banner.append("\n")
    banner.append("╦  ╦ ╦ ╦═╗ ╔═╗\n", style="bold cyan")
    banner.append("║  ╚╦╝ ╠╦╝ ╠═╣\n", style="bold cyan")
    banner.append("╩═╝ ╩  ╩╚═ ╩ ╩\n", style="bold cyan")
    banner.append("\n")
    banner.append("AI Coding Assistant\n", style="dim")
    banner.append(f"{model}\n", style="bold magenta")
    banner.append("\n")

    # Path
    cwd = os.getcwd()
    home = os.path.expanduser("~")
    if cwd.startswith(home):
        cwd = "~" + cwd[len(home):]
    banner.append(f"{cwd}\n", style="dim blue")

    panel = Panel(
        Align.center(banner),
        title="[bold cyan]Lyra v0.1.0[/bold cyan]",
        subtitle="[dim]Press Ctrl+D to exit[/dim]",
        border_style="cyan",
        padding=(0, 2),
    )

    console.print()
    console.print(panel)
    console.print()
