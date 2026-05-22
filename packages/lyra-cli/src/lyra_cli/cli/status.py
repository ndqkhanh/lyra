"""Enhanced status bar with Claude Code-inspired design"""

from rich.console import Console
from rich.text import Text
from typing import Optional
import time


class StatusBar:
    """Status bar at bottom of terminal (Claude Code style)"""

    def __init__(self, console: Console):
        self.console = console
        self.model = "opus"
        self.tokens_used = 0
        self.cost = 0.0
        self.session_id = None
        self.start_time = time.time()

    def update(
        self,
        model: Optional[str] = None,
        tokens: Optional[int] = None,
        cost: Optional[float] = None,
        session_id: Optional[str] = None,
    ):
        """Update status bar values"""
        if model:
            self.model = model
        if tokens is not None:
            self.tokens_used = tokens
        if cost is not None:
            self.cost = cost
        if session_id:
            self.session_id = session_id

    def render(self, message: str = ""):
        """Render status bar (Claude Code style)"""
        width = self.console.width

        # Left side: Model and session
        left = f" {self.model}"
        if self.session_id:
            left += f" · {self.session_id[:8]}"

        # Center: Message or status
        center = message

        # Right side: Tokens and cost
        right = ""
        if self.tokens_used > 0:
            right = f"{self.tokens_used:,} tokens"
        if self.cost > 0:
            right += f" · ${self.cost:.4f}"
        right += " "

        # Calculate spacing
        left_len = len(left)
        right_len = len(right)
        center_len = len(center)

        # Build status line
        if left_len + center_len + right_len > width:
            # Truncate center if too long
            available = width - left_len - right_len - 3
            if available > 0:
                center = center[:available] + "..."
            else:
                center = ""

        # Calculate padding
        total_content = left_len + center_len + right_len
        padding = width - total_content

        if padding > 0:
            # Distribute padding
            left_pad = padding // 2
            right_pad = padding - left_pad
            status_line = f"{left}{' ' * left_pad}{center}{' ' * right_pad}{right}"
        else:
            status_line = f"{left}{center}{right}"

        # Ensure exact width
        status_line = status_line[:width].ljust(width)

        # Print with inverse colors (Claude Code style)
        self.console.print(f"[reverse dim]{status_line}[/reverse dim]", end="")

    def clear(self):
        """Clear status bar"""
        width = self.console.width
        self.console.print(" " * width, end="\r")


class StatusLine:
    """Customizable status line (Claude Code style)"""

    def __init__(self, console: Console):
        self.console = console
        self.fields = {}

    def set_field(self, key: str, value: str):
        """Set a status field"""
        self.fields[key] = value

    def render(self):
        """Render status line with custom fields"""
        width = self.console.width

        # Build status from fields
        parts = []
        for key, value in self.fields.items():
            if value:
                parts.append(f"{key}: {value}")

        status = " · ".join(parts)

        # Truncate if too long
        if len(status) > width - 2:
            status = status[:width-5] + "..."

        # Pad to full width
        status = f" {status}".ljust(width)

        # Print with inverse colors
        self.console.print(f"[reverse dim]{status}[/reverse dim]", end="")

    def clear(self):
        """Clear status line"""
        width = self.console.width
        self.console.print(" " * width, end="\r")
