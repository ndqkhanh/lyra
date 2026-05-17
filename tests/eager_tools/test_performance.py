"""Tests for performance metrics."""

import time

import pytest

from lyra_cli.eager_tools.performance import EagerMetrics


def test_record_seal():
    """Seal detection is recorded."""
    metrics = EagerMetrics()

    metrics.record_seal(2.5, dispatched=True)
    metrics.record_seal(3.0, dispatched=False)

    assert metrics.seals_detected == 2
    assert metrics.seals_dispatched == 1
    assert len(metrics.seal_latency_ms) == 2


def test_record_tool_execution():
    """Tool execution is recorded."""
    metrics = EagerMetrics()

    metrics.record_tool_execution("read_file", 100.0)
    metrics.record_tool_execution("read_file", 150.0)
    metrics.record_tool_execution("search", 200.0)

    assert metrics.tools_executed == 3
    assert len(metrics.tool_durations_ms["read_file"]) == 2
    assert len(metrics.tool_durations_ms["search"]) == 1


def test_calculate_speedup():
    """Speedup is calculated correctly."""
    metrics = EagerMetrics()

    # Simulate stream: 2000ms
    metrics.start_stream()
    time.sleep(0.002)  # 2ms
    metrics.end_stream()

    # Simulate tools: max 1500ms
    metrics.record_tool_execution("tool1", 1500.0)
    metrics.record_tool_execution("tool2", 1000.0)

    speedup = metrics.calculate_speedup()

    # Traditional: 2 + 1500 = 1502ms (approx)
    # Eager: max(2, 1500) = 1500ms (approx)
    # Speedup: ~1.0 (small difference due to short sleep)
    assert speedup >= 1.0


def test_speedup_with_slow_tools():
    """Speedup is significant with slow tools."""
    metrics = EagerMetrics()

    # Simulate stream: 2000ms
    metrics.stream_start = 0.0
    metrics.stream_end = 2.0  # 2000ms

    # Simulate slow tools: 1500ms
    metrics.record_tool_execution("slow_tool", 1500.0)

    speedup = metrics.calculate_speedup()

    # Traditional: 2000 + 1500 = 3500ms
    # Eager: max(2000, 1500) = 2000ms
    # Speedup: 3500 / 2000 = 1.75×
    assert speedup == pytest.approx(1.75, rel=0.01)


def test_get_summary():
    """Summary includes all metrics."""
    metrics = EagerMetrics()

    metrics.record_seal(2.5, dispatched=True)
    metrics.record_seal(3.0, dispatched=True)
    metrics.record_tool_execution("tool1", 100.0)

    metrics.stream_start = 0.0
    metrics.stream_end = 2.0

    summary = metrics.get_summary()

    assert summary["seals_detected"] == 2
    assert summary["seals_dispatched"] == 2
    assert summary["dispatch_rate"] == 1.0
    assert summary["tools_executed"] == 1
    assert "speedup" in summary
    assert "cost_reduction_pct" in summary
