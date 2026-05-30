"""Metrics Command — user-facing `/metrics` CLI command for querying swarm metrics.

Provides metric recording, querying, aggregation, and formatted output
for counters, gauges, and histograms.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import StrEnum
from statistics import mean, median


class MetricType(StrEnum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


class MetricsFormat(StrEnum):
    TEXT = "text"
    JSON = "json"


@dataclass(frozen=True)
class MetricsQuery:
    metric_name: str
    metric_type: MetricType = MetricType.GAUGE
    labels: dict[str, str] = field(default_factory=dict)


@dataclass
class MetricsFilter:
    time_range_seconds: float | None = None
    labels: dict[str, str] = field(default_factory=dict)
    min_value: float | None = None
    max_value: float | None = None


@dataclass
class _MetricSeries:
    metric_type: MetricType
    values: list[float] = field(default_factory=list)
    timestamps: list[float] = field(default_factory=list)
    labels: dict[str, str] = field(default_factory=dict)


class MetricsCommand:
    """User-facing `/metrics` command for querying operational metrics.

    Records and queries counters, gauges, and histograms with
    optional label-based filtering and time-range queries.

    Usage::

        cmd = MetricsCommand()
        cmd.record("api_latency_ms", 42.5, MetricType.HISTOGRAM)
        results = cmd.query("api_latency_ms", MetricsFilter(time_range_seconds=60))
        print(cmd.format_output(format=MetricsFormat.JSON))
    """

    def __init__(self) -> None:
        self._series: dict[str, _MetricSeries] = {}

    @property
    def metric_count(self) -> int:
        return len(self._series)

    def record(
        self,
        name: str,
        value: float,
        metric_type: MetricType = MetricType.GAUGE,
        labels: dict[str, str] | None = None,
    ) -> None:
        if name not in self._series:
            self._series[name] = _MetricSeries(
                metric_type=metric_type,
                labels=labels or {},
            )
        series = self._series[name]
        series.values.append(value)
        series.timestamps.append(time.monotonic())

    def get_metric(self, name: str) -> dict | None:
        series = self._series.get(name)
        if series is None:
            return None
        return self._build_metric_data(series)

    def query(self, name: str, filter_: MetricsFilter) -> dict | None:
        series = self._series.get(name)
        if series is None:
            return None
        values = series.values
        if filter_.time_range_seconds is not None:
            cutoff = time.monotonic() - filter_.time_range_seconds
            values = [
                v for v, ts in zip(values, series.timestamps)
                if ts >= cutoff
            ]
        if filter_.min_value is not None:
            values = [v for v in values if v >= filter_.min_value]
        if filter_.max_value is not None:
            values = [v for v in values if v <= filter_.max_value]
        return self._build_metric_data(series, values)

    def format_output(self, format: MetricsFormat = MetricsFormat.TEXT) -> str:
        if format == MetricsFormat.JSON:
            data = {name: self._build_metric_data(s) for name, s in self._series.items()}
            return json.dumps(data, indent=2)
        lines = []
        for name, series in self._series.items():
            data = self._build_metric_data(series)
            lines.append(f"{name} [{series.metric_type.value}] count={data['count']}")
            if data["count"] > 0:
                lines.append(f"  min={data['min']:.2f} max={data['max']:.2f} "
                             f"mean={data['mean']:.2f}")
        return "\n".join(lines) if lines else "No metrics recorded"

    def list_metric_names(self) -> list[str]:
        return sorted(self._series.keys())

    def get_summary(self, name: str) -> dict | None:
        series = self._series.get(name)
        if series is None:
            return None
        values = sorted(series.values)
        if not values:
            return None
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": mean(values),
            "median": median(values),
            "p50": self._percentile(values, 50),
            "p95": self._percentile(values, 95),
            "p99": self._percentile(values, 99),
        }

    def reset(self) -> None:
        self._series.clear()

    @staticmethod
    def _percentile(sorted_values: list[float], pct: float) -> float:
        if not sorted_values:
            return 0.0
        idx = int(len(sorted_values) * pct / 100.0)
        idx = min(idx, len(sorted_values) - 1)
        return sorted_values[idx]

    @staticmethod
    def _build_metric_data(
        series: _MetricSeries, values: list[float] | None = None
    ) -> dict:
        vals = values if values is not None else series.values
        if not vals:
            return {"count": 0, "type": series.metric_type.value}
        return {
            "type": series.metric_type.value,
            "count": len(vals),
            "min": min(vals),
            "max": max(vals),
            "mean": mean(vals),
            "labels": series.labels,
        }
