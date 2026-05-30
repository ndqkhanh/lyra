"""Budget Enforcer - Token and cost budget enforcement for autonomous missions.

Tracks budget consumption and enforces limits with escalating responses
from warnings through soft caps to hard termination.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class BudgetLevel(StrEnum):
    """Budget consumption levels."""

    GREEN = "green"       # < 50% consumed
    YELLOW = "yellow"     # 50-75% consumed
    ORANGE = "orange"     # 75-90% consumed
    RED = "red"           # 90-100% consumed
    EXCEEDED = "exceeded" # > 100% consumed


@dataclass(frozen=True)
class BudgetLimits:
    """Budget limits configuration."""

    max_tokens: int = 1_000_000
    max_cost_cents: int = 1000  # $10.00
    max_time_minutes: int = 120
    max_operations: int = 500


@dataclass(frozen=True)
class BudgetState:
    """Current budget consumption state."""

    tokens_used: int = 0
    cost_cents_used: int = 0
    time_minutes_used: float = 0.0
    operations_completed: int = 0
    level: BudgetLevel = BudgetLevel.GREEN
    can_continue: bool = True


class BudgetEnforcer:
    """Enforces budget limits for autonomous operations.

    Features:
    - Multi-dimensional budget tracking (tokens, cost, time, operations)
    - Escalating enforcement levels
    - Real-time consumption monitoring
    - Hard-stop enforcement
    """

    def __init__(self, limits: BudgetLimits | None = None):
        self.limits = limits or BudgetLimits()
        self._started_at = datetime.now()
        self._state = BudgetState()

    def consume_tokens(self, count: int) -> BudgetState:
        """Record token consumption.

        Args:
            count: Number of tokens consumed

        Returns:
            Updated budget state
        """
        return self._update(
            tokens_used=self._state.tokens_used + count,
        )

    def consume_cost(self, cents: int) -> BudgetState:
        """Record monetary cost.

        Args:
            cents: Cost in cents

        Returns:
            Updated budget state
        """
        return self._update(
            cost_cents_used=self._state.cost_cents_used + cents,
        )

    def complete_operation(self) -> BudgetState:
        """Record a completed operation.

        Returns:
            Updated budget state
        """
        return self._update(
            operations_completed=self._state.operations_completed + 1,
        )

    def check(self) -> BudgetState:
        """Check current budget state without consuming anything.

        Returns:
            Current budget state
        """
        elapsed = (datetime.now() - self._started_at).total_seconds() / 60
        return self._update(time_minutes_used=elapsed)

    def can_proceed(self, estimated_tokens: int = 0, estimated_cost_cents: int = 0) -> tuple[bool, str]:
        """Check if operation can proceed based on estimates.

        Args:
            estimated_tokens: Estimated tokens for the operation
            estimated_cost_cents: Estimated cost in cents

        Returns:
            Tuple of (can_proceed, reason)
        """
        state = self.check()

        if state.level == BudgetLevel.EXCEEDED:
            return False, "Budget exceeded — operation blocked"

        projected_tokens = state.tokens_used + estimated_tokens
        if projected_tokens > self.limits.max_tokens:
            return False, f"Token budget would be exceeded ({projected_tokens}/{self.limits.max_tokens})"

        projected_cost = state.cost_cents_used + estimated_cost_cents
        if projected_cost > self.limits.max_cost_cents:
            return False, f"Cost budget would be exceeded ({projected_cost}/{self.limits.max_cost_cents})"

        return True, "OK"

    def _update(
        self,
        tokens_used: int | None = None,
        cost_cents_used: int | None = None,
        time_minutes_used: float | None = None,
        operations_completed: int | None = None,
    ) -> BudgetState:
        """Update budget state and recalculate level."""
        new_tokens = tokens_used if tokens_used is not None else self._state.tokens_used
        new_cost = cost_cents_used if cost_cents_used is not None else self._state.cost_cents_used
        new_time = time_minutes_used if time_minutes_used is not None else self._state.time_minutes_used
        new_ops = operations_completed if operations_completed is not None else self._state.operations_completed

        # Calculate consumption percentages
        token_pct = new_tokens / self.limits.max_tokens if self.limits.max_tokens > 0 else 0
        cost_pct = new_cost / self.limits.max_cost_cents if self.limits.max_cost_cents > 0 else 0
        time_pct = new_time / self.limits.max_time_minutes if self.limits.max_time_minutes > 0 else 0
        ops_pct = new_ops / self.limits.max_operations if self.limits.max_operations > 0 else 0

        max_pct = max(token_pct, cost_pct, time_pct, ops_pct)

        if max_pct > 1.0:
            level = BudgetLevel.EXCEEDED
            can_continue = False
        elif max_pct > 0.9:
            level = BudgetLevel.RED
            can_continue = True
        elif max_pct > 0.75:
            level = BudgetLevel.ORANGE
            can_continue = True
        elif max_pct > 0.5:
            level = BudgetLevel.YELLOW
            can_continue = True
        else:
            level = BudgetLevel.GREEN
            can_continue = True

        self._state = BudgetState(
            tokens_used=new_tokens,
            cost_cents_used=new_cost,
            time_minutes_used=new_time,
            operations_completed=new_ops,
            level=level,
            can_continue=can_continue,
        )
        return self._state

    def reset(self) -> None:
        """Reset the budget enforcer."""
        self._started_at = datetime.now()
        self._state = BudgetState()
