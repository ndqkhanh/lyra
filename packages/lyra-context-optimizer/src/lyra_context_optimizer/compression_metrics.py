"""Track and analyze compression effectiveness across strategies and tasks."""

from __future__ import annotations

import statistics
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MetricsSnapshot:
    """A single compression event snapshot.

    Attributes:
        strategy: Which compression strategy was used.
        task_type: Type of task being compressed.
        tokens_before: Token count before compression.
        tokens_after: Token count after compression.
        compression_ratio: Ratio (0.0 = no compression, 1.0 = full compression).
        fidelity_score: Fidelity score (0.0 to 1.0).
        time_taken_ms: Milliseconds taken for compression.
        accuracy_impact: Change in accuracy (positive = improvement).
        timestamp: Unix timestamp of the event.
    """

    strategy: str
    task_type: str
    tokens_before: int
    tokens_after: int
    compression_ratio: float
    fidelity_score: float
    time_taken_ms: float
    accuracy_impact: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class StrategyStats:
    """Aggregated statistics for a compression strategy.

    Attributes:
        strategy: Strategy name.
        count: Number of events.
        avg_compression_ratio: Average compression ratio.
        avg_fidelity_score: Average fidelity score.
        avg_time_taken_ms: Average time in milliseconds.
        total_tokens_saved: Total tokens saved.
        min_compression_ratio: Minimum compression ratio.
        max_compression_ratio: Maximum compression ratio.
    """

    strategy: str
    count: int
    avg_compression_ratio: float
    avg_fidelity_score: float
    avg_time_taken_ms: float
    total_tokens_saved: int
    min_compression_ratio: float
    max_compression_ratio: float


@dataclass(frozen=True)
class MetricsReport:
    """Full metrics report.

    Attributes:
        total_events: Total compression events recorded.
        total_tokens_saved: Total tokens saved across all events.
        overall_avg_ratio: Average compression ratio across all events.
        overall_avg_fidelity: Average fidelity score across all events.
        strategy_stats: Per-strategy statistics.
        task_type_stats: Per-task-type statistics.
        optimization_suggestions: Suggested improvements.
    """

    total_events: int
    total_tokens_saved: int
    overall_avg_ratio: float
    overall_avg_fidelity: float
    strategy_stats: list[StrategyStats]
    task_type_stats: dict[str, dict[str, float]]
    optimization_suggestions: list[str]


