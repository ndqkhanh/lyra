"""
Tests for Audit Logger (Bypass Permissions Phase 0)

Tests audit logging for bypassed operations.
"""

import tempfile
from pathlib import Path

import pytest
from lyra_research.permissions.audit_logger import (
    AuditEntry,
    AuditLogger,
)
from lyra_research.permissions.permission_gate import (
    PermissionLevel,
    PermissionRequest,
)


class TestAuditLogger:
    """Test audit logger"""

    def test_log_bypass_operation(self):
        """Test logging a bypassed operation"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "audit.jsonl"
            logger = AuditLogger(log_path)

            request = PermissionRequest(
                operation="api_call",
                level=PermissionLevel.STANDARD,
                description="Call external API",
                context={"endpoint": "/api/data"}
            )

            logger.log_bypass(request)

            # Check log file exists
            assert log_path.exists()

            # Check log content
            entries = logger.get_recent_bypasses(limit=10)
            assert len(entries) == 1
            assert entries[0].operation == "api_call"
            assert entries[0].level == "standard"
            assert entries[0].bypassed is True

    def test_get_recent_bypasses(self):
        """Test getting recent bypassed operations"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "audit.jsonl"
            logger = AuditLogger(log_path)

            # Log multiple operations
            for i in range(5):
                request = PermissionRequest(
                    operation=f"operation_{i}",
                    level=PermissionLevel.STANDARD,
                    description=f"Operation {i}",
                    context={}
                )
                logger.log_bypass(request)

            # Get recent bypasses
            entries = logger.get_recent_bypasses(limit=3)
            assert len(entries) == 3
            assert entries[-1].operation == "operation_4"

    def test_jsonl_format(self):
        """Test JSONL format"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "audit.jsonl"
            logger = AuditLogger(log_path)

            request = PermissionRequest(
                operation="test_op",
                level=PermissionLevel.STANDARD,
                description="Test operation",
                context={"key": "value"}
            )

            logger.log_bypass(request)

            # Read raw file
            with open(log_path) as f:
                lines = f.readlines()

            assert len(lines) == 1
            assert lines[0].strip().endswith("}")  # Valid JSON

    def test_log_persistence(self):
        """Test log persistence"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "audit.jsonl"

            # Create logger and log operation
            logger1 = AuditLogger(log_path)
            request = PermissionRequest(
                operation="persistent_op",
                level=PermissionLevel.STANDARD,
                description="Persistent operation",
                context={}
            )
            logger1.log_bypass(request)

            # Create new logger instance
            logger2 = AuditLogger(log_path)
            entries = logger2.get_recent_bypasses(limit=10)

            assert len(entries) == 1
            assert entries[0].operation == "persistent_op"

    def test_clear_log(self):
        """Test clearing audit log"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "audit.jsonl"
            logger = AuditLogger(log_path)

            # Log operation
            request = PermissionRequest(
                operation="test_op",
                level=PermissionLevel.STANDARD,
                description="Test operation",
                context={}
            )
            logger.log_bypass(request)

            assert log_path.exists()

            # Clear log
            logger.clear_log()

            assert not log_path.exists()

    def test_empty_log(self):
        """Test getting bypasses from empty log"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "audit.jsonl"
            logger = AuditLogger(log_path)

            entries = logger.get_recent_bypasses(limit=10)
            assert len(entries) == 0

    def test_audit_entry_dataclass(self):
        """Test AuditEntry dataclass"""
        entry = AuditEntry(
            timestamp="2026-05-20T10:00:00",
            operation="test_op",
            level="standard",
            description="Test",
            context={},
            bypassed=True
        )

        assert entry.operation == "test_op"
        assert entry.bypassed is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
