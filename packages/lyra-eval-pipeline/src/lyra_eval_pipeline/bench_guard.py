"""BenchGuard: cost-controlled evaluation guardrails."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .domain_evaluator import EvalSample
from .exceptions import BenchGuardError


@dataclass(frozen=True)
class BenchGuardConfig:
    """Configuration for bench guard cost control."""

    max_cost_per_audit: float = 15.0
    max_tokens_per_sample: int = 2000
    batch_size: int = 10
    cache_enabled: bool = True


@dataclass(frozen=True)
class CostEstimate:
    """Estimated and actual costs for an evaluation."""

    estimated_tokens: int
    estimated_cost: float
    actual_cost: float = 0.0
    over_budget: bool = False


@dataclass(frozen=True)
class GuardResult:
    """Result of a bench guard check."""

    allowed: bool
    reason: str
    cost: CostEstimate
    mitigation: str = ""


_TOKENS_PER_CHAR: float = 0.35
_COST_PER_TOKEN: float = 0.000015


class BenchGuard:
    """Cost-controlled guard for evaluation."""

    def __init__(self, config: BenchGuardConfig | None = None) -> None:
        self._config = config or BenchGuardConfig()
        self._spend: dict[str, float] = {}
        self._total_spend: float = 0.0

    async def estimate_cost(
        self, samples: list[EvalSample], config: BenchGuardConfig | None = None
    ) -> CostEstimate:
        """Estimate the cost of evaluating a set of samples."""
        cfg = config or self._config

        if not samples:
            raise BenchGuardError("Cannot estimate cost for empty sample list")

        total_chars = sum(len(s.input_text) + len(s.expected_output) for s in samples)
        estimated_tokens = int(total_chars * _TOKENS_PER_CHAR)
        estimated_cost = estimated_tokens * _COST_PER_TOKEN

        # Cap per-sample token usage
        max_total_tokens = min(
            estimated_tokens, cfg.max_tokens_per_sample * len(samples)
        )
        capped_cost = max_total_tokens * _COST_PER_TOKEN
        over_budget = capped_cost > cfg.max_cost_per_audit

        return CostEstimate(
            estimated_tokens=estimated_tokens,
            estimated_cost=round(capped_cost, 6),
            over_budget=over_budget,
        )

    async def guard_evaluation(
        self, samples: list[EvalSample]
    ) -> GuardResult:
        """Guard an evaluation, checking if it should proceed."""
        if not samples:
            return GuardResult(
                allowed=False,
                reason="No samples provided",
                cost=CostEstimate(estimated_tokens=0, estimated_cost=0.0),
                mitigation="Provide at least one sample",
            )

        cost = await self.estimate_cost(samples)

        if cost.over_budget:
            # Reduce batch size as mitigation
            reduced = samples[: self._config.batch_size]
            reduced_cost = await self.estimate_cost(reduced)
            return GuardResult(
                allowed=True,
                reason=f"Full evaluation over budget, using batch of {len(reduced)}",
                cost=reduced_cost,
                mitigation=f"Reduced batch from {len(samples)} to {len(reduced)}",
            )

        return GuardResult(
            allowed=True,
            reason="Evaluation within budget",
            cost=cost,
        )

    async def track_spend(self, eval_id: str) -> float:
        """Track spending for an evaluation by ID."""
        current = self._spend.get(eval_id, 0.0)
        spend = current + 0.001  # Simulate real spend tracking
        self._spend[eval_id] = spend
        self._total_spend += 0.001
        return round(spend, 6)

    async def get_total_spend(self) -> float:
        """Get the total accumulated spend."""
        return round(self._total_spend, 6)
