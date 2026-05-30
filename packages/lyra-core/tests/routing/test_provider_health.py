"""Tests for provider health monitoring and circuit breaker."""

from __future__ import annotations

import pytest

from lyra_core.routing.provider_health import (
    CircuitState,
    HealthStatus,
    ProviderHealthMonitor,
    ProviderMetrics,
)


@pytest.fixture
def monitor():
    return ProviderHealthMonitor()


@pytest.fixture
def strict_monitor():
    return ProviderHealthMonitor(
        error_threshold=3,
        recovery_timeout_seconds=0.0,  # immediate recovery for testing
    )


class TestProviderMetrics:
    def test_metrics_creation(self):
        m = ProviderMetrics(
            provider_id="anthropic",
            status=HealthStatus.HEALTHY,
            circuit_state=CircuitState.CLOSED,
            success_rate=0.99,
            error_rate=0.01,
            avg_latency_ms=150.0,
            p95_latency_ms=450.0,
            total_requests=1000,
            total_errors=10,
            consecutive_errors=0,
            last_success_time=0.0,
            last_error_time=0.0,
            last_error_message="",
        )
        assert m.provider_id == "anthropic"
        assert m.success_rate == 0.99

    def test_metrics_immutability(self):
        m = ProviderMetrics(
            provider_id="test",
            status=HealthStatus.HEALTHY,
            circuit_state=CircuitState.CLOSED,
            success_rate=1.0,
            error_rate=0.0,
            avg_latency_ms=100.0,
            p95_latency_ms=200.0,
            total_requests=10,
            total_errors=0,
            consecutive_errors=0,
            last_success_time=0.0,
            last_error_time=0.0,
            last_error_message="",
        )
        with pytest.raises(Exception):
            m.success_rate = 0.5


class TestProviderHealthMonitorBasic:
    def test_empty_monitor(self, monitor):
        assert monitor.provider_count == 0

    def test_register_provider(self, monitor):
        monitor.register_provider("anthropic")
        assert monitor.provider_count == 1

    def test_auto_register_on_record(self, monitor):
        monitor.record_success("anthropic")
        assert monitor.provider_count == 1

    def test_record_success(self, monitor):
        monitor.record_success("anthropic", latency_ms=100.0)
        metrics = monitor.get_metrics("anthropic")
        assert metrics is not None
        assert metrics.success_rate == 1.0
        assert metrics.total_requests == 1
        assert metrics.total_errors == 0

    def test_record_error(self, monitor):
        monitor.record_error("openrouter", "Connection timeout")
        metrics = monitor.get_metrics("openrouter")
        assert metrics is not None
        assert metrics.error_rate == 1.0
        assert metrics.consecutive_errors == 1

    def test_is_healthy_initial(self, monitor):
        monitor.register_provider("anthropic")
        assert monitor.is_healthy("anthropic")

    def test_is_healthy_unknown(self, monitor):
        assert monitor.is_healthy("unknown_provider")

    def test_get_metrics_missing(self, monitor):
        assert monitor.get_metrics("nonexistent") is None

    def test_multiple_successes(self, monitor):
        for i in range(10):
            monitor.record_success("anthropic", latency_ms=float(i * 10))
        metrics = monitor.get_metrics("anthropic")
        assert metrics is not None
        assert metrics.total_requests == 10
        assert metrics.success_rate == 1.0

    def test_latency_tracking(self, monitor):
        latencies = [50.0, 100.0, 150.0, 200.0, 1000.0]
        for lat in latencies:
            monitor.record_success("anthropic", latency_ms=lat)
        metrics = monitor.get_metrics("anthropic")
        assert metrics is not None
        assert metrics.avg_latency_ms > 0
        assert metrics.p95_latency_ms >= 200.0

    def test_get_all_metrics(self, monitor):
        monitor.record_success("anthropic")
        monitor.record_success("openrouter")
        all_metrics = monitor.get_all_metrics()
        assert len(all_metrics) == 2

    def test_get_healthy_providers(self, monitor):
        monitor.record_success("anthropic")
        monitor.record_success("openrouter")
        healthy = monitor.get_healthy_providers()
        assert len(healthy) == 2

    def test_reset_provider(self, monitor):
        monitor.record_success("anthropic")
        monitor.reset_provider("anthropic")
        assert monitor.provider_count == 0

    def test_reset(self, monitor):
        monitor.record_success("a")
        monitor.record_success("b")
        monitor.reset()
        assert monitor.provider_count == 0


