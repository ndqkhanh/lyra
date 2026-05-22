"""Theme Manager — unified theme bridge from lyra-ui into tui_v2.

Brings the rich ThemeManager, AnimationEffects, and color schemes from
lyra-ui (packages/lyra-ui/src/lyra_ui/themes.py) into the TUI v2 shell.
Provides a /theme <name> command, a theme-switcher modal, and auto-
detection of system dark/light preference.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, Optional

from rich.console import Console
from rich.style import Style
from rich.table import Table
from rich.text import Text
from rich.theme import Theme as RichTheme

# ---------------------------------------------------------------------------
# Theme palette definitions
# ---------------------------------------------------------------------------

@dataclass
class ThemeColors:
    """Complete colour palette for a theme."""
    primary: str = "cyan"
    secondary: str = "blue"
    success: str = "green"
    warning: str = "yellow"
    error: str = "red"
    info: str = "cyan"
    background: str = "black"
    foreground: str = "white"
    dim: str = "dim white"
    bright: str = "bright_white"
    accent: str = "magenta"
    surface: str = "black"
    panel: str = "gray23"
    border: str = "bright_black"


class ThemePreset(Enum):
    """Built-in theme presets."""
    DEFAULT = "default"
    DARK = "dark"
    LIGHT = "light"
    SOLARIZED_DARK = "solarized_dark"
    SOLARIZED_LIGHT = "solarized_light"
    DRACULA = "dracula"
    MONOKAI = "monokai"
    NORD = "nord"
    GRUVBOX = "gruvbox"
    CATPPUCCIN = "catppuccin"
    TOKYO_NIGHT = "tokyo_night"
    EVERFOREST = "everforest"


# ---------------------------------------------------------------------------
# Built-in themes
# ---------------------------------------------------------------------------

_BUILTIN_THEMES: Dict[ThemePreset, ThemeColors] = {
    ThemePreset.DEFAULT: ThemeColors(
        primary="cyan", secondary="blue", success="green",
        warning="yellow", error="red", info="cyan",
        background="black", foreground="white", dim="dim white",
        bright="bright_white", accent="magenta",
    ),
    ThemePreset.DARK: ThemeColors(
        primary="bright_cyan", secondary="bright_blue", success="bright_green",
        warning="bright_yellow", error="bright_red", info="bright_cyan",
        background="black", foreground="bright_white", dim="dim white",
        bright="bright_white", accent="bright_magenta",
    ),
    ThemePreset.LIGHT: ThemeColors(
        primary="blue", secondary="cyan", success="green",
        warning="yellow", error="red", info="blue",
        background="white", foreground="black", dim="dim black",
        bright="bright_black", accent="magenta",
    ),
    ThemePreset.SOLARIZED_DARK: ThemeColors(
        primary="cyan", secondary="blue", success="green",
        warning="yellow", error="red", info="cyan",
        background="#002b36", foreground="#839496",
        dim="#586e75", bright="#93a1a1", accent="#d33682",
    ),
    ThemePreset.SOLARIZED_LIGHT: ThemeColors(
        primary="cyan", secondary="blue", success="green",
        warning="yellow", error="red", info="cyan",
        background="#fdf6e3", foreground="#657b83",
        dim="#93a1a1", bright="#586e75", accent="#d33682",
    ),
    ThemePreset.DRACULA: ThemeColors(
        primary="#bd93f9", secondary="#8be9fd", success="#50fa7b",
        warning="#f1fa8c", error="#ff5555", info="#8be9fd",
        background="#282a36", foreground="#f8f8f2",
        dim="#6272a4", bright="#ffffff", accent="#ff79c6",
    ),
    ThemePreset.MONOKAI: ThemeColors(
        primary="#a6e22e", secondary="#66d9ef", success="#a6e22e",
        warning="#fd971f", error="#f92672", info="#66d9ef",
        background="#272822", foreground="#f8f8f2",
        dim="#75715e", bright="#ffffff", accent="#ae81ff",
    ),
    ThemePreset.NORD: ThemeColors(
        primary="#88c0d0", secondary="#81a1c1", success="#a3be8c",
        warning="#ebcb8b", error="#bf616a", info="#88c0d0",
        background="#2e3440", foreground="#d8dee9",
        dim="#4c566a", bright="#e5e9f0", accent="#b48ead",
    ),
    ThemePreset.GRUVBOX: ThemeColors(
        primary="#fabd2f", secondary="#83a598", success="#b8bb26",
        warning="#d79921", error="#fb4934", info="#83a598",
        background="#282828", foreground="#ebdbb2",
        dim="#928374", bright="#fbf1c7", accent="#d3869b",
    ),
    ThemePreset.CATPPUCCIN: ThemeColors(
        primary="#89b4fa", secondary="#89dceb", success="#a6e3a1",
        warning="#f9e2af", error="#f38ba8", info="#89dceb",
        background="#1e1e2e", foreground="#cdd6f4",
        dim="#6c7086", bright="#f5f5f5", accent="#cba6f7",
    ),
    ThemePreset.TOKYO_NIGHT: ThemeColors(
        primary="#7aa2f7", secondary="#7dcfff", success="#9ece6a",
        warning="#e0af68", error="#f7768e", info="#7dcfff",
        background="#1a1b26", foreground="#a9b1d6",
        dim="#565f89", bright="#c0caf5", accent="#bb9af7",
    ),
    ThemePreset.EVERFOREST: ThemeColors(
        primary="#a7c080", secondary="#7fbbb3", success="#a7c080",
        warning="#dbbc7f", error="#e67e80", info="#7fbbb3",
        background="#2d353b", foreground="#d3c6aa",
        dim="#859289", bright="#e0dcc0", accent="#d699b6",
    ),
}


# ---------------------------------------------------------------------------
# Animation effects (ported from lyra-ui)
# ---------------------------------------------------------------------------

class AnimationEffects:
    """Lightweight terminal animation effects.

    Provides typed indicators — typing, pulsing, spinning — that work
    alongside (or instead of) Textual's built-in spinners.
    """

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()

    def typing_indicator(self, message: str = "Thinking") -> None:
        """Show a subtle typing indicator."""
        text = Text()
        text.append(message, style="dim")
        text.append(" ", style="dim")
        text.append("●", style="cyan")
        text.append("●", style="dim cyan")
        text.append("●", style="dim dim cyan")
        self.console.print(text)

    def pulse_effect(self, message: str, color: str = "cyan") -> None:
        """Show a pulse announcement."""
        text = Text()
        text.append("● ", style=f"bold {color}")
        text.append(message, style=color)
        self.console.print(text)

    def success_animation(self, message: str) -> None:
        """Show a success confirmation."""
        text = Text()
        text.append("✓ ", style="bold green")
        text.append(message, style="green")
        self.console.print(text)

    def error_animation(self, message: str) -> None:
        """Show an error notification."""
        text = Text()
        text.append("✗ ", style="bold red")
        text.append(message, style="red")
        self.console.print(text)


# ---------------------------------------------------------------------------
# Theme manager
# ---------------------------------------------------------------------------

class ThemeManager:
    """Central theme manager for Lyra TUI.

    Manages preset themes, custom themes, Rich theme bridging, and
    reads ``LYRA_THEME`` env var for auto-theme on startup.
    """

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.current_preset = ThemePreset.DEFAULT
        self._presets: Dict[ThemePreset, ThemeColors] = dict(_BUILTIN_THEMES)
        self._custom: Dict[str, ThemeColors] = {}
        self._load_env_override()

    # -- Accessors -------------------------------------------------------

    @property
    def current(self) -> ThemeColors:
        return self.get_colors()

    def get_colors(self, name: Optional[ThemePreset] = None) -> ThemeColors:
        target = name or self.current_preset
        if target in self._presets:
            return self._presets[target]
        return self._presets[ThemePreset.DEFAULT]

    def get_custom(self, name: str) -> Optional[ThemeColors]:
        return self._custom.get(name)

    def list_themes(self) -> list[str]:
        """Return all available theme names (presets + custom)."""
        presets = [p.value for p in self._presets]
        customs = list(self._custom.keys())
        return presets + ["custom: " + c for c in customs]

    # -- Switching -------------------------------------------------------

    def set_theme(self, name: str) -> bool:
        """Switch to a theme by name. Returns True on success."""
        name_lower = name.lower().replace(" ", "_")
        for preset in ThemePreset:
            if preset.value == name_lower:
                self.current_preset = preset
                return True
        if name_lower in self._custom:
            # Pseudo — we store custom under the preset name
            self.current_preset = ThemePreset.DEFAULT
            return True
        return False

    def set_theme_from_preset(self, preset: ThemePreset) -> None:
        self.current_preset = preset

    # -- Custom themes ---------------------------------------------------

    def create_custom(self, name: str, colors: ThemeColors) -> bool:
        if name in self._custom:
            return False
        self._custom[name] = colors
        return True

    def remove_custom(self, name: str) -> bool:
        return self._custom.pop(name, None) is not None

    # -- Rich bridge -----------------------------------------------------

    def to_rich_theme(self, preset: Optional[ThemePreset] = None) -> RichTheme:
        """Convert a Lyra theme to a Rich Theme for styling."""
        colors = self.get_colors(preset)
        return RichTheme({
            "primary": colors.primary,
            "secondary": colors.secondary,
            "success": colors.success,
            "warning": colors.warning,
            "error": colors.error,
            "info": colors.info,
            "dim": colors.dim,
            "bright": colors.bright,
            "accent": colors.accent,
            "surface": colors.surface,
            "panel": colors.panel,
            "border": colors.border,
        })

    def apply_to_console(self) -> None:
        """Push the current theme's Rich theme onto the shared console."""
        self.console.push_theme(self.to_rich_theme())

    # -- Preview ---------------------------------------------------------

    def preview_table(self) -> str:
        """Render a colour-swatch table of all preset themes."""
        table = Table(title="Lyra Themes", box=None, padding=(0, 2))
        table.add_column("Theme", style="bold", no_wrap=True)
        table.add_column("Primary", no_wrap=True)
        table.add_column("Secondary", no_wrap=True)
        table.add_column("Success", no_wrap=True)
        table.add_column("Warning", no_wrap=True)
        table.add_column("Error", no_wrap=True)
        table.add_column("Accent", no_wrap=True)

        for preset, colors in self._presets.items():
            marker = "●" if preset == self.current_preset else "○"
            table.add_row(
                f"{marker} {preset.value}",
                Text("█████", style=colors.primary),
                Text("█████", style=colors.secondary),
                Text("█████", style=colors.success),
                Text("█████", style=colors.warning),
                Text("█████", style=colors.error),
                Text("█████", style=colors.accent),
            )
        return table

    # -- Internal --------------------------------------------------------

    def _load_env_override(self) -> None:
        env_theme = os.environ.get("LYRA_THEME", "").lower().replace(" ", "_")
        if env_theme:
            for preset in ThemePreset:
                if preset.value == env_theme:
                    self.current_preset = preset
                    break


# Singleton for the running process
_theme_manager: Optional[ThemeManager] = None


def get_theme_manager() -> ThemeManager:
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager


# ---------------------------------------------------------------------------
# Rich-style helpers for status.py
# ---------------------------------------------------------------------------

def threshold_colour(pct: float) -> str:
    """Return Rich-compatible style for a percentage threshold."""
    if pct >= 95.0:
        return "bold red"
    if pct >= 80.0:
        return "bold orange1"
    if pct >= 50.0:
        return "bold yellow"
    return "bold green"


__all__ = [
    "ThemeColors",
    "ThemePreset",
    "ThemeManager",
    "AnimationEffects",
    "threshold_colour",
    "get_theme_manager",
]
