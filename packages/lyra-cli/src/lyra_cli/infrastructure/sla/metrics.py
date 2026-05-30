"""SLA Metrics — measurement collection and percentile computation for SLA tracking."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class SLAMetricType(StrEnum):
    UPTIME = "uptime"
    LATENCY = "latency"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"
    AVAILABILITY = "availability"
    CUSTOM = "custom"


@dataclass(frozen=True)
class SLAMetricSnapshot:
    metric_name: str
    metric_type: SLAMetricType
    value: float
    timestamp: float


@dataclass
class SLAMetricSeries:
    metric_name: str
    metric_type: SLAMetricType
    values: list[float] = field(default_factory=list)
    timestamps: list[float] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.values)

    @property
    def latest(self) -> float | None:
        return self.values[-1] if self.values else None

    @property
    def mean(self) -> float:
        if not self.values:
            return 0.0
        return sum(self.values) / len(self.values)

    def add(self, value: float, timestamp: float) -> None:
        self.values.append(value)
        self.timestamps.append(timestamp)

    def percentile(self, pct: float) -> float:
        if not self.values:
            return 0.0
        sorted_vals = sorted(self.values)
        idx = int(len(sorted_vals) * pct / 100.0)
        idx = min(idx, len(sorted_vals) - 1)
        return sorted_vals[idx]

    def get_values_in_window(self, window_start: float) -> list[float]:
        return [
            v for v, ts in zip(self.values, self.timestamps)
            if ts >= window_start
        ]
