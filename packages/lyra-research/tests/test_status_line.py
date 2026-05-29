"""
Tests for Status Line (Bypass Permissions Phase 1)

Tests status line display with bypass mode indicators.
"""

import tempfile
from pathlib import Path

import pytest
from lyra_research.permissions.bypass_manager import BypassManager
from lyra_research.ui.status_line import StatusLine


class TestStatusLine:
    """Test status line"""

    def test_render_with_bypass_on(self):
        """Test render with bypass enabled"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "bypass_config.json"
            manager = BypassManager(config_path)
            manager.enable_bypass()

            status_line = StatusLine(manager)
            output = status_line.render()

            assert "bypass permissions on" in output
            assert "(shift+tab to cycle)" in output
            assert "· esc to interrupt" in output

    def test_render_with_bypass_off(self):
        """Test render with bypass disabled"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "bypass_config.json"
            manager = BypassManager(config_path)

            status_line = StatusLine(manager)
            output = status_line.render()

            assert "bypass permissions off" in output
            assert "(shift+tab to cycle)" in output

    def test_indicator_symbols(self):
        """Test indicator symbols"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "bypass_config.json"
            manager = BypassManager(config_path)

            status_line = StatusLine(manager)

            # Disabled indicator
            assert status_line.get_bypass_indicator() == "◯"

            # Enabled indicator
            manager.enable_bypass()
            assert status_line.get_bypass_indicator() == "⏺"

    def test_keyboard_shortcuts_display(self):
        """Test keyboard shortcuts are displayed"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "bypass_config.json"
            manager = BypassManager(config_path)

            status_line = StatusLine(manager)
            output = status_line.render()

            assert "shift+tab" in output
            assert "esc" in output

    def test_status_line_updates_with_bypass_toggle(self):
        """Test status line updates when bypass is toggled"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "bypass_config.json"
            manager = BypassManager(config_path)
            status_line = StatusLine(manager)

            # Initially off
            output1 = status_line.render()
            assert "bypass permissions off" in output1

            # Toggle on
            manager.toggle_bypass()
            output2 = status_line.render()
            assert "bypass permissions on" in output2

            # Toggle off
            manager.toggle_bypass()
            output3 = status_line.render()
            assert "bypass permissions off" in output3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
