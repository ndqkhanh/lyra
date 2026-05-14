"""3-tier routing policy — Phase B of the Lyra 322-326 evolution plan.

Adds signal-driven tier selection (fast / reasoning / advisor) with a
trajectory-level Budget-Aware Adaptive Routing (BAAR) ledger on top of
the existing ConfidenceCascadeRouter.

Grounded in:
- Doc 323 §8.5 — Router observability and SLOs
- arXiv:2602.21227 — BAAR: Budget-Aware Adaptive Routing for LLM agents
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional


__all__ = [
    "ModelTier",
    "RoutingSignals",
    "TrajectoryBudget",
    "RoutingDecision",
    "RoutingConfig",
    "route_step",
    "TrajectoryRouter",
]

ModelTier = Literal["fast", "reasoning", "advisor"]


# ------------------------------------------------------------------ #
# Routing signals                                                      #
# ------------------------------------------------------------------ #

@dataclass(frozen=True)
class RoutingSignals:
    """Per-turn signals that inform tier selection.

    All float signals are normalised to [0, 1].
    """

    task_ambiguity: float = 0.0        # inferred from entropy / length of clarifying Qs
    evidence_conflict: bool = False    # two evidence sources contradict each other
    tool_risk: float = 0.0             # 0 = read-only, 1 = destructive / irreversible
    context_pressure: float = 0.0     # context_window_pct / 100
    uncertainty: float = 0.0          # model self-reported or verifier-derived
    repeated_failure: bool = False    # same tool failed >= 2 times this trajectory
    budget_pressure: float = 0.0      # cost_spent / cost_budget

    def __post_init__(self) -> None:
        for name in ("task_ambiguity", "tool_risk", "context_pressure",
                     "uncertainty", "budget_pressure"):
            v = getattr(self, name)
            if not 0.0 <= v <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {v!r}")


# ------------------------------------------------------------------ #
# BAAR budget ledger                                                   #
# ------------------------------------------------------------------ #

@dataclass
class TrajectoryBudget:
    """Mutable per-trajectory cost/token ledger (BAAR, arXiv:2602.21227)."""

    max_cost_usd: float = 5.0
    max_advisor_calls: int = 3

    cost_spent_usd: float = 0.0
    advisor_calls: int = 0
    reasoning_calls: int = 0
    fast_calls: int = 0
    total_turns: int = 0

    def record(self, tier: ModelTier, cost_usd: float = 0.0) -> None:
        self.cost_spent_usd += cost_usd
        self.total_turns += 1
        if tier == "advisor":
            self.advisor_calls += 1
        elif tier == "reasoning":
            self.reasoning_calls += 1
        else:
            self.fast_calls += 1

    @property
    def budget_pressure(self) -> float:
        if self.max_cost_usd <= 0:
            return 1.0
        return min(self.cost_spent_usd / self.max_cost_usd, 1.0)

    @property
    def advisor_budget_exhausted(self) -> bool:
        return self.advisor_calls >= self.max_advisor_calls


# ------------------------------------------------------------------ #
# Routing config + decision                                            #
# ------------------------------------------------------------------ #

@dataclass(frozen=True)
class RoutingConfig:
    """Tunable thresholds for the routing policy."""

    # Escalate fast → reasoning when any of these are exceeded
    ambiguity_reasoning_threshold: float = 0.4
    context_reasoning_threshold: float = 0.70   # 70 % context fill
    uncertainty_reasoning_threshold: float = 0.5

    # Additional gate to escalate reasoning → advisor
    tool_risk_advisor_threshold: float = 0.7
    uncertainty_advisor_threshold: float = 0.75

    # Suppress advisor when budget is too tight
    budget_pressure_advisor_cap: float = 0.85


@dataclass(frozen=True)
class RoutingDecision:
    """Result of one routing call."""

    tier: ModelTier
    reason: str
    escalated: bool   # True if tier > "fast"


# ------------------------------------------------------------------ #
# Pure routing function                                                #
# ------------------------------------------------------------------ #

def route_step(
    signals: RoutingSignals,
    budget: TrajectoryBudget,
    config: Optional[RoutingConfig] = None,
) -> RoutingDecision:
    """Decide which model tier to use for the current turn.

    Decision order (first matching rule wins):
    1. advisor — high tool_risk + (high uncertainty OR evidence_conflict)
                 AND budget not exhausted
    2. reasoning — any of: high ambiguity, evidence_conflict, high context fill,
                   high uncertainty, repeated failure
    3. fast — default
    """
    cfg = config or RoutingConfig()

    # Gate 1: advisor
    advisor_eligible = (
        not budget.advisor_budget_exhausted
        and budget.budget_pressure < cfg.budget_pressure_advisor_cap
        and signals.tool_risk >= cfg.tool_risk_advisor_threshold
        and (
            signals.uncertainty >= cfg.uncertainty_advisor_threshold
            or signals.evidence_conflict
        )
    )
    if advisor_eligible:
        return RoutingDecision(
            tier="advisor",
            reason=(
                f"tool_risk={signals.tool_risk:.2f} >= {cfg.tool_risk_advisor_threshold}, "
                f"uncertainty={signals.uncertainty:.2f} or evidence_conflict={signals.evidence_conflict}"
            ),
            escalated=True,
        )

    # Gate 2: reasoning
    reasoning_triggers: list[str] = []
    if signals.task_ambiguity >= cfg.ambiguity_reasoning_threshold:
        reasoning_triggers.append(f"ambiguity={signals.task_ambiguity:.2f}")
    if signals.evidence_conflict:
        reasoning_triggers.append("evidence_conflict")
    if signals.context_pressure >= cfg.context_reasoning_threshold:
        reasoning_triggers.append(f"context_pressure={signals.context_pressure:.2f}")
    if signals.uncertainty >= cfg.uncertainty_reasoning_threshold:
        reasoning_triggers.append(f"uncertainty={signals.uncertainty:.2f}")
    if signals.repeated_failure:
        reasoning_triggers.append("repeated_failure")

    if reasoning_triggers:
        return RoutingDecision(
            tier="reasoning",
            reason="; ".join(reasoning_triggers),
            escalated=True,
        )

    # Default
    return RoutingDecision(tier="fast", reason="all signals below thresholds", escalated=False)


# ------------------------------------------------------------------ #
# Stateful trajectory router                                           #
# ------------------------------------------------------------------ #

class TrajectoryRouter:
    """Wraps route_step with per-trajectory budget tracking.

    Usage::

        router = TrajectoryRouter(max_cost_usd=10.0, max_advisor_calls=5)
        decision = router.decide(signals)
        # ... call the model ...
        router.record(decision.tier, cost_usd=0.02)
    """

    def __init__(
        self,
        max_cost_usd: float = 5.0,
        max_advisor_calls: int = 3,
        config: Optional[RoutingConfig] = None,
    ) -> None:
        self._budget = TrajectoryBudget(
            max_cost_usd=max_cost_usd,
            max_advisor_calls=max_advisor_calls,
        )
        self._config = config or RoutingConfig()

    # ---------------------------------------------------------------- #

    def decide(self, signals: RoutingSignals) -> RoutingDecision:
        """Route the current turn and return the decision (does not record cost)."""
        return route_step(signals, self._budget, self._config)

    def record(self, tier: ModelTier, cost_usd: float = 0.0) -> None:
        """Update the budget ledger after a turn completes."""
        self._budget.record(tier, cost_usd)

    @property
    def budget(self) -> TrajectoryBudget:
        return self._budget

    def reset(self) -> None:
        self._budget = TrajectoryBudget(
            max_cost_usd=self._budget.max_cost_usd,
            max_advisor_calls=self._budget.max_advisor_calls,
        )
