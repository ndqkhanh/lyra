"""Plan 11: Continuous Guard — autonomous operation safety rails.

Provides rate limiting, destructive operation blocking, cost/file quotas,
and pause-on-failure logic for safe autonomous agent operation.
"""

from __future__ import annotations

import re
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from re import Pattern

# ── Safety Constants ──────────────────────────────────────────────────────

MAX_CONSECUTIVE_FAILURES = 5
MAX_COST_PER_HOUR_USD = 2.00
MAX_FILES_PER_HOUR = 50
MAX_OPERATIONS_PER_MINUTE = 30

DESTRUCTIVE_PATTERNS: tuple[str, ...] = (
    r"rm\s+(-rf?\s+|--recursive\s+)",
    r"DROP\s+(TABLE|DATABASE|SCHEMA)\s+",
    r"DELETE\s+FROM\s+\w+",
    r"git\s+push\s+(-f|--force)",
    r"git\s+reset\s+--hard",
    r"TRUNCATE\s+(TABLE\s+)?\w+",
    r":\(\)\s*\{\s*:\|:&\s*\};:",  # fork bomb
)

SAFETY_RULES: tuple[str, ...] = (
    "Never execute destructive commands without user confirmation",
    "Never modify files outside the project workspace",
    "Never expose secrets or API keys in output",
    "Never execute code from untrusted sources",
    "Always validate inputs before processing",
    "Stop and report after 5 consecutive failures",
    "Respect budget and rate limits at all times",
)


class GuardAction(Enum):
    ALLOW = "allow"
    BLOCK = "block"
    WARN = "warn"
    PAUSE = "pause"
    ESCALATE = "escalate"


class GuardReason(Enum):
    DESTRUCTIVE_PATTERN = "destructive_pattern"
    RATE_LIMIT = "rate_limit"
    COST_LIMIT = "cost_limit"
    FILE_LIMIT = "file_limit"
    CONSECUTIVE_FAILURES = "consecutive_failures"
    SAFETY_RULE_VIOLATION = "safety_rule_violation"
    WORKSPACE_VIOLATION = "workspace_violation"
    OK = "ok"


# ── Data Models ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class GuardVerdict:
    """Result of a safety check on an operation.

    Attributes:
        action: What the guard decided to do.
        reason: Why the guard made this decision.
        detail: Human-readable explanation.
        timestamp: When the verdict was issued.
    """

    action: GuardAction
    reason: GuardReason
    detail: str = ""
    timestamp: float = field(default_factory=time.time)

    @property
    def is_allowed(self) -> bool:
        return self.action == GuardAction.ALLOW

    @property
    def is_blocked(self) -> bool:
        return self.action in (GuardAction.BLOCK, GuardAction.PAUSE)


@dataclass(frozen=True)
class OperationRecord:
    """A logged operation for quota tracking.

    Attributes:
        command: The operation/command string.
        timestamp: When it was executed.
        cost_usd: Cost incurred.
        files_touched: Files modified.
        success: Whether the operation succeeded.
    """

    command: str
    timestamp: float
    cost_usd: float = 0.0
    files_touched: int = 0
    success: bool = True


@dataclass(frozen=True)
class GuardState:
    """Immutable snapshot of the guard's current state.

    Attributes:
        consecutive_failures: Current streak of failures.
        total_cost_usd: Accumulated cost in this window.
        files_modified: Files changed in this window.
        operations_this_minute: Operations in the current minute.
        is_paused: Whether the guard has paused operations.
        pause_reason: Why operations were paused.
        window_start: Start of the current hourly window.
    """

    consecutive_failures: int = 0
    total_cost_usd: float = 0.0
    files_modified: int = 0
    operations_this_minute: int = 0
    is_paused: bool = False
    pause_reason: str = ""
    window_start: float = field(default_factory=time.time)


# ── Continuous Guard ──────────────────────────────────────────────────────


