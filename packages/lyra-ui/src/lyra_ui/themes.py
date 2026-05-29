"""
Theme System - Customizable color themes and styling.

Features:
- Multiple built-in themes
- Custom theme creation
- Theme preview
- Theme import/export
- Per-component styling
"""

from dataclasses import dataclass
from enum import Enum

from rich.console import Console
from rich.table import Table
from rich.theme import Theme as RichTheme


class ThemeName(Enum):
    """Theme name."""

    DEFAULT = "default"
    DARK = "dark"
    LIGHT = "light"
    SOLARIZED_DARK = "solarized_dark"
    SOLARIZED_LIGHT = "solarized_light"
    DRACULA = "dracula"
    MONOKAI = "monokai"
    NORD = "nord"
    GRUVBOX = "gruvbox"


@dataclass
class ThemeColors:
    """Theme colors."""

    primary: str
    secondary: str
    success: str
    warning: str
    error: str
    info: str
    background: str
    foreground: str
    dim: str
    bright: str


class ThemeManager:
    """
    Theme manager.

    Features:
    - Built-in themes
    - Custom themes
    - Theme switching
    - Theme preview
    """

    def __init__(self, console: Console | None = None):
        """
        Initialize theme manager.

        Args:
            console: Rich console
        """
        self.console = console or Console()
        self.current_theme = ThemeName.DEFAULT
        self.themes = self._load_builtin_themes()
        self.custom_themes: dict[str, ThemeColors] = {}

    def _load_builtin_themes(self) -> dict[ThemeName, ThemeColors]:
        """Load built-in themes."""
        return {
            ThemeName.DEFAULT: ThemeColors(
                primary="cyan",
                secondary="blue",
                success="green",
                warning="yellow",
                error="red",
                info="cyan",
                background="black",
                foreground="white",
                dim="dim white",
                bright="bright_white",
            ),
            ThemeName.DARK: ThemeColors(
                primary="bright_cyan",
                secondary="bright_blue",
                success="bright_green",
                warning="bright_yellow",
                error="bright_red",
                info="bright_cyan",
                background="black",
                foreground="bright_white",
                dim="dim white",
                bright="bright_white",
            ),
            ThemeName.LIGHT: ThemeColors(
                primary="blue",
                secondary="cyan",
                success="green",
                warning="yellow",
                error="red",
                info="blue",
                background="white",
                foreground="black",
                dim="dim black",
                bright="bright_black",
            ),
            ThemeName.SOLARIZED_DARK: ThemeColors(
                primary="cyan",
                secondary="blue",
                success="green",
                warning="yellow",
                error="red",
                info="cyan",
                background="#002b36",
                foreground="#839496",
                dim="#586e75",
                bright="#93a1a1",
            ),
            ThemeName.SOLARIZED_LIGHT: ThemeColors(
                primary="cyan",
                secondary="blue",
                success="green",
                warning="yellow",
                error="red",
                info="cyan",
                background="#fdf6e3",
                foreground="#657b83",
                dim="#93a1a1",
                bright="#586e75",
            ),
            ThemeName.DRACULA: ThemeColors(
                primary="#bd93f9",
                secondary="#8be9fd",
                success="#50fa7b",
                warning="#f1fa8c",
                error="#ff5555",
                info="#8be9fd",
                background="#282a36",
                foreground="#f8f8f2",
                dim="#6272a4",
                bright="#ffffff",
            ),
            ThemeName.MONOKAI: ThemeColors(
                primary="#66d9ef",
                secondary="#a6e22e",
                success="#a6e22e",
                warning="#e6db74",
                error="#f92672",
                info="#66d9ef",
                background="#272822",
                foreground="#f8f8f2",
                dim="#75715e",
                bright="#f8f8f2",
            ),
            ThemeName.NORD: ThemeColors(
                primary="#88c0d0",
                secondary="#81a1c1",
                success="#a3be8c",
                warning="#ebcb8b",
                error="#bf616a",
                info="#88c0d0",
                background="#2e3440",
                foreground="#d8dee9",
                dim="#4c566a",
                bright="#eceff4",
            ),
            ThemeName.GRUVBOX: ThemeColors(
                primary="#83a598",
                secondary="#8ec07c",
                success="#b8bb26",
                warning="#fabd2f",
                error="#fb4934",
                info="#83a598",
                background="#282828",
                foreground="#ebdbb2",
                dim="#928374",
                bright="#fbf1c7",
            ),
        }

    def get_theme(self, name: ThemeName) -> ThemeColors:
        """
        Get theme by name.

        Args:
            name: Theme name

        Returns:
            Theme colors
        """
        return self.themes.get(name, self.themes[ThemeName.DEFAULT])

    def set_theme(self, name: ThemeName):
        """
        Set current theme.

        Args:
            name: Theme name
        """
        self.current_theme = name

    def get_current_theme(self) -> ThemeColors:
        """
        Get current theme.

        Returns:
            Current theme colors
        """
        return self.get_theme(self.current_theme)

    def create_custom_theme(self, name: str, colors: ThemeColors):
        """
        Create custom theme.

        Args:
            name: Theme name
            colors: Theme colors
        """
        self.custom_themes[name] = colors

    def get_custom_theme(self, name: str) -> ThemeColors | None:
        """
        Get custom theme.

        Args:
            name: Theme name

        Returns:
            Theme colors or None
        """
        return self.custom_themes.get(name)

    def list_themes(self) -> list[str]:
        """
        List all themes.

        Returns:
            List of theme names
        """
        builtin = [theme.value for theme in ThemeName]
        custom = list(self.custom_themes.keys())
        return builtin + custom

    def preview_theme(self, name: ThemeName):
        """
        Preview theme.

        Args:
            name: Theme name
        """
        theme = self.get_theme(name)

        table = Table(title=f"Theme Preview: {name.value}")
        table.add_column("Color", style="bold")
        table.add_column("Value")
        table.add_column("Preview")

        # Add rows
        table.add_row("Primary", theme.primary, f"[{theme.primary}]Sample[/{theme.primary}]")
        table.add_row("Secondary", theme.secondary, f"[{theme.secondary}]Sample[/{theme.secondary}]")
        table.add_row("Success", theme.success, f"[{theme.success}]Sample[/{theme.success}]")
        table.add_row("Warning", theme.warning, f"[{theme.warning}]Sample[/{theme.warning}]")
        table.add_row("Error", theme.error, f"[{theme.error}]Sample[/{theme.error}]")
        table.add_row("Info", theme.info, f"[{theme.info}]Sample[/{theme.info}]")
        table.add_row("Dim", theme.dim, f"[{theme.dim}]Sample[/{theme.dim}]")
        table.add_row("Bright", theme.bright, f"[{theme.bright}]Sample[/{theme.bright}]")

        self.console.print(table)

    def export_theme(self, name: ThemeName) -> dict[str, str]:
        """
        Export theme to dictionary.

        Args:
            name: Theme name

        Returns:
            Theme dictionary
        """
        theme = self.get_theme(name)
        return {
            "primary": theme.primary,
            "secondary": theme.secondary,
            "success": theme.success,
            "warning": theme.warning,
            "error": theme.error,
            "info": theme.info,
            "background": theme.background,
            "foreground": theme.foreground,
            "dim": theme.dim,
            "bright": theme.bright,
        }

    def import_theme(self, name: str, theme_dict: dict[str, str]):
        """
        Import theme from dictionary.

        Args:
            name: Theme name
            theme_dict: Theme dictionary
        """
        colors = ThemeColors(
            primary=theme_dict.get("primary", "cyan"),
            secondary=theme_dict.get("secondary", "blue"),
            success=theme_dict.get("success", "green"),
            warning=theme_dict.get("warning", "yellow"),
            error=theme_dict.get("error", "red"),
            info=theme_dict.get("info", "cyan"),
            background=theme_dict.get("background", "black"),
            foreground=theme_dict.get("foreground", "white"),
            dim=theme_dict.get("dim", "dim white"),
            bright=theme_dict.get("bright", "bright_white"),
        )
        self.create_custom_theme(name, colors)

    def to_rich_theme(self, name: ThemeName) -> RichTheme:
        """
        Convert to Rich theme.

        Args:
            name: Theme name

        Returns:
            Rich theme
        """
        theme = self.get_theme(name)
        return RichTheme({
            "primary": theme.primary,
            "secondary": theme.secondary,
            "success": theme.success,
            "warning": theme.warning,
            "error": theme.error,
            "info": theme.info,
            "dim": theme.dim,
            "bright": theme.bright,
        })


