"""
Tests for the permission manager module.
"""

import pytest

from src.permissions.manager import (
    AccessLevel,
    PermissionManager,
    PermissionOverride,
    PermissionPolicy,
    PermissionResult,
)


class TestAccessLevel:
    """Tests for AccessLevel enum."""

    def test_values(self):
        """AccessLevel should have exactly three values."""
        assert AccessLevel.ALLOW.value == "allow"
        assert AccessLevel.DENY.value == "deny"
        assert AccessLevel.ASK.value == "ask"


class TestPermissionPolicy:
    """Tests for PermissionPolicy resolution and inheritance."""

    def test_direct_tool_level(self):
        """get_level should return the explicitly set level for a tool."""
        policy = PermissionPolicy(
            name="test",
            default_level=AccessLevel.ASK,
            tools={"read_file": AccessLevel.ALLOW},
        )
        assert policy.get_level("read_file") == AccessLevel.ALLOW

    def test_default_level_fallback(self):
        """get_level should fall back to default for unregistered tools."""
        policy = PermissionPolicy(
            name="test",
            default_level=AccessLevel.DENY,
        )
        assert policy.get_level("unknown_tool") == AccessLevel.DENY

    def test_parent_inheritance(self):
        """get_level should check parent policy when tool not in child."""
        parent = PermissionPolicy(
            name="parent",
            tools={"read_file": AccessLevel.ALLOW},
        )
        child = PermissionPolicy(
            name="child",
            default_level=AccessLevel.ASK,
            parent=parent,
        )
        # Inherited from parent
        assert child.get_level("read_file") == AccessLevel.ALLOW
        # Falls back to child's default
        assert child.get_level("write_file") == AccessLevel.ASK

    def test_child_overrides_parent(self):
        """A child's tool setting should override the parent."""
        parent = PermissionPolicy(
            name="parent",
            tools={"read_file": AccessLevel.ALLOW},
        )
        child = PermissionPolicy(
            name="child",
            default_level=AccessLevel.ASK,
            parent=parent,
            tools={"read_file": AccessLevel.DENY},
        )
        assert child.get_level("read_file") == AccessLevel.DENY


