"""Streaming Backpressure — tmux-inspired pause/resume flow control.

Inspired by tmux's control-mode backpressure:
  - Producers can be paused when consumers fall behind
  - Token bucket rate limiting for smooth throughput
  - Circuit breaker for cascading failure prevention
  - Watermark-based adaptive backpressure (low/high thresholds)

Also incorporates patterns from:
  - cmux agent flow control
  - alphaclaw health-based throttling
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from lyra_core.events import EventBus, EventCategory

logger = logging.getLogger(__name__)


# ── Watermark ────────────────────────────────────────────────────────────────


@dataclass
class Watermark:
    """High/low watermark for adaptive backpressure.

    When buffer exceeds high_watermark → pause producers.
    When buffer drops below low_watermark → resume producers.
    """

    low: int = 64
    high: int = 256

    def __post_init__(self) -> None:
        if self.low >= self.high:
            raise ValueError(f"low ({self.low}) must be < high ({self.high})")


class BackpressureState(str, Enum):
    """States of a backpressure-regulated stream."""
    FLOWING = "flowing"      # Normal operation, data flowing freely
    WARNING = "warning"       # Approaching high watermark
    PAUSED = "paused"         # Producers paused, draining consumers
    RESUMING = "resuming"     # Transitioning back to flowing
    OVERFLOW = "overflow"    # Buffer exhausted despite backpressure


# ── Token Bucket ─────────────────────────────────────────────────────────────


@dataclass
class TokenBucket:
    """Rate limiter using the token bucket algorithm.

    Tokens refill at `rate` tokens/second. Each operation consumes `cost` tokens.
    When the bucket is empty, operations must wait or be rejected.
    """

    rate: float  # Tokens per second
    capacity: float  # Maximum tokens (burst capacity)
    tokens: float = field(default=0.0)
    last_refill: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        self.tokens = self.capacity

    def refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_refill = now

    def try_consume(self, cost: float = 1.0) -> bool:
        """Try to consume tokens. Returns True if successful."""
        self.refill()
        if self.tokens >= cost:
            self.tokens -= cost
            return True
        return False

    async def consume(self, cost: float = 1.0) -> None:
        """Consume tokens, waiting if necessary."""
        while not self.try_consume(cost):
            wait_time = (cost - self.tokens) / self.rate
            await asyncio.sleep(wait_time)

    @property
    def available(self) -> float:
        self.refill()
        return self.tokens

    @property
    def is_empty(self) -> bool:
        self.refill()
        return self.tokens < 0.001


# ── Backpressure Regulator ───────────────────────────────────────────────────


@dataclass
class BackpressureConfig:
    """Configuration for backpressure regulation."""

    watermark: Watermark = field(default_factory=Watermark)
    token_bucket_rate: float = 100.0  # tokens/sec
    token_bucket_capacity: float = 200.0  # max burst
    drain_batch_size: int = 16
    max_buffer_size: int = 1024
    pause_timeout_seconds: float = 30.0  # Auto-resume if paused too long


class BackpressureRegulator:
    """Adaptive backpressure regulator for streaming data.

    Like tmux's control-mode backpressure:
      - Buffer with high/low watermarks
      - Automatic pause when buffer exceeds high watermark
      - Automatic resume when buffer drains below low watermark
      - Token bucket rate limiting
      - Overflow detection and circuit breaking
    """

    def __init__(self, config: BackpressureConfig | None = None,
                 bus: EventBus | None = None) -> None:
        self.config = config or BackpressureConfig()
        self._buffer: deque[Any] = deque()
        self._bucket = TokenBucket(
            rate=self.config.token_bucket_rate,
            capacity=self.config.token_bucket_capacity,
        )
        self._bus = bus or EventBus.get()
        self._state = BackpressureState.FLOWING
        self._paused_at: float | None = None
        self._items_processed: int = 0
        self._items_dropped: int = 0
        self._pause_count: int = 0
        self._lock = asyncio.Lock()
        self._drain_event = asyncio.Event()

    @property
    def state(self) -> BackpressureState:
        return self._state

    @property
    def buffer_size(self) -> int:
        return len(self._buffer)

    @property
    def is_paused(self) -> bool:
        return self._state == BackpressureState.PAUSED

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "state": self._state.value,
            "buffer_size": len(self._buffer),
            "tokens_available": self._bucket.available,
            "items_processed": self._items_processed,
            "items_dropped": self._items_dropped,
            "pause_count": self._pause_count,
        }

    async def produce(self, item: Any) -> bool:
        """Produce an item. Returns False if item was dropped due to overflow."""
        async with self._lock:
            if len(self._buffer) >= self.config.max_buffer_size:
                self._items_dropped += 1
                self._transition(BackpressureState.OVERFLOW)
                self._bus.publish(
                    category=EventCategory.TELEMETRY,
                    name="backpressure.overflow",
                    origin=__name__,
                    payload={"buffer_size": len(self._buffer),
                            "dropped_count": self._items_dropped},
                )
                return False

            self._buffer.append(item)

            # Check high watermark — pause takes priority over warning
            wm = self.config.watermark
            if len(self._buffer) >= wm.high and self._state in (
                BackpressureState.FLOWING, BackpressureState.WARNING,
            ):
                self._transition(BackpressureState.PAUSED)
                self._paused_at = time.time()
                self._pause_count += 1
                self._bus.publish(
                    category=EventCategory.TELEMETRY,
                    name="backpressure.paused",
                    origin=__name__,
                    payload={"buffer_size": len(self._buffer),
                            "high_watermark": wm.high},
                )
            elif len(self._buffer) >= wm.high * 0.8 and self._state == BackpressureState.FLOWING:
                self._transition(BackpressureState.WARNING)

            return True

    async def consume(self) -> Any | None:
        """Consume an item from the buffer. Returns None if buffer is empty."""
        async with self._lock:
            if not self._buffer:
                return None

            # Rate limit via token bucket
            if not self._bucket.try_consume():
                return None

            item = self._buffer.popleft()
            self._items_processed += 1

            # Check low watermark — resume if drained enough
            wm = self.config.watermark
            if len(self._buffer) <= wm.low and self._state in (
                BackpressureState.PAUSED, BackpressureState.WARNING,
            ):
                self._transition(BackpressureState.RESUMING)
                self._transition(BackpressureState.FLOWING)
                self._paused_at = None
                self._bus.publish(
                    category=EventCategory.TELEMETRY,
                    name="backpressure.resumed",
                    origin=__name__,
                    payload={"buffer_size": len(self._buffer),
                            "low_watermark": wm.low},
                )

            return item

    async def drain_batch(self, batch_size: int | None = None) -> list[Any]:
        """Drain a batch of items from the buffer."""
        size = batch_size or self.config.drain_batch_size
        batch: list[Any] = []
        for _ in range(size):
            item = await self.consume()
            if item is None:
                break
            batch.append(item)
        return batch

    async def drain_all(self) -> list[Any]:
        """Drain all available items from the buffer."""
        batch: list[Any] = []
        while True:
            item = await self.consume()
            if item is None:
                break
            batch.append(item)
        return batch

    def should_resume(self) -> bool:
        """Check if auto-resume timeout has elapsed."""
        if self._paused_at is None:
            return False
        elapsed = time.time() - self._paused_at
        return elapsed >= self.config.pause_timeout_seconds

    async def force_resume(self) -> None:
        """Force resume producers, discarding any timeout."""
        async with self._lock:
            if self._state == BackpressureState.PAUSED:
                self._transition(BackpressureState.RESUMING)
                self._transition(BackpressureState.FLOWING)
                self._paused_at = None

    async def clear(self) -> None:
        """Clear the buffer and reset state."""
        async with self._lock:
            self._buffer.clear()
            self._transition(BackpressureState.FLOWING)
            self._paused_at = None

    def _transition(self, new_state: BackpressureState) -> None:
        if self._state != new_state:
            old = self._state
            self._state = new_state
            logger.debug("Backpressure: %s → %s (buffer=%d)",
                        old.value, new_state.value, len(self._buffer))


# ── Circuit Breaker ──────────────────────────────────────────────────────────


class CircuitState(str, Enum):
    CLOSED = "closed"        # Normal operation
    OPEN = "open"            # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if failure resolved


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5
    recovery_timeout_seconds: float = 30.0
    half_open_max_requests: int = 3


class CircuitBreaker:
    """Circuit breaker for cascading failure prevention.

    Like standard circuit breaker pattern:
      - CLOSED → OPEN after N consecutive failures
      - OPEN → HALF_OPEN after recovery timeout
      - HALF_OPEN → CLOSED after successful test requests
      - HALF_OPEN → OPEN if test requests fail
    """

    def __init__(self, name: str, config: CircuitBreakerConfig | None = None,
                 bus: EventBus | None = None) -> None:
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._bus = bus or EventBus.get()
        self._state = CircuitState.CLOSED
        self._failure_count: int = 0
        self._success_count: int = 0
        self._last_failure_time: float = 0.0
        self._opened_at: float | None = None
        self._half_open_requests: int = 0

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def is_open(self) -> bool:
        return self._state == CircuitState.OPEN

    def allow_request(self) -> bool:
        """Check if a request should be allowed through."""
        if self._state == CircuitState.CLOSED:
            return True

        if self._state == CircuitState.OPEN:
            elapsed = time.time() - (self._opened_at or time.time())
            if elapsed >= self.config.recovery_timeout_seconds:
                self._transition(CircuitState.HALF_OPEN)
                self._half_open_requests = 0
                return True
            return False

        # HALF_OPEN: allow limited requests
        if self._state == CircuitState.HALF_OPEN:
            if self._half_open_requests < self.config.half_open_max_requests:
                self._half_open_requests += 1
                return True
            return False

        return False

    def record_success(self) -> None:
        """Record a successful request."""
        self._failure_count = 0

        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.config.half_open_max_requests:
                self._transition(CircuitState.CLOSED)
                self._success_count = 0

    def record_failure(self) -> None:
        """Record a failed request."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._state == CircuitState.HALF_OPEN:
            self._transition(CircuitState.OPEN)
            self._opened_at = time.time()
        elif (self._state == CircuitState.CLOSED
              and self._failure_count >= self.config.failure_threshold):
            self._transition(CircuitState.OPEN)
            self._opened_at = time.time()

    def reset(self) -> None:
        """Reset the circuit breaker to closed state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_requests = 0
        self._opened_at = None

    def _transition(self, new_state: CircuitState) -> None:
        if self._state != new_state:
            old = self._state
            self._state = new_state
            self._bus.publish(
                category=EventCategory.LIFECYCLE,
                name="circuit_breaker.state_changed",
                origin=__name__,
                payload={
                    "name": self.name,
                    "old_state": old.value,
                    "new_state": new_state.value,
                    "failure_count": self._failure_count,
                },
            )


# ── Adaptive Throttler ───────────────────────────────────────────────────────


@dataclass
class ThrottleConfig:
    """Configuration for adaptive throttling."""
    initial_rate: float = 100.0  # requests/sec
    min_rate: float = 10.0
    max_rate: float = 1000.0
    increase_factor: float = 1.5   # Multiply rate on success
    decrease_factor: float = 0.5   # Multiply rate on failure
    window_seconds: float = 10.0   # Observation window


class AdaptiveThrottler:
    """Adaptive throttling that adjusts rate based on success/failure.

    Increases throughput when healthy, backs off when failing.
    Like alphaclaw's health-based throttling.
    """

    def __init__(self, config: ThrottleConfig | None = None) -> None:
        self.config = config or ThrottleConfig()
        self._current_rate: float = self.config.initial_rate
        self._bucket = TokenBucket(rate=self._current_rate,
                                  capacity=self._current_rate * 2)
        self._recent_successes: int = 0
        self._recent_failures: int = 0
        self._window_start: float = time.time()

    @property
    def current_rate(self) -> float:
        return self._current_rate

    @property
    def success_rate(self) -> float:
        total = self._recent_successes + self._recent_failures
        if total == 0:
            return 1.0
        return self._recent_successes / total

    def allow_request(self) -> bool:
        """Check if a request should be allowed (rate limited)."""
        self._maybe_rotate_window()
        return self._bucket.try_consume()

    async def wait_and_proceed(self) -> None:
        """Wait until a request can proceed."""
        await self._bucket.consume()

    def record_success(self) -> None:
        self._recent_successes += 1
        self._maybe_increase_rate()

    def record_failure(self) -> None:
        self._recent_failures += 1
        self._maybe_decrease_rate()

    def _maybe_rotate_window(self) -> None:
        elapsed = time.time() - self._window_start
        if elapsed >= self.config.window_seconds:
            self._recent_successes = 0
            self._recent_failures = 0
            self._window_start = time.time()

    def _maybe_increase_rate(self) -> None:
        if self.success_rate > 0.9:
            new_rate = min(self._current_rate * self.config.increase_factor,
                          self.config.max_rate)
            if new_rate != self._current_rate:
                self._current_rate = new_rate
                self._bucket = TokenBucket(rate=self._current_rate,
                                          capacity=self._current_rate * 2)

    def _maybe_decrease_rate(self) -> None:
        if self.success_rate < 0.5:
            new_rate = max(self._current_rate * self.config.decrease_factor,
                          self.config.min_rate)
            if new_rate != self._current_rate:
                self._current_rate = new_rate
                self._bucket = TokenBucket(rate=self._current_rate,
                                          capacity=self._current_rate * 2)
