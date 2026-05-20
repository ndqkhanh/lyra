"""
Banner System - Adaptive banners with themes and animations.

Features:
- Adaptive width (36-100 cols)
- Multiple styles (minimal, standard, full)
- Theme support
- Status indicators
- Quick stats display
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.text import Text


class BannerStyle(Enum):
    """Banner style."""

    MINIMAL = "minimal"
    STANDARD = "standard"
    FULL = "full"


class BannerTheme(Enum):
    """Banner theme."""

    DEFAULT = "default"
    DARK = "dark"
    LIGHT = "light"
    SOLARIZED = "solarized"
    DRACULA = "dracula"


@dataclass
class BannerStats:
    """Banner statistics."""

    tokens_used: int = 0
    total_cost: float = 0.0
    elapsed_time: float = 0.0
    agents_active: int = 0


class BannerSystem:
    """
    Adaptive banner system.

    Features:
    - Adaptive width (36-100 cols)
    - Multiple styles
    - Theme support
    - Status indicators
    - Quick stats
    """

    def __init__(
        self,
        console: Optional[Console] = None,
        style: BannerStyle = BannerStyle.STANDARD,
        theme: BannerTheme = BannerTheme.DEFAULT,
    ):
        """
        Initialize banner system.

        Args:
            console: Rich console
            style: Banner style
            theme: Banner theme
        """
        self.console = console or Console()
        self.style = style
        self.theme = theme

    def render(
        self,
        title: str = "Lyra",
        subtitle: Optional[str] = None,
        status: Optional[str] = None,
        stats: Optional[BannerStats] = None,
    ) -> Panel:
        """
        Render banner.

        Args:
            title: Banner title
            subtitle: Banner subtitle
            status: Status message
            stats: Banner statistics

        Returns:
            Rich panel
        """
        # Get terminal width
        width = self.console.width
        adaptive_width = max(36, min(100, width))

        # Build banner content based on style
        if self.style == BannerStyle.MINIMAL:
            content = self._render_minimal(title)
        elif self.style == BannerStyle.STANDARD:
            content = self._render_standard(title, subtitle, status)
        else:  # FULL
            content = self._render_full(title, subtitle, status, stats)

        # Get theme colors
        border_color = self._get_theme_border_color()

        return Panel(
            content,
            border_style=border_color,
            width=adaptive_width,
        )

    def _render_minimal(self, title: str) -> Text:
        """Render minimal banner."""
        text = Text()
        text.append(title, style="bold cyan")
        return text

    def _render_standard(
        self,
        title: str,
        subtitle: Optional[str],
        status: Optional[str],
    ) -> Text:
        """Render standard banner."""
        text = Text()

        # Title
        text.append(title, style="bold cyan")

        # Subtitle
        if subtitle:
            text.append("\n")
            text.append(subtitle, style="dim")

        # Status
        if status:
            text.append("\n")
            text.append("● ", style="green")
            text.append(status, style="italic")

        return text

    def _render_full(
        self,
        title: str,
        subtitle: Optional[str],
        status: Optional[str],
        stats: Optional[BannerStats],
    ) -> Text:
        """Render full banner."""
        text = Text()

        # Title
        text.append(title, style="bold cyan")

        # Subtitle
        if subtitle:
            text.append("\n")
            text.append(subtitle, style="dim")

        # Status
        if status:
            text.append("\n")
            text.append("● ", style="green")
            text.append(status, style="italic")

        # Stats
        if stats:
            text.append("\n\n")
            text.append("Stats: ", style="bold")

            # Tokens
            text.append(f"Tokens: {stats.tokens_used:,}", style="cyan")
            text.append(" | ")

            # Cost
            text.append(f"Cost: ${stats.total_cost:.4f}", style="yellow")
            text.append(" | ")

            # Time
            text.append(f"Time: {stats.elapsed_time:.1f}s", style="magenta")
            text.append(" | ")

            # Agents
            text.append(f"Agents: {stats.agents_active}", style="green")

        return text

    def _get_theme_border_color(self) -> str:
        """Get border color for theme."""
        colors = {
            BannerTheme.DEFAULT: "cyan",
            BannerTheme.DARK: "dim white",
            BannerTheme.LIGHT: "bright_white",
            BannerTheme.SOLARIZED: "yellow",
            BannerTheme.DRACULA: "magenta",
        }
        return colors.get(self.theme, "cyan")

    def set_style(self, style: BannerStyle):
        """
        Set banner style.

        Args:
            style: Banner style
        """
        self.style = style

    def set_theme(self, theme: BannerTheme):
        """
        Set banner theme.

        Args:
            theme: Banner theme
        """
        self.theme = theme

    def display(
        self,
        title: str = "Lyra",
        subtitle: Optional[str] = None,
        status: Optional[str] = None,
        stats: Optional[BannerStats] = None,
    ):
        """
        Display banner.

        Args:
            title: Banner title
            subtitle: Banner subtitle
            status: Status message
            stats: Banner statistics
        """
        panel = self.render(title, subtitle, status, stats)
        self.console.print(panel)


class StartupBanner:
    """
    Startup banner with animation.

    Features:
    - Animated startup sequence
    - Version display
    - Loading indicators
    """

    def __init__(self, console: Optional[Console] = None):
        """
        Initialize startup banner.

        Args:
            console: Rich console
        """
        self.console = console or Console()

    def display(
        self,
        version: str = "0.1.0",
        loading_message: str = "Initializing...",
    ):
        """
        Display startup banner.

        Args:
            version: Version string
            loading_message: Loading message
        """
        text = Text()

        # Logo
        text.append("╔═══════════════════════════╗\n", style="cyan")
        text.append("║                           ║\n", style="cyan")
        text.append("║    ", style="cyan")
        text.append("L Y R A", style="bold cyan")
        text.append("              ║\n", style="cyan")
        text.append("║                           ║\n", style="cyan")
        text.append("╚═══════════════════════════╝\n", style="cyan")

        # Version
        text.append(f"\nVersion {version}", style="dim")

        # Loading
        text.append("\n\n")
        text.append("● ", style="yellow")
        text.append(loading_message, style="italic")

        self.console.print(text)


class ShutdownBanner:
    """
    Shutdown banner.

    Features:
    - Graceful shutdown message
    - Session summary
    """

    def __init__(self, console: Optional[Console] = None):
        """
        Initialize shutdown banner.

        Args:
            console: Rich console
        """
        self.console = console or Console()

    def display(
        self,
        tasks_completed: int = 0,
        total_time: float = 0.0,
    ):
        """
        Display shutdown banner.

        Args:
            tasks_completed: Number of tasks completed
            total_time: Total session time
        """
        text = Text()

        # Message
        text.append("Shutting down...\n\n", style="yellow")

        # Summary
        text.append("Session Summary:\n", style="bold")
        text.append(f"  Tasks completed: {tasks_completed}\n", style="green")
        text.append(f"  Total time: {total_time:.1f}s\n", style="cyan")

        # Goodbye
        text.append("\nGoodbye! 👋", style="dim")

        self.console.print(text)
