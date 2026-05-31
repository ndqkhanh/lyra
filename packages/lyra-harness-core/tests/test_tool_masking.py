"""Tests for Tool Masking over Tool Removal (P2-B8)."""
from __future__ import annotations

import pytest

from lyra_harness_core.tool_masking import (
    MaskRule,
    ToolDescriptor,
    ToolMask,
    ToolMaskApplier,
    ToolMaskMode,
    ToolMaskPolicy,
    build_safety_policy,
    build_strict_policy,
)


# ---------------------------------------------------------------------------
# ToolMaskMode
# ---------------------------------------------------------------------------


class TestToolMaskMode:
    def test_values(self):
        assert ToolMaskMode.AUTO.value == "auto"
        assert ToolMaskMode.REQUIRED.value == "required"
        assert ToolMaskMode.SPECIFIED.value == "specified"

    def test_three_modes(self):
        assert len(ToolMaskMode) == 3


# ---------------------------------------------------------------------------
# ToolDescriptor
# ---------------------------------------------------------------------------


class TestToolDescriptor:
    def test_minimal(self):
        d = ToolDescriptor(name="read")
        assert d.name == "read"
        assert d.description == ""
        assert d.parameters == {}

    def test_with_params(self):
        d = ToolDescriptor(name="search", parameters={"query": "string"})
        assert d.parameters == {"query": "string"}

    def test_frozen(self):
        d = ToolDescriptor(name="x")
        with pytest.raises(Exception):
            d.name = "y"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ToolMask
# ---------------------------------------------------------------------------


class TestToolMask:
    def test_default_auto(self):
        m = ToolMask()
        assert m.mode == ToolMaskMode.AUTO
        assert not m.is_restrictive
        assert m.tool_count == 0

    def test_required_restrictive(self):
        m = ToolMask(
            mode=ToolMaskMode.REQUIRED,
            allowed_tools=frozenset({"read", "write"}),
        )
        assert m.is_restrictive
        assert m.tool_count == 2

    def test_specified_restrictive(self):
        m = ToolMask(mode=ToolMaskMode.SPECIFIED, required_tool="search")
        assert m.is_restrictive

    def test_allows_auto(self):
        m = ToolMask(mode=ToolMaskMode.AUTO)
        assert m.allows("anything")

    def test_allows_required(self):
        m = ToolMask(mode=ToolMaskMode.REQUIRED, allowed_tools=frozenset({"read", "write"}))
        assert m.allows("read")
        assert not m.allows("delete")

    def test_allows_specified(self):
        m = ToolMask(mode=ToolMaskMode.SPECIFIED, required_tool="search")
        assert m.allows("search")
        assert not m.allows("read")

    def test_reason(self):
        m = ToolMask(reason="safety check")
        assert m.reason == "safety check"

    def test_frozen(self):
        m = ToolMask()
        with pytest.raises(Exception):
            m.mode = ToolMaskMode.REQUIRED  # type: ignore[misc]


# ---------------------------------------------------------------------------
# MaskRule
# ---------------------------------------------------------------------------


class TestMaskRule:
    def test_defaults(self):
        r = MaskRule(name="test")
        assert r.name == "test"
        assert r.mode == ToolMaskMode.AUTO
        assert r.priority == 0

    def test_with_tools(self):
        r = MaskRule(
            name="readonly",
            mode=ToolMaskMode.REQUIRED,
            allowed_tools=frozenset({"read"}),
            priority=10,
        )
        assert r.allowed_tools == frozenset({"read"})
        assert r.priority == 10

    def test_frozen(self):
        r = MaskRule(name="x")
        with pytest.raises(Exception):
            r.priority = 5  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ToolMaskPolicy
# ---------------------------------------------------------------------------


