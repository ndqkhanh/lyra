"""Tests for infrastructure monitoring system."""

from __future__ import annotations

from lyra_cli.infrastructure.monitoring import (
    Alert,
    AlertManager,
    AlertSeverity,
    Metric,
    MetricsCollector,
    MetricType,
    MonitoringService,
)


class TestMetricsCollector:
    """Tests for MetricsCollector."""

    def test_register_metric(self):
        """Test metric registration."""
        collector = MetricsCollector()
        collector.register_metric(
            "test.counter",
            MetricType.COUNTER,
            "Test counter",
            "count",
        )

        metric = collector.get_metric("test.counter")
        assert metric is not None
        assert metric.name == "test.counter"
        assert metric.metric_type == MetricType.COUNTER

    def test_record_metric(self):
        """Test recording metric values."""
        collector = MetricsCollector()
        collector.register_metric("test.gauge", MetricType.GAUGE, "Test gauge")

        collector.record("test.gauge", 42.0)
        metric = collector.get_metric("test.gauge")

        assert metric is not None
        assert metric.get_latest() == 42.0

    def test_increment_counter(self):
        """Test incrementing counter."""
        collector = MetricsCollector()
        collector.register_metric("test.counter", MetricType.COUNTER, "Test counter")

        collector.increment("test.counter", 5.0)
        collector.increment("test.counter", 3.0)

        metric = collector.get_metric("test.counter")
        assert metric is not None
        assert metric.get_latest() == 8.0

    def test_set_gauge(self):
        """Test setting gauge value."""
        collector = MetricsCollector()
        collector.set_gauge("test.gauge", 100.0)

        metric = collector.get_metric("test.gauge")
        assert metric is not None
        assert metric.get_latest() == 100.0

    def test_observe_histogram(self):
        """Test observing histogram values."""
        collector = MetricsCollector()
        collector.register_metric("test.histogram", MetricType.HISTOGRAM, "Test histogram")

        collector.observe("test.histogram", 10.0)
        collector.observe("test.histogram", 20.0)
        collector.observe("test.histogram", 30.0)

        metric = collector.get_metric("test.histogram")
        assert metric is not None
        assert metric.get_average() == 20.0

    def test_metric_with_labels(self):
        """Test metrics with labels."""
        collector = MetricsCollector()
        collector.register_metric(
            "test.labeled",
            MetricType.COUNTER,
            "Test labeled metric",
            labels={"env": "test"},
        )

        collector.record("test.labeled", 1.0, labels={"status": "success"})
        metric = collector.get_metric("test.labeled")

        assert metric is not None
        assert len(metric.points) == 1
        assert metric.points[0].labels["env"] == "test"
        assert metric.points[0].labels["status"] == "success"

    def test_metric_percentiles(self):
        """Test metric percentile calculations."""
        collector = MetricsCollector()
        collector.register_metric("test.latency", MetricType.HISTOGRAM, "Test latency")

        values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        for value in values:
            collector.observe("test.latency", float(value))

        metric = collector.get_metric("test.latency")
        assert metric is not None
        # Percentile calculation: index = int(len * percentile / 100)
        # For 10 values, p50 index = int(10 * 50 / 100) = 5, which is 60.0
        assert metric.get_percentile(50) == 60.0
        assert metric.get_percentile(95) == 100.0

    def test_get_metric_summary(self):
        """Test getting metric summary."""
        collector = MetricsCollector()
        collector.register_metric("test.metric", MetricType.HISTOGRAM, "Test metric", "ms")

        collector.observe("test.metric", 10.0)
        collector.observe("test.metric", 20.0)
        collector.observe("test.metric", 30.0)

        summary = collector.get_metric_summary("test.metric")
        assert summary is not None
        assert summary["name"] == "test.metric"
        assert summary["type"] == "histogram"
        assert summary["unit"] == "ms"
        assert summary["latest"] == 30.0
        assert summary["average"] == 20.0


