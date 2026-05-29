"""
Productivity Mode

Reduces sounds near deadlines or during focus time.
"""

from datetime import date


class ProductivityMode:
    """
    Productivity mode

    Reduces funny sounds near deadlines or during focus time.
    """

    def __init__(self):
        self.deadlines: list[tuple[date, str]] = []
        self.focus_mode = False

    def add_deadline(self, deadline_date: date, description: str):
        """Add a deadline"""
        self.deadlines.append((deadline_date, description))

    def is_near_deadline(self, days_threshold: int = 3) -> bool:
        """Check if near any deadline"""
        today = date.today()
        for deadline_date, _ in self.deadlines:
            days_until = (deadline_date - today).days
            if 0 <= days_until <= days_threshold:
                return True
        return False

    def should_reduce_sounds(self) -> bool:
        """Check if sounds should be reduced"""
        return self.focus_mode or self.is_near_deadline()

    def get_volume_multiplier(self) -> float:
        """Get volume multiplier for productivity mode"""
        if self.should_reduce_sounds():
            return 0.3  # Reduce to 30%
        return 1.0

    def enable_focus_mode(self):
        """Enable focus mode"""
        self.focus_mode = True

    def disable_focus_mode(self):
        """Disable focus mode"""
        self.focus_mode = False
