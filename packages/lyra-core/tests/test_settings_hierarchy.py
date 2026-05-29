"""Dedicated tests for config/settings_hierarchy.py."""

from __future__ import annotations

import json
import os
import tempfile

import pytest
from lyra_core.config.settings_hierarchy import (
    LockedSettingError,
    ManagedPolicy,
    PolicyRule,
    PolicyViolationError,
    SettingOverride,
    SettingScope,
    SettingsError,
    SettingsHierarchy,
    SettingValue,
)


class TestSettingScope:
    def test_priority_ordering(self):
        assert SettingScope.MANAGED.value < SettingScope.CLI.value
        assert SettingScope.CLI.value < SettingScope.LOCAL.value
        assert SettingScope.LOCAL.value < SettingScope.PROJECT.value
        assert SettingScope.PROJECT.value < SettingScope.USER.value


class TestSettingValue:
    def test_create(self):
        sv = SettingValue(value="dark", source=SettingScope.USER)
        assert sv.value == "dark"
        assert sv.source == SettingScope.USER
        assert sv.is_locked is False
        assert sv.description == ""

    def test_create_locked(self):
        sv = SettingValue(
            value="dark",
            source=SettingScope.MANAGED,
            is_locked=True,
            description="Theme setting",
        )
        assert sv.is_locked is True
        assert sv.description == "Theme setting"

    def test_is_frozen(self):
        sv = SettingValue(value="x", source=SettingScope.USER)
        with pytest.raises(Exception):  # noqa: B017
            sv.value = "y"  # type: ignore[misc]


class TestSettingOverride:
    def test_create(self):
        sv = SettingValue(value=42, source=SettingScope.PROJECT)
        override = SettingOverride(key="timeout", value=sv, reason="Project default")
        assert override.key == "timeout"
        assert override.value.value == 42
        assert override.reason == "Project default"

    def test_is_frozen(self):
        sv = SettingValue(value=1, source=SettingScope.USER)
        override = SettingOverride(key="k", value=sv)
        with pytest.raises(Exception):  # noqa: B017
            override.key = "other"  # type: ignore[misc]


class TestPolicyRule:
    def test_create(self):
        rule = PolicyRule(
            key_pattern="theme.*",
            allowed_values=("light", "dark"),
            deny_message="Must be light or dark",
        )
        assert rule.key_pattern == "theme.*"
        assert rule.allowed_values == ("light", "dark")

    def test_is_frozen(self):
        rule = PolicyRule(key_pattern="*", allowed_values=("a",))
        with pytest.raises(Exception):  # noqa: B017
            rule.key_pattern = "other"  # type: ignore[misc]


class TestManagedPolicy:
    def test_create(self):
        rule = PolicyRule(key_pattern="theme", allowed_values=("light", "dark"))
        policy = ManagedPolicy(
            policy_id="ui-policy",
            rules=(rule,),
            description="UI restrictions",
        )
        assert policy.policy_id == "ui-policy"
        assert len(policy.rules) == 1
        assert policy.description == "UI restrictions"

    def test_is_frozen(self):
        policy = ManagedPolicy(policy_id="p1", rules=())
        with pytest.raises(Exception):  # noqa: B017
            policy.policy_id = "p2"  # type: ignore[misc]


