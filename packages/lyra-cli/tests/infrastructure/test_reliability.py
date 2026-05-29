"""Tests for infrastructure reliability patterns."""

from __future__ import annotations

import time

import pytest
from lyra_cli.infrastructure.reliability import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    CircuitState,
    Fallback,
    ReliabilityManager,
    RetryConfig,
    RetryPolicy,
)


class TestCircuitBreaker:
    """Tests for CircuitBreaker."""

    def test_circuit_breaker_closed_state(self):
        """Test circuit breaker in closed state."""
        config = CircuitBreakerConfig(failure_threshold=3)
        cb = CircuitBreaker("test", config)

        assert cb.get_state() == CircuitState.CLOSED

        # Successful calls should keep circuit closed
        result = cb.call(lambda: "success")
        assert result == "success"
        assert cb.get_state() == CircuitState.CLOSED

    def test_circuit_breaker_opens_on_failures(self):
        """Test circuit breaker opens after threshold failures."""
        config = CircuitBreakerConfig(failure_threshold=3)
        cb = CircuitBreaker("test", config)

        # Fail 3 times to reach threshold
        for _ in range(3):
            with pytest.raises(ValueError):
                cb.call(lambda: (_ for _ in ()).throw(ValueError("test error")))

        assert cb.get_state() == CircuitState.OPEN

    def test_circuit_breaker_rejects_when_open(self):
        """Test circuit breaker rejects calls when open."""
        config = CircuitBreakerConfig(failure_threshold=2)
        cb = CircuitBreaker("test", config)

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(lambda: (_ for _ in ()).throw(ValueError("test error")))

        # Should reject immediately
        with pytest.raises(CircuitBreakerOpenError):
            cb.call(lambda: "success")

    def test_circuit_breaker_half_open_state(self):
        """Test circuit breaker transitions to half-open."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            timeout_seconds=0.1,
        )
        cb = CircuitBreaker("test", config)

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(lambda: (_ for _ in ()).throw(ValueError("test error")))

        assert cb.get_state() == CircuitState.OPEN

        # Wait for timeout
        time.sleep(0.2)

        # Next call should be allowed (half-open)
        result = cb.call(lambda: "success")
        assert result == "success"

    def test_circuit_breaker_closes_after_success(self):
        """Test circuit breaker closes after successful recovery."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            success_threshold=2,
            timeout_seconds=0.1,
        )
        cb = CircuitBreaker("test", config)

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(lambda: (_ for _ in ()).throw(ValueError("test error")))

        # Wait for timeout
        time.sleep(0.2)

        # Succeed twice to close
        cb.call(lambda: "success")
        cb.call(lambda: "success")

        assert cb.get_state() == CircuitState.CLOSED

    def test_circuit_breaker_reset(self):
        """Test manually resetting circuit breaker."""
        config = CircuitBreakerConfig(failure_threshold=2)
        cb = CircuitBreaker("test", config)

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(lambda: (_ for _ in ()).throw(ValueError("test error")))

        assert cb.get_state() == CircuitState.OPEN

        # Reset
        cb.reset()
        assert cb.get_state() == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_breaker_async(self):
        """Test circuit breaker with async functions."""
        config = CircuitBreakerConfig(failure_threshold=2)
        cb = CircuitBreaker("test", config)

        async def async_success():
            return "success"

        result = await cb.call_async(async_success)
        assert result == "success"


class TestRetryPolicy:
    """Tests for RetryPolicy."""

    def test_retry_success_on_first_attempt(self):
        """Test retry with immediate success."""
        config = RetryConfig(max_attempts=3)
        policy = RetryPolicy(config)

        result = policy.execute(lambda: "success")
        assert result == "success"

    def test_retry_success_after_failures(self):
        """Test retry succeeds after initial failures."""
        config = RetryConfig(max_attempts=3, initial_delay=0.01)
        policy = RetryPolicy(config)

        attempts = [0]

        def flaky_function():
            attempts[0] += 1
            if attempts[0] < 3:
                raise ValueError("temporary error")
            return "success"

        result = policy.execute(flaky_function)
        assert result == "success"
        assert attempts[0] == 3

    def test_retry_exhausts_attempts(self):
        """Test retry exhausts all attempts."""
        config = RetryConfig(max_attempts=3, initial_delay=0.01)
        policy = RetryPolicy(config)

        attempts = [0]

        def always_fails():
            attempts[0] += 1
            raise ValueError("permanent error")

        with pytest.raises(ValueError):
            policy.execute(always_fails)

        assert attempts[0] == 3

    def test_retry_exponential_backoff(self):
        """Test retry uses exponential backoff."""
        config = RetryConfig(
            max_attempts=3,
            initial_delay=0.1,
            exponential_base=2.0,
            jitter=False,
        )
        policy = RetryPolicy(config)


        def failing_function():
            raise ValueError("error")

        start_time = time.time()
        with pytest.raises(ValueError):
            policy.execute(failing_function)
        total_time = time.time() - start_time

        # Should have delays of ~0.1s and ~0.2s (total ~0.3s)
        assert total_time >= 0.3

    @pytest.mark.asyncio
    async def test_retry_async(self):
        """Test retry with async functions."""
        config = RetryConfig(max_attempts=3, initial_delay=0.01)
        policy = RetryPolicy(config)

        attempts = [0]

        async def flaky_async():
            attempts[0] += 1
            if attempts[0] < 2:
                raise ValueError("temporary error")
            return "success"

        result = await policy.execute_async(flaky_async)
        assert result == "success"
        assert attempts[0] == 2


