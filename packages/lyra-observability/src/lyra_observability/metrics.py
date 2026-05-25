"""Metrics Collector — counter, gauge, and histogram metric types.

Provides a MetricsCollector class that supports labeled metrics and
percentile computation for histograms.
"""

from __future__ import annotations

import enum
import math
import time
from collections import defaultdict
from dataclasses import dataclass, field


class MetricType(enum.Enum):
    """Supported metric types."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


@dataclass(frozen=True)
class MetricValue:
    """A single metric data point.

    Attributes:
        name: Metric name.
        type: Metric type (counter, gauge, histogram).
        value: Numeric value.
        labels: Immutable set of (key, value) pairs for dimensionality.
        timestamp: Unix timestamp when the metric was recorded.
    """

    name: str
    type: MetricType
    value: float
    labels: frozenset[tuple[str, str]] = field(default_factory=frozenset)
    timestamp: float = field(default_factory=time.time)


class MetricsCollector:
    """Collects and queries counters, gauges, and histograms.

    All operations are in-memory and thread-safe by convention (no locks
    needed in an asyncio context).
    """

    def __init__(self) -> None:
        self._counters: dict[
            tuple[str, frozenset[tuple[str, str]]], float
        ] = defaultdict(float)
        self._gauges: dict[
            tuple[str, frozenset[tuple[str, str]]], float
        ] = {}
        self._histograms: dict[
            tuple[str, frozenset[tuple[str, str]]], list[float]
        ] = defaultdict(list)
        self._all_metrics: list[MetricValue] = []

    @staticmethod
    def _make_key(
        name: str, labels: dict[str, str] | None
    ) -> tuple[str, frozenset[tuple[str, str]]]:
        """Build a canonical lookup key from name and optional labels."""
        if labels:
            return (name, frozenset(sorted(labels.items())))
        return (name, frozenset())

    @staticmethod
    def _parse_query_labels(
        labels: dict[str, str] | None,
    ) -> frozenset[tuple[str, str]] | None:
        """Convert optional query labels to frozenset, or None for wildcard."""
        if labels is not None:
            return frozenset(sorted(labels.items()))
        return None

    def counter(
        self,
        name: str,
        value: float = 1.0,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Increment a counter metric.

        Args:
            name: Metric name.
            value: Amount to increment by (default 1.0).
            labels: Optional label dimensions.
        """
        key = self._make_key(name, labels)
        self._counters[key] += value
        self._all_metrics.append(
            MetricValue(
                name=name, type=MetricType.COUNTER, value=value, labels=key[1]
            )
        )

    def gauge(
        self,
        name: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Set a gauge metric to a specific value.

        Args:
            name: Metric name.
            value: Current value to record.
            labels: Optional label dimensions.
        """
        key = self._make_key(name, labels)
        self._gauges[key] = value
        self._all_metrics.append(
            MetricValue(
                name=name, type=MetricType.GAUGE, value=value, labels=key[1]
            )
        )

    def histogram(
        self,
        name: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Record a value in a histogram metric.

        Args:
            name: Metric name.
            value: Observation value to record.
            labels: Optional label dimensions.
        """
        key = self._make_key(name, labels)
        self._histograms[key].append(value)
        self._all_metrics.append(
            MetricValue(
                name=name, type=MetricType.HISTOGRAM, value=value, labels=key[1]
            )
        )

    def get_counter(
        self,
        name: str,
        labels: dict[str, str] | None = None,
    ) -> float:
        """Return the total for a counter, optionally filtered by labels.

        Args:
            name: Metric name.
            labels: If None, aggregates across all label variants.
                    If a dict, returns only the matching variant.

        Returns:
            Sum of all counter values matching the query.
        """
        query = self._parse_query_labels(labels)
        total = 0.0
        for (n, lbls), val in self._counters.items():
            if n == name and (query is None or lbls == query):
                total += val
        return total

    def get_gauge(
        self,
        name: str,
        labels: dict[str, str] | None = None,
    ) -> float:
        """Return the current gauge value, optionally filtered by labels.

        Args:
            name: Metric name.
            labels: If None, aggregates across all label variants.
                    If a dict, returns only the matching variant.

        Returns:
            Sum of gauge values matching the query.
        """
        query = self._parse_query_labels(labels)
        total = 0.0
        for (n, lbls), val in self._gauges.items():
            if n == name and (query is None or lbls == query):
                total += val
        return total

    def get_histogram_stats(
        self,
        name: str,
        labels: dict[str, str] | None = None,
    ) -> dict[str, float | int]:
        """Return statistics for a histogram metric.

        Args:
            name: Metric name.
            labels: If None, aggregates across all label variants.
                    If a dict, returns only the matching variant.

        Returns:
            Dict with ``count``, ``sum``, ``avg``, ``p50``, ``p95``, ``p99``.
        """
        query = self._parse_query_labels(labels)
        values: list[float] = []
        for (n, lbls), vals in self._histograms.items():
            if n == name and (query is None or lbls == query):
                values.extend(vals)

        if not values:
            return {
                "count": 0,
                "sum": 0.0,
                "avg": 0.0,
                "p50": 0.0,
                "p95": 0.0,
                "p99": 0.0,
            }

        sorted_vals = sorted(values)
        count = len(sorted_vals)
        total = sum(sorted_vals)

        def _percentile(p: float) -> float:
            """Compute the p-th percentile using linear interpolation."""
            k = (count - 1) * p / 100.0
            f = math.floor(k)
            c = math.ceil(k)
            if f == c:
                return sorted_vals[int(k)]
            return sorted_vals[int(f)] * (c - k) + sorted_vals[int(c)] * (
                k - f
            )

        return {
            "count": count,
            "sum": total,
            "avg": total / count,
            "p50": _percentile(50),
            "p95": _percentile(95),
            "p99": _percentile(99),
        }

    def get_all_metrics(self) -> dict[str, list[MetricValue]]:
        """Return all recorded metrics grouped by name.

        Returns:
            Dict mapping metric names to lists of MetricValue objects.
        """
        result: dict[str, list[MetricValue]] = defaultdict(list)
        for m in self._all_metrics:
            result[m.name].append(m)
        return dict(result)