class ContinuousGuard:
    """Safety guardrails for autonomous agent operation.

    Enforces rate limits, destructive operation blocking, cost/file quotas,
    and pause-on-failure logic. All state transitions produce new immutable
    GuardState snapshots.

    Usage::

        guard = ContinuousGuard(workspace="/path/to/project")
        verdict = guard.check("rm -rf /tmp/cache")
        if verdict.is_allowed:
            guard.record("rm -rf /tmp/cache", cost_usd=0.0)
    """

    def __init__(
        self,
        workspace: str = "",
        max_consecutive_failures: int = MAX_CONSECUTIVE_FAILURES,
        max_cost_per_hour: float = MAX_COST_PER_HOUR_USD,
        max_files_per_hour: int = MAX_FILES_PER_HOUR,
        max_ops_per_minute: int = MAX_OPERATIONS_PER_MINUTE,
        destructive_patterns: tuple[str, ...] = DESTRUCTIVE_PATTERNS,
    ) -> None:
        self._workspace = workspace
        self._max_consecutive_failures = max_consecutive_failures
        self._max_cost_per_hour = max_cost_per_hour
        self._max_files_per_hour = max_files_per_hour
        self._max_ops_per_minute = max_ops_per_minute

        self._compiled_patterns: tuple[Pattern[str], ...] = tuple(
            re.compile(p, re.IGNORECASE) for p in destructive_patterns
        )

        self._history: deque[OperationRecord] = deque()
        self._state = GuardState()
        self._verdicts: deque[GuardVerdict] = deque(maxlen=100)

    # ── Read ──────────────────────────────────────────────────────────────

    @property
    def state(self) -> GuardState:
        return self._state

    @property
    def is_paused(self) -> bool:
        return self._state.is_paused

    @property
    def consecutive_failures(self) -> int:
        return self._state.consecutive_failures

    @property
    def total_cost(self) -> float:
        return self._state.total_cost_usd

    @property
    def files_modified(self) -> int:
        return self._state.files_modified

    @property
    def history(self) -> tuple[OperationRecord, ...]:
        return tuple(self._history)

    @property
    def recent_verdicts(self) -> tuple[GuardVerdict, ...]:
        return tuple(self._verdicts)

    # ── Core Check ────────────────────────────────────────────────────────

    def check(
        self, command: str, cost_estimate: float = 0.0, files_estimate: int = 0
    ) -> GuardVerdict:
        """Evaluate whether an operation should be allowed to proceed.

        Checks run in priority order: pause state → destructive patterns →
        rate limits → cost quota → file quota → failure streak.
        """
        if self._state.is_paused:
            return self._emit(
                GuardVerdict(
                    action=GuardAction.PAUSE,
                    reason=GuardReason.CONSECUTIVE_FAILURES,
                    detail=f"Guard is paused: {self._state.pause_reason}",
                )
            )

        # 1. Destructive pattern check
        for pattern in self._compiled_patterns:
            if pattern.search(command):
                return self._emit(
                    GuardVerdict(
                        action=GuardAction.BLOCK,
                        reason=GuardReason.DESTRUCTIVE_PATTERN,
                        detail=f"Command matches destructive pattern: {pattern.pattern}",
                    )
                )

        # 2. Rate limit check
        self._rotate_windows()
        if self._state.operations_this_minute >= self._max_ops_per_minute:
            return self._emit(
                GuardVerdict(
                    action=GuardAction.WARN,
                    reason=GuardReason.RATE_LIMIT,
                    detail=(
                        f"Rate limit reached: {self._state.operations_this_minute}/"
                        f"{self._max_ops_per_minute} ops/min"
                    ),
                )
            )

        # 3. Cost quota check
        if self._state.total_cost_usd + cost_estimate > self._max_cost_per_hour:
            return self._emit(
                GuardVerdict(
                    action=GuardAction.BLOCK,
                    reason=GuardReason.COST_LIMIT,
                    detail=(
                        f"Cost limit would be exceeded: $"
                        f"{self._state.total_cost_usd + cost_estimate:.2f} > $"
                        f"{self._max_cost_per_hour:.2f}"
                    ),
                )
            )

        # 4. File quota check
        if self._state.files_modified + files_estimate > self._max_files_per_hour:
            return self._emit(
                GuardVerdict(
                    action=GuardAction.BLOCK,
                    reason=GuardReason.FILE_LIMIT,
                    detail=(
                        f"File limit would be exceeded: "
                        f"{self._state.files_modified + files_estimate} > "
                        f"{self._max_files_per_hour}"
                    ),
                )
            )

        # 5. Consecutive failure check
        if self._state.consecutive_failures >= self._max_consecutive_failures:
            self._state = GuardState(
                consecutive_failures=self._state.consecutive_failures,
                total_cost_usd=self._state.total_cost_usd,
                files_modified=self._state.files_modified,
                operations_this_minute=self._state.operations_this_minute,
                is_paused=True,
                pause_reason=f"Reached {self._max_consecutive_failures} consecutive failures",
                window_start=self._state.window_start,
            )
            return self._emit(
                GuardVerdict(
                    action=GuardAction.PAUSE,
                    reason=GuardReason.CONSECUTIVE_FAILURES,
                    detail=(
                        f"Auto-paused after {self._max_consecutive_failures} consecutive failures"
                    ),
                )
            )

        return self._emit(
            GuardVerdict(
                action=GuardAction.ALLOW,
                reason=GuardReason.OK,
                detail="All safety checks passed",
            )
        )

    def is_destructive(self, command: str) -> bool:
        """Quick check if a command matches any destructive pattern."""
        return any(p.search(command) for p in self._compiled_patterns)

    # ── Record ────────────────────────────────────────────────────────────

    def record(
        self,
        command: str,
        cost_usd: float = 0.0,
        files_touched: int = 0,
        success: bool = True,
    ) -> GuardState:
        """Record an operation's outcome and update state."""
        self._rotate_windows()

        record = OperationRecord(
            command=command,
            timestamp=time.time(),
            cost_usd=cost_usd,
            files_touched=files_touched,
            success=success,
        )
        self._history.append(record)

        consecutive = 0 if success else self._state.consecutive_failures + 1
        is_paused = self._state.is_paused

        if consecutive >= self._max_consecutive_failures:
            is_paused = True

        self._state = GuardState(
            consecutive_failures=consecutive,
            total_cost_usd=self._state.total_cost_usd + cost_usd,
            files_modified=self._state.files_modified + files_touched,
            operations_this_minute=self._state.operations_this_minute + 1,
            is_paused=is_paused,
            pause_reason=f"Reached {consecutive} consecutive failures" if is_paused else "",
            window_start=self._state.window_start,
        )

        verdict = GuardVerdict(
            action=GuardAction.PAUSE if is_paused else GuardAction.ALLOW,
            reason=GuardReason.CONSECUTIVE_FAILURES if is_paused else GuardReason.OK,
            detail=f"Recorded {'failure' if not success else 'success'}: {command[:80]}",
        )
        self._verdicts.append(verdict)

        return self._state

    # ── Control ───────────────────────────────────────────────────────────

    def resume(self) -> GuardState:
        """Resume operations after a pause, resetting the failure counter."""
        self._state = GuardState(
            consecutive_failures=0,
            total_cost_usd=self._state.total_cost_usd,
            files_modified=self._state.files_modified,
            operations_this_minute=0,
            is_paused=False,
            pause_reason="",
            window_start=time.time(),
        )
        return self._state

    def reset_quotas(self) -> GuardState:
        """Reset all quotas and counters to start a fresh window."""
        self._state = GuardState(
            consecutive_failures=0,
            total_cost_usd=0.0,
            files_modified=0,
            operations_this_minute=0,
            is_paused=False,
            pause_reason="",
            window_start=time.time(),
        )
        return self._state

    def acknowledge_failure(self) -> GuardState:
        """Increment the failure counter without recording a full operation."""
        consecutive = self._state.consecutive_failures + 1
        is_paused = consecutive >= self._max_consecutive_failures

        self._state = GuardState(
            consecutive_failures=consecutive,
            total_cost_usd=self._state.total_cost_usd,
            files_modified=self._state.files_modified,
            operations_this_minute=self._state.operations_this_minute + 1,
            is_paused=is_paused,
            pause_reason=f"Reached {consecutive} consecutive failures" if is_paused else "",
            window_start=self._state.window_start,
        )
        return self._state

    # ── Stats ─────────────────────────────────────────────────────────────

    def stats(self) -> dict:
        """Return summary statistics for monitoring."""
        self._rotate_windows()
        return {
            "consecutive_failures": self._state.consecutive_failures,
            "total_cost_usd": round(self._state.total_cost_usd, 4),
            "files_modified": self._state.files_modified,
            "operations_this_minute": self._state.operations_this_minute,
            "is_paused": self._state.is_paused,
            "pause_reason": self._state.pause_reason,
            "total_operations": len(self._history),
            "success_rate": self._compute_success_rate(),
            "cost_per_hour_limit": self._max_cost_per_hour,
            "files_per_hour_limit": self._max_files_per_hour,
        }

    # ── Internal ──────────────────────────────────────────────────────────

    def _emit(self, verdict: GuardVerdict) -> GuardVerdict:
        self._verdicts.append(verdict)
        return verdict

    def _rotate_windows(self) -> None:
        """Reset per-minute and per-hour counters when windows expire."""
        now = time.time()

        # Per-hour window
        if now - self._state.window_start > 3600:
            self._state = GuardState(
                consecutive_failures=self._state.consecutive_failures,
                total_cost_usd=0.0,
                files_modified=0,
                operations_this_minute=0,
                is_paused=self._state.is_paused,
                pause_reason=self._state.pause_reason,
                window_start=now,
            )
            # Prune old history entries
            cutoff = now - 3600
            while self._history and self._history[0].timestamp < cutoff:
                self._history.popleft()

    def _compute_success_rate(self) -> float:
        if not self._history:
            return 1.0
        successes = sum(1 for r in self._history if r.success)
        return successes / len(self._history)


# ── Pre-configured Instances ──────────────────────────────────────────────


def create_default_guard(workspace: str = "") -> ContinuousGuard:
    """Create a ContinuousGuard with default safety settings."""
    return ContinuousGuard(workspace=workspace)


def create_lenient_guard(workspace: str = "") -> ContinuousGuard:
    """Create a lenient guard for low-risk environments."""
    return ContinuousGuard(
        workspace=workspace,
        max_consecutive_failures=10,
        max_cost_per_hour=10.0,
        max_files_per_hour=200,
        max_ops_per_minute=60,
    )


def create_strict_guard(workspace: str = "") -> ContinuousGuard:
    """Create a strict guard for high-risk or production environments."""
    return ContinuousGuard(
        workspace=workspace,
        max_consecutive_failures=2,
        max_cost_per_hour=0.50,
        max_files_per_hour=10,
        max_ops_per_minute=10,
        destructive_patterns=DESTRUCTIVE_PATTERNS
        + (
            r"git\s+push",
            r"kubectl\s+delete",
            r"terraform\s+destroy",
        ),
    )
