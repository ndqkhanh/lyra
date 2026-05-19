"""
Event Mapper

Maps Lyra events to sound events with intelligent detection.
"""

from enum import Enum
from typing import Optional


class SoundEvent(Enum):
    """Sound events"""
    SESSION_START = "session_start"
    TASK_START = "task_start"
    TASK_COMPLETE = "task_complete"
    ERROR = "error"
    SYNTAX_ERROR = "syntax_error"
    LOGIC_ERROR = "logic_error"
    RATE_LIMIT = "rate_limit"
    MILESTONE = "milestone"
    COMPACT = "compact"


class EventMapper:
    """
    Maps Lyra events to sound events

    Provides intelligent event detection and mapping.
    """

    def map_error(self, error_message: str) -> SoundEvent:
        """
        Map error message to specific sound event

        Args:
            error_message: Error message text

        Returns:
            Appropriate sound event
        """
        msg_lower = error_message.lower()

        # Syntax errors
        if any(kw in msg_lower for kw in ["syntax", "parse", "unexpected token"]):
            return SoundEvent.SYNTAX_ERROR

        # Logic errors
        if any(kw in msg_lower for kw in ["assertion", "logic", "invalid"]):
            return SoundEvent.LOGIC_ERROR

        # Rate limiting
        if any(kw in msg_lower for kw in ["rate limit", "too many requests", "quota"]):
            return SoundEvent.RATE_LIMIT

        # Generic error
        return SoundEvent.ERROR

    def detect_milestone(self, task_count: int) -> Optional[SoundEvent]:
        """
        Detect milestone achievements

        Args:
            task_count: Number of completed tasks

        Returns:
            MILESTONE event if milestone reached, None otherwise
        """
        # Milestones at 10, 25, 50, 100 tasks
        if task_count in [10, 25, 50, 100]:
            return SoundEvent.MILESTONE
        return None
