"""Monitoring system with metrics collection, dashboards, and alerts.

Provides comprehensive monitoring capabilities for production systems:
- Metrics collection (counters, gauges, histograms)
- Real-time dashboards
- Alert management with severity levels
- Integration with existing logging
"""

from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from lyra_cli.logging_config import get_logger

logger = get_logger(__name__)


class MetricType(Enum):
    """Type of metric."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class AlertSeverity(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass(frozen=True)
class MetricPoint:
    """A single metric data point."""

    timestamp: float
    value: float
    labels: dict[str, str] = field(default_factory=dict)


@dataclass
class Metric:
    """A metric with metadata and data points."""

    name: str
    metric_type: MetricType
    description: str
    unit: str
    labels: dict[str, str] = field(default_factory=dict)
    points: deque = field(default_factory=lambda: deque(maxlen=10000))

    def add_point(self, value: float, labels: dict[str, str] | None = None) -> None:
        """Add a data point to the metric."""
        point = MetricPoint(
            timestamp=time.time(),
            value=value,
            labels={**self.labels, **(labels or {})},
        )
        self.points.append(point)

    def get_latest(self) -> float | None:
        """Get the latest value."""
        return self.points[-1].value if self.points else None

    def get_average(self, last_n: int | None = None) -> float | None:
        """Get average value over last N points."""
        if not self.points:
            return None

        points_to_avg = list(self.points)
        if last_n:
            points_to_avg = points_to_avg[-last_n:]

        return sum(p.value for p in points_to_avg) / len(points_to_avg)

    def get_percentile(self, percentile: float, last_n: int | None = None) -> float | None:
        """Get percentile value (0-100)."""
        if not self.points:
            return None

        points_to_calc = list(self.points)
        if last_n:
            points_to_calc = points_to_calc[-last_n:]

        values = sorted(p.value for p in points_to_calc)
        index = int(len(values) * percentile / 100)
        return values[min(index, len(values) - 1)]


@dataclass
class Alert:
    """An alert triggered by a metric condition."""

    name: str
    severity: AlertSeverity
    message: str
    metric_name: str
    threshold: float
    triggered_at: float = field(default_factory=time.time)
    resolved_at: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_active(self) -> bool:
        """Check if alert is still active."""
        return self.resolved_at is None

    def resolve(self) -> None:
        """Mark alert as resolved."""
        self.resolved_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "status": self.severity.value,
            "message": self.message,
            "metric_name": self.metric_name,
            "threshold": self.threshold,
            "triggered_at": self.triggered_at,
            "resolved_at": self.resolved_at,
            "details": self.metadata,
        }


class MetricsCollector:
    """Collects and manages metrics.

    Features:
    - Multiple metric types (counter, gauge, histogram)
    - Label support for dimensional metrics
    - Efficient storage with configurable retention
    - Query interface for dashboards
    """

    def __init__(self, max_points_per_metric: int = 10000):
        """Initialize metrics collector.

        Args:
            max_points_per_metric: Maximum data points to retain per metric
        """
        self._metrics: dict[str, Metric] = {}
        self._max_points = max_points_per_metric

    def register_metric(
        self,
        name: str,
        metric_type: MetricType,
        description: str,
        unit: str = "",
        labels: dict[str, str] | None = None,
    ) -> None:
        """Register a new metric.

        Args:
            name: Metric name (should be unique)
            metric_type: Type of metric
            description: Human-readable description
            unit: Unit of measurement
            labels: Default labels for this metric
        """
        if name in self._metrics:
            logger.warning(f"Metric {name} already registered, skipping")
            return

        self._metrics[name] = Metric(
            name=name,
            metric_type=metric_type,
            description=description,
            unit=unit,
            labels=labels or {},
        )
        logger.debug(f"Registered metric: {name} ({metric_type.value})")

    def record(
        self,
        name: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Record a metric value.

        Args:
            name: Metric name
            value: Metric value
            labels: Additional labels for this data point
        """
        if name not in self._metrics:
            logger.warning(f"Metric {name} not registered, auto-registering as gauge")
            self.register_metric(name, MetricType.GAUGE, f"Auto-registered: {name}")

        self._metrics[name].add_point(value, labels)

    def increment(self, name: str, value: float = 1.0, labels: dict[str, str] | None = None) -> None:
        """Increment a counter metric.

        Args:
            name: Counter name
            value: Amount to increment
            labels: Additional labels
        """
        if name not in self._metrics:
            self.register_metric(name, MetricType.COUNTER, f"Counter: {name}", "count")

        current = self._metrics[name].get_latest() or 0.0
        self.record(name, current + value, labels)

    def set_gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Set a gauge metric value.

        Args:
            name: Gauge name
            value: New value
            labels: Additional labels
        """
        if name not in self._metrics:
            self.register_metric(name, MetricType.GAUGE, f"Gauge: {name}")

        self.record(name, value, labels)

    def observe(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Observe a value for histogram/summary metrics.

        Args:
            name: Metric name
            value: Observed value
            labels: Additional labels
        """
        if name not in self._metrics:
            self.register_metric(name, MetricType.HISTOGRAM, f"Histogram: {name}")

        self.record(name, value, labels)

    def get_metric(self, name: str) -> Metric | None:
        """Get a metric by name."""
        return self._metrics.get(name)

    def get_all_metrics(self) -> dict[str, Metric]:
        """Get all registered metrics."""
        return self._metrics.copy()

    def get_metric_summary(self, name: str) -> dict[str, Any] | None:
        """Get summary statistics for a metric."""
        metric = self.get_metric(name)
        if not metric:
            return None

        return {
            "name": metric.name,
            "type": metric.metric_type.value,
            "description": metric.description,
            "unit": metric.unit,
            "latest": metric.get_latest(),
            "average": metric.get_average(),
            "p50": metric.get_percentile(50),
            "p95": metric.get_percentile(95),
            "p99": metric.get_percentile(99),
            "data_points": len(metric.points),
        }


