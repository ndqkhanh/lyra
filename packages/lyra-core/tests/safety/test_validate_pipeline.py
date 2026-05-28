"""Tests for ValidatePipeline — multi-agent executor→validator→critic safety chain."""

import pytest
from lyra_core.safety.validate_pipeline import (
    PipelineResult,
    StageResult,
    StageStatus,
    ValidatePipeline,
    ValidationDecision,
    ValidatorConfig,
)


class TestStageStatus:
    def test_status_values(self):
        assert StageStatus.PENDING.value == "pending"
        assert StageStatus.APPROVED.value == "approved"
        assert StageStatus.REJECTED.value == "rejected"
        assert StageStatus.NEEDS_CLARIFICATION.value == "needs_clarification"
        assert StageStatus.ESCALATED.value == "escalated"


class TestValidationDecision:
    def test_decision_values(self):
        assert ValidationDecision.PROCEED.value == "proceed"
        assert ValidationDecision.BLOCK.value == "block"
        assert ValidationDecision.FLAG.value == "flag"
        assert ValidationDecision.REWRITE.value == "rewrite"


class TestStageResult:
    def test_approved_result(self):
        result = StageResult(
            stage="validator",
            status=StageStatus.APPROVED,
            decision=ValidationDecision.PROCEED,
            reviewer_model="claude-sonnet",
            reasoning="All checks passed.",
            confidence=0.95,
            issues_found=(),
            suggestions=(),
        )
        assert result.status == StageStatus.APPROVED
        assert result.decision == ValidationDecision.PROCEED

    def test_result_with_issues(self):
        result = StageResult(
            stage="validator",
            status=StageStatus.NEEDS_CLARIFICATION,
            decision=ValidationDecision.FLAG,
            reviewer_model="gpt-5",
            reasoning="Found 2 concerns.",
            confidence=0.4,
            issues_found=("Dangerous operation", "Missing validation"),
            suggestions=("Add confirmation gate",),
        )
        assert len(result.issues_found) == 2
        assert len(result.suggestions) == 1

    def test_result_immutable(self):
        r = StageResult("s", StageStatus.APPROVED, ValidationDecision.PROCEED, "m", "ok", 0.9, (), ())
        with pytest.raises(Exception):
            r.confidence = 0.5


class TestValidatorConfig:
    def test_default_config(self):
        config = ValidatorConfig()
        assert config.require_different_family is True
        assert config.min_validator_confidence == 0.6
        assert config.max_rewrite_rounds == 3
        assert config.enable_critic_stage is True

    def test_custom_config(self):
        config = ValidatorConfig(min_validator_confidence=0.8, max_rewrite_rounds=5)
        assert config.min_validator_confidence == 0.8
        assert config.max_rewrite_rounds == 5


class TestPipelineResult:
    def test_passed(self):
        stages = (
            StageResult("executor", StageStatus.APPROVED, ValidationDecision.PROCEED, "m1", "ok", 0.9, (), ()),
            StageResult("validator", StageStatus.APPROVED, ValidationDecision.PROCEED, "m2", "ok", 0.85, (), ()),
            StageResult("critic", StageStatus.APPROVED, ValidationDecision.PROCEED, "m3", "ok", 0.88, (), ()),
        )
        result = PipelineResult("p1", "action", "claude-sonnet", stages, ValidationDecision.PROCEED, 0.88, 0, 0.0)
        assert result.passed is True
        assert result.blocked is False

    def test_blocked(self):
        stages = (
            StageResult("executor", StageStatus.APPROVED, ValidationDecision.PROCEED, "m1", "ok", 0.9, (), ()),
            StageResult("validator", StageStatus.REJECTED, ValidationDecision.BLOCK, "m2", "DANGER", 0.2, ("risk",), ()),
        )
        result = PipelineResult("p2", "delete db", "claude-sonnet", stages, ValidationDecision.BLOCK, 0.55, 0, 0.0)
        assert result.blocked is True
        assert result.passed is False


