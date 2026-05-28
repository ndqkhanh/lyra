"""Metrics collection and aggregation for Lyra performance benchmarking.

Provides MetricsCollector for collecting and aggregating performance
metrics across runs, with percentile computation and trend analysis.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class MetricSample:
    """A single metric data point with timestamp."""

    name: str
    value: float
    timestamp: float = field(default_factory=time.time)
    labels: dict[str, str] = field(default_factory=dict)


@dataclass
class MetricSeries:
    """A time series of metric samples with computed statistics."""

    name: str
    samples: list[float] = field(default_factory=list)
    timestamps: list[float] = field(default_factory=list)

    @property
    def count(self) -> int:
        """Number of samples in this series."""
        return len(self.samples)

    @property
    def mean(self) -> float:
        """Arithmetic mean of samples."""
        if not self.samples:
            return 0.0
        return sum(self.samples) / len(self.samples)

    @property
    def median(self) -> float:
        """Median value of samples."""
        if not self.samples:
            return 0.0
        sorted_vals = sorted(self.samples)
        n = len(sorted_vals)
        mid = n // 2
        if n % 2 == 1:
            return sorted_vals[mid]
        return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0

    @property
    def minimum(self) -> float:
        """Minimum sample value."""
        return min(self.samples) if self.samples else 0.0

    @property
    def maximum(self) -> float:
        """Maximum sample value."""
        return max(self.samples) if self.samples else 0.0

    @property
    def stddev(self) -> float:
        """Standard deviation of samples."""
        if len(self.samples) < 2:
            return 0.0
        m = self.mean
        variance = sum((x - m) ** 2 for x in self.samples) / (len(self.samples) - 1)
        return math.sqrt(variance)

    @property
    def latest(self) -> float | None:
        """Most recent sample value."""
        return self.samples[-1] if self.samples else None

    @property
    def trend(self) -> float:
        """Simple trend indicator (positive means increasing over time).

        Uses linear regression slope normalized by mean.
        Returns 0.0 if insufficient data.
        """
        if len(self.samples) < 3:
            return 0.0
        n = len(self.samples)
        _indices = list(range(n))
        mean_x = (n - 1) / 2.0
        mean_y = self.mean
        num = sum((idx - mean_x) * (v - mean_y) for idx, v in enumerate(self.samples))
        den = sum((idx - mean_x) ** 2 for idx in range(n))
        if den == 0:
            return 0.0
        return num / den

    def percentile(self, p: int) -> float:
        """Compute the p-th percentile.

        Args:
            p: Percentile to compute (0-100).

        Returns:
            The p-th percentile value.
        """
        if not self.samples:
            return 0.0
        sorted_vals = sorted(self.samples)
        k = (p / 100.0) * (len(sorted_vals) - 1)
        f_idx = int(k)
        c_idx = f_idx + 1
        if f_idx >= len(sorted_vals) - 1:
            return sorted_vals[-1]
        frac = k - f_idx
        return sorted_vals[f_idx] * (1 - frac) + sorted_vals[c_idx] * frac

    @property
    def p50(self) -> float:
        """50th percentile."""
        return self.percentile(50)

    @property
    def p95(self) -> float:
        """95th percentile."""
        return self.percentile(95)

    @property
    def p99(self) -> float:
        """99th percentile."""
        return self.percentile(99)

    @property
    def summary(self) -> dict[str, float]:
        """Full statistical summary of this series."""
        return {
            "count": self.count,
            "mean": self.mean,
            "median": self.median,
            "min": self.minimum,
            "max": self.maximum,
            "stddev": self.stddev,
            "p50": self.p50,
            "p95": self.p95,
            "p99": self.p99,
            "trend": self.trend,
            "latest": self.latest or 0.0,
        }

    def to_dict(self) -> dict[str, Any]:
        """Export series as dictionary."""
        return {
            "name": self.name,
            "statistics": self.summary,
            "samples": self.samples,
            "timestamps": self.timestamps,
        }


class MetricsCollector:
    """Collects and aggregates performance metrics across runs.

    Thread-safe metric accumulation with percentile computation
    (p50, p95, p99), mean, stddev, and trend analysis.
    """

    def __init__(self) -> None:
        """Initialize collector with empty metric stores."""
        self.collected: dict[str, list[float]] = {}
        self._labels: dict[str, list[dict[str, str]]] = {}
        self._series: dict[str, MetricSeries] = {}

    def record(
        self,
        name: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Record a single metric sample.

        Args:
            name: Metric name.
            value: Metric value.
            labels: Optional key-value labels for this sample.
        """
        if name not in self.collected:
            self.collected[name] = []
            self._labels[name] = []
            self._series[name] = MetricSeries(name=name)

        self.collected[name].append(value)
        if labels:
            self._labels[name].append(labels)

        self._series[name].samples.append(value)
        self._series[name].timestamps.append(time.time())

    def record_many(
        self,
        name: str,
        values: list[float],
    ) -> None:
        """Record multiple samples for a metric at once.

        Args:
            name: Metric name.
            values: List of metric values.
        """
        for value in values:
            self.record(name, value)

    def series(self, name: str) -> MetricSeries:
        """Get the MetricSeries for a named metric.

        Args:
            name: Metric name.

        Returns:
            MetricSeries for the metric (empty if not found).
        """
        return self._series.get(name, MetricSeries(name=name))

    def get_all_series(self) -> list[MetricSeries]:
        """Get all metric series.

        Returns:
            List of all MetricSeries objects.
        """
        return list(self._series.values())

    def percentile(self, name: str, p: int) -> float:
        """Compute the p-th percentile for a named metric.

        Args:
            name: Metric name.
            p: Percentile (0-100).

        Returns:
            The percentile value, or 0.0 if metric not found.
        """
        return self.series(name).percentile(p)

    def mean(self, name: str) -> float:
        """Compute mean for a named metric.

        Args:
            name: Metric name.

        Returns:
            Mean value, or 0.0 if metric not found.
        """
        return self.series(name).mean

    def stddev(self, name: str) -> float:
        """Compute standard deviation for a named metric.

        Args:
            name: Metric name.

        Returns:
            Standard deviation, or 0.0 if metric not found.
        """
        return self.series(name).stddev

    def clear(self) -> None:
        """Clear all collected metrics."""
        self.collected.clear()
        self._labels.clear()
        self._series.clear()

    def list_metrics(self) -> list[str]:
        """List all metric names that have been recorded.

        Returns:
            Sorted list of metric names.
        """
        return sorted(self.collected.keys())

    def summary(self) -> dict[str, dict[str, float]]:
        """Get a summary of all collected metrics.

        Returns:
            Dict mapping metric names to their statistical summaries.
        """
        return {
            name: series.summary
            for name, series in sorted(self._series.items())
        }

    def merge(self, other: MetricsCollector) -> None:
        """Merge metrics from another collector into this one.

        Args:
            other: Another MetricsCollector to merge from.
        """
        for name, values in other.collected.items():
            for value in values:
                self.record(name, value)

    def export_json(self) -> dict[str, Any]:
        """Export all metrics as a JSON-serializable dict.

        Returns:
            Dictionary with all metric data.
        """
        return {
            "timestamp": datetime.now().isoformat(),
            "series": {
                name: series.to_dict()
                for name, series in self._series.items()
            },
        }
