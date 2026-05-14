"""AICL stability budgets — Phase E of the Lyra 322-326 evolution plan.

Tracks per-trajectory behavioral safety invariants. When any budget is
exceeded, the closed-loop controller must halt or hand off to a human.

Grounded in:
- Zenodo:17835680 — AICL: Adaptive In-Context Learning stability budgets
- Doc 326 §6 — Closed-loop safety constraints
"""
from __future__ import annotations

from dataclasses import dataclass


__all__ = [
    "StabilityBudget",
    "StabilityState",
    "BudgetViolation",
]


@dataclass(frozen=True)
class StabilityBudget:
    """Hard limits for one evolution episode."""

    max_behavior_drift: float = 0.30   # max cosine distance from baseline policy
    max_retry_count: int = 5            # total tool retries allowed
    max_cost_usd: float = 10.0          # total spend cap
    max_unsafe_actions: int = 0         # policy-gate blocks tolerated
    max_failed_tests: int = 3           # verifier failures before halt


@dataclass
class BudgetViolation:
    """One exceeded budget limit."""

    budget_name: str
    current_value: float
    limit: float

    @property
    def excess(self) -> float:
        return self.current_value - self.limit


@dataclass
class StabilityState:
    """Mutable per-episode accumulator checked against StabilityBudget."""

    behavior_drift: float = 0.0
    retry_count: int = 0
    cost_usd: float = 0.0
    unsafe_actions: int = 0
    failed_tests: int = 0

    def record_retry(self) -> None:
        self.retry_count += 1

    def record_cost(self, amount: float) -> None:
        self.cost_usd += amount

    def record_unsafe_action(self) -> None:
        self.unsafe_actions += 1

    def record_failed_test(self) -> None:
        self.failed_tests += 1

    def set_behavior_drift(self, drift: float) -> None:
        self.behavior_drift = drift

    def check(self, budget: StabilityBudget) -> list[BudgetViolation]:
        """Return list of violated budget limits (empty = all clear)."""
        violations: list[BudgetViolation] = []
        checks = [
            ("behavior_drift", self.behavior_drift, budget.max_behavior_drift),
            ("retry_count", float(self.retry_count), float(budget.max_retry_count)),
            ("cost_usd", self.cost_usd, budget.max_cost_usd),
            ("unsafe_actions", float(self.unsafe_actions), float(budget.max_unsafe_actions)),
            ("failed_tests", float(self.failed_tests), float(budget.max_failed_tests)),
        ]
        for name, current, limit in checks:
            if current > limit:
                violations.append(BudgetViolation(name, current, limit))
        return violations

    @property
    def is_safe(self) -> bool:
        return len(self.check(StabilityBudget())) == 0
