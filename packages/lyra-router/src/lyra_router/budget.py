"""
Budget tracker for the Lyra Model Router (V4).

Implements Google BATS-style budget-aware routing with four regimes:
HIGH (>70%), MEDIUM (30-70%), LOW (10-30%), CRITICAL (<10%).

Features:
- Per-session and per-task cost tracking
- Circuit breaker at $5/session
- Budget XML injection for reasoning context
- Thread-safe accumulation
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

from .models import BudgetRegime, ModelTier, TaskComplexity

# Circuit breaker: maximum spend per session (USD)
CIRCUIT_BREAKER_LIMIT_USD: float = 5.0


@dataclass
class TaskCostEntry:
    """A single task cost record (NOT frozen — mutated by tracker)."""

    task_id: str
    task_summary: str
    complexity: TaskComplexity
    model_used: str
    cost_usd: float
    latency_ms: float
    success: bool
    timestamp: float = field(default_factory=time.time)


class BudgetTracker:
    """
    Tracks spending across tasks within a session.

    Implements BATS-style budget regimes and XML context injection
    for budget-aware reasoning. Thread-safe via internal lock.
    """

    _HIGH_THRESHOLD = 0.70
    _MEDIUM_THRESHOLD = 0.30
    _LOW_THRESHOLD = 0.10

    def __init__(
        self,
        session_budget_usd: float = CIRCUIT_BREAKER_LIMIT_USD,
        name: str = "default",
    ) -> None:
        """
        Args:
            session_budget_usd: Total USD budget for this session.
            name: Human-readable session name for logging.
        """
        self.session_budget_usd = session_budget_usd
        self.name = name
        self._total_spent: float = 0.0
        self._task_count: int = 0
        self._success_count: int = 0
        self._entries: list[TaskCostEntry] = []
        self._lock = threading.Lock()
        self._tripped: bool = False

    # ── Public API ─────────────────────────────────────────────────

    def record(
        self,
        cost_usd: float,
        task_id: str = "",
        task_summary: str = "",
        complexity: TaskComplexity = TaskComplexity.SIMPLE,
        model_used: str = "",
        latency_ms: float = 0.0,
        success: bool = True,
    ) -> bool:
        """
        Record a task cost and return True if within budget, False if tripped.

        If the circuit breaker has already been tripped, returns False
        without recording.
        """
        with self._lock:
            if self._tripped:
                return False

            self._total_spent += cost_usd
            self._task_count += 1
            if success:
                self._success_count += 1

            self._entries.append(TaskCostEntry(
                task_id=task_id,
                task_summary=task_summary,
                complexity=complexity,
                model_used=model_used,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
                success=success,
            ))

            if self._total_spent >= self.session_budget_usd:
                self._tripped = True
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(
                    "Circuit breaker tripped at $%.4f / $%.2f (session: %s)",
                    self._total_spent,
                    self.session_budget_usd,
                    self.name,
                )
                return False
            return True

    # ── Budget Status ──────────────────────────────────────────────

    @property
    def total_spent(self) -> float:
        """Total USD spent in the current session."""
        return self._total_spent

    @property
    def remaining(self) -> float:
        """Remaining USD budget for the current session."""
        return max(0.0, self.session_budget_usd - self._total_spent)

    @property
    def budget_used_ratio(self) -> float:
        """Fraction of budget consumed in [0, 1]."""
        if self.session_budget_usd <= 0:
            return 1.0
        return min(1.0, self._total_spent / self.session_budget_usd)

    @property
    def budget_remaining_ratio(self) -> float:
        """Fraction of budget remaining in [0, 1]."""
        return 1.0 - self.budget_used_ratio

    @property
    def regime(self) -> BudgetRegime:
        """Current budget regime based on remaining budget."""
        ratio = self.budget_remaining_ratio
        if ratio > self._HIGH_THRESHOLD:
            return BudgetRegime.HIGH
        if ratio > self._MEDIUM_THRESHOLD:
            return BudgetRegime.MEDIUM
        if ratio > self._LOW_THRESHOLD:
            return BudgetRegime.LOW
        return BudgetRegime.CRITICAL

    @property
    def is_tripped(self) -> bool:
        """Whether the circuit breaker has been tripped."""
        return self._tripped

    @property
    def task_count(self) -> int:
        """Total number of tasks recorded in this session."""
        return self._task_count

    @property
    def success_count(self) -> int:
        """Total number of successful tasks in this session."""
        return self._success_count

    @property
    def success_rate(self) -> float:
        """Task success rate in [0, 1]."""
        if self._task_count == 0:
            return 1.0
        return self._success_count / self._task_count

    @property
    def cost_per_successful_task(self) -> float:
        """Average cost per successful task (USD)."""
        if self._success_count == 0:
            return 0.0
        return self._total_spent / self._success_count

    def reset(self) -> None:
        """Reset the tracker for a new session."""
        with self._lock:
            self._total_spent = 0.0
            self._task_count = 0
            self._success_count = 0
            self._entries.clear()
            self._tripped = False

    # ── Task-level budget guidance ─────────────────────────────────

    def get_max_task_budget(self) -> float:
        """
        Return the recommended maximum spend for the next task.

        Depends on regime — more conservative at lower budgets.
        """
        ratio = self.budget_remaining_ratio
        if ratio > self._HIGH_THRESHOLD:
            # HIGH: can spend up to 20% of remaining
            return self.remaining * 0.20
        if ratio > self._MEDIUM_THRESHOLD:
            # MEDIUM: up to 10% of remaining
            return self.remaining * 0.10
        if ratio > self._LOW_THRESHOLD:
            # LOW: up to 5% of remaining
            return self.remaining * 0.05
        # CRITICAL: up to 2% of remaining
        return self.remaining * 0.02

    def should_downgrade_tier(self, target_tier: ModelTier) -> bool:
        """
        Determine whether the budget regime requires tier downgrade.

        Args:
            target_tier: The model tier that would normally be selected.

        Returns:
            True if a cheaper model should be used instead.
        """
        if self.regime == BudgetRegime.CRITICAL:
            return target_tier not in (ModelTier.LOCAL_SLM, ModelTier.HAIKU)
        if self.regime == BudgetRegime.LOW:
            return target_tier in (ModelTier.PREMIUM, ModelTier.AGENTIC)
        return False

    # ── Budget XML for reasoning context ───────────────────────────

    def to_xml_context(self) -> str:
        """
        Produce BATS-style budget XML for injection into reasoning prompts.

        Returns a structured XML block with budget status.
        """
        regime = self.regime
        return (
            f"<budget>\n"
            f"  <session_name>{self.name}</session_name>\n"
            f"  <spent>${self._total_spent:.4f}</spent>\n"
            f"  <limit>${self.session_budget_usd:.2f}</limit>\n"
            f"  <remaining>${self.remaining:.4f}</remaining>\n"
            f"  <ratio_used>{self.budget_used_ratio:.1%}</ratio_used>\n"
            f"  <regime>{regime.value.upper()}</regime>\n"
            f"  <tasks>{self._task_count}</tasks>\n"
            f"  <success_rate>{self.success_rate:.1%}</success_rate>\n"
            f"  <circuit_breaker>{'TRIPPED' if self._tripped else 'OK'}</circuit_breaker>\n"
            f"  <max_next_task>${self.get_max_task_budget():.4f}</max_next_task>\n"
            f"</budget>"
        )

    def get_summary(self) -> dict:
        """Return a dict summary of budget state for metrics/monitoring."""
        return {
            "name": self.name,
            "total_spent": round(self._total_spent, 6),
            "session_budget": self.session_budget_usd,
            "remaining": round(self.remaining, 6),
            "regime": self.regime.value,
            "is_tripped": self._tripped,
            "task_count": self._task_count,
            "success_rate": round(self.success_rate, 4),
            "cost_per_successful_task": round(self.cost_per_successful_task, 6),
            "max_next_task_budget": round(self.get_max_task_budget(), 6),
        }
