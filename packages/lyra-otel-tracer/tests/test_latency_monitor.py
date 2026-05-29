"""Tests for lyra_otel_tracer.latency_monitor."""

from __future__ import annotations

import pytest
from lyra_otel_tracer.exceptions import LatencyMonitorError
from lyra_otel_tracer.latency_monitor import (
    LatencyAlert,
    LatencyMonitor,
    LatencySample,
    LatencyStats,
)


class TestLatencySample:
    def test_latency_sample_creation(self) -> None:
        sample = LatencySample(
            agent_id="a1",
            operation="code_gen",
            duration_ms=150.0,
            timestamp=1000.0,
        )
        assert sample.agent_id == "a1"
        assert sample.duration_ms == 150.0

    def test_latency_sample_frozen(self) -> None:
        sample = LatencySample(agent_id="a1", operation="op", duration_ms=1.0, timestamp=0.0)
        with pytest.raises(AttributeError):
            sample.agent_id = "changed"  # type: ignore[misc]


class TestLatencyStats:
    def test_latency_stats_creation(self) -> None:
        stats = LatencyStats(
            p50_ms=100.0, p95_ms=200.0, p99_ms=300.0,
            avg_ms=150.0, min_ms=50.0, max_ms=500.0,
            sample_count=100,
        )
        assert stats.p50_ms == 100.0
        assert stats.p99_ms == 300.0
        assert stats.sample_count == 100

    def test_latency_stats_defaults(self) -> None:
        stats = LatencyStats()
        assert stats.p50_ms == 0.0
        assert stats.sample_count == 0


class TestLatencyAlert:
    def test_latency_alert_creation(self) -> None:
        alert = LatencyAlert(
            alert_type="threshold_exceeded",
            stat_name="p95",
            current_value=500.0,
            threshold=200.0,
            timestamp=100.0,
        )
        assert alert.stat_name == "p95"
        assert alert.current_value == 500.0

    def test_latency_alert_frozen(self) -> None:
        alert = LatencyAlert(
            alert_type="test", stat_name="p50", current_value=1.0, threshold=2.0, timestamp=0.0
        )
        with pytest.raises(AttributeError):
            alert.alert_type = "changed"  # type: ignore[misc]


class TestLatencyMonitor:
    @pytest.mark.asyncio
    async def test_record_latency(self) -> None:
        monitor = LatencyMonitor()
        await monitor.record_latency("a1", "code_gen", 150.0)
        assert len(monitor._samples) == 1

    @pytest.mark.asyncio
    async def test_get_stats_empty(self) -> None:
        monitor = LatencyMonitor()
        stats = await monitor.get_stats()
        assert stats.sample_count == 0

    @pytest.mark.asyncio
    async def test_get_stats_single_sample(self) -> None:
        monitor = LatencyMonitor()
        await monitor.record_latency("a1", "code_gen", 100.0)
        stats = await monitor.get_stats()
        assert stats.sample_count == 1
        assert stats.min_ms == 100.0
        assert stats.max_ms == 100.0
        assert stats.avg_ms == 100.0

    @pytest.mark.asyncio
    async def test_get_stats_multiple_samples(self) -> None:
        monitor = LatencyMonitor()
        for i in range(1, 101):
            await monitor.record_latency("a1", "code_gen", float(i))
        stats = await monitor.get_stats()
        assert stats.sample_count == 100
        assert stats.min_ms == 1.0
        assert stats.max_ms == 100.0
        assert stats.p50_ms > 0

    @pytest.mark.asyncio
    async def test_get_stats_filtered_by_agent(self) -> None:
        monitor = LatencyMonitor()
        await monitor.record_latency("a1", "code_gen", 100.0)
        await monitor.record_latency("a2", "review", 200.0)
        stats = await monitor.get_stats(agent_id="a1")
        assert stats.sample_count == 1
        assert stats.avg_ms == 100.0

    @pytest.mark.asyncio
    async def test_get_stats_filtered_by_operation(self) -> None:
        monitor = LatencyMonitor()
        await monitor.record_latency("a1", "code_gen", 100.0)
        await monitor.record_latency("a1", "review", 200.0)
        stats = await monitor.get_stats(operation="review")
        assert stats.sample_count == 1
        assert stats.avg_ms == 200.0

    @pytest.mark.asyncio
    async def test_get_stats_filtered_no_match(self) -> None:
        monitor = LatencyMonitor()
        await monitor.record_latency("a1", "code_gen", 100.0)
        stats = await monitor.get_stats(agent_id="nonexistent")
        assert stats.sample_count == 0

    @pytest.mark.asyncio
    async def test_set_threshold(self) -> None:
        monitor = LatencyMonitor()
        await monitor.set_threshold("p95", 500.0)
        assert monitor._thresholds["p95"] == 500.0

    @pytest.mark.asyncio
    async def test_set_threshold_invalid_stat(self) -> None:
        monitor = LatencyMonitor()
        with pytest.raises(LatencyMonitorError, match="Invalid stat"):
            await monitor.set_threshold("invalid_stat", 100.0)

    @pytest.mark.asyncio
    async def test_check_thresholds_no_thresholds(self) -> None:
        monitor = LatencyMonitor()
        alerts = await monitor.check_thresholds()
        assert alerts == ()

    @pytest.mark.asyncio
    async def test_check_thresholds_no_samples(self) -> None:
        monitor = LatencyMonitor()
        await monitor.set_threshold("p95", 100.0)
        alerts = await monitor.check_thresholds()
        assert alerts == ()

    @pytest.mark.asyncio
    async def test_check_thresholds_triggered(self) -> None:
        monitor = LatencyMonitor()
        await monitor.record_latency("a1", "op", 1000.0)
        await monitor.set_threshold("max", 500.0)
        alerts = await monitor.check_thresholds()
        assert len(alerts) > 0
        assert alerts[0].stat_name == "max"

    @pytest.mark.asyncio
    async def test_check_thresholds_not_triggered(self) -> None:
        monitor = LatencyMonitor()
        await monitor.record_latency("a1", "op", 100.0)
        await monitor.set_threshold("max", 500.0)
        alerts = await monitor.check_thresholds()
        assert alerts == ()

    @pytest.mark.asyncio
    async def test_get_stats_p95_p99(self) -> None:
        monitor = LatencyMonitor()
        for i in range(1, 201):
            await monitor.record_latency("a1", "code_gen", float(i))
        stats = await monitor.get_stats()
        assert stats.p50_ms == pytest.approx(100.5, rel=0.1)
        assert stats.p95_ms > stats.p50_ms
        assert stats.p99_ms > stats.p95_ms

    @pytest.mark.asyncio
    async def test_record_latency_zero(self) -> None:
        monitor = LatencyMonitor()
        await monitor.record_latency("a1", "op", 0.0)
        stats = await monitor.get_stats()
        assert stats.min_ms == 0.0
        assert stats.max_ms == 0.0

    @pytest.mark.asyncio
    async def test_record_latency_negative_value(self) -> None:
        monitor = LatencyMonitor()
        await monitor.record_latency("a1", "op", -10.0)
        stats = await monitor.get_stats()
        assert stats.min_ms == -10.0
        assert stats.max_ms == -10.0

    @pytest.mark.asyncio
    async def test_multiple_thresholds(self) -> None:
        monitor = LatencyMonitor()
        await monitor.record_latency("a1", "op", 1000.0)
        await monitor.set_threshold("p50", 100.0)
        await monitor.set_threshold("p95", 100.0)
        await monitor.set_threshold("p99", 100.0)
        alerts = await monitor.check_thresholds()
        assert len(alerts) >= 1
