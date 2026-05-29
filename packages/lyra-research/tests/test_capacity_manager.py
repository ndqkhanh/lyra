"""
Tests for Memory Capacity Management.

Covers:
- Capacity enforcement (alert at 80%, block at 100%)
- Compaction (archive old notes, deduplicate embeddings)
- Query latency monitoring (SLO violations)
- Capacity reporting
"""
import gzip
import json
import sqlite3
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from lyra_research.capacity_manager import (
    CapacityLevel,
    CapacityLimits,
    CapacityManager,
    CapacityReport,
    CapacityStatus,
    CompactionResult,
    LatencyStats,
    QuerySLOs,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Create memories table
        cursor.execute("""
            CREATE TABLE memories (
                id TEXT PRIMARY KEY,
                scope TEXT NOT NULL,
                type TEXT NOT NULL,
                content TEXT NOT NULL,
                source_span TEXT,
                created_at TEXT NOT NULL,
                valid_from TEXT,
                valid_until TEXT,
                confidence REAL NOT NULL,
                links TEXT,
                verifier_status TEXT NOT NULL,
                metadata TEXT,
                superseded_by TEXT
            )
        """)

        # Create sources table
        cursor.execute("""
            CREATE TABLE sources (
                id TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        conn.commit()
        conn.close()

        yield db_path


@pytest.fixture
def capacity_manager(temp_db):
    """Create a capacity manager with test database."""
    return CapacityManager(temp_db)


@pytest.fixture
def custom_limits():
    """Create custom capacity limits for testing."""
    limits = CapacityLimits()
    limits.MAX_SOURCES = 100
    limits.MAX_NOTES = 1000
    limits.MAX_SESSIONS = 50
    return limits


@pytest.fixture
def small_limits():
    """Create small capacity limits for testing."""
    limits = CapacityLimits()
    limits.MAX_SOURCES = 100
    limits.MAX_NOTES = 100
    limits.MAX_SESSIONS = 50
    return limits


# ---------------------------------------------------------------------------
# CapacityLimits Tests
# ---------------------------------------------------------------------------


def test_capacity_limits_defaults():
    """Test default capacity limits."""
    limits = CapacityLimits()
    assert limits.MAX_SOURCES == 10_000
    assert limits.MAX_NOTES == 100_000
    assert limits.MAX_SESSIONS == 1_000
    assert limits.ALERT_THRESHOLD == 0.8
    assert limits.BLOCK_THRESHOLD == 1.0


def test_capacity_limits_custom():
    """Test custom capacity limits."""
    limits = CapacityLimits()
    limits.MAX_SOURCES = 5000
    limits.MAX_NOTES = 50000
    assert limits.MAX_SOURCES == 5000
    assert limits.MAX_NOTES == 50000


# QuerySLOs Tests
# ---------------------------------------------------------------------------


def test_query_slos_defaults():
    """Test default query SLOs."""
    slos = QuerySLOs()
    assert slos.FTS5_SEARCH_MS == 100
    assert slos.EMBEDDING_SEARCH_MS == 200
    assert slos.RERANKING_MS == 500


def test_query_slos_custom():
    """Test custom query SLOs."""
    slos = QuerySLOs()
    slos.FTS5_SEARCH_MS = 50
    slos.EMBEDDING_SEARCH_MS = 150
    assert slos.FTS5_SEARCH_MS == 50
    assert slos.EMBEDDING_SEARCH_MS == 150


# ---------------------------------------------------------------------------
# CapacityStatus Tests
# ---------------------------------------------------------------------------


def test_capacity_status_utilization():
    """Test capacity status utilization calculations."""
    status = CapacityStatus(
        sources_count=80,
        sources_limit=100,
        notes_count=500,
        notes_limit=1000,
        sessions_count=25,
        sessions_limit=50,
        db_size_mb=100.0,
        level=CapacityLevel.WARNING,
    )

    assert status.sources_utilization == 0.8
    assert status.notes_utilization == 0.5
    assert status.sessions_utilization == 0.5
    assert status.max_utilization == 0.8


def test_capacity_status_max_utilization():
    """Test max utilization calculation."""
    status = CapacityStatus(
        sources_count=50,
        sources_limit=100,
        notes_count=900,
        notes_limit=1000,
        sessions_count=10,
        sessions_limit=50,
        db_size_mb=100.0,
        level=CapacityLevel.WARNING,
    )

    assert status.max_utilization == 0.9  # Notes is highest


def test_capacity_status_zero_limit():
    """Test utilization with zero limit."""
    status = CapacityStatus(
        sources_count=10,
        sources_limit=0,
        notes_count=100,
        notes_limit=1000,
        sessions_count=5,
        sessions_limit=50,
        db_size_mb=100.0,
        level=CapacityLevel.HEALTHY,
    )

    assert status.sources_utilization == 0.0  # Should handle division by zero


# ---------------------------------------------------------------------------
# CompactionResult Tests
# ---------------------------------------------------------------------------


def test_compaction_result_size_reduction():
    """Test compaction result size reduction calculations."""
    result = CompactionResult(
        archived_notes=100,
        deduplicated_embeddings=50,
        compressed_sessions=10,
        db_size_before_mb=1000.0,
        db_size_after_mb=700.0,
        duration_seconds=5.0,
    )

    assert result.size_reduction_mb == 300.0
    assert result.size_reduction_percent == 30.0


def test_compaction_result_zero_before_size():
    """Test compaction result with zero before size."""
    result = CompactionResult(
        db_size_before_mb=0.0,
        db_size_after_mb=0.0,
    )

    assert result.size_reduction_percent == 0.0


# ---------------------------------------------------------------------------
# LatencyStats Tests
# ---------------------------------------------------------------------------


def test_latency_stats_record():
    """Test recording latency samples."""
    stats = LatencyStats("test_query")
    stats.record(100.0)
    stats.record(200.0)
    stats.record(150.0)

    assert stats.count() == 3
    assert 100.0 in stats.samples
    assert 200.0 in stats.samples


def test_latency_stats_percentiles():
    """Test latency percentile calculations."""
    stats = LatencyStats("test_query")
    samples = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    for sample in samples:
        stats.record(float(sample))

    assert stats.p50() == pytest.approx(55.0)  # Median
    assert stats.p95() == pytest.approx(95.5)  # 95th percentile
    assert stats.p99() == pytest.approx(99.1)  # 99th percentile
    assert stats.mean() == pytest.approx(55.0)


def test_latency_stats_empty():
    """Test latency stats with no samples."""
    stats = LatencyStats("test_query")

    assert stats.count() == 0
    assert stats.p50() == 0.0
    assert stats.p95() == 0.0
    assert stats.p99() == 0.0
    assert stats.mean() == 0.0


def test_latency_stats_max_samples():
    """Test latency stats respects max samples limit."""
    stats = LatencyStats("test_query", max_samples=10)

    # Record 20 samples
    for i in range(20):
        stats.record(float(i))

    # Should only keep last 10
    assert stats.count() == 10
    assert stats.samples[0] == 10.0  # First sample should be 10 (0-9 dropped)
    assert stats.samples[-1] == 19.0


# ---------------------------------------------------------------------------
# CapacityManager Tests - Basic Operations
# ---------------------------------------------------------------------------


def test_capacity_manager_init(temp_db):
    """Test capacity manager initialization."""
    manager = CapacityManager(temp_db)

    assert manager.db_path == temp_db
    assert manager.cold_storage_path.exists()
    assert isinstance(manager.limits, CapacityLimits)
    assert isinstance(manager.slos, QuerySLOs)
    assert len(manager.latency_stats) == 3


def test_capacity_manager_custom_limits(temp_db, custom_limits):
    """Test capacity manager with custom limits."""
    manager = CapacityManager(temp_db, limits=custom_limits)

    assert manager.limits.MAX_SOURCES == 100
    assert manager.limits.MAX_NOTES == 1000
    assert manager.limits.MAX_SESSIONS == 50


def test_capacity_manager_custom_cold_storage(temp_db):
    """Test capacity manager with custom cold storage path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cold_path = Path(tmpdir) / "cold"
        manager = CapacityManager(temp_db, cold_storage_path=cold_path)

        assert manager.cold_storage_path == cold_path
        assert cold_path.exists()


# ---------------------------------------------------------------------------
# CapacityManager Tests - Capacity Checking
# ---------------------------------------------------------------------------


def test_check_capacity_empty_db(capacity_manager):
    """Test capacity check on empty database."""
    status = capacity_manager.check_capacity()

    assert status.sources_count == 0
    assert status.notes_count == 0
    assert status.level == CapacityLevel.HEALTHY
    assert not status.blocked
    assert len(status.warnings) == 0


def test_check_capacity_with_data(temp_db, small_limits):
    """Test capacity check with data."""
    # Insert test data
    conn = sqlite3.connect(str(temp_db))
    cursor = conn.cursor()

    # Insert 85 notes (85% of 100 limit)
    for i in range(85):
        cursor.execute(
            "INSERT INTO memories (id, scope, type, content, created_at, confidence, verifier_status) "
            "VALUES (?, 'session', 'episodic', ?, ?, 1.0, 'verified')",
            (f"mem_{i}", f"Content {i}", datetime.now(timezone.utc).isoformat()),
        )

    # Insert 50 sources (50% of 100 limit)
    for i in range(50):
        cursor.execute(
            "INSERT INTO sources (id, url, created_at) VALUES (?, ?, ?)",
            (f"src_{i}", f"https://example.com/{i}", datetime.now(timezone.utc).isoformat()),
        )

    conn.commit()
    conn.close()

    manager = CapacityManager(temp_db, limits=small_limits)
    status = manager.check_capacity()

    assert status.notes_count == 85
    assert status.sources_count == 50
    assert status.level == CapacityLevel.WARNING  # 85% > 80% threshold
    assert not status.blocked
    assert len(status.warnings) > 0


def test_check_capacity_at_limit(temp_db, small_limits):
    """Test capacity check at 100% limit."""
    # Insert test data at limit
    conn = sqlite3.connect(str(temp_db))
    cursor = conn.cursor()

    # Insert 100 notes (100% of limit)
    for i in range(100):
        cursor.execute(
            "INSERT INTO memories (id, scope, type, content, created_at, confidence, verifier_status) "
            "VALUES (?, 'session', 'episodic', ?, ?, 1.0, 'verified')",
            (f"mem_{i}", f"Content {i}", datetime.now(timezone.utc).isoformat()),
        )

    conn.commit()
    conn.close()

    manager = CapacityManager(temp_db, limits=small_limits)
    status = manager.check_capacity()

    assert status.notes_count == 100
    assert status.level == CapacityLevel.CRITICAL
    assert status.blocked
    assert "CRITICAL" in status.warnings[0]


def test_check_capacity_below_threshold(temp_db, small_limits):
    """Test capacity check below alert threshold."""
    # Insert test data below threshold
    conn = sqlite3.connect(str(temp_db))
    cursor = conn.cursor()

    # Insert 50 notes (50% of 100 limit)
    for i in range(50):
        cursor.execute(
            "INSERT INTO memories (id, scope, type, content, created_at, confidence, verifier_status) "
            "VALUES (?, 'session', 'episodic', ?, ?, 1.0, 'verified')",
            (f"mem_{i}", f"Content {i}", datetime.now(timezone.utc).isoformat()),
        )

    conn.commit()
    conn.close()

    manager = CapacityManager(temp_db, limits=small_limits)
    status = manager.check_capacity()

    assert status.notes_count == 50
    assert status.level == CapacityLevel.HEALTHY
    assert not status.blocked
    assert len(status.warnings) == 0


# CapacityManager Tests - Enforce Limits
# ---------------------------------------------------------------------------


def test_enforce_limits_healthy(capacity_manager):
    """Test enforce limits with healthy capacity."""
    # Should not raise
    capacity_manager.enforce_limits()


def test_enforce_limits_warning(temp_db, small_limits):
    """Test enforce limits at warning level (should not block)."""
    # Insert 85 notes (85% of limit)
    conn = sqlite3.connect(str(temp_db))
    cursor = conn.cursor()

    for i in range(85):
        cursor.execute(
            "INSERT INTO memories (id, scope, type, content, created_at, confidence, verifier_status) "
            "VALUES (?, 'session', 'episodic', ?, ?, 1.0, 'verified')",
            (f"mem_{i}", f"Content {i}", datetime.now(timezone.utc).isoformat()),
        )

    conn.commit()
    conn.close()

    manager = CapacityManager(temp_db, limits=small_limits)

    # Should not raise at 85%
    manager.enforce_limits()


def test_enforce_limits_critical(temp_db, small_limits):
    """Test enforce limits at critical level (should block)."""
    # Insert 100 notes (100% of limit)
    conn = sqlite3.connect(str(temp_db))
    cursor = conn.cursor()

    for i in range(100):
        cursor.execute(
            "INSERT INTO memories (id, scope, type, content, created_at, confidence, verifier_status) "
            "VALUES (?, 'session', 'episodic', ?, ?, 1.0, 'verified')",
            (f"mem_{i}", f"Content {i}", datetime.now(timezone.utc).isoformat()),
        )

    conn.commit()
    conn.close()

    manager = CapacityManager(temp_db, limits=small_limits)

    # Should raise at 100%
    with pytest.raises(RuntimeError, match="Capacity limit reached"):
        manager.enforce_limits()


# ---------------------------------------------------------------------------
# CapacityManager Tests - Compaction
# ---------------------------------------------------------------------------


def test_compact_empty_db(capacity_manager):
    """Test compaction on empty database."""
    result = capacity_manager.compact(age_days=90)

    assert result.archived_notes == 0
    assert result.deduplicated_embeddings == 0
    assert result.compressed_sessions == 0
    assert result.duration_seconds >= 0


def test_compact_archive_old_notes(temp_db):
    """Test compaction archives old notes."""
    # Insert old and new notes
    conn = sqlite3.connect(str(temp_db))
    cursor = conn.cursor()

    # Old notes (100 days ago)
    old_date = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()
    for i in range(10):
        cursor.execute(
            "INSERT INTO memories (id, scope, type, content, created_at, confidence, verifier_status) "
            "VALUES (?, 'session', 'episodic', ?, ?, 1.0, 'verified')",
            (f"old_{i}", f"Old content {i}", old_date),
        )

    # New notes (10 days ago)
    new_date = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    for i in range(5):
        cursor.execute(
            "INSERT INTO memories (id, scope, type, content, created_at, confidence, verifier_status) "
            "VALUES (?, 'session', 'episodic', ?, ?, 1.0, 'verified')",
            (f"new_{i}", f"New content {i}", new_date),
        )

    conn.commit()
    conn.close()

    manager = CapacityManager(temp_db)
    result = manager.compact(age_days=90)

    assert result.archived_notes == 10  # Only old notes archived

    # Verify old notes are deleted
    conn = sqlite3.connect(str(temp_db))
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM memories")
    remaining = cursor.fetchone()[0]
    conn.close()

    assert remaining == 5  # Only new notes remain


def test_compact_creates_archive_file(temp_db):
    """Test compaction creates compressed archive file."""
    # Insert old notes
    conn = sqlite3.connect(str(temp_db))
    cursor = conn.cursor()

    old_date = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()
    for i in range(5):
        cursor.execute(
            "INSERT INTO memories (id, scope, type, content, created_at, confidence, verifier_status) "
            "VALUES (?, 'session', 'episodic', ?, ?, 1.0, 'verified')",
            (f"old_{i}", f"Old content {i}", old_date),
        )

    conn.commit()
    conn.close()

    manager = CapacityManager(temp_db)
    manager.compact(age_days=90)

    # Check archive file exists
    archive_files = list(manager.cold_storage_path.glob("archive_*.json.gz"))
    assert len(archive_files) == 1

    # Verify archive content
    with gzip.open(archive_files[0], "rt", encoding="utf-8") as f:
        archived_data = json.load(f)
        assert len(archived_data) == 5


def test_compact_deduplicate_content(temp_db):
    """Test compaction deduplicates identical content."""
    # Insert duplicate notes
    conn = sqlite3.connect(str(temp_db))
    cursor = conn.cursor()

    # Insert 5 notes with same content
    for i in range(5):
        cursor.execute(
            "INSERT INTO memories (id, scope, type, content, created_at, confidence, verifier_status) "
            "VALUES (?, 'session', 'episodic', 'Duplicate content', ?, 1.0, 'verified')",
            (f"dup_{i}", datetime.now(timezone.utc).isoformat()),
        )

    # Insert 3 notes with unique content
    for i in range(3):
        cursor.execute(
            "INSERT INTO memories (id, scope, type, content, created_at, confidence, verifier_status) "
            "VALUES (?, 'session', 'episodic', ?, ?, 1.0, 'verified')",
            (f"unique_{i}", f"Unique content {i}", datetime.now(timezone.utc).isoformat()),
        )

    conn.commit()
    conn.close()

    manager = CapacityManager(temp_db)
    result = manager.compact(age_days=90)

    # Should deduplicate 4 of the 5 duplicates (keep 1)
    assert result.deduplicated_embeddings == 4

    # Verify only 4 notes remain (1 duplicate + 3 unique)
    conn = sqlite3.connect(str(temp_db))
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM memories")
    remaining = cursor.fetchone()[0]
    conn.close()

    assert remaining == 4


def test_compact_vacuum_reduces_size(temp_db):
    """Test compaction vacuum reduces database size."""
    # Insert and delete many notes to create fragmentation
    conn = sqlite3.connect(str(temp_db))
    cursor = conn.cursor()

    # Insert 100 notes
    for i in range(100):
        cursor.execute(
            "INSERT INTO memories (id, scope, type, content, created_at, confidence, verifier_status) "
            "VALUES (?, 'session', 'episodic', ?, ?, 1.0, 'verified')",
            (f"mem_{i}", f"Content {i}" * 100, datetime.now(timezone.utc).isoformat()),
        )

    conn.commit()

    # Delete 90 notes using subquery
    cursor.execute("""
        DELETE FROM memories WHERE id IN (
            SELECT id FROM memories WHERE id LIKE 'mem_%' LIMIT 90
        )
    """)
    conn.commit()
    conn.close()

    manager = CapacityManager(temp_db)
    result = manager.compact(age_days=90)

    # Vacuum should reduce size
    assert result.size_reduction_mb >= 0  # Size should not increase


def test_compact_compress_sessions(temp_db):
    """Test compaction compresses session files."""
    manager = CapacityManager(temp_db)

    # Create uncompressed session files
    for i in range(3):
        session_file = manager.cold_storage_path / f"session_{i}.json"
        with open(session_file, "w") as f:
            json.dump({"session_id": i, "data": "test" * 100}, f)

    result = manager.compact(age_days=90)

    assert result.compressed_sessions == 3

    # Verify compressed files exist
    compressed_files = list(manager.cold_storage_path.glob("session_*.json.gz"))
    assert len(compressed_files) == 3

    # Verify uncompressed files are deleted
    uncompressed_files = list(manager.cold_storage_path.glob("session_*.json"))
    assert len(uncompressed_files) == 0


def test_compact_size_reduction_calculation(temp_db):
    """Test compaction calculates size reduction correctly."""
    # Insert data
    conn = sqlite3.connect(str(temp_db))
    cursor = conn.cursor()

    old_date = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()
    for i in range(50):
        cursor.execute(
            "INSERT INTO memories (id, scope, type, content, created_at, confidence, verifier_status) "
            "VALUES (?, 'session', 'episodic', ?, ?, 1.0, 'verified')",
            (f"mem_{i}", f"Content {i}" * 100, old_date),
        )

    conn.commit()
    conn.close()

    manager = CapacityManager(temp_db)
    result = manager.compact(age_days=90)

    assert result.db_size_before_mb > 0
    assert result.db_size_after_mb >= 0
    assert result.size_reduction_mb >= 0
    assert result.size_reduction_percent >= 0


# ---------------------------------------------------------------------------
# CapacityManager Tests - Query Latency Monitoring
# ---------------------------------------------------------------------------


def test_monitor_query_latency(capacity_manager):
    """Test monitoring query latency."""
    capacity_manager.monitor_query_latency("fts5_search", 50.0)
    capacity_manager.monitor_query_latency("fts5_search", 75.0)
    capacity_manager.monitor_query_latency("fts5_search", 100.0)

    stats = capacity_manager.latency_stats["fts5_search"]
    assert stats.count() == 3
    assert 50.0 in stats.samples


def test_monitor_query_latency_multiple_types(capacity_manager):
    """Test monitoring multiple query types."""
    capacity_manager.monitor_query_latency("fts5_search", 50.0)
    capacity_manager.monitor_query_latency("embedding_search", 150.0)
    capacity_manager.monitor_query_latency("reranking", 400.0)

    assert capacity_manager.latency_stats["fts5_search"].count() == 1
    assert capacity_manager.latency_stats["embedding_search"].count() == 1
    assert capacity_manager.latency_stats["reranking"].count() == 1


def test_monitor_query_latency_new_type(capacity_manager):
    """Test monitoring creates new stats for unknown query type."""
    capacity_manager.monitor_query_latency("custom_query", 100.0)

    assert "custom_query" in capacity_manager.latency_stats
    assert capacity_manager.latency_stats["custom_query"].count() == 1


# CapacityManager Tests - SLO Violations
# ---------------------------------------------------------------------------


def test_get_slo_violations_none(capacity_manager):
    """Test no SLO violations with healthy latency."""
    # Record latencies below SLO
    for _ in range(10):
        capacity_manager.monitor_query_latency("fts5_search", 50.0)
        capacity_manager.monitor_query_latency("embedding_search", 100.0)
        capacity_manager.monitor_query_latency("reranking", 300.0)

    violations = capacity_manager.get_slo_violations()
    assert len(violations) == 0


def test_get_slo_violations_fts5(capacity_manager):
    """Test SLO violation for FTS5 search."""
    # Record latencies above SLO (100ms)
    for _ in range(10):
        capacity_manager.monitor_query_latency("fts5_search", 150.0)

    violations = capacity_manager.get_slo_violations()
    assert len(violations) == 1
    assert "FTS5 search" in violations[0]
    assert "150" in violations[0]


def test_get_slo_violations_embedding(capacity_manager):
    """Test SLO violation for embedding search."""
    # Record latencies above SLO (200ms)
    for _ in range(10):
        capacity_manager.monitor_query_latency("embedding_search", 300.0)

    violations = capacity_manager.get_slo_violations()
    assert len(violations) == 1
    assert "Embedding search" in violations[0]


def test_get_slo_violations_reranking(capacity_manager):
    """Test SLO violation for reranking."""
    # Record latencies above SLO (500ms)
    for _ in range(10):
        capacity_manager.monitor_query_latency("reranking", 700.0)

    violations = capacity_manager.get_slo_violations()
    assert len(violations) == 1
    assert "Reranking" in violations[0]


def test_get_slo_violations_multiple(capacity_manager):
    """Test multiple SLO violations."""
    # Record latencies above SLO for all types
    for _ in range(10):
        capacity_manager.monitor_query_latency("fts5_search", 150.0)
        capacity_manager.monitor_query_latency("embedding_search", 300.0)
        capacity_manager.monitor_query_latency("reranking", 700.0)

    violations = capacity_manager.get_slo_violations()
    assert len(violations) == 3


def test_get_slo_violations_p95_threshold(capacity_manager):
    """Test SLO violations use p95, not mean."""
    # Record mostly fast queries with some slow outliers
    for _ in range(90):
        capacity_manager.monitor_query_latency("fts5_search", 50.0)  # Fast

    for _ in range(10):
        capacity_manager.monitor_query_latency("fts5_search", 200.0)  # Slow

    # p95 should be around 200ms (above 100ms SLO)
    violations = capacity_manager.get_slo_violations()
    assert len(violations) == 1
    assert "FTS5 search" in violations[0]


# ---------------------------------------------------------------------------
# CapacityManager Tests - Capacity Report
# ---------------------------------------------------------------------------


def test_get_capacity_report_empty(capacity_manager):
    """Test capacity report on empty database."""
    report = capacity_manager.get_capacity_report()

    assert isinstance(report, CapacityReport)
    assert report.status.level == CapacityLevel.HEALTHY
    assert len(report.slo_violations) == 0
    assert len(report.latency_stats) == 3


def test_get_capacity_report_with_data(temp_db, small_limits):
    """Test capacity report with data and latency."""
    # Insert data
    conn = sqlite3.connect(str(temp_db))
    cursor = conn.cursor()

    for i in range(85):
        cursor.execute(
            "INSERT INTO memories (id, scope, type, content, created_at, confidence, verifier_status) "
            "VALUES (?, 'session', 'episodic', ?, ?, 1.0, 'verified')",
            (f"mem_{i}", f"Content {i}", datetime.now(timezone.utc).isoformat()),
        )

    conn.commit()
    conn.close()

    manager = CapacityManager(temp_db, limits=small_limits)

    # Record latencies
    for _ in range(10):
        manager.monitor_query_latency("fts5_search", 50.0)

    report = manager.get_capacity_report()

    assert report.status.notes_count == 85
    assert report.status.level == CapacityLevel.WARNING
    assert report.latency_stats["fts5_search"].count() == 10


def test_get_capacity_report_with_violations(capacity_manager):
    """Test capacity report includes SLO violations."""
    # Record slow queries
    for _ in range(10):
        capacity_manager.monitor_query_latency("fts5_search", 150.0)
        capacity_manager.monitor_query_latency("embedding_search", 300.0)

    report = capacity_manager.get_capacity_report()

    assert len(report.slo_violations) == 2


def test_capacity_report_to_dict(capacity_manager):
    """Test capacity report serialization to dict."""
    # Add some data
    for _ in range(5):
        capacity_manager.monitor_query_latency("fts5_search", 50.0)

    report = capacity_manager.get_capacity_report()
    report_dict = report.to_dict()

    assert "timestamp" in report_dict
    assert "capacity" in report_dict
    assert "latency" in report_dict
    assert "slo_violations" in report_dict

    # Check capacity section
    assert "sources" in report_dict["capacity"]
    assert "notes" in report_dict["capacity"]
    assert "sessions" in report_dict["capacity"]
    assert "level" in report_dict["capacity"]

    # Check latency section
    assert "fts5_search" in report_dict["latency"]
    assert "p50" in report_dict["latency"]["fts5_search"]
    assert "p95" in report_dict["latency"]["fts5_search"]


def test_capacity_report_timestamp(capacity_manager):
    """Test capacity report includes timestamp."""
    report = capacity_manager.get_capacity_report()

    assert isinstance(report.timestamp, datetime)
    assert report.timestamp.tzinfo is not None  # Should be timezone-aware


# ---------------------------------------------------------------------------
# CapacityManager Tests - Reset
# ---------------------------------------------------------------------------


def test_reset_latency_stats(capacity_manager):
    """Test resetting latency statistics."""
    # Record some latencies
    for _ in range(10):
        capacity_manager.monitor_query_latency("fts5_search", 50.0)
        capacity_manager.monitor_query_latency("embedding_search", 100.0)

    # Verify data exists
    assert capacity_manager.latency_stats["fts5_search"].count() == 10
    assert capacity_manager.latency_stats["embedding_search"].count() == 10

    # Reset
    capacity_manager.reset_latency_stats()

    # Verify data cleared
    assert capacity_manager.latency_stats["fts5_search"].count() == 0
    assert capacity_manager.latency_stats["embedding_search"].count() == 0


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------


def test_full_capacity_lifecycle(temp_db, custom_limits):
    """Test full capacity management lifecycle."""
    manager = CapacityManager(temp_db, limits=custom_limits)

    # 1. Start with empty database
    status = manager.check_capacity()
    assert status.level == CapacityLevel.HEALTHY

    # 2. Add data to warning level
    conn = sqlite3.connect(str(temp_db))
    cursor = conn.cursor()

    for i in range(850):
        cursor.execute(
            "INSERT INTO memories (id, scope, type, content, created_at, confidence, verifier_status) "
            "VALUES (?, 'session', 'episodic', ?, ?, 1.0, 'verified')",
            (f"mem_{i}", f"Content {i}", datetime.now(timezone.utc).isoformat()),
        )

    conn.commit()
    conn.close()

    status = manager.check_capacity()
    assert status.level == CapacityLevel.WARNING

    # 3. Run compaction
    result = manager.compact(age_days=0)  # Archive everything
    assert result.archived_notes == 850

    # 4. Verify capacity improved
    status = manager.check_capacity()
    assert status.notes_count == 0
    assert status.level == CapacityLevel.HEALTHY


def test_capacity_with_latency_monitoring(temp_db, custom_limits):
    """Test capacity management with latency monitoring."""
    manager = CapacityManager(temp_db, limits=custom_limits)

    # Add data
    conn = sqlite3.connect(str(temp_db))
    cursor = conn.cursor()

    for i in range(500):
        cursor.execute(
            "INSERT INTO memories (id, scope, type, content, created_at, confidence, verifier_status) "
            "VALUES (?, 'session', 'episodic', ?, ?, 1.0, 'verified')",
            (f"mem_{i}", f"Content {i}", datetime.now(timezone.utc).isoformat()),
        )

    conn.commit()
    conn.close()

    # Record latencies
    for _ in range(20):
        manager.monitor_query_latency("fts5_search", 50.0)
        manager.monitor_query_latency("embedding_search", 250.0)  # Above SLO

    # Get report
    report = manager.get_capacity_report()

    assert report.status.notes_count == 500
    assert report.status.level == CapacityLevel.HEALTHY  # 50% utilization
    assert len(report.slo_violations) == 1  # Embedding search violation
    assert "Embedding search" in report.slo_violations[0]


def test_enforce_and_compact_workflow(temp_db, small_limits):
    """Test workflow: fill to capacity, enforce blocks, compact, continue."""
    manager = CapacityManager(temp_db, limits=small_limits)

    # Fill to capacity
    conn = sqlite3.connect(str(temp_db))
    cursor = conn.cursor()

    for i in range(100):
        cursor.execute(
            "INSERT INTO memories (id, scope, type, content, created_at, confidence, verifier_status) "
            "VALUES (?, 'session', 'episodic', ?, ?, 1.0, 'verified')",
            (f"mem_{i}", f"Content {i}", datetime.now(timezone.utc).isoformat()),
        )

    conn.commit()
    conn.close()

    # Enforce should block
    with pytest.raises(RuntimeError):
        manager.enforce_limits()

    # Compact to free space
    result = manager.compact(age_days=0)
    assert result.archived_notes == 100

    # Enforce should now pass
    manager.enforce_limits()


def test_compaction_reduces_size_by_30_percent(temp_db):
    """Test compaction reduces database size by at least 30%."""
    # Insert large amount of data
    conn = sqlite3.connect(str(temp_db))
    cursor = conn.cursor()

    old_date = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()
    for i in range(200):
        cursor.execute(
            "INSERT INTO memories (id, scope, type, content, created_at, confidence, verifier_status) "
            "VALUES (?, 'session', 'episodic', ?, ?, 1.0, 'verified')",
            (f"mem_{i}", f"Content {i}" * 200, old_date),  # Large content
        )

    conn.commit()
    conn.close()

    manager = CapacityManager(temp_db)
    result = manager.compact(age_days=90)

    # Should reduce by at least 30%
    assert result.size_reduction_percent >= 30.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])



