"""Compression Effectiveness Tracker.

Tracks memory compression metrics including:
- Compression ratio (original size / compressed size)
- Consolidation latency
- 30-day knowledge retention rate
- Memory efficiency over time
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class DreamConsolidator(Protocol):
    """Protocol for dream consolidator interface."""

    def run_full_cycle(self, session_traces: list[dict[str, Any]]) -> list[Any]:
        """Run full consolidation cycle."""
        ...


class EternalStore(Protocol):
    """Protocol for eternal store interface."""

    def query_by_age(self, min_age_days: int, max_age_days: int) -> list[Any]:
        """Query records by age."""
        ...

    def count_active_records(self) -> int:
        """Count active records."""
        ...


@dataclass
class CompressionMetrics:
    """Metrics for a single compression operation."""

    original_size_bytes: int
    compressed_size_bytes: int
    compression_ratio: float
    consolidation_latency_ms: float
    fragments_before: int
    fragments_after: int
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "original_size_bytes": self.original_size_bytes,
            "compressed_size_bytes": self.compressed_size_bytes,
            "compression_ratio": self.compression_ratio,
            "consolidation_latency_ms": self.consolidation_latency_ms,
            "fragments_before": self.fragments_before,
            "fragments_after": self.fragments_after,
            "timestamp": self.timestamp,
        }


@dataclass
class RetentionMetrics:
    """30-day knowledge retention metrics."""

    total_memories_30d_ago: int
    retained_memories: int
    retention_rate: float
    avg_access_count: float
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_memories_30d_ago": self.total_memories_30d_ago,
            "retained_memories": self.retained_memories,
            "retention_rate": self.retention_rate,
            "avg_access_count": self.avg_access_count,
            "timestamp": self.timestamp,
        }


@dataclass
class CompressionReport:
    """Comprehensive compression tracking report."""

    avg_compression_ratio: float
    avg_consolidation_latency_ms: float
    total_compressions: int
    total_bytes_saved: int
    retention_rate_30d: float
    compression_history: list[CompressionMetrics] = field(default_factory=list)
    retention_history: list[RetentionMetrics] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON export."""
        return {
            "avg_compression_ratio": self.avg_compression_ratio,
            "avg_consolidation_latency_ms": self.avg_consolidation_latency_ms,
            "total_compressions": self.total_compressions,
            "total_bytes_saved": self.total_bytes_saved,
            "retention_rate_30d": self.retention_rate_30d,
            "compression_history": [m.to_dict() for m in self.compression_history],
            "retention_history": [m.to_dict() for m in self.retention_history],
            "timestamp": self.timestamp,
        }

    def to_json(self, path: Path) -> None:
        """Export report to JSON file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CompressionReport:
        """Create from dictionary."""
        compression_history = [
            CompressionMetrics(**m) for m in data.get("compression_history", [])
        ]
        retention_history = [
            RetentionMetrics(**m) for m in data.get("retention_history", [])
        ]

        return cls(
            avg_compression_ratio=data["avg_compression_ratio"],
            avg_consolidation_latency_ms=data["avg_consolidation_latency_ms"],
            total_compressions=data["total_compressions"],
            total_bytes_saved=data["total_bytes_saved"],
            retention_rate_30d=data["retention_rate_30d"],
            compression_history=compression_history,
            retention_history=retention_history,
            timestamp=data.get("timestamp", time.time()),
        )


class CompressionTracker:
    """Tracks compression effectiveness and memory efficiency."""

    def __init__(
        self,
        dream_consolidator: DreamConsolidator | None = None,
        eternal_store: EternalStore | None = None,
    ):
        """Initialize compression tracker.

        Args:
            dream_consolidator: Optional dream consolidator for tracking
            eternal_store: Optional eternal store for retention tracking
        """
        self.dream_consolidator = dream_consolidator
        self.eternal_store = eternal_store
        self.compression_history: list[CompressionMetrics] = []
        self.retention_history: list[RetentionMetrics] = []

    def track_compression(
        self,
        original_content: list[str],
        compressed_content: list[str],
        latency_ms: float,
    ) -> CompressionMetrics:
        """Track a compression operation.

        Args:
            original_content: Original memory fragments
            compressed_content: Compressed/consolidated fragments
            latency_ms: Time taken for consolidation

        Returns:
            CompressionMetrics for this operation
        """
        # Calculate sizes
        original_size = sum(len(c.encode("utf-8")) for c in original_content)
        compressed_size = sum(len(c.encode("utf-8")) for c in compressed_content)

        # Calculate compression ratio
        compression_ratio = (
            original_size / compressed_size if compressed_size > 0 else 1.0
        )

        metrics = CompressionMetrics(
            original_size_bytes=original_size,
            compressed_size_bytes=compressed_size,
            compression_ratio=compression_ratio,
            consolidation_latency_ms=latency_ms,
            fragments_before=len(original_content),
            fragments_after=len(compressed_content),
        )

        self.compression_history.append(metrics)

        logger.info(
            f"Compression tracked: {compression_ratio:.2f}x ratio, "
            f"{latency_ms:.1f}ms latency"
        )

        return metrics

    def track_consolidation_cycle(
        self, session_traces: list[dict[str, Any]]
    ) -> CompressionMetrics:
        """Track a full dream consolidation cycle.

        Args:
            session_traces: Session traces to consolidate

        Returns:
            CompressionMetrics for this cycle
        """
        if not self.dream_consolidator:
            raise ValueError("Dream consolidator not configured")

        # Extract original content
        original_content = [
            trace.get("content", "") for trace in session_traces if "content" in trace
        ]

        # Run consolidation and measure latency
        start_time = time.time()
        consolidated_fragments = self.dream_consolidator.run_full_cycle(session_traces)
        latency_ms = (time.time() - start_time) * 1000

        # Extract consolidated content
        compressed_content = [
            getattr(frag, "content", "") for frag in consolidated_fragments
        ]

        return self.track_compression(original_content, compressed_content, latency_ms)

    def calculate_retention_rate(self, days: int = 30) -> RetentionMetrics:
        """Calculate knowledge retention rate over specified days.

        Args:
            days: Number of days to look back (default: 30)

        Returns:
            RetentionMetrics for the period
        """
        if not self.eternal_store:
            raise ValueError("Eternal store not configured")

        # Query memories from N days ago
        memories_then = self.eternal_store.query_by_age(
            min_age_days=days, max_age_days=days + 1
        )
        total_then = len(memories_then)

        # Count how many are still active
        retained = sum(
            1
            for mem in memories_then
            if getattr(mem, "status", None) == "active"
        )

        # Calculate retention rate
        retention_rate = retained / total_then if total_then > 0 else 0.0

        # Calculate average access count
        avg_access = (
            sum(getattr(mem, "access_count", 0) for mem in memories_then) / total_then
            if total_then > 0
            else 0.0
        )

        metrics = RetentionMetrics(
            total_memories_30d_ago=total_then,
            retained_memories=retained,
            retention_rate=retention_rate,
            avg_access_count=avg_access,
        )

        self.retention_history.append(metrics)

        logger.info(
            f"Retention rate ({days}d): {retention_rate:.2%} "
            f"({retained}/{total_then} memories)"
        )

        return metrics

    def generate_report(self) -> CompressionReport:
        """Generate comprehensive compression report.

        Returns:
            CompressionReport with all tracked metrics
        """
        if not self.compression_history:
            logger.warning("No compression history available")
            return CompressionReport(
                avg_compression_ratio=1.0,
                avg_consolidation_latency_ms=0.0,
                total_compressions=0,
                total_bytes_saved=0,
                retention_rate_30d=0.0,
            )

        # Calculate averages
        avg_ratio = sum(m.compression_ratio for m in self.compression_history) / len(
            self.compression_history
        )
        avg_latency = sum(
            m.consolidation_latency_ms for m in self.compression_history
        ) / len(self.compression_history)

        # Calculate total bytes saved
        total_saved = sum(
            m.original_size_bytes - m.compressed_size_bytes
            for m in self.compression_history
        )

        # Get latest retention rate
        retention_rate = (
            self.retention_history[-1].retention_rate if self.retention_history else 0.0
        )

        report = CompressionReport(
            avg_compression_ratio=avg_ratio,
            avg_consolidation_latency_ms=avg_latency,
            total_compressions=len(self.compression_history),
            total_bytes_saved=total_saved,
            retention_rate_30d=retention_rate,
            compression_history=self.compression_history.copy(),
            retention_history=self.retention_history.copy(),
        )

        logger.info("Compression report generated:")
        logger.info(f"  Avg compression ratio: {avg_ratio:.2f}x")
        logger.info(f"  Avg consolidation latency: {avg_latency:.1f}ms")
        logger.info(f"  Total compressions: {len(self.compression_history)}")
        logger.info(f"  Total bytes saved: {total_saved:,}")
        logger.info(f"  30-day retention rate: {retention_rate:.2%}")

        return report

    def compare_with_baseline(
        self, baseline_report: CompressionReport, current_report: CompressionReport
    ) -> dict[str, Any]:
        """Compare current compression metrics with baseline.

        Args:
            baseline_report: Previous compression report
            current_report: Current compression report

        Returns:
            Dictionary with comparison metrics
        """
        ratio_change = (
            current_report.avg_compression_ratio - baseline_report.avg_compression_ratio
        )
        latency_change = (
            current_report.avg_consolidation_latency_ms
            - baseline_report.avg_consolidation_latency_ms
        )
        retention_change = (
            current_report.retention_rate_30d - baseline_report.retention_rate_30d
        )

        # Detect regressions (worse compression, slower, lower retention)
        ratio_regression = ratio_change < -0.1  # 10% worse compression
        latency_regression = latency_change > 100  # 100ms slower
        retention_regression = retention_change < -0.05  # 5% lower retention

        comparison = {
            "baseline_timestamp": baseline_report.timestamp,
            "current_timestamp": current_report.timestamp,
            "regression_detected": any(
                [ratio_regression, latency_regression, retention_regression]
            ),
            "metrics": {
                "compression_ratio": {
                    "baseline": baseline_report.avg_compression_ratio,
                    "current": current_report.avg_compression_ratio,
                    "change": ratio_change,
                    "regression": ratio_regression,
                },
                "consolidation_latency_ms": {
                    "baseline": baseline_report.avg_consolidation_latency_ms,
                    "current": current_report.avg_consolidation_latency_ms,
                    "change": latency_change,
                    "regression": latency_regression,
                },
                "retention_rate_30d": {
                    "baseline": baseline_report.retention_rate_30d,
                    "current": current_report.retention_rate_30d,
                    "change": retention_change,
                    "regression": retention_regression,
                },
                "total_bytes_saved": {
                    "baseline": baseline_report.total_bytes_saved,
                    "current": current_report.total_bytes_saved,
                    "change": current_report.total_bytes_saved
                    - baseline_report.total_bytes_saved,
                },
            },
        }

        if comparison["regression_detected"]:
            logger.warning("⚠️  Compression performance regression detected!")
            for metric, data in comparison["metrics"].items():
                if data.get("regression"):
                    logger.warning(
                        f"  {metric}: {data['baseline']:.3f} → {data['current']:.3f} "
                        f"(change: {data['change']:.3f})"
                    )

        return comparison

    def clear_history(self) -> None:
        """Clear all tracking history."""
        self.compression_history.clear()
        self.retention_history.clear()
        logger.info("Compression tracking history cleared")
