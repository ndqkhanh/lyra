"""
Tests for Memory System

Tests the multi-tier memory architecture with SQLite backend.
"""

import shutil
import tempfile
from pathlib import Path

import pytest
from lyra_evolution.memory_system import MemoryRecord, MemorySystem


@pytest.fixture
def temp_memory_system():
    """Create temporary memory system for testing."""
    temp_dir = Path(tempfile.mkdtemp())
    db_path = temp_dir / "test_memories.db"

    memory_system = MemorySystem(db_path=db_path)

    yield memory_system

    # Cleanup
    shutil.rmtree(temp_dir)


def test_memory_system_initialization(temp_memory_system):
    """Test memory system initializes correctly."""
    assert temp_memory_system.db_path.exists()
    stats = temp_memory_system.get_statistics()
    assert stats["total"] == 0


def test_add_episodic_memory(temp_memory_system):
    """Test adding episodic memory."""
    memory_id = MemorySystem.generate_memory_id("test event", "episodic")

    memory = MemoryRecord(
        id=memory_id,
        scope="session",
        type="episodic",
        content="User performed action X"
    )

    added_id = temp_memory_system.add_memory(memory)
    assert added_id == memory_id

    # Verify memory exists
    retrieved = temp_memory_system.get_memory(memory_id)
    assert retrieved is not None
    assert retrieved.content == "User performed action X"


def test_add_semantic_memory(temp_memory_system):
    """Test adding semantic memory."""
    memory_id = MemorySystem.generate_memory_id("test fact", "semantic")

    memory = MemoryRecord(
        id=memory_id,
        scope="project",
        type="semantic",
        content="Harness prevents reward hacking",
        confidence=0.95,
        verifier_status="verified"
    )

    temp_memory_system.add_memory(memory)

    retrieved = temp_memory_system.get_memory(memory_id)
    assert retrieved.confidence == 0.95
    assert retrieved.verifier_status == "verified"


def test_search_memories_by_query(temp_memory_system):
    """Test searching memories by text query."""
    # Add multiple memories
    for i in range(3):
        memory_id = MemorySystem.generate_memory_id(f"test {i}", "episodic")
        memory = MemoryRecord(
            id=memory_id,
            scope="session",
            type="episodic",
            content=f"Memory about harness feature {i}"
        )
        temp_memory_system.add_memory(memory)

    # Search
    results = temp_memory_system.search_memories(query="harness")
    assert len(results) == 3


def test_search_memories_by_type(temp_memory_system):
    """Test filtering memories by type."""
    # Add different types
    episodic_id = MemorySystem.generate_memory_id("episodic", "episodic")
    temp_memory_system.add_memory(MemoryRecord(
        id=episodic_id,
        scope="session",
        type="episodic",
        content="Episodic memory"
    ))

    semantic_id = MemorySystem.generate_memory_id("semantic", "semantic")
    temp_memory_system.add_memory(MemoryRecord(
        id=semantic_id,
        scope="project",
        type="semantic",
        content="Semantic memory"
    ))

    # Filter by type
    episodic_results = temp_memory_system.search_memories(memory_type="episodic")
    assert len(episodic_results) == 1
    assert episodic_results[0].type == "episodic"


def test_update_memory(temp_memory_system):
    """Test updating memory fields."""
    memory_id = MemorySystem.generate_memory_id("test", "semantic")

    memory = MemoryRecord(
        id=memory_id,
        scope="project",
        type="semantic",
        content="Initial content",
        confidence=0.5
    )

    temp_memory_system.add_memory(memory)

    # Update confidence
    updated = temp_memory_system.update_memory(
        memory_id,
        {"confidence": 0.95, "verifier_status": "verified"}
    )

    assert updated

    # Verify update
    retrieved = temp_memory_system.get_memory(memory_id)
    assert retrieved.confidence == 0.95
    assert retrieved.verifier_status == "verified"


def test_delete_memory(temp_memory_system):
    """Test deleting memory."""
    memory_id = MemorySystem.generate_memory_id("test", "episodic")

    memory = MemoryRecord(
        id=memory_id,
        scope="session",
        type="episodic",
        content="To be deleted"
    )

    temp_memory_system.add_memory(memory)

    # Delete
    deleted = temp_memory_system.delete_memory(memory_id)
    assert deleted

    # Verify deletion
    retrieved = temp_memory_system.get_memory(memory_id)
    assert retrieved is None


def test_memory_links(temp_memory_system):
    """Test memory relationships."""
    # Create parent memory
    parent_id = MemorySystem.generate_memory_id("parent", "semantic")
    parent = MemoryRecord(
        id=parent_id,
        scope="project",
        type="semantic",
        content="Parent memory"
    )
    temp_memory_system.add_memory(parent)

    # Create child memory with link
    child_id = MemorySystem.generate_memory_id("child", "semantic")
    child = MemoryRecord(
        id=child_id,
        scope="project",
        type="semantic",
        content="Child memory",
        links=[parent_id]
    )
    temp_memory_system.add_memory(child)

    # Verify link
    retrieved = temp_memory_system.get_memory(child_id)
    assert parent_id in retrieved.links


def test_get_statistics(temp_memory_system):
    """Test memory statistics."""
    # Add various memories
    temp_memory_system.add_memory(MemoryRecord(
        id=MemorySystem.generate_memory_id("1", "episodic"),
        scope="session",
        type="episodic",
        content="Memory 1"
    ))

    temp_memory_system.add_memory(MemoryRecord(
        id=MemorySystem.generate_memory_id("2", "semantic"),
        scope="project",
        type="semantic",
        content="Memory 2"
    ))

    stats = temp_memory_system.get_statistics()

    assert stats["total"] == 2
    assert stats["by_type"]["episodic"] == 1
    assert stats["by_type"]["semantic"] == 1


def test_temporal_validity(temp_memory_system):
    """Test temporal validity fields."""
    memory_id = MemorySystem.generate_memory_id("temporal", "semantic")

    memory = MemoryRecord(
        id=memory_id,
        scope="project",
        type="semantic",
        content="Fact with validity window",
        valid_from="2026-01-01T00:00:00",
        valid_until="2026-12-31T23:59:59"
    )

    temp_memory_system.add_memory(memory)

    retrieved = temp_memory_system.get_memory(memory_id)
    assert retrieved.valid_from == "2026-01-01T00:00:00"
    assert retrieved.valid_until == "2026-12-31T23:59:59"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
