"""Cost tracker — session and task-level cost tracking for Lyra AGI.

Tracks every model API call, aggregates costs at the task and session level,
and exposes cost-per-successful-task as the primary metric.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from lyra_cost.models import (
    TIER_PRICING,
    CallOutcome,
    CostRecord,
    ModelTier,
    SessionBudget,
    TaskCostSummary,
)

logger = logging.getLogger(__name__)


def _resolve_tier(model_name: str) -> ModelTier:
    """Map a model name to its tier based on naming conventions."""
    name_lower = model_name.lower()
    # Tier 3 — most expensive
    if any(x in name_lower for x in ("opus", "deepseek-v4-pro")):
        return ModelTier.TIER_3
    # Tier 2 — daily coding workhorses
    if any(x in name_lower for x in ("sonnet", "gpt-4o", "gpt4o")):
        return ModelTier.TIER_2
    # Tier 1 — cost-effective for simple tasks
    if any(x in name_lower for x in ("haiku", "flash", "deepseek", "gemini")):
        return ModelTier.TIER_1
    # Tier 0 — local models
    if any(x in name_lower for x in ("local", "slm")):
        return ModelTier.TIER_0
    return ModelTier.TIER_1


def _compute_cost(
    tier: ModelTier, input_tokens: int, output_tokens: int
) -> tuple[float, float, float]:
    """Compute input, output, and total cost for a call."""
    input_price, output_price = TIER_PRICING[tier]
    input_cost = (input_tokens / 1_000_000) * input_price
    output_cost = (output_tokens / 1_000_000) * output_price
    total_cost = input_cost + output_cost
    return input_cost, output_cost, total_cost


class CostTracker:
    """Tracks API call costs at the session and task level.

    Usage:
        tracker = CostTracker("session-abc")
        tracker.record_call(model="sonnet-4", input_tokens=500, output_tokens=200)
        tracker.record_success(task_id="task-1")
        print(tracker.cost_per_successful_task)
    """

    def __init__(self, session_id: str, circuit_breaker_limit: float = 5.0) -> None:
        self._session_id = session_id
        self._circuit_breaker_limit = circuit_breaker_limit
        self._records: list[CostRecord] = []
        self._session_start = time.time()
        self._task_calls: dict[str, list[CostRecord]] = {}
        self._task_successes: set[str] = set()
        self._task_failures: set[str] = set()
        self._task_start_times: dict[str, float] = {}
        self._circuit_triggered = False

    # -- Public API -----------------------------------------------------------

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def records(self) -> tuple[CostRecord, ...]:
        return tuple(self._records)

    @property
    def total_spent(self) -> float:
        return sum(r.total_cost for r in self._records)

    @property
    def total_calls(self) -> int:
        return len(self._records)

    @property
    def successful_tasks(self) -> int:
        return len(self._task_successes)

    @property
    def failed_tasks(self) -> int:
        return len(self._task_failures)

    @property
    def cost_per_successful_task(self) -> float:
        """Primary metric: total cost divided by number of successful tasks."""
        if self._task_successes:
            return self.total_spent / len(self._task_successes)
        return 0.0

    @property
    def cost_per_call(self) -> float:
        if self._records:
            return self.total_spent / len(self._records)
        return 0.0

    @property
    def budget(self) -> SessionBudget:
        return SessionBudget(
            session_id=self._session_id,
            total_spent=self.total_spent,
            total_calls=self.total_calls,
            successful_tasks=self.successful_tasks,
            failed_tasks=self.failed_tasks,
            circuit_breaker_triggered=self._circuit_triggered,
            circuit_breaker_limit=self._circuit_breaker_limit,
        )

    def record_call(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        task_id: str | None = None,
        outcome: CallOutcome = CallOutcome.SUCCESS,
    ) -> CostRecord:
        """Record a single model API call and its cost."""
        if self._circuit_triggered:
            logger.warning("Circuit breaker active — call not recorded")
            raise RuntimeError("Circuit breaker is active; calls are blocked")

        tier = _resolve_tier(model)
        input_cost, output_cost, total_cost = _compute_cost(tier, input_tokens, output_tokens)

        record = CostRecord(
            model_name=model,
            model_tier=tier,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=total_cost,
            outcome=outcome,
            task_id=task_id,
        )
        self._records.append(record)

        if task_id:
            if task_id not in self._task_calls:
                self._task_calls[task_id] = []
                self._task_start_times[task_id] = record.timestamp
            self._task_calls[task_id].append(record)

        logger.debug(
            "Call recorded: model=%s tier=%s input=%d output=%d cost=%.6f",
            model,
            tier.name,
            input_tokens,
            output_tokens,
            total_cost,
        )

        # Check circuit breaker after every call
        if self.total_spent >= self._circuit_breaker_limit:
            self._circuit_triggered = True
            logger.warning(
                "Circuit breaker triggered at $%.2f (limit $%.2f)",
                self.total_spent,
                self._circuit_breaker_limit,
            )

        return record

    def record_success(self, task_id: str) -> None:
        """Mark a task as successfully completed."""
        self._task_successes.add(task_id)
        self._task_failures.discard(task_id)
        logger.info("Task %s marked successful", task_id)

    def record_failure(self, task_id: str) -> None:
        """Mark a task as failed."""
        self._task_failures.add(task_id)
        self._task_successes.discard(task_id)
        logger.info("Task %s marked failed", task_id)

    def task_summary(self, task_id: str) -> TaskCostSummary | None:
        """Get cost summary for a specific task."""
        calls = self._task_calls.get(task_id)
        if not calls:
            return None

        successful = [c for c in calls if c.outcome == CallOutcome.SUCCESS]
        cached = [c for c in calls if c.outcome in (CallOutcome.CACHED_PROMPT, CallOutcome.CACHED_SEMANTIC)]
        cached_savings = sum(c.total_cost for c in cached)

        end_time = calls[-1].timestamp if calls else None

        return TaskCostSummary(
            task_id=task_id,
            total_calls=len(calls),
            successful_calls=len(successful),
            total_cost=sum(c.total_cost for c in calls),
            successful_cost=sum(c.total_cost for c in successful),
            cached_cost_savings=cached_savings,
            start_time=self._task_start_times.get(task_id, 0.0),
            end_time=end_time,
        )

    @property
    def session_summary(self) -> dict[str, Any]:
        return {
            "session_id": self._session_id,
            "total_spent": round(self.total_spent, 4),
            "total_calls": self.total_calls,
            "successful_tasks": self.successful_tasks,
            "failed_tasks": self.failed_tasks,
            "cost_per_successful_task": round(self.cost_per_successful_task, 4),
            "cost_per_call": round(self.cost_per_call, 6),
            "circuit_breaker_triggered": self._circuit_triggered,
            "circuit_breaker_limit": self._circuit_breaker_limit,
            "session_duration_seconds": round(time.time() - self._session_start, 2),
        }
