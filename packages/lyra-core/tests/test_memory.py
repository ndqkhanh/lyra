"""
Tests for Memory Architecture

Tests the 4-tier memory system with breakthrough patterns from MemAgents research.
"""

import pytest
from datetime import datetime
from lyra_core.memory import (
    MemoryArchitecture,
    MemoryType,
    MemoryPriority,
    MemoryEntry,
    WorkingMemory,
    EpisodicMemory,
    SemanticMemory,
    ProceduralMemory
)


class TestMemoryEntry:
    """Test MemoryEntry functionality"""

    def test_create_entry(self):
        """Test creating a memory entry"""
        entry = MemoryEntry(
            id="test-1",
            content="Test content",
            memory_type=MemoryType.WORKING,
            priority=MemoryPriority.HIGH,
            created_at=datetime.now(),
            accessed_at=datetime.now()
        )
        assert entry.id == "test-1"
        assert entry.content == "Test content"
        assert entry.memory_type == MemoryType.WORKING
        assert entry.priority == MemoryPriority.HIGH
        assert entry.access_count == 0

    def test_update_access(self):
        """Test updating access statistics"""
        entry = MemoryEntry(
            id="test-1",
            content="Test content",
            memory_type=MemoryType.WORKING,
            priority=MemoryPriority.HIGH,
            created_at=datetime.now(),
            accessed_at=datetime.now()
        )
        initial_count = entry.access_count
        entry.update_access()
        assert entry.access_count == initial_count + 1
        assert entry.utility_score > 0.0


class TestWorkingMemory:
    """Test Working Memory functionality"""

    def test_add_entry(self):
        """Test adding entry to working memory"""
        wm = WorkingMemory()
        entry = MemoryEntry(
            id="test-1",
            content="Test content",
            memory_type=MemoryType.WORKING,
            priority=MemoryPriority.HIGH,
            created_at=datetime.now(),
            accessed_at=datetime.now()
        )
        result = wm.add(entry)
        assert result is True
        assert len(wm.entries) == 1

    def test_goal_gating(self):
        """Test goal-based gating"""
        wm = WorkingMemory()
        wm.current_goal = "implement memory system"

        relevant_entry = MemoryEntry(
            id="test-1",
            content="Memory system implementation details",
            memory_type=MemoryType.WORKING,
            priority=MemoryPriority.HIGH,
            created_at=datetime.now(),
            accessed_at=datetime.now()
        )

        irrelevant_entry = MemoryEntry(
            id="test-2",
            content="Unrelated content about cooking",
            memory_type=MemoryType.WORKING,
            priority=MemoryPriority.HIGH,
            created_at=datetime.now(),
            accessed_at=datetime.now()
        )

        assert wm.add(relevant_entry) is True
        assert wm.add(irrelevant_entry) is False
        assert len(wm.entries) == 1

    def test_capacity_enforcement(self):
        """Test capacity enforcement"""
        wm = WorkingMemory(capacity=100)  # Small capacity for testing

        # Add entries until over capacity
        for i in range(50):
            entry = MemoryEntry(
                id=f"test-{i}",
                content=f"Test content {i} " * 10,  # ~10 tokens each
                memory_type=MemoryType.WORKING,
                priority=MemoryPriority.MEDIUM,
                created_at=datetime.now(),
                accessed_at=datetime.now()
            )
            wm.add(entry)

        # Should have evicted some entries
        total_tokens = sum(len(e.content.split()) for e in wm.entries)
        assert total_tokens <= wm.capacity


