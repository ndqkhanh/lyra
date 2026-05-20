"""
Notification System - Toast notifications with sound integration.

Features:
- Toast notifications (non-blocking)
- Notification levels (info, success, warning, error)
- Notification history
- Sound integration
- Notification persistence
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.text import Text


class NotificationLevel(Enum):
    """Notification level."""

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class Notification:
    """Notification."""

    id: str
    level: NotificationLevel
    title: str
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    read: bool = False
    action: Optional[str] = None


class NotificationSystem:
    """
    Notification system.

    Features:
    - Toast notifications
    - Notification history
    - Sound integration
    - Persistence
    """

    def __init__(
        self,
        console: Optional[Console] = None,
        max_history: int = 100,
        enable_sound: bool = True,
    ):
        """
        Initialize notification system.

        Args:
            console: Rich console
            max_history: Maximum notifications in history
            enable_sound: Enable notification sounds
        """
        self.console = console or Console()
        self.notifications: List[Notification] = []
        self.max_history = max_history
        self.enable_sound = enable_sound
        self._notification_counter = 0

    def notify(
        self,
        level: NotificationLevel,
        title: str,
        message: str,
        action: Optional[str] = None,
        play_sound: bool = True,
    ) -> Notification:
        """
        Create notification.

        Args:
            level: Notification level
            title: Notification title
            message: Notification message
            action: Optional action
            play_sound: Play notification sound

        Returns:
            Created notification
        """
        # Create notification
        notification = Notification(
            id=f"notif_{self._notification_counter}",
            level=level,
            title=title,
            message=message,
            action=action,
        )
        self._notification_counter += 1

        # Add to history
        self.notifications.append(notification)

        # Trim history
        if len(self.notifications) > self.max_history:
            self.notifications = self.notifications[-self.max_history :]

        # Play sound
        if self.enable_sound and play_sound:
            self._play_sound(level)

        return notification

    def info(self, title: str, message: str, action: Optional[str] = None):
        """
        Create info notification.

        Args:
            title: Notification title
            message: Notification message
            action: Optional action
        """
        return self.notify(NotificationLevel.INFO, title, message, action)

    def success(self, title: str, message: str, action: Optional[str] = None):
        """
        Create success notification.

        Args:
            title: Notification title
            message: Notification message
            action: Optional action
        """
        return self.notify(NotificationLevel.SUCCESS, title, message, action)

    def warning(self, title: str, message: str, action: Optional[str] = None):
        """
        Create warning notification.

        Args:
            title: Notification title
            message: Notification message
            action: Optional action
        """
        return self.notify(NotificationLevel.WARNING, title, message, action)

    def error(self, title: str, message: str, action: Optional[str] = None):
        """
        Create error notification.

        Args:
            title: Notification title
            message: Notification message
            action: Optional action
        """
        return self.notify(NotificationLevel.ERROR, title, message, action)

    def display_toast(self, notification: Notification):
        """
        Display toast notification.

        Args:
            notification: Notification to display
        """
        # Get icon and color
        icon = self._get_level_icon(notification.level)
        color = self._get_level_color(notification.level)

        # Build content
        text = Text()
        text.append(f"{icon} ", style=color)
        text.append(notification.title, style=f"bold {color}")
        text.append("\n")
        text.append(notification.message, style="dim")

        # Add action
        if notification.action:
            text.append("\n\n")
            text.append(f"→ {notification.action}", style="italic cyan")

        # Display
        panel = Panel(
            text,
            border_style=color,
            width=60,
        )
        self.console.print(panel)

    def get_history(
        self,
        level: Optional[NotificationLevel] = None,
        unread_only: bool = False,
        limit: int = 10,
    ) -> List[Notification]:
        """
        Get notification history.

        Args:
            level: Filter by level
            unread_only: Only unread notifications
            limit: Maximum notifications

        Returns:
            List of notifications
        """
        notifications = self.notifications

        # Filter by level
        if level is not None:
            notifications = [n for n in notifications if n.level == level]

        # Filter by read status
        if unread_only:
            notifications = [n for n in notifications if not n.read]

        # Limit
        return notifications[-limit:]

    def mark_read(self, notification_id: str):
        """
        Mark notification as read.

        Args:
            notification_id: Notification ID
        """
        for notification in self.notifications:
            if notification.id == notification_id:
                notification.read = True
                break

    def mark_all_read(self):
        """Mark all notifications as read."""
        for notification in self.notifications:
            notification.read = True

    def clear_history(self):
        """Clear notification history."""
        self.notifications.clear()

    def get_unread_count(self) -> int:
        """
        Get unread notification count.

        Returns:
            Number of unread notifications
        """
        return sum(1 for n in self.notifications if not n.read)

    def _get_level_icon(self, level: NotificationLevel) -> str:
        """Get icon for notification level."""
        icons = {
            NotificationLevel.INFO: "ℹ",
            NotificationLevel.SUCCESS: "✓",
            NotificationLevel.WARNING: "⚠",
            NotificationLevel.ERROR: "✗",
        }
        return icons.get(level, "●")

    def _get_level_color(self, level: NotificationLevel) -> str:
        """Get color for notification level."""
        colors = {
            NotificationLevel.INFO: "cyan",
            NotificationLevel.SUCCESS: "green",
            NotificationLevel.WARNING: "yellow",
            NotificationLevel.ERROR: "red",
        }
        return colors.get(level, "white")

    def _play_sound(self, level: NotificationLevel):
        """
        Play notification sound.

        Args:
            level: Notification level
        """
        # Sound integration with lyra-audio
        # This would integrate with the lyra-audio package
        # For now, this is a placeholder
        pass


class ToastNotification:
    """
    Toast notification widget.

    Features:
    - Non-blocking display
    - Auto-dismiss
    - Position control
    """

    def __init__(self, console: Optional[Console] = None):
        """
        Initialize toast notification.

        Args:
            console: Rich console
        """
        self.console = console or Console()

    def show(
        self,
        message: str,
        level: NotificationLevel = NotificationLevel.INFO,
        duration: float = 3.0,
    ):
        """
        Show toast notification.

        Args:
            message: Notification message
            level: Notification level
            duration: Display duration in seconds
        """
        # Get icon and color
        icon = self._get_level_icon(level)
        color = self._get_level_color(level)

        # Build text
        text = Text()
        text.append(f"{icon} ", style=color)
        text.append(message, style=color)

        # Display
        self.console.print(text)

    def _get_level_icon(self, level: NotificationLevel) -> str:
        """Get icon for notification level."""
        icons = {
            NotificationLevel.INFO: "ℹ",
            NotificationLevel.SUCCESS: "✓",
            NotificationLevel.WARNING: "⚠",
            NotificationLevel.ERROR: "✗",
        }
        return icons.get(level, "●")

    def _get_level_color(self, level: NotificationLevel) -> str:
        """Get color for notification level."""
        colors = {
            NotificationLevel.INFO: "cyan",
            NotificationLevel.SUCCESS: "green",
            NotificationLevel.WARNING: "yellow",
            NotificationLevel.ERROR: "red",
        }
        return colors.get(level, "white")


class NotificationHistory:
    """
    Notification history viewer.

    Features:
    - View notification history
    - Filter by level
    - Search notifications
    """

    def __init__(self, console: Optional[Console] = None):
        """
        Initialize notification history.

        Args:
            console: Rich console
        """
        self.console = console or Console()

    def display(self, notifications: List[Notification]):
        """
        Display notification history.

        Args:
            notifications: List of notifications
        """
        if not notifications:
            self.console.print("No notifications", style="dim")
            return

        for notification in notifications:
            # Get icon and color
            icon = self._get_level_icon(notification.level)
            color = self._get_level_color(notification.level)

            # Build text
            text = Text()

            # Timestamp
            time_str = notification.timestamp.strftime("%H:%M:%S")
            text.append(f"[{time_str}] ", style="dim")

            # Icon and title
            text.append(f"{icon} ", style=color)
            text.append(notification.title, style=f"bold {color}")

            # Read indicator
            if not notification.read:
                text.append(" ●", style="cyan")

            # Message
            text.append("\n  ")
            text.append(notification.message, style="dim")

            self.console.print(text)
            self.console.print()

    def _get_level_icon(self, level: NotificationLevel) -> str:
        """Get icon for notification level."""
        icons = {
            NotificationLevel.INFO: "ℹ",
            NotificationLevel.SUCCESS: "✓",
            NotificationLevel.WARNING: "⚠",
            NotificationLevel.ERROR: "✗",
        }
        return icons.get(level, "●")

    def _get_level_color(self, level: NotificationLevel) -> str:
        """Get color for notification level."""
        colors = {
            NotificationLevel.INFO: "cyan",
            NotificationLevel.SUCCESS: "green",
            NotificationLevel.WARNING: "yellow",
            NotificationLevel.ERROR: "red",
        }
        return colors.get(level, "white")
