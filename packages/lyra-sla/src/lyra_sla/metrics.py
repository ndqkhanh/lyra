"""SLA metrics collection: real-time collection, rolling window aggregation, percentile computation, Prometheus-compatible export."""

from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .sla_manager import SLAManager

logger = logging.getLogger(__name__)


# ── Data structures ────────────────────────────────────────────────────


@dataclass
class MetricSnapshot:
    """Snapshot of a single metric at a point in time.

    Attributes:
        metric: Metric name.
        value: Current value.
        timestamp: Unix timestamp.
        labels: Optional labels for multi-dimensional metrics.
    """

    metric: str
    value: float
    timestamp: float = field(default_factory=time.time)
    labels: dict[str, str] = field(default_factory=dict)


@dataclass
class RollingStats:
    """Rolling window statistics for a metric.

    Attributes:
        count: Number of observations.
        mean: Running mean.
        variance: Running variance (Welford's algorithm).
        min_val: Minimum observed.
        max_val: Maximum observed.
        p50: 50th percentile.
        p95: 95th percentile.
        p99: 99th percentile.
    """

    count: int = 0
    mean: float = 0.0
    variance: float = 0.0
    min_val: float = float("inf")
    max_val: float = float("-inf")
    p50: float = 0.0
    p95: float = 0.0
    p99: float = 0.0


# ── Metric collector ───────────────────────────────────────────────────


