"""Tests for Plugin Manifest — schema, validation, lifecycle."""
from __future__ import annotations

import pytest

from lyra_harness_core.plugins.manifest import (
    DependencySpec,
    HookBinding,
    PluginInstance,
    PluginLifecycle,
    PluginManifest,
    SandboxConfig,
    SemVer,
    ToolDeclaration,
    check_version_constraint,
    load_manifest_from_yaml,
    parse_manifest,
)
from lyra_harness_core.tools import RiskLevel, ToolAnnotation, ToolCategory


# ---------------------------------------------------------------------------
# SemVer
# ---------------------------------------------------------------------------


class TestSemVer:
    def test_parse_simple(self):
        v = SemVer.parse("1.2.3")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3

    def test_parse_with_pre(self):
        v = SemVer.parse("2.0.0-alpha.1")
        assert v.pre == "alpha.1"

    def test_parse_with_build(self):
        v = SemVer.parse("1.0.0+build.123")
        assert v.build == "build.123"

    def test_parse_with_pre_and_build(self):
        v = SemVer.parse("1.0.0-rc.2+build.5")
        assert v.pre == "rc.2"
        assert v.build == "build.5"

    def test_parse_invalid_raises(self):
        with pytest.raises(ValueError):
            SemVer.parse("not-a-version")

    def test_parse_leading_v_raises(self):
        with pytest.raises(ValueError):
            SemVer.parse("v1.2.3")

    def test_str_simple(self):
        assert str(SemVer.parse("1.2.3")) == "1.2.3"

    def test_comparison_ordering(self):
        v1 = SemVer.parse("1.0.0")
        v2 = SemVer.parse("1.1.0")
        v3 = SemVer.parse("2.0.0")
        assert v1 < v2 < v3

    def test_equality(self):
        v1 = SemVer.parse("1.2.3")
        v2 = SemVer.parse("1.2.3")
        assert v1 == v2

    def test_total_ordering_operators(self):
        v1 = SemVer.parse("1.0.0")
        v2 = SemVer.parse("1.1.0")
        assert v1 <= v2
        assert v2 >= v1
        assert v2 > v1
        assert v1 != v2
        assert v1 <= v1
        assert v1 >= v1

    def test_frozen(self):
        v = SemVer.parse("1.2.3")
        with pytest.raises(Exception):
            v.major = 2  # type: ignore[misc]


# ---------------------------------------------------------------------------
# check_version_constraint
# ---------------------------------------------------------------------------


class TestCheckVersionConstraint:
    def test_exact_match(self):
        v = SemVer.parse("1.2.3")
        assert check_version_constraint(v, "== 1.2.3")
        assert not check_version_constraint(v, "== 1.2.4")

    def test_gte(self):
        v = SemVer.parse("2.0.0")
        assert check_version_constraint(v, ">= 1.0.0")
        assert check_version_constraint(v, ">= 2.0.0")
        assert not check_version_constraint(v, ">= 3.0.0")

    def test_lte(self):
        v = SemVer.parse("1.5.0")
        assert check_version_constraint(v, "<= 2.0.0")
        assert check_version_constraint(v, "<= 1.5.0")
        assert not check_version_constraint(v, "<= 1.0.0")

    def test_gt(self):
        v = SemVer.parse("1.1.0")
        assert check_version_constraint(v, "> 1.0.0")
        assert not check_version_constraint(v, "> 1.1.0")

    def test_lt(self):
        v = SemVer.parse("1.0.0")
        assert check_version_constraint(v, "< 2.0.0")
        assert not check_version_constraint(v, "< 1.0.0")

    def test_not_equal(self):
        v = SemVer.parse("1.0.0")
        assert check_version_constraint(v, "!= 2.0.0")
        assert not check_version_constraint(v, "!= 1.0.0")

    def test_pessimistic_major(self):
        v = SemVer.parse("2.3.1")
        assert check_version_constraint(v, "~> 2.3.0")
        v2 = SemVer.parse("3.0.0")
        assert not check_version_constraint(v2, "~> 2.3.0")

    def test_pessimistic_zero_major(self):
        v = SemVer.parse("0.3.1")
        assert check_version_constraint(v, "~> 0.3.0")
        v2 = SemVer.parse("0.4.0")
        assert not check_version_constraint(v2, "~> 0.3.0")

    def test_invalid_constraint_raises(self):
        v = SemVer.parse("1.0.0")
        with pytest.raises(ValueError):
            check_version_constraint(v, "=> 1.0.0")


# ---------------------------------------------------------------------------
# PluginLifecycle
# ---------------------------------------------------------------------------


