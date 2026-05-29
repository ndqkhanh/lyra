"""Performance regression detection with historical baseline comparison.

Detects performance regressions by comparing current benchmark runs
against stored historical baselines using configurable thresholds.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class RegressionSeverity(StrEnum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class RegressionEvent:
    metric_name: str
    current_value: float
    baseline_mean: float
    baseline_std: float
    deviation_pct: float
    severity: RegressionSeverity
    timestamp: float


@dataclass
class RegressionConfig:
    history_path: str = "/tmp/lyra_regression_history"
    critical_threshold_pct: float = 20.0
    warning_threshold_pct: float = 10.0
    info_threshold_pct: float = 5.0
    min_baseline_samples: int = 5
    max_history_per_metric: int = 1000


@dataclass
class MetricHistory:
    values: list[float] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.values)

    @property
    def mean(self) -> float:
        if not self.values:
            return 0.0
        return sum(self.values) / len(self.values)

    @property
    def std(self) -> float:
        if len(self.values) < 2:
            return 0.0
        m = self.mean
        variance = sum((x - m) ** 2 for x in self.values) / len(self.values)
        return variance**0.5

    def add(self, value: float, max_items: int = 1000) -> None:
        self.values.append(value)
        if len(self.values) > max_items:
            self.values = self.values[-max_items:]

    def to_dict(self) -> dict:
        return {"values": self.values}

    @classmethod
    def from_dict(cls, data: dict) -> MetricHistory:
        return cls(values=data.get("values", []))


class RegressionDetector:
    """Detects performance regressions against historical baselines."""

    def __init__(self, config: RegressionConfig | None = None) -> None:
        self.config = config or RegressionConfig()
        self._history: dict[str, MetricHistory] = {}
        self._events: list[RegressionEvent] = []
        self._load_history()

    @property
    def recent_events(self) -> list[RegressionEvent]:
        return list(self._events)

    def record(
        self, metric: str, value: float, timestamp: float | None = None
    ) -> RegressionEvent | None:
        if metric not in self._history:
            self._history[metric] = MetricHistory()

        hist = self._history[metric]
        event = None

        if hist.count >= self.config.min_baseline_samples:
            deviation = self._compute_deviation(value, hist.mean)
            severity = self._classify(deviation)
            if severity is not None:
                event = RegressionEvent(
                    metric_name=metric,
                    current_value=value,
                    baseline_mean=hist.mean,
                    baseline_std=hist.std,
                    deviation_pct=round(deviation, 2),
                    severity=severity,
                    timestamp=timestamp or time.time(),
                )
                self._events.append(event)

        hist.add(value, self.config.max_history_per_metric)
        return event

    def check(self, metric: str, value: float) -> RegressionSeverity | None:
        hist = self._history.get(metric)
        if hist is None or hist.count < self.config.min_baseline_samples:
            return None
        deviation = self._compute_deviation(value, hist.mean)
        return self._classify(deviation)

    def compare(
        self, current: dict[str, float], _baseline_tag: str | None = None
    ) -> list[RegressionEvent]:
        results: list[RegressionEvent] = []
        for metric, value in current.items():
            event = self.record(metric, value)
            if event is not None:
                results.append(event)
        return results

    def get_baseline(self, metric: str) -> dict | None:
        hist = self._history.get(metric)
        if hist is None or hist.count == 0:
            return None
        return {
            "metric": metric,
            "count": hist.count,
            "mean": round(hist.mean, 4),
            "std": round(hist.std, 4),
            "min": round(min(hist.values), 4),
            "max": round(max(hist.values), 4),
        }

    def stats(self) -> dict:
        return {
            "metrics_tracked": len(self._history),
            "total_events": len(self._events),
            "events_by_severity": {
                s.value: sum(1 for e in self._events if e.severity == s) for s in RegressionSeverity
            },
            "baselines": {
                name: {"count": h.count, "mean": round(h.mean, 4), "std": round(h.std, 4)}
                for name, h in self._history.items()
                if h.count > 0
            },
        }

    def save_history(self) -> None:
        path = Path(self.config.history_path)
        path.mkdir(parents=True, exist_ok=True)
        data = {name: h.to_dict() for name, h in self._history.items()}
        (path / "history.json").write_text(json.dumps(data, indent=2))

    def _load_history(self) -> None:
        path = Path(self.config.history_path) / "history.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text())
            self._history = {name: MetricHistory.from_dict(h) for name, h in data.items()}
        except (json.JSONDecodeError, OSError):
            pass

    def _compute_deviation(self, current: float, baseline_mean: float) -> float:
        if baseline_mean == 0.0:
            return 0.0
        return abs((current - baseline_mean) / baseline_mean) * 100.0

    def _classify(self, deviation_pct: float) -> RegressionSeverity | None:
        if deviation_pct >= self.config.critical_threshold_pct:
            return RegressionSeverity.CRITICAL
        if deviation_pct >= self.config.warning_threshold_pct:
            return RegressionSeverity.WARNING
        if deviation_pct >= self.config.info_threshold_pct:
            return RegressionSeverity.INFO
        return None
