"""Tests for Phase 6: Streaming Backpressure & Circuit Breaker."""

from __future__ import annotations

import pytest

from lyra_core.backpressure import (
    AdaptiveThrottler,
    BackpressureConfig,
    BackpressureRegulator,
    BackpressureState,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    ThrottleConfig,
    TokenBucket,
    Watermark,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Watermark
# ═══════════════════════════════════════════════════════════════════════════════


class TestWatermark:
    def test_defaults(self):
        wm = Watermark()
        assert wm.low == 64
        assert wm.high == 256

    def test_custom(self):
        wm = Watermark(low=10, high=50)
        assert wm.low == 10
        assert wm.high == 50

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            Watermark(low=100, high=50)


# ═══════════════════════════════════════════════════════════════════════════════
# TokenBucket
# ═══════════════════════════════════════════════════════════════════════════════


class TestTokenBucket:
    def test_initial_full(self):
        bucket = TokenBucket(rate=10.0, capacity=100.0)
        assert bucket.available >= 99.0

    def test_try_consume_success(self):
        bucket = TokenBucket(rate=100.0, capacity=10.0)
        assert bucket.try_consume(1.0)

    def test_try_consume_empty(self):
        bucket = TokenBucket(rate=0.0, capacity=0.0)
        bucket.tokens = 0.0
        assert not bucket.try_consume(1.0)

    def test_refill(self):
        bucket = TokenBucket(rate=1000.0, capacity=10.0)
        bucket.tokens = 0.0
        bucket.last_refill = bucket.last_refill - 1.0  # 1 second ago
        bucket.refill()
        assert bucket.tokens >= 9.0  # ~1000 tokens/sec for 1 sec, capped at 10

    def test_available(self):
        bucket = TokenBucket(rate=10.0, capacity=50.0)
        assert bucket.available >= 49.0

    def test_is_empty(self):
        bucket = TokenBucket(rate=0.0, capacity=0.0)
        bucket.tokens = 0.0
        assert bucket.is_empty

    def test_is_not_empty(self):
        bucket = TokenBucket(rate=10.0, capacity=50.0)
        assert not bucket.is_empty


# ═══════════════════════════════════════════════════════════════════════════════
# BackpressureRegulator
# ═══════════════════════════════════════════════════════════════════════════════


class TestBackpressureRegulator:
    def test_initial_state(self):
        reg = BackpressureRegulator()
        assert reg.state == BackpressureState.FLOWING
        assert reg.buffer_size == 0

    @pytest.mark.asyncio
    async def test_produce_and_consume(self):
        reg = BackpressureRegulator()
        await reg.produce("item1")
        assert reg.buffer_size == 1
        item = await reg.consume()
        assert item == "item1"
        assert reg.buffer_size == 0

    @pytest.mark.asyncio
    async def test_produce_triggers_pause_at_high_watermark(self):
        config = BackpressureConfig(
            watermark=Watermark(low=2, high=5),
            token_bucket_rate=10000.0,  # Fast tokens
            token_bucket_capacity=10000.0,
        )
        reg = BackpressureRegulator(config=config)
        for i in range(6):
            await reg.produce(f"item{i}")
        assert reg.state == BackpressureState.PAUSED

    @pytest.mark.asyncio
    async def test_consume_triggers_resume(self):
        config = BackpressureConfig(
            watermark=Watermark(low=2, high=5),
            token_bucket_rate=10000.0,
            token_bucket_capacity=10000.0,
        )
        reg = BackpressureRegulator(config=config)
        for i in range(6):
            await reg.produce(f"item{i}")
        assert reg.is_paused
        # Drain below low watermark
        for _ in range(5):
            await reg.consume()
        assert reg.state == BackpressureState.FLOWING

    @pytest.mark.asyncio
    async def test_overflow_drops_items(self):
        config = BackpressureConfig(
            max_buffer_size=3,
            token_bucket_rate=10000.0,
            token_bucket_capacity=10000.0,
        )
        reg = BackpressureRegulator(config=config)
        for i in range(5):
            result = await reg.produce(f"item{i}")
            if i >= 3:
                assert result is False
        assert reg.stats["items_dropped"] >= 2

    @pytest.mark.asyncio
    async def test_drain_batch(self):
        config = BackpressureConfig(
            token_bucket_rate=10000.0,
            token_bucket_capacity=10000.0,
            drain_batch_size=3,
        )
        reg = BackpressureRegulator(config=config)
        for i in range(5):
            await reg.produce(f"item{i}")
        batch = await reg.drain_batch()
        assert len(batch) == 3

    @pytest.mark.asyncio
    async def test_drain_all(self):
        config = BackpressureConfig(
            token_bucket_rate=10000.0,
            token_bucket_capacity=10000.0,
        )
        reg = BackpressureRegulator(config=config)
        for i in range(3):
            await reg.produce(f"item{i}")
        batch = await reg.drain_all()
        assert len(batch) == 3

    @pytest.mark.asyncio
    async def test_clear_resets_state(self):
        config = BackpressureConfig(
            watermark=Watermark(low=2, high=5),
            token_bucket_rate=10000.0,
            token_bucket_capacity=10000.0,
        )
        reg = BackpressureRegulator(config=config)
        for i in range(6):
            await reg.produce(f"item{i}")
        assert reg.is_paused
        await reg.clear()
        assert reg.state == BackpressureState.FLOWING
        assert reg.buffer_size == 0

    @pytest.mark.asyncio
    async def test_force_resume(self):
        config = BackpressureConfig(
            watermark=Watermark(low=2, high=5),
            token_bucket_rate=10000.0,
            token_bucket_capacity=10000.0,
        )
        reg = BackpressureRegulator(config=config)
        for i in range(6):
            await reg.produce(f"item{i}")
        assert reg.is_paused
        await reg.force_resume()
        assert not reg.is_paused

    @pytest.mark.asyncio
    async def test_stats(self):
        reg = BackpressureRegulator()
        await reg.produce("x")
        await reg.consume()
        stats = reg.stats
        assert stats["items_processed"] == 1

    @pytest.mark.asyncio
    async def test_consume_empty_returns_none(self):
        reg = BackpressureRegulator()
        item = await reg.consume()
        assert item is None


# ═══════════════════════════════════════════════════════════════════════════════
# CircuitBreaker
# ═══════════════════════════════════════════════════════════════════════════════


class TestCircuitBreaker:
    def test_initial_state_closed(self):
        cb = CircuitBreaker("test")
        assert cb.state == CircuitState.CLOSED
        assert not cb.is_open

    def test_allows_requests_when_closed(self):
        cb = CircuitBreaker("test")
        assert cb.allow_request()

    def test_opens_after_failures(self):
        cb = CircuitBreaker("test", CircuitBreakerConfig(failure_threshold=3))
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open

    def test_blocks_requests_when_open(self):
        cb = CircuitBreaker("test", CircuitBreakerConfig(failure_threshold=1))
        cb.record_failure()
        assert not cb.allow_request()

    def test_resets_after_success(self):
        cb = CircuitBreaker("test", CircuitBreakerConfig(failure_threshold=3))
        cb.record_failure()
        cb.record_failure()
        cb.record_success()  # resets failure count
        cb.record_failure()
        cb.record_failure()
        assert not cb.is_open  # Only 2 consecutive failures

    def test_manual_reset(self):
        cb = CircuitBreaker("test", CircuitBreakerConfig(failure_threshold=1))
        cb.record_failure()
        assert cb.is_open
        cb.reset()
        assert cb.state == CircuitState.CLOSED

    def test_half_open_allows_limited_requests(self):
        cb = CircuitBreaker("test", CircuitBreakerConfig(
            failure_threshold=1,
            recovery_timeout_seconds=0,  # immediate
            half_open_max_requests=2,
        ))
        cb.record_failure()
        assert cb.is_open
        # recovery_timeout=0 → immediate transition to half_open (1st call)
        # Then 2 more half_open requests allowed → total 3 passes
        assert cb.allow_request()   # OPEN→HALF_OPEN transition
        assert cb.allow_request()   # half_open request 1
        assert cb.allow_request()   # half_open request 2
        assert not cb.allow_request()  # 4th request blocked (exceeded max)

    def test_half_open_to_closed_after_successes(self):
        cb = CircuitBreaker("test", CircuitBreakerConfig(
            failure_threshold=1,
            recovery_timeout_seconds=0,
            half_open_max_requests=2,
        ))
        cb.record_failure()
        cb.allow_request()
        cb.allow_request()
        cb.record_success()
        cb.record_success()
        assert cb.state == CircuitState.CLOSED


# ═══════════════════════════════════════════════════════════════════════════════
# AdaptiveThrottler
# ═══════════════════════════════════════════════════════════════════════════════


class TestAdaptiveThrottler:
    def test_initial_rate(self):
        throttler = AdaptiveThrottler(ThrottleConfig(initial_rate=50.0))
        assert throttler.current_rate == 50.0

    def test_allows_requests(self):
        throttler = AdaptiveThrottler(ThrottleConfig(initial_rate=100.0,
                                                     max_rate=1000.0))
        assert throttler.allow_request()

    def test_success_rate_initial(self):
        throttler = AdaptiveThrottler()
        assert throttler.success_rate == 1.0

    def test_increase_rate_on_success(self):
        config = ThrottleConfig(initial_rate=100.0, max_rate=1000.0,
                               increase_factor=2.0, window_seconds=60.0)
        throttler = AdaptiveThrottler(config)
        for _ in range(10):
            throttler.record_success()
        assert throttler.current_rate > 100.0

    def test_decrease_rate_on_failure(self):
        config = ThrottleConfig(initial_rate=100.0, min_rate=10.0,
                               decrease_factor=0.5, window_seconds=60.0)
        throttler = AdaptiveThrottler(config)
        for _ in range(5):
            throttler.record_failure()
        assert throttler.current_rate < 100.0

    def test_rate_bounded_by_max(self):
        config = ThrottleConfig(initial_rate=100.0, max_rate=150.0,
                               increase_factor=2.0, window_seconds=60.0)
        throttler = AdaptiveThrottler(config)
        for _ in range(20):
            throttler.record_success()
        assert throttler.current_rate <= 150.0

    def test_rate_bounded_by_min(self):
        config = ThrottleConfig(initial_rate=100.0, min_rate=50.0,
                               decrease_factor=0.5, window_seconds=60.0)
        throttler = AdaptiveThrottler(config)
        for _ in range(10):
            throttler.record_failure()
        assert throttler.current_rate >= 50.0


# ═══════════════════════════════════════════════════════════════════════════════
# Enum completeness
# ═══════════════════════════════════════════════════════════════════════════════


class TestEnums:
    def test_backpressure_state_values(self):
        for s in BackpressureState:
            assert isinstance(s.value, str)

    def test_circuit_state_values(self):
        for s in CircuitState:
            assert isinstance(s.value, str)
