"""Equal-budget enforcer for fair single-vs-multi-agent comparisons.

Tran & Kiela (arXiv:2604.02460) showed multi-agent gains on multi-hop QA shrink
or invert when total thinking-token budget is held constant. Any internal
benchmark that compares single-agent extended-reasoning to a multi-agent setup
must use this enforcer to be honest.
"""
from __future__ import annotations

from dataclasses import dataclass


class BudgetExhausted(RuntimeError):
    """Raised when an attempted consumption would exceed the cap."""


@dataclass
class BudgetController:
    """Token-budget enforcer. Single shared budget across all sub-agents.

    Pass the same controller into every sub-agent of a multi-agent run; the
    cumulative consumption is bounded by ``budget_tokens``.

    >>> ctrl = BudgetController(budget_tokens=1000)
    >>> ctrl.consume(400)
    600
    >>> ctrl.consume(700)
    Traceback (most recent call last):
      ...
    harness_core.evals.equal_budget.BudgetExhausted: ...
    """

    budget_tokens: int
    consumed_tokens: int = 0

    def remaining(self) -> int:
        return self.budget_tokens - self.consumed_tokens

    def consume(self, n_tokens: int, *, label: str = "") -> int:
        """Consume ``n_tokens`` from the budget; return remaining.

        Raises :class:`BudgetExhausted` if the consumption would exceed the cap.
        """
        if n_tokens < 0:
            raise ValueError(f"cannot consume negative tokens: {n_tokens}")
        if self.consumed_tokens + n_tokens > self.budget_tokens:
            tag = f" ({label})" if label else ""
            raise BudgetExhausted(
                f"requested {n_tokens} tokens{tag}, only {self.remaining()} remain "
                f"of {self.budget_tokens} budget"
            )
        self.consumed_tokens += n_tokens
        return self.remaining()

    def reserve(self, n_tokens: int) -> bool:
        """Non-raising consumption attempt; returns True on success."""
        try:
            self.consume(n_tokens)
            return True
        except BudgetExhausted:
            return False

    def reset(self) -> None:
        """Reset consumption to zero. Use between benchmark runs, not within."""
        self.consumed_tokens = 0

    @property
    def fraction_used(self) -> float:
        if self.budget_tokens == 0:
            return 1.0
        return self.consumed_tokens / self.budget_tokens
