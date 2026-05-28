"""Tests for the anomaly detector."""
from __future__ import annotations

from lyra_cli.infrastructure.anomaly_detector import (
    AnomalyDetector,
    AnomalySeverity,
    DetectorConfig,
    MetricTracker,
)


class TestMetricTracker:
    def test_initial_state(self):
        t = MetricTracker()
        assert t.count == 0
        assert t.mean == 0.0
        assert t.std == 0.0

    def test_add_updates_count(self):
        t = MetricTracker()
        t.add(5.0)
        assert t.count == 1

    def test_mean_single_value(self):
        t = MetricTracker()
        t.add(10.0)
        assert t.mean == 10.0

    def test_mean_multiple_values(self):
        t = MetricTracker()
        for v in [1.0, 2.0, 3.0]:
            t.add(v)
        assert t.mean == 2.0

    def test_z_score_zero_with_no_data(self):
        t = MetricTracker()
        assert t.z_score(100.0) == 0.0

    def test_z_score_detects_outlier(self):
        t = MetricTracker()
        for i in range(50):
            t.add(10.0 + (i % 7 - 3) * 0.5)
        z = t.z_score(50.0)
        assert abs(z) > 2.0

    def test_window_size_limit(self):
        t = MetricTracker(window_size=10)
        for i in range(20):
            t.add(float(i))
        assert t.count == 10


class TestAnomalyDetector:
    def test_initial_state(self):
        d = AnomalyDetector()
        assert d.event_count == 0

    def test_observe_normal_value_no_alert(self):
        d = AnomalyDetector()
        for i in range(20):
            d.observe("latency", 10.0 + (i % 7 - 3) * 0.5)
        event = d.observe("latency", 10.0)
        assert event is None

    def test_observe_critical_anomaly(self):
        config = DetectorConfig(z_score_critical=3.0, min_samples=10)
        d = AnomalyDetector(config=config)
        for i in range(20):
            d.observe("latency", 10.0 + (i % 7 - 3) * 0.5)
        event = d.observe("latency", 100.0)
        assert event is not None
        assert event.severity == AnomalySeverity.CRITICAL

    def test_check_without_data(self):
        d = AnomalyDetector()
        assert d.check("metric", 100.0) is None

    def test_register_metric(self):
        d = AnomalyDetector()
        d.register_metric("custom")
        assert "custom" in d._trackers

    def test_stats(self):
        d = AnomalyDetector()
        d.register_metric("cpu")
        d.observe("cpu", 50.0)
        stats = d.stats()
        assert stats["metrics_tracked"] == 1

    def test_multiple_metrics_independent(self):
        config = DetectorConfig(z_score_critical=3.0, min_samples=10)
        d = AnomalyDetector(config=config)
        for i in range(20):
            d.observe("cpu", 50.0 + (i % 7 - 3) * 0.5)
            d.observe("mem", 70.0 + (i % 7 - 3) * 0.5)
        cpu_event = d.observe("cpu", 200.0)
        assert cpu_event is not None
        assert cpu_event.metric_name == "cpu"

    def test_config_custom_thresholds(self):
        config = DetectorConfig(z_score_critical=5.0, z_score_warning=2.0, min_samples=10)
        d = AnomalyDetector(config=config)
        for i in range(20):
            d.observe("latency", 10.0 + (i % 7 - 3) * 0.5)
        event = d.observe("latency", 13.0)
        assert event is not None
        assert event.severity == AnomalySeverity.WARNING

    def test_recent_events(self):
        config = DetectorConfig(z_score_critical=2.0, min_samples=10)
        d = AnomalyDetector(config=config)
        for i in range(20):
            d.observe("latency", 10.0 + (i % 7 - 3) * 0.5)
        d.observe("latency", 50.0)
        events = d.recent_events
        assert len(events) == 1
