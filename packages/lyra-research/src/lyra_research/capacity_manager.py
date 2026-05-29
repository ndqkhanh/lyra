"""
Memory Capacity Management for Lyra Deep Research.

Implements capacity limits, compaction strategies, query latency monitoring,
and automated alerts for memory system health.
"""
from __future__ import annotations

import gzip
import json
import shutil
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------------------
# Capacity Limits
# ---------------------------------------------------------------------------


class CapacityLimits:
    """Hard limits for memory system capacity."""

    MAX_SOURCES = 10_000
    MAX_NOTES = 100_000
    MAX_SESSIONS = 1_000
    ALERT_THRESHOLD = 0.8  # Alert at 80% capacity
    BLOCK_THRESHOLD = 1.0  # Block writes at 100%


# ---------------------------------------------------------------------------
# Query SLOs
# ---------------------------------------------------------------------------


class QuerySLOs:
    """Service Level Objectives for query latency (p95 in milliseconds)."""

    FTS5_SEARCH_MS = 100  # Full-text search
    EMBEDDING_SEARCH_MS = 200  # Vector similarity search
    RERANKING_MS = 500  # Reranking with cross-encoder


# ---------------------------------------------------------------------------
# Capacity Status
# ---------------------------------------------------------------------------


class CapacityLevel(Enum):
    """Current capacity utilization level."""

    HEALTHY = "healthy"  # < 80%
    WARNING = "warning"  # 80-99%
    CRITICAL = "critical"  # >= 100%


@dataclass
class CapacityStatus:
    """Current capacity status across all dimensions."""

    sources_count: int
    sources_limit: int
    notes_count: int
    notes_limit: int
    sessions_count: int
    sessions_limit: int
    db_size_mb: float
    level: CapacityLevel
    blocked: bool = False
    warnings: list[str] = field(default_factory=list)

    @property
    def sources_utilization(self) -> float:
        """Calculate sources utilization (0.0-1.0)."""
        return self.sources_count / self.sources_limit if self.sources_limit > 0 else 0.0

    @property
    def notes_utilization(self) -> float:
        """Calculate notes utilization (0.0-1.0)."""
        return self.notes_count / self.notes_limit if self.notes_limit > 0 else 0.0

    @property
    def sessions_utilization(self) -> float:
        """Calculate sessions utilization (0.0-1.0)."""
        return self.sessions_count / self.sessions_limit if self.sessions_limit > 0 else 0.0

    @property
    def max_utilization(self) -> float:
        """Get maximum utilization across all dimensions."""
        return max(
            self.sources_utilization,
            self.notes_utilization,
            self.sessions_utilization,
        )


# ---------------------------------------------------------------------------
# Compaction Result
# ---------------------------------------------------------------------------


@dataclass
class CompactionResult:
    """Result of a compaction operation."""

    archived_notes: int = 0
    deduplicated_embeddings: int = 0
    compressed_sessions: int = 0
    db_size_before_mb: float = 0.0
    db_size_after_mb: float = 0.0
    duration_seconds: float = 0.0

    @property
    def size_reduction_mb(self) -> float:
        """Calculate size reduction in MB."""
        return self.db_size_before_mb - self.db_size_after_mb

    @property
    def size_reduction_percent(self) -> float:
        """Calculate size reduction percentage."""
        if self.db_size_before_mb == 0:
            return 0.0
        return (self.size_reduction_mb / self.db_size_before_mb) * 100


# ---------------------------------------------------------------------------
# Query Latency Tracking
# ---------------------------------------------------------------------------


