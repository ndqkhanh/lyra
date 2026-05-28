"""
Theme Engine — curated terminal color themes with runtime switching.

Ships 17 themes: 9 dark, 2 light, 2 colorblind-friendly, 4 signature Lyra.
Switch via ``/theme <name>`` or ``ThemeEngine.apply("dracula")``.
Custom themes load from ``~/.lyra/themes/<name>.json``.

Source: Deep Research — abtop, Catppuccin, Tokyo Night, Dracula, Gruvbox, Nord.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

ThemeVariant = Literal["dark", "light", "colorblind"]


@dataclass
class Theme:
    """A terminal color theme definition."""

    name: str
    description: str
    variant: ThemeVariant = "dark"
    primary: str = "cyan"
    secondary: str = "magenta"
    success: str = "green"
    warning: str = "yellow"
    error: str = "red"
    dim: str = "bright_black"
    highlight: str = "bold white"
    bg: str = "black"
    fg: str = "white"
    accent: str = "cyan"
    muted: str = "bright_black"
    border: str = "blue"
    status_ok: str = "green"
    status_warn: str = "yellow"
    status_err: str = "red"
    link: str = "bright_blue"
    code_bg: str = "bright_black"
    quote: str = "green"
    heading: str = "bold cyan"
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "variant": self.variant,
            "colors": {
                "primary": self.primary,
                "secondary": self.secondary,
                "success": self.success,
                "warning": self.warning,
                "error": self.error,
                "dim": self.dim,
                "highlight": self.highlight,
                "bg": self.bg,
                "fg": self.fg,
                "accent": self.accent,
                "muted": self.muted,
                "border": self.border,
                "status_ok": self.status_ok,
                "status_warn": self.status_warn,
                "status_err": self.status_err,
                "link": self.link,
                "code_bg": self.code_bg,
                "quote": self.quote,
                "heading": self.heading,
            },
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Theme:
        colors = data.get("colors", {})
        return cls(
            name=data.get("name", "custom"),
            description=data.get("description", ""),
            variant=data.get("variant", "dark"),
            primary=colors.get("primary", "cyan"),
            secondary=colors.get("secondary", "magenta"),
            success=colors.get("success", "green"),
            warning=colors.get("warning", "yellow"),
            error=colors.get("error", "red"),
            dim=colors.get("dim", "bright_black"),
            highlight=colors.get("highlight", "bold white"),
            bg=colors.get("bg", "black"),
            fg=colors.get("fg", "white"),
            accent=colors.get("accent", "cyan"),
            muted=colors.get("muted", "bright_black"),
            border=colors.get("border", "blue"),
            status_ok=colors.get("status_ok", "green"),
            status_warn=colors.get("status_warn", "yellow"),
            status_err=colors.get("status_err", "red"),
            link=colors.get("link", "bright_blue"),
            code_bg=colors.get("code_bg", "bright_black"),
            quote=colors.get("quote", "green"),
            heading=colors.get("heading", "bold cyan"),
            metadata=data.get("metadata", {}),
        )


BUILTIN_THEMES: dict[str, Theme] = {
    # ── Dark themes ─────────────────────────────────────────────
    "dracula": Theme(
        name="dracula",
        description="Dracula — dark purple/cyan with green accents",
        variant="dark",
        primary="cyan",
        secondary="magenta",
        success="green",
        warning="yellow",
        error="red",
        dim="bright_black",
        highlight="bold white",
        bg="black",
        fg="white",
        accent="magenta",
        muted="bright_black",
        border="blue",
        status_ok="green",
        status_warn="yellow",
        status_err="red",
        link="bright_blue",
        code_bg="bright_black",
        quote="green",
        heading="bold cyan",
        metadata={"source": "https://draculatheme.com"},
    ),
    "tokyo-night": Theme(
        name="tokyo-night",
        description="Tokyo Night — deep navy with vibrant blue/purple",
        variant="dark",
        primary="blue",
        secondary="magenta",
        success="green",
        warning="yellow",
        error="red",
        dim="bright_black",
        highlight="bold white",
        bg="black",
        fg="white",
        accent="cyan",
        muted="bright_black",
        border="blue",
        status_ok="green",
        status_warn="yellow",
        status_err="red",
        link="bright_blue",
        code_bg="bright_black",
        quote="bright_cyan",
        heading="bold blue",
        metadata={"source": "https://github.com/enkia/tokyo-night-vscode-theme"},
    ),
    "catppuccin": Theme(
        name="catppuccin",
        description="Catppuccin Mocha — warm pastel dark theme",
        variant="dark",
        primary="cyan",
        secondary="magenta",
        success="green",
        warning="yellow",
        error="red",
        dim="bright_black",
        highlight="bold white",
        bg="black",
        fg="white",
        accent="magenta",
        muted="bright_black",
        border="blue",
        status_ok="green",
        status_warn="yellow",
        status_err="red",
        link="bright_blue",
        code_bg="bright_black",
        quote="green",
        heading="bold magenta",
        metadata={"source": "https://catppuccin.com"},
    ),
    "gruvbox": Theme(
        name="gruvbox",
        description="Gruvbox Dark — retro warm earthy tones",
        variant="dark",
        primary="yellow",
        secondary="blue",
        success="green",
        warning="yellow",
        error="red",
        dim="bright_black",
        highlight="bold white",
        bg="black",
        fg="white",
        accent="yellow",
        muted="bright_black",
        border="yellow",
        status_ok="green",
        status_warn="yellow",
        status_err="red",
        link="bright_blue",
        code_bg="bright_black",
        quote="green",
        heading="bold yellow",
        metadata={"source": "https://github.com/morhetz/gruvbox"},
    ),
    "rose-pine": Theme(
        name="rose-pine",
        description="Rosé Pine — warm rose/gold with pine accents",
        variant="dark",
        primary="magenta",
        secondary="yellow",
        success="green",
        warning="yellow",
        error="red",
        dim="bright_black",
        highlight="bold white",
        bg="black",
        fg="white",
        accent="magenta",
        muted="bright_black",
        border="magenta",
        status_ok="green",
        status_warn="yellow",
        status_err="red",
        link="bright_magenta",
        code_bg="bright_black",
        quote="magenta",
        heading="bold magenta",
        metadata={"source": "https://rosepinetheme.com"},
    ),
    "everforest": Theme(
        name="everforest",
        description="Everforest — soothing forest greens on dark bg",
        variant="dark",
        primary="green",
        secondary="cyan",
        success="green",
        warning="yellow",
        error="red",
        dim="bright_black",
        highlight="bold white",
        bg="black",
        fg="white",
        accent="green",
        muted="bright_black",
        border="green",
        status_ok="green",
        status_warn="yellow",
        status_err="red",
        link="bright_cyan",
        code_bg="bright_black",
        quote="green",
        heading="bold green",
        metadata={"source": "https://github.com/sainnhe/everforest"},
    ),
    "kanagawa": Theme(
        name="kanagawa",
        description="Kanagawa — Hokusai-inspired deep blue wave theme",
        variant="dark",
        primary="blue",
        secondary="cyan",
        success="green",
        warning="yellow",
        error="red",
        dim="bright_black",
        highlight="bold white",
        bg="black",
        fg="white",
        accent="blue",
        muted="bright_black",
        border="blue",
        status_ok="green",
        status_warn="yellow",
        status_err="red",
        link="bright_blue",
        code_bg="bright_black",
        quote="cyan",
        heading="bold blue",
        metadata={"source": "https://github.com/rebelot/kanagawa.nvim"},
    ),
    "melange": Theme(
        name="melange",
        description="Melange — warm earth/amber blend with golden accents",
        variant="dark",
        primary="yellow",
        secondary="green",
        success="green",
        warning="bright_yellow",
        error="red",
        dim="bright_black",
        highlight="bold white",
        bg="black",
        fg="white",
        accent="yellow",
        muted="bright_black",
        border="yellow",
        status_ok="green",
        status_warn="bright_yellow",
        status_err="red",
        link="bright_yellow",
        code_bg="bright_black",
        quote="yellow",
        heading="bold yellow",
        metadata={"source": "https://github.com/savq/melange-nvim"},
    ),
    "zenburn": Theme(
        name="zenburn",
        description="Zenburn — classic low-contrast muted retro palette",
        variant="dark",
        primary="cyan",
        secondary="green",
        success="green",
        warning="yellow",
        error="red",
        dim="bright_black",
        highlight="bold white",
        bg="black",
        fg="white",
        accent="cyan",
        muted="bright_black",
        border="cyan",
        status_ok="green",
        status_warn="yellow",
        status_err="red",
        link="bright_cyan",
        code_bg="bright_black",
        quote="green",
        heading="bold cyan",
        metadata={"source": "https://github.com/jnurmine/Zenburn"},
    ),
    # ── Light themes ────────────────────────────────────────────
    "nord-light": Theme(
        name="nord-light",
        description="Nord Light — cool arctic blues on white",
        variant="light",
        primary="blue",
        secondary="cyan",
        success="green",
        warning="yellow",
        error="red",
        dim="bright_black",
        highlight="bold black",
        bg="white",
        fg="black",
        accent="cyan",
        muted="bright_black",
        border="blue",
        status_ok="green",
        status_warn="yellow",
        status_err="red",
        link="blue",
        code_bg="bright_black",
        quote="green",
        heading="bold blue",
        metadata={"source": "https://www.nordtheme.com"},
    ),
    "github-light": Theme(
        name="github-light",
        description="GitHub Light — clean, high-contrast light theme",
        variant="light",
        primary="blue",
        secondary="green",
        success="green",
        warning="yellow",
        error="red",
        dim="bright_black",
        highlight="bold black",
        bg="white",
        fg="black",
        accent="blue",
        muted="bright_black",
        border="blue",
        status_ok="green",
        status_warn="yellow",
        status_err="red",
        link="blue",
        code_bg="bright_black",
        quote="green",
        heading="bold blue",
        metadata={"source": "GitHub Primer Design"},
    ),
    # ── Colorblind-friendly ──────────────────────────────────────
    "cb-blue": Theme(
        name="cb-blue",
        description="Colorblind-friendly — blue/orange high contrast",
        variant="colorblind",
        primary="blue",
        secondary="bright_cyan",
        success="green",
        warning="yellow",
        error="red",
        dim="bright_black",
        highlight="bold white",
        bg="black",
        fg="white",
        accent="bright_cyan",
        muted="bright_black",
        border="blue",
        status_ok="green",
        status_warn="yellow",
        status_err="red",
        link="bright_blue",
        code_bg="bright_black",
        quote="bright_cyan",
        heading="bold blue",
        metadata={"palette": "blue-orange", "cvd_friendly": True},
    ),
    "cb-viridis": Theme(
        name="cb-viridis",
        description="Colorblind-friendly — Viridis perceptually uniform",
        variant="colorblind",
        primary="bright_cyan",
        secondary="yellow",
        success="bright_green",
        warning="yellow",
        error="bright_red",
        dim="bright_black",
        highlight="bold white",
        bg="black",
        fg="white",
        accent="bright_cyan",
        muted="bright_black",
        border="blue",
        status_ok="bright_green",
        status_warn="yellow",
        status_err="bright_red",
        link="bright_blue",
        code_bg="bright_black",
        quote="bright_green",
        heading="bold cyan",
        metadata={"palette": "viridis", "cvd_friendly": True},
    ),
    # ── Lyra signature themes ────────────────────────────────────
    "lyra-aurora": Theme(
        name="lyra-aurora",
        description="Lyra Aurora — green/purple aurora borealis",
        variant="dark",
        primary="green",
        secondary="magenta",
        success="bright_green",
        warning="yellow",
        error="red",
        dim="bright_black",
        highlight="bold white",
        bg="black",
        fg="white",
        accent="bright_green",
        muted="bright_black",
        border="green",
        status_ok="bright_green",
        status_warn="yellow",
        status_err="red",
        link="bright_cyan",
        code_bg="bright_black",
        quote="green",
        heading="bold green",
        metadata={"series": "lyra-signature"},
    ),
    "lyra-crimson": Theme(
        name="lyra-crimson",
        description="Lyra Crimson — warm red/gold power theme",
        variant="dark",
        primary="red",
        secondary="yellow",
        success="green",
        warning="bright_yellow",
        error="bright_red",
        dim="bright_black",
        highlight="bold white",
        bg="black",
        fg="white",
        accent="yellow",
        muted="bright_black",
        border="red",
        status_ok="green",
        status_warn="bright_yellow",
        status_err="bright_red",
        link="bright_blue",
        code_bg="bright_black",
        quote="yellow",
        heading="bold red",
        metadata={"series": "lyra-signature"},
    ),
    "lyra-ocean": Theme(
        name="lyra-ocean",
        description="Lyra Ocean — deep blue/teal submerged theme",
        variant="dark",
        primary="cyan",
        secondary="blue",
        success="bright_green",
        warning="yellow",
        error="red",
        dim="bright_black",
        highlight="bold white",
        bg="black",
        fg="white",
        accent="bright_cyan",
        muted="bright_black",
        border="cyan",
        status_ok="bright_green",
        status_warn="yellow",
        status_err="red",
        link="bright_blue",
        code_bg="bright_black",
        quote="bright_cyan",
        heading="bold cyan",
        metadata={"series": "lyra-signature"},
    ),
    "lyra-ember": Theme(
        name="lyra-ember",
        description="Lyra Ember — smoldering orange/amber hot-path theme",
        variant="dark",
        primary="yellow",
        secondary="red",
        success="green",
        warning="bright_yellow",
        error="bright_red",
        dim="bright_black",
        highlight="bold white",
        bg="black",
        fg="white",
        accent="bright_yellow",
        muted="bright_black",
        border="yellow",
        status_ok="green",
        status_warn="bright_yellow",
        status_err="bright_red",
        link="bright_blue",
        code_bg="bright_black",
        quote="yellow",
        heading="bold yellow",
        metadata={"series": "lyra-signature"},
    ),
}


class ThemeEngine:
    """Manages theme loading, switching, and custom theme support.

    Usage::

        engine = ThemeEngine()
        engine.apply("dracula")
        current = engine.current
    """

    def __init__(self) -> None:
        self._themes: dict[str, Theme] = dict(BUILTIN_THEMES)
        self._current: Theme = self._themes["lyra-aurora"]
        self._load_custom_themes()

    @property
    def current(self) -> Theme:
        return self._current

    @property
    def theme_names(self) -> list[str]:
        return sorted(self._themes.keys())

    @property
    def variant_groups(self) -> dict[ThemeVariant, list[str]]:
        groups: dict[ThemeVariant, list[str]] = {"dark": [], "light": [], "colorblind": []}
        for name, theme in self._themes.items():
            groups[theme.variant].append(name)
        return groups

    def apply(self, name: str) -> bool:
        """Switch to a theme by name."""
        theme = self._themes.get(name)
        if theme is None:
            return False
        self._current = theme
        return True

    def register(self, theme: Theme) -> None:
        """Register a new theme."""
        self._themes[theme.name] = theme

    def preview(self, name: str) -> str:
        """Get a preview string showing theme colors."""
        theme = self._themes.get(name)
        if theme is None:
            return f"Theme '{name}' not found."

        from .ui.colors import ColorEngine

        ce = ColorEngine()

        def swatch(label: str, color: str) -> str:
            return f"  {ce.color(label, color)}"

        lines = [
            f"{ce.bold(theme.name)} — {theme.description}",
            f"  Variant: {theme.variant}",
            swatch("primary   ", theme.primary),
            swatch("secondary ", theme.secondary),
            swatch("success   ", theme.success),
            swatch("warning   ", theme.warning),
            swatch("error     ", theme.error),
            swatch("accent    ", theme.accent),
        ]
        return "\n".join(lines)

    def _load_custom_themes(self) -> None:
        """Load custom themes from ~/.lyra/themes/."""
        themes_dir = Path.home() / ".lyra" / "themes"
        if not themes_dir.exists():
            return
        for json_file in themes_dir.glob("*.json"):
            try:
                data = json.loads(json_file.read_text())
                theme = Theme.from_dict(data)
                self._themes[theme.name] = theme
            except (json.JSONDecodeError, KeyError):
                pass

    def export_current(self, path: str | Path) -> None:
        """Export the current theme as a JSON file."""
        target = Path(path)
        target.write_text(json.dumps(self._current.to_dict(), indent=2))

    def reset(self) -> None:
        """Reset to the default theme."""
        self._current = self._themes["lyra-aurora"]


_theme_engine: ThemeEngine | None = None


def get_theme_engine() -> ThemeEngine:
    """Get the global theme engine singleton."""
    global _theme_engine
    if _theme_engine is None:
        _theme_engine = ThemeEngine()
    return _theme_engine
