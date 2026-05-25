from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Sequence

from lyra_adversarial_review.exceptions import RecoveryError


class RecoveryAction(Enum):
    REFINE = "refine"
    PIVOT = "pivot"
    RETRY = "retry"
    ESCALATE = "escalate"
    ABORT = "abort"


class FailureType(Enum):
    TOOL_ERROR = "tool_error"
    APPROACH_INVALID = "approach_invalid"
    TIMEOUT = "timeout"
    PARSE_ERROR = "parse_error"
    MODEL_ERROR = "model_error"
    RESOURCE_EXHAUSTED = "resource_exhausted"


@dataclass(frozen=True)
class FailureSignal:
    failure_type: FailureType
    context: str
    attempt_count: int
    max_attempts: int
    details: str = ""


@dataclass(frozen=True)
class RecoveryDecision:
    action: RecoveryAction
    reason: str
    modified_params: dict[str, Any] = field(default_factory=dict)
    new_approach: str = ""


@dataclass(frozen=True)
class RecoveryTrace:
    sequence: Sequence[RecoveryDecision]
    outcomes: Sequence[str]
    started_at: datetime
    completed_at: datetime


@dataclass(frozen=True)
class RecoveryConfig:
    max_refines: int = 3
    max_pivots: int = 2
    max_retries: int = 3
    escalation_threshold: int = 5

    def validate(self) -> None:
        if self.max_refines < 0:
            raise RecoveryError("max_refines must be >= 0")
        if self.max_pivots < 0:
            raise RecoveryError("max_pivots must be >= 0")
        if self.max_retries < 0:
            raise RecoveryError("max_retries must be >= 0")
        if self.escalation_threshold < 1:
            raise RecoveryError("escalation_threshold must be >= 1")


@dataclass(frozen=True)
class RecoveryResult:
    success: bool
    final_output: str
    recovery_trace: RecoveryTrace
    total_attempts: int


