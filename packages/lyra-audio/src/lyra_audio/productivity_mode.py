"""
Productivity Mode - Productivity-focused sound behavior.

Features:
- Reduce sounds near deadlines
- Critical sounds only
- Focus mode
"""

from datetime import datetime, timedelta
from typing import List, Optional


class ProductivityModeController:
    """
    Productivity mode controller.

    Features:
    - Deadline-aware sound reduction
    - Critical sounds only
    - Focus mode
    """

    CRITICAL_EVENTS = [
        "error_general",
        "error_syntax",
        "error_logic",
        "error_network",
        "error_rate_limit",
        "task_complete",
        "milestone_10",
        "milestone_50",
        "milestone_100",
    ]

    def __init__(self):
        """Initialize productivity mode controller."""
        self.enabled = False
        self.deadline: Optional[datetime] = None
        self.deadline_threshold_hours = 2.0  # 2 hours before deadline
        self.focus_mode = False

    def set_deadline(self, deadline: datetime):
        """
        Set deadline.

        Args:
            deadline: Deadline datetime
        """
        self.deadline = deadline

    def clear_deadline(self):
        """Clear deadline."""
        self.deadline = None

    def is_near_deadline(self) -> bool:
        """
        Check if near deadline.

        Returns:
            True if within threshold of deadline
        """
        if not self.deadline:
            return False

        now = datetime.now()
        time_until_deadline = (self.deadline - now).total_seconds() / 3600.0

        return 0 < time_until_deadline <= self.deadline_threshold_hours

    def should_play_sound(self, event: str) -> bool:
        """
        Check if should play sound for event.

        Args:
            event: Event name

        Returns:
            True if should play sound
        """
        if not self.enabled:
            return True

        # Focus mode: only critical sounds
        if self.focus_mode:
            return event in self.CRITICAL_EVENTS

        # Near deadline: only critical sounds
        if self.is_near_deadline():
            return event in self.CRITICAL_EVENTS

        return True

    def enable(self):
        """Enable productivity mode."""
        self.enabled = True

    def disable(self):
        """Disable productivity mode."""
        self.enabled = False

    def is_enabled(self) -> bool:
        """Check if productivity mode is enabled."""
        return self.enabled

    def enable_focus_mode(self):
        """Enable focus mode (critical sounds only)."""
        self.focus_mode = True

    def disable_focus_mode(self):
        """Disable focus mode."""
        self.focus_mode = False

    def is_focus_mode(self) -> bool:
        """Check if focus mode is enabled."""
        return self.focus_mode

    def set_deadline_threshold(self, hours: float):
        """
        Set deadline threshold.

        Args:
            hours: Hours before deadline to activate
        """
        self.deadline_threshold_hours = max(0.0, hours)

    def get_time_until_deadline(self) -> Optional[float]:
        """
        Get time until deadline in hours.

        Returns:
            Hours until deadline or None
        """
        if not self.deadline:
            return None

        now = datetime.now()
        time_until = (self.deadline - now).total_seconds() / 3600.0

        return max(0.0, time_until)

    def is_critical_event(self, event: str) -> bool:
        """
        Check if event is critical.

        Args:
            event: Event name

        Returns:
            True if critical event
        """
        return event in self.CRITICAL_EVENTS
