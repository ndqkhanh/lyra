"""Vibes dashboard — agent emotional state and sentiment monitoring.

Displays real-time agent vibes (confidence, curiosity, caution, etc.)
as a terminal dashboard with trend indicators and alert thresholds.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import StrEnum


class VibeDimension(StrEnum):
    CONFIDENCE = "confidence"
    CURIOSITY = "curiosity"
    CAUTION = "caution"
    CREATIVITY = "creativity"
    DETERMINATION = "determination"
    HELPFULNESS = "helpfulness"


@dataclass(frozen=True)
class VibeReading:
    dimension: VibeDimension
    score: float
    trend: float
    timestamp: float


@dataclass(frozen=True)
class VibeSnapshot:
    readings: list[VibeReading]
    overall_vibe: str
    alert_count: int
    captured_at: float

    @property
    def dominant_dimension(self) -> VibeDimension | None:
        if not self.readings:
            return None
        return max(self.readings, key=lambda r: r.score).dimension


class VibesDashboard:
    """Real-time agent vibes monitor with trend tracking.

    Tracks six vibe dimensions, computes trends via exponential
    moving average, and fires alerts when dimensions exceed
    healthy thresholds.
    """

    ALERT_HIGH = 0.95
    ALERT_LOW = 0.1

    def __init__(self, history_size: int = 100) -> None:
        self.history_size = history_size
        self._history: dict[VibeDimension, list[VibeReading]] = {d: [] for d in VibeDimension}
        self._alerts: list[str] = []

    def record(self, dimension: VibeDimension, score: float) -> VibeReading:
        score = max(0.0, min(1.0, score))
        previous = self._history[dimension][-1].score if self._history[dimension] else score
        trend = round(score - previous, 3)

        reading = VibeReading(
            dimension=dimension,
            score=round(score, 3),
            trend=trend,
            timestamp=time.time(),
        )
        self._history[dimension].append(reading)
        if len(self._history[dimension]) > self.history_size:
            self._history[dimension] = self._history[dimension][-self.history_size :]

        self._check_alerts(reading)
        return reading

    def snapshot(self) -> VibeSnapshot:
        readings = [self._history[d][-1] for d in VibeDimension if self._history[d]]
        latest = readings[-1].timestamp if readings else time.time()

        if not readings:
            return VibeSnapshot(
                readings=[],
                overall_vibe="neutral",
                alert_count=len(self._alerts),
                captured_at=latest,
            )

        avg = sum(r.score for r in readings) / len(readings)
        if avg > 0.8:
            vibe = "excellent"
        elif avg > 0.6:
            vibe = "positive"
        elif avg > 0.4:
            vibe = "neutral"
        elif avg > 0.2:
            vibe = "cautious"
        else:
            vibe = "struggling"

        return VibeSnapshot(
            readings=readings,
            overall_vibe=vibe,
            alert_count=len(self._alerts),
            captured_at=latest,
        )

    def _check_alerts(self, reading: VibeReading) -> None:
        if reading.score >= self.ALERT_HIGH:
            self._alerts.append(f"HIGH {reading.dimension.value}: {reading.score}")
        elif reading.score <= self.ALERT_LOW:
            self._alerts.append(f"LOW {reading.dimension.value}: {reading.score}")

    def get_alerts(self) -> list[str]:
        alerts = list(self._alerts)
        self._alerts.clear()
        return alerts

    def stats(self) -> dict:
        return {
            "total_readings": sum(len(h) for h in self._history.values()),
            "current_alerts": len(self._alerts),
            "dimensions_tracked": len(VibeDimension),
        }
