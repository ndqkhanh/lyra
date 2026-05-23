"""Scrollable area manager - Manage scrollable content above fixed UI"""

import shutil
from typing import List


class ScrollManager:
    """Manage scrollable content area above fixed UI

    Implements virtualized scrolling with:
    - Auto-scroll to bottom on new content
    - User scroll with preserved position
    - Only render visible lines (performance)
    """

    def __init__(self, fixed_height: int = 4):
        self.fixed_height = fixed_height  # Height of fixed UI at bottom
        self.scroll_offset = 0
        self.content_lines: List[str] = []
        self.auto_scroll = True

    def get_terminal_size(self) -> tuple[int, int]:
        """Get terminal size (width, height)"""
        size = shutil.get_terminal_size()
        return size.columns, size.lines

    def get_visible_height(self) -> int:
        """Calculate visible area height

        Returns:
            Number of visible lines
        """
        _, height = self.get_terminal_size()
        return height - self.fixed_height

    def append_line(self, line: str) -> None:
        """Append line and auto-scroll to bottom

        Args:
            line: Line to append
        """
        self.content_lines.append(line)

        # Auto-scroll to bottom if enabled
        if self.auto_scroll:
            visible_height = self.get_visible_height()
            if len(self.content_lines) > visible_height:
                self.scroll_offset = len(self.content_lines) - visible_height

    def append_lines(self, lines: List[str]) -> None:
        """Append multiple lines

        Args:
            lines: Lines to append
        """
        for line in lines:
            self.append_line(line)

    def scroll_up(self, lines: int = 1) -> None:
        """Scroll up

        Args:
            lines: Number of lines to scroll
        """
        self.auto_scroll = False
        self.scroll_offset = max(0, self.scroll_offset - lines)

    def scroll_down(self, lines: int = 1) -> None:
        """Scroll down

        Args:
            lines: Number of lines to scroll
        """
        visible_height = self.get_visible_height()
        max_offset = max(0, len(self.content_lines) - visible_height)
        self.scroll_offset = min(max_offset, self.scroll_offset + lines)

        # Re-enable auto-scroll if at bottom
        if self.scroll_offset >= max_offset:
            self.auto_scroll = True

    def scroll_to_bottom(self) -> None:
        """Scroll to bottom"""
        visible_height = self.get_visible_height()
        if len(self.content_lines) > visible_height:
            self.scroll_offset = len(self.content_lines) - visible_height
        else:
            self.scroll_offset = 0
        self.auto_scroll = True

    def scroll_to_top(self) -> None:
        """Scroll to top"""
        self.scroll_offset = 0
        self.auto_scroll = False

    def get_visible_lines(self) -> List[str]:
        """Get currently visible lines

        Returns:
            List of visible lines
        """
        visible_height = self.get_visible_height()
        start = self.scroll_offset
        end = start + visible_height

        return self.content_lines[start:end]

    def render_visible_area(self) -> str:
        """Render only visible lines

        Returns:
            Formatted visible content
        """
        visible_lines = self.get_visible_lines()
        return "\n".join(visible_lines)

    def clear(self) -> None:
        """Clear all content"""
        self.content_lines.clear()
        self.scroll_offset = 0
        self.auto_scroll = True

    def get_scroll_position(self) -> tuple[int, int, int]:
        """Get scroll position info

        Returns:
            Tuple of (offset, total_lines, visible_height)
        """
        return (
            self.scroll_offset,
            len(self.content_lines),
            self.get_visible_height()
        )

    def is_at_bottom(self) -> bool:
        """Check if scrolled to bottom

        Returns:
            True if at bottom
        """
        visible_height = self.get_visible_height()
        max_offset = max(0, len(self.content_lines) - visible_height)
        return self.scroll_offset >= max_offset