class TestPluginLifecycle:
    def test_enum_values(self):
        assert PluginLifecycle.INSTALLED.value == "installed"
        assert PluginLifecycle.CONFIGURED.value == "configured"
        assert PluginLifecycle.ENABLED.value == "enabled"
        assert PluginLifecycle.DISABLED.value == "disabled"
        assert PluginLifecycle.UNINSTALLED.value == "uninstalled"
        assert PluginLifecycle.ERROR.value == "error"


# ---------------------------------------------------------------------------
# parse_manifest
# ---------------------------------------------------------------------------


_MINIMAL_MANIFEST = {"name": "test-plugin", "version": "1.0.0"}

_FULL_MANIFEST = {
    "name": "lyra-plugin-research",
    "version": "1.2.0",
    "lyra_version": ">=7.2.0",
    "author": "lyra-community",
    "license": "MIT",
    "description": "Deep research plugin with multi-hop reasoning",
    "hooks": [
        {"event": "session.start", "handler": "research.init_session"},
        {"event": "tool.pre_execute", "handler": "research.validate_sources"},
    ],
    "tools": [
        {"name": "deep_search", "annotations": {"read_only": True, "network_access": True}},
    ],
    "dependencies": [
        {"package": "arxiv", "constraint": ">=2.0"},
        {"package": "scholarly", "constraint": ">=1.7"},
    ],
    "sandbox": {
        "network": ["api.semanticscholar.org", "api.openalex.org"],
        "filesystem": ["~/.lyra/cache/research/"],
    },
}


class TestParseManifest:
    def test_minimal_manifest(self):
        m = parse_manifest(_MINIMAL_MANIFEST)
        assert m.name == "test-plugin"
        assert str(m.version) == "1.0.0"
        assert m.author == ""
        assert m.license == "MIT"
        assert m.description == ""

    def test_full_manifest(self):
        m = parse_manifest(_FULL_MANIFEST)
        assert m.name == "lyra-plugin-research"
        assert m.version == SemVer.parse("1.2.0")
        assert m.author == "lyra-community"
        assert m.description == "Deep research plugin with multi-hop reasoning"

    def test_hooks_parsed(self):
        m = parse_manifest(_FULL_MANIFEST)
        assert len(m.hooks) == 2
        assert m.hooks[0].event == "session.start"
        assert m.hooks[0].handler == "research.init_session"

    def test_tools_parsed(self):
        m = parse_manifest(_FULL_MANIFEST)
        assert len(m.tools) == 1
        assert m.tools[0].name == "deep_search"
        assert m.tools[0].annotations.read_only is True
        assert m.tools[0].annotations.network_access is True

    def test_dependencies_parsed(self):
        m = parse_manifest(_FULL_MANIFEST)
        assert len(m.dependencies) == 2
        assert m.dependencies[0].package == "arxiv"
        assert m.dependencies[0].constraint == ">=2.0"

    def test_dependencies_string_form(self):
        raw = {"name": "p", "version": "1.0.0", "dependencies": ["numpy", "pandas"]}
        m = parse_manifest(raw)
        assert len(m.dependencies) == 2
        assert m.dependencies[0].package == "numpy"
        assert m.dependencies[0].constraint == ""

    def test_sandbox_parsed(self):
        m = parse_manifest(_FULL_MANIFEST)
        assert "api.semanticscholar.org" in m.sandbox.network_allowlist
        assert "~/.lyra/cache/research/" in m.sandbox.filesystem_allowlist
        assert m.sandbox.read_only_base is True

    def test_missing_name_raises(self):
        with pytest.raises(ValueError, match="name"):
            parse_manifest({"version": "1.0.0"})

    def test_missing_version_raises(self):
        with pytest.raises(ValueError, match="version"):
            parse_manifest({"name": "p"})

    def test_display_name(self):
        m = parse_manifest(_MINIMAL_MANIFEST)
        assert "test-plugin" in m.display_name
        assert "1.0.0" in m.display_name

    def test_validate_lyra_version_passes(self):
        m = parse_manifest(_MINIMAL_MANIFEST)
        assert m.validate_lyra_version(SemVer.parse("7.2.0"))

    def test_validate_lyra_version_fails(self):
        m = parse_manifest({"name": "p", "version": "1.0.0", "lyra_version": ">=8.0.0"})
        assert not m.validate_lyra_version(SemVer.parse("7.2.0"))

    def test_tool_annotation_with_risk_level(self):
        raw = {
            "name": "p",
            "version": "1.0.0",
            "tools": [
                {
                    "name": "dangerous_tool",
                    "annotations": {
                        "read_only": False,
                        "network_access": True,
                        "mutates_filesystem": True,
                        "risk_level": "high",
                        "category": "file",
                        "tags": ["dangerous"],
                    },
                }
            ],
        }
        m = parse_manifest(raw)
        t = m.tools[0]
        assert t.annotations.risk_level == RiskLevel.HIGH
        assert t.annotations.category == ToolCategory.FILE
        assert t.annotations.tags == ("dangerous",)

    def test_empty_manifest_no_hooks_or_tools(self):
        m = parse_manifest(_MINIMAL_MANIFEST)
        assert m.hooks == ()
        assert m.tools == ()
        assert m.dependencies == ()


