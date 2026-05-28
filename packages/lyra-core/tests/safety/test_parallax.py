"""Tests for Cognitive-Executive Separation (Parallax)."""

from __future__ import annotations

import pytest

from lyra_core.safety.parallax import (
    CognitiveContext,
    ContextType,
    ExecutionPlan,
    ParallaxConfig,
    SeparationGate,
)


class TestExecutionPlan:
    def test_plan_is_immutable(self) -> None:
        plan = ExecutionPlan(
            plan_id="plan-001",
            steps=("read file", "write file"),
            required_tools=("read_file", "write_file"),
            file_targets=("/tmp/test.txt",),
            risk_level=0.3,
            reasoning_summary="Simple file operation.",
            proposed_by="claude-sonnet-4",
        )
        with pytest.raises(Exception):
            plan.risk_level = 0.9  # type: ignore[misc]


class TestParallaxConfig:
    def test_default_config(self) -> None:
        config = ParallaxConfig()
        assert config.max_risk_threshold == 0.7
        assert config.require_different_validator is True
        assert config.audit_all_plans is True

    def test_blocked_tools_default(self) -> None:
        config = ParallaxConfig()
        assert "rm -rf" in config.blocked_tools
        assert "DROP TABLE" in config.blocked_tools
        assert "git push --force" in config.blocked_tools

    def test_config_is_immutable(self) -> None:
        config = ParallaxConfig()
        with pytest.raises(Exception):
            config.max_risk_threshold = 0.5  # type: ignore[misc]


