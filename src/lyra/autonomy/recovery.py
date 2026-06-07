"""Crash recovery with escalating actions — restart, rollback, escalate."""

from dataclasses import dataclass, field
from enum import Enum
import time


class RecoveryAction(str, Enum):
    RETRY = "retry"           # Retry the same task
    ROLLBACK = "rollback"     # Rollback to last checkpoint
    SKIP = "skip"             # Skip the failing task
    ESCALATE = "escalate"     # Escalate to human / halt


@dataclass
class CrashRecovery:
    """Escalating crash recovery: retry → rollback → skip → escalate."""

    max_retries: int = 3
    retry_delay: float = 1.0  # seconds
    escalation_order: list[RecoveryAction] = field(default_factory=lambda: [
        RecoveryAction.RETRY,
        RecoveryAction.RETRY,
        RecoveryAction.RETRY,
        RecoveryAction.ROLLBACK,
        RecoveryAction.SKIP,
        RecoveryAction.ESCALATE,
    ])

    _failure_timestamps: list[float] = field(default_factory=list)
    _recovery_index: int = 0

    @property
    def current_action(self) -> RecoveryAction:
        idx = min(self._recovery_index, len(self.escalation_order) - 1)
        return self.escalation_order[idx]

    @property
    def should_escalate(self) -> bool:
        return self.current_action == RecoveryAction.ESCALATE

    def record_failure(self):
        self._failure_timestamps.append(time.time())
        self._recovery_index += 1

    def record_success(self):
        self._failure_timestamps.clear()
        self._recovery_index = 0

    def failure_rate(self, window_seconds: float = 300) -> float:
        """Failures per minute in the recent window."""
        cutoff = time.time() - window_seconds
        recent = [t for t in self._failure_timestamps if t > cutoff]
        return len(recent) / (window_seconds / 60)

    def stats(self) -> dict:
        return {
            "total_failures": len(self._failure_timestamps),
            "recovery_level": self._recovery_index,
            "current_action": self.current_action.value,
            "should_escalate": self.should_escalate,
            "failure_rate_per_min": round(self.failure_rate(), 2),
        }
