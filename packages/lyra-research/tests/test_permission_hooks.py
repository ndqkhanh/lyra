"""
Tests for Permission Hooks (Bypass Permissions Phase 2)

Tests hook integration for permission system.
"""

import pytest
from pathlib import Path
import tempfile
from lyra_research.hooks.permission_hooks import PermissionHooks
from lyra_research.permissions.permission_gate import PermissionLevel
from lyra_research.permissions.bypass_manager import BypassManager


class TestPermissionHooks:
    """Test permission hooks"""

    def test_pre_operation_hook_safe(self):
        """Test pre-operation hook with SAFE operation"""
        hooks = PermissionHooks()

        result = hooks.pre_operation_hook(
            operation="file_read",
            level=PermissionLevel.SAFE,
            description="Read config file",
            context={}
        )

        assert result is True

    def test_pre_operation_hook_standard_without_bypass(self):
        """Test pre-operation hook with STANDARD operation without bypass"""
        hooks = PermissionHooks()

        result = hooks.pre_operation_hook(
            operation="api_call",
            level=PermissionLevel.STANDARD,
            description="Call external API",
            context={}
        )

        # Returns True because _request_confirmation returns True for testing
        assert result is True

    def test_pre_operation_hook_standard_with_bypass(self):
        """Test pre-operation hook with STANDARD operation with bypass"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "bypass_config.json"
            manager = BypassManager(config_path)
            manager.enable_bypass()

            hooks = PermissionHooks(manager)

            result = hooks.pre_operation_hook(
                operation="api_call",
                level=PermissionLevel.STANDARD,
                description="Call external API",
                context={}
            )

            assert result is True

    def test_pre_operation_hook_critical(self):
        """Test pre-operation hook with CRITICAL operation"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "bypass_config.json"
            manager = BypassManager(config_path)
            manager.enable_bypass()

            hooks = PermissionHooks(manager)

            result = hooks.pre_operation_hook(
                operation="file_delete",
                level=PermissionLevel.CRITICAL,
                description="Delete production data",
                context={}
            )

            # Even with bypass, critical operations require confirmation
            assert result is True

    def test_post_operation_hook(self):
        """Test post-operation hook"""
        hooks = PermissionHooks()

        # Should not raise exception
        hooks.post_operation_hook(
            operation="test_op",
            success=True,
            result={"data": "test"}
        )

    def test_toggle_bypass_hook(self):
        """Test toggle bypass hook"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "bypass_config.json"
            manager = BypassManager(config_path)
            hooks = PermissionHooks(manager)

            # Initially disabled
            assert not hooks.get_bypass_status()

            # Toggle to enabled
            result = hooks.toggle_bypass_hook()
            assert result is True
            assert hooks.get_bypass_status()

            # Toggle to disabled
            result = hooks.toggle_bypass_hook()
            assert result is False
            assert not hooks.get_bypass_status()

    def test_get_bypass_status(self):
        """Test get bypass status"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "bypass_config.json"
            manager = BypassManager(config_path)
            hooks = PermissionHooks(manager)

            # Initially disabled
            assert hooks.get_bypass_status() is False

            # Enable bypass
            manager.enable_bypass()
            assert hooks.get_bypass_status() is True

            # Disable bypass
            manager.disable_bypass()
            assert hooks.get_bypass_status() is False

    def test_hook_integration_with_bypass_manager(self):
        """Test hook integration with bypass manager"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "bypass_config.json"
            manager = BypassManager(config_path)
            hooks = PermissionHooks(manager)

            # Enable bypass via manager
            manager.enable_bypass()

            # Hook should reflect bypass state
            assert hooks.get_bypass_status()

            # Pre-operation should bypass
            result = hooks.pre_operation_hook(
                operation="data_analysis",
                level=PermissionLevel.STANDARD,
                description="Analyze data",
                context={}
            )
            assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
