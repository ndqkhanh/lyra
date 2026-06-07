"""
Tests for Long-Term Memory.
"""

import os
import tempfile
import time

from lyra.memory.long_term_memory import LongTermMemory, MemoryIndex
from lyra.memory.memory_store import MemoryType


class TestMemoryIndex:
    """Test MemoryIndex class."""

    def test_index_creation(self):
        """Test creating a memory index."""
        index = MemoryIndex()

        assert len(index.tag_index) == 0
        assert len(index.type_index) == 0
        assert len(index.time_index) == 0

    def test_add_memory_to_index(self):
        """Test adding a memory to index."""
        from lyra.memory.memory_store import Memory

        index = MemoryIndex()
        memory = Memory(
            memory_id="test-1",
            content="Test",
            memory_type=MemoryType.EPISODIC,
            timestamp=time.time(),
            tags=["tag1", "tag2"],
        )

        index.add_memory(memory)

        assert "test-1" in index.tag_index["tag1"]
        assert "test-1" in index.tag_index["tag2"]
        assert "test-1" in index.type_index[MemoryType.EPISODIC]

    def test_remove_memory_from_index(self):
        """Test removing a memory from index."""
        from lyra.memory.memory_store import Memory

        index = MemoryIndex()
        memory = Memory(
            memory_id="test-1",
            content="Test",
            memory_type=MemoryType.EPISODIC,
            timestamp=time.time(),
            tags=["tag1"],
        )

        index.add_memory(memory)
        index.remove_memory(memory)

        assert "test-1" not in index.tag_index["tag1"]
        assert "test-1" not in index.type_index[MemoryType.EPISODIC]

    def test_find_by_tags_any(self):
        """Test finding by tags (any match)."""
        from lyra.memory.memory_store import Memory

        index = MemoryIndex()

        m1 = Memory("m1", "Test 1", MemoryType.EPISODIC, time.time(), tags=["tag1"])
        m2 = Memory("m2", "Test 2", MemoryType.EPISODIC, time.time(), tags=["tag2"])
        m3 = Memory("m3", "Test 3", MemoryType.EPISODIC, time.time(), tags=["tag1", "tag2"])

        index.add_memory(m1)
        index.add_memory(m2)
        index.add_memory(m3)

        results = index.find_by_tags(["tag1", "tag2"], match_all=False)

        assert len(results) == 3

    def test_find_by_tags_all(self):
        """Test finding by tags (all match)."""
        from lyra.memory.memory_store import Memory

        index = MemoryIndex()

        m1 = Memory("m1", "Test 1", MemoryType.EPISODIC, time.time(), tags=["tag1"])
        m2 = Memory("m2", "Test 2", MemoryType.EPISODIC, time.time(), tags=["tag2"])
        m3 = Memory("m3", "Test 3", MemoryType.EPISODIC, time.time(), tags=["tag1", "tag2"])

        index.add_memory(m1)
        index.add_memory(m2)
        index.add_memory(m3)

        results = index.find_by_tags(["tag1", "tag2"], match_all=True)

        assert len(results) == 1
        assert "m3" in results

    def test_find_by_type(self):
        """Test finding by type."""
        from lyra.memory.memory_store import Memory

        index = MemoryIndex()

        m1 = Memory("m1", "Test 1", MemoryType.EPISODIC, time.time())
        m2 = Memory("m2", "Test 2", MemoryType.SEMANTIC, time.time())
        m3 = Memory("m3", "Test 3", MemoryType.EPISODIC, time.time())

        index.add_memory(m1)
        index.add_memory(m2)
        index.add_memory(m3)

        results = index.find_by_type(MemoryType.EPISODIC)

        assert len(results) == 2

    def test_find_by_time_range(self):
        """Test finding by time range."""
        from lyra.memory.memory_store import Memory

        index = MemoryIndex()

        now = time.time()
        m1 = Memory("m1", "Test 1", MemoryType.EPISODIC, now - 200)
        m2 = Memory("m2", "Test 2", MemoryType.EPISODIC, now - 100)
        m3 = Memory("m3", "Test 3", MemoryType.EPISODIC, now)

        index.add_memory(m1)
        index.add_memory(m2)
        index.add_memory(m3)

        results = index.find_by_time_range(start_time=now - 150)

        assert len(results) == 2

    def test_clear_index(self):
        """Test clearing index."""
        from lyra.memory.memory_store import Memory

        index = MemoryIndex()
        memory = Memory("m1", "Test", MemoryType.EPISODIC, time.time(), tags=["tag1"])

        index.add_memory(memory)
        index.clear()

        assert len(index.tag_index) == 0
        assert len(index.type_index) == 0
        assert len(index.time_index) == 0


