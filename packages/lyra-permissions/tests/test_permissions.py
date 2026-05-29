"""Tests for permission management system."""

import tempfile
from pathlib import Path

from lyra_permissions import (
    PermissionDecision,
    PermissionLevel,
    PermissionManager,
    PermissionPolicy,
    PermissionStore,
    PolicyEngine,
)

# Permission Manager Tests


def test_permission_manager_init():
    """Test permission manager initialization."""
    manager = PermissionManager()
    assert manager.policy_engine.policy == PermissionPolicy.BALANCED


def test_permission_manager_check_safe_operation():
    """Test checking safe operation."""
    manager = PermissionManager()

    result = manager.check_permission("file_read", "read", {"path": "/tmp/test.txt"})

    assert result.allow is True
    assert result.level == PermissionLevel.SAFE


def test_permission_manager_check_critical_operation():
    """Test checking critical operation."""
    manager = PermissionManager()

    result = manager.check_permission("database", "drop", {"table": "users"})

    assert result.allow is False
    assert result.level == PermissionLevel.CRITICAL
    assert result.decision == PermissionDecision.PROMPT


def test_permission_manager_assess_risk_critical():
    """Test risk assessment for critical operations."""
    manager = PermissionManager()

    risk = manager.assess_risk("file_delete", "delete", {"path": "/etc/passwd"})

    assert risk == PermissionLevel.CRITICAL


def test_permission_manager_assess_risk_dangerous():
    """Test risk assessment for dangerous operations."""
    manager = PermissionManager()

    risk = manager.assess_risk("script", "execute", {"script": "deploy.sh"})

    assert risk == PermissionLevel.DANGEROUS


def test_permission_manager_assess_risk_medium():
    """Test risk assessment for medium operations."""
    manager = PermissionManager()

    risk = manager.assess_risk("file_write", "write", {"path": "/tmp/output.txt"})

    assert risk == PermissionLevel.MEDIUM


def test_permission_manager_assess_risk_safe():
    """Test risk assessment for safe operations."""
    manager = PermissionManager()

    risk = manager.assess_risk("file_read", "read", {"path": "/tmp/data.txt"})

    assert risk == PermissionLevel.SAFE


def test_permission_manager_user_preference_allow():
    """Test user preference allows operation."""
    manager = PermissionManager()
    manager.bypass_mode.disable()  # Ensure bypass mode is off
    manager.granular_controller.set_profile("default")  # Use default profile (no context rules)
    manager.store.allow("file_write", "write")

    result = manager.check_permission("file_write", "write", {"path": "/tmp/test.txt"})

    assert result.allow is True
    assert "User preference" in result.reason


def test_permission_manager_user_preference_deny():
    """Test user preference denies operation."""
    manager = PermissionManager()
    manager.bypass_mode.disable()  # Ensure bypass mode is off
    manager.granular_controller.set_profile("default")  # Use default profile (no context rules)
    manager.store.deny("file_write", "write")

    result = manager.check_permission("file_write", "write", {"path": "/tmp/test.txt"})

    assert result.allow is False
    assert "User preference" in result.reason


def test_permission_manager_set_policy():
    """Test setting permission policy."""
    manager = PermissionManager()

    manager.set_policy(PermissionPolicy.PERMISSIVE)

    assert manager.get_policy() == PermissionPolicy.PERMISSIVE


# Permission Policy Tests


def test_policy_engine_init():
    """Test policy engine initialization."""
    engine = PolicyEngine()
    assert engine.policy == PermissionPolicy.BALANCED


def test_policy_engine_strict_policy():
    """Test strict policy."""
    engine = PolicyEngine(PermissionPolicy.STRICT)

    assert engine.apply_policy(PermissionLevel.SAFE) == PermissionDecision.ALLOW
    assert engine.apply_policy(PermissionLevel.MEDIUM) == PermissionDecision.PROMPT
    assert engine.apply_policy(PermissionLevel.DANGEROUS) == PermissionDecision.PROMPT
    assert engine.apply_policy(PermissionLevel.CRITICAL) == PermissionDecision.PROMPT


