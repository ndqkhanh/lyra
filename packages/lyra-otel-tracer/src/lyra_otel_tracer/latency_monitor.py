"""p50/p95/p99 latency tracking for agent operations."""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np

from .exceptions import LatencyMonitorError


@dataclass(frozen=True)
class LatencySample:
    """A single latency measurement."""

    agent_id: str
    operation: str
    duration_ms: float
    timestamp: float


@dataclass(frozen=True)
class LatencyStats:
    """Statistical summary of latency measurements."""

    p50_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    avg_ms: float = 0.0
    min_ms: float = 0.0
    max_ms: float = 0.0
    sample_count: int = 0


@dataclass(frozen=True)
class LatencyAlert:
    """Alert raised when a latency stat exceeds its threshold."""

    alert_type: str
    stat_name: str
    current_value: float
    threshold: float
    timestamp: float


VALID_STATS = frozenset({"p50", "p95", "p99", "avg", "min", "max"})


class LatencyMonitor:
    """Tracks latency statistics with p50/p95/p99 and threshold alerts."""

    def __init__(self) -> None:
        self._samples: list[LatencySample] = []
        self._thresholds: dict[str, float] = {}

    async def record_latency(
        self,
        agent_id: str,
        operation: str,
        duration_ms: float,
    ) -> None:
        """Record a latency sample."""
        sample = LatencySample(
            agent_id=agent_id,
            operation=operation,
            duration_ms=duration_ms,
            timestamp=time.time(),
        )
        self._samples.append(sample)

    async def get_stats(
        self,
        agent_id: str = "",
        operation: str = "",
    ) -> LatencyStats:
        """Get latency statistics, optionally filtered by agent and/or operation."""
        filtered = self._samples

        if agent_id:
            filtered = [s for s in filtered if s.agent_id == agent_id]
        if operation:
            filtered = [s for s in filtered if s.operation == operation]

        if not filtered:
            return LatencyStats()

        durations = np.array([s.duration_ms for s in filtered], dtype=np.float64)

        return LatencyStats(
            p50_ms=float(np.percentile(durations, 50)),
            p95_ms=float(np.percentile(durations, 95)),
            p99_ms=float(np.percentile(durations, 99)),
            avg_ms=float(np.mean(durations)),
            min_ms=float(np.min(durations)),
            max_ms=float(np.max(durations)),
            sample_count=len(filtered),
        )

    async def set_threshold(self, stat: str, value_ms: float) -> None:
        """Set a threshold alert for a given latency stat."""
        if stat not in VALID_STATS:
            raise LatencyMonitorError(
                f"Invalid stat '{stat}'. Valid stats: {sorted(VALID_STATS)}"
            )
        self._thresholds[stat] = value_ms

    async def check_thresholds(self) -> tuple[LatencyAlert, ...]:
        """Check all latency thresholds and return active alerts."""
        if not self._thresholds:
            return ()

        all_stats = await self.get_stats()
        if all_stats.sample_count == 0:
            return ()

        alerts: list[LatencyAlert] = []
        now = time.time()
        stat_map = {
            "p50": all_stats.p50_ms,
            "p95": all_stats.p95_ms,
            "p99": all_stats.p99_ms,
            "avg": all_stats.avg_ms,
            "min": all_stats.min_ms,
            "max": all_stats.max_ms,
        }

        for stat_name, threshold in self._thresholds.items():
            current = stat_map.get(stat_name, 0.0)
            if current > threshold:
                alerts.append(
                    LatencyAlert(
                        alert_type="threshold_exceeded",
                        stat_name=stat_name,
                        current_value=round(current, 2),
                        threshold=threshold,
                        timestamp=now,
                    )
                )

        return tuple(alerts)