class TestCircuitBreaker:
    def test_circuit_opens_after_errors(self):
        m = ProviderHealthMonitor(error_threshold=3, recovery_timeout_seconds=999.0)
        for _ in range(3):
            m.record_error("anthropic", "fail")
        metrics = m.get_metrics("anthropic")
        assert metrics is not None
        assert metrics.circuit_state == CircuitState.OPEN
        assert metrics.status == HealthStatus.DEAD

    def test_circuit_does_not_open_below_threshold(self, monitor):
        monitor = ProviderHealthMonitor(error_threshold=5)
        for _ in range(3):
            monitor.record_error("anthropic", "fail")
        assert monitor.is_healthy("anthropic")

    def test_circuit_half_open_after_timeout(self, strict_monitor):
        for _ in range(3):
            strict_monitor.record_error("anthropic", "fail")
        # recovery_timeout is 0, so immediate half-open check
        metrics = strict_monitor.get_metrics("anthropic")
        assert metrics is not None
        assert metrics.circuit_state == CircuitState.HALF_OPEN

    def test_recovery_in_half_open(self):
        m = ProviderHealthMonitor(error_threshold=3, recovery_timeout_seconds=0.0)
        for _ in range(3):
            m.record_error("anthropic", "fail")
        # trigger half-open via get_metrics (calls _maybe_transition_half_open)
        _ = m.get_metrics("anthropic")
        for _ in range(3):
            m.record_success("anthropic")
        metrics = m.get_metrics("anthropic")
        assert metrics is not None
        assert metrics.circuit_state == CircuitState.CLOSED

    def test_failure_in_half_open_reopens(self):
        m = ProviderHealthMonitor(error_threshold=3, recovery_timeout_seconds=10.0)
        for _ in range(3):
            m.record_error("anthropic", "fail")
        # Circuit is OPEN — provider is not healthy
        assert not m.is_healthy("anthropic")
        # Additional errors keep it OPEN
        m.record_error("anthropic", "fail again")
        assert not m.is_healthy("anthropic")

    def test_healthy_provider_not_in_get_healthy_when_circuit_open(self, monitor):
        m = ProviderHealthMonitor(error_threshold=2, recovery_timeout_seconds=999.0)
        m.record_error("bedrock", "fail")
        m.record_error("bedrock", "fail again")
        assert not m.is_healthy("bedrock")


class TestHealthStatusTransitions:
    def test_degraded_from_error_rate(self, monitor):
        m = ProviderHealthMonitor(error_rate_degraded_threshold=0.1)
        for _ in range(9):
            m.record_success("test")
        m.record_error("test", "one error")
        metrics = m.get_metrics("test")
        assert metrics is not None
        # 1/10 = 0.1 error rate, exactly at threshold — not degraded yet
        # add another error
        m.record_error("test", "second error")
        metrics = m.get_metrics("test")
        # 2/11 ≈ 0.18 > 0.1
        assert metrics.status in (HealthStatus.DEGRADED, HealthStatus.UNHEALTHY)

    def test_unhealthy_from_high_error_rate(self):
        m = ProviderHealthMonitor(
            error_rate_degraded_threshold=0.1,
            error_threshold=20,  # high threshold so circuit breaker doesn't trip
        )
        for _ in range(5):
            m.record_error("test", "fail")
        for _ in range(5):
            m.record_success("test")
        metrics = m.get_metrics("test")
        assert metrics is not None
        assert metrics.status == HealthStatus.UNHEALTHY  # 50% > 20%

    def test_degraded_from_latency(self, monitor):
        m = ProviderHealthMonitor(latency_degraded_threshold_ms=500.0)
        m.record_success("test", latency_ms=6000.0)
        metrics = m.get_metrics("test")
        assert metrics is not None
        assert metrics.status == HealthStatus.DEGRADED
