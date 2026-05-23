"""ANSI color engine for terminal styling"""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class AnsiStyle:
    """ANSI style configuration"""
    fg: int | None = None
    bg: int | None = None
    bold: bool = False
    dim: bool = False
    italic: bool = False
    underline: bool = False


# Color palette
COLORS = {
    "primary": "white",
    "secondary": "cyan",
    "success": "green",
    "warning": "yellow",
    "error": "red",
    "dim": "bright_black",
    "highlight": "bold white",
}


class ColorEngine:
    """ANSI color code generator"""

    # Standard 16-color palette
    COLORS_16 = {
        "black": 30,
        "red": 31,
        "green": 32,
        "yellow": 33,
        "blue": 34,
        "magenta": 35,
        "cyan": 36,
        "white": 37,
        "bright_black": 90,
        "bright_red": 91,
        "bright_green": 92,
        "bright_yellow": 93,
        "bright_blue": 94,
        "bright_magenta": 95,
        "bright_cyan": 96,
        "bright_white": 97,
    }

    def __init__(self, use_colors: bool = True):
        self.use_colors = use_colors

    def style(self, text: str, style: AnsiStyle) -> str:
        """Apply ANSI style to text"""
        if not self.use_colors:
            return text

        codes = []

        # Foreground color
        if style.fg is not None:
            codes.append(str(style.fg))

        # Background color
        if style.bg is not None:
            codes.append(str(style.bg + 10))  # BG codes are FG + 10

        # Text styles
        if style.bold:
            codes.append("1")
        if style.dim:
            codes.append("2")
        if style.italic:
            codes.append("3")
        if style.underline:
            codes.append("4")

        if not codes:
            return text

        return f"\x1b[{';'.join(codes)}m{text}\x1b[0m"

    def color(self, text: str, color: str) -> str:
        """Apply color to text"""
        if not self.use_colors:
            return text

        code = self.COLORS_16.get(color)
        if code is None:
            return text

        return self.style(text, AnsiStyle(fg=code))

    def bold(self, text: str) -> str:
        """Make text bold"""
        return self.style(text, AnsiStyle(bold=True))

    def dim(self, text: str) -> str:
        """Make text dim"""
        return self.style(text, AnsiStyle(dim=True))

    def cyan(self, text: str) -> str:
        """Cyan text"""
        return self.color(text, "cyan")

    def yellow(self, text: str) -> str:
        """Yellow text"""
        return self.color(text, "yellow")

    def green(self, text: str) -> str:
        """Green text"""
        return self.color(text, "green")

    def red(self, text: str) -> str:
        """Red text"""
        return self.color(text, "red")

    def white(self, text: str) -> str:
        """White text"""
        return self.color(text, "white")

    def bright_black(self, text: str) -> str:
        """Bright black (dim) text"""
        return self.color(text, "bright_black")

    def strip_ansi(self, text: str) -> str:
        """Remove ANSI codes from text"""
        import re
        ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
        return ansi_escape.sub('', text)

    def visual_width(self, text: str) -> int:
        """Calculate visual width of text (excluding ANSI codes)"""
        clean_text = self.strip_ansi(text)
        # Simple width calculation (doesn't handle wide Unicode chars)
        return len(clean_text)
