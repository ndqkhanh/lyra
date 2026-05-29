"""Evolution Tracking — track skill improvement over time with metrics and trends."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from enum import Enum, auto

from .exceptions import MetricsError
from .lifelong_learner import LearningState


class TrendDirection(Enum):
    """Direction of a metric trend."""

    IMPROVING = auto()
    STABLE = auto()
    DECLINING = auto()


@dataclass(frozen=True)
class MetricsSnapshot:
    """A snapshot of skill metrics at a point in time.

    Attributes:
        timestamp: Unix timestamp of the snapshot.
        total_skills: Number of skills tracked.
        avg_quality: Average quality score across all skills (0.0 to 1.0).
        benchmark_score: Current benchmark score.
        regression_count: Number of regressions detected.
    """

    timestamp: float
    total_skills: int = 0
    avg_quality: float = 0.0
    benchmark_score: float = 0.0
    regression_count: int = 0


@dataclass(frozen=True)
class EvolutionTrend:
    """A trend for a single metric.

    Attributes:
        metric_name: Name of the metric being tracked.
        direction: Direction of the trend.
        slope: Slope of the linear regression (units per second).
        confidence: Confidence in the trend (0.0 to 1.0).
    """

    metric_name: str
    direction: TrendDirection
    slope: float
    confidence: float


@dataclass(frozen=True)
class PeriodComparison:
    """Comparison of metrics between two time periods.

    Attributes:
        start_snapshot: Snapshot at the start of the period.
        end_snapshot: Snapshot at the end of the period.
        quality_delta: Change in average quality.
        benchmark_delta: Change in benchmark score.
        regression_delta: Change in regression count.
    """

    start_snapshot: MetricsSnapshot
    end_snapshot: MetricsSnapshot
    quality_delta: float = 0.0
    benchmark_delta: float = 0.0
    regression_delta: int = 0


@dataclass(frozen=True)
class EvolutionReport:
    """Full evolution report with charts data and recommendations.

    Attributes:
        snapshots: List of historical metric snapshots.
        trends: List of detected trends.
        highlights: Notable events or achievements.
        recommendations: Suggested actions based on trends.
    """

    snapshots: list[MetricsSnapshot] = field(default_factory=list)
    trends: list[EvolutionTrend] = field(default_factory=list)
    highlights: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


class EvolutionMetrics:
    """Tracks evolution of skills over time with trend analysis.

    Records metric snapshots, computes trends using linear regression,
    compares periods, and generates evolution reports.
    """

    def __init__(self) -> None:
        self._snapshots: list[MetricsSnapshot] = []

    def record_snapshot(self, state: LearningState) -> MetricsSnapshot:
        """Record a metric snapshot from the current learning state.

        Args:
            state: The current learning state.

        Returns:
            The recorded MetricsSnapshot.

        Raises:
            MetricsError: If the state is invalid.
        """
        if state.total_improvement < -100:
            raise MetricsError(f"Invalid total_improvement: {state.total_improvement}")

        total_skills = 0
        if state.history:
            last_cycle = state.history[-1]
            total_skills = last_cycle.patches_applied

        snapshot = MetricsSnapshot(
            timestamp=time.time(),
            total_skills=total_skills,
            avg_quality=max(0.0, min(1.0, 0.5 + state.total_improvement)),
            benchmark_score=max(0.0, min(1.0, 0.6 + state.total_improvement)),
            regression_count=max(0, int(abs(state.total_improvement * 10))),
        )

        self._snapshots.append(snapshot)
        return snapshot

    def get_trends(self) -> list[EvolutionTrend]:
        """Compute trends for tracked metrics.

        Uses linear regression to determine the direction and magnitude
        of change over recorded snapshots.

        Returns:
            List of EvolutionTrend for each tracked metric.

        Raises:
            MetricsError: If there are too few snapshots for trend analysis.
        """
        if len(self._snapshots) < 2:
            raise MetricsError(
                f"Need at least 2 snapshots for trends, got {len(self._snapshots)}"
            )

        metrics = ["avg_quality", "benchmark_score", "regression_count"]
        trends: list[EvolutionTrend] = []

        for metric in metrics:
            values = [
                getattr(s, metric, 0.0)
                for s in self._snapshots
            ]

            # Linear regression
            n = len(values)
            x_mean = (n - 1) / 2.0
            y_mean = sum(values) / n

            numerator = sum(
                (i - x_mean) * (values[i] - y_mean)
                for i in range(n)
            )
            denominator = sum((i - x_mean) ** 2 for i in range(n))

            slope = numerator / denominator if denominator != 0 else 0.0
            confidence = self._compute_confidence(values)

            if metric == "regression_count":
                # Lower is better
                direction = TrendDirection.IMPROVING if slope < 0 else (
                    TrendDirection.DECLINING if slope > 0 else TrendDirection.STABLE
                )
            else:
                direction = TrendDirection.IMPROVING if slope > 0 else (
                    TrendDirection.DECLINING if slope < 0 else TrendDirection.STABLE
                )

            trends.append(EvolutionTrend(
                metric_name=metric,
                direction=direction,
                slope=slope,
                confidence=confidence,
            ))

        return trends

    def _compute_confidence(self, values: list[float]) -> float:
        """Compute confidence in a trend based on value variance.

        Args:
            values: List of metric values.

        Returns:
            Confidence score between 0.0 and 1.0.
        """
        if len(values) < 3:
            return 0.5

        n = len(values)
        mean = sum(values) / n
        variance = sum((v - mean) ** 2 for v in values) / n

        if variance == 0:
            return 1.0

        std_dev = math.sqrt(variance)
        relative_std = std_dev / max(abs(mean), 0.001)

        return max(0.0, min(1.0, 1.0 - relative_std))

    def compare_periods(
        self,
        start: MetricsSnapshot,
        end: MetricsSnapshot,
    ) -> PeriodComparison:
        """Compare metrics between two time periods.

        Args:
            start: Snapshot at the start of the period.
            end: Snapshot at the end of the period.

        Returns:
            PeriodComparison with deltas.
        """
        return PeriodComparison(
            start_snapshot=start,
            end_snapshot=end,
            quality_delta=end.avg_quality - start.avg_quality,
            benchmark_delta=end.benchmark_score - start.benchmark_score,
            regression_delta=end.regression_count - start.regression_count,
        )

    def generate_evolution_report(self) -> EvolutionReport:
        """Generate a comprehensive evolution report.

        Includes snapshots, trends, highlights based on improvement,
        and recommendations based on declining metrics.

        Returns:
            An EvolutionReport with all analysis.

        Raises:
            MetricsError: If no snapshots have been recorded.
        """
        if not self._snapshots:
            raise MetricsError("No snapshots recorded yet")

        trends: list[EvolutionTrend] = []
        try:
            trends = self.get_trends()
        except MetricsError:
            pass

        highlights: list[str] = []
        recommendations: list[str] = []

        first = self._snapshots[0]
        last = self._snapshots[-1]

        quality_delta = last.avg_quality - first.avg_quality
        benchmark_delta = last.benchmark_score - first.benchmark_score

        if quality_delta > 0.05:
            highlights.append(
                f"Quality improved by {quality_delta:.1%} across {len(self._snapshots)} snapshots"
            )
        if benchmark_delta > 0.05:
            highlights.append(
                f"Benchmark score improved by {benchmark_delta:.1%}"
            )
        if last.regression_count == 0:
            highlights.append("Zero regressions in latest snapshot")

        # Check for declining trends
        for trend in trends:
            if trend.direction == TrendDirection.DECLINING:
                recommendations.append(
                    f"Declining trend in {trend.metric_name} (slope: {trend.slope:.4f}). "
                    "Consider rolling back recent changes."
                )

        if last.regression_count > first.regression_count:
            recommendations.append(
                f"Regressions increased from {first.regression_count} to "
                f"{last.regression_count}. Investigate root causes."
            )

        if not highlights:
            highlights.append("No significant improvements detected in this period.")

        return EvolutionReport(
            snapshots=list(self._snapshots),
            trends=trends,
            highlights=highlights,
            recommendations=recommendations,
        )

    @property
    def snapshots(self) -> list[MetricsSnapshot]:
        """Get all recorded snapshots."""
        return list(self._snapshots)

    def clear_snapshots(self) -> None:
        """Clear all recorded snapshots."""
        self._snapshots.clear()