# ---------------------------------------------------------------------------
# load_manifest_from_yaml
# ---------------------------------------------------------------------------


class TestLoadManifestFromYaml:
    def test_valid_yaml(self):
        yaml_text = """
name: test-plugin
version: "1.0.0"
author: test-author
hooks:
  - event: tool.pre_execute
    handler: plugin.check
"""
        m = load_manifest_from_yaml(yaml_text)
        assert m.name == "test-plugin"
        assert m.author == "test-author"
        assert len(m.hooks) == 1

    def test_invalid_yaml_raises(self):
        with pytest.raises((ValueError, Exception)):
            load_manifest_from_yaml("not valid: yaml: [")

    def test_non_mapping_yaml_raises(self):
        with pytest.raises(ValueError, match="mapping"):
            load_manifest_from_yaml("- list item")


# ---------------------------------------------------------------------------
# PluginInstance (lifecycle management)
# ---------------------------------------------------------------------------


class TestPluginInstance:
    @pytest.fixture
    def instance(self):
        m = parse_manifest(_MINIMAL_MANIFEST)
        return PluginInstance(manifest=m)

    def test_initial_state_installed(self, instance):
        assert instance.manifest.lifecycle == PluginLifecycle.INSTALLED

    def test_configure_from_installed(self, instance):
        instance.transition_to(PluginLifecycle.CONFIGURED)
        assert instance.manifest.lifecycle == PluginLifecycle.CONFIGURED

    def test_enable_from_configured(self, instance):
        instance.transition_to(PluginLifecycle.CONFIGURED)
        instance.transition_to(PluginLifecycle.ENABLED)
        assert instance.manifest.lifecycle == PluginLifecycle.ENABLED

    def test_disable_from_enabled(self, instance):
        instance.transition_to(PluginLifecycle.CONFIGURED)
        instance.transition_to(PluginLifecycle.ENABLED)
        instance.transition_to(PluginLifecycle.DISABLED)
        assert instance.manifest.lifecycle == PluginLifecycle.DISABLED

    def test_reenable_from_disabled(self, instance):
        instance.transition_to(PluginLifecycle.CONFIGURED)
        instance.transition_to(PluginLifecycle.ENABLED)
        instance.transition_to(PluginLifecycle.DISABLED)
        instance.transition_to(PluginLifecycle.ENABLED)
        assert instance.manifest.lifecycle == PluginLifecycle.ENABLED

    def test_uninstall_from_any_state(self, instance):
        instance.transition_to(PluginLifecycle.CONFIGURED)
        instance.transition_to(PluginLifecycle.ENABLED)
        instance.transition_to(PluginLifecycle.UNINSTALLED)
        assert instance.manifest.lifecycle == PluginLifecycle.UNINSTALLED

    def test_error_from_any_state(self, instance):
        instance.transition_to(PluginLifecycle.ERROR)
        assert instance.manifest.lifecycle == PluginLifecycle.ERROR

    def test_recover_from_error(self, instance):
        instance.transition_to(PluginLifecycle.ERROR)
        instance.transition_to(PluginLifecycle.DISABLED)
        assert instance.manifest.lifecycle == PluginLifecycle.DISABLED

    def test_invalid_transition_raises(self, instance):
        with pytest.raises(ValueError, match="invalid lifecycle transition"):
            instance.transition_to(PluginLifecycle.ENABLED)  # cannot go installed→enabled directly

    def test_cannot_transition_from_uninstalled(self, instance):
        instance.transition_to(PluginLifecycle.UNINSTALLED)
        with pytest.raises(ValueError, match="invalid lifecycle transition"):
            instance.transition_to(PluginLifecycle.ENABLED)

    def test_install_path_default(self, instance):
        assert instance.install_path == ""


# ---------------------------------------------------------------------------
# ToolDeclaration
# ---------------------------------------------------------------------------


class TestToolDeclaration:
    def test_default_annotation(self):
        td = ToolDeclaration(name="test_tool")
        assert td.name == "test_tool"
        assert td.annotations.read_only is False  # ToolAnnotation default

    def test_custom_annotation(self):
        ann = ToolAnnotation(read_only=False, network_access=True, risk_level=RiskLevel.HIGH)
        td = ToolDeclaration(name="admin_tool", annotations=ann)
        assert td.annotations.read_only is False
        assert td.annotations.risk_level == RiskLevel.HIGH
