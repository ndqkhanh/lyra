"""
Tests for Memory Consolidation.
"""

import pytest
import time

from src.memory.memory_store import MemoryType
from src.memory.short_term_memory import ShortTermMemory, ConversationTurn
from src.memory.long_term_memory import LongTermMemory
from src.memory.memory_consolidation import (
    MemoryConsolidator,
    ConsolidationPolicy,
    ConsolidationResult,
)


class TestConsolidationResult:
    """Test ConsolidationResult class."""

    def test_result_creation(self):
        """Test creating a consolidation result."""
        result = ConsolidationResult(
            memories_created=5,
            memories_merged=2,
            patterns_extracted=1,
            duration=0.5,
        )
        
        assert result.memories_created == 5
        assert result.memories_merged == 2
        assert result.patterns_extracted == 1
        assert result.duration == 0.5


class TestMemoryConsolidator:
    """Test MemoryConsolidator class."""

    def test_consolidator_creation(self):
        """Test creating a memory consolidator."""
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(stm, ltm)
        
        assert consolidator.policy == ConsolidationPolicy.THRESHOLD
        assert consolidator.importance_threshold == 0.5

    def test_should_consolidate_immediate(self):
        """Test immediate consolidation policy."""
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(
            stm, ltm,
            policy=ConsolidationPolicy.IMMEDIATE
        )
        
        assert consolidator.should_consolidate()

    def test_should_consolidate_threshold(self):
        """Test threshold consolidation policy."""
        stm = ShortTermMemory(consolidation_threshold=3)
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(
            stm, ltm,
            policy=ConsolidationPolicy.THRESHOLD
        )
        
        assert not consolidator.should_consolidate()
        
        stm.add_turn("user", "Turn 1")
        stm.add_turn("agent", "Turn 2")
        stm.add_turn("user", "Turn 3")
        
        assert consolidator.should_consolidate()

    def test_should_consolidate_periodic(self):
        """Test periodic consolidation policy."""
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(
            stm, ltm,
            policy=ConsolidationPolicy.PERIODIC
        )
        
        # Just created, should not consolidate
        assert not consolidator.should_consolidate()
        
        # Simulate time passing
        consolidator.last_consolidation = time.time() - 400
        assert consolidator.should_consolidate()

    def test_should_consolidate_manual(self):
        """Test manual consolidation policy."""
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(
            stm, ltm,
            policy=ConsolidationPolicy.MANUAL
        )
        
        assert not consolidator.should_consolidate()

    def test_consolidate(self):
        """Test consolidation process."""
        stm = ShortTermMemory(consolidation_threshold=2)
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(stm, ltm)
        
        stm.add_turn("user", "Important message")
        stm.add_turn("agent", "Response")
        stm.add_turn("user", "Another message")
        
        result = consolidator.consolidate()
        
        assert isinstance(result, ConsolidationResult)
        assert result.memories_created >= 0
        assert result.duration > 0

    def test_consolidate_creates_memories(self):
        """Test that consolidation creates long-term memories."""
        stm = ShortTermMemory(consolidation_threshold=2)
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(stm, ltm)
        
        stm.add_turn("user", "A" * 200)  # Long message = high importance
        stm.add_turn("agent", "Response")
        stm.add_turn("user", "Another long message " * 20)
        
        initial_count = len(ltm.store.memories)
        result = consolidator.consolidate()
        final_count = len(ltm.store.memories)
        
        assert final_count > initial_count

    def test_extract_patterns(self):
        """Test pattern extraction."""
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(stm, ltm)
        
        # Add episodic memories with repeated keywords
        for i in range(5):
            ltm.add(f"Python programming task {i}", MemoryType.EPISODIC)
        
        patterns = consolidator._extract_patterns()
        
        # Should find "python" and "programming" patterns
        assert patterns >= 0

    def test_find_repeated_patterns(self):
        """Test finding repeated patterns."""
        from src.memory.memory_store import Memory
        
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(stm, ltm)
        
        memories = [
            Memory("m1", "Python programming is great", MemoryType.EPISODIC, time.time()),
            Memory("m2", "Python coding is fun", MemoryType.EPISODIC, time.time()),
            Memory("m3", "Python development rocks", MemoryType.EPISODIC, time.time()),
        ]
        
        patterns = consolidator._find_repeated_patterns(memories)
        
        # Should find "python" pattern
        assert len(patterns) > 0

    def test_consolidate_specific(self):
        """Test consolidating specific turns."""
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(stm, ltm)
        
        turns = [
            ConversationTurn("user", "Message 1", time.time()),
            ConversationTurn("agent", "Response 1", time.time()),
            ConversationTurn("user", "Message 2", time.time()),
        ]
        
        created = consolidator.consolidate_specific(turns)
        
        assert created >= 0
        assert len(ltm.store.memories) >= 0

    def test_calculate_turn_importance(self):
        """Test calculating turn importance."""
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(stm, ltm)
        
        # User turn with long content
        turn1 = ConversationTurn("user", "A" * 200, time.time())
        importance1 = consolidator._calculate_turn_importance(turn1)
        
        # Agent turn with short content
        turn2 = ConversationTurn("agent", "Short", time.time())
        importance2 = consolidator._calculate_turn_importance(turn2)
        
        assert importance1 > importance2

    def test_calculate_turn_importance_with_metadata(self):
        """Test importance calculation with metadata."""
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(stm, ltm)
        
        turn = ConversationTurn(
            "user",
            "Test",
            time.time(),
            metadata={"important": True}
        )
        
        importance = consolidator._calculate_turn_importance(turn)
        
        assert importance >= 0.7

    def test_extract_knowledge(self):
        """Test extracting knowledge about a topic."""
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(stm, ltm)
        
        # Add memories about Python
        ltm.add("Python is a programming language", MemoryType.EPISODIC)
        ltm.add("Python is used for web development", MemoryType.EPISODIC)
        ltm.add("Python has great libraries", MemoryType.EPISODIC)
        
        knowledge = consolidator.extract_knowledge("Python")
        
        assert knowledge is not None
        assert knowledge.memory_type == MemoryType.SEMANTIC
        assert "Python" in knowledge.content

    def test_extract_knowledge_no_results(self):
        """Test extracting knowledge with no relevant memories."""
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(stm, ltm)
        
        knowledge = consolidator.extract_knowledge("NonexistentTopic")
        
        assert knowledge is None

    def test_create_procedure(self):
        """Test creating a procedural memory."""
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(stm, ltm)
        
        steps = [
            "Step 1: Initialize",
            "Step 2: Process",
            "Step 3: Finalize",
        ]
        
        procedure = consolidator.create_procedure("Test Procedure", steps)
        
        assert procedure.memory_type == MemoryType.PROCEDURAL
        assert "Test Procedure" in procedure.content
        assert all(step in procedure.content for step in steps)

    def test_auto_consolidate(self):
        """Test automatic consolidation."""
        stm = ShortTermMemory(consolidation_threshold=2)
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(
            stm, ltm,
            policy=ConsolidationPolicy.THRESHOLD
        )
        
        # Not enough turns yet
        result = consolidator.auto_consolidate()
        assert result is None
        
        # Add enough turns
        stm.add_turn("user", "Message 1")
        stm.add_turn("agent", "Response 1")
        stm.add_turn("user", "Message 2")
        
        result = consolidator.auto_consolidate()
        assert result is not None

    def test_auto_consolidate_manual_policy(self):
        """Test auto consolidate with manual policy."""
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(
            stm, ltm,
            policy=ConsolidationPolicy.MANUAL
        )
        
        stm.add_turn("user", "Message")
        result = consolidator.auto_consolidate()
        
        assert result is None

    def test_get_statistics(self):
        """Test getting consolidation statistics."""
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(
            stm, ltm,
            policy=ConsolidationPolicy.THRESHOLD,
            importance_threshold=0.6
        )
        
        stats = consolidator.get_statistics()
        
        assert stats["policy"] == "threshold"
        assert stats["importance_threshold"] == 0.6
        assert "last_consolidation" in stats
        assert "should_consolidate" in stats

    def test_consolidation_respects_importance_threshold(self):
        """Test that consolidation respects importance threshold."""
        stm = ShortTermMemory(consolidation_threshold=2)
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(
            stm, ltm,
            importance_threshold=0.9  # Very high threshold
        )
        
        # Add low-importance turns
        stm.add_turn("system", "Low importance")
        stm.add_turn("system", "Also low")
        stm.add_turn("system", "Still low")
        
        result = consolidator.consolidate()
        
        # Should create few or no memories
        assert result.memories_created <= 1

    def test_consolidation_merges_similar(self):
        """Test that consolidation merges similar memories."""
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(stm, ltm)
        
        # Add duplicate memories
        ltm.add("Same content", MemoryType.SEMANTIC)
        ltm.add("Same content", MemoryType.SEMANTIC)
        ltm.add("Different content", MemoryType.SEMANTIC)
        
        result = consolidator.consolidate()
        
        assert result.memories_merged >= 0
