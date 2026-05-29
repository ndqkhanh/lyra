"""
Integration Tests for Bypass Permissions (Phase 4)

Tests complete bypass workflow with security boundaries.
"""

import tempfile
import time
from pathlib import Path

import pytest
from lyra_research.permissions.audit_logger import AuditLogger
from lyra_research.permissions.bypass_manager import BypassManager
from lyra_research.permissions.permission_gate import (
    CRITICAL_OPERATIONS,
    PermissionGate,
    PermissionLevel,
    PermissionRequest,
)


class TestBypassIntegration:
    """Test bypass permissions integration"""

    def test_full_bypass_workflow(self):
        """Test complete bypass workflow"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "bypass_config.json"
            manager = BypassManager(config_path)
            gate = PermissionGate(manager)

            # Start with bypass disabled
            assert not manager.is_bypass_enabled()

            # Standard operation requires confirmation
            request = PermissionRequest(
                operation="file_read",
                level=PermissionLevel.STANDARD,
                description="Read config file",
                context={}
            )
            # Would require confirmation (mocked as True)
            assert gate.check_permission(request)

            # Enable bypass
            manager.enable_bypass()
            assert manager.is_bypass_enabled()

            # Same operation now bypasses
            allowed = gate.check_permission(request)
            assert allowed

    def test_bypass_with_audit_trail(self):
        """Test that bypassed operations are logged"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "bypass_config.json"
            log_path = Path(tmpdir) / "audit.jsonl"

            logger = AuditLogger(log_path)
            manager = BypassManager(config_path, audit_logger=logger)
            gate = PermissionGate(manager)

            # Clear previous logs
            logger.clear_log()

            # Enable bypass
            manager.enable_bypass()

            # Perform bypassed operation
            request = PermissionRequest(
                operation="api_call",
                level=PermissionLevel.STANDARD,
                description="Call external API",
                context={"endpoint": "/api/data"}
            )
            gate.check_permission(request)

            # Check audit log
            entries = logger.get_recent_bypasses(limit=10)
            assert len(entries) == 1
            assert entries[0].operation == "api_call"
            assert entries[0].bypassed is True

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

    def test_critical_operation_blocking(self):
        """Test that critical operations cannot be bypassed"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "bypass_config.json"
            manager = BypassManager(config_path)
            manager.enable_bypass()

            gate = PermissionGate(manager)

            # Test each critical operation
            for op in CRITICAL_OPERATIONS:
                request = PermissionRequest(
                    operation=op,
                    level=PermissionLevel.STANDARD,
                    description=f"Critical: {op}",
                    context={}
                )

                # Should set can_bypass to False
                gate.check_permission(request)
                assert not request.can_bypass

    def test_config_persistence_across_restarts(self):
        """Test config persistence across manager restarts"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "bypass_config.json"

            # Create manager and enable bypass
            manager1 = BypassManager(config_path)
            manager1.enable_bypass()
            manager1.config.allowed_operations = ["file_read", "api_call"]
            manager1._save_config()

            # Create new manager instance (simulates restart)
            manager2 = BypassManager(config_path)

            # Config should be loaded
            assert manager2.config.enabled is True
            assert "file_read" in manager2.config.allowed_operations
            assert "api_call" in manager2.config.allowed_operations

    def test_multiple_concurrent_operations(self):
        """Test multiple concurrent operations with bypass"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "bypass_config.json"
            log_path = Path(tmpdir) / "audit.jsonl"

            logger = AuditLogger(log_path)
            manager = BypassManager(config_path, audit_logger=logger)
            manager.enable_bypass()

            gate = PermissionGate(manager)
            logger.clear_log()

            # Perform multiple operations
            operations = ["op1", "op2", "op3", "op4", "op5"]
            for op in operations:
                request = PermissionRequest(
                    operation=op,
                    level=PermissionLevel.STANDARD,
                    description=f"Operation {op}",
                    context={}
                )
                gate.check_permission(request)

            # All should be logged
            entries = logger.get_recent_bypasses(limit=10)
            assert len(entries) == 5
            logged_ops = [e.operation for e in entries]
            assert set(logged_ops) == set(operations)

    def test_whitelist_enforcement(self):
        """Test operation whitelist enforcement"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "bypass_config.json"
            manager = BypassManager(config_path)
            manager.config.allowed_operations = ["file_read"]
            manager.enable_bypass()

            # Whitelisted operation
            assert manager.is_operation_allowed("file_read")

            # Non-whitelisted operation
            assert not manager.is_operation_allowed("file_delete")

    def test_security_boundary_testing(self):
        """Test security boundaries"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "bypass_config.json"
            manager = BypassManager(config_path)
            manager.enable_bypass()

            gate = PermissionGate(manager)

            # SAFE operations always allowed
            safe_request = PermissionRequest(
                operation="read_only",
                level=PermissionLevel.SAFE,
                description="Safe read operation",
                context={}
            )
            assert gate.check_permission(safe_request)

            # CRITICAL operations require confirmation even with bypass
            critical_request = PermissionRequest(
                operation="production_deploy",
                level=PermissionLevel.CRITICAL,
                description="Deploy to production",
                context={}
            )
            # Returns True because _request_confirmation returns True for testing
            assert gate.check_permission(critical_request)
            assert not critical_request.can_bypass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
