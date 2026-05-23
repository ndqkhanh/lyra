"""Status line - Fixed at bottom below input"""

import sys
import shutil
from typing import TextIO, Optional

from .colors import ColorEngine


class StatusLine:
    """Fixed status line below input box

    Displays mode, keyboard hints, context percentage, and permission mode.
    Always visible at the very bottom of the terminal.
    """

    def __init__(self, output: TextIO = sys.stdout):
        self.output = output
        self.mode = "default"
        self.hints: list[str] = []
        self.mode_symbol = "⏵⏵"
        self.colors = ColorEngine()

        # Enhanced features
        self.context_percentage: Optional[int] = None
        self.permission_mode: Optional[str] = None

    def get_terminal_size(self) -> tuple[int, int]:
        """Get terminal size (width, height)"""
        size = shutil.get_terminal_size()
        return size.columns, size.lines

    def update(
        self,
        mode: str | None = None,
        hints: list[str] | None = None,
        context_percentage: Optional[int] = None,
        permission_mode: Optional[str] = None
    ) -> None:
        """Update status line content

        Args:
            mode: Current mode (e.g., "default", "streaming")
            hints: List of keyboard hints (e.g., ["esc to exit", "↓ to manage"])
            context_percentage: Context window usage (0-100)
            permission_mode: Permission mode (ask, bypass, deny)
        """
        if mode is not None:
            self.mode = mode
        if hints is not None:
            self.hints = hints
        if context_percentage is not None:
            self.context_percentage = context_percentage
        if permission_mode is not None:
            self.permission_mode = permission_mode

        self.render()

    def render(self) -> None:
        """Render status line at bottom"""
        width, height = self.get_terminal_size()

        # Build status text with enhanced features
        status_parts = [f"  {self.mode_symbol} {self.mode}"]

        # Add context percentage if available
        if self.context_percentage is not None and self.context_percentage > 0:
            ctx_text = f"{self.context_percentage}% context"

            # Color code based on usage
            if self.context_percentage < 50:
                ctx_text = self.colors.green(ctx_text)
            elif self.context_percentage < 80:
                ctx_text = self.colors.yellow(ctx_text)
            else:
                ctx_text = self.colors.red(ctx_text)

            status_parts.append(ctx_text)

        # Add permission mode if available
        if self.permission_mode:
            mode_text = f"{self.permission_mode} permissions"

            # Color code based on mode
            if self.permission_mode == "bypass":
                mode_text = self.colors.yellow(mode_text)
            elif self.permission_mode == "ask":
                mode_text = self.colors.green(mode_text)
            elif self.permission_mode == "deny":
                mode_text = self.colors.red(mode_text)

            status_parts.append(mode_text)

        # Add hints
        if self.hints:
            status_parts.extend(self.hints)

        status_text = " · ".join(status_parts)

        # Truncate if too long (accounting for ANSI codes)
        # Note: This is a simple truncation, real implementation should handle ANSI codes properly
        visible_length = len(self._strip_ansi(status_text))
        if visible_length > width - 2:
            # Truncate the plain text parts, not the colored ones
            status_text = status_text[:width - 5] + "..."

        # Pad to full width (accounting for ANSI codes)
        padding_needed = width - visible_length
        if padding_needed > 0:
            status_text += " " * padding_needed

        # Move to bottom line
        self.output.write(f"\033[{height};1H")

        # Render with inverse colors
        self.output.write(f"\033[7m{status_text}\033[0m")

        self.output.flush()

    def _strip_ansi(self, text: str) -> str:
        """Strip ANSI escape codes from text

        Args:
            text: Text with ANSI codes

        Returns:
            Plain text without ANSI codes
        """
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)

    def render_inline(self) -> None:
        """Render status line inline (no newline)"""
        # Build status text (same as render but without positioning)
        status_parts = [f"  {self.mode_symbol} {self.mode}"]

        # Add context percentage
        if self.context_percentage is not None and self.context_percentage > 0:
            ctx_text = f"{self.context_percentage}% context"
            if self.context_percentage < 50:
                ctx_text = self.colors.green(ctx_text)
            elif self.context_percentage < 80:
                ctx_text = self.colors.yellow(ctx_text)
            else:
                ctx_text = self.colors.red(ctx_text)
            status_parts.append(ctx_text)

        # Add permission mode
        if self.permission_mode:
            mode_text = f"{self.permission_mode} permissions"
            if self.permission_mode == "bypass":
                mode_text = self.colors.yellow(mode_text)
            elif self.permission_mode == "ask":
                mode_text = self.colors.green(mode_text)
            elif self.permission_mode == "deny":
                mode_text = self.colors.red(mode_text)
            status_parts.append(mode_text)

        # Add hints
        if self.hints:
            status_parts.extend(self.hints)

        status_text = " · ".join(status_parts)

        self.output.write(status_text)
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