class TestToolMaskPolicy:
    @pytest.fixture
    def policy(self):
        return ToolMaskPolicy()

    def test_default_evaluates_auto(self, policy):
        mask = policy.evaluate()
        assert mask.mode == ToolMaskMode.AUTO

    def test_add_rule_sorts_by_priority(self, policy):
        policy.add_rule(MaskRule(name="low", priority=1))
        policy.add_rule(MaskRule(name="high", priority=100))
        assert policy.rules[0].name == "high"

    def test_phase_matched_rule(self, policy):
        policy.add_rule(MaskRule(
            name="planning_rule",
            condition="planning",
            mode=ToolMaskMode.REQUIRED,
            allowed_tools=frozenset({"read"}),
            priority=10,
        ))
        policy.add_rule(MaskRule(
            name="execution_rule",
            condition="execution",
            mode=ToolMaskMode.AUTO,
            priority=5,
        ))
        mask = policy.evaluate(phase="planning")
        assert mask.mode == ToolMaskMode.REQUIRED
        assert mask.allows("read")

    def test_phase_not_matched_falls_back(self, policy):
        policy.add_rule(MaskRule(
            name="planning_rule",
            condition="planning",
            mode=ToolMaskMode.REQUIRED,
            allowed_tools=frozenset({"read"}),
            priority=10,
        ))
        mask = policy.evaluate(phase="execution")
        assert mask.mode == ToolMaskMode.AUTO

    def test_highest_priority_wins(self, policy):
        policy.add_rule(MaskRule(
            name="general",
            mode=ToolMaskMode.AUTO,
            priority=1,
        ))
        policy.add_rule(MaskRule(
            name="verification_strict",
            condition="verification",
            mode=ToolMaskMode.REQUIRED,
            allowed_tools=frozenset({"read"}),
            priority=20,
        ))
        mask = policy.evaluate(phase="verification")
        assert mask.mode == ToolMaskMode.REQUIRED
        assert mask.reason == "verification_strict"

    def test_no_matching_rule_returns_auto(self, policy):
        policy.add_rule(MaskRule(
            name="only_planning",
            condition="planning",
            mode=ToolMaskMode.REQUIRED,
            allowed_tools=frozenset({"read"}),
            priority=10,
        ))
        mask = policy.evaluate(phase="unknown_phase")
        assert mask.mode == ToolMaskMode.AUTO


# ---------------------------------------------------------------------------
# ToolMaskApplier
# ---------------------------------------------------------------------------


class TestToolMaskApplier:
    @pytest.fixture
    def tools(self):
        return [
            ToolDescriptor(name="read", description="Read files"),
            ToolDescriptor(name="write", description="Write files"),
            ToolDescriptor(name="search", description="Web search"),
            ToolDescriptor(name="delete", description="Delete files"),
        ]

    @pytest.fixture
    def applier(self, tools):
        return ToolMaskApplier(available_tools=tools)

    def test_apply_auto_all_tools(self, applier):
        mask = ToolMask(mode=ToolMaskMode.AUTO)
        result = applier.apply(mask)
        assert len(result) == 4

    def test_apply_required_subset(self, applier):
        mask = ToolMask(
            mode=ToolMaskMode.REQUIRED,
            allowed_tools=frozenset({"read", "write"}),
        )
        result = applier.apply(mask)
        assert len(result) == 2
        names = {t.name for t in result}
        assert names == {"read", "write"}

    def test_apply_specified_single(self, applier):
        mask = ToolMask(mode=ToolMaskMode.SPECIFIED, required_tool="search")
        result = applier.apply(mask)
        assert len(result) == 1
        assert result[0].name == "search"

    def test_apply_specified_not_found(self, applier):
        mask = ToolMask(mode=ToolMaskMode.SPECIFIED, required_tool="nonexistent")
        result = applier.apply(mask)
        assert len(result) == 0

    def test_build_mask_config_auto(self, applier):
        mask = ToolMask(mode=ToolMaskMode.AUTO)
        config = applier.build_mask_config(mask)
        assert config["mode"] == "auto"

    def test_build_mask_config_required(self, applier):
        mask = ToolMask(
            mode=ToolMaskMode.REQUIRED,
            allowed_tools=frozenset({"read", "write"}),
        )
        config = applier.build_mask_config(mask)
        assert config["mode"] == "required"
        assert config["allowed_tools"] == ["read", "write"]

    def test_build_mask_config_specified(self, applier):
        mask = ToolMask(mode=ToolMaskMode.SPECIFIED, required_tool="search")
        config = applier.build_mask_config(mask)
        assert config["mode"] == "specified"
        assert config["required_tool"] == "search"

    def test_apply_and_config(self, applier):
        mask = ToolMask(
            mode=ToolMaskMode.REQUIRED,
            allowed_tools=frozenset({"read"}),
        )
        tools, config = applier.apply_and_config(mask)
        assert len(tools) == 1
        assert config["mode"] == "required"

    def test_tool_names(self, applier):
        assert applier.tool_names == ["read", "write", "search", "delete"]

    def test_policy_integration(self, applier):
        policy = ToolMaskPolicy()
        policy.add_rule(MaskRule(
            name="exec_readonly",
            condition="execution",
            mode=ToolMaskMode.REQUIRED,
            allowed_tools=frozenset({"read", "search"}),
            priority=10,
        ))
        applier.policy = policy

        mask = applier.policy.evaluate(phase="execution")
        result = applier.apply(mask)
        names = {t.name for t in result}
        assert names == {"read", "search"}

    def test_empty_tools(self):
        applier = ToolMaskApplier(available_tools=[])
        mask = ToolMask(mode=ToolMaskMode.AUTO)
        assert applier.apply(mask) == []
        assert applier.tool_names == []


