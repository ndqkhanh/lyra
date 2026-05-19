"""
Tests for Visual Indicators (Bypass Permissions Phase 1)

Tests visual feedback components.
"""

import pytest
from lyra_research.ui.indicators import VisualIndicator, IndicatorStyle


class TestVisualIndicator:
    """Test visual indicators"""

    def test_indicator_symbols(self):
        """Test indicator symbol values"""
        assert IndicatorStyle.ENABLED.value == "⏺"
        assert IndicatorStyle.DISABLED.value == "◯"
        assert IndicatorStyle.WARNING.value == "⚠"
        assert IndicatorStyle.CRITICAL.value == "🔴"

    def test_get_bypass_indicator_enabled(self):
        """Test bypass indicator when enabled"""
        indicator = VisualIndicator.get_bypass_indicator(enabled=True)
        assert indicator == "⏺"

    def test_get_bypass_indicator_disabled(self):
        """Test bypass indicator when disabled"""
        indicator = VisualIndicator.get_bypass_indicator(enabled=False)
        assert indicator == "◯"

    def test_get_bypass_indicator_with_warnings(self):
        """Test bypass indicator with warnings"""
        indicator = VisualIndicator.get_bypass_indicator(enabled=True, has_warnings=True)
        assert indicator == "⚠"

        indicator = VisualIndicator.get_bypass_indicator(enabled=False, has_warnings=True)
        assert indicator == "⚠"

    def test_format_status_message_disabled(self):
        """Test status message when disabled"""
        msg = VisualIndicator.format_status_message(enabled=False)
        assert msg == "Bypass mode disabled"

    def test_format_status_message_enabled_no_operations(self):
        """Test status message when enabled with no operations"""
        msg = VisualIndicator.format_status_message(enabled=True)
        assert msg == "Bypass mode ENABLED"

    def test_format_status_message_enabled_with_operations(self):
        """Test status message when enabled with operations"""
        msg = VisualIndicator.format_status_message(enabled=True, operation_count=5)
        assert "Bypass mode ENABLED" in msg
        assert "5 operations bypassed" in msg

    def test_format_status_message_with_zero_operations(self):
        """Test status message with zero operations"""
        msg = VisualIndicator.format_status_message(enabled=True, operation_count=0)
        assert msg == "Bypass mode ENABLED"
        assert "operations bypassed" not in msg


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
