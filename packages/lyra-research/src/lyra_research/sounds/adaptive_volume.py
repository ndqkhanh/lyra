"""
Adaptive Volume

Adaptive volume adjustment based on user response.
"""

from datetime import datetime, timedelta


class AdaptiveVolume:
    """
    Adaptive volume adjustment

    Increases volume if user hasn't responded to completion notification.
    """

    def __init__(self, base_volume: float = 0.5):
        self.base_volume = base_volume
        self.last_completion: datetime | None = None
        self.no_response_threshold = timedelta(seconds=30)

    def get_volume(self, event: str) -> float:
        """
        Get adaptive volume for event

        Args:
            event: Event name

        Returns:
            Adjusted volume level
        """
        if event != "task_complete":
            return self.base_volume

        # Check if previous completion was ignored
        if self.last_completion:
            elapsed = datetime.now() - self.last_completion
            if elapsed > self.no_response_threshold:
                # Increase volume by 50%
                return min(1.0, self.base_volume * 1.5)

        return self.base_volume

    def mark_completion(self):
        """Mark task completion time"""
        self.last_completion = datetime.now()

    def mark_response(self):
        """Mark user response (resets adaptive volume)"""
        self.last_completion = None
