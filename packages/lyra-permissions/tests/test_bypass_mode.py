"""Tests for bypass mode functionality."""

import os
import tempfile
from pathlib import Path

from lyra_permissions import (
    AuditLogger,
    BypassMode,
    PermissionDecision,
    PermissionLevel,
    PermissionManager,
    SafetyGuardrails,
)

# Bypass Mode Tests


def test_bypass_mode_init():
    """Test bypass mode initialization."""
    bypass = BypassMode()
    assert isinstance(bypass.enabled, bool)


def test_bypass_mode_enable():
    """Test enabling bypass mode."""
    bypass = BypassMode()
    bypass.enable()
    assert bypass.is_enabled() is True


def test_bypass_mode_disable():
    """Test disabling bypass mode."""
    bypass = BypassMode()
    bypass.disable()
    assert bypass.is_enabled() is False


def test_bypass_mode_toggle():
    """Test toggling bypass mode."""
    bypass = BypassMode()
    initial_state = bypass.is_enabled()
    new_state = bypass.toggle()
    assert new_state != initial_state


def test_bypass_mode_status_indicator():
    """Test status indicator."""
    bypass = BypassMode()

    bypass.enable()
    assert bypass.get_status_indicator() == "[BYPASS MODE]"

    bypass.disable()
    assert bypass.get_status_indicator() == ""


def test_bypass_mode_env_var():
    """Test bypass mode from environment variable."""
    os.environ["LYRA_BYPASS_PERMISSIONS"] = "true"
    bypass = BypassMode()
    assert bypass.is_enabled() is True
    del os.environ["LYRA_BYPASS_PERMISSIONS"]


# Audit Logger Tests


def test_audit_logger_init():
    """Test audit logger initialization."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = Path(tmpdir) / "audit.log"
        logger = AuditLogger(str(log_path))
        assert logger.log_path == log_path


def test_audit_logger_log():
    """Test logging permission decision."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = Path(tmpdir) / "audit.log"
        logger = AuditLogger(str(log_path))

        logger.log(
            "file_write",
            "write",
            PermissionDecision.ALLOW,
            PermissionLevel.MEDIUM,
            {"path": "/tmp/test.txt"},
        )

        assert log_path.exists()


def test_audit_logger_get_recent():
    """Test getting recent audit entries."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = Path(tmpdir) / "audit.log"
        logger = AuditLogger(str(log_path))

        # Log multiple entries
        for i in range(5):
            logger.log(
                f"tool_{i}",
                "operation",
                PermissionDecision.ALLOW,
                PermissionLevel.SAFE,
            )

        entries = logger.get_recent(limit=10)
        assert len(entries) == 5


def test_audit_logger_get_stats():
    """Test getting audit statistics."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = Path(tmpdir) / "audit.log"
        logger = AuditLogger(str(log_path))

        # Log different decisions
        logger.log("tool1", "op1", PermissionDecision.ALLOW, PermissionLevel.SAFE)
        logger.log("tool2", "op2", PermissionDecision.PROMPT, PermissionLevel.DANGEROUS)
        logger.log("tool3", "op3", PermissionDecision.DENY, PermissionLevel.CRITICAL)

        stats = logger.get_stats()
        assert stats["total_entries"] == 3
        assert stats["auto_accepted"] == 1
        assert stats["prompted"] == 1
        assert stats["denied"] == 1


def test_audit_logger_clear():
    """Test clearing audit log."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = Path(tmpdir) / "audit.log"
        logger = AuditLogger(str(log_path))

        logger.log("tool", "op", PermissionDecision.ALLOW, PermissionLevel.SAFE)
        logger.clear()

        assert not log_path.exists()


def test_audit_logger_export_json():
    """Test exporting audit log as JSON."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = Path(tmpdir) / "audit.log"
        output_path = Path(tmpdir) / "export.json"
        logger = AuditLogger(str(log_path))

        logger.log("tool", "op", PermissionDecision.ALLOW, PermissionLevel.SAFE)

        success = logger.export(str(output_path), format="json")
        assert success is True
        assert output_path.exists()


# Safety Guardrails Tests


def test_safety_guardrails_critical_operation():
    """Test critical operation detection."""
    assert SafetyGuardrails.requires_confirmation("db", "drop", {}) is True
    assert SafetyGuardrails.requires_confirmation("git", "force_push", ) is True


def test_safety_guardrails_sensitive_path():
    """Test sensitive path detection."""
    assert (
        SafetyGuardrails.requires_confirmation("file", "write", {"path": "/etc/passwd"})
        is True
    )
    assert (
        SafetyGuardrails.requires_confirmation("file", "read", {"path": "/tmp/test.txt"})
        is False
    )


def test_safety_guardrails_force_operation():
    """Test force operation detection."""
    assert (
        SafetyGuardrails.requires_confirmation("git", "push", {"force": True}) is True
    )
    assert (
        SafetyGuardrails.requires_confirmation("git", "push", {"force": False}) is False
    )


def test_safety_guardrails_bulk_operation():
    """Test bulk operation detection."""
    assert (
        SafetyGuardrails.requires_confirmation("file", "delete", {"count": 20}) is True
    )
    assert (
        SafetyGuardrails.requires_confirmation("file", "delete", {"count": 5}) is False
    )


def test_safety_guardrails_warning_message():
    """Test warning message generation."""
    msg = SafetyGuardrails.get_warning_message("db", "drop", {})
    assert "CRITICAL" in msg
    assert "destructive" in msg


# Integration Tests


def test_permission_manager_bypass_mode():
    """Test permission manager with bypass mode."""
    manager = PermissionManager()

    # Enable bypass mode and use default profile (no context rules)
    manager.bypass_mode.enable()
    manager.granular_controller.set_profile("default")

    # Check medium risk operation (should be auto-accepted)
    result = manager.check_permission("file_write", "write", {"path": "/tmp/test.txt"})

    assert result.allow is True
    assert "Bypass mode" in result.reason


def test_permission_manager_bypass_mode_critical():
    """Test bypass mode doesn't bypass critical operations."""
    manager = PermissionManager()

    # Enable bypass mode
    manager.bypass_mode.enable()

    # Check critical operation (should still prompt)
    result = manager.check_permission("database", "drop", {"table": "users"})

    assert result.allow is False
    assert result.decision == PermissionDecision.PROMPT


def test_permission_manager_audit_logging():
    """Test audit logging integration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = PermissionManager()
        manager.audit_logger = AuditLogger(str(Path(tmpdir) / "audit.log"))

        # Perform operation
        manager.check_permission("file_read", "read", {"path": "/tmp/test.txt"})

        # Check audit log
        entries = manager.audit_logger.get_recent()
        assert len(entries) == 1
        assert entries[0]["tool"] == "file_read"


def test_permission_manager_safety_guardrails():
    """Test safety guardrails integration."""
    manager = PermissionManager()
    manager.bypass_mode.enable()

    # Try sensitive path operation
    result = manager.check_permission("file_write", "write", {"path": "/etc/passwd"})

    # Should require confirmation despite bypass mode
    assert result.allow is False
    assert result.decision == PermissionDecision.PROMPT