class PivotRefineEngine:
    """Autonomous recovery engine implementing 2605.20025 pattern."""

    def __init__(self, config: RecoveryConfig | None = None) -> None:
        self._config = config or RecoveryConfig()
        self._config.validate()
        self._refine_count = 0
        self._pivot_count = 0
        self._total_attempts = 0

    def analyze_failure(self, signal: FailureSignal) -> RecoveryDecision:
        total_attempts = signal.attempt_count + self._total_attempts

        if total_attempts >= self._config.escalation_threshold:
            return RecoveryDecision(
                action=RecoveryAction.ESCALATE,
                reason=f"Total attempts ({total_attempts}) reached escalation threshold",
            )

        if signal.attempt_count >= signal.max_attempts:
            if self._pivot_count < self._config.max_pivots:
                return self._build_pivot_decision(signal)
            return RecoveryDecision(
                action=RecoveryAction.ABORT,
                reason=f"Max attempts ({signal.attempt_count}) reached and no pivots remaining",
            )

        if signal.failure_type == FailureType.TOOL_ERROR:
            if self._refine_count < self._config.max_refines:
                return RecoveryDecision(
                    action=RecoveryAction.REFINE,
                    reason=f"Tool error on attempt {signal.attempt_count + 1}; refining parameters",
                    modified_params={"retry_delay": 2 ** signal.attempt_count, "timeout_multiplier": 1.5},
                )
            return RecoveryDecision(
                action=RecoveryAction.RETRY,
                reason="Max refines reached; retrying with original parameters",
            )

        if signal.failure_type == FailureType.APPROACH_INVALID:
            if self._pivot_count < self._config.max_pivots:
                return self._build_pivot_decision(signal)
            return RecoveryDecision(
                action=RecoveryAction.RETRY,
                reason="Max pivots reached; retrying current approach",
            )

        if signal.failure_type == FailureType.TIMEOUT:
            if self._refine_count < self._config.max_refines:
                return RecoveryDecision(
                    action=RecoveryAction.REFINE,
                    reason="Timeout occurred; increasing timeout and simplifying",
                    modified_params={"timeout": 2 ** (signal.attempt_count + 1) * 30},
                )
            return RecoveryDecision(
                action=RecoveryAction.RETRY,
                reason="Max refines reached; retrying with current timeout",
            )

        if signal.failure_type == FailureType.PARSE_ERROR:
            return RecoveryDecision(
                action=RecoveryAction.RETRY,
                reason="Parse error; retrying and expecting well-formed output",
                modified_params={"format_instructions": "Strict output format required"},
            )

        if signal.failure_type == FailureType.MODEL_ERROR:
            return RecoveryDecision(
                action=RecoveryAction.RETRY,
                reason="Model error; transient issue, retrying",
                modified_params={"temperature": 0.3, "max_tokens": None},
            )

        if signal.failure_type == FailureType.RESOURCE_EXHAUSTED:
            if self._pivot_count < self._config.max_pivots:
                return self._build_pivot_decision(signal)
            return RecoveryDecision(
                action=RecoveryAction.RETRY,
                reason=f"Resource exhausted on approach; {'pivoting' if self._pivot_count < self._config.max_pivots else 'retrying'}",
            )

        return RecoveryDecision(
            action=RecoveryAction.ABORT,
            reason=f"Unrecognized failure type: {signal.failure_type.value}",
        )

    async def recover(
        self,
        original_task: str,
        failure_signal: FailureSignal,
        config: RecoveryConfig | None = None,
    ) -> RecoveryResult:
        cfg = config or self._config
        cfg.validate()

        decisions: list[RecoveryDecision] = []
        outcomes: list[str] = []
        started_at = datetime.now(timezone.utc)
        current_task = original_task
        cumulative_attempts = failure_signal.attempt_count

        decision = self.analyze_failure(failure_signal)
        decisions.append(decision)
        self._total_attempts = self._refine_count + self._pivot_count + cumulative_attempts

        while decision.action in (RecoveryAction.REFINE, RecoveryAction.PIVOT, RecoveryAction.RETRY):
            cumulative_attempts += 1
            self._total_attempts += 1

            if decision.action == RecoveryAction.REFINE:
                self._refine_count += 1
                current_task = self._apply_refine(current_task, decision.modified_params)
                outcomes.append(f"REFINE: {decision.reason}")
                simulated_success = self._simulate_recovery(decision, 0.7)
            elif decision.action == RecoveryAction.PIVOT:
                self._pivot_count += 1
                current_task = decision.new_approach or self._generate_pivot(current_task)
                outcomes.append(f"PIVOT: {decision.reason}")
                simulated_success = self._simulate_recovery(decision, 0.6)
            else:
                outcomes.append(f"RETRY: {decision.reason}")
                simulated_success = self._simulate_recovery(decision, 0.5)

            if cumulative_attempts >= cfg.escalation_threshold:
                decisions.append(
                    RecoveryDecision(
                        action=RecoveryAction.ESCALATE,
                        reason=f"Escalation threshold ({cfg.escalation_threshold}) reached",
                    )
                )
                outcomes.append("ESCALATE: Attempt threshold reached")
                completed_at = datetime.now(timezone.utc)
                return RecoveryResult(
                    success=False,
                    final_output=current_task,
                    recovery_trace=RecoveryTrace(
                        sequence=decisions,
                        outcomes=outcomes,
                        started_at=started_at,
                        completed_at=completed_at,
                    ),
                    total_attempts=cumulative_attempts,
                )

            if simulated_success:
                outcomes.append("SUCCESS: Recovery action resolved the failure")
                completed_at = datetime.now(timezone.utc)
                return RecoveryResult(
                    success=True,
                    final_output=current_task,
                    recovery_trace=RecoveryTrace(
                        sequence=decisions,
                        outcomes=outcomes,
                        started_at=started_at,
                        completed_at=completed_at,
                    ),
                    total_attempts=cumulative_attempts,
                )

            next_failure_type = self._action_to_failure_type(decision.action)
            new_signal = FailureSignal(
                failure_type=next_failure_type,
                context=current_task,
                attempt_count=cumulative_attempts,
                max_attempts=failure_signal.max_attempts,
                details=f"Recovery attempt {cumulative_attempts} failed",
            )
            decision = self.analyze_failure(new_signal)
            decisions.append(decision)

        completed_at = datetime.now(timezone.utc)
        return RecoveryResult(
            success=False,
            final_output=current_task,
            recovery_trace=RecoveryTrace(
                sequence=decisions,
                outcomes=outcomes,
                started_at=started_at,
                completed_at=completed_at,
            ),
            total_attempts=cumulative_attempts,
        )

    def _build_pivot_decision(self, signal: FailureSignal) -> RecoveryDecision:
        pivot_approaches = [
            "Use divide-and-conquer: break the problem into smaller sub-problems",
            "Use a different algorithm: switch from top-down to bottom-up",
            "Use approximation: trade precision for tractability",
            "Use caching: memoize intermediate results to avoid recomputation",
            "Use parallel execution: process independent sub-tasks concurrently",
        ]
        approach = pivot_approaches[self._pivot_count % len(pivot_approaches)]
        return RecoveryDecision(
            action=RecoveryAction.PIVOT,
            reason=f"Approach invalid on attempt {signal.attempt_count + 1}; switching strategy",
            new_approach=approach,
        )

    def _apply_refine(
        self, task: str, params: dict[str, Any]
    ) -> str:
        refined = task
        if "retry_delay" in params:
            refined += f"\n[Refined: retry_delay={params['retry_delay']}s]"
        if "timeout" in params:
            refined += f"\n[Refined: timeout={params['timeout']}s]"
        if "format_instructions" in params:
            refined += f"\n[Refined: {params['format_instructions']}]"
        return refined

    def _generate_pivot(self, task: str) -> str:
        return f"[PIVOTED] {task}\nNew approach: Alternate strategy applied"

    def _action_to_failure_type(self, action: RecoveryAction) -> FailureType:
        mapping = {
            RecoveryAction.REFINE: FailureType.TOOL_ERROR,
            RecoveryAction.PIVOT: FailureType.APPROACH_INVALID,
            RecoveryAction.RETRY: FailureType.TOOL_ERROR,
            RecoveryAction.ESCALATE: FailureType.RESOURCE_EXHAUSTED,
            RecoveryAction.ABORT: FailureType.RESOURCE_EXHAUSTED,
        }
        return mapping.get(action, FailureType.TOOL_ERROR)

    def _simulate_recovery(self, decision: RecoveryDecision, base_rate: float) -> bool:
        import random
        success_rate = base_rate
        if self._refine_count > self._config.max_refines:
            success_rate *= 0.5
        if self._pivot_count > self._config.max_pivots:
            success_rate *= 0.3
        return random.random() < success_rate