class TestCognitiveContext:
    def test_create_reasoning_context(self) -> None:
        ctx = CognitiveContext()
        rid = ctx.create_reasoning_context()
        assert rid.startswith("reason-")

    def test_create_execution_context(self) -> None:
        ctx = CognitiveContext()
        rid = ctx.create_reasoning_context()
        eid = ctx.create_execution_context(rid)
        assert eid.startswith("exec-")

    def test_execution_context_requires_valid_reasoning(self) -> None:
        ctx = CognitiveContext()
        with pytest.raises(ValueError, match="Unknown reasoning context"):
            ctx.create_execution_context("nonexistent")

    def test_submit_low_risk_plan_approved(self) -> None:
        ctx = CognitiveContext()
        plan = ExecutionPlan(
            plan_id="plan-001",
            steps=("read a file",),
            required_tools=("read_file",),
            file_targets=("/tmp/test.txt",),
            risk_level=0.1,
            reasoning_summary="Safe file read.",
            proposed_by="claude-sonnet-4",
        )
        gate = ctx.submit_plan(plan)
        assert gate.approved

    def test_high_risk_plan_blocked(self) -> None:
        ctx = CognitiveContext()
        plan = ExecutionPlan(
            plan_id="plan-002",
            steps=("delete everything",),
            required_tools=("rm -rf /",),
            file_targets=("/",),
            risk_level=0.9,
            reasoning_summary="Destructive operation.",
            proposed_by="claude-sonnet-4",
        )
        gate = ctx.submit_plan(plan)
        assert not gate.approved
        assert gate.block_reason == "risk_threshold_exceeded"

    def test_blocked_tool_plan_rejected(self) -> None:
        ctx = CognitiveContext()
        plan = ExecutionPlan(
            plan_id="plan-003",
            steps=("force push",),
            required_tools=("git push --force origin main",),
            file_targets=(),
            risk_level=0.2,
            reasoning_summary="Force push to main.",
            proposed_by="claude-sonnet-4",
        )
        gate = ctx.submit_plan(plan)
        assert not gate.approved
        assert gate.block_reason == "blocked_tool_requested"

    def test_different_validator_family_approved(self) -> None:
        ctx = CognitiveContext()
        plan = ExecutionPlan(
            plan_id="plan-004",
            steps=("test",),
            required_tools=("echo",),
            file_targets=(),
            risk_level=0.2,
            reasoning_summary="Simple test.",
            proposed_by="claude-sonnet-4",
        )
        gate = ctx.validate_plan(plan, validator_model="gpt-validator-1")
        assert gate.approved

    def test_same_validator_family_blocked(self) -> None:
        ctx = CognitiveContext()
        plan = ExecutionPlan(
            plan_id="plan-004b",
            steps=("test",),
            required_tools=("echo",),
            file_targets=(),
            risk_level=0.2,
            reasoning_summary="Simple test.",
            proposed_by="claude-sonnet-4",
        )
        gate = ctx.validate_plan(plan, validator_model="claude-opus-4")
        assert not gate.approved

    def test_same_validator_allowed_when_config_disabled(self) -> None:
        config = ParallaxConfig(require_different_validator=False)
        ctx = CognitiveContext(config=config)
        plan = ExecutionPlan(
            plan_id="plan-005",
            steps=("test",),
            required_tools=("echo",),
            file_targets=(),
            risk_level=0.1,
            reasoning_summary="Simple test.",
            proposed_by="claude-sonnet-4",
        )
        gate = ctx.validate_plan(plan, validator_model="claude-sonnet-4")
        assert gate.approved

    def test_execute_approved_returns_true(self) -> None:
        ctx = CognitiveContext()
        plan = ExecutionPlan(
            plan_id="plan-006",
            steps=("test",),
            required_tools=("echo",),
            file_targets=(),
            risk_level=0.1,
            reasoning_summary="Safe.",
            proposed_by="claude-sonnet-4",
        )
        gate = ctx.submit_plan(plan)
        assert ctx.execute_approved(gate)

    def test_execute_blocked_returns_false(self) -> None:
        ctx = CognitiveContext()
        plan = ExecutionPlan(
            plan_id="plan-007",
            steps=("test",),
            required_tools=("echo",),
            file_targets=(),
            risk_level=0.9,
            reasoning_summary="Dangerous.",
            proposed_by="claude-sonnet-4",
        )
        gate = ctx.submit_plan(plan)
        assert not ctx.execute_approved(gate)

    def test_get_stats_tracks_correctly(self) -> None:
        ctx = CognitiveContext()
        for i in range(3):
            plan = ExecutionPlan(
                plan_id=f"plan-{i}",
                steps=("test",),
                required_tools=("echo",),
                file_targets=(),
                risk_level=0.1,
                reasoning_summary="Safe.",
                proposed_by="claude-sonnet-4",
            )
            ctx.submit_plan(plan)
        stats = ctx.get_stats()
        assert stats["total_plans"] == 3
        assert stats["approved"] == 3
        assert stats["blocked"] == 0

    def test_block_rate_tracking(self) -> None:
        ctx = CognitiveContext()
        ctx.submit_plan(
            ExecutionPlan(
                plan_id="p1",
                steps=("t",),
                required_tools=("e",),
                file_targets=(),
                risk_level=0.9,
                reasoning_summary="D.",
                proposed_by="claude-sonnet-4",
            )
        )
        ctx.submit_plan(
            ExecutionPlan(
                plan_id="p2",
                steps=("t",),
                required_tools=("e",),
                file_targets=(),
                risk_level=0.1,
                reasoning_summary="S.",
                proposed_by="claude-sonnet-4",
            )
        )
        stats = ctx.get_stats()
        assert stats["block_rate"] == 0.5

    def test_borderline_risk_adds_mitigation(self) -> None:
        ctx = CognitiveContext()
        plan = ExecutionPlan(
            plan_id="plan-008",
            steps=("test",),
            required_tools=("echo",),
            file_targets=(),
            risk_level=0.65,
            reasoning_summary="Borderline safe.",
            proposed_by="claude-sonnet-4",
        )
        gate = ctx.submit_plan(plan)
        assert gate.approved
        assert "human_review_recommended" in gate.risk_mitigations

    def test_multiple_reasoning_contexts_unique(self) -> None:
        ctx = CognitiveContext()
        r1 = ctx.create_reasoning_context()
        r2 = ctx.create_reasoning_context()
        assert r1 != r2


class TestContextType:
    def test_enum_values(self) -> None:
        assert ContextType.REASONING.value == "reasoning"
        assert ContextType.EXECUTION.value == "execution"


class TestSeparationGate:
    def test_gate_is_immutable(self) -> None:
        plan = ExecutionPlan(
            plan_id="p1",
            steps=("t",),
            required_tools=(),
            file_targets=(),
            risk_level=0.1,
            reasoning_summary=".",
            proposed_by="x",
        )
        gate = SeparationGate(
            plan=plan,
            approved=True,
            validator_model="v",
            validation_reasoning="ok",
        )
        with pytest.raises(Exception):
            gate.approved = False  # type: ignore[misc]
