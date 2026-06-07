"""
Tests for Memory Store.
"""

import os
import tempfile
import time

from lyra.memory.memory_store import Memory, MemoryStore, MemoryType


class TestMemory:
    """Test Memory class."""

    def test_memory_creation(self):
        """Test creating a memory."""
        memory = Memory(
            memory_id="test-1",
            content="Test memory",
            memory_type=MemoryType.EPISODIC,
            timestamp=time.time(),
            importance=0.8,
            tags=["test"],
        )

        assert memory.memory_id == "test-1"
        assert memory.content == "Test memory"
        assert memory.memory_type == MemoryType.EPISODIC
        assert memory.importance == 0.8
        assert "test" in memory.tags
        assert memory.access_count == 0

    def test_memory_access(self):
        """Test memory access tracking."""
        memory = Memory(
            memory_id="test-1",
            content="Test",
            memory_type=MemoryType.EPISODIC,
            timestamp=time.time(),
        )

        initial_count = memory.access_count
        initial_time = memory.last_accessed

        time.sleep(0.01)
        memory.access()

        assert memory.access_count == initial_count + 1
        assert memory.last_accessed > initial_time

    def test_memory_decay(self):
        """Test importance decay."""
        memory = Memory(
            memory_id="test-1",
            content="Test",
            memory_type=MemoryType.EPISODIC,
            timestamp=time.time() - 86400,  # 1 day ago
            importance=0.8,
        )

        memory.last_accessed = time.time() - 86400
        memory.decay_importance(decay_rate=0.1)

        assert memory.importance < 0.8

    def test_memory_to_dict(self):
        """Test converting memory to dictionary."""
        memory = Memory(
            memory_id="test-1",
            content="Test",
            memory_type=MemoryType.SEMANTIC,
            timestamp=time.time(),
        )

        data = memory.to_dict()

        assert data["memory_id"] == "test-1"
        assert data["memory_type"] == "semantic"

    def test_memory_from_dict(self):
        """Test creating memory from dictionary."""
        data = {
            "memory_id": "test-1",
            "content": "Test",
            "memory_type": "procedural",
            "timestamp": time.time(),
            "importance": 0.7,
            "tags": ["test"],
            "context": {},
            "access_count": 0,
            "last_accessed": time.time(),
        }

        memory = Memory.from_dict(data)

        assert memory.memory_id == "test-1"
        assert memory.memory_type == MemoryType.PROCEDURAL


