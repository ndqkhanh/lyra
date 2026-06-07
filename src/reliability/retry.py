"""
Retry with exponential backoff and jitter.

Provides:
- RetryPolicy: configuration dataclass.
- async retry(): wraps any async callable with configurable retry logic.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Awaitable])

# Maximum delay cap to prevent unbounded growth
_MAX_CAP = 3600.0  # 1 hour


@dataclass
class RetryPolicy:
    """Configuration for retry behaviour.

    Attributes
    ----------
    max_retries:
        Maximum number of retry attempts (default 3).
    base_delay:
        Initial delay in seconds before the first retry (default 1.0).
    max_delay:
        Maximum delay in seconds between retries (default 60.0).
    jitter:
        If True, randomise delay by +/- 50% to avoid thundering-herd
        effects (default True).
    """

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    jitter: bool = True

    def __post_init__(self) -> None:
        if self.max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        if self.base_delay < 0:
            raise ValueError("base_delay must be >= 0")
        if self.max_delay < 0:
            raise ValueError("max_delay must be >= 0")
        if self.max_delay > _MAX_CAP:
            raise ValueError(f"max_delay cannot exceed {_MAX_CAP}s")


class RetryExhaustedError(Exception):
    """Raised when all retry attempts have been exhausted."""


async def retry(
    fn: Callable[..., Awaitable],
    *args: object,
    policy: RetryPolicy | None = None,
    **kwargs: object,
) -> object:
    """Execute *fn* asynchronously with exponential-backoff retry.

    Parameters
    ----------
    fn:
        The async callable to invoke.
    *args:
        Positional arguments forwarded to *fn*.
    policy:
        RetryPolicy controlling retry behaviour.  Uses the default policy
        (3 retries, 1s base, 60s cap, jitter enabled) when *None*.
    **kwargs:
        Keyword arguments forwarded to *fn*.

    Returns
    -------
    The return value of the successful invocation.

    Raises
    ------
    RetryExhaustedError
        If all attempts fail.  The final exception from *fn* is chained.
    """
    policy = policy or RetryPolicy()
    last_exception: Exception | None = None

    for attempt in range(policy.max_retries + 1):
        try:
            return await fn(*args, **kwargs)
        except Exception as exc:
            last_exception = exc
            logger.debug(
                "Retry attempt %d/%d failed: %s",
                attempt + 1,
                policy.max_retries + 1,
                exc,
            )

            if attempt < policy.max_retries:
                delay = _compute_delay(attempt, policy)
                await asyncio.sleep(delay)

    raise RetryExhaustedError(
        f"All {policy.max_retries + 1} attempt(s) failed"
    ) from last_exception


def _compute_delay(attempt: int, policy: RetryPolicy) -> float:
    """Compute exponential-backoff delay for the given attempt index."""
    delay = policy.base_delay * (2**attempt)
    delay = min(delay, policy.max_delay)

    if policy.jitter:
        # +/- 50% jitter
        jitter_factor = 0.5 + random.random()  # 0.5 ... 1.5
        delay *= jitter_factor

    return delay
