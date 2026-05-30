"""Provider health monitoring for dynamic multi-provider optimization.

Tracks provider health, latency, error rates, and success rates across
LLM providers (Anthropic, AWS Bedrock, Google Vertex AI, OpenRouter, etc.)
to feed cost/quality routing decisions.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from enum import StrEnum


class HealthStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    DEAD = "dead"


class CircuitState(StrEnum):
    CLOSED = "closed"        # normal operation
    OPEN = "open"            # failing, reject requests
    HALF_OPEN = "half_open"  # testing recovery


@dataclass(frozen=True)
class ProviderMetrics:
    provider_id: str
    status: HealthStatus
    circuit_state: CircuitState
    success_rate: float
    error_rate: float
    avg_latency_ms: float
    p95_latency_ms: float
    total_requests: int
    total_errors: int
    consecutive_errors: int
    last_success_time: float
    last_error_time: float
    last_error_message: str


@dataclass
class _ProviderState:
    provider_id: str
    status: HealthStatus = HealthStatus.HEALTHY
    circuit_state: CircuitState = CircuitState.CLOSED
    total_requests: int = 0
    total_errors: int = 0
    consecutive_errors: int = 0
    latencies: deque[float] = field(default_factory=lambda: deque(maxlen=200))
    last_success_time: float = 0.0
    last_error_time: float = 0.0
    last_error_message: str = ""
    circuit_opened_at: float = 0.0


class ProviderHealthMonitor:
    """Monitors health of LLM providers for dynamic routing optimization.

    Tracks per-provider success/error rates, latency percentiles,
    circuit breaker state, and health status to inform routing decisions.

    Usage::

        monitor = ProviderHealthMonitor()
        monitor.record_success("anthropic", latency_ms=150.0)
        monitor.record_error("openrouter", "Connection timeout")
        if monitor.is_healthy("anthropic"):
            route_to("anthropic")
    """

    def __init__(
        self,
        error_threshold: int = 5,
        recovery_timeout_seconds: float = 30.0,
        half_open_max_requests: int = 3,
        latency_degraded_threshold_ms: float = 5000.0,
        error_rate_degraded_threshold: float = 0.1,
    ) -> None:
        self.error_threshold = error_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.half_open_max_requests = half_open_max_requests
        self.latency_degraded_threshold_ms = latency_degraded_threshold_ms
        self.error_rate_degraded_threshold = error_rate_degraded_threshold
        self._providers: dict[str, _ProviderState] = {}
        self._half_open_requests: dict[str, int] = {}

    @property
    def provider_count(self) -> int:
        return len(self._providers)

    def register_provider(self, provider_id: str) -> None:
        if provider_id not in self._providers:
            self._providers[provider_id] = _ProviderState(provider_id=provider_id)

    def record_success(self, provider_id: str, latency_ms: float = 0.0) -> None:
        state = self._ensure_provider(provider_id)
        state.total_requests += 1
        state.consecutive_errors = 0
        state.latencies.append(latency_ms)
        state.last_success_time = time.monotonic()

        if state.circuit_state == CircuitState.HALF_OPEN:
            count = self._half_open_requests.get(provider_id, 0) + 1
            self._half_open_requests[provider_id] = count
            if count >= self.half_open_max_requests:
                state.circuit_state = CircuitState.CLOSED
                state.status = HealthStatus.HEALTHY
                self._half_open_requests.pop(provider_id, None)

        self._recalculate_status(state)

    def record_error(self, provider_id: str, message: str = "") -> None:
        state = self._ensure_provider(provider_id)
        now = time.monotonic()
        state.total_requests += 1
        state.total_errors += 1
        state.consecutive_errors += 1
        state.last_error_time = now
        state.last_error_message = message

        if state.circuit_state == CircuitState.HALF_OPEN:
            # Failed in half-open — go back to open
            state.circuit_state = CircuitState.OPEN
            state.circuit_opened_at = now
            self._half_open_requests.pop(provider_id, None)

        if (state.circuit_state == CircuitState.CLOSED
                and state.consecutive_errors >= self.error_threshold):
            state.circuit_state = CircuitState.OPEN
            state.circuit_opened_at = now

        self._recalculate_status(state)

    def is_healthy(self, provider_id: str) -> bool:
        state = self._providers.get(provider_id)
        if state is None:
            return True  # unknown providers assumed healthy
        self._maybe_transition_half_open(state)
        return state.circuit_state != CircuitState.OPEN

    def get_metrics(self, provider_id: str) -> ProviderMetrics | None:
        state = self._providers.get(provider_id)
        if state is None:
            return None
        self._maybe_transition_half_open(state)
        total = max(state.total_requests, 1)
        return ProviderMetrics(
            provider_id=provider_id,
            status=state.status,
            circuit_state=state.circuit_state,
            success_rate=(total - state.total_errors) / total,
            error_rate=state.total_errors / total,
            avg_latency_ms=self._mean(state.latencies),
            p95_latency_ms=self._percentile(state.latencies, 95),
            total_requests=state.total_requests,
            total_errors=state.total_errors,
            consecutive_errors=state.consecutive_errors,
            last_success_time=state.last_success_time,
            last_error_time=state.last_error_time,
            last_error_message=state.last_error_message,
        )

    def get_all_metrics(self) -> dict[str, ProviderMetrics]:
        result: dict[str, ProviderMetrics] = {}
        for pid in self._providers:
            m = self.get_metrics(pid)
            if m is not None:
                result[pid] = m
        return result

    def get_healthy_providers(self) -> list[str]:
        return [pid for pid in self._providers if self.is_healthy(pid)]

    def reset_provider(self, provider_id: str) -> None:
        self._providers.pop(provider_id, None)
        self._half_open_requests.pop(provider_id, None)

    def reset(self) -> None:
        self._providers.clear()
        self._half_open_requests.clear()

    def _ensure_provider(self, provider_id: str) -> _ProviderState:
        if provider_id not in self._providers:
            self._providers[provider_id] = _ProviderState(provider_id=provider_id)
        return self._providers[provider_id]

    def _maybe_transition_half_open(self, state: _ProviderState) -> None:
        if state.circuit_state != CircuitState.OPEN:
            return
        elapsed = time.monotonic() - state.circuit_opened_at
        if elapsed >= self.recovery_timeout_seconds:
            state.circuit_state = CircuitState.HALF_OPEN
            self._half_open_requests[state.provider_id] = 0

    def _recalculate_status(self, state: _ProviderState) -> None:
        if state.circuit_state == CircuitState.OPEN:
            state.status = HealthStatus.DEAD
            return
        if state.circuit_state == CircuitState.HALF_OPEN:
            state.status = HealthStatus.DEGRADED
            return

        total = max(state.total_requests, 1)
        error_rate = state.total_errors / total
        avg_latency = self._mean(state.latencies)

        if error_rate >= self.error_rate_degraded_threshold * 2:
            state.status = HealthStatus.UNHEALTHY
        elif (error_rate >= self.error_rate_degraded_threshold
              or avg_latency >= self.latency_degraded_threshold_ms):
            state.status = HealthStatus.DEGRADED
        else:
            state.status = HealthStatus.HEALTHY

    @staticmethod
    def _mean(values: deque[float]) -> float:
        if not values:
            return 0.0
        return sum(values) / len(values)

    @staticmethod
    def _percentile(values: deque[float], pct: float) -> float:
        if not values:
            return 0.0
        sorted_vals = sorted(values)
        idx = int(len(sorted_vals) * pct / 100.0)
        idx = min(idx, len(sorted_vals) - 1)
        return sorted_vals[idx]
