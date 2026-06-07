"""
Tests for CircuitBreaker state machine.
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, Mock

import pytest

from src.reliability.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerError,
    CircuitState,
)


# ------------------------------------------------------------------
# CircuitBreaker state transitions
# ------------------------------------------------------------------


class TestCircuitBreakerState:
    """CircuitBreaker state-machine correctness."""

    def test_initial_state_is_closed(self):
        """A fresh circuit breaker is CLOSED."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=10.0)
        assert cb.state is CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_transitions_to_open_after_threshold(self):
        """After N consecutive failures the circuit opens."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)
        fn = Mock(side_effect=ValueError("fail"))

        for _ in range(3):
            with pytest.raises(ValueError):
                cb.call(fn)

        assert cb.state is CircuitState.OPEN
        assert cb.failure_count == 3

    def test_rejects_calls_when_open(self):
        """Calls are rejected with CircuitBreakerError when OPEN."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60.0)
        fn_fail = Mock(side_effect=ValueError("fail"))

        with pytest.raises(ValueError):
            cb.call(fn_fail)

        with pytest.raises(CircuitBreakerError, match="Circuit is OPEN"):
            cb.call(Mock(return_value="ok"))

    def test_transitions_to_half_open_after_timeout(self):
        """After recovery_timeout the circuit transitions to HALF_OPEN."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.05)

        with pytest.raises(ValueError):
            cb.call(Mock(side_effect=ValueError("fail")))

        assert cb.state is CircuitState.OPEN

        time.sleep(0.06)

        # Accessing .state triggers the check
        assert cb.state is CircuitState.HALF_OPEN

    def test_probe_success_resets_to_closed(self):
        """A successful call in HALF_OPEN resets the circuit to CLOSED."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.05)

        # Open the circuit
        with pytest.raises(ValueError):
            cb.call(Mock(side_effect=ValueError("fail")))

        time.sleep(0.06)
        assert cb.state is CircuitState.HALF_OPEN

        # Successful probe
        cb.call(Mock(return_value="ok"))

        assert cb.state is CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_probe_failure_stays_open(self):
        """A failed call in HALF_OPEN returns the circuit to OPEN."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.05)

        with pytest.raises(ValueError):
            cb.call(Mock(side_effect=ValueError("fail")))

        time.sleep(0.06)
        assert cb.state is CircuitState.HALF_OPEN

        # Failed probe
        with pytest.raises(RuntimeError):
            cb.call(Mock(side_effect=RuntimeError("probe fail")))

        assert cb.state is CircuitState.OPEN
        assert cb.failure_count == 2

    def test_reset_clears_state(self):
        """reset() returns the circuit to CLOSED with zero failures."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=60.0)

        with pytest.raises(ValueError):
            cb.call(Mock(side_effect=ValueError("fail")))
        with pytest.raises(ValueError):
            cb.call(Mock(side_effect=ValueError("fail")))

        assert cb.state is CircuitState.OPEN

        cb.reset()
        assert cb.state is CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_success_in_closed_resets_failure_count(self):
        """A successful call while CLOSED resets the failure count to 0."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)

        # Two failures
        with pytest.raises(ValueError):
            cb.call(Mock(side_effect=ValueError("fail")))
        with pytest.raises(ValueError):
            cb.call(Mock(side_effect=ValueError("fail")))

        assert cb.failure_count == 2

        # Then success resets count
        cb.call(Mock(return_value="ok"))
        assert cb.failure_count == 0
        assert cb.state is CircuitState.CLOSED


# ------------------------------------------------------------------
# CircuitBreaker async call
# ------------------------------------------------------------------


class TestCircuitBreakerAsync:
    """CircuitBreaker.acall() behaviour."""

    @pytest.mark.asyncio
    async def test_acall_success(self):
        """acall() returns the result when the async function succeeds."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=10.0)
        fn = AsyncMock(return_value="ok")

        result = await cb.acall(fn)

        assert result == "ok"

    @pytest.mark.asyncio
    async def test_acall_rejected_when_open(self):
        """acall() raises CircuitBreakerError when the circuit is OPEN."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60.0)

        with pytest.raises(ValueError):
            await cb.acall(AsyncMock(side_effect=ValueError("fail")))

        with pytest.raises(CircuitBreakerError):
            await cb.acall(AsyncMock(return_value="ok"))


# ------------------------------------------------------------------
# Validation
# ------------------------------------------------------------------


class TestCircuitBreakerValidation:
    """CircuitBreaker parameter validation."""

    def test_invalid_failure_threshold(self):
        with pytest.raises(ValueError, match="failure_threshold must be >= 1"):
            CircuitBreaker(failure_threshold=0)

    def test_invalid_recovery_timeout(self):
        with pytest.raises(ValueError, match="recovery_timeout must be > 0"):
            CircuitBreaker(recovery_timeout=0)
