"""
Tests for memory schema and data structures.
"""

from datetime import datetime, timedelta

import pytest

from lyra_memory.schema import (
    MemoryRecord,
    MemoryScope,
    MemoryType,
    VerifierStatus,
)


def test_memory_record_creation():
    """Test creating a basic memory record."""
    memory = MemoryRecord(
        content="User prefers pytest over unittest",
        scope=MemoryScope.USER,
        type=MemoryType.PREFERENCE,
    )

    assert memory.id  # UUID generated
    assert memory.content == "User prefers pytest over unittest"
    assert memory.scope == MemoryScope.USER
    assert memory.type == MemoryType.PREFERENCE
    assert memory.confidence == 1.0
    assert memory.verifier_status == VerifierStatus.UNVERIFIED


def test_memory_record_temporal_validity():
    """Test temporal validity checking."""
    now = datetime.now()
    past = now - timedelta(days=7)
    future = now + timedelta(days=7)

    memory = MemoryRecord(
        content="Project uses Python 3.10",
        valid_from=past,
        valid_until=future,
    )

    assert memory.is_valid_at(now)
    assert memory.is_valid_at(past)
    assert memory.is_valid_at(future)
    assert not memory.is_valid_at(past - timedelta(days=1))
    assert not memory.is_valid_at(future + timedelta(days=1))


def test_memory_record_superseded():
    """Test superseded memory tracking."""
    memory = MemoryRecord(content="Old fact")
    assert not memory.is_superseded()

    memory.superseded_by = "new-memory-id"
    assert memory.is_superseded()


def test_memory_record_validation():
    """Test field validation."""
    # Invalid confidence
    with pytest.raises(ValueError, match="Confidence must be"):
        MemoryRecord(content="Test", confidence=1.5)

    with pytest.raises(ValueError, match="Confidence must be"):
        MemoryRecord(content="Test", confidence=-0.1)

    # Invalid temporal range
    now = datetime.now()
    future = now + timedelta(days=1)
    with pytest.raises(ValueError, match="valid_from must be"):
        MemoryRecord(
            content="Test",
            valid_from=future,
            valid_until=now,
        )


def test_memory_record_to_dict():
    """Test serialization to dictionary."""
    now = datetime.now()
    memory = MemoryRecord(
        content="Test memory",
        scope=MemoryScope.PROJECT,
        type=MemoryType.SEMANTIC,
        source_span="turn 42",
        valid_from=now,
        confidence=0.9,
        links=["mem-1", "mem-2"],
        metadata={"key": "value"},
    )

    data = memory.to_dict()

    assert data["id"] == memory.id
    assert data["content"] == "Test memory"
    assert data["scope"] == "project"
    assert data["type"] == "semantic"
    assert data["source_span"] == "turn 42"
    assert data["confidence"] == 0.9
    assert data["links"] == ["mem-1", "mem-2"]
    assert data["metadata"] == {"key": "value"}


def test_memory_record_from_dict():
    """Test deserialization from dictionary."""
    now = datetime.now()
    data = {
        "id": "test-id",
        "scope": "user",
        "type": "preference",
        "content": "Test content",
        "source_span": "turn 1",
        "created_at": now.isoformat(),
        "valid_from": now.isoformat(),
        "valid_until": None,
        "confidence": 0.8,
        "links": ["link-1"],
        "verifier_status": "verified",
        "metadata": {"test": "data"},
        "superseded_by": None,
    }

    memory = MemoryRecord.from_dict(data)

    assert memory.id == "test-id"
    assert memory.scope == MemoryScope.USER
    assert memory.type == MemoryType.PREFERENCE
    assert memory.content == "Test content"
    assert memory.confidence == 0.8
    assert memory.verifier_status == VerifierStatus.VERIFIED


def test_memory_scopes():
    """Test all memory scopes."""
    scopes = [
        MemoryScope.USER,
        MemoryScope.SESSION,
        MemoryScope.PROJECT,
        MemoryScope.GLOBAL,
    ]

    for scope in scopes:
        memory = MemoryRecord(content="Test", scope=scope)
        assert memory.scope == scope


def test_memory_types():
    """Test all memory types."""
    types = [
        MemoryType.EPISODIC,
        MemoryType.SEMANTIC,
        MemoryType.PROCEDURAL,
        MemoryType.PREFERENCE,
        MemoryType.FAILURE,
    ]

    for mem_type in types:
        memory = MemoryRecord(content="Test", type=mem_type)
        assert memory.type == mem_type


def test_verifier_statuses():
    """Test all verifier statuses."""
    statuses = [
        VerifierStatus.UNVERIFIED,
        VerifierStatus.VERIFIED,
        VerifierStatus.REJECTED,
        VerifierStatus.QUARANTINED,
    ]

    for status in statuses:
        memory = MemoryRecord(content="Test", verifier_status=status)
        assert memory.verifier_status == status
