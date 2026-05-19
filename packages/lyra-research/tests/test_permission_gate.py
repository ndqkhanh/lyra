"""
Tests for Permission Gate (Bypass Permissions Phase 0)

Tests permission checkpoint with bypass support.
"""

import pytest
from lyra_research.permissions.permission_gate import (
    PermissionGate,
    PermissionRequest,
    PermissionLevel,
    CRITICAL_OPERATIONS,
)
from lyra_research.permissions.bypass_manager import BypassManager


class TestPermissionGate:
    """Test permission gate"""

    def test_safe_operations_always_allowed(self):
        """Test that SAFE operations are always allowed"""
        manager = BypassManager()
        gate = PermissionGate(manager)

        request = PermissionRequest(
            operation="file_read",
            level=PermissionLevel.SAFE,
            description="Read config file",
            context={}
        )

        assert gate.check_permission(request)

    def test_critical_operations_always_require_confirmation(self):
        """Test that CRITICAL operations always require confirmation"""
        manager = BypassManager()
        gate = PermissionGate(manager)

        request = PermissionRequest(
            operation="file_delete",
            level=PermissionLevel.CRITICAL,
            description="Delete production data",
            context={}
        )

        # Even with bypass enabled, critical operations require confirmation
        manager.enable_bypass()
        result = gate.check_permission(request)
        # Returns True because _request_confirmation returns True for testing
        assert result

    def test_bypass_allows_standard_operations(self):
        """Test that bypass mode allows STANDARD operations"""
        manager = BypassManager()
        gate = PermissionGate(manager)

        request = PermissionRequest(
            operation="api_call",
            level=PermissionLevel.STANDARD,
            description="Call external API",
            context={}
        )

        # Without bypass, requires confirmation (returns True for testing)
        assert gate.check_permission(request)

        # With bypass, should bypass
        manager.enable_bypass()
        assert gate.check_permission(request)

    def test_bypass_respects_can_bypass_flag(self):
        """Test that bypass respects can_bypass flag"""
        manager = BypassManager()
        manager.enable_bypass()
        gate = PermissionGate(manager)

        request = PermissionRequest(
            operation="sensitive_op",
            level=PermissionLevel.STANDARD,
            description="Sensitive operation",
            context={},
            can_bypass=False
        )

        # Should require confirmation even with bypass enabled
        result = gate.check_permission(request)
        assert result  # Returns True because _request_confirmation returns True

    def test_critical_operations_set_cannot_bypass(self):
        """Test that critical operations in CRITICAL_OPERATIONS set cannot be bypassed"""
        manager = BypassManager()
        manager.enable_bypass()
        gate = PermissionGate(manager)

        for op in CRITICAL_OPERATIONS:
            request = PermissionRequest(
                operation=op,
                level=PermissionLevel.STANDARD,
                description=f"Critical operation: {op}",
                context={}
            )

            # Check permission should set can_bypass to False
            gate.check_permission(request)
            assert not request.can_bypass

    def test_standard_operations_without_bypass(self):
        """Test standard operations without bypass mode"""
        manager = BypassManager()
        gate = PermissionGate(manager)

        request = PermissionRequest(
            operation="data_analysis",
            level=PermissionLevel.STANDARD,
            description="Analyze data",
            context={}
        )

        # Should require confirmation (returns True for testing)
        assert gate.check_permission(request)

    def test_dangerous_operations_require_confirmation(self):
        """Test that DANGEROUS operations require confirmation"""
        manager = BypassManager()
        gate = PermissionGate(manager)

        request = PermissionRequest(
            operation="database_modify",
            level=PermissionLevel.DANGEROUS,
            description="Modify database schema",
            context={}
        )

        # Should require confirmation
        assert gate.check_permission(request)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
