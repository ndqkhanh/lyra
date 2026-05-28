"""Reliability patterns: circuit breakers, retries, and fallbacks.

Provides production-grade reliability features:
- Circuit breaker pattern to prevent cascading failures
- Configurable retry policies with exponential backoff
- Fallback mechanisms for graceful degradation
- Unified reliability manager
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional, TypeVar

from lyra_cli.logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""

    failure_threshold: int = 5  # Failures before opening
    success_threshold: int = 2  # Successes to close from half-open
    timeout_seconds: float = 60.0  # Time before trying half-open
    half_open_max_calls: int = 3  # Max calls in half-open state


class CircuitBreaker:
    """Circuit breaker pattern implementation.

    Prevents cascading failures by stopping requests to failing services.
    Automatically recovers when service becomes healthy.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Service failing, requests rejected immediately
    - HALF_OPEN: Testing recovery, limited requests allowed
    """

    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        """Initialize circuit breaker.

        Args:
            name: Circuit breaker name for logging
            config: Configuration (uses defaults if not provided)
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.half_open_calls = 0

    def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerOpenError: If circuit is open
            Exception: Original exception from function
        """
        if not self._allow_request():
            raise CircuitBreakerOpenError(
                f"Circuit breaker {self.name} is OPEN"
            )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    async def call_async(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute async function with circuit breaker protection.

        Args:
            func: Async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerOpenError: If circuit is open
            Exception: Original exception from function
        """
        if not self._allow_request():
            raise CircuitBreakerOpenError(
                f"Circuit breaker {self.name} is OPEN"
            )

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _allow_request(self) -> bool:
        """Check if request should be allowed."""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if timeout expired
            if self.last_failure_time is None:
                return False

            elapsed = time.time() - self.last_failure_time
            if elapsed >= self.config.timeout_seconds:
                logger.info(f"Circuit breaker {self.name} entering HALF_OPEN state")
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            # Allow limited requests in half-open state
            if self.half_open_calls < self.config.half_open_max_calls:
                self.half_open_calls += 1
                return True
            return False

        return False

    def _on_success(self) -> None:
        """Handle successful request."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                logger.info(f"Circuit breaker {self.name} closing (recovered)")
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0

    def _on_failure(self) -> None:
        """Handle failed request."""
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            logger.warning(f"Circuit breaker {self.name} opening (recovery failed)")
            self.state = CircuitState.OPEN
            self.success_count = 0
        elif self.state == CircuitState.CLOSED:
            self.failure_count += 1
            if self.failure_count >= self.config.failure_threshold:
                logger.warning(
                    f"Circuit breaker {self.name} opening "
                    f"(threshold {self.config.failure_threshold} reached)"
                )
                self.state = CircuitState.OPEN

    def reset(self) -> None:
        """Manually reset circuit breaker to closed state."""
        logger.info(f"Circuit breaker {self.name} manually reset")
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None

    def get_state(self) -> CircuitState:
        """Get current circuit state."""
        return self.state


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""

    pass


@dataclass
class RetryConfig:
    """Configuration for retry policy."""

    max_attempts: int = 3
    initial_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True


class RetryPolicy:
    """Retry policy with exponential backoff.

    Features:
    - Configurable max attempts
    - Exponential backoff
    - Optional jitter to prevent thundering herd
    - Exception filtering
    """

    def __init__(self, config: Optional[RetryConfig] = None):
        """Initialize retry policy.

        Args:
            config: Retry configuration (uses defaults if not provided)
        """
        self.config = config or RetryConfig()

    def execute(
        self,
        func: Callable[..., T],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Execute function with retry logic.

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            Exception: Last exception if all retries failed
        """
        last_exception = None

        for attempt in range(self.config.max_attempts):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.config.max_attempts - 1:
                    delay = self._calculate_delay(attempt)
                    logger.warning(
                        f"Retry attempt {attempt + 1}/{self.config.max_attempts} "
                        f"failed, retrying in {delay:.2f}s: {e}"
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"All {self.config.max_attempts} retry attempts failed"
                    )

        raise last_exception  # type: ignore

    async def execute_async(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute async function with retry logic.

        Args:
            func: Async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            Exception: Last exception if all retries failed
        """
        last_exception = None

        for attempt in range(self.config.max_attempts):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.config.max_attempts - 1:
                    delay = self._calculate_delay(attempt)
                    logger.warning(
                        f"Retry attempt {attempt + 1}/{self.config.max_attempts} "
                        f"failed, retrying in {delay:.2f}s: {e}"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"All {self.config.max_attempts} retry attempts failed"
                    )

        raise last_exception  # type: ignore

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt with exponential backoff."""
        delay = min(
            self.config.initial_delay * (self.config.exponential_base ** attempt),
            self.config.max_delay,
        )

        if self.config.jitter:
            import random
            delay *= random.uniform(0.5, 1.5)

        return delay


class Fallback:
    """Fallback mechanism for graceful degradation.

    Provides alternative behavior when primary operation fails.
    """

    def __init__(
        self,
        primary: Callable[..., T],
        fallback: Callable[..., T],
        name: str = "fallback",
    ):
        """Initialize fallback.

        Args:
            primary: Primary function to try
            fallback: Fallback function if primary fails
            name: Name for logging
        """
        self.primary = primary
        self.fallback = fallback
        self.name = name

    def execute(self, *args: Any, **kwargs: Any) -> T:
        """Execute with fallback.

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Result from primary or fallback function
        """
        try:
            return self.primary(*args, **kwargs)
        except Exception as e:
            logger.warning(
                f"Primary function failed in {self.name}, using fallback: {e}"
            )
            return self.fallback(*args, **kwargs)

    async def execute_async(self, *args: Any, **kwargs: Any) -> Any:
        """Execute async with fallback.

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Result from primary or fallback function
        """
        try:
            return await self.primary(*args, **kwargs)
        except Exception as e:
            logger.warning(
                f"Primary function failed in {self.name}, using fallback: {e}"
            )
            return await self.fallback(*args, **kwargs)


class ReliabilityManager:
    """Unified reliability manager.

    Combines circuit breakers, retries, and fallbacks for comprehensive
    reliability patterns.
    """

    def __init__(self):
        """Initialize reliability manager."""
        self._circuit_breakers: dict[str, CircuitBreaker] = {}
        self._retry_policies: dict[str, RetryPolicy] = {}

    def get_circuit_breaker(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
    ) -> CircuitBreaker:
        """Get or create a circuit breaker.

        Args:
            name: Circuit breaker name
            config: Configuration (uses defaults if not provided)

        Returns:
            Circuit breaker instance
        """
        if name not in self._circuit_breakers:
            self._circuit_breakers[name] = CircuitBreaker(name, config)
        return self._circuit_breakers[name]

    def get_retry_policy(
        self,
        name: str,
        config: Optional[RetryConfig] = None,
    ) -> RetryPolicy:
        """Get or create a retry policy.

        Args:
            name: Policy name
            config: Configuration (uses defaults if not provided)

        Returns:
            Retry policy instance
        """
        if name not in self._retry_policies:
            self._retry_policies[name] = RetryPolicy(config)
        return self._retry_policies[name]

    def execute_with_reliability(
        self,
        func: Callable[..., T],
        circuit_breaker_name: Optional[str] = None,
        retry_policy_name: Optional[str] = None,
        fallback_func: Optional[Callable[..., T]] = None,
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Execute function with full reliability patterns.

        Args:
            func: Function to execute
            circuit_breaker_name: Circuit breaker to use (optional)
            retry_policy_name: Retry policy to use (optional)
            fallback_func: Fallback function (optional)
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result
        """
        # Apply patterns in order: retry -> circuit breaker -> fallback
        # This ensures retries happen before fallback is triggered

        # Wrap with retry if provided
        if retry_policy_name:
            retry_policy = self.get_retry_policy(retry_policy_name)
            original_func = func
            func = lambda *a, **kw: retry_policy.execute(original_func, *a, **kw)

        # Wrap with circuit breaker if provided
        if circuit_breaker_name:
            circuit_breaker = self.get_circuit_breaker(circuit_breaker_name)
            original_func = func
            func = lambda *a, **kw: circuit_breaker.call(original_func, *a, **kw)

        # Wrap with fallback if provided (outermost layer)
        if fallback_func:
            fallback = Fallback(func, fallback_func, "reliability_manager")
            return fallback.execute(*args, **kwargs)

        return func(*args, **kwargs)

    def get_status(self) -> dict[str, Any]:
        """Get status of all reliability components.

        Returns:
            Status dictionary
        """
        return {
            "circuit_breakers": {
                name: {
                    "state": cb.get_state().value,
                    "failure_count": cb.failure_count,
                    "success_count": cb.success_count,
                }
                for name, cb in self._circuit_breakers.items()
            },
            "retry_policies": {
                name: {
                    "max_attempts": policy.config.max_attempts,
                    "initial_delay": policy.config.initial_delay,
                }
                for name, policy in self._retry_policies.items()
            },
        }


__all__ = [
    "CircuitState",
    "CircuitBreakerConfig",
    "CircuitBreaker",
    "CircuitBreakerOpenError",
    "RetryConfig",
    "RetryPolicy",
    "Fallback",
    "ReliabilityManager",
]
