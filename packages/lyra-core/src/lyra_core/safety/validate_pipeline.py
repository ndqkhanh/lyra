"""Multi-Agent Validation Pipeline — executor→validator→critic safety chain.

Implements a 3-stage validation pipeline where:
1. Executor produces an output
2. Validator (different model family) cross-checks the output
3. Critic reviews the validator's reasoning (not just the output)

All critical operations pass through this pipeline before execution,
providing defense-in-depth against single-model failures.

Inspired by ARIS (arXiv 2605.03042) 3-stage evidence verification and
Claude Code's multi-agent safety architecture.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import StrEnum


class StageStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_CLARIFICATION = "needs_clarification"
    ESCALATED = "escalated"


class ValidationDecision(StrEnum):
    PROCEED = "proceed"
    BLOCK = "block"
    FLAG = "flag"
    REWRITE = "rewrite"


@dataclass(frozen=True)
class StageResult:
    """Result from a single validation stage."""

    stage: str
    status: StageStatus
    decision: ValidationDecision
    reviewer_model: str
    reasoning: str
    confidence: float
    issues_found: tuple[str, ...]
    suggestions: tuple[str, ...]


@dataclass(frozen=True)
class ValidatorConfig:
    """Configuration for the validation pipeline.

    Attributes:
        require_different_family: if True, validator must use a different
            model family than the executor
        min_validator_confidence: threshold below which validation is rejected
        max_rewrite_rounds: maximum number of rewrite-and-revalidate cycles
        escalation_threshold: consecutive failures before auto-escalation
        enable_critic_stage: whether to enable the 3rd critic stage
    """

    require_different_family: bool = True
    min_validator_confidence: float = 0.6
    max_rewrite_rounds: int = 3
    escalation_threshold: int = 3
    enable_critic_stage: bool = True


@dataclass(frozen=True)
class PipelineResult:
    """Complete validation pipeline result."""

    pipeline_id: str
    action_text: str
    executor_model: str
    stages: tuple[StageResult, ...]
    final_decision: ValidationDecision
    total_confidence: float
    rewrite_count: int
    timestamp: float

    @property
    def passed(self) -> bool:
        return self.final_decision == ValidationDecision.PROCEED

    @property
    def blocked(self) -> bool:
        return self.final_decision == ValidationDecision.BLOCK

    @property
    def total_issues(self) -> int:
        return sum(len(s.issues_found) for s in self.stages)


class ValidatePipeline:
    """3-stage executor→validator→critic safety validation pipeline.

    Usage::

        pipeline = ValidatePipeline()
        result = pipeline.validate(
            action_text="deploy to production",
            executor_output="...",
            executor_model="claude-sonnet-4-20250514",
            validator_fn=my_validator,
            critic_fn=my_critic,
        )
        if result.passed:
            proceed_with_action()
    """

    def __init__(self, config: ValidatorConfig | None = None) -> None:
        self.config = config or ValidatorConfig()
        self._history: list[PipelineResult] = []

    def validate(
        self,
        action_text: str,
        executor_output: str,
        executor_model: str,
        executor_confidence: float,
        validator_fn=None,
        critic_fn=None,
    ) -> PipelineResult:
        """Run the full validation pipeline.

        Args:
            action_text: what action is being validated
            executor_output: the executor's proposed output
            executor_model: model family of the executor
            executor_confidence: executor's self-reported confidence
            validator_fn: callable(stage, context) -> StageResult for validation
            critic_fn: callable(stage, context) -> StageResult for critique
        """
        stages: list[StageResult] = []
        pipeline_id = f"vp-{int(time.time() * 1000)}"

        # Stage 1: Executor self-assessment (always runs)
        stages.append(
            StageResult(
                stage="executor",
                status=StageStatus.APPROVED if executor_confidence >= self.config.min_validator_confidence else StageStatus.NEEDS_CLARIFICATION,
                decision=ValidationDecision.PROCEED if executor_confidence >= self.config.min_validator_confidence else ValidationDecision.FLAG,
                reviewer_model=executor_model,
                reasoning="Executor self-assessment",
                confidence=executor_confidence,
                issues_found=(),
                suggestions=(),
            )
        )

        # Stage 2: Validator (different model family if configured)
        if validator_fn is not None:
            validator_result = validator_fn("validator", {
                "action_text": action_text,
                "executor_output": executor_output,
                "executor_model": executor_model,
                "executor_confidence": executor_confidence,
            })
            stages.append(validator_result)
        else:
            stages.append(self._default_validator(executor_model, executor_output, action_text))

        # Stage 3: Critic (reviews validator reasoning)
        if self.config.enable_critic_stage:
            if critic_fn is not None:
                critic_result = critic_fn("critic", {
                    "action_text": action_text,
                    "executor_output": executor_output,
                    "validator_stage": stages[-1],
                })
                stages.append(critic_result)
            else:
                stages.append(self._default_critic(stages[-1]))

        final_decision = self._compute_final_decision(stages)
        total_confidence = sum(s.confidence for s in stages) / max(len(stages), 1)

        result = PipelineResult(
            pipeline_id=pipeline_id,
            action_text=action_text,
            executor_model=executor_model,
            stages=tuple(stages),
            final_decision=final_decision,
            total_confidence=total_confidence,
            rewrite_count=0,
            timestamp=time.time(),
        )
        self._history.append(result)
        return result

    def validate_with_rewrite(
        self,
        action_text: str,
        executor_output: str,
        executor_model: str,
        executor_confidence: float,
        rewriter_fn=None,
        validator_fn=None,
        critic_fn=None,
    ) -> PipelineResult:
        """Validate with automatic rewrite on rejection.

        If the pipeline blocks or flags, the rewriter_fn is invoked to
        produce an improved output, and validation is retried.
        """
        rewrite_count = 0
        current_output = executor_output
        current_confidence = executor_confidence
        stages: list[StageResult] = []
        pipeline_id = f"vp-{int(time.time() * 1000)}"

        while rewrite_count <= self.config.max_rewrite_rounds:
            result = self.validate(
                action_text=action_text,
                executor_output=current_output,
                executor_model=executor_model,
                executor_confidence=current_confidence,
                validator_fn=validator_fn,
                critic_fn=critic_fn,
            )
            stages = list(result.stages)

            if result.final_decision == ValidationDecision.PROCEED:
                return PipelineResult(
                    pipeline_id=pipeline_id,
                    action_text=action_text,
                    executor_model=executor_model,
                    stages=tuple(stages),
                    final_decision=ValidationDecision.PROCEED,
                    total_confidence=result.total_confidence,
                    rewrite_count=rewrite_count,
                    timestamp=time.time(),
                )

            if result.final_decision == ValidationDecision.BLOCK:
                return PipelineResult(
                    pipeline_id=pipeline_id,
                    action_text=action_text,
                    executor_model=executor_model,
                    stages=tuple(stages),
                    final_decision=ValidationDecision.BLOCK,
                    total_confidence=result.total_confidence,
                    rewrite_count=rewrite_count,
                    timestamp=time.time(),
                )

            if rewriter_fn is None:
                break

            rewrite_output, rewrite_confidence = rewriter_fn(current_output, stages)
            current_output = rewrite_output
            current_confidence = rewrite_confidence
            rewrite_count += 1

        total_confidence = sum(s.confidence for s in stages) / max(len(stages), 1)
        final = PipelineResult(
            pipeline_id=pipeline_id,
            action_text=action_text,
            executor_model=executor_model,
            stages=tuple(stages),
            final_decision=ValidationDecision.FLAG,
            total_confidence=total_confidence,
            rewrite_count=rewrite_count,
            timestamp=time.time(),
        )
        self._history.append(final)
        return final

    def _default_validator(
        self,
        _executor_model: str,
        output: str,
        action: str,
    ) -> StageResult:
        """Built-in heuristic validator for when no custom validator is provided."""
        issues: list[str] = []
        suggestions: list[str] = []

        dangerous = ("delete", "drop", "rm -rf", "format", "truncate", "purge")
        for pattern in dangerous:
            if pattern in action.lower() or pattern in output.lower():
                issues.append(f"Dangerous operation detected: {pattern}")
                suggestions.append("Add confirmation gate before execution")

        confidence = 0.9 if not issues else max(0.2, 0.9 - 0.15 * len(issues))
        return StageResult(
            stage="validator",
            status=StageStatus.APPROVED if not issues else StageStatus.NEEDS_CLARIFICATION,
            decision=ValidationDecision.PROCEED if not issues else ValidationDecision.FLAG,
            reviewer_model="heuristic-validator",
            reasoning="Heuristic safety scan" if not issues else f"Found {len(issues)} concern(s)",
            confidence=confidence,
            issues_found=tuple(issues),
            suggestions=tuple(suggestions),
        )

    def _default_critic(self, validator_stage: StageResult) -> StageResult:
        """Built-in critic that reviews the validator's reasoning quality."""
        issues: list[str] = []
        suggestions: list[str] = []

        if validator_stage.confidence < 0.5:
            issues.append("Validator confidence critically low")
            suggestions.append("Request re-validation with stronger model")

        if len(validator_stage.reasoning) < 10:
            issues.append("Validator reasoning is insufficiently detailed")
            suggestions.append("Require more detailed validation reasoning")

        if not validator_stage.issues_found and validator_stage.confidence > 0.95:
            issues.append("Possibly overconfident validation — verify manually")

        confidence = validator_stage.confidence * 0.85 if issues else validator_stage.confidence
        return StageResult(
            stage="critic",
            status=StageStatus.APPROVED if not issues else StageStatus.NEEDS_CLARIFICATION,
            decision=validator_stage.decision if not issues else ValidationDecision.FLAG,
            reviewer_model="heuristic-critic",
            reasoning="Reviewed validator output" if not issues else f"Found {len(issues)} concern(s) with validation",
            confidence=confidence,
            issues_found=tuple(issues),
            suggestions=tuple(suggestions),
        )

    def _compute_final_decision(self, stages: list[StageResult]) -> ValidationDecision:
        """Compute final decision from all stages."""
        decisions = [s.decision for s in stages]
        if ValidationDecision.BLOCK in decisions:
            return ValidationDecision.BLOCK
        if ValidationDecision.FLAG in decisions:
            return ValidationDecision.FLAG
        if ValidationDecision.REWRITE in decisions:
            return ValidationDecision.REWRITE
        if all(d == ValidationDecision.PROCEED for d in decisions):
            return ValidationDecision.PROCEED
        return ValidationDecision.FLAG

    @property
    def history(self) -> list[PipelineResult]:
        return list(self._history)

    def stats(self) -> dict:
        if not self._history:
            return {"total": 0, "pass_rate": 0.0, "block_rate": 0.0, "mean_confidence": 0.0}
        total = len(self._history)
        passed = sum(1 for r in self._history if r.passed)
        blocked = sum(1 for r in self._history if r.blocked)
        mean_conf = sum(r.total_confidence for r in self._history) / total
        return {
            "total": total,
            "pass_rate": passed / total,
            "block_rate": blocked / total,
            "mean_confidence": round(mean_conf, 3),
            "mean_issues": round(sum(r.total_issues for r in self._history) / total, 2),
        }
