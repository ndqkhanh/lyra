"""
Visual Indicators

Visual feedback components for bypass mode.
"""

from enum import Enum


class IndicatorStyle(Enum):
    """Visual indicator styles"""
    ENABLED = "⏺"   # Filled circle
    DISABLED = "◯"  # Empty circle
    WARNING = "⚠"   # Warning triangle
    CRITICAL = "🔴" # Red circle


class VisualIndicator:
    """Visual feedback for bypass mode"""

    @staticmethod
    def get_bypass_indicator(enabled: bool, has_warnings: bool = False) -> str:
        """
        Get indicator for bypass mode

        Args:
            enabled: Whether bypass is enabled
            has_warnings: Whether there are security warnings

        Returns:
            Indicator symbol
        """
        if has_warnings:
            return IndicatorStyle.WARNING.value
        return IndicatorStyle.ENABLED.value if enabled else IndicatorStyle.DISABLED.value

    @staticmethod
    def format_status_message(enabled: bool, operation_count: int = 0) -> str:
        """Format status message for bypass mode"""
        if enabled:
            msg = "Bypass mode ENABLED"
            if operation_count > 0:
                msg += f" ({operation_count} operations bypassed)"
            return msg
        return "Bypass mode disabled"
