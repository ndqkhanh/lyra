"""
Tests for Bypass Manager (Bypass Permissions Phase 0)

Tests bypass mode management with configuration and timeout.
"""

import tempfile
import time
from pathlib import Path

import pytest
from lyra_research.permissions.bypass_manager import (
    BypassConfig,
    BypassManager,
)


class TestBypassManager:
    """Test bypass manager"""

    def test_enable_disable_bypass(self):
        """Test enable and disable bypass"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "bypass_config.json"
            manager = BypassManager(config_path)

            # Start disabled
            assert not manager.is_bypass_enabled()

            # Enable
            manager.enable_bypass()
            assert manager.is_bypass_enabled()
            assert manager.enabled_at is not None

            # Disable
            manager.disable_bypass()
            assert not manager.is_bypass_enabled()
            assert manager.enabled_at is None

    def test_toggle_bypass(self):
        """Test toggle bypass"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "bypass_config.json"
            manager = BypassManager(config_path)

            # Start disabled
            assert not manager.is_bypass_enabled()

            # Toggle to enabled
            result = manager.toggle_bypass()
            assert result is True
            assert manager.is_bypass_enabled()

            # Toggle to disabled
            result = manager.toggle_bypass()
            assert result is False
            assert not manager.is_bypass_enabled()

    def test_auto_disable_timeout(self):
        """Test auto-disable after timeout"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "bypass_config.json"
            manager = BypassManager(config_path)
            manager.config.auto_disable_after_minutes = 0.01  # 0.6 seconds

            # Enable bypass
            manager.enable_bypass()
            assert manager.is_bypass_enabled()

            # Wait for timeout
            time.sleep(1)

            # Should be auto-disabled
            assert not manager.is_bypass_enabled()

    def test_operation_whitelist_empty(self):
        """Test operation whitelist when empty (all allowed)"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "bypass_config.json"
            manager = BypassManager(config_path)

            # Empty list = all operations allowed
            assert manager.is_operation_allowed("any_operation")
            assert manager.is_operation_allowed("another_operation")

    def test_operation_whitelist_specific(self):
        """Test operation whitelist with specific operations"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "bypass_config.json"
            manager = BypassManager(config_path)
            manager.config.allowed_operations = ["file_read", "api_call"]

            # Only whitelisted operations allowed
            assert manager.is_operation_allowed("file_read")
            assert manager.is_operation_allowed("api_call")
            assert not manager.is_operation_allowed("file_delete")

    def test_config_persistence(self):
        """Test config persistence across instances"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "bypass_config.json"

            # Create manager and enable bypass
            manager1 = BypassManager(config_path)
            manager1.enable_bypass()
            manager1.config.allowed_operations = ["file_read"]
            manager1._save_config()

            # Create new manager instance
            manager2 = BypassManager(config_path)

            # Config should be loaded
            assert manager2.config.enabled is True
            assert "file_read" in manager2.config.allowed_operations

    def test_multiple_toggle_cycles(self):
        """Test multiple toggle cycles"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "bypass_config.json"
            manager = BypassManager(config_path)

            for _ in range(5):
                # Toggle on
                manager.toggle_bypass()
                assert manager.is_bypass_enabled()

                # Toggle off
                manager.toggle_bypass()
                assert not manager.is_bypass_enabled()

    def test_bypass_config_defaults(self):
        """Test BypassConfig default values"""
        config = BypassConfig()

        assert config.enabled is False
        assert config.auto_disable_after_minutes == 30
        assert config.allowed_operations == []

    def test_no_timeout_when_none(self):
        """Test that no timeout occurs when auto_disable_after_minutes is None"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "bypass_config.json"
            manager = BypassManager(config_path)
            manager.config.auto_disable_after_minutes = None

            # Enable bypass
            manager.enable_bypass()
            assert manager.is_bypass_enabled()

            # Wait a bit
            time.sleep(0.5)

            # Should still be enabled (no timeout)
            assert manager.is_bypass_enabled()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
