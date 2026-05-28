"""Budget and cost tracking for Lyra autonomy.

Tracks API call costs, token usage, and enforces daily/monthly limits
with graceful degradation.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_DAILY_LIMIT_USD: float = 10.0
_DEFAULT_MONTHLY_LIMIT_USD: float = 200.0
_DEFAULT_WARNING_THRESHOLD: float = 0.8  # warn at 80% of limit
_DEFAULT_BUDGET_FILE: str = "budget_data.json"


class BudgetExceededError(Exception):
    """Raised when a budget limit has been exceeded."""


@dataclass(frozen=True)
class CostEntry:
    """A single cost-accounting record."""

    timestamp: str  # ISO-8601
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        """Return the sum of prompt and completion tokens."""
        return self.prompt_tokens + self.completion_tokens


@dataclass(frozen=True)
class BudgetSummary:
    """Roll-up of budget usage for a period."""

    total_cost_usd: float = 0.0
    total_tokens: int = 0
    entry_count: int = 0
    daily_cost_usd: float = 0.0
    daily_tokens: int = 0
    daily_limit_usd: float = _DEFAULT_DAILY_LIMIT_USD
    monthly_cost_usd: float = 0.0
    monthly_tokens: int = 0
    monthly_limit_usd: float = _DEFAULT_MONTHLY_LIMIT_USD
    daily_pct: float = 0.0
    monthly_pct: float = 0.0
    degraded: bool = False


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------


@dataclass
class BudgetManager:
    """Tracks API costs and enforces budgets.

    Args:
        data_dir: Directory for persisting the budget journal.
        daily_limit_usd: Hard daily spending cap.
        monthly_limit_usd: Hard monthly spending cap.
        warning_threshold: Fraction at which a warning is logged.
    """

    data_dir: Path = field(
        default_factory=lambda: Path.home() / ".lyra"
    )
    daily_limit_usd: float = _DEFAULT_DAILY_LIMIT_USD
    monthly_limit_usd: float = _DEFAULT_MONTHLY_LIMIT_USD
    warning_threshold: float = _DEFAULT_WARNING_THRESHOLD

    _entries: list[CostEntry] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record_usage(
        self,
        model: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        cost_usd: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> CostEntry:
        """Record an API usage event. Raises if budget is exceeded.

        Call :meth:`check_limits` beforehand to fail fast.
        """
        entry = CostEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost_usd,
            metadata=metadata or {},
        )
        self._entries.append(entry)
        self._save()

        self._check_warnings()
        logger.info("usage_recorded: model=%s cost=%s tokens=%d", model, cost_usd, entry.total_tokens)
        return entry

    def check_limits(self) -> None:
        """Raise :class:`BudgetExceededError` if any limit is breached."""
        now = datetime.now(timezone.utc)
        today_prefix = now.strftime("%Y-%m-%d")
        month_prefix = now.strftime("%Y-%m")

        daily_cost = sum(
            e.cost_usd
            for e in self._entries
            if e.timestamp.startswith(today_prefix)
        )
        monthly_cost = sum(
            e.cost_usd
            for e in self._entries
            if e.timestamp.startswith(month_prefix)
        )

        if daily_cost >= self.daily_limit_usd:
            raise BudgetExceededError(
                f"Daily budget ${daily_cost:.2f} >= limit ${self.daily_limit_usd:.2f}"
            )
        if monthly_cost >= self.monthly_limit_usd:
            raise BudgetExceededError(
                f"Monthly budget ${monthly_cost:.2f} >= limit ${self.monthly_limit_usd:.2f}"
            )

    def summary(self) -> BudgetSummary:
        """Return a roll-up of current budget usage."""
        now = datetime.now(timezone.utc)
        today_prefix = now.strftime("%Y-%m-%d")
        month_prefix = now.strftime("%Y-%m")

        total_cost = sum(e.cost_usd for e in self._entries)
        total_tok = sum(e.total_tokens for e in self._entries)

        daily_cost = sum(
            e.cost_usd for e in self._entries if e.timestamp.startswith(today_prefix)
        )
        daily_tok = sum(
            e.total_tokens for e in self._entries if e.timestamp.startswith(today_prefix)
        )
        monthly_cost = sum(
            e.cost_usd for e in self._entries if e.timestamp.startswith(month_prefix)
        )
        monthly_tok = sum(
            e.total_tokens for e in self._entries if e.timestamp.startswith(month_prefix)
        )

        return BudgetSummary(
            total_cost_usd=total_cost,
            total_tokens=total_tok,
            entry_count=len(self._entries),
            daily_cost_usd=daily_cost,
            daily_tokens=daily_tok,
            daily_limit_usd=self.daily_limit_usd,
            monthly_cost_usd=monthly_cost,
            monthly_tokens=monthly_tok,
            monthly_limit_usd=self.monthly_limit_usd,
            daily_pct=daily_cost / self.daily_limit_usd if self.daily_limit_usd > 0 else 0.0,
            monthly_pct=monthly_cost / self.monthly_limit_usd if self.monthly_limit_usd > 0 else 0.0,
            degraded=daily_cost >= self.daily_limit_usd * self.warning_threshold,
        )

    def reset_daily(self) -> int:
        """Clear today's entries (for testing / manual reset). Returns count removed."""
        today_prefix = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        before = len(self._entries)
        self._entries = [
            e for e in self._entries if not e.timestamp.startswith(today_prefix)
        ]
        self._save()
        return before - len(self._entries)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _journal_path(self) -> Path:
        return self.data_dir / _DEFAULT_BUDGET_FILE

    def _load(self) -> None:
        path = self._journal_path()
        if path.exists():
            try:
                raw = json.loads(path.read_text())
                self._entries = [CostEntry(**e) for e in raw]
            except (json.JSONDecodeError, KeyError, TypeError):
                logger.warning("budget_journal_corrupt, starting fresh")
                self._entries = []

    def _save(self) -> None:
        path = self._journal_path()
        path.write_text(
            json.dumps(
                [asdict(e) for e in self._entries],
                indent=2,
            )
        )

    def _check_warnings(self) -> None:
        """Log warnings when approaching limits."""
        summary = self.summary()
        if summary.daily_pct >= self.warning_threshold:
            logger.warning(
                "budget_warning_daily: pct=%.1f%% cost=%.2f limit=%.2f",
                round(summary.daily_pct * 100, 1),
                round(summary.daily_cost_usd, 2),
                self.daily_limit_usd,
            )
        if summary.monthly_pct >= self.warning_threshold:
            logger.warning(
                "budget_warning_monthly: pct=%.1f%% cost=%.2f limit=%.2f",
                round(summary.monthly_pct * 100, 1),
                round(summary.monthly_cost_usd, 2),
                self.monthly_limit_usd,
            )