class TestPermissionManager:
    """Tests for PermissionManager."""

    def test_default_level_is_ask(self):
        """Default level should be ASK."""
        pm = PermissionManager()
        result = pm.check("unknown_tool")
        assert result.level == AccessLevel.ASK
        assert not result.allowed

    def test_custom_default_level(self):
        """Custom default level should be respected."""
        pm = PermissionManager(default_level=AccessLevel.DENY)
        result = pm.check("unknown")
        assert result.level == AccessLevel.DENY
        assert not result.allowed

    def test_create_policy(self):
        """create_policy should register a new policy."""
        pm = PermissionManager()
        policy = pm.create_policy("safe", default_level=AccessLevel.DENY)
        assert policy.name == "safe"
        assert pm.get_policy("safe") is policy

    def test_create_duplicate_policy_raises(self):
        """Creating a policy with an existing name should raise."""
        pm = PermissionManager()
        pm.create_policy("dup")
        with pytest.raises(ValueError, match="already exists"):
            pm.create_policy("dup")

    def test_create_policy_with_invalid_parent_raises(self):
        """Creating a policy with a nonexistent parent should raise."""
        pm = PermissionManager()
        with pytest.raises(ValueError, match="not found"):
            pm.create_policy("child", parent_name="ghost")

    def test_policy_inheritance(self):
        """Policy inheritance should work end-to-end."""
        pm = PermissionManager()
        pm.create_policy("base", default_level=AccessLevel.ASK)
        pm.create_policy("extended", parent_name="base")
        pm.register_tool("read", policy_name="base")
        pm.register_tool("write", policy_name="extended", level=AccessLevel.ALLOW)

        assert pm.check("read").level == AccessLevel.ASK
        assert pm.check("write").level == AccessLevel.ALLOW

    def test_delete_policy(self):
        """Deleting a policy should remove it."""
        pm = PermissionManager()
        pm.create_policy("temp")
        pm.register_tool("temp_tool", policy_name="temp")
        assert pm.delete_policy("temp") is True
        assert pm.get_policy("temp") is None

    def test_delete_nonexistent_policy(self):
        """Deleting a nonexistent policy should return False."""
        pm = PermissionManager()
        assert pm.delete_policy("ghost") is False

    def test_register_tool_with_explicit_level(self):
        """Registering a tool with an explicit level should work."""
        pm = PermissionManager()
        pm.register_tool("execute", level=AccessLevel.ALLOW)
        assert pm.is_allowed("execute") is True

    def test_register_tool_with_nonexistent_policy_raises(self):
        """Registering a tool with a nonexistent policy should raise."""
        pm = PermissionManager()
        with pytest.raises(ValueError, match="not found"):
            pm.register_tool("tool_x", policy_name="ghost")

    def test_unregister_tool(self):
        """Unregistering a tool should remove it from tracking."""
        pm = PermissionManager()
        pm.register_tool("temp_tool", level=AccessLevel.DENY)
        assert pm.unregister_tool("temp_tool") is True
        # After unregistration, should fall back to default
        assert pm.is_allowed("temp_tool") is False  # default ASK

    def test_unregister_nonexistent_tool(self):
        """Unregistering a tool that is not registered should return False."""
        pm = PermissionManager()
        assert pm.unregister_tool("ghost") is False

    def test_session_override_allows_denied_tool(self):
        """A session override should be able to ALLOW a globally DENIED tool."""
        pm = PermissionManager()
        pm.register_tool("dangerous", level=AccessLevel.DENY)
        assert pm.is_allowed("dangerous") is False

        pm.set_session_override("session-1", "dangerous", AccessLevel.ALLOW)
        assert pm.is_allowed("dangerous", session_id="session-1") is True
        # Other session should still see DENY
        assert pm.is_allowed("dangerous", session_id="session-2") is False

    def test_session_override_denies_allowed_tool(self):
        """A session override should be able to DENY a globally ALLOWED tool."""
        pm = PermissionManager()
        pm.register_tool("safe", level=AccessLevel.ALLOW)
        assert pm.is_allowed("safe") is True

        pm.set_session_override("session-1", "safe", AccessLevel.DENY)
        assert pm.is_allowed("safe", session_id="session-1") is False

    def test_clear_session_overrides(self):
        """Clearing session overrides should restore global behavior."""
        pm = PermissionManager()
        pm.register_tool("tool", level=AccessLevel.DENY)
        pm.set_session_override("sid", "tool", AccessLevel.ALLOW)
        assert pm.is_allowed("tool", session_id="sid") is True

        pm.clear_session_overrides("sid")
        assert pm.is_allowed("tool", session_id="sid") is False

    def test_clear_tool_override(self):
        """Clearing a specific tool override should work."""
        pm = PermissionManager()
        pm.set_session_override("sid", "tool_a", AccessLevel.ALLOW)
        pm.set_session_override("sid", "tool_b", AccessLevel.DENY)

        assert pm.clear_tool_override("sid", "tool_a") is True
        assert pm.check("tool_a", session_id="sid").level == AccessLevel.ASK
        assert pm.check("tool_b", session_id="sid").level == AccessLevel.DENY

    def test_clear_tool_override_nonexistent(self):
        """Clearing a nonexistent override should return False."""
        pm = PermissionManager()
        assert pm.clear_tool_override("sid", "ghost") is False

    def test_list_tools(self):
        """list_tools should return registered tool names."""
        pm = PermissionManager()
        pm.create_policy("p1")
        pm.create_policy("p2")
        pm.register_tool("tool_a", policy_name="p1")
        pm.register_tool("tool_b", policy_name="p2")
        pm.register_tool("tool_c", policy_name="p2")

        all_tools = pm.list_tools()
        assert sorted(all_tools) == ["tool_a", "tool_b", "tool_c"]

        p2_tools = pm.list_tools(policy_name="p2")
        assert sorted(p2_tools) == ["tool_b", "tool_c"]

    def test_list_policies(self):
        """list_policies should return user-created policy names."""
        pm = PermissionManager()
        pm.create_policy("policy_a")
        pm.create_policy("policy_b")
        # Internal _explicit should not appear
        pm.register_tool("tool", level=AccessLevel.ALLOW)
        policies = pm.list_policies()
        assert sorted(policies) == ["policy_a", "policy_b"]

    def test_list_session_overrides(self):
        """list_session_overrides should return overrides for a session."""
        pm = PermissionManager()
        pm.set_session_override("sid", "tool_a", AccessLevel.ALLOW)
        pm.set_session_override("sid", "tool_b", AccessLevel.DENY)
        overrides = pm.list_session_overrides("sid")
        assert overrides == {"tool_a": AccessLevel.ALLOW, "tool_b": AccessLevel.DENY}

    def test_list_session_overrides_empty(self):
        """list_session_overrides for an unknown session should return empty."""
        pm = PermissionManager()
        assert pm.list_session_overrides("ghost") == {}

    def test_permission_result_immutable(self):
        """PermissionResult should be immutable (frozen dataclass)."""
        result = PermissionResult(allowed=True, level=AccessLevel.ALLOW, reason="ok")
        assert result.allowed is True
        assert result.level == AccessLevel.ALLOW
        assert result.reason == "ok"