class CompressionMetrics:
    """Tracks compression effectiveness, aggregates stats, and generates
    optimization suggestions.

    Collects per-event metrics, maintains strategy-level and task-type-level
    aggregations, and provides optimization recommendations based on
    historical data.
    """

    def __init__(self) -> None:
        self._snapshots: list[MetricsSnapshot] = []
        self._by_strategy: dict[str, list[MetricsSnapshot]] = defaultdict(list)
        self._by_task_type: dict[str, list[MetricsSnapshot]] = defaultdict(list)

    def record(
        self,
        strategy: str,
        task_type: str,
        tokens_before: int,
        tokens_after: int,
        time_taken_ms: float,
        fidelity_score: float = 1.0,
        accuracy_impact: float = 0.0,
    ) -> MetricsSnapshot:
        """Record a compression event.

        Args:
            strategy: Strategy name.
            task_type: Task type name.
            tokens_before: Tokens before compression.
            tokens_after: Tokens after compression.
            time_taken_ms: Time taken in milliseconds.
            fidelity_score: Fidelity score (0.0 to 1.0).
            accuracy_impact: Accuracy impact.

        Returns:
            The metrics snapshot.
        """
        tokens_before = max(1, tokens_before)
        tokens_after = min(tokens_before, max(0, tokens_after))
        compression_ratio = 1.0 - (tokens_after / tokens_before)
        fidelity_score = max(0.0, min(1.0, fidelity_score))

        snapshot = MetricsSnapshot(
            strategy=strategy,
            task_type=task_type,
            tokens_before=tokens_before,
            tokens_after=tokens_after,
            compression_ratio=compression_ratio,
            fidelity_score=fidelity_score,
            time_taken_ms=time_taken_ms,
            accuracy_impact=accuracy_impact,
        )
        self._snapshots.append(snapshot)
        self._by_strategy[strategy].append(snapshot)
        self._by_task_type[task_type].append(snapshot)
        return snapshot

    def get_snapshots(
        self,
        strategy: str | None = None,
        task_type: str | None = None,
        limit: int = 100,
    ) -> list[MetricsSnapshot]:
        """Get snapshots, optionally filtered.

        Args:
            strategy: Optional strategy filter.
            task_type: Optional task type filter.
            limit: Max number of snapshots.

        Returns:
            List of snapshots, most recent first.
        """
        snapshots = list(self._snapshots)
        if strategy:
            snapshots = [s for s in snapshots if s.strategy == strategy]
        if task_type:
            snapshots = [s for s in snapshots if s.task_type == task_type]
        return sorted(snapshots, key=lambda s: s.timestamp, reverse=True)[:limit]

    def get_strategy_stats(self, strategy: str) -> StrategyStats | None:
        """Get aggregated stats for a strategy.

        Args:
            strategy: Strategy name.

        Returns:
            StrategyStats or None if no data.
        """
        snapshots = self._by_strategy.get(strategy, [])
        if not snapshots:
            return None
        ratios = [s.compression_ratio for s in snapshots]
        return StrategyStats(
            strategy=strategy,
            count=len(snapshots),
            avg_compression_ratio=statistics.mean(ratios),
            avg_fidelity_score=statistics.mean([s.fidelity_score for s in snapshots]),
            avg_time_taken_ms=statistics.mean([s.time_taken_ms for s in snapshots]),
            total_tokens_saved=sum(
                s.tokens_before - s.tokens_after for s in snapshots
            ),
            min_compression_ratio=min(ratios),
            max_compression_ratio=max(ratios),
        )

    def get_task_type_summary(self, task_type: str) -> dict[str, float] | None:
        """Get summary stats for a task type.

        Args:
            task_type: Task type name.

        Returns:
            Dict with avg_ratio, avg_fidelity, avg_time_ms, total_saved or None.
        """
        snapshots = self._by_task_type.get(task_type, [])
        if not snapshots:
            return None
        return {
            "avg_compression_ratio": statistics.mean(
                [s.compression_ratio for s in snapshots]
            ),
            "avg_fidelity_score": statistics.mean(
                [s.fidelity_score for s in snapshots]
            ),
            "avg_time_ms": statistics.mean([s.time_taken_ms for s in snapshots]),
            "total_tokens_saved": sum(
                s.tokens_before - s.tokens_after for s in snapshots
            ),
            "event_count": len(snapshots),
        }

    def get_optimization_suggestions(self) -> list[str]:
        """Generate optimization suggestions based on historical data.

        Analyzes past compression events to identify underperforming strategies,
        high-variance approaches, and opportunities for improvement.

        Returns:
            List of suggestion strings.
        """
        suggestions: list[str] = []
        if not self._snapshots:
            return suggestions

        for strategy in self._by_strategy:
            stats = self.get_strategy_stats(strategy)
            if stats is None or stats.count < 2:
                continue
            if stats.avg_fidelity_score < 0.8:
                suggestions.append(
                    f"Strategy '{strategy}' has low fidelity "
                    f"({stats.avg_fidelity_score:.2f}). "
                    "Consider raising min_fidelity_threshold."
                )
            if stats.avg_compression_ratio < 0.2:
                suggestions.append(
                    f"Strategy '{strategy}' has low compression ratio "
                    f"({stats.avg_compression_ratio:.2f}). "
                    "Switch to a more aggressive strategy."
                )
            if stats.avg_time_taken_ms > 1000:
                suggestions.append(
                    f"Strategy '{strategy}' is slow "
                    f"({stats.avg_time_taken_ms:.0f}ms avg). "
                    "Consider using async or simpler approach."
                )

        all_ratios = [s.compression_ratio for s in self._snapshots]
        if len(all_ratios) > 2 and statistics.stdev(all_ratios) > 0.3:
            suggestions.append(
                "High variance in compression ratios "
                f"(std={statistics.stdev(all_ratios):.2f}). "
                "Consider strategy selection based on content type."
            )

        return suggestions

    def generate_report(self) -> MetricsReport:
        """Generate a full metrics report.

        Returns:
            MetricsReport with all aggregated data.
        """
        total_saved = sum(
            s.tokens_before - s.tokens_after for s in self._snapshots
        )
        overall_ratio = (
            statistics.mean([s.compression_ratio for s in self._snapshots])
            if self._snapshots
            else 0.0
        )
        overall_fidelity = (
            statistics.mean([s.fidelity_score for s in self._snapshots])
            if self._snapshots
            else 1.0
        )

        strategy_stats = [
            s
            for strategy in self._by_strategy
            if (s := self.get_strategy_stats(strategy)) is not None
        ]

        task_type_stats = {
            tt: summary
            for tt in self._by_task_type
            if (summary := self.get_task_type_summary(tt)) is not None
        }

        return MetricsReport(
            total_events=len(self._snapshots),
            total_tokens_saved=total_saved,
            overall_avg_ratio=overall_ratio,
            overall_avg_fidelity=overall_fidelity,
            strategy_stats=strategy_stats,
            task_type_stats=task_type_stats,
            optimization_suggestions=self.get_optimization_suggestions(),
        )

    def export_json(self) -> dict[str, Any]:
        """Export metrics as a JSON-serializable dict."""
        return {
            "total_events": len(self._snapshots),
            "recent_snapshots": [
                {
                    "strategy": s.strategy,
                    "task_type": s.task_type,
                    "tokens_before": s.tokens_before,
                    "tokens_after": s.tokens_after,
                    "compression_ratio": s.compression_ratio,
                    "fidelity_score": s.fidelity_score,
                }
                for s in self._snapshots[-50:]
            ],
            "suggestions": self.get_optimization_suggestions(),
        }
