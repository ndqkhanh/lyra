"""Tests for the MetricsCollector module."""

from __future__ import annotations

import math

import pytest
from lyra_cli.performance.metrics_collector import (
    MetricSample,
    MetricsCollector,
    MetricSeries,
)


def test_record_and_retrieve() -> None:
    """Recording a metric should make it available in collected."""
    collector = MetricsCollector()
    collector.record("latency", 42.0)
    assert "latency" in collector.collected
    assert collector.collected["latency"] == [42.0]


def test_record_many_multiple_values() -> None:
    """record_many should add all values to the metric store."""
    collector = MetricsCollector()
    collector.record_many("latency", [10.0, 20.0, 30.0])
    assert collector.collected["latency"] == [10.0, 20.0, 30.0]


def test_series_provides_statistics() -> None:
    """series() should return a MetricSeries with computed statistics."""
    collector = MetricsCollector()
    for v in [10.0, 20.0, 30.0, 40.0, 50.0]:
        collector.record("test_metric", v)

    series = collector.series("test_metric")
    assert series.count == 5
    assert series.mean == 30.0
    assert series.median == 30.0
    assert series.minimum == 10.0
    assert series.maximum == 50.0
    assert series.p50 == 30.0
    assert series.p95 == 48.0
    assert series.p99 == pytest.approx(49.6)
    assert series.latest == 50.0


def test_series_stddev() -> None:
    """stddev should compute sample standard deviation."""
    series = MetricSeries(name="test", samples=[10.0, 20.0, 30.0])
    expected = math.sqrt(((10 - 20) ** 2 + (20 - 20) ** 2 + (30 - 20) ** 2) / 2)
    assert series.stddev == pytest.approx(expected)


def test_series_trend_with_insufficient_data() -> None:
    """trend should return 0 with fewer than 3 samples."""
    series = MetricSeries(name="test", samples=[1.0, 2.0])
    assert series.trend == 0.0


def test_series_trend_with_sufficient_data() -> None:
    """trend should compute a non-zero value with 3+ samples."""
    series = MetricSeries(name="test", samples=[1.0, 2.0, 3.0, 4.0, 5.0])
    assert series.trend > 0


def test_series_summary_keys() -> None:
    """summary should contain all expected statistical keys."""
    series = MetricSeries(name="test", samples=[1.0, 2.0, 3.0])
    s = series.summary
    expected_keys = {
        "count", "mean", "median", "min", "max", "stddev",
        "p50", "p95", "p99", "trend", "latest",
    }
    assert set(s.keys()) == expected_keys


def test_percentile_edge_cases() -> None:
    """percentile should handle empty and single-value series."""
    series = MetricSeries(name="empty")
    assert series.percentile(50) == 0.0

    series = MetricSeries(name="single", samples=[5.0])
    assert series.percentile(50) == 5.0
    assert series.percentile(95) == 5.0


def test_clear_removes_all_metrics() -> None:
    """clear should empty all collected metrics."""
    collector = MetricsCollector()
    collector.record("latency", 42.0)
    collector.clear()
    assert collector.list_metrics() == []


def test_list_metrics_returns_sorted_names() -> None:
    """list_metrics should return alphabetically sorted metric names."""
    collector = MetricsCollector()
    collector.record("z_metric", 1.0)
    collector.record("a_metric", 2.0)
    collector.record("m_metric", 3.0)
    assert collector.list_metrics() == ["a_metric", "m_metric", "z_metric"]


def test_merge_combines_collectors() -> None:
    """merge should combine metrics from another collector."""
    c1 = MetricsCollector()
    c2 = MetricsCollector()

    c1.record("latency", 10.0)
    c2.record("latency", 20.0)
    c2.record("throughput", 100.0)

    c1.merge(c2)
    assert c1.collected["latency"] == [10.0, 20.0]
    assert c1.collected["throughput"] == [100.0]


def test_metric_sample_frozen() -> None:
    """MetricSample should be a frozen dataclass (immutable)."""
    sample = MetricSample(name="test", value=42.0)
    assert sample.name == "test"
    assert sample.value == 42.0
    with pytest.raises(AttributeError):
        sample.value = 99.0  # type: ignore[misc]


def test_series_to_dict() -> None:
    """to_dict should export all data including samples."""
    series = MetricSeries(name="test", samples=[1.0, 2.0, 3.0])
    data = series.to_dict()
    assert data["name"] == "test"
    assert data["samples"] == [1.0, 2.0, 3.0]
    assert "statistics" in data
    assert "timestamps" in data