@dataclass
class LatencyStats:
    """Latency statistics for a query type."""

    query_type: str
    samples: list[float] = field(default_factory=list)
    max_samples: int = 1000  # Keep last 1000 samples

    def record(self, latency_ms: float) -> None:
        """Record a latency sample."""
        self.samples.append(latency_ms)
        if len(self.samples) > self.max_samples:
            self.samples.pop(0)

    def p50(self) -> float:
        """Calculate p50 (median) latency."""
        if not self.samples:
            return 0.0
        return float(np.percentile(self.samples, 50))

    def p95(self) -> float:
        """Calculate p95 latency."""
        if not self.samples:
            return 0.0
        return float(np.percentile(self.samples, 95))

    def p99(self) -> float:
        """Calculate p99 latency."""
        if not self.samples:
            return 0.0
        return float(np.percentile(self.samples, 99))

    def mean(self) -> float:
        """Calculate mean latency."""
        if not self.samples:
            return 0.0
        return float(np.mean(self.samples))

    def count(self) -> int:
        """Get sample count."""
        return len(self.samples)


# Capacity Report
# ---------------------------------------------------------------------------


@dataclass
class CapacityReport:
    """Comprehensive capacity and performance report."""

    status: CapacityStatus
    latency_stats: dict[str, LatencyStats]
    slo_violations: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "capacity": {
                "sources": {
                    "count": self.status.sources_count,
                    "limit": self.status.sources_limit,
                    "utilization": f"{self.status.sources_utilization:.1%}",
                },
                "notes": {
                    "count": self.status.notes_count,
                    "limit": self.status.notes_limit,
                    "utilization": f"{self.status.notes_utilization:.1%}",
                },
                "sessions": {
                    "count": self.status.sessions_count,
                    "limit": self.status.sessions_limit,
                    "utilization": f"{self.status.sessions_utilization:.1%}",
                },
                "db_size_mb": self.status.db_size_mb,
                "level": self.status.level.value,
                "blocked": self.status.blocked,
                "warnings": self.status.warnings,
            },
            "latency": {
                query_type: {
                    "p50": stats.p50(),
                    "p95": stats.p95(),
                    "p99": stats.p99(),
                    "mean": stats.mean(),
                    "count": stats.count(),
                }
                for query_type, stats in self.latency_stats.items()
            },
            "slo_violations": self.slo_violations,
        }


# ---------------------------------------------------------------------------
# Capacity Manager
# ---------------------------------------------------------------------------


