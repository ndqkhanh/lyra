"""
Adaptive Volume - Adaptive volume control based on user activity.

Features:
- Volume boost after inactivity
- Gradual volume increase
- Activity detection
"""

import time


class AdaptiveVolumeController:
    """
    Adaptive volume controller.

    Features:
    - Increase volume after inactivity
    - Base volume + boost
    - Activity tracking
    """

    def __init__(self, base_volume: float = 0.7, boost_amount: float = 0.3):
        """
        Initialize adaptive volume controller.

        Args:
            base_volume: Base volume level (0.0 to 1.0)
            boost_amount: Volume boost amount (0.0 to 1.0)
        """
        self.base_volume = base_volume
        self.boost_amount = boost_amount
        self.last_activity_time = time.time()
        self.inactivity_threshold = 30.0  # 30 seconds
        self.enabled = True

    def record_activity(self):
        """Record user activity."""
        self.last_activity_time = time.time()

    def get_current_volume(self) -> float:
        """
        Get current volume with adaptive boost.

        Returns:
            Current volume level
        """
        if not self.enabled:
            return self.base_volume

        # Calculate inactivity duration
        inactivity_duration = time.time() - self.last_activity_time

        # Apply boost if inactive
        if inactivity_duration >= self.inactivity_threshold:
            boosted_volume = min(1.0, self.base_volume + self.boost_amount)
            return boosted_volume

        return self.base_volume

    def set_base_volume(self, volume: float):
        """
        Set base volume.

        Args:
            volume: Base volume level (0.0 to 1.0)
        """
        self.base_volume = max(0.0, min(1.0, volume))

    def set_boost_amount(self, boost: float):
        """
        Set boost amount.

        Args:
            boost: Boost amount (0.0 to 1.0)
        """
        self.boost_amount = max(0.0, min(1.0, boost))

    def set_inactivity_threshold(self, seconds: float):
        """
        Set inactivity threshold.

        Args:
            seconds: Inactivity threshold in seconds
        """
        self.inactivity_threshold = max(0.0, seconds)

    def enable(self):
        """Enable adaptive volume."""
        self.enabled = True

    def disable(self):
        """Disable adaptive volume."""
        self.enabled = False

    def is_enabled(self) -> bool:
        """Check if adaptive volume is enabled."""
        return self.enabled

    def get_inactivity_duration(self) -> float:
        """Get current inactivity duration in seconds."""
        return time.time() - self.last_activity_time

    def is_boosted(self) -> bool:
        """Check if volume is currently boosted."""
        return self.get_inactivity_duration() >= self.inactivity_threshold