class AlertManager:
    """Manages alerts based on metric conditions.

    Features:
    - Threshold-based alerting
    - Multiple severity levels
    - Alert history and resolution tracking
    - Callback support for alert notifications
    """

    def __init__(self, metrics_collector: MetricsCollector):
        """Initialize alert manager.

        Args:
            metrics_collector: Metrics collector to monitor
        """
        self._collector = metrics_collector
        self._alerts: list[Alert] = []
        self._alert_rules: list[dict[str, Any]] = []
        self._callbacks: list[Callable[[Alert], None]] = []

    def add_rule(
        self,
        name: str,
        metric_name: str,
        condition: Callable[[float], bool],
        severity: AlertSeverity,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add an alert rule.

        Args:
            name: Alert name
            metric_name: Metric to monitor
            condition: Function that returns True when alert should trigger
            severity: Alert severity
            message: Alert message
            metadata: Additional metadata
        """
        self._alert_rules.append({
            "name": name,
            "metric_name": metric_name,
            "condition": condition,
            "severity": severity,
            "message": message,
            "metadata": metadata or {},
        })
        logger.debug(f"Added alert rule: {name} for metric {metric_name}")

    def add_threshold_rule(
        self,
        name: str,
        metric_name: str,
        threshold: float,
        operator: str,
        severity: AlertSeverity,
        message: str,
    ) -> None:
        """Add a threshold-based alert rule.

        Args:
            name: Alert name
            metric_name: Metric to monitor
            threshold: Threshold value
            operator: Comparison operator (>, <, >=, <=, ==)
            severity: Alert severity
            message: Alert message
        """
        operators = {
            ">": lambda x: x > threshold,
            "<": lambda x: x < threshold,
            ">=": lambda x: x >= threshold,
            "<=": lambda x: x <= threshold,
            "==": lambda x: x == threshold,
        }

        if operator not in operators:
            raise ValueError(f"Invalid operator: {operator}")

        self.add_rule(
            name=name,
            metric_name=metric_name,
            condition=operators[operator],
            severity=severity,
            message=message,
            metadata={"threshold": threshold, "operator": operator},
        )

    def register_callback(self, callback: Callable[[Alert], None]) -> None:
        """Register a callback to be called when alerts trigger.

        Args:
            callback: Function to call with Alert object
        """
        self._callbacks.append(callback)

    def check_rules(self) -> list[Alert]:
        """Check all alert rules and trigger alerts if needed.

        Returns:
            List of newly triggered alerts
        """
        new_alerts = []

        for rule in self._alert_rules:
            metric = self._collector.get_metric(rule["metric_name"])
            if not metric:
                continue

            latest_value = metric.get_latest()
            if latest_value is None:
                continue

            if rule["condition"](latest_value):
                # Check if alert already active
                active_alert = next(
                    (a for a in self._alerts if a.name == rule["name"] and a.is_active()),
                    None,
                )

                if not active_alert:
                    alert = Alert(
                        name=rule["name"],
                        severity=rule["severity"],
                        message=rule["message"],
                        metric_name=rule["metric_name"],
                        threshold=rule["metadata"].get("threshold", 0.0),
                        metadata=rule["metadata"],
                    )
                    self._alerts.append(alert)
                    new_alerts.append(alert)

                    # Notify callbacks
                    for callback in self._callbacks:
                        try:
                            callback(alert)
                        except Exception as e:
                            logger.error(f"Alert callback failed: {e}")

                    logger.warning(
                        f"Alert triggered: {alert.name} ({alert.severity.value})",
                        extra={"alert": alert.name, "severity": alert.severity.value},
                    )

        return new_alerts

    def get_active_alerts(self) -> list[Alert]:
        """Get all active alerts."""
        return [a for a in self._alerts if a.is_active()]

    def get_all_alerts(self) -> list[Alert]:
        """Get all alerts (active and resolved)."""
        return self._alerts.copy()

    def resolve_alert(self, alert_name: str) -> bool:
        """Manually resolve an alert.

        Args:
            alert_name: Name of alert to resolve

        Returns:
            True if alert was resolved, False if not found
        """
        for alert in self._alerts:
            if alert.name == alert_name and alert.is_active():
                alert.resolve()
                logger.info(f"Alert resolved: {alert_name}")
                return True
        return False


class MonitoringService:
    """Complete monitoring service integrating metrics and alerts.

    Features:
    - Unified interface for monitoring
    - Pre-configured common metrics
    - Automatic alert checking
    - Dashboard data export
    """

    def __init__(self):
        """Initialize monitoring service."""
        self.metrics = MetricsCollector()
        self.alerts = AlertManager(self.metrics)
        self._initialize_default_metrics()
        self._initialize_default_alerts()

    def _initialize_default_metrics(self) -> None:
        """Register default metrics."""
        # Agent metrics
        self.metrics.register_metric(
            "agent.tasks.completed",
            MetricType.COUNTER,
            "Number of completed tasks",
            "count",
        )
        self.metrics.register_metric(
            "agent.tasks.failed",
            MetricType.COUNTER,
            "Number of failed tasks",
            "count",
        )
        self.metrics.register_metric(
            "agent.response_time",
            MetricType.HISTOGRAM,
            "Agent response time",
            "ms",
        )

        # System metrics
        self.metrics.register_metric(
            "system.active_agents",
            MetricType.GAUGE,
            "Number of active agents",
            "count",
        )
        self.metrics.register_metric(
            "system.error_rate",
            MetricType.GAUGE,
            "System error rate",
            "percent",
        )
        self.metrics.register_metric(
            "system.memory_usage",
            MetricType.GAUGE,
            "System memory usage",
            "MB",
        )

        # LLM metrics
        self.metrics.register_metric(
            "llm.requests",
            MetricType.COUNTER,
            "Number of LLM requests",
            "count",
        )
        self.metrics.register_metric(
            "llm.tokens.input",
            MetricType.COUNTER,
            "Input tokens consumed",
            "tokens",
        )
        self.metrics.register_metric(
            "llm.tokens.output",
            MetricType.COUNTER,
            "Output tokens generated",
            "tokens",
        )
        self.metrics.register_metric(
            "llm.latency",
            MetricType.HISTOGRAM,
            "LLM request latency",
            "ms",
        )

    def _initialize_default_alerts(self) -> None:
        """Configure default alert rules."""
        # High error rate
        self.alerts.add_threshold_rule(
            name="high_error_rate",
            metric_name="system.error_rate",
            threshold=10.0,
            operator=">",
            severity=AlertSeverity.WARNING,
            message="Error rate exceeded 10%",
        )

        # Critical error rate
        self.alerts.add_threshold_rule(
            name="critical_error_rate",
            metric_name="system.error_rate",
            threshold=25.0,
            operator=">",
            severity=AlertSeverity.CRITICAL,
            message="Error rate exceeded 25%",
        )

        # Slow response time
        self.alerts.add_rule(
            name="slow_response_time",
            metric_name="agent.response_time",
            condition=lambda x: x > 5000,  # 5 seconds
            severity=AlertSeverity.WARNING,
            message="Agent response time exceeded 5 seconds",
        )

    def get_dashboard_data(self) -> dict[str, Any]:
        """Get complete dashboard data.

        Returns:
            Dashboard data including metrics and alerts
        """
        # Check alerts
        self.alerts.check_rules()

        # Collect metric summaries
        metric_summaries = {}
        for name in self.metrics.get_all_metrics():
            summary = self.metrics.get_metric_summary(name)
            if summary:
                metric_summaries[name] = summary

        # Get active alerts
        active_alerts = [
            {
                "name": alert.name,
                "severity": alert.severity.value,
                "message": alert.message,
                "metric": alert.metric_name,
                "triggered_at": alert.triggered_at,
            }
            for alert in self.alerts.get_active_alerts()
        ]

        return {
            "metrics": metric_summaries,
            "alerts": active_alerts,
            "timestamp": time.time(),
        }


__all__ = [
    "MetricType",
    "AlertSeverity",
    "MetricPoint",
    "Metric",
    "Alert",
    "MetricsCollector",
    "AlertManager",
    "MonitoringService",
]
