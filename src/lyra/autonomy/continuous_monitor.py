"""Continuous monitor — background health checking and alerting.

Provides the :class:`ContinuousMonitor` that runs in the background,
collecting metrics like token burn rate, error rate, P95 latency, and
cost per minute.  Alerts are emitted when anomalies are detected, budgets
are exceeded, or sessions stall.  Integrates with the Phase 3 remote relay
for push notifications.
"""

from __future__ import annotations

import asyncio
import logging
import statistics
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Alert severity
# ---------------------------------------------------------------------------


class AlertSeverity(str, Enum):
    """Severity levels for monitor alerts."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertKind(str, Enum):
    """Types of alerts the monitor can emit."""

    ANOMALY_DETECTED = "anomaly_detected"
    BUDGET_EXCEEDED = "budget_exceeded"
    SESSION_STALLED = "session_stalled"
    ERROR_RATE_SPIKE = "error_rate_spike"
    HIGH_LATENCY = "high_latency"


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MonitorAlert:
    """An alert emitted by the continuous monitor.

    Attributes:
        kind: The type of alert.
        severity: How serious the alert is.
        message: Human-readable description.
        metric_value: The metric value that triggered the alert.
        threshold: The threshold that was crossed.
        session_id: Optional session the alert relates to.
        timestamp: When the alert was created.
    """

    kind: AlertKind
    severity: AlertSeverity
    message: str
    metric_value: float
    threshold: float
    session_id: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class MetricsSnapshot:
    """A snapshot of all monitored metrics at a point in time.

    Attributes:
        token_burn_rate: Tokens consumed per minute (rolling window).
        error_rate: Errors per minute (rolling window).
        latency_p95: P95 latency in seconds for the rolling window.
        cost_per_minute: Cost per minute (rolling window).
        session_count: Number of active sessions being tracked.
        timestamp: When this snapshot was taken.
    """

    token_burn_rate: float = 0.0
    error_rate: float = 0.0
    latency_p95: float = 0.0
    cost_per_minute: float = 0.0
    session_count: int = 0
    timestamp: float = field(default_factory=time.time)


@dataclass
class MonitorConfig:
    """Configuration for the continuous monitor.

    Attributes:
        check_interval_seconds: How often metrics are collected.
        metric_window_seconds: Size of the rolling window for metric
            calculation.
        anomaly_stddev_threshold: Number of standard deviations from the
            mean that triggers an anomaly alert.
        budget_exceeded_threshold: Fraction of the budget that triggers
            a budget exceeded alert (0-1).
        stall_threshold_seconds: Seconds of activity with no progress
            before a stall alert is emitted.
        error_rate_spike_threshold: Errors per minute that triggers a
            spike alert.
        latency_p95_threshold_seconds: P95 latency above this value
            triggers a high-latency alert.
        max_alert_history: Maximum number of recent alerts to retain.
    """

    check_interval_seconds: float = 30.0
    metric_window_seconds: float = 300.0  # 5 minutes
    anomaly_stddev_threshold: float = 3.0
    budget_exceeded_threshold: float = 0.9
    stall_threshold_seconds: float = 600.0  # 10 minutes
    error_rate_spike_threshold: float = 10.0
    latency_p95_threshold_seconds: float = 2.0
    max_alert_history: int = 100


# ---------------------------------------------------------------------------
# ContinuousMonitor
# ---------------------------------------------------------------------------


class ContinuousMonitor:
    """Background health checker that collects metrics and emits alerts.

    Runs an async loop that periodically samples metrics, detects
    anomalies, and fires callbacks.  Integrates with the Phase 3
    remote relay by accepting an ``on_alert`` callback that can
    forward alerts to a push notification relay.

    Usage::

        monitor = ContinuousMonitor()
        monitor.on_alert = lambda alert: logging.warning(alert.message)

        # Start the background loop
        asyncio.create_task(monitor.start())

        # Feed data points
        monitor.record_latency(0.45)
        monitor.record_error("session-1", "timeout")
        monitor.record_tokens(5000)
        monitor.record_cost(0.05)
    """

    def __init__(self, config: MonitorConfig | None = None) -> None:
        self._config = config or MonitorConfig()

        # Rolling windows (deques of (timestamp, value) tuples)
        self._token_samples: deque[tuple[float, int]] = deque()
        self._error_samples: deque[tuple[float, str]] = deque()
        self._latency_samples: deque[tuple[float, float]] = deque()
        self._cost_samples: deque[tuple[float, float]] = deque()

        # Running mean / stddev for anomaly detection
        self._metric_history: deque[float] = deque(maxlen=100)

        # Session activity tracking for stall detection
        self._session_last_activity: dict[str, float] = {}

        # Alert history
        self._alerts: deque[MonitorAlert] = deque(
            maxlen=self._config.max_alert_history,
        )

        # Latest snapshot
        self._latest_snapshot: MetricsSnapshot = MetricsSnapshot()

        # Control
        self._running = False

        # External callbacks
        self.on_alert: Callable[[MonitorAlert], Any] | None = None
        self.on_metrics: Callable[[MetricsSnapshot], Any] | None = None

    # ── Properties ────────────────────────────────────────────────────

    @property
    def config(self) -> MonitorConfig:
        return self._config

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def latest_snapshot(self) -> MetricsSnapshot:
        return self._latest_snapshot

    @property
    def alerts(self) -> list[MonitorAlert]:
        return list(self._alerts)

    # ── Data ingestion ────────────────────────────────────────────────

    def record_tokens(self, count: int) -> None:
        """Record a token consumption data point.

        Args:
            count: Number of tokens consumed.
        """
        now = time.time()
        self._token_samples.append((now, count))
        self._prune_window()

    def record_error(self, session_id: str, error_type: str = "unknown") -> None:
        """Record an error occurrence.

        Args:
            session_id: The session that produced the error.
            error_type: A label categorising the error.
        """
        now = time.time()
        self._error_samples.append((now, error_type))
        self._prune_window()
        logger.debug("Recorded error for session '%s': %s", session_id, error_type)

    def record_latency(self, seconds: float) -> None:
        """Record a latency data point.

        Args:
            seconds: Latency in seconds.
        """
        now = time.time()
        self._latency_samples.append((now, seconds))
        self._prune_window()

    def record_cost(self, cost: float) -> None:
        """Record a cost data point.

        Args:
            cost: Cost in your chosen unit (e.g. cents).
        """
        now = time.time()
        self._cost_samples.append((now, cost))
        self._prune_window()

    def record_session_activity(self, session_id: str) -> None:
        """Record activity for a session (used for stall detection).

        Args:
            session_id: The session that had activity.
        """
        self._session_last_activity[session_id] = time.time()

    def remove_session(self, session_id: str) -> None:
        """Stop tracking a session.

        Args:
            session_id: The session to remove.
        """
        self._session_last_activity.pop(session_id, None)

    # ── Metric computation ────────────────────────────────────────────

    def compute_metrics(self) -> MetricsSnapshot:
        """Compute the current metrics snapshot from rolling windows.

        Prunes stale samples from all windows, then computes burn rates,
        P95 latency, and cost rate.

        Returns:
            A :class:`MetricsSnapshot` with current values.
        """
        self._prune_window()
        now = time.time()
        window = self._config.metric_window_seconds

        # Token burn rate (tokens per minute)
        token_total = sum(v for _, v in self._token_samples)
        token_burn = (token_total / (window / 60.0)) if window > 0 else 0.0

        # Error rate (errors per minute)
        error_total = len(self._error_samples)
        error_rate = (error_total / (window / 60.0)) if window > 0 else 0.0

        # P95 latency
        if self._latency_samples:
            latencies = sorted(v for _, v in self._latency_samples)
            idx = int(len(latencies) * 0.95)
            latency_p95 = latencies[min(idx, len(latencies) - 1)]
        else:
            latency_p95 = 0.0

        # Cost per minute
        cost_total = sum(v for _, v in self._cost_samples)
        cost_per_min = (cost_total / (window / 60.0)) if window > 0 else 0.0

        self._latest_snapshot = MetricsSnapshot(
            token_burn_rate=round(token_burn, 2),
            error_rate=round(error_rate, 2),
            latency_p95=round(latency_p95, 3),
            cost_per_minute=round(cost_per_min, 4),
            session_count=len(self._session_last_activity),
            timestamp=now,
        )

        return self._latest_snapshot

    # ── Anomaly detection ─────────────────────────────────────────────

    def detect_anomalies(self, metrics: MetricsSnapshot) -> list[MonitorAlert]:
        """Run all detection checks and return any triggered alerts.

        Checks:
        1. **Metric anomaly** — current burn rate deviates from historical
           mean by > N standard deviations.
        2. **Error rate spike** — error rate exceeds threshold.
        3. **High latency** — P95 latency exceeds threshold.
        4. **Session stall** — any session has been inactive past threshold.

        Args:
            metrics: The most recent metrics snapshot.

        Returns:
            A list of triggered alerts (empty if all clear).
        """
        alerts: list[MonitorAlert] = []

        # 1. Anomaly detection on token burn rate
        self._metric_history.append(metrics.token_burn_rate)
        if len(self._metric_history) >= 10:
            mean = statistics.mean(self._metric_history)
            stdev = statistics.stdev(self._metric_history) if len(self._metric_history) > 1 else 0.0
            if stdev > 0:
                z_score = abs(metrics.token_burn_rate - mean) / stdev
                if z_score > self._config.anomaly_stddev_threshold:
                    alerts.append(MonitorAlert(
                        kind=AlertKind.ANOMALY_DETECTED,
                        severity=AlertSeverity.WARNING,
                        message=(
                            f"Token burn rate anomaly: {metrics.token_burn_rate:.0f} tokens/min "
                            f"(z-score={z_score:.1f}, threshold={self._config.anomaly_stddev_threshold:.0f})"
                        ),
                        metric_value=metrics.token_burn_rate,
                        threshold=mean + self._config.anomaly_stddev_threshold * stdev,
                    ))

        # 2. Error rate spike
        if metrics.error_rate > self._config.error_rate_spike_threshold:
            alerts.append(MonitorAlert(
                kind=AlertKind.ERROR_RATE_SPIKE,
                severity=(
                    AlertSeverity.CRITICAL
                    if metrics.error_rate > self._config.error_rate_spike_threshold * 2
                    else AlertSeverity.WARNING
                ),
                message=(
                    f"Error rate spike: {metrics.error_rate:.1f} errors/min "
                    f"(threshold={self._config.error_rate_spike_threshold:.0f})"
                ),
                metric_value=metrics.error_rate,
                threshold=self._config.error_rate_spike_threshold,
            ))

        # 3. High latency
        if metrics.latency_p95 > self._config.latency_p95_threshold_seconds:
            alerts.append(MonitorAlert(
                kind=AlertKind.HIGH_LATENCY,
                severity=AlertSeverity.WARNING,
                message=(
                    f"High P95 latency: {metrics.latency_p95:.2f}s "
                    f"(threshold={self._config.latency_p95_threshold_seconds:.1f}s)"
                ),
                metric_value=metrics.latency_p95,
                threshold=self._config.latency_p95_threshold_seconds,
            ))

        # 4. Session stall detection
        now = time.time()
        for session_id, last_active in self._session_last_activity.items():
            idle_seconds = now - last_active
            if idle_seconds > self._config.stall_threshold_seconds:
                alerts.append(MonitorAlert(
                    kind=AlertKind.SESSION_STALLED,
                    severity=AlertSeverity.WARNING,
                    message=(
                        f"Session '{session_id}' stalled: {idle_seconds:.0f}s idle "
                        f"(threshold={self._config.stall_threshold_seconds:.0f}s)"
                    ),
                    metric_value=idle_seconds,
                    threshold=self._config.stall_threshold_seconds,
                    session_id=session_id,
                ))

        # Record alerts
        self._alerts.extend(alerts)

        return alerts

    # ── Background loop ───────────────────────────────────────────────

    async def start(self) -> None:
        """Start the background monitoring loop.

        Collects metrics on each interval, runs anomaly detection, and
        invokes the ``on_alert`` callback for each triggered alert.
        The loop runs until :meth:`stop` is called.
        """
        self._running = True
        logger.info(
            "ContinuousMonitor started (interval=%ss, window=%ss)",
            self._config.check_interval_seconds,
            self._config.metric_window_seconds,
        )

        while self._running:
            try:
                await asyncio.sleep(self._config.check_interval_seconds)

                if not self._running:
                    break

                metrics = self.compute_metrics()

                # Emit metrics callback
                if self.on_metrics:
                    try:
                        result = self.on_metrics(metrics)
                        if asyncio.iscoroutine(result):
                            await result
                    except Exception:
                        logger.exception("Metrics callback failed")

                alerts = self.detect_anomalies(metrics)

                # Emit alert callbacks
                for alert in alerts:
                    if self.on_alert:
                        try:
                            result = self.on_alert(alert)
                            if asyncio.iscoroutine(result):
                                await result
                        except Exception:
                            logger.exception("Alert callback failed for %s", alert.kind.value)

            except asyncio.CancelledError:
                logger.info("ContinuousMonitor cancelled")
                self._running = False
                raise
            except Exception:
                logger.exception("ContinuousMonitor cycle error")

        logger.info("ContinuousMonitor stopped")

    def stop(self) -> None:
        """Stop the background monitoring loop."""
        self._running = False
        logger.info("ContinuousMonitor stopping...")

    # ── Alert management ──────────────────────────────────────────────

    def recent_alerts(
        self,
        kind: AlertKind | None = None,
        severity: AlertSeverity | None = None,
        limit: int = 10,
    ) -> list[MonitorAlert]:
        """Return recent alerts, optionally filtered.

        Args:
            kind: Filter by alert kind (None = all kinds).
            severity: Filter by severity (None = all severities).
            limit: Maximum number of alerts to return.

        Returns:
            A list of matching alerts, most recent first.
        """
        filtered: list[MonitorAlert] = list(self._alerts)

        if kind is not None:
            filtered = [a for a in filtered if a.kind == kind]
        if severity is not None:
            filtered = [a for a in filtered if a.severity == severity]

        # Reverse: most recent first
        filtered.reverse()
        return filtered[:limit]

    def clear_alerts(self) -> None:
        """Clear all stored alerts."""
        self._alerts.clear()

    # ── Statistics ────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics for the continuous monitor.

        Returns:
            Dict with keys ``is_running``, ``alerts_count``,
            ``latest_snapshot``, ``session_count``.
        """
        return {
            "is_running": self._running,
            "alerts_count": len(self._alerts),
            "latest_snapshot": {
                "token_burn_rate": self._latest_snapshot.token_burn_rate,
                "error_rate": self._latest_snapshot.error_rate,
                "latency_p95": self._latest_snapshot.latency_p95,
                "cost_per_minute": self._latest_snapshot.cost_per_minute,
                "session_count": self._latest_snapshot.session_count,
            },
            "session_count": len(self._session_last_activity),
        }

    # ── Internal helpers ──────────────────────────────────────────────

    def _prune_window(self) -> None:
        """Remove samples outside the metric window."""
        cutoff = time.time() - self._config.metric_window_seconds

        while self._token_samples and self._token_samples[0][0] < cutoff:
            self._token_samples.popleft()
        while self._error_samples and self._error_samples[0][0] < cutoff:
            self._error_samples.popleft()
        while self._latency_samples and self._latency_samples[0][0] < cutoff:
            self._latency_samples.popleft()
        while self._cost_samples and self._cost_samples[0][0] < cutoff:
            self._cost_samples.popleft()
