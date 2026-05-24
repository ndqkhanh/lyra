"""Retry policies — pluggable strategies for transient tool failures.

Two built-ins:

    - :class:`NoRetry` — single attempt; fail immediately on first error.
    - :class:`ExponentialBackoff` — retry up to N times with exponential delay
      when the error message matches one of ``retriable_substrings``.

Production may wire custom policies (e.g., circuit-breaker, jittered backoff)
through the same :class:`RetryPolicy` Protocol from ``types.py``.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class NoRetry:
    """Single-attempt policy. Fails fast on first error."""

    max_attempts: int = 1

    def should_retry(self, *, attempt: int, error: str) -> bool:
        return False

    def delay_seconds(self, *, attempt: int) -> float:
        return 0.0


@dataclass
class ExponentialBackoff:
    """Retry on transient failures with exponential delay.

    ``retriable_substrings`` are matched case-insensitively against the error
    message; only matching errors trigger a retry. This avoids retrying
    deterministic failures (validation errors, permission denials) where a
    repeat would just fail again.

    >>> policy = ExponentialBackoff(max_attempts=3, base_delay=0.0, multiplier=2.0)
    >>> policy.should_retry(attempt=1, error="upstream timeout")
    True
    >>> policy.should_retry(attempt=1, error="invalid argument")
    False
    >>> policy.delay_seconds(attempt=2)
    0.0
    """

    max_attempts: int = 3
    base_delay: float = 0.0
    multiplier: float = 2.0
    retriable_substrings: tuple[str, ...] = (
        "timeout",
        "rate limit",
        "rate-limit",
        "connection",
        "503",
        "504",
        "temporarily unavailable",
    )

    def should_retry(self, *, attempt: int, error: str) -> bool:
        if attempt >= self.max_attempts:
            return False
        err_lc = error.lower()
        return any(sub.lower() in err_lc for sub in self.retriable_substrings)

    def delay_seconds(self, *, attempt: int) -> float:
        # attempt is 1-indexed and just failed → next-attempt delay = base * mult^(attempt-1).
        if attempt < 1:
            return 0.0
        return self.base_delay * (self.multiplier ** (attempt - 1))


__all__ = ["ExponentialBackoff", "NoRetry"]
