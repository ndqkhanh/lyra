"""
Circuit Breaker pattern for protecting external dependencies.

The circuit breaker has three states:

* CLOSED  -- normal operation, calls pass through.
* OPEN    -- calls are rejected immediately; a recovery timeout is started.
* HALF_OPEN -- a probe call is allowed; success transitions back to
               CLOSED, failure transitions back to OPEN.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Generic, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(Enum):
    """Possible states of a CircuitBreaker."""

    CLOSED = auto()
    OPEN = auto()
    HALF_OPEN = auto()


class CircuitBreakerError(Exception):
    """Raised when a call is rejected because the circuit is OPEN."""


@dataclass
class CircuitBreaker(Generic[T]):
    """State-machine-based circuit breaker.

    The circuit starts CLOSED.  After *failure_threshold* consecutive
    failures it transitions to OPEN, rejecting all calls for
    *recovery_timeout* seconds.  After the timeout a probe call is
    allowed (HALF_OPEN).  If the probe succeeds the circuit resets to
    CLOSED; if it fails the circuit returns to OPEN.

    Parameters
    ----------
    failure_threshold:
        Number of consecutive failures before opening the circuit (default 5).
    recovery_timeout:
        Seconds to wait before transitioning to HALF_OPEN (default 30.0).

    Examples
    --------
    >>> cb = CircuitBreaker(failure_threshold=3, recovery_timeout=10.0)
    >>> cb.state
    <CircuitState.CLOSED: 1>
    """

    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False, repr=False)
    _failure_count: int = field(default=0, init=False, repr=False)
    _last_failure_time: float | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if self.recovery_timeout <= 0:
            raise ValueError("recovery_timeout must be > 0")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def state(self) -> CircuitState:
        """Current circuit state (CLOSED / OPEN / HALF_OPEN)."""
        self._maybe_transition_to_half_open()
        return self._state

    @property
    def failure_count(self) -> int:
        """Current consecutive failure count."""
        return self._failure_count

    def call(self, fn: ...) -> T:
        """Execute *fn* if the circuit is not OPEN.

        Raises
        ------
        CircuitBreakerError
            If the circuit is OPEN and not yet eligible for recovery.
        """
        self._maybe_transition_to_half_open()

        if self._state is CircuitState.OPEN:
            raise CircuitBreakerError("Circuit is OPEN; call rejected")

        try:
            result: T = fn()
        except Exception as exc:
            self._on_failure()
            raise exc

        self._on_success()
        return result

    async def acall(self, fn: ...) -> T:
        """Async variant of :meth:`call`.

        Usage::

            result = await cb.acall(some_async_function)
        """
        self._maybe_transition_to_half_open()

        if self._state is CircuitState.OPEN:
            raise CircuitBreakerError("Circuit is OPEN; call rejected")

        try:
            result: T = await fn()
        except Exception as exc:
            self._on_failure()
            raise exc

        self._on_success()
        return result

    def reset(self) -> None:
        """Manually reset the circuit to CLOSED and clear failure count."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _on_success(self) -> None:
        """Handle a successful call."""
        if self._state is CircuitState.HALF_OPEN:
            logger.info("Circuit HCO: probe succeeded, resetting to CLOSED")
            self.reset()
        else:
            # CLOSED: just reset the failure count on success
            self._failure_count = 0

    def _on_failure(self) -> None:
        """Handle a failed call."""
        self._failure_count += 1
        self._last_failure_time = time.monotonic()

        if self._state is CircuitState.HALF_OPEN:
            logger.warning("Circuit HCO: probe failed, returning to OPEN")
            self._state = CircuitState.OPEN
        elif self._failure_count >= self.failure_threshold:
            logger.warning(
                "Circuit HCO: failure count %d >= threshold %d, opening",
                self._failure_count,
                self.failure_threshold,
            )
            self._state = CircuitState.OPEN

    def _maybe_transition_to_half_open(self) -> None:
        """Check if the recovery timeout has elapsed and move to HALF_OPEN."""
        if self._state is not CircuitState.OPEN:
            return
        if self._last_failure_time is None:
            return

        elapsed = time.monotonic() - self._last_failure_time
        if elapsed >= self.recovery_timeout:
            logger.info("Circuit HCO: recovery timeout elapsed, transitioning to HALF_OPEN")
            self._state = CircuitState.HALF_OPEN
