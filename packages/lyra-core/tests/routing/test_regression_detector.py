"""Tests for the regression detector."""
from __future__ import annotations

from lyra_cli.infrastructure.regression_detector import (
    MetricHistory,
    RegressionConfig,
    RegressionDetector,
    RegressionSeverity,
)


class TestMetricHistory:
    def test_initial_state(self):
        h = MetricHistory()
        assert h.count == 0
        assert h.mean == 0.0
        assert h.std == 0.0

    def test_add_updates_count(self):
        h = MetricHistory()
        h.add(5.0)
        assert h.count == 1

    def test_mean_single_value(self):
        h = MetricHistory()
        h.add(10.0)
        assert h.mean == 10.0

    def test_mean_multiple_values(self):
        h = MetricHistory()
        for v in [1.0, 2.0, 3.0]:
            h.add(v)
        assert h.mean == 2.0

    def test_std_nonzero_with_variance(self):
        h = MetricHistory()
        for i in range(10):
            h.add(10.0 + (i % 5) * 0.5)
        assert h.std > 0.0

    def test_max_items_enforced(self):
        h = MetricHistory()
        for i in range(10):
            h.add(float(i), max_items=5)
        assert h.count == 5

    def test_roundtrip_serialization(self):
        h = MetricHistory()
        h.add(42.0)
        data = h.to_dict()
        h2 = MetricHistory.from_dict(data)
        assert h2.values == [42.0]


class TestRegressionDetector:
    def test_initial_state(self):
        d = RegressionDetector()
        assert d.recent_events == []

    def test_record_insufficient_data_no_event(self):
        d = RegressionDetector()
        for _ in range(4):
            d.record("latency", 10.0)
        event = d.record("latency", 10.0)
        assert event is None

    def test_record_normal_value_no_regression(self):
        config = RegressionConfig(min_baseline_samples=5)
        d = RegressionDetector(config=config)
        for i in range(10):
            d.record("latency", 10.0 + (i % 5) * 0.5)
        event = d.record("latency", 10.5)
        assert event is None

    def test_record_critical_regression(self):
        config = RegressionConfig(
            critical_threshold_pct=20.0,
            min_baseline_samples=5,
        )
        d = RegressionDetector(config=config)
        for i in range(10):
            d.record("latency", 10.0 + (i % 5) * 0.3)
        event = d.record("latency", 20.0)
        assert event is not None
        assert event.severity == RegressionSeverity.CRITICAL
        assert event.deviation_pct > 20.0

    def test_record_warning_regression(self):
        config = RegressionConfig(
            critical_threshold_pct=50.0,
            warning_threshold_pct=10.0,
            min_baseline_samples=5,
        )
        d = RegressionDetector(config=config)
        for i in range(10):
            d.record("latency", 10.0 + (i % 5) * 0.3)
        event = d.record("latency", 12.0)
        assert event is not None
        assert event.severity == RegressionSeverity.WARNING

    def test_check_without_data(self):
        d = RegressionDetector()
        assert d.check("metric", 100.0) is None

    def test_check_returns_severity(self):
        config = RegressionConfig(
            critical_threshold_pct=50.0,
            warning_threshold_pct=10.0,
            min_baseline_samples=5,
        )
        d = RegressionDetector(config=config)
        for i in range(10):
            d.record("latency", 10.0 + (i % 5) * 0.3)
        severity = d.check("latency", 13.0)
        assert severity == RegressionSeverity.WARNING

    def test_compare_multiple_metrics(self):
        config = RegressionConfig(
            critical_threshold_pct=20.0,
            warning_threshold_pct=10.0,
            min_baseline_samples=3,
        )
        d = RegressionDetector(config=config)
        for i in range(5):
            d.record("cpu", 50.0 + (i % 3) * 2.0)
            d.record("mem", 70.0 + (i % 3) * 2.0)
        events = d.compare({"cpu": 100.0, "mem": 72.0})
        assert len(events) >= 1
        assert any(e.metric_name == "cpu" for e in events)

    def test_get_baseline(self):
        d = RegressionDetector()
        for i in range(10):
            d.record("latency", 10.0 + i * 0.1)
        baseline = d.get_baseline("latency")
        assert baseline is not None
        assert baseline["metric"] == "latency"
        assert baseline["count"] == 10

    def test_get_baseline_unknown_metric(self):
        d = RegressionDetector()
        assert d.get_baseline("unknown") is None

    def test_stats(self):
        d = RegressionDetector()
        d.record("latency", 10.0)
        stats = d.stats()
        assert stats["metrics_tracked"] == 1
        assert stats["total_events"] == 0