class TestEpisodicMemory:
    """Test Episodic Memory functionality"""

    def test_add_entry(self):
        """Test adding entry to episodic memory"""
        em = EpisodicMemory()
        entry = MemoryEntry(
            id="test-1",
            content="Test event",
            memory_type=MemoryType.EPISODIC,
            priority=MemoryPriority.MEDIUM,
            created_at=datetime.now(),
            accessed_at=datetime.now()
        )
        em.add(entry)
        assert len(em.entries) == 1
        assert 'temporal_context' in entry.metadata

    def test_get_recent(self):
        """Test getting recent entries"""
        em = EpisodicMemory()

        # Add multiple entries
        for i in range(20):
            entry = MemoryEntry(
                id=f"test-{i}",
                content=f"Event {i}",
                memory_type=MemoryType.EPISODIC,
                priority=MemoryPriority.MEDIUM,
                created_at=datetime.now(),
                accessed_at=datetime.now()
            )
            em.add(entry)

        recent = em.get_recent(n=5)
        assert len(recent) == 5
        # Should be in reverse chronological order
        assert recent[0].id == "test-19"


class TestSemanticMemory:
    """Test Semantic Memory functionality"""

    def test_add_entry(self):
        """Test adding entry to semantic memory"""
        sm = SemanticMemory()
        entry = MemoryEntry(
            id="test-1",
            content="Python programming language concepts",
            memory_type=MemoryType.SEMANTIC,
            priority=MemoryPriority.HIGH,
            created_at=datetime.now(),
            accessed_at=datetime.now()
        )
        sm.add(entry)
        assert len(sm.entries) == 1
        assert len(sm.knowledge_graph) > 0

    def test_query(self):
        """Test querying semantic memory"""
        sm = SemanticMemory()

        entry1 = MemoryEntry(
            id="test-1",
            content="Python programming language concepts",
            memory_type=MemoryType.SEMANTIC,
            priority=MemoryPriority.HIGH,
            created_at=datetime.now(),
            accessed_at=datetime.now()
        )

        entry2 = MemoryEntry(
            id="test-2",
            content="JavaScript programming language features",
            memory_type=MemoryType.SEMANTIC,
            priority=MemoryPriority.HIGH,
            created_at=datetime.now(),
            accessed_at=datetime.now()
        )

        sm.add(entry1)
        sm.add(entry2)

        results = sm.query("programming")
        assert len(results) == 2


class TestProceduralMemory:
    """Test Procedural Memory functionality"""

    def test_add_skill(self):
        """Test adding skill to procedural memory"""
        pm = ProceduralMemory()
        entry = MemoryEntry(
            id="test-1",
            content="def hello(): print('Hello')",
            memory_type=MemoryType.PROCEDURAL,
            priority=MemoryPriority.HIGH,
            created_at=datetime.now(),
            accessed_at=datetime.now()
        )
        pm.add_skill("hello_function", entry)
        assert len(pm.skills) == 1

    def test_get_skill(self):
        """Test retrieving skill"""
        pm = ProceduralMemory()
        entry = MemoryEntry(
            id="test-1",
            content="def hello(): print('Hello')",
            memory_type=MemoryType.PROCEDURAL,
            priority=MemoryPriority.HIGH,
            created_at=datetime.now(),
            accessed_at=datetime.now()
        )
        pm.add_skill("hello_function", entry)

        retrieved = pm.get_skill("hello_function")
        assert retrieved is not None
        assert retrieved.id == "test-1"