class AnimationEffects:
    """
    Animation effects.

    Features:
    - Fade in/out
    - Pulse
    - Typing indicator
    - Loading animations
    """

    def __init__(self, console: Console | None = None):
        """
        Initialize animation effects.

        Args:
            console: Rich console
        """
        self.console = console or Console()

    def typing_indicator(self, message: str = "Typing"):
        """
        Show typing indicator.

        Args:
            message: Indicator message
        """
        from rich.text import Text

        text = Text()
        text.append(message, style="dim")
        text.append(" ", style="dim")
        text.append("●", style="cyan")
        text.append("●", style="dim cyan")
        text.append("●", style="dim dim cyan")

        self.console.print(text)

    def pulse_effect(self, message: str, color: str = "cyan"):
        """
        Show pulse effect.

        Args:
            message: Message to pulse
            color: Pulse color
        """
        from rich.text import Text

        text = Text()
        text.append("● ", style=f"bold {color}")
        text.append(message, style=color)

        self.console.print(text)

    def loading_spinner(self, message: str = "Loading"):
        """
        Show loading spinner.

        Args:
            message: Loading message
        """
        from rich.text import Text

        text = Text()
        text.append("⠋ ", style="cyan")
        text.append(message, style="dim")

        self.console.print(text)

    def success_animation(self, message: str):
        """
        Show success animation.

        Args:
            message: Success message
        """
        from rich.text import Text

        text = Text()
        text.append("✓ ", style="bold green")
        text.append(message, style="green")

        self.console.print(text)

    def error_animation(self, message: str):
        """
        Show error animation.

        Args:
            message: Error message
        """
        from rich.text import Text

        text = Text()
        text.append("✗ ", style="bold red")
        text.append(message, style="red")

        self.console.print(text)
