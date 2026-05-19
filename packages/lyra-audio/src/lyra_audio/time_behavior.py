"""
Time Behavior - Time-based sound behavior.

Features:
- Time-of-day behavior changes
- Different sound variants
- Ridiculous mode after hours
"""

from datetime import datetime, time
from typing import Optional


class TimeBehaviorController:
    """
    Time-based behavior controller.

    Features:
    - Time-of-day behavior
    - After-hours ridiculous mode
    - Sound variant selection
    """

    def __init__(self):
        """Initialize time behavior controller."""
        self.ridiculous_start_hour = 17  # 5 PM
        self.ridiculous_boost = 0.2  # 20% more ridiculous
        self.enabled = True

    def is_after_hours(self) -> bool:
        """
        Check if current time is after hours.

        Returns:
            True if after hours (after 5 PM)
        """
        now = datetime.now()
        return now.hour >= self.ridiculous_start_hour

    def get_ridiculous_factor(self) -> float:
        """
        Get ridiculous factor based on time.

        Returns:
            Ridiculous factor (0.0 to 1.0)
        """
        if not self.enabled:
            return 0.0

        if self.is_after_hours():
            return self.ridiculous_boost

        return 0.0

    def should_use_variant(self, event: str) -> bool:
        """
        Check if should use sound variant.

        Args:
            event: Event name

        Returns:
            True if should use variant
        """
        if not self.enabled:
            return False

        # Use variants after hours
        if self.is_after_hours():
            # Use variant for some events
            import random
            return random.random() < self.ridiculous_boost

        return False

    def get_variant_suffix(self) -> str:
        """
        Get variant suffix for sound file.

        Returns:
            Variant suffix (e.g., "_alt", "_ridiculous")
        """
        if self.is_after_hours():
            return "_ridiculous"
        return ""

    def set_ridiculous_start_hour(self, hour: int):
        """
        Set ridiculous mode start hour.

        Args:
            hour: Hour (0-23)
        """
        self.ridiculous_start_hour = max(0, min(23, hour))

    def set_ridiculous_boost(self, boost: float):
        """
        Set ridiculous boost factor.

        Args:
            boost: Boost factor (0.0 to 1.0)
        """
        self.ridiculous_boost = max(0.0, min(1.0, boost))

    def enable(self):
        """Enable time-based behavior."""
        self.enabled = True

    def disable(self):
        """Disable time-based behavior."""
        self.enabled = False

    def is_enabled(self) -> bool:
        """Check if time-based behavior is enabled."""
        return self.enabled

    def get_current_hour(self) -> int:
        """Get current hour."""
        return datetime.now().hour

    def is_work_hours(self) -> bool:
        """
        Check if current time is work hours (9 AM - 5 PM).

        Returns:
            True if work hours
        """
        hour = self.get_current_hour()
        return 9 <= hour < 17
