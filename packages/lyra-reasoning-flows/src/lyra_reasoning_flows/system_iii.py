from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RegulationAction(str, Enum):
    CONTINUE_FAST = "continue_fast"
    ENGAGE_PLANNING = "engage_planning"
    ESCALATE_MODEL = "escalate_model"
    REQUEST_HUMAN = "request_human"


@dataclass(frozen=True)
class MetaDecision:
    reasoning: str
    confidence: float
    escalation_flag: bool
    regulation_action: RegulationAction

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0.0, 1.0], got {self.confidence}")


@dataclass
class MetaMetrics:
    total_decisions: int = 0
    fast_decisions: int = 0
    planning_escalations: int = 0
    model_escalations: int = 0
    human_requests: int = 0
    avg_confidence: float = 0.0
    _confidence_sum: float = 0.0

    def record_decision(self, action: RegulationAction, confidence: float) -> None:
        self.total_decisions += 1
        self._confidence_sum += confidence
        self.avg_confidence = (
            self._confidence_sum / self.total_decisions if self.total_decisions > 0 else 0.0
        )

        if action == RegulationAction.CONTINUE_FAST:
            self.fast_decisions += 1
        elif action == RegulationAction.ENGAGE_PLANNING:
            self.planning_escalations += 1
        elif action == RegulationAction.ESCALATE_MODEL:
            self.model_escalations += 1
        elif action == RegulationAction.REQUEST_HUMAN:
            self.human_requests += 1


@dataclass(frozen=True)
class RegulationCost:
    computational_cost: float
    latency_cost: float
    quality_benefit: float
    net_value: float  # benefit - cost


class SystemIIIMetaRegulator:
    """System III meta-regulation: decides WHEN to engage deep planning.

    Performs cost/benefit analysis before escalating to System II or
    an Opus-tier model, tracking metrics over time.
    """

    def __init__(self, fast_threshold: float = 0.8, planning_threshold: float = 0.5) -> None:
        self.fast_threshold = fast_threshold
        self.planning_threshold = planning_threshold
        self.metrics = MetaMetrics()

    def should_plan_deep(self, task_context: str) -> MetaDecision:
        complexity = self._estimate_complexity(task_context)

        if complexity >= 0.9:
            return MetaDecision(
                reasoning=f"Task complexity {complexity:.2f} is very high; request human input",
                confidence=0.95,
                escalation_flag=True,
                regulation_action=RegulationAction.REQUEST_HUMAN,
            )

        if complexity >= 0.7:
            return MetaDecision(
                reasoning=f"Task complexity {complexity:.2f} above escalation threshold; escalate model",
                confidence=0.90,
                escalation_flag=True,
                regulation_action=RegulationAction.ESCALATE_MODEL,
            )

        if complexity >= 0.4:
            return MetaDecision(
                reasoning=f"Task complexity {complexity:.2f} above planning threshold; engage System II",
                confidence=0.85,
                escalation_flag=True,
                regulation_action=RegulationAction.ENGAGE_PLANNING,
            )

        return MetaDecision(
            reasoning=f"Task complexity {complexity:.2f} below planning threshold; continue fast",
            confidence=0.95,
            escalation_flag=False,
            regulation_action=RegulationAction.CONTINUE_FAST,
        )

    def regulate(
        self,
        current_trace: dict[str, Any] | None = None,
        performance_history: list[dict[str, Any]] | None = None,
    ) -> RegulationAction:
        base_action = RegulationAction.CONTINUE_FAST

        if performance_history:
            # Check recent performance to decide regulation.
            recent = performance_history[-5:] if len(performance_history) > 5 else performance_history
            avg_success = sum(
                1.0 for p in recent if p.get("success", False)
            ) / len(recent) if recent else 1.0

            if avg_success < 0.4:
                base_action = RegulationAction.ESCALATE_MODEL
            elif avg_success < 0.7:
                base_action = RegulationAction.ENGAGE_PLANNING
            elif current_trace and current_trace.get("loop_count", 0) > 10:
                base_action = RegulationAction.REQUEST_HUMAN

        self.metrics.record_decision(base_action, 0.8)
        return base_action

    def estimate_cost_benefit(
        self,
        task_complexity: float,
        estimated_depth: int,
    ) -> RegulationCost:
        comp_cost = task_complexity * estimated_depth * 0.1
        latency_cost = estimated_depth * 0.05
        quality_benefit = task_complexity * (1.0 - comp_cost)
        net_value = quality_benefit - comp_cost - latency_cost

        return RegulationCost(
            computational_cost=round(comp_cost, 4),
            latency_cost=round(latency_cost, 4),
            quality_benefit=round(quality_benefit, 4),
            net_value=round(net_value, 4),
        )

    def _estimate_complexity(self, task_context: str) -> float:
        """Estimate task complexity from context string features."""
        length = len(task_context)
        words = task_context.split()
        word_count = len(words)

        # Longer tasks with more unique words tend to be more complex.
        unique_ratio = len(set(w.lower() for w in words)) / max(word_count, 1)

        # Complexity factors.
        length_factor = min(1.0, length / 2000.0)
        structure_factor = 1.0 - unique_ratio  # more repetition => simpler
        _special_terms = ["analyze", "compare", "contrast", "synthesize", "evaluate", "why"]
        special_term_count = sum(
            1 for term in _special_terms if term in task_context.lower()
        )
        has_special_terms = special_term_count > 0

        complexity = length_factor * 0.4 + structure_factor * 0.3
        if has_special_terms:
            # Proportional boost: more distinct special terms = higher complexity.
            complexity += min(0.3, special_term_count * 0.05)

        return min(1.0, complexity)