class MetricsCollector:
    """Real-time metric collection with rolling window aggregation.

    Supports common SLA metric types, percentile computation,
    and export to Prometheus-compatible format.
    """

    def __init__(
        self,
        sla_manager: SLAManager | None = None,
        default_window_seconds: float = 300.0,
        max_history: int = 100_000,
    ) -> None:
        self.sla_manager = sla_manager
        self.default_window_seconds = default_window_seconds
        self.max_history = max_history

        # Metric storage: agent_id -> metric_name -> deque of (timestamp, value)
        self._metrics: dict[str, dict[str, deque[tuple[float, float]]]] = defaultdict(
            lambda: defaultdict(lambda: deque(maxlen=max_history))
        )

        # Aggregated stats cache
        self._stats_cache: dict[str, dict[str, RollingStats]] = {}
        self._last_stats_compute: float = 0.0
        self._stats_cache_ttl: float = 5.0  # seconds

    def observe(
        self,
        agent_id: str,
        metric: str,
        value: float,
        labels: dict[str, str] | None = None,
        timestamp: float | None = None,
    ) -> None:
        """Record a metric observation.

        Args:
            agent_id: Agent or service identifier.
            metric: Metric name.
            value: Observed value.
            labels: Optional metric labels.
            timestamp: Optional timestamp (defaults to now).
        """
        ts = timestamp or time.time()
        key = self._make_key(agent_id, metric, labels)
        self._metrics[agent_id][key].append((ts, value))

        # Forward to SLA manager if available
        if self.sla_manager:
            self.sla_manager.record_metric(agent_id, metric, value, ts)

    def observe_batch(
        self,
        agent_id: str,
        observations: dict[str, float],
        labels: dict[str, str] | None = None,
        timestamp: float | None = None,
    ) -> None:
        """Record multiple metric observations at once."""
        ts = timestamp or time.time()
        for metric, value in observations.items():
            self.observe(agent_id, metric, value, labels, ts)

    @staticmethod
    def _make_key(
        agent_id: str,
        metric: str,
        labels: dict[str, str] | None = None,
    ) -> str:
        """Create a storage key from agent, metric, and labels."""
        if labels:
            label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
            return f"{metric}{{{label_str}}}"
        return metric

    def query(
        self,
        agent_id: str,
        metric: str,
        window_seconds: float | None = None,
        labels: dict[str, str] | None = None,
    ) -> list[float]:
        """Query metric values within a time window.

        Args:
            agent_id: Agent identifier.
            metric: Metric name (or key with labels).
            window_seconds: Optional time window (default window if None).
            labels: Optional metric labels.

        Returns:
            List of metric values in the window.
        """
        key = self._make_key(agent_id, metric, labels)
        obs = self._metrics.get(agent_id, {}).get(key, deque())

        if window_seconds is None:
            window_seconds = self.default_window_seconds

        if window_seconds:
            cutoff = time.time() - window_seconds
            return [v for ts, v in obs if ts >= cutoff]

        return [v for _, v in obs]

    def query_timeseries(
        self,
        agent_id: str,
        metric: str,
        window_seconds: float | None = None,
        labels: dict[str, str] | None = None,
    ) -> list[tuple[float, float]]:
        """Query metric as a timeseries (timestamp, value).

        Args:
            agent_id: Agent identifier.
            metric: Metric name.
            window_seconds: Optional time window.
            labels: Optional metric labels.

        Returns:
            List of (timestamp, value) tuples.
        """
        key = self._make_key(agent_id, metric, labels)
        obs = self._metrics.get(agent_id, {}).get(key, deque())

        if window_seconds:
            cutoff = time.time() - window_seconds
            return [(ts, v) for ts, v in obs if ts >= cutoff]

        return list(obs)

    # ── Statistics computation ─────────────────────────────────────────

    def compute_stats(
        self,
        agent_id: str,
        metric: str,
        window_seconds: float | None = None,
        labels: dict[str, str] | None = None,
    ) -> RollingStats:
        """Compute rolling statistics for a metric.

        Args:
            agent_id: Agent identifier.
            metric: Metric name.
            window_seconds: Optional time window.
            labels: Optional metric labels.

        Returns:
            RollingStats with summary statistics.
        """
        values = self.query(agent_id, metric, window_seconds, labels)
        return self._compute_stats_from_values(values)

    @staticmethod
    def _compute_stats_from_values(values: list[float]) -> RollingStats:
        """Compute RollingStats from a list of values."""
        if not values:
            return RollingStats()

        arr = np.array(values, dtype=np.float64)
        sorted_arr = np.sort(arr)

        return RollingStats(
            count=len(arr),
            mean=float(np.mean(arr)),
            variance=float(np.var(arr)),
            min_val=float(np.min(arr)),
            max_val=float(np.max(arr)),
            p50=float(np.percentile(sorted_arr, 50)),
            p95=float(np.percentile(sorted_arr, 95)),
            p99=float(np.percentile(sorted_arr, 99)),
        )

    def get_all_stats(
        self,
        agent_id: str,
        window_seconds: float | None = None,
    ) -> dict[str, RollingStats]:
        """Get statistics for all metrics of an agent.

        Args:
            agent_id: Agent identifier.
            window_seconds: Optional time window.

        Returns:
            Dict of metric_name -> RollingStats.
        """
        now = time.time()
        if (
            agent_id in self._stats_cache
            and now - self._last_stats_compute < self._stats_cache_ttl
        ):
            return self._stats_cache[agent_id]

        stats: dict[str, RollingStats] = {}
        for key in self._metrics.get(agent_id, {}):
            values = self.query(agent_id, key, window_seconds)
            stats[key] = self._compute_stats_from_values(values)

        self._stats_cache[agent_id] = stats
        self._last_stats_compute = now
        return stats

    # ── Percentile computation ─────────────────────────────────────────

    def percentile(
        self,
        agent_id: str,
        metric: str,
        percentile: float,
        window_seconds: float | None = None,
        labels: dict[str, str] | None = None,
    ) -> float:
        """Compute a specific percentile for a metric.

        Args:
            agent_id: Agent identifier.
            metric: Metric name.
            percentile: Percentile to compute (0-100).
            window_seconds: Optional time window.
            labels: Optional labels.

        Returns:
            The percentile value.
        """
        values = self.query(agent_id, metric, window_seconds, labels)
        if not values:
            return 0.0
        return float(np.percentile(np.array(values, dtype=np.float64), percentile))

    # ── Rate computation ───────────────────────────────────────────────

    def rate(
        self,
        agent_id: str,
        metric: str,
        window_seconds: float | None = None,
        labels: dict[str, str] | None = None,
    ) -> float:
        """Compute the rate (per second) of a cumulative counter metric.

        Args:
            agent_id: Agent identifier.
            metric: Metric name.
            window_seconds: Time window.
            labels: Optional labels.

        Returns:
            Rate per second.
        """
        timeseries = self.query_timeseries(agent_id, metric, window_seconds, labels)
        if len(timeseries) < 2:
            return 0.0

        timeseries.sort(key=lambda x: x[0])
        first_ts, first_val = timeseries[0]
        last_ts, last_val = timeseries[-1]

        duration = last_ts - first_ts
        if duration <= 0:
            return 0.0

        return (last_val - first_val) / duration

    def increase(
        self,
        agent_id: str,
        metric: str,
        window_seconds: float | None = None,
        labels: dict[str, str] | None = None,
    ) -> float:
        """Compute the total increase of a counter metric in the window.

        Args:
            agent_id: Agent identifier.
            metric: Metric name.
            window_seconds: Time window.
            labels: Optional labels.

        Returns:
            Total increase.
        """
        timeseries = self.query_timeseries(agent_id, metric, window_seconds, labels)
        if len(timeseries) < 2:
            return 0.0

        timeseries.sort(key=lambda x: x[0])
        return timeseries[-1][1] - timeseries[0][1]

    # ── Prometheus-compatible export ───────────────────────────────────

    def export_prometheus(self) -> str:
        """Export all metrics in Prometheus text format.

        Returns:
            Prometheus exposition format string.
        """
        lines: list[str] = []
        time.time()

        for agent_id, agent_metrics in self._metrics.items():
            for metric_key, observations in agent_metrics.items():
                stats = self.compute_stats(agent_id, metric_key)

                # Base metric name (strip label suffix for Prometheus)
                if "{" in metric_key:
                    base_name = metric_key[: metric_key.index("{")]
                    label_part = metric_key[metric_key.index("{") :]
                else:
                    base_name = metric_key
                    label_part = ""

                # Add agent_id label
                if label_part:
                    label_part = label_part.rstrip("}") + f',agent_id="{agent_id}"}}'
                else:
                    label_part = f'{{agent_id="{agent_id}"}}'

                metric_prefix = f"lyra_{base_name}"

                # HELP and TYPE lines
                lines.append(f"# HELP {metric_prefix} Lyra SLA metric: {base_name}")
                lines.append(f"# TYPE {metric_prefix} gauge")

                # Metric values
                lines.append(f"{metric_prefix}_count{label_part} {stats.count}")
                lines.append(f"{metric_prefix}_mean{label_part} {stats.mean:.6f}")
                lines.append(f"{metric_prefix}_p50{label_part} {stats.p50:.6f}")
                lines.append(f"{metric_prefix}_p95{label_part} {stats.p95:.6f}")
                lines.append(f"{metric_prefix}_p99{label_part} {stats.p99:.6f}")
                lines.append(f"{metric_prefix}_min{label_part} {stats.min_val:.6f}")
                lines.append(f"{metric_prefix}_max{label_part} {stats.max_val:.6f}")

                if observations:
                    lines.append(f"{metric_prefix}_latest{label_part} {observations[-1][1]:.6f}")

        lines.append("# EOF")
        return "\n".join(lines) + "\n"

    def export_json(self, agent_id: str | None = None) -> dict[str, Any]:
        """Export metrics as JSON-serializable dict.

        Args:
            agent_id: Optional agent filter.

        Returns:
            Dict with metrics data.
        """
        result: dict[str, Any] = {
            "timestamp": time.time(),
            "agents": {},
        }

        agents_to_export = [agent_id] if agent_id else list(self._metrics.keys())
        for aid in agents_to_export:
            if aid not in self._metrics:
                continue
            result["agents"][aid] = {}
            all_stats = self.get_all_stats(aid)
            for key, stats in all_stats.items():
                result["agents"][aid][key] = {
                    "count": stats.count,
                    "mean": stats.mean,
                    "variance": stats.variance,
                    "min": stats.min_val,
                    "max": stats.max_val,
                    "p50": stats.p50,
                    "p95": stats.p95,
                    "p99": stats.p99,
                }

        return result

    # ── Utility ────────────────────────────────────────────────────────

    def clear_agent(self, agent_id: str) -> None:
        """Clear all metrics for an agent."""
        self._metrics.pop(agent_id, None)
        self._stats_cache.pop(agent_id, None)

    def clear_all(self) -> None:
        """Clear all collected metrics."""
        self._metrics.clear()
        self._stats_cache.clear()

    @property
    def agent_count(self) -> int:
        """Number of agents being tracked."""
        return len(self._metrics)

    @property
    def total_observations(self) -> int:
        """Total number of metric observations across all agents."""
        return sum(
            len(obs) for agent_metrics in self._metrics.values()
            for obs in agent_metrics.values()
        )

    @property
    def summary(self) -> dict[str, Any]:
        """Get collector summary."""
        agent_stats = {}
        for aid in self._metrics:
            all_stats = self.get_all_stats(aid)
            agent_stats[aid] = {
                "metric_count": len(all_stats),
                "total_observations": sum(s.count for s in all_stats.values()),
            }

        return {
            "agents_tracked": self.agent_count,
            "total_observations": self.total_observations,
            "agent_stats": agent_stats,
        }
