"""Retry Policy - Configurable retry with exponential backoff and jitter."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from enum import StrEnum


class RetryDecision(StrEnum):
    """Decision after evaluating retry policy."""

    RETRY = "retry"
    ABORT = "abort"
    ESCALATE = "escalate"


@dataclass(frozen=True)
class RetryConfig:
    """Configuration for retry behavior."""

    max_retries: int = 3
    base_delay_ms: int = 1000
    max_delay_ms: int = 60000
    backoff_factor: float = 2.0
    jitter_pct: float = 0.1
    retryable_categories: tuple[str, ...] = (
        "transient",
        "timeout",
        "resource",
    )


@dataclass(frozen=True)
class RetryResult:
    """Result of a retry evaluation."""

    decision: RetryDecision
    delay_ms: int = 0
    attempts_used: int = 0
    total_time_ms: float = 0.0
    reason: str = ""


class RetryPolicy:
    """Retry policy with exponential backoff and jitter.

    Features:
    - Configurable max retries
    - Exponential backoff with jitter
    - Category-based retry decisions
    - Max delay cap
    - Circuit breaker integration
    """

    def __init__(self, config: RetryConfig | None = None):
        self.config = config or RetryConfig()
        self._attempts: dict[str, int] = {}  # {error_key: attempts}
        self._last_attempt: dict[str, float] = {}  # {error_key: timestamp}
        self._total_retries = 0

    def should_retry(
        self,
        error_key: str,
        category: str,
        attempt: int | None = None,
    ) -> RetryResult:
        """Determine if a retry should be attempted.

        Args:
            error_key: Unique key for the error context
            category: Error category
            attempt: Current attempt number (auto-tracked if None)

        Returns:
            RetryResult with decision and delay
        """
        current_attempt = attempt if attempt is not None else self._attempts.get(error_key, 0)

        # Check if category is retryable
        if category not in self.config.retryable_categories:
            return RetryResult(
                decision=RetryDecision.ABORT,
                attempts_used=current_attempt,
                reason=f"Category '{category}' is not retryable",
            )

        # Check max retries
        if current_attempt >= self.config.max_retries:
            return RetryResult(
                decision=RetryDecision.ESCALATE,
                attempts_used=current_attempt,
                reason=f"Max retries ({self.config.max_retries}) exceeded",
            )

        # Calculate delay with exponential backoff
        delay = self._calculate_delay(current_attempt)
        self._attempts[error_key] = current_attempt + 1
        self._last_attempt[error_key] = time.time()
        self._total_retries += 1

        return RetryResult(
            decision=RetryDecision.RETRY,
            delay_ms=delay,
            attempts_used=current_attempt + 1,
            reason=f"Retry {current_attempt + 1}/{self.config.max_retries}",
        )

    def _calculate_delay(self, attempt: int) -> int:
        """Calculate delay with exponential backoff and jitter."""
        delay = self.config.base_delay_ms * (self.config.backoff_factor ** attempt)
        delay = min(delay, self.config.max_delay_ms)

        # Add jitter
        jitter = delay * self.config.jitter_pct * random.uniform(-1, 1)
        return max(0, int(delay + jitter))

    def reset(self, error_key: str) -> None:
        """Reset retry state for an error key."""
        self._attempts.pop(error_key, None)
        self._last_attempt.pop(error_key, None)

    def reset_all(self) -> None:
        """Reset all retry state."""
        self._attempts.clear()
        self._last_attempt.clear()

    def get_total_retries(self) -> int:
        """Get total retries across all operations."""
        return self._total_retries

    def get_retry_rate(self, total_operations: int) -> float:
        """Get retry rate per operation."""
        return self._total_retries / total_operations if total_operations > 0 else 0.0
