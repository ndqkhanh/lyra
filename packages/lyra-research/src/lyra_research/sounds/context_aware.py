"""
Context-Aware Sounds

Context-aware sound selection based on file type and time.
"""

from pathlib import Path
from typing import Any


class ContextAwareSounds:
    """
    Context-aware sound selection

    Chooses different sounds based on file type, time of day, etc.
    """

    def __init__(self, theme_manager):
        self.theme_manager = theme_manager

    def get_context_sound(self, event: str, context: dict[str, Any]) -> str | None:
        """
        Get context-specific sound

        Args:
            event: Base event name
            context: Context information (file_path, time, etc.)

        Returns:
            Modified event name or None
        """
        # File type specific sounds
        if "file_path" in context:
            file_path = Path(context["file_path"])
            suffix = file_path.suffix

            # Test files (check before Python files)
            if "test" in file_path.name:
                if event == "task_complete":
                    return "task_complete_test"

            # Python files
            if suffix == ".py":
                if event == "task_complete":
                    return "task_complete_python"

        # Time-based sounds
        if "time" in context:
            hour = context["time"].hour

            # After 5 PM: different sounds
            if hour >= 17:
                if event == "task_complete":
                    return "task_complete_evening"

        return None
