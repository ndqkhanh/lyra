"""
Tests for retry logic (RetryPolicy, retry).
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from src.reliability.retry import RetryExhaustedError, RetryPolicy, retry


# ------------------------------------------------------------------
# RetryPolicy
# ------------------------------------------------------------------


class TestRetryPolicy:
    """RetryPolicy dataclass validation."""

    def test_default_policy(self):
        """Default policy is created without error."""
        p = RetryPolicy()
        assert p.max_retries == 3
        assert p.base_delay == 1.0
        assert p.max_delay == 60.0
        assert p.jitter is True

    def test_custom_policy(self):
        """Custom values are stored correctly."""
        p = RetryPolicy(max_retries=5, base_delay=0.5, max_delay=30.0, jitter=False)
        assert p.max_retries == 5
        assert p.base_delay == 0.5
        assert p.max_delay == 30.0
        assert p.jitter is False

    def test_negative_max_retries_raises(self):
        with pytest.raises(ValueError, match="max_retries must be >= 0"):
            RetryPolicy(max_retries=-1)

    def test_negative_base_delay_raises(self):
        with pytest.raises(ValueError, match="base_delay must be >= 0"):
            RetryPolicy(base_delay=-1)

    def test_negative_max_delay_raises(self):
        with pytest.raises(ValueError, match="max_delay must be >= 0"):
            RetryPolicy(max_delay=-1)


# ------------------------------------------------------------------
# retry()
# ------------------------------------------------------------------


class TestRetryFn:
    """async retry() function behaviour."""

    @pytest.mark.asyncio
    async def test_success_on_first_try(self):
        """retry() returns the result when the callable succeeds immediately."""
        mock = AsyncMock(return_value="ok")
        result = await retry(mock)
        assert result == "ok"
        mock.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_retries_and_succeeds(self):
        """retry() retries and eventually succeeds."""
        mock = AsyncMock(side_effect=[ValueError("fail1"), ValueError("fail2"), "success"])

        result = await retry(mock, policy=RetryPolicy(max_retries=3, base_delay=0.01))

        assert result == "success"
        assert mock.await_count == 3

    @pytest.mark.asyncio
    async def test_exhausted_raises(self):
        """retry() raises RetryExhaustedError when all attempts fail."""
        mock = AsyncMock(side_effect=ValueError("always fails"))

        with pytest.raises(RetryExhaustedError, match="All 2 attempt"):
            await retry(mock, policy=RetryPolicy(max_retries=1, base_delay=0.01))

        assert mock.await_count == 2  # 1 initial + 1 retry

    @pytest.mark.asyncio
    async def test_zero_retries_no_retry(self):
        """retry() with max_retries=0 does not retry on failure."""
        mock = AsyncMock(side_effect=ValueError("fail"))

        with pytest.raises(RetryExhaustedError):
            await retry(mock, policy=RetryPolicy(max_retries=0, base_delay=0.01))

        mock.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_passes_args_and_kwargs(self):
        """retry() forwards args and kwargs to the wrapped function."""
        mock = AsyncMock(return_value="done")

        await retry(mock, "arg1", "arg2", key="val")

        mock.assert_awaited_once_with("arg1", "arg2", key="val")

    @pytest.mark.asyncio
    async def test_custom_policy_used(self):
        """A user-supplied policy is respected."""
        mock = AsyncMock(side_effect=[RuntimeError("fail"), "ok"])

        result = await retry(mock, policy=RetryPolicy(max_retries=1, base_delay=0.01))

        assert result == "ok"
        assert mock.await_count == 2

    @pytest.mark.asyncio
    async def test_does_not_exceed_max_delay(self):
        """Delay never exceeds max_delay even when exponential backoff grows."""
        mock = AsyncMock(side_effect=ValueError("fail"))

        start = asyncio.get_event_loop().time()
        with pytest.raises(RetryExhaustedError):
            await retry(
                mock,
                policy=RetryPolicy(max_retries=5, base_delay=100.0, max_delay=0.01, jitter=False),
            )
        elapsed = asyncio.get_event_loop().time() - start
        # 5 retries * 0.01s max_delay = 0.05s, plus overhead -- well under 1s
        assert elapsed < 1.0
