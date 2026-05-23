"""Status line - Fixed at bottom below input"""

import sys
import shutil
from typing import TextIO


class StatusLine:
    """Fixed status line below input box

    Displays mode, keyboard hints, and background task indicators.
    Always visible at the very bottom of the terminal.
    """

    def __init__(self, output: TextIO = sys.stdout):
        self.output = output
        self.mode = "default"
        self.hints: list[str] = []
        self.mode_symbol = "⏵⏵"

    def get_terminal_size(self) -> tuple[int, int]:
        """Get terminal size (width, height)"""
        size = shutil.get_terminal_size()
        return size.columns, size.lines

    def update(self, mode: str | None = None, hints: list[str] | None = None) -> None:
        """Update status line content

        Args:
            mode: Current mode (e.g., "bypass permissions on")
            hints: List of keyboard hints (e.g., ["esc to interrupt", "↓ to manage"])
        """
        if mode is not None:
            self.mode = mode
        if hints is not None:
            self.hints = hints

        self.render()

    def render(self) -> None:
        """Render status line at bottom"""
        width, height = self.get_terminal_size()

        # Build status text
        status_parts = [f"  {self.mode_symbol} {self.mode}"]

        if self.hints:
            status_parts.extend(self.hints)

        status_text = " · ".join(status_parts)

        # Truncate if too long
        if len(status_text) > width - 2:
            status_text = status_text[:width - 5] + "..."

        # Pad to full width
        status_text = status_text.ljust(width)

        # Move to bottom line
        self.output.write(f"\033[{height};1H")

        # Render with inverse colors
        self.output.write(f"\033[7m{status_text}\033[0m")

        self.output.flush()

    def clear(self) -> None:
        """Clear status line"""
        width, height = self.get_terminal_size()

        # Move to bottom line and clear
        self.output.write(f"\033[{height};1H\033[K")
        self.output.flush()

    def set_mode(self, mode: str) -> None:
        """Set current mode

        Args:
            mode: Mode name (e.g., "bypass permissions on")
        """
        self.mode = mode
        self.render()

    def set_hints(self, hints: list[str]) -> None:
        """Set keyboard hints

        Args:
            hints: List of hints (e.g., ["esc to exit", "↓ to manage"])
        """
        self.hints = hints
        self.render()

    def add_hint(self, hint: str) -> None:
        """Add a keyboard hint

        Args:
            hint: Hint to add
        """
        if hint not in self.hints:
            self.hints.append(hint)
            self.render()

    def remove_hint(self, hint: str) -> None:
        """Remove a keyboard hint

        Args:
            hint: Hint to remove
        """
        if hint in self.hints:
            self.hints.remove(hint)
            self.render()
