"""Error handling utilities with retry logic for Lyra.

Provides exponential backoff, circuit breakers, and graceful degradation.
"""

from __future__ import annotations

import logging
from functools import wraps
from typing import Any, Callable, TypeVar

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


def retry_on_api_error(
    max_attempts: int = 3,
    min_wait: int = 4,
    max_wait: int = 10,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Retry decorator for API calls with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time in seconds
        max_wait: Maximum wait time in seconds

    Returns:
        Decorated function with retry logic

    Example:
        >>> @retry_on_api_error(max_attempts=3)
        ... async def call_llm_api(prompt: str) -> str:
        ...     return await client.complete(prompt)
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
            retry=retry_if_exception_type((ConnectionError, TimeoutError)),
            reraise=True,
        )
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(
                    f"api_call_failed: {func.__name__}, error: {str(e)}"
                )
                raise

        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
            retry=retry_if_exception_type((ConnectionError, TimeoutError)),
            reraise=True,
        )
        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(
                    f"api_call_failed: {func.__name__}, error: {str(e)}"
                )
                raise

        # Return appropriate wrapper based on function type
        import inspect

        if inspect.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator


class CircuitBreaker:
    """Circuit breaker pattern for fault tolerance.

    Prevents cascading failures by stopping requests to failing services.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type[Exception] = Exception,
    ):
        """Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type to catch
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time: float | None = None
        self.state = "closed"  # closed, open, half_open

    def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            Exception: If circuit is open or function fails
        """
        import time

        if self.state == "open":
            if (
                self.last_failure_time
                and time.time() - self.last_failure_time > self.recovery_timeout
            ):
                self.state = "half_open"
                logger.info(f"circuit_breaker_half_open: {func.__name__}")
            else:
                raise Exception(f"Circuit breaker is OPEN for {func.__name__}")

        try:
            result = func(*args, **kwargs)
            if self.state == "half_open":
                self.state = "closed"
                self.failure_count = 0
                logger.info(f"circuit_breaker_closed: {func.__name__}")
            return result
        except self.expected_exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                logger.error(
                    f"circuit_breaker_opened: {func.__name__}, failures: {self.failure_count}"
                )

            raise e


def with_fallback(
    fallback_value: T,
    log_error: bool = True,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for graceful degradation with fallback value.

    Args:
        fallback_value: Value to return on error
        log_error: Whether to log errors

    Returns:
        Decorated function with fallback

    Example:
        >>> @with_fallback(fallback_value="default response")
        ... def get_llm_response(prompt: str) -> str:
        ...     return call_api(prompt)
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_error:
                    logger.warning(
                        f"fallback_triggered: {func.__name__}, error: {str(e)}, fallback: {fallback_value}"
                    )
                return fallback_value

        return wrapper

    return decorator


__all__ = [
    "retry_on_api_error",
    "CircuitBreaker",
    "with_fallback",
]