class TestMemoryStore:
    """Test MemoryStore class."""

    def test_store_creation(self):
        """Test creating a memory store."""
        store = MemoryStore()
        assert len(store.memories) == 0

    def test_add_memory(self):
        """Test adding a memory."""
        store = MemoryStore()

        memory = store.add(
            content="Test memory",
            memory_type=MemoryType.EPISODIC,
            importance=0.8,
            tags=["test"],
        )

        assert memory.memory_id in store.memories
        assert memory.content == "Test memory"
        assert memory.importance == 0.8

    def test_get_memory(self):
        """Test getting a memory."""
        store = MemoryStore()
        memory = store.add("Test", MemoryType.EPISODIC)

        retrieved = store.get(memory.memory_id)

        assert retrieved is not None
        assert retrieved.memory_id == memory.memory_id
        assert retrieved.access_count == 1

    def test_get_nonexistent_memory(self):
        """Test getting a nonexistent memory."""
        store = MemoryStore()

        retrieved = store.get("nonexistent")

        assert retrieved is None

    def test_update_memory(self):
        """Test updating a memory."""
        store = MemoryStore()
        memory = store.add("Test", MemoryType.EPISODIC)

        success = store.update(memory.memory_id, importance=0.9)

        assert success
        assert store.memories[memory.memory_id].importance == 0.9

    def test_update_nonexistent_memory(self):
        """Test updating a nonexistent memory."""
        store = MemoryStore()

        success = store.update("nonexistent", importance=0.9)

        assert not success

    def test_delete_memory(self):
        """Test deleting a memory."""
        store = MemoryStore()
        memory = store.add("Test", MemoryType.EPISODIC)

        success = store.delete(memory.memory_id)

        assert success
        assert memory.memory_id not in store.memories

    def test_delete_nonexistent_memory(self):
        """Test deleting a nonexistent memory."""
        store = MemoryStore()

        success = store.delete("nonexistent")

        assert not success

    def test_get_all_memories(self):
        """Test getting all memories."""
        store = MemoryStore()
        store.add("Test 1", MemoryType.EPISODIC)
        store.add("Test 2", MemoryType.SEMANTIC)

        all_memories = store.get_all()

        assert len(all_memories) == 2

    def test_get_by_type(self):
        """Test getting memories by type."""
        store = MemoryStore()
        store.add("Episodic 1", MemoryType.EPISODIC)
        store.add("Semantic 1", MemoryType.SEMANTIC)
        store.add("Episodic 2", MemoryType.EPISODIC)

        episodic = store.get_by_type(MemoryType.EPISODIC)

        assert len(episodic) == 2
        assert all(m.memory_type == MemoryType.EPISODIC for m in episodic)

    def test_get_by_tags_any(self):
        """Test getting memories by tags (any match)."""
        store = MemoryStore()
        store.add("Test 1", MemoryType.EPISODIC, tags=["tag1", "tag2"])
        store.add("Test 2", MemoryType.EPISODIC, tags=["tag2", "tag3"])
        store.add("Test 3", MemoryType.EPISODIC, tags=["tag3"])

        results = store.get_by_tags(["tag1", "tag3"], match_all=False)

        assert len(results) == 3

    def test_get_by_tags_all(self):
        """Test getting memories by tags (all match)."""
        store = MemoryStore()
        store.add("Test 1", MemoryType.EPISODIC, tags=["tag1", "tag2"])
        store.add("Test 2", MemoryType.EPISODIC, tags=["tag2", "tag3"])
        store.add("Test 3", MemoryType.EPISODIC, tags=["tag1", "tag2", "tag3"])

        results = store.get_by_tags(["tag1", "tag2"], match_all=True)

        assert len(results) == 2

    def test_get_recent(self):
        """Test getting recent memories."""
        store = MemoryStore()

        for i in range(5):
            store.add(f"Test {i}", MemoryType.EPISODIC)
            time.sleep(0.01)

        recent = store.get_recent(limit=3)

        assert len(recent) == 3
        assert recent[0].content == "Test 4"

    def test_get_important(self):
        """Test getting important memories."""
        store = MemoryStore()
        store.add("Low", MemoryType.EPISODIC, importance=0.3)
        store.add("High 1", MemoryType.EPISODIC, importance=0.8)
        store.add("High 2", MemoryType.EPISODIC, importance=0.9)

        important = store.get_important(threshold=0.7, limit=10)

        assert len(important) == 2
        assert important[0].importance == 0.9

    def test_apply_decay(self):
        """Test applying decay to all memories."""
        store = MemoryStore()

        memory = store.add("Test", MemoryType.EPISODIC, importance=0.8)
        memory.last_accessed = time.time() - 86400  # 1 day ago

        store.apply_decay(decay_rate=0.1)

        assert memory.importance < 0.8

    def test_prune(self):
        """Test pruning low-importance memories."""
        store = MemoryStore()
        store.add("Low 1", MemoryType.EPISODIC, importance=0.05)
        store.add("Low 2", MemoryType.EPISODIC, importance=0.08)
        store.add("High", MemoryType.EPISODIC, importance=0.8)

        pruned = store.prune(min_importance=0.1)

        assert pruned == 2
        assert len(store.memories) == 1

    def test_save_and_load(self):
        """Test saving and loading memories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "memories.json")

            # Create and save
            store1 = MemoryStore(storage_path=path)
            store1.add("Test 1", MemoryType.EPISODIC, importance=0.8)
            store1.add("Test 2", MemoryType.SEMANTIC, importance=0.6)
            store1.save()

            # Load in new store
            store2 = MemoryStore(storage_path=path)

            assert len(store2.memories) == 2

    def test_clear(self):
        """Test clearing all memories."""
        store = MemoryStore()
        store.add("Test 1", MemoryType.EPISODIC)
        store.add("Test 2", MemoryType.SEMANTIC)

        store.clear()

        assert len(store.memories) == 0

    def test_get_statistics(self):
        """Test getting statistics."""
        store = MemoryStore()
        store.add("Episodic", MemoryType.EPISODIC, importance=0.8)
        store.add("Semantic", MemoryType.SEMANTIC, importance=0.6)

        # Access one memory
        memories = store.get_all()
        store.get(memories[0].memory_id)

        stats = store.get_statistics()

        assert stats["total_memories"] == 2
        assert stats["by_type"]["episodic"] == 1
        assert stats["by_type"]["semantic"] == 1
        assert stats["total_accesses"] == 1

    def test_get_statistics_empty(self):
        """Test getting statistics for empty store."""
        store = MemoryStore()

        stats = store.get_statistics()

        assert stats["total_memories"] == 0
        assert stats["average_importance"] == 0.0
