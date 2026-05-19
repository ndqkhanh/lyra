"""
Status Line

Status line display for Lyra showing bypass mode and shortcuts.
"""

from ..permissions.bypass_manager import BypassManager


class StatusLine:
    """
    Status line display for Lyra

    Shows:
    - Bypass mode status
    - Current operation
    - Keyboard shortcuts
    """

    def __init__(self, bypass_manager: BypassManager):
        self.bypass_manager = bypass_manager

    def render(self) -> str:
        """
        Render status line

        Returns:
            Formatted status line string
        """
        parts = []

        # Bypass status
        if self.bypass_manager.is_bypass_enabled():
            parts.append("⏵⏵ bypass permissions on")
        else:
            parts.append("⏵⏵ bypass permissions off")

        # Keyboard shortcuts
        parts.append("(shift+tab to cycle)")
        parts.append("· esc to interrupt")

        return " ".join(parts)

    def get_bypass_indicator(self) -> str:
        """Get bypass mode indicator symbol"""
        return "⏺" if self.bypass_manager.is_bypass_enabled() else "◯"
