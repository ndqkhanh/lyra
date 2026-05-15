"""Active-parameter cost accounting for MoE-aware comparisons.

Steele & Katz (arXiv:2601.04254) found Mixtral's multi-hop performance correlates
with its ~12B *active* parameters, not the 47B total. Any benchmark comparing
MoE and dense models must normalise against active parameters.

This module records (total_params, active_params, n_tokens) per inference and
exposes cost-per-accuracy-grade in active-param-token-units.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ActiveParamReading:
    """One inference's parameter accounting."""

    total_params: int  # billions, e.g. 47_000_000_000 for Mixtral 8x7B
    active_params: int  # billions activated per token, e.g. 12_900_000_000
    n_tokens: int  # tokens generated this inference

    def __post_init__(self) -> None:
        if self.total_params < self.active_params:
            raise ValueError(
                f"total_params ({self.total_params}) must be >= active_params ({self.active_params})"
            )
        if self.n_tokens < 0:
            raise ValueError(f"n_tokens must be >= 0, got {self.n_tokens}")

    @property
    def active_param_token_cost(self) -> int:
        """Active-parameter-token-units = active_params * n_tokens."""
        return self.active_params * self.n_tokens

    @property
    def total_param_token_cost(self) -> int:
        """Naive total-parameter-token-units (the wrong number to use for MoE)."""
        return self.total_params * self.n_tokens


@dataclass
class ActiveParamAccount:
    """Aggregate over many inferences; surface cost-per-grade-bump."""

    readings: list[ActiveParamReading] = field(default_factory=list)

    def record(self, reading: ActiveParamReading) -> None:
        self.readings.append(reading)

    def total_active_cost(self) -> int:
        return sum(r.active_param_token_cost for r in self.readings)

    def total_naive_cost(self) -> int:
        return sum(r.total_param_token_cost for r in self.readings)

    def cost_per_grade(self, *, accuracy_delta: float) -> float:
        """Active-param-token cost per accuracy point gained.

        Use to compare two methods on the same benchmark:
            method_A.cost_per_grade(accuracy_delta=A_acc - baseline) /
            method_B.cost_per_grade(accuracy_delta=B_acc - baseline)
        is the honest cost-efficiency ratio.
        """
        if accuracy_delta <= 0:
            raise ValueError(
                f"accuracy_delta must be > 0 for cost-per-grade; got {accuracy_delta}"
            )
        return self.total_active_cost() / accuracy_delta

    def moe_savings_ratio(self) -> float:
        """Fraction of cost saved by counting active vs total params.

        For dense models = 0.0 (no savings); for sparse MoE = high.
        """
        naive = self.total_naive_cost()
        if naive == 0:
            return 0.0
        return 1.0 - (self.total_active_cost() / naive)