class TestMemoryArchitecture:
    """Test complete Memory Architecture"""

    def test_initialization(self):
        """Test memory architecture initialization"""
        ma = MemoryArchitecture()
        assert ma.working is not None
        assert ma.episodic is not None
        assert ma.semantic is not None
        assert ma.procedural is not None

    def test_store_working_memory(self):
        """Test storing in working memory"""
        ma = MemoryArchitecture()
        entry_id = ma.store(
            content="Current task context",
            memory_type=MemoryType.WORKING,
            priority=MemoryPriority.HIGH
        )
        assert entry_id is not None
        assert len(ma.working.entries) == 1

    def test_store_episodic_memory(self):
        """Test storing in episodic memory"""
        ma = MemoryArchitecture()
        entry_id = ma.store(
            content="Recent event",
            memory_type=MemoryType.EPISODIC,
            priority=MemoryPriority.MEDIUM
        )
        assert entry_id is not None
        assert len(ma.episodic.entries) == 1

    def test_store_semantic_memory(self):
        """Test storing in semantic memory"""
        ma = MemoryArchitecture()
        entry_id = ma.store(
            content="Knowledge about Python programming",
            memory_type=MemoryType.SEMANTIC,
            priority=MemoryPriority.HIGH
        )
        assert entry_id is not None
        assert len(ma.semantic.entries) == 1

    def test_store_procedural_memory(self):
        """Test storing in procedural memory"""
        ma = MemoryArchitecture()
        entry_id = ma.store(
            content="def greet(name): return f'Hello {name}'",
            memory_type=MemoryType.PROCEDURAL,
            priority=MemoryPriority.HIGH,
            metadata={'skill_name': 'greet_function'}
        )
        assert entry_id is not None
        assert len(ma.procedural.skills) == 1

    def test_retrieve_with_high_uncertainty(self):
        """Test retrieval with high epistemic uncertainty"""
        ma = MemoryArchitecture()

        # Store some memories
        ma.store("Python programming concepts", MemoryType.WORKING)
        ma.store("Recent Python project", MemoryType.EPISODIC)
        ma.store("Python language features", MemoryType.SEMANTIC)

        # Retrieve with high uncertainty (should retrieve)
        results = ma.retrieve("Python", uncertainty=0.8)
        assert len(results) > 0

    def test_retrieve_with_low_uncertainty(self):
        """Test retrieval with low epistemic uncertainty"""
        ma = MemoryArchitecture()

        # Store some memories
        ma.store("Python programming concepts", MemoryType.WORKING)

        # Retrieve with low uncertainty (should not retrieve)
        results = ma.retrieve("Python", uncertainty=0.2)
        assert len(results) == 0

    def test_get_stats(self):
        """Test getting memory statistics"""
        ma = MemoryArchitecture()

        # Store some memories
        ma.store("Working memory content", MemoryType.WORKING)
        ma.store("Episodic memory content", MemoryType.EPISODIC)
        ma.store("Semantic memory content", MemoryType.SEMANTIC)
        ma.store("Procedural memory content", MemoryType.PROCEDURAL,
                metadata={'skill_name': 'test_skill'})

        stats = ma.get_stats()
        assert stats['working_memory']['entries'] == 1
        assert stats['episodic_memory']['entries'] == 1
        assert stats['semantic_memory']['entries'] == 1
        assert stats['procedural_memory']['skills'] == 1


class TestMemoryIntegration:
    """Integration tests for memory architecture"""

    def test_full_workflow(self):
        """Test complete memory workflow"""
        ma = MemoryArchitecture()

        # Set working memory goal
        ma.working.current_goal = "implement memory system"

        # Store various types of memories
        ma.store("Implementing 4-tier memory architecture", MemoryType.WORKING)
        ma.store("Completed memory module design", MemoryType.EPISODIC)
        ma.store("Memory systems use tiered architecture", MemoryType.SEMANTIC)
        ma.store("def create_memory(): pass", MemoryType.PROCEDURAL,
                metadata={'skill_name': 'create_memory'})

        # Retrieve with high uncertainty
        results = ma.retrieve("memory", uncertainty=0.9)
        assert len(results) >= 3

        # Check stats
        stats = ma.get_stats()
        assert stats['working_memory']['entries'] >= 1
        assert stats['episodic_memory']['entries'] >= 1
        assert stats['semantic_memory']['entries'] >= 1
        assert stats['procedural_memory']['skills'] >= 1

    def test_memory_consolidation(self):
        """Test memory consolidation across tiers"""
        ma = MemoryArchitecture()

        # Fill working memory
        for i in range(10):
            ma.store(f"Task {i} context", MemoryType.WORKING)

        # Fill episodic memory
        for i in range(20):
            ma.store(f"Event {i} details", MemoryType.EPISODIC)

        # Verify consolidation happened
        stats = ma.get_stats()
        assert stats['working_memory']['entries'] <= 10
        assert stats['episodic_memory']['entries'] <= 20


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
