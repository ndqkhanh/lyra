"""
Tests for memory database layer.
"""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from lyra_memory.database import MemoryDatabase
from lyra_memory.schema import (
    MemoryRecord,
    MemoryScope,
    MemoryType,
    VerifierStatus,
)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = MemoryDatabase(db_path)
        yield db
        db.close()


def test_database_initialization(temp_db):
    """Test database schema initialization."""
    # Check that tables exist
    cursor = temp_db.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )
    tables = {row[0] for row in cursor.fetchall()}

    assert "memories" in tables
    assert "memories_fts" in tables


def test_insert_and_get(temp_db):
    """Test inserting and retrieving a memory."""
    memory = MemoryRecord(
        content="Test memory",
        scope=MemoryScope.PROJECT,
        type=MemoryType.SEMANTIC,
    )

    temp_db.insert(memory)
    retrieved = temp_db.get(memory.id)

    assert retrieved is not None
    assert retrieved.id == memory.id
    assert retrieved.content == "Test memory"
    assert retrieved.scope == MemoryScope.PROJECT
    assert retrieved.type == MemoryType.SEMANTIC


def test_update(temp_db):
    """Test updating a memory."""
    memory = MemoryRecord(content="Original content")
    temp_db.insert(memory)

    memory.content = "Updated content"
    memory.confidence = 0.8
    temp_db.update(memory)

    retrieved = temp_db.get(memory.id)
    assert retrieved.content == "Updated content"
    assert retrieved.confidence == 0.8


def test_delete(temp_db):
    """Test deleting a memory."""
    memory = MemoryRecord(content="To be deleted")
    temp_db.insert(memory)

    temp_db.delete(memory.id)
    retrieved = temp_db.get(memory.id)

    assert retrieved is None


def test_full_text_search(temp_db):
    """Test FTS5 full-text search."""
    memories = [
        MemoryRecord(content="Python is a programming language"),
        MemoryRecord(content="JavaScript is also a programming language"),
        MemoryRecord(content="The weather is nice today"),
    ]

    for mem in memories:
        temp_db.insert(mem)

    results = temp_db.search_fts("programming")
    assert len(results) == 2

    results = temp_db.search_fts("weather")
    assert len(results) == 1
    assert "weather" in results[0].content.lower()


def test_filter_by_scope(temp_db):
    """Test filtering by scope."""
    temp_db.insert(MemoryRecord(content="User memory", scope=MemoryScope.USER))
    temp_db.insert(MemoryRecord(content="Project memory", scope=MemoryScope.PROJECT))
    temp_db.insert(MemoryRecord(content="Session memory", scope=MemoryScope.SESSION))

    results = temp_db.filter(scope=MemoryScope.USER)
    assert len(results) == 1
    assert results[0].scope == MemoryScope.USER


def test_filter_by_type(temp_db):
    """Test filtering by type."""
    temp_db.insert(MemoryRecord(content="Fact", type=MemoryType.SEMANTIC))
    temp_db.insert(MemoryRecord(content="Event", type=MemoryType.EPISODIC))
    temp_db.insert(MemoryRecord(content="Preference", type=MemoryType.PREFERENCE))

    results = temp_db.filter(type=MemoryType.SEMANTIC)
    assert len(results) == 1
    assert results[0].type == MemoryType.SEMANTIC


def test_filter_by_temporal_validity(temp_db):
    """Test filtering by temporal validity."""
    now = datetime.now()
    past = now - timedelta(days=7)
    future = now + timedelta(days=7)

    # Memory valid in the past
    temp_db.insert(
        MemoryRecord(
            content="Old fact",
            valid_from=past - timedelta(days=14),
            valid_until=past,
        )
    )

    # Memory valid now
    temp_db.insert(
        MemoryRecord(
            content="Current fact",
            valid_from=past,
            valid_until=future,
        )
    )

    # Memory valid in the future
    temp_db.insert(
        MemoryRecord(
            content="Future fact",
            valid_from=future,
            valid_until=future + timedelta(days=7),
        )
    )

    # Query for memories valid now
    results = temp_db.filter(valid_at=now)
    assert len(results) == 1
    assert results[0].content == "Current fact"


def test_get_recent(temp_db):
    """Test getting recent memories."""
    now = datetime.now()

    # Old memory
    old_mem = MemoryRecord(content="Old memory")
    old_mem.created_at = now - timedelta(days=10)
    temp_db.insert(old_mem)

    # Recent memory
    recent_mem = MemoryRecord(content="Recent memory")
    recent_mem.created_at = now - timedelta(days=3)
    temp_db.insert(recent_mem)

    results = temp_db.get_recent(days=7)
    assert len(results) == 1
    assert results[0].content == "Recent memory"


def test_get_stats(temp_db):
    """Test database statistics."""
    temp_db.insert(
        MemoryRecord(content="Verified", verifier_status=VerifierStatus.VERIFIED)
    )
    temp_db.insert(
        MemoryRecord(content="Unverified", verifier_status=VerifierStatus.UNVERIFIED)
    )
    temp_db.insert(
        MemoryRecord(content="Quarantined", verifier_status=VerifierStatus.QUARANTINED)
    )

    # Supersede one memory (starts as unverified by default)
    superseded = MemoryRecord(content="Superseded")
    temp_db.insert(superseded)
    superseded.superseded_by = "new-id"
    temp_db.update(superseded)

    stats = temp_db.get_stats()

    assert stats["total"] == 4
    assert stats["verified"] == 1
    assert stats["unverified"] == 2  # "Unverified" + "Superseded" (default status)
    assert stats["quarantined"] == 1
    assert stats["superseded"] == 1
    assert stats["active"] == 3


def test_links_and_metadata(temp_db):
    """Test storing links and metadata."""
    memory = MemoryRecord(
        content="Test",
        links=["mem-1", "mem-2", "mem-3"],
        metadata={"key1": "value1", "key2": 42, "key3": True},
    )

    temp_db.insert(memory)
    retrieved = temp_db.get(memory.id)

    assert retrieved.links == ["mem-1", "mem-2", "mem-3"]
    assert retrieved.metadata == {"key1": "value1", "key2": 42, "key3": True}