class TestFallback:
    """Tests for Fallback."""

    def test_fallback_uses_primary(self):
        """Test fallback uses primary when it succeeds."""
        def primary():
            return "primary"
        def fallback_func():
            return "fallback"

        fallback = Fallback(primary, fallback_func)
        result = fallback.execute()

        assert result == "primary"

    def test_fallback_uses_fallback_on_error(self):
        """Test fallback uses fallback when primary fails."""
        def primary():
            raise ValueError("primary failed")

        def fallback_func():
            return "fallback"

        fallback = Fallback(primary, fallback_func)
        result = fallback.execute()

        assert result == "fallback"

    def test_fallback_with_arguments(self):
        """Test fallback with function arguments."""
        def primary(x, y):
            raise ValueError("primary failed")

        def fallback_func(x, y):
            return x + y

        fallback = Fallback(primary, fallback_func)
        result = fallback.execute(2, 3)

        assert result == 5

    @pytest.mark.asyncio
    async def test_fallback_async(self):
        """Test fallback with async functions."""
        async def primary():
            raise ValueError("primary failed")

        async def fallback_func():
            return "fallback"

        fallback = Fallback(primary, fallback_func)
        result = await fallback.execute_async()

        assert result == "fallback"


class TestReliabilityManager:
    """Tests for ReliabilityManager."""

    def test_get_circuit_breaker(self):
        """Test getting circuit breaker."""
        manager = ReliabilityManager()

        cb1 = manager.get_circuit_breaker("test")
        cb2 = manager.get_circuit_breaker("test")

        assert cb1 is cb2  # Should return same instance

    def test_get_retry_policy(self):
        """Test getting retry policy."""
        manager = ReliabilityManager()

        policy1 = manager.get_retry_policy("test")
        policy2 = manager.get_retry_policy("test")

        assert policy1 is policy2  # Should return same instance

    def test_execute_with_circuit_breaker(self):
        """Test executing with circuit breaker."""
        manager = ReliabilityManager()

        result = manager.execute_with_reliability(
            lambda: "success",
            circuit_breaker_name="test",
        )

        assert result == "success"

    def test_execute_with_retry(self):
        """Test executing with retry policy."""
        manager = ReliabilityManager()

        attempts = [0]

        def flaky_function():
            attempts[0] += 1
            if attempts[0] < 2:
                raise ValueError("temporary error")
            return "success"

        config = RetryConfig(max_attempts=3, initial_delay=0.01)
        manager.get_retry_policy("test", config)

        result = manager.execute_with_reliability(
            flaky_function,
            retry_policy_name="test",
        )

        assert result == "success"
        assert attempts[0] == 2

    def test_execute_with_fallback(self):
        """Test executing with fallback."""
        manager = ReliabilityManager()

        def primary():
            raise ValueError("primary failed")

        def fallback_func():
            return "fallback"

        result = manager.execute_with_reliability(
            primary,
            fallback_func=fallback_func,
        )

        assert result == "fallback"

    def test_execute_with_all_patterns(self):
        """Test executing with all reliability patterns."""
        manager = ReliabilityManager()

        attempts = [0]

        def flaky_function():
            attempts[0] += 1
            if attempts[0] < 2:
                raise ValueError("temporary error")
            return "success"

        def fallback_func():
            return "fallback"

        config = RetryConfig(max_attempts=3, initial_delay=0.01)
        manager.get_retry_policy("test", config)

        result = manager.execute_with_reliability(
            flaky_function,
            circuit_breaker_name="test",
            retry_policy_name="test",
            fallback_func=fallback_func,
        )

        assert result == "success"

    def test_get_status(self):
        """Test getting reliability status."""
        manager = ReliabilityManager()

        # Create some components
        manager.get_circuit_breaker("cb1")
        manager.get_retry_policy("retry1")

        status = manager.get_status()

        assert "circuit_breakers" in status
        assert "retry_policies" in status
        assert "cb1" in status["circuit_breakers"]
        assert "retry1" in status["retry_policies"]
