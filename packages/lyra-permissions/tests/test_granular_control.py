"""Tests for granular permission control."""

import tempfile
from datetime import time
from pathlib import Path

import pytest

from lyra_permissions import (
    GranularController,
    PermissionDecision,
    PermissionLevel,
    PermissionManager,
    TimeBasedController,
    ToolPermission,
)


# Granular Controller Tests


def test_granular_controller_init():
    """Test granular controller initialization."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "granular.json"
        controller = GranularController(str(config_path))
        assert controller.current_profile == "default"


def test_granular_controller_profiles():
    """Test listing profiles."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "granular.json"
        controller = GranularController(str(config_path))

        profiles = controller.list_profiles()
        assert "default" in profiles
        assert "development" in profiles
        assert "production" in profiles


def test_granular_controller_set_profile():
    """Test setting profile."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "granular.json"
        controller = GranularController(str(config_path))

        controller.set_profile("development")
        assert controller.current_profile == "development"


def test_granular_controller_tool_permission():
    """Test tool-specific permission."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "granular.json"
        controller = GranularController(str(config_path))

        controller.set_profile("development")

        # Check configured permission
        decision = controller.check_tool_permission(
            "file_read", "read", PermissionLevel.SAFE
        )
        assert decision == PermissionDecision.ALLOW


def test_granular_controller_add_tool_permission():
    """Test adding tool permission."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "granular.json"
        controller = GranularController(str(config_path))

        controller.add_tool_permission(
            "custom_tool", "custom_op", ToolPermission.ALWAYS_ALLOW
        )

        decision = controller.check_tool_permission(
            "custom_tool", "custom_op", PermissionLevel.MEDIUM
        )
        assert decision == PermissionDecision.ALLOW


def test_granular_controller_context_rules():
    """Test context-aware rules."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "granular.json"
        controller = GranularController(str(config_path))

        controller.set_profile("development")

        # Check context rule for /tmp path
        decision = controller.check_context_rules({"path": "/tmp/test.txt"})
        assert decision == PermissionDecision.ALLOW


def test_granular_controller_add_context_rule():
    """Test adding context rule."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "granular.json"
        controller = GranularController(str(config_path))

        controller.add_context_rule(
            name="Test rule",
            condition={"path": {"startswith": "/test"}},
            decision="allow",
            priority=5,
        )

        decision = controller.check_context_rules({"path": "/test/file.txt"})
        assert decision == PermissionDecision.ALLOW


def test_granular_controller_context_rule_priority():
    """Test context rule priority."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "granular.json"
        controller = GranularController(str(config_path))

        # Add two rules with different priorities
        controller.add_context_rule(
            name="Low priority",
            condition={"path": {"startswith": "/test"}},
            decision="deny",
            priority=1,
        )

        controller.add_context_rule(
            name="High priority",
            condition={"path": {"startswith": "/test"}},
            decision="allow",
            priority=10,
        )

        # Higher priority rule should win
        decision = controller.check_context_rules({"path": "/test/file.txt"})
        assert decision == PermissionDecision.ALLOW


# Time-Based Controller Tests


def test_time_based_controller_init():
    """Test time-based controller initialization."""
    controller = TimeBasedController()
    assert len(controller.rules) == 0


def test_time_based_controller_add_rule():
    """Test adding time-based rule."""
    controller = TimeBasedController()

    controller.add_time_rule(
        start_time=time(9, 0),
        end_time=time(17, 0),
        decision=PermissionDecision.ALLOW,
        days=[0, 1, 2, 3, 4],  # Monday-Friday
    )

    assert len(controller.rules) == 1


def test_time_based_controller_work_hours():
    """Test work hours detection."""
    controller = TimeBasedController()

    # This test depends on current time, so we just check it returns a boolean
    is_work_hours = controller.is_work_hours()
    assert isinstance(is_work_hours, bool)


# Integration Tests


def test_permission_manager_granular_control():
    """Test permission manager with granular control."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = PermissionManager()
        manager.granular_controller = GranularController(str(Path(tmpdir) / "granular.json"))
        manager.bypass_mode.disable()

        # Set development profile
        manager.granular_controller.set_profile("development")

        # Check tool permission
        result = manager.check_permission("file_read", "read", {"path": "/tmp/test.txt"})

        # Should be allowed by tool permission or context rule
        assert result.allow is True


def test_permission_manager_context_rule():
    """Test permission manager with context rule."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = PermissionManager()
        manager.granular_controller = GranularController(str(Path(tmpdir) / "granular.json"))
        manager.bypass_mode.disable()

        # Add context rule
        manager.granular_controller.add_context_rule(
            name="Allow /tmp",
            condition={"path": {"startswith": "/tmp"}},
            decision="allow",
            priority=10,
        )

        # Check permission
        result = manager.check_permission("file_write", "write", {"path": "/tmp/test.txt"})

        assert result.allow is True
        assert "Context rule" in result.reason


def test_permission_manager_tool_permission():
    """Test permission manager with tool permission."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = PermissionManager()
        manager.granular_controller = GranularController(str(Path(tmpdir) / "granular.json"))
        manager.bypass_mode.disable()

        # Add tool permission
        manager.granular_controller.add_tool_permission(
            "custom_tool", "custom_op", ToolPermission.ALWAYS_ALLOW
        )

        # Check permission
        result = manager.check_permission("custom_tool", "custom_op", {})

        assert result.allow is True
        assert "Tool permission" in result.reason


def test_permission_manager_profile_switching():
    """Test switching between profiles."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = PermissionManager()
        manager.granular_controller = GranularController(str(Path(tmpdir) / "granular.json"))
        manager.bypass_mode.disable()

        # Development profile - more permissive
        manager.granular_controller.set_profile("development")
        result1 = manager.check_permission("file_write", "write", {"path": "/tmp/test.txt"})

        # Production profile - more restrictive
        manager.granular_controller.set_profile("production")
        result2 = manager.check_permission("file_write", "write", {"path": "/var/test.txt"})

        # Development should be more permissive
        assert result1.allow is True or result1.decision == PermissionDecision.PROMPT


def test_permission_manager_granular_priority():
    """Test granular control takes priority over bypass mode."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = PermissionManager()
        manager.granular_controller = GranularController(str(Path(tmpdir) / "granular.json"))
        manager.bypass_mode.enable()

        # Add context rule that denies
        manager.granular_controller.add_context_rule(
            name="Deny /sensitive",
            condition={"path": {"startswith": "/sensitive"}},
            decision="prompt",
            priority=100,
        )

        # Check permission - context rule should override bypass mode
        result = manager.check_permission(
            "file_write", "write", {"path": "/sensitive/data.txt"}
        )

        assert "Context rule" in result.reason