def test_policy_engine_balanced_policy():
    """Test balanced policy."""
    engine = PolicyEngine(PermissionPolicy.BALANCED)

    assert engine.apply_policy(PermissionLevel.SAFE) == PermissionDecision.ALLOW
    assert engine.apply_policy(PermissionLevel.MEDIUM) == PermissionDecision.ALLOW
    assert engine.apply_policy(PermissionLevel.DANGEROUS) == PermissionDecision.PROMPT
    assert engine.apply_policy(PermissionLevel.CRITICAL) == PermissionDecision.PROMPT


def test_policy_engine_permissive_policy():
    """Test permissive policy."""
    engine = PolicyEngine(PermissionPolicy.PERMISSIVE)

    assert engine.apply_policy(PermissionLevel.SAFE) == PermissionDecision.ALLOW
    assert engine.apply_policy(PermissionLevel.MEDIUM) == PermissionDecision.ALLOW
    assert engine.apply_policy(PermissionLevel.DANGEROUS) == PermissionDecision.ALLOW
    assert engine.apply_policy(PermissionLevel.CRITICAL) == PermissionDecision.PROMPT


def test_policy_engine_bypass_policy():
    """Test bypass policy."""
    engine = PolicyEngine(PermissionPolicy.BYPASS)

    assert engine.apply_policy(PermissionLevel.SAFE) == PermissionDecision.ALLOW
    assert engine.apply_policy(PermissionLevel.MEDIUM) == PermissionDecision.ALLOW
    assert engine.apply_policy(PermissionLevel.DANGEROUS) == PermissionDecision.ALLOW
    assert engine.apply_policy(PermissionLevel.CRITICAL) == PermissionDecision.ALLOW


def test_policy_engine_set_policy():
    """Test setting policy."""
    engine = PolicyEngine(PermissionPolicy.STRICT)

    engine.set_policy(PermissionPolicy.PERMISSIVE)

    assert engine.get_policy() == PermissionPolicy.PERMISSIVE


# Permission Store Tests


def test_permission_store_init():
    """Test permission store initialization."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store_path = Path(tmpdir) / "permissions.json"
        store = PermissionStore(str(store_path))

        assert store.store_path == store_path


def test_permission_store_allow():
    """Test adding to allow list."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store_path = Path(tmpdir) / "permissions.json"
        store = PermissionStore(str(store_path))

        store.allow("file_write", "write")

        assert store.is_allowed("file_write", "write")


def test_permission_store_deny():
    """Test adding to deny list."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store_path = Path(tmpdir) / "permissions.json"
        store = PermissionStore(str(store_path))

        store.deny("file_delete", "delete")

        assert store.is_denied("file_delete", "delete")


def test_permission_store_remove():
    """Test removing from lists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store_path = Path(tmpdir) / "permissions.json"
        store = PermissionStore(str(store_path))

        store.allow("file_write", "write")
        store.remove("file_write", "write")

        assert not store.is_allowed("file_write", "write")


def test_permission_store_persistence():
    """Test preference persistence."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store_path = Path(tmpdir) / "permissions.json"

        # Create store and add preference
        store1 = PermissionStore(str(store_path))
        store1.allow("file_write", "write")

        # Create new store and check persistence
        store2 = PermissionStore(str(store_path))
        assert store2.is_allowed("file_write", "write")


def test_permission_store_clear():
    """Test clearing all preferences."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store_path = Path(tmpdir) / "permissions.json"
        store = PermissionStore(str(store_path))

        store.allow("file_write", "write")
        store.deny("file_delete", "delete")
        store.clear()

        assert not store.is_allowed("file_write", "write")
        assert not store.is_denied("file_delete", "delete")


def test_permission_store_get_lists():
    """Test getting allow and deny lists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store_path = Path(tmpdir) / "permissions.json"
        store = PermissionStore(str(store_path))

        store.allow("file_write", "write")
        store.deny("file_delete", "delete")

        allow_list = store.get_allow_list()
        deny_list = store.get_deny_list()

        assert "file_write:write" in allow_list
        assert "file_delete:delete" in deny_list


def test_permission_store_cache():
    """Test session cache."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store_path = Path(tmpdir) / "permissions.json"
        store = PermissionStore(str(store_path))

        store.allow("file_write", "write")

        # First check loads from disk
        assert store.is_allowed("file_write", "write")

        # Second check uses cache
        assert ("file_write", "write") in store.cache
        assert store.is_allowed("file_write", "write")
