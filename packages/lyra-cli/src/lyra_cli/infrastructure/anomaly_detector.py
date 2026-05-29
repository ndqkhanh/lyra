"""ML Anomaly Detection — Z-score and moving-average based anomaly detection.

Detects anomalies in Lyra's operational metrics:
  - Latency spikes (routing, API calls, tool execution)
  - Error rate surges
  - Memory/CPU utilization anomalies
  - Throughput drops

Uses rolling statistics (mean, stddev) with configurable window sizes.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import StrEnum


class AnomalySeverity(StrEnum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class AnomalyEvent:
    metric_name: str
    value: float
    expected_mean: float
    expected_std: float
    z_score: float
    severity: AnomalySeverity
    timestamp: float


@dataclass
class DetectorConfig:
    window_size: int = 100
    z_score_critical: float = 4.0
    z_score_warning: float = 3.0
    z_score_info: float = 2.0
    min_samples: int = 10
    decay_factor: float = 0.95  # EWMA decay


class MetricTracker:
    """Tracks rolling statistics for a single metric."""

    def __init__(self, window_size: int = 100, decay: float = 0.95) -> None:
        self._window: deque[float] = deque(maxlen=window_size)
        self._decay = decay
        self._ewma: float | None = None
        self._ewma_var: float | None = None

    @property
    def count(self) -> int:
        return len(self._window)

    @property
    def mean(self) -> float:
        if not self._window:
            return 0.0
        return sum(self._window) / len(self._window)

    @property
    def std(self) -> float:
        if len(self._window) < 2:
            return 0.0
        m = self.mean
        variance = sum((x - m) ** 2 for x in self._window) / len(self._window)
        return variance**0.5

    def add(self, value: float) -> None:
        self._window.append(value)
        if self._ewma is None:
            self._ewma = value
            self._ewma_var = 0.0
        else:
            alpha = 1 - self._decay
            self._ewma = self._decay * self._ewma + alpha * value
            self._ewma_var = (
                self._decay * self._ewma_var + alpha * (value - self._ewma) ** 2
            )  # type: ignore[operator]

    def z_score(self, value: float) -> float:
        """Return the z-score of a value relative to the rolling window."""
        if len(self._window) < 2:
            return 0.0
        m = self.mean
        s = self.std
        if s == 0.0:
            return 0.0
        return (value - m) / s


class AnomalyDetector:
    """Detects anomalies across multiple metrics using z-score thresholds."""

    def __init__(self, config: DetectorConfig | None = None) -> None:
        self.config = config or DetectorConfig()
        self._trackers: dict[str, MetricTracker] = {}
        self._events: deque[AnomalyEvent] = deque(maxlen=1000)

    @property
    def event_count(self) -> int:
        return len(self._events)

    @property
    def recent_events(self) -> list[AnomalyEvent]:
        return list(self._events)

    def register_metric(self, name: str) -> None:
        if name not in self._trackers:
            self._trackers[name] = MetricTracker(
                window_size=self.config.window_size,
                decay=self.config.decay_factor,
            )

    def observe(
        self, metric: str, value: float, timestamp: float | None = None
    ) -> AnomalyEvent | None:
        """Feed an observation and check for anomaly."""
        import time as _time

        if metric not in self._trackers:
            self.register_metric(metric)

        tracker = self._trackers[metric]
        z = tracker.z_score(value) if tracker.count >= self.config.min_samples else 0.0
        tracker.add(value)

        severity = self._classify(abs(z))
        if severity is None:
            return None

        event = AnomalyEvent(
            metric_name=metric,
            value=value,
            expected_mean=tracker.mean,
            expected_std=tracker.std,
            z_score=z,
            severity=severity,
            timestamp=timestamp or _time.time(),
        )
        self._events.append(event)
        return event

    def check(self, metric: str, value: float) -> AnomalySeverity | None:
        """Check if a value is anomalous without recording it."""
        tracker = self._trackers.get(metric)
        if tracker is None or tracker.count < self.config.min_samples:
            return None

        z = abs(tracker.z_score(value))
        return self._classify(z)

    def stats(self) -> dict:
        return {
            "metrics_tracked": len(self._trackers),
            "total_events": self.event_count,
            "events_by_severity": {
                s.value: sum(1 for e in self._events if e.severity == s) for s in AnomalySeverity
            },
            "metric_summaries": {
                name: {"count": t.count, "mean": t.mean, "std": t.std}
                for name, t in self._trackers.items()
            },
        }

    def _classify(self, abs_z: float) -> AnomalySeverity | None:
        if abs_z >= self.config.z_score_critical:
            return AnomalySeverity.CRITICAL
        if abs_z >= self.config.z_score_warning:
            return AnomalySeverity.WARNING
        if abs_z >= self.config.z_score_info:
            return AnomalySeverity.INFO
        return None