class CapacityManager:
    """
    Manages memory system capacity, compaction, and monitoring.

    Responsibilities:
    - Enforce capacity limits (alert at 80%, block at 100%)
    - Compact old data (archive, deduplicate, vacuum)
    - Monitor query latency and detect SLO violations
    - Generate capacity reports and alerts
    """

    def __init__(
        self,
        db_path: Path,
        cold_storage_path: Path | None = None,
        limits: CapacityLimits | None = None,
        slos: QuerySLOs | None = None,
    ):
        """
        Initialize capacity manager.

        Args:
            db_path: Path to main SQLite database
            cold_storage_path: Path to cold storage directory (default: db_path.parent / "cold_storage")
            limits: Custom capacity limits (default: CapacityLimits)
            slos: Custom query SLOs (default: QuerySLOs)
        """
        self.db_path = db_path
        self.cold_storage_path = cold_storage_path or (db_path.parent / "cold_storage")
        self.cold_storage_path.mkdir(parents=True, exist_ok=True)

        self.limits = limits or CapacityLimits()
        self.slos = slos or QuerySLOs()

        # Latency tracking
        self.latency_stats: dict[str, LatencyStats] = {
            "fts5_search": LatencyStats("fts5_search"),
            "embedding_search": LatencyStats("embedding_search"),
            "reranking": LatencyStats("reranking"),
        }

    def check_capacity(self) -> CapacityStatus:
        """
        Check current capacity status.

        Returns:
            CapacityStatus with current utilization and warnings.
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Count sources (assuming a sources table exists)
        try:
            cursor.execute("SELECT COUNT(*) FROM sources")
            sources_count = cursor.fetchone()[0]
        except sqlite3.OperationalError:
            sources_count = 0

        # Count notes (memories table)
        try:
            cursor.execute("SELECT COUNT(*) FROM memories")
            notes_count = cursor.fetchone()[0]
        except sqlite3.OperationalError:
            notes_count = 0

        # Count sessions (assuming a sessions table exists)
        try:
            cursor.execute("SELECT COUNT(DISTINCT metadata->>'session_id') FROM memories WHERE metadata IS NOT NULL")
            sessions_count = cursor.fetchone()[0] or 0
        except (sqlite3.OperationalError, TypeError):
            sessions_count = 0

        conn.close()

        # Get database size
        db_size_mb = self.db_path.stat().st_size / (1024 * 1024) if self.db_path.exists() else 0.0

        # Calculate utilization
        status = CapacityStatus(
            sources_count=sources_count,
            sources_limit=self.limits.MAX_SOURCES,
            notes_count=notes_count,
            notes_limit=self.limits.MAX_NOTES,
            sessions_count=sessions_count,
            sessions_limit=self.limits.MAX_SESSIONS,
            db_size_mb=db_size_mb,
            level=CapacityLevel.HEALTHY,
        )

        max_util = status.max_utilization

        # Determine level and warnings
        if max_util >= self.limits.BLOCK_THRESHOLD:
            status.level = CapacityLevel.CRITICAL
            status.blocked = True
            status.warnings.append(f"CRITICAL: Capacity at {max_util:.1%} - writes blocked")
        elif max_util >= self.limits.ALERT_THRESHOLD:
            status.level = CapacityLevel.WARNING
            status.warnings.append(f"WARNING: Capacity at {max_util:.1%} - consider compaction")

        # Specific warnings
        if status.sources_utilization >= self.limits.ALERT_THRESHOLD:
            status.warnings.append(
                f"Sources: {status.sources_count}/{status.sources_limit} ({status.sources_utilization:.1%})"
            )
        if status.notes_utilization >= self.limits.ALERT_THRESHOLD:
            status.warnings.append(
                f"Notes: {status.notes_count}/{status.notes_limit} ({status.notes_utilization:.1%})"
            )
        if status.sessions_utilization >= self.limits.ALERT_THRESHOLD:
            status.warnings.append(
                f"Sessions: {status.sessions_count}/{status.sessions_limit} ({status.sessions_utilization:.1%})"
            )

        return status

    def enforce_limits(self) -> None:
        """
        Enforce capacity limits by blocking writes if at 100%.

        Raises:
            RuntimeError: If capacity is at 100% and writes should be blocked.
        """
        status = self.check_capacity()
        if status.blocked:
            raise RuntimeError(
                f"Capacity limit reached: {status.max_utilization:.1%} utilization. "
                f"Run compaction to free space."
            )

    def compact(self, age_days: int = 90) -> CompactionResult:
        """
        Compact the database by archiving old data and deduplicating.

        Strategy:
        1. Archive notes older than age_days to cold storage
        2. Deduplicate embeddings with cosine similarity > 0.95
        3. Vacuum SQLite database
        4. Compress archived sessions

        Args:
            age_days: Archive notes older than this many days (default: 90)

        Returns:
            CompactionResult with statistics.
        """
        start_time = time.time()
        result = CompactionResult()

        # Get initial size
        result.db_size_before_mb = self.db_path.stat().st_size / (1024 * 1024)

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # 1. Archive old notes
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=age_days)).isoformat()

        try:
            # Get old notes
            cursor.execute(
                "SELECT * FROM memories WHERE created_at < ?",
                (cutoff_date,)
            )
            old_notes = cursor.fetchall()
            result.archived_notes = len(old_notes)

            if old_notes:
                # Save to cold storage
                archive_file = self.cold_storage_path / f"archive_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json.gz"
                with gzip.open(archive_file, "wt", encoding="utf-8") as f:
                    # Get column names
                    cursor.execute("PRAGMA table_info(memories)")
                    columns = [col[1] for col in cursor.fetchall()]

                    # Convert rows to dicts
                    archived_data = [dict(zip(columns, row)) for row in old_notes]
                    json.dump(archived_data, f, indent=2)

                # Delete from main database
                cursor.execute("DELETE FROM memories WHERE created_at < ?", (cutoff_date,))
                conn.commit()

        except sqlite3.OperationalError:
            pass  # Table might not exist

        # 2. Deduplicate embeddings
        # This is a simplified version - in production, you'd use vector similarity
        try:
            # Find duplicates by content
            cursor.execute("""
                SELECT content, MIN(id) as keep_id, GROUP_CONCAT(id) as all_ids
                FROM memories
                GROUP BY content
                HAVING COUNT(*) > 1
            """)
            duplicates = cursor.fetchall()

            # Delete all but the first occurrence
            for content, keep_id, all_ids in duplicates:
                ids_to_delete = [id for id in all_ids.split(',') if id != keep_id]
                for row_id in ids_to_delete:
                    cursor.execute("DELETE FROM memories WHERE id = ?", (row_id,))
                    result.deduplicated_embeddings += 1

            conn.commit()

        except sqlite3.OperationalError:
            pass

        # 3. Vacuum database
        cursor.execute("VACUUM")
        conn.commit()

        # 4. Compress old session files
        # Look for uncompressed session files in cold storage
        for session_file in self.cold_storage_path.glob("session_*.json"):
            if not session_file.with_suffix(".json.gz").exists():
                with open(session_file, "rb") as f_in:
                    with gzip.open(session_file.with_suffix(".json.gz"), "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
                session_file.unlink()
                result.compressed_sessions += 1

        conn.close()

        # Get final size
        result.db_size_after_mb = self.db_path.stat().st_size / (1024 * 1024)
        result.duration_seconds = time.time() - start_time

        return result

    def monitor_query_latency(self, query_type: str, latency_ms: float) -> None:
        """
        Record query latency and check for SLO violations.

        Args:
            query_type: Type of query (fts5_search, embedding_search, reranking)
            latency_ms: Query latency in milliseconds
        """
        if query_type not in self.latency_stats:
            self.latency_stats[query_type] = LatencyStats(query_type)

        self.latency_stats[query_type].record(latency_ms)

    def get_slo_violations(self) -> list[str]:
        """
        Check for SLO violations based on p95 latency.

        Returns:
            List of violation messages.
        """
        violations = []

        # Check FTS5 search
        fts5_stats = self.latency_stats.get("fts5_search")
        if fts5_stats and fts5_stats.count() > 0:
            p95 = fts5_stats.p95()
            if p95 > self.slos.FTS5_SEARCH_MS:
                violations.append(
                    f"FTS5 search p95 latency: {p95:.1f}ms (SLO: {self.slos.FTS5_SEARCH_MS}ms)"
                )

        # Check embedding search
        embedding_stats = self.latency_stats.get("embedding_search")
        if embedding_stats and embedding_stats.count() > 0:
            p95 = embedding_stats.p95()
            if p95 > self.slos.EMBEDDING_SEARCH_MS:
                violations.append(
                    f"Embedding search p95 latency: {p95:.1f}ms (SLO: {self.slos.EMBEDDING_SEARCH_MS}ms)"
                )

        # Check reranking
        reranking_stats = self.latency_stats.get("reranking")
        if reranking_stats and reranking_stats.count() > 0:
            p95 = reranking_stats.p95()
            if p95 > self.slos.RERANKING_MS:
                violations.append(
                    f"Reranking p95 latency: {p95:.1f}ms (SLO: {self.slos.RERANKING_MS}ms)"
                )

        return violations

    def get_capacity_report(self) -> CapacityReport:
        """
        Generate comprehensive capacity report.

        Returns:
            CapacityReport with current status, latency stats, and violations.
        """
        status = self.check_capacity()
        violations = self.get_slo_violations()

        return CapacityReport(
            status=status,
            latency_stats=self.latency_stats.copy(),
            slo_violations=violations,
        )

    def reset_latency_stats(self) -> None:
        """Reset all latency statistics."""
        for stats in self.latency_stats.values():
            stats.samples.clear()