class TestAlertManager:
    """Tests for AlertManager."""

    def test_add_threshold_rule(self):
        """Test adding threshold-based alert rule."""
        collector = MetricsCollector()
        collector.register_metric("test.error_rate", MetricType.GAUGE, "Error rate")

        alert_manager = AlertManager(collector)
        alert_manager.add_threshold_rule(
            name="high_error_rate",
            metric_name="test.error_rate",
            threshold=10.0,
            operator=">",
            severity=AlertSeverity.WARNING,
            message="Error rate too high",
        )

        # Should not trigger
        collector.set_gauge("test.error_rate", 5.0)
        alerts = alert_manager.check_rules()
        assert len(alerts) == 0

        # Should trigger
        collector.set_gauge("test.error_rate", 15.0)
        alerts = alert_manager.check_rules()
        assert len(alerts) == 1
        assert alerts[0].name == "high_error_rate"
        assert alerts[0].severity == AlertSeverity.WARNING

    def test_alert_deduplication(self):
        """Test that alerts are not duplicated."""
        collector = MetricsCollector()
        collector.register_metric("test.metric", MetricType.GAUGE, "Test metric")

        alert_manager = AlertManager(collector)
        alert_manager.add_threshold_rule(
            name="test_alert",
            metric_name="test.metric",
            threshold=10.0,
            operator=">",
            severity=AlertSeverity.WARNING,
            message="Test alert",
        )

        collector.set_gauge("test.metric", 15.0)

        # First check should trigger
        alerts = alert_manager.check_rules()
        assert len(alerts) == 1

        # Second check should not trigger (already active)
        alerts = alert_manager.check_rules()
        assert len(alerts) == 0

    def test_get_active_alerts(self):
        """Test getting active alerts."""
        collector = MetricsCollector()
        collector.register_metric("test.metric", MetricType.GAUGE, "Test metric")

        alert_manager = AlertManager(collector)
        alert_manager.add_threshold_rule(
            name="test_alert",
            metric_name="test.metric",
            threshold=10.0,
            operator=">",
            severity=AlertSeverity.WARNING,
            message="Test alert",
        )

        collector.set_gauge("test.metric", 15.0)
        alert_manager.check_rules()

        active_alerts = alert_manager.get_active_alerts()
        assert len(active_alerts) == 1
        assert active_alerts[0].is_active()

    def test_resolve_alert(self):
        """Test resolving alerts."""
        collector = MetricsCollector()
        collector.register_metric("test.metric", MetricType.GAUGE, "Test metric")

        alert_manager = AlertManager(collector)
        alert_manager.add_threshold_rule(
            name="test_alert",
            metric_name="test.metric",
            threshold=10.0,
            operator=">",
            severity=AlertSeverity.WARNING,
            message="Test alert",
        )

        collector.set_gauge("test.metric", 15.0)
        alert_manager.check_rules()

        # Resolve alert
        resolved = alert_manager.resolve_alert("test_alert")
        assert resolved is True

        active_alerts = alert_manager.get_active_alerts()
        assert len(active_alerts) == 0

    def test_alert_callback(self):
        """Test alert callbacks."""
        collector = MetricsCollector()
        collector.register_metric("test.metric", MetricType.GAUGE, "Test metric")

        alert_manager = AlertManager(collector)

        callback_called = []

        def callback(alert: Alert):
            callback_called.append(alert.name)

        alert_manager.register_callback(callback)
        alert_manager.add_threshold_rule(
            name="test_alert",
            metric_name="test.metric",
            threshold=10.0,
            operator=">",
            severity=AlertSeverity.WARNING,
            message="Test alert",
        )

        collector.set_gauge("test.metric", 15.0)
        alert_manager.check_rules()

        assert len(callback_called) == 1
        assert callback_called[0] == "test_alert"


class TestMonitoringService:
    """Tests for MonitoringService."""

    def test_initialization(self):
        """Test monitoring service initialization."""
        service = MonitoringService()

        # Check default metrics are registered
        assert service.metrics.get_metric("agent.tasks.completed") is not None
        assert service.metrics.get_metric("system.active_agents") is not None
        assert service.metrics.get_metric("llm.requests") is not None

    def test_get_dashboard_data(self):
        """Test getting dashboard data."""
        service = MonitoringService()

        # Record some metrics
        service.metrics.increment("agent.tasks.completed", 5.0)
        service.metrics.set_gauge("system.active_agents", 3.0)

        dashboard = service.get_dashboard_data()

        assert "metrics" in dashboard
        assert "alerts" in dashboard
        assert "timestamp" in dashboard
        assert len(dashboard["metrics"]) > 0

    def test_default_alerts(self):
        """Test default alert rules."""
        service = MonitoringService()

        # Trigger high error rate alert
        service.metrics.set_gauge("system.error_rate", 15.0)
        dashboard = service.get_dashboard_data()

        assert len(dashboard["alerts"]) > 0
        alert_names = [a["name"] for a in dashboard["alerts"]]
        assert "high_error_rate" in alert_names


class TestMetric:
    """Tests for Metric class."""

    def test_metric_creation(self):
        """Test creating a metric."""
        metric = Metric(
            name="test.metric",
            metric_type=MetricType.GAUGE,
            description="Test metric",
            unit="count",
        )

        assert metric.name == "test.metric"
        assert metric.metric_type == MetricType.GAUGE
        assert len(metric.points) == 0

    def test_add_point(self):
        """Test adding data points."""
        metric = Metric(
            name="test.metric",
            metric_type=MetricType.GAUGE,
            description="Test metric",
            unit="count",
        )

        metric.add_point(42.0)
        assert len(metric.points) == 1
        assert metric.get_latest() == 42.0

    def test_get_average(self):
        """Test calculating average."""
        metric = Metric(
            name="test.metric",
            metric_type=MetricType.HISTOGRAM,
            description="Test metric",
            unit="ms",
        )

        metric.add_point(10.0)
        metric.add_point(20.0)
        metric.add_point(30.0)

        assert metric.get_average() == 20.0
        assert metric.get_average(last_n=2) == 25.0


class TestAlert:
    """Tests for Alert class."""

    def test_alert_creation(self):
        """Test creating an alert."""
        alert = Alert(
            name="test_alert",
            severity=AlertSeverity.WARNING,
            message="Test alert message",
            metric_name="test.metric",
            threshold=10.0,
        )

        assert alert.name == "test_alert"
        assert alert.severity == AlertSeverity.WARNING
        assert alert.is_active()

    def test_alert_resolution(self):
        """Test resolving an alert."""
        alert = Alert(
            name="test_alert",
            severity=AlertSeverity.WARNING,
            message="Test alert message",
            metric_name="test.metric",
            threshold=10.0,
        )

        assert alert.is_active()

        alert.resolve()
        assert not alert.is_active()
        assert alert.resolved_at is not None

    def test_alert_to_dict(self):
        """Test converting alert to dictionary."""
        alert = Alert(
            name="test_alert",
            severity=AlertSeverity.WARNING,
            message="Test alert message",
            metric_name="test.metric",
            threshold=10.0,
            metadata={"key": "value"},
        )

        alert_dict = alert.to_dict()
        assert alert_dict["status"] == "warning"
        assert alert_dict["message"] == "Test alert message"
        assert alert_dict["details"]["key"] == "value"
