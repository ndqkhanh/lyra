"""Text layout engine for terminal formatting"""

from dataclasses import dataclass
from typing import Literal
from .colors import AnsiStyle, ColorEngine


@dataclass(frozen=True)
class TextSegment:
    """Formatted text segment"""
    content: str
    style: AnsiStyle
    indent: int = 0


@dataclass(frozen=True)
class LayoutConfig:
    """Layout configuration"""
    max_width: int = 120
    indent_size: int = 2
    truncate_at: int = 20
    wrap_mode: Literal["word", "char", "none"] = "word"


class LayoutEngine:
    """Text layout and formatting engine"""

    def __init__(self, config: LayoutConfig | None = None):
        self.config = config or LayoutConfig()
        self.color_engine = ColorEngine()

    def wrap_text(self, text: str, max_width: int, indent: int = 0) -> list[str]:
        """Wrap text to max width with word breaks"""
        if self.config.wrap_mode == "none":
            return [text]

        lines = []
        words = text.split()
        current_line = " " * indent

        for word in words:
            # Check if adding word exceeds width
            test_line = current_line + (" " if current_line.strip() else "") + word
            if self.color_engine.visual_width(test_line) <= max_width:
                current_line = test_line
            else:
                # Start new line
                if current_line.strip():
                    lines.append(current_line)
                current_line = " " * indent + word

        if current_line.strip():
            lines.append(current_line)

        return lines if lines else [" " * indent]

    def truncate_text(self, text: str, max_width: int, ellipsis: str = "…") -> str:
        """Truncate text with ellipsis"""
        visual_width = self.color_engine.visual_width(text)
        if visual_width <= max_width:
            return text

        # Calculate how much to keep
        ellipsis_width = len(ellipsis)
        keep_width = max_width - ellipsis_width

        # Simple truncation (doesn't handle ANSI codes perfectly)
        clean_text = self.color_engine.strip_ansi(text)
        return clean_text[:keep_width] + ellipsis

    def indent_lines(self, lines: list[str], indent: int) -> list[str]:
        """Add indentation to lines"""
        indent_str = " " * indent
        return [indent_str + line for line in lines]

    def align_right(self, text: str, width: int) -> str:
        """Right-align text within width"""
        visual_width = self.color_engine.visual_width(text)
        padding = max(0, width - visual_width)
        return " " * padding + text

    def align_center(self, text: str, width: int) -> str:
        """Center-align text within width"""
        visual_width = self.color_engine.visual_width(text)
        padding = max(0, width - visual_width)
        left_padding = padding // 2
        return " " * left_padding + text

    def format_number(self, n: int) -> str:
        """Format number with thousands separator"""
        return f"{n:,}"

    def format_token_count(self, tokens: int) -> str:
        """Format token count (e.g., 12.4k)"""
        if tokens < 1000:
            return str(tokens)
        elif tokens < 1_000_000:
            return f"{tokens / 1000:.1f}k"
        else:
            return f"{tokens / 1_000_000:.1f}M"

    def format_time(self, seconds: int) -> str:
        """Format time as Xm Ys or Xs"""
        if seconds < 60:
            return f"{seconds}s"

        minutes = seconds // 60
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds}s"

    def measure_visual_width(self, text: str) -> int:
        """Measure visual width of text"""
        return self.color_engine.visual_width(text)

    def create_separator(self, width: int, char: str = "─") -> str:
        """Create horizontal separator line"""
        return char * width

    def pad_to_width(self, text: str, width: int, align: Literal["left", "right", "center"] = "left") -> str:
        """Pad text to specific width"""
        visual_width = self.measure_visual_width(text)

        if visual_width >= width:
            return text

        if align == "left":
            return text + " " * (width - visual_width)
        elif align == "right":
            return " " * (width - visual_width) + text
        else:  # center
            padding = width - visual_width
            left_pad = padding // 2
            right_pad = padding - left_pad
            return " " * left_pad + text + " " * right_pad
