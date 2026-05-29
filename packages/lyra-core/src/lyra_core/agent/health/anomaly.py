"""Statistical anomaly detection on health signal time series."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from enum import Enum


class AnomalyType(str, Enum):
    SPIKE = "spike"
    DIP = "dip"
    DRIFT = "drift"
    PATTERN_BREAK = "pattern_break"


@dataclass(frozen=True)
class AnomalyRecord:
    anomaly_type: AnomalyType
    source: str
    metric: str
    detected_value: float
    expected_range: tuple[float, float]
    z_score: float
    confidence: float
    description: str = ""
    timestamp: float = field(default_factory=time.time)

    @property
    def is_significant(self) -> bool:
        return self.confidence >= 0.7


@dataclass
class AnomalyDetector:
    """Detects anomalies in health signal time series using z-score analysis.

    Usage::

        detector = AnomalyDetector(z_threshold=2.0)
        anomaly = detector.detect([0.1, 0.2, 0.15, 0.9, 0.12], source="error_rate")
        if anomaly and anomaly.is_significant:
            print(f"Anomaly: {anomaly.description}")
    """

    z_threshold: float = 2.0
    drift_window: int = 20
    min_samples: int = 5
    _baselines: dict[str, tuple[float, float]] = field(default_factory=dict)

    def detect(
        self,
        values: list[float],
        source: str,
        *,
        metric: str = "default",
    ) -> AnomalyRecord | None:
        if len(values) < self.min_samples:
            return None

        mean = sum(values[:-1]) / (len(values) - 1) if len(values) > 1 else values[0]
        std = self._std(values[:-1]) if len(values) > 1 else 0.0
        latest = values[-1]

        if std < 1e-10:
            if abs(latest - mean) < 1e-10:
                return None
            std = abs(mean) * 0.01 if abs(mean) > 1e-10 else 0.01

        z_score = (latest - mean) / std
        abs_z = abs(z_score)

        if abs_z < self.z_threshold:
            return None

        anomaly_type = AnomalyType.SPIKE if z_score > 0 else AnomalyType.DIP
        confidence = min(abs_z / (self.z_threshold * 2), 1.0)
        margin = self.z_threshold * std

        return AnomalyRecord(
            anomaly_type=anomaly_type,
            source=source,
            metric=metric,
            detected_value=latest,
            expected_range=(mean - margin, mean + margin),
            z_score=round(z_score, 4),
            confidence=round(confidence, 4),
            description=f"{anomaly_type.value} detected: value {latest:.4f} (z={z_score:.2f}), "
            f"expected [{mean - margin:.4f}, {mean + margin:.4f}]",
        )

    def detect_drift(
        self,
        values: list[float],
        source: str,
        *,
        metric: str = "default",
    ) -> AnomalyRecord | None:
        if len(values) < self.drift_window:
            return None

        key = f"{source}:{metric}"
        baseline = self._baselines.get(key)

        if baseline is None:
            self._baselines[key] = (sum(values) / len(values), self._std(values))
            return None

        baseline_mean, baseline_std = baseline
        recent = values[-self.drift_window // 2 :]
        recent_mean = sum(recent) / len(recent)

        effective_std = baseline_std if baseline_std > 1e-10 else abs(baseline_mean) * 0.05
        if effective_std < 1e-10:
            effective_std = 0.01

        z_score = (recent_mean - baseline_mean) / (effective_std / math.sqrt(len(recent)))
        abs_z = abs(z_score)

        if abs_z < self.z_threshold:
            return None

        anomaly_type = AnomalyType.DRIFT if z_score > 0 else AnomalyType.DIP
        confidence = min(abs_z / (self.z_threshold * 2), 1.0)

        return AnomalyRecord(
            anomaly_type=anomaly_type,
            source=source,
            metric=metric,
            detected_value=recent_mean,
            expected_range=(baseline_mean - self.z_threshold * effective_std, baseline_mean + self.z_threshold * effective_std),
            z_score=round(z_score, 4),
            confidence=round(confidence, 4),
            description=f"drift from baseline {baseline_mean:.4f} to {recent_mean:.4f} (z={z_score:.2f})",
        )

    def reset_baseline(self, source: str, metric: str = "default") -> None:
        key = f"{source}:{metric}"
        self._baselines.pop(key, None)

    def clear_baselines(self) -> None:
        self._baselines.clear()

    @staticmethod
    def _std(values: list[float]) -> float:
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
        return math.sqrt(variance)