class TestSettingsHierarchy:
    @pytest.fixture
    def hierarchy(self):
        return SettingsHierarchy()

    def test_set_and_get_value(self, hierarchy):
        hierarchy.set_value("theme", "dark", SettingScope.USER)
        sv = hierarchy.get_value("theme")
        assert sv is not None
        assert sv.value == "dark"

    def test_get_missing_key(self, hierarchy):
        assert hierarchy.get_value("nonexistent") is None

    def test_get_effective_value(self, hierarchy):
        hierarchy.set_value("theme", "dark", SettingScope.USER)
        assert hierarchy.get_effective_value("theme") == "dark"

    def test_get_effective_value_missing(self, hierarchy):
        assert hierarchy.get_effective_value("missing") is None

    def test_scope_priority(self, hierarchy):
        hierarchy.set_value("theme", "dark", SettingScope.USER)
        hierarchy.set_value("theme", "light", SettingScope.CLI)
        sv = hierarchy.get_value("theme")
        assert sv is not None
        assert sv.value == "light"

    def test_managed_has_highest_priority(self, hierarchy):
        hierarchy.set_value("timeout", 30, SettingScope.USER)
        hierarchy.set_value("timeout", 60, SettingScope.CLI)
        hierarchy.set_value("timeout", 10, SettingScope.MANAGED)
        assert hierarchy.get_effective_value("timeout") == 10

    def test_delete_value(self, hierarchy):
        hierarchy.set_value("theme", "dark", SettingScope.USER)
        assert hierarchy.delete_value("theme", SettingScope.USER) is True
        assert hierarchy.get_value("theme") is None

    def test_delete_missing(self, hierarchy):
        assert hierarchy.delete_value("nope", SettingScope.USER) is False

    def test_delete_falls_back_to_lower(self, hierarchy):
        hierarchy.set_value("theme", "dark", SettingScope.USER)
        hierarchy.set_value("theme", "light", SettingScope.PROJECT)
        hierarchy.delete_value("theme", SettingScope.PROJECT)
        assert hierarchy.get_effective_value("theme") == "dark"

    def test_lock_value(self, hierarchy):
        hierarchy.set_value("api_key", "secret", SettingScope.MANAGED)
        locked = hierarchy.lock_value("api_key", SettingScope.MANAGED)
        assert locked.is_locked is True

    def test_lock_missing_raises(self, hierarchy):
        with pytest.raises(SettingsError, match="Cannot lock"):
            hierarchy.lock_value("nope", SettingScope.USER)

    def test_locked_prevents_override(self, hierarchy):
        hierarchy.set_value("api_key", "secret", SettingScope.MANAGED)
        hierarchy.lock_value("api_key", SettingScope.MANAGED)
        with pytest.raises(LockedSettingError, match="locked by MANAGED"):
            hierarchy.set_value("api_key", "override", SettingScope.USER)

    def test_locked_prevents_delete(self, hierarchy):
        hierarchy.set_value("api_key", "secret", SettingScope.MANAGED)
        hierarchy.lock_value("api_key", SettingScope.MANAGED)
        with pytest.raises(LockedSettingError):
            hierarchy.delete_value("api_key", SettingScope.USER)

    def test_locked_at_same_scope_allowed(self, hierarchy):
        hierarchy.set_value("k", "v1", SettingScope.USER)
        hierarchy.lock_value("k", SettingScope.USER)
        hierarchy.set_value("k", "v2", SettingScope.USER)
        assert hierarchy.get_effective_value("k") == "v2"

    def test_check_policy_allowed(self, hierarchy):
        rule = PolicyRule(
            key_pattern="theme",
            allowed_values=("light", "dark"),
        )
        policy = ManagedPolicy(policy_id="p1", rules=(rule,))
        hierarchy.apply_managed_policy(policy)
        allowed, msg = hierarchy.check_policy("theme", "light")
        assert allowed is True
        assert msg == ""

    def test_check_policy_denied(self, hierarchy):
        rule = PolicyRule(
            key_pattern="theme",
            allowed_values=("light", "dark"),
            deny_message="Bad theme",
        )
        policy = ManagedPolicy(policy_id="p1", rules=(rule,))
        hierarchy.apply_managed_policy(policy)
        allowed, msg = hierarchy.check_policy("theme", "neon")
        assert allowed is False
        assert msg == "Bad theme"

    def test_check_policy_no_match(self, hierarchy):
        rule = PolicyRule(key_pattern="theme", allowed_values=("light",))
        policy = ManagedPolicy(policy_id="p1", rules=(rule,))
        hierarchy.apply_managed_policy(policy)
        allowed, _ = hierarchy.check_policy("editor.font_size", 14)
        assert allowed is True

    def test_check_policy_glob_pattern(self, hierarchy):
        rule = PolicyRule(key_pattern="editor.*", allowed_values=(12, 14, 16))
        policy = ManagedPolicy(policy_id="p1", rules=(rule,))
        hierarchy.apply_managed_policy(policy)
        allowed, _ = hierarchy.check_policy("editor.font_size", 14)
        assert allowed is True
        denied, _ = hierarchy.check_policy("editor.font_size", 8)
        assert denied is False

    def test_policy_denies_managed_set(self, hierarchy):
        rule = PolicyRule(key_pattern="theme", allowed_values=("light",))
        policy = ManagedPolicy(policy_id="p1", rules=(rule,))
        hierarchy.apply_managed_policy(policy)
        with pytest.raises(PolicyViolationError):
            hierarchy.set_value("theme", "neon", SettingScope.MANAGED)

    def test_export_settings(self, hierarchy):
        hierarchy.set_value("k1", "v1", SettingScope.USER)
        hierarchy.set_value("k2", "v2", SettingScope.PROJECT)
        hierarchy.set_value("k3", "v3", SettingScope.CLI)
        exported = hierarchy.export_settings(SettingScope.PROJECT)
        assert "k2" in exported
        assert "k3" in exported

    def test_list_overrides(self, hierarchy):
        hierarchy.set_value("theme", "dark", SettingScope.USER)
        hierarchy.set_value("theme", "light", SettingScope.PROJECT)
        overrides = hierarchy.list_overrides("theme")
        assert len(overrides) == 2
        assert overrides[0].value.source == SettingScope.PROJECT

    def test_list_overrides_empty_key(self, hierarchy):
        assert hierarchy.list_overrides("missing") == []

    def test_clear_scope(self, hierarchy):
        hierarchy.set_value("k1", "v1", SettingScope.USER)
        hierarchy.set_value("k2", "v2", SettingScope.USER)
        removed = hierarchy.clear_scope(SettingScope.USER)
        assert removed == 2
        assert hierarchy.get_value("k1") is None

    def test_load_policy_fragment_json(self, hierarchy):
        data = {
            "policy_id": "test-policy",
            "description": "Test policy",
            "rules": [
                {
                    "key_pattern": "theme",
                    "allowed_values": ["light", "dark"],
                    "deny_message": "Invalid theme",
                }
            ],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            fpath = f.name
        try:
            policy = hierarchy.load_policy_fragment(fpath)
            assert policy.policy_id == "test-policy"
            assert len(policy.rules) == 1
        finally:
            os.unlink(fpath)

    def test_load_policy_fragment_unsupported_format(self, hierarchy):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("hello")
            fpath = f.name
        try:
            with pytest.raises(ValueError, match="Unsupported"):
                hierarchy.load_policy_fragment(fpath)
        finally:
            os.unlink(fpath)

    def test_scope_hierarchy_is_correct(self, hierarchy):
        hierarchy.set_value("k", "managed", SettingScope.MANAGED)
        hierarchy.set_value("k", "cli", SettingScope.CLI)
        hierarchy.set_value("k", "local", SettingScope.LOCAL)
        hierarchy.set_value("k", "project", SettingScope.PROJECT)
        hierarchy.set_value("k", "user", SettingScope.USER)
        assert hierarchy.get_effective_value("k") == "managed"

        hierarchy.delete_value("k", SettingScope.MANAGED)
        assert hierarchy.get_effective_value("k") == "cli"
        hierarchy.delete_value("k", SettingScope.CLI)
        assert hierarchy.get_effective_value("k") == "local"
        hierarchy.delete_value("k", SettingScope.LOCAL)
        assert hierarchy.get_effective_value("k") == "project"
        hierarchy.delete_value("k", SettingScope.PROJECT)
        assert hierarchy.get_effective_value("k") == "user"

    def test_multiple_policies_fifo_order(self, hierarchy):
        policy1 = ManagedPolicy(
            policy_id="p1",
            rules=(PolicyRule(key_pattern="k", allowed_values=("a", "b"), deny_message="P1 deny"),),
        )
        policy2 = ManagedPolicy(
            policy_id="p2",
            rules=(PolicyRule(key_pattern="k", allowed_values=("a", "c"), deny_message="P2 deny"),),
        )
        hierarchy.apply_managed_policy(policy1)
        hierarchy.apply_managed_policy(policy2)
        allowed, _ = hierarchy.check_policy("k", "a")
        assert allowed is True
        denied, msg = hierarchy.check_policy("k", "b")
        assert denied is False
        assert msg == "P2 deny"

    def test_description_on_set_value(self, hierarchy):
        hierarchy.set_value("k", "v", SettingScope.USER, description="A test setting")
        sv = hierarchy.get_value("k")
        assert sv is not None
        assert sv.description == "A test setting"
