"""Cost tracking for evolution runs."""
from dataclasses import dataclass
from time import time


@dataclass
class BudgetCap:
    """Budget limits for evolution."""
    max_tokens: int | None = None
    max_dollars: float | None = None
    max_wall_clock_s: float | None = None


class CostMeter:
    """Track evolution costs."""

    def __init__(self):
        self.tokens_used: int = 0
        self.dollars_spent: float = 0.0
        self.wall_clock_s: float = 0.0
        self._start_time: float = time()

    def add_tokens(self, tokens: int, cost_per_token: float = 0.0):
        """Add token usage and cost."""
        self.tokens_used += tokens
        self.dollars_spent += tokens * cost_per_token

    def update_wall_clock(self):
        """Update wall clock time."""
        self.wall_clock_s = time() - self._start_time

    def check_budget(self, cap: BudgetCap) -> bool:
        """Return True if under budget."""
        self.update_wall_clock()

        if cap.max_tokens and self.tokens_used >= cap.max_tokens:
            return False
        if cap.max_dollars and self.dollars_spent >= cap.max_dollars:
            return False
        if cap.max_wall_clock_s and self.wall_clock_s >= cap.max_wall_clock_s:
            return False

        return True

    def get_stats(self) -> dict:
        """Get current cost statistics."""
        self.update_wall_clock()
        return {
            "tokens_used": self.tokens_used,
            "dollars_spent": self.dollars_spent,
            "wall_clock_s": self.wall_clock_s,
        }
