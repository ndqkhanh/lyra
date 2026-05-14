"""SLIM skill lifecycle management — Phase F of the Lyra skill-curation plan.

Implements marginal contribution estimation (leave-one-skill-out validation)
and three lifecycle decisions: Retain, Retire, Expand.

Grounded in:
- arXiv:2605.10923 — SLIM: Dynamic Skill Lifecycle Management
- +12.5pp over monotonic accumulation on ALFWorld (87.5% vs 75.0%)

Key insight: skills should be retired when their marginal external contribution
Δ(s) = Perf(library) − Perf(library ∖ {s}) drops near zero — i.e. when the
policy has already internalized the skill.  Monotonic accumulation degrades
library signal-to-noise over time.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


__all__ = [
    "LifecycleDecision",
    "SkillFitness",
    "LifecycleConfig",
    "LifecycleManager",
]


class LifecycleDecision(str, Enum):
    """Three SLIM lifecycle operations."""
    RETAIN = "retain"      # positive marginal value — keep
    RETIRE = "retire"      # marginal value ≈ 0 — remove
    EXPAND = "expand"      # persistent failures — coverage gap, add new skill


@dataclass
class SkillFitness:
    """Observed fitness metrics for one skill."""

    skill_id: str
    use_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    marginal_contribution: float = 0.0   # Δ(s) = Perf(lib) − Perf(lib \ {s})
    contexts_applied: list[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0

    @property
    def is_exercised(self) -> bool:
        return self.use_count >= 1


@dataclass(frozen=True)
class LifecycleConfig:
    """Tunable thresholds for lifecycle decisions."""

    min_uses_before_evaluation: int = 5        # skip decision until sufficiently exercised
    retire_marginal_threshold: float = 0.02    # Δ(s) < this → retire
    retire_success_rate_floor: float = 0.20    # also retire if success_rate too low
    expand_failure_streak: int = 3             # N consecutive failures → expand
    retain_min_success_rate: float = 0.50      # must exceed this to retain confidently


@dataclass(frozen=True)
class LifecycleEvaluation:
    """Result of evaluating one skill."""

    skill_id: str
    decision: LifecycleDecision
    reason: str
    marginal_contribution: float
    success_rate: float


class LifecycleManager:
    """Evaluates skills against SLIM lifecycle policy.

    Usage::

        mgr = LifecycleManager()
        mgr.record_outcome("greet-skill", success=True, context="onboarding")
        mgr.set_marginal_contribution("greet-skill", 0.08)
        eval_ = mgr.evaluate("greet-skill")
        if eval_.decision == LifecycleDecision.RETIRE:
            library.remove("greet-skill")
    """

    def __init__(self, config: Optional[LifecycleConfig] = None) -> None:
        self._config = config or LifecycleConfig()
        self._fitness: dict[str, SkillFitness] = {}
        self._failure_streaks: dict[str, int] = {}

    # ---------------------------------------------------------------- #
    # Observation                                                        #
    # ---------------------------------------------------------------- #

    def register(self, skill_id: str) -> SkillFitness:
        fitness = SkillFitness(skill_id=skill_id)
        self._fitness[skill_id] = fitness
        return fitness

    def record_outcome(
        self,
        skill_id: str,
        success: bool,
        context: str = "",
    ) -> None:
        if skill_id not in self._fitness:
            self.register(skill_id)
        f = self._fitness[skill_id]
        f.use_count += 1
        if success:
            f.success_count += 1
            self._failure_streaks[skill_id] = 0
        else:
            f.failure_count += 1
            self._failure_streaks[skill_id] = self._failure_streaks.get(skill_id, 0) + 1
        if context and context not in f.contexts_applied:
            f.contexts_applied.append(context)

    def set_marginal_contribution(self, skill_id: str, delta: float) -> None:
        if skill_id not in self._fitness:
            self.register(skill_id)
        self._fitness[skill_id].marginal_contribution = delta

    # ---------------------------------------------------------------- #
    # Decision                                                           #
    # ---------------------------------------------------------------- #

    def evaluate(self, skill_id: str) -> LifecycleEvaluation:
        cfg = self._config
        f = self._fitness.get(skill_id)
        if f is None:
            return LifecycleEvaluation(
                skill_id=skill_id,
                decision=LifecycleDecision.RETAIN,
                reason="not yet registered",
                marginal_contribution=0.0,
                success_rate=0.0,
            )

        if f.use_count < cfg.min_uses_before_evaluation:
            return LifecycleEvaluation(
                skill_id=skill_id,
                decision=LifecycleDecision.RETAIN,
                reason=f"only {f.use_count} uses; need {cfg.min_uses_before_evaluation} before evaluation",
                marginal_contribution=f.marginal_contribution,
                success_rate=f.success_rate,
            )

        streak = self._failure_streaks.get(skill_id, 0)
        if streak >= cfg.expand_failure_streak:
            return LifecycleEvaluation(
                skill_id=skill_id,
                decision=LifecycleDecision.EXPAND,
                reason=f"{streak} consecutive failures — coverage gap detected",
                marginal_contribution=f.marginal_contribution,
                success_rate=f.success_rate,
            )

        if (
            f.marginal_contribution < cfg.retire_marginal_threshold
            or f.success_rate < cfg.retire_success_rate_floor
        ):
            return LifecycleEvaluation(
                skill_id=skill_id,
                decision=LifecycleDecision.RETIRE,
                reason=(
                    f"Δ={f.marginal_contribution:.3f} < {cfg.retire_marginal_threshold} "
                    f"or success_rate={f.success_rate:.2f} < {cfg.retire_success_rate_floor}"
                ),
                marginal_contribution=f.marginal_contribution,
                success_rate=f.success_rate,
            )

        return LifecycleEvaluation(
            skill_id=skill_id,
            decision=LifecycleDecision.RETAIN,
            reason=f"Δ={f.marginal_contribution:.3f}, success_rate={f.success_rate:.2f}",
            marginal_contribution=f.marginal_contribution,
            success_rate=f.success_rate,
        )

    def evaluate_all(self) -> list[LifecycleEvaluation]:
        return [self.evaluate(sid) for sid in self._fitness]

    def skills_to_retire(self) -> list[str]:
        return [
            e.skill_id for e in self.evaluate_all()
            if e.decision == LifecycleDecision.RETIRE
        ]

    def fitness(self, skill_id: str) -> Optional[SkillFitness]:
        return self._fitness.get(skill_id)
