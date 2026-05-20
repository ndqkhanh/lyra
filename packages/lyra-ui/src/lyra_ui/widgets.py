"""
Widgets - Custom Textual widgets for Lyra UI.

Features:
- Message bubbles
- Status indicators
- Progress displays
"""

from datetime import datetime
from typing import List, Optional

from rich.syntax import Syntax
from textual.widgets import Static


class MessageBubble(Static):
    """
    Message bubble widget.

    Features:
    - User/assistant styling
    - Timestamp
    - Syntax highlighting for code
    """

    def __init__(
        self,
        role: str,
        content: str,
        timestamp: Optional[datetime] = None,
    ):
        """
        Initialize message bubble.

        Args:
            role: Message role (user/assistant)
            content: Message content
            timestamp: Message timestamp
        """
        super().__init__()
        self.role = role
        self.content = content
        self.timestamp = timestamp or datetime.now()

    def render(self) -> str:
        """Render message bubble."""
        time_str = self.timestamp.strftime("%H:%M:%S")
        role_label = "You" if self.role == "user" else "Assistant"

        # Check if content contains code blocks
        if "```" in self.content:
            # TODO: Parse and highlight code blocks
            return f"[{time_str}] {role_label}:\n{self.content}"
        else:
            return f"[{time_str}] {role_label}:\n{self.content}"


class TokenUsageIndicator(Static):
    """
    Token usage indicator widget.

    Features:
    - Visual bar
    - Percentage display
    - Color coding (green/yellow/red)
    """

    def __init__(self, used: int = 0, total: int = 200000):
        """
        Initialize token usage indicator.

        Args:
            used: Tokens used
            total: Total tokens available
        """
        super().__init__()
        self.used = used
        self.total = total

    def render(self) -> str:
        """Render token usage indicator."""
        percentage = (self.used / self.total) * 100 if self.total > 0 else 0

        # Color coding
        if percentage < 50:
            color = "green"
        elif percentage < 80:
            color = "yellow"
        else:
            color = "red"

        # Create bar
        bar_width = 20
        filled = int((percentage / 100) * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)

        return f"[{color}]{bar}[/{color}] {self.used:,} / {self.total:,} ({percentage:.1f}%)"

    def update_usage(self, used: int):
        """
        Update token usage.

        Args:
            used: New token count
        """
        self.used = used
        self.refresh()


class AgentStatusIndicator(Static):
    """
    Agent status indicator widget.

    Features:
    - Status display (idle/working/success/error)
    - Color coding
    - Status icon
    """

    def __init__(self, status: str = "idle"):
        """
        Initialize agent status indicator.

        Args:
            status: Agent status
        """
        super().__init__()
        self.status = status

    def render(self) -> str:
        """Render agent status indicator."""
        status_map = {
            "idle": ("⚪", "dim white", "Idle"),
            "working": ("🟡", "yellow", "Working"),
            "success": ("🟢", "green", "Success"),
            "error": ("🔴", "red", "Error"),
        }

        icon, color, label = status_map.get(
            self.status, ("⚪", "white", "Unknown")
        )

        return f"{icon} [{color}]{label}[/{color}]"

    def update_status(self, status: str):
        """
        Update agent status.

        Args:
            status: New status
        """
        self.status = status
        self.refresh()


class ContextUsageRing(Static):
    """
    Context usage ring widget.

    Features:
    - Ring visualization
    - Percentage display
    - Color coding
    """

    def __init__(self, percentage: float = 0.0):
        """
        Initialize context usage ring.

        Args:
            percentage: Context usage percentage (0-100)
        """
        super().__init__()
        self.percentage = percentage

    def render(self) -> str:
        """Render context usage ring."""
        # Simple text-based ring for now
        # TODO: Implement actual ring visualization
        if self.percentage < 50:
            color = "green"
        elif self.percentage < 80:
            color = "yellow"
        else:
            color = "red"

        return f"Context: [{color}]{self.percentage:.1f}%[/{color}]"

    def update_percentage(self, percentage: float):
        """
        Update context usage.

        Args:
            percentage: New percentage
        """
        self.percentage = percentage
        self.refresh()