class TestLongTermMemory:
    """Test LongTermMemory class."""

    def test_ltm_creation(self):
        """Test creating long-term memory."""
        ltm = LongTermMemory()

        assert len(ltm.store.memories) == 0

    def test_add_memory(self):
        """Test adding a memory."""
        ltm = LongTermMemory()

        memory = ltm.add(
            content="Test memory",
            memory_type=MemoryType.SEMANTIC,
            importance=0.8,
            tags=["test"],
        )

        assert memory.memory_id in ltm.store.memories
        assert memory.content == "Test memory"

    def test_get_memory(self):
        """Test getting a memory."""
        ltm = LongTermMemory()
        memory = ltm.add("Test", MemoryType.EPISODIC)

        retrieved = ltm.get(memory.memory_id)

        assert retrieved is not None
        assert retrieved.memory_id == memory.memory_id

    def test_search_by_tags(self):
        """Test searching by tags."""
        ltm = LongTermMemory()

        ltm.add("Test 1", MemoryType.EPISODIC, tags=["tag1", "tag2"])
        ltm.add("Test 2", MemoryType.EPISODIC, tags=["tag2", "tag3"])
        ltm.add("Test 3", MemoryType.EPISODIC, tags=["tag3"])

        results = ltm.search_by_tags(["tag1", "tag2"], match_all=False)

        assert len(results) == 2

    def test_search_by_tags_with_limit(self):
        """Test searching by tags with limit."""
        ltm = LongTermMemory()

        for i in range(5):
            ltm.add(f"Test {i}", MemoryType.EPISODIC, tags=["common"])

        results = ltm.search_by_tags(["common"], limit=3)

        assert len(results) == 3

    def test_search_by_type(self):
        """Test searching by type."""
        ltm = LongTermMemory()

        ltm.add("Episodic 1", MemoryType.EPISODIC)
        ltm.add("Semantic 1", MemoryType.SEMANTIC)
        ltm.add("Episodic 2", MemoryType.EPISODIC)

        results = ltm.search_by_type(MemoryType.EPISODIC)

        assert len(results) == 2

    def test_search_by_time_range(self):
        """Test searching by time range."""
        ltm = LongTermMemory()

        now = time.time()

        # Add memories at different times
        m1 = ltm.add("Old", MemoryType.EPISODIC)
        m1.timestamp = now - 200

        m2 = ltm.add("Recent", MemoryType.EPISODIC)
        m2.timestamp = now - 50

        m3 = ltm.add("New", MemoryType.EPISODIC)
        m3.timestamp = now

        # Rebuild index after modifying timestamps
        ltm._rebuild_index()

        results = ltm.search_by_time_range(start_time=now - 100)

        assert len(results) == 2

    def test_search_by_content(self):
        """Test searching by content."""
        ltm = LongTermMemory()

        ltm.add("Python is great", MemoryType.SEMANTIC)
        ltm.add("JavaScript is useful", MemoryType.SEMANTIC)
        ltm.add("Python and JavaScript", MemoryType.SEMANTIC)

        results = ltm.search_by_content("Python")

        assert len(results) == 2

    def test_search_by_content_with_limit(self):
        """Test searching by content with limit."""
        ltm = LongTermMemory()

        for i in range(5):
            ltm.add(f"Test keyword {i}", MemoryType.SEMANTIC)

        results = ltm.search_by_content("keyword", limit=3)

        assert len(results) == 3

    def test_get_recent(self):
        """Test getting recent memories."""
        ltm = LongTermMemory()

        for i in range(5):
            ltm.add(f"Test {i}", MemoryType.EPISODIC)
            time.sleep(0.01)

        recent = ltm.get_recent(limit=3)

        assert len(recent) == 3
        assert recent[0].content == "Test 4"

    def test_get_important(self):
        """Test getting important memories."""
        ltm = LongTermMemory()

        ltm.add("Low", MemoryType.EPISODIC, importance=0.3)
        ltm.add("High 1", MemoryType.EPISODIC, importance=0.8)
        ltm.add("High 2", MemoryType.EPISODIC, importance=0.9)

        important = ltm.get_important(threshold=0.7)

        assert len(important) == 2

    def test_merge_similar(self):
        """Test merging similar memories."""
        ltm = LongTermMemory()

        ltm.add("Same content", MemoryType.SEMANTIC, importance=0.8, tags=["tag1"])
        ltm.add("Same content", MemoryType.SEMANTIC, importance=0.6, tags=["tag2"])
        ltm.add("Different", MemoryType.SEMANTIC, importance=0.7)

        merged = ltm.merge_similar()

        assert merged == 1
        assert len(ltm.store.memories) == 2

    def test_apply_decay(self):
        """Test applying decay."""
        ltm = LongTermMemory()

        memory = ltm.add("Test", MemoryType.EPISODIC, importance=0.8)
        memory.last_accessed = time.time() - 86400

        ltm.apply_decay(decay_rate=0.1)

        assert memory.importance < 0.8

    def test_prune(self):
        """Test pruning low-importance memories."""
        ltm = LongTermMemory()

        ltm.add("Low 1", MemoryType.EPISODIC, importance=0.05)
        ltm.add("Low 2", MemoryType.EPISODIC, importance=0.08)
        ltm.add("High", MemoryType.EPISODIC, importance=0.8)

        pruned = ltm.prune(min_importance=0.1)

        assert pruned == 2
        assert len(ltm.store.memories) == 1

    def test_save_and_load(self):
        """Test saving and loading."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "ltm.json")

            ltm1 = LongTermMemory(storage_path=path)
            ltm1.add("Test 1", MemoryType.EPISODIC, tags=["tag1"])
            ltm1.add("Test 2", MemoryType.SEMANTIC, tags=["tag2"])
            ltm1.save()

            ltm2 = LongTermMemory(storage_path=path)

            assert len(ltm2.store.memories) == 2
            # Index should be rebuilt
            assert len(ltm2.index.tag_index) > 0

    def test_clear(self):
        """Test clearing all memories."""
        ltm = LongTermMemory()

        ltm.add("Test 1", MemoryType.EPISODIC)
        ltm.add("Test 2", MemoryType.SEMANTIC)

        ltm.clear()

        assert len(ltm.store.memories) == 0
        assert len(ltm.index.tag_index) == 0

    def test_get_statistics(self):
        """Test getting statistics."""
        ltm = LongTermMemory()

        ltm.add("Test 1", MemoryType.EPISODIC, tags=["tag1"])
        ltm.add("Test 2", MemoryType.SEMANTIC, tags=["tag2"])

        stats = ltm.get_statistics()

        assert stats["total_memories"] == 2
        assert stats["indexed_tags"] == 2
        assert stats["indexed_types"] == 2