# ---------------------------------------------------------------------------
# Pre-built Policies
# ---------------------------------------------------------------------------


class TestBuildSafetyPolicy:
    def test_verification_readonly(self):
        policy = build_safety_policy()
        mask = policy.evaluate(phase="verification")
        assert mask.mode == ToolMaskMode.REQUIRED
        assert mask.allows("Read")
        assert "Read" in mask.allowed_tools

    def test_planning_readonly(self):
        policy = build_safety_policy()
        mask = policy.evaluate(phase="planning")
        assert mask.mode == ToolMaskMode.REQUIRED
        assert mask.allows("Read")
        assert mask.allows("WebSearch")

    def test_execution_auto(self):
        policy = build_safety_policy()
        mask = policy.evaluate(phase="execution")
        assert mask.mode == ToolMaskMode.AUTO

    def test_unknown_phase_falls_back(self):
        policy = build_safety_policy()
        mask = policy.evaluate(phase="unknown")
        assert mask.mode == ToolMaskMode.AUTO


class TestBuildStrictPolicy:
    def test_specified_tool(self):
        policy = build_strict_policy(required_tool="deploy")
        mask = policy.evaluate()
        assert mask.mode == ToolMaskMode.SPECIFIED
        assert mask.allows("deploy")
        assert not mask.allows("read")

    def test_empty_required(self):
        policy = build_strict_policy()
        mask = policy.evaluate()
        assert mask.mode == ToolMaskMode.SPECIFIED
        assert mask.required_tool == ""


# ---------------------------------------------------------------------------
# Integration test
# ---------------------------------------------------------------------------


class TestToolMaskingIntegration:
    def test_full_safety_workflow(self):
        applier = ToolMaskApplier(
            available_tools=[
                ToolDescriptor(name="Read"),
                ToolDescriptor(name="Write"),
                ToolDescriptor(name="Bash(grep"),
                ToolDescriptor(name="WebSearch"),
                ToolDescriptor(name="WebFetch"),
                ToolDescriptor(name="Bash(git push"),
            ],
            policy=build_safety_policy(),
        )

        # Planning phase: only read/search
        mask = applier.policy.evaluate(phase="planning")
        assert mask.is_restrictive
        tools = applier.apply(mask)
        names = {t.name for t in tools}
        assert "Read" in names
        assert "Write" not in names
        assert "Bash(git push" not in names

        # Execution phase: all tools
        mask = applier.policy.evaluate(phase="execution")
        assert not mask.is_restrictive
        tools = applier.apply(mask)
        assert len(tools) == 6

        # Verification phase: read-only
        mask = applier.policy.evaluate(phase="verification")
        assert mask.is_restrictive
        tools = applier.apply(mask)
        for t in tools:
            assert t.name in ("Read",) or t.name.startswith("Bash(grep") or t.name.startswith("Bash(find") or t.name.startswith("Bash(git diff")

    def test_dynamic_policy_switch(self):
        """Simulate switching policies mid-workflow."""
        applier = ToolMaskApplier(
            available_tools=[
                ToolDescriptor(name="read"),
                ToolDescriptor(name="write"),
                ToolDescriptor(name="delete"),
            ],
        )

        # Phase 1: planning, all tools (default AUTO)
        mask = ToolMask(mode=ToolMaskMode.AUTO)
        assert applier.apply(mask) == applier.available_tools

        # Phase 2: execution, restrict to safe tools
        mask = ToolMask(mode=ToolMaskMode.REQUIRED, allowed_tools=frozenset({"read", "write"}))
        tools = applier.apply(mask)
        assert len(tools) == 2

        # Phase 3: critical operation, single tool only
        mask = ToolMask(mode=ToolMaskMode.SPECIFIED, required_tool="read")
        tools = applier.apply(mask)
        assert len(tools) == 1
        assert tools[0].name == "read"