class TestValidatePipeline:
    def test_pipeline_creation(self):
        pipeline = ValidatePipeline()
        assert pipeline.config is not None
        assert pipeline.history == []

    def test_validate_proceed(self):
        pipeline = ValidatePipeline()
        result = pipeline.validate(
            action_text="read file",
            executor_output="File contents: hello",
            executor_model="claude-sonnet-4-20250514",
            executor_confidence=0.9,
        )
        assert isinstance(result, PipelineResult)
        assert result.final_decision in (ValidationDecision.PROCEED, ValidationDecision.FLAG)

    def test_validate_dangerous_action_flagged(self):
        pipeline = ValidatePipeline()
        result = pipeline.validate(
            action_text="delete database",
            executor_output="DROP TABLE users",
            executor_model="claude-sonnet-4-20250514",
            executor_confidence=0.9,
        )
        assert result.total_issues > 0

    def test_validate_with_custom_validator(self):
        pipeline = ValidatePipeline()

        def my_validator(stage, context):
            return StageResult(
                stage=stage,
                status=StageStatus.APPROVED,
                decision=ValidationDecision.PROCEED,
                reviewer_model="custom-validator",
                reasoning="Custom validation passed",
                confidence=0.95,
                issues_found=(),
                suggestions=(),
            )

        result = pipeline.validate(
            action_text="deploy",
            executor_output="kubectl apply -f config.yaml",
            executor_model="claude-sonnet-4-20250514",
            executor_confidence=0.85,
            validator_fn=my_validator,
        )
        assert result.passed is True

    def test_validate_with_critic(self):
        pipeline = ValidatePipeline()

        def my_validator(stage, context):
            return StageResult(
                stage=stage,
                status=StageStatus.APPROVED,
                decision=ValidationDecision.PROCEED,
                reviewer_model="validator",
                reasoning="Looks good",
                confidence=0.9,
                issues_found=(),
                suggestions=(),
            )

        def my_critic(stage, context):
            return StageResult(
                stage=stage,
                status=StageStatus.APPROVED,
                decision=ValidationDecision.PROCEED,
                reviewer_model="critic",
                reasoning="Validator reasoning is sound",
                confidence=0.85,
                issues_found=(),
                suggestions=(),
            )

        result = pipeline.validate(
            action_text="read config",
            executor_output="config loaded",
            executor_model="claude-sonnet-4-20250514",
            executor_confidence=0.9,
            validator_fn=my_validator,
            critic_fn=my_critic,
        )
        assert len(result.stages) == 3

    def test_history_accumulates(self):
        pipeline = ValidatePipeline()
        pipeline.validate("a1", "out1", "m1", 0.9)
        pipeline.validate("a2", "out2", "m2", 0.9)
        assert len(pipeline.history) == 2

    def test_stats(self):
        pipeline = ValidatePipeline()
        pipeline.validate("a1", "out1", "m1", 0.9)
        stats = pipeline.stats()
        assert stats["total"] == 1
        assert "pass_rate" in stats
        assert "mean_confidence" in stats

    def test_stats_empty(self):
        pipeline = ValidatePipeline()
        stats = pipeline.stats()
        assert stats["total"] == 0

    def test_low_confidence_flags(self):
        pipeline = ValidatePipeline()
        result = pipeline.validate(
            action_text="modify config",
            executor_output="config changed",
            executor_model="claude-sonnet-4-20250514",
            executor_confidence=0.3,
        )
        # Low executor confidence results in FLAG decision
        assert result.final_decision == ValidationDecision.FLAG

    def test_validate_with_rewrite_proceed(self):
        pipeline = ValidatePipeline()

        def my_validator(stage, context):
            return StageResult(
                stage=stage, status=StageStatus.APPROVED,
                decision=ValidationDecision.PROCEED,
                reviewer_model="v", reasoning="Comprehensive validation passed all checks", confidence=0.95, issues_found=(), suggestions=(),
            )

        result = pipeline.validate_with_rewrite(
            action_text="test",
            executor_output="output",
            executor_model="claude-sonnet",
            executor_confidence=0.9,
            validator_fn=my_validator,
        )
        assert result.passed is True
        assert result.rewrite_count == 0

    def test_critic_disabled_by_config(self):
        config = ValidatorConfig(enable_critic_stage=False)
        pipeline = ValidatePipeline(config=config)
        result = pipeline.validate(
            action_text="read",
            executor_output="data",
            executor_model="m",
            executor_confidence=0.9,
        )
        assert len(result.stages) == 2
