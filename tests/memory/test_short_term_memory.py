"""
Tests for Short-Term Memory.
"""

import pytest
import time

from src.memory.memory_store import MemoryStore, MemoryType
from src.memory.short_term_memory import ShortTermMemory, ConversationTurn


class TestConversationTurn:
    """Test ConversationTurn class."""

    def test_turn_creation(self):
        """Test creating a conversation turn."""
        turn = ConversationTurn(
            role="user",
            content="Hello",
            timestamp=time.time(),
        )
        
        assert turn.role == "user"
        assert turn.content == "Hello"
        assert turn.metadata == {}

    def test_turn_with_metadata(self):
        """Test creating a turn with metadata."""
        turn = ConversationTurn(
            role="agent",
            content="Hi there",
            timestamp=time.time(),
            metadata={"important": True},
        )
        
        assert turn.metadata["important"] is True


class TestShortTermMemory:
    """Test ShortTermMemory class."""

    def test_stm_creation(self):
        """Test creating short-term memory."""
        stm = ShortTermMemory(capacity=5)
        
        assert stm.capacity == 5
        assert len(stm.turns) == 0

    def test_add_turn(self):
        """Test adding a conversation turn."""
        stm = ShortTermMemory()
        
        turn = stm.add_turn("user", "Hello")
        
        assert turn.role == "user"
        assert turn.content == "Hello"
        assert len(stm.turns) == 1

    def test_capacity_limit(self):
        """Test that capacity is enforced."""
        stm = ShortTermMemory(capacity=3)
        
        stm.add_turn("user", "Turn 1")
        stm.add_turn("agent", "Turn 2")
        stm.add_turn("user", "Turn 3")
        stm.add_turn("agent", "Turn 4")
        
        assert len(stm.turns) == 3
        assert stm.turns[0].content == "Turn 2"

    def test_get_recent(self):
        """Test getting recent turns."""
        stm = ShortTermMemory()
        
        stm.add_turn("user", "Turn 1")
        stm.add_turn("agent", "Turn 2")
        stm.add_turn("user", "Turn 3")
        
        recent = stm.get_recent(limit=2)
        
        assert len(recent) == 2
        assert recent[0].content == "Turn 2"

    def test_get_recent_all(self):
        """Test getting all recent turns."""
        stm = ShortTermMemory()
        
        stm.add_turn("user", "Turn 1")
        stm.add_turn("agent", "Turn 2")
        
        recent = stm.get_recent()
        
        assert len(recent) == 2

    def test_get_context(self):
        """Test getting conversation context."""
        stm = ShortTermMemory()
        
        stm.add_turn("user", "Hello")
        stm.add_turn("agent", "Hi there")
        
        context = stm.get_context()
        
        assert "user: Hello" in context
        assert "agent: Hi there" in context

    def test_get_context_limited(self):
        """Test getting limited context."""
        stm = ShortTermMemory()
        
        stm.add_turn("user", "Turn 1")
        stm.add_turn("agent", "Turn 2")
        stm.add_turn("user", "Turn 3")
        
        context = stm.get_context(max_turns=2)
        
        assert "Turn 1" not in context
        assert "Turn 2" in context
        assert "Turn 3" in context

    def test_get_by_role(self):
        """Test getting turns by role."""
        stm = ShortTermMemory()
        
        stm.add_turn("user", "User 1")
        stm.add_turn("agent", "Agent 1")
        stm.add_turn("user", "User 2")
        
        user_turns = stm.get_by_role("user")
        
        assert len(user_turns) == 2
        assert all(t.role == "user" for t in user_turns)

    def test_working_memory(self):
        """Test working memory operations."""
        stm = ShortTermMemory()
        
        stm.set_working_memory("key1", "value1")
        stm.set_working_memory("key2", 42)
        
        assert stm.get_working_memory("key1") == "value1"
        assert stm.get_working_memory("key2") == 42
        assert stm.get_working_memory("key3", "default") == "default"

    def test_clear_working_memory(self):
        """Test clearing working memory."""
        stm = ShortTermMemory()
        
        stm.set_working_memory("key1", "value1")
        stm.clear_working_memory()
        
        assert stm.get_working_memory("key1") is None

    def test_should_consolidate(self):
        """Test consolidation trigger."""
        stm = ShortTermMemory(capacity=10, consolidation_threshold=3)
        
        assert not stm.should_consolidate()
        
        stm.add_turn("user", "Turn 1")
        stm.add_turn("agent", "Turn 2")
        assert not stm.should_consolidate()
        
        stm.add_turn("user", "Turn 3")
        assert stm.should_consolidate()

    def test_prepare_for_consolidation(self):
        """Test preparing turns for consolidation."""
        stm = ShortTermMemory()
        
        stm.add_turn("user", "Turn 1")
        stm.add_turn("agent", "Turn 2")
        stm.add_turn("user", "Turn 3")
        stm.add_turn("agent", "Turn 4")
        
        to_consolidate = stm.prepare_for_consolidation()
        
        assert len(to_consolidate) == 2
        assert to_consolidate[0].content == "Turn 1"

    def test_consolidate_to_long_term(self):
        """Test consolidating to long-term memory."""
        stm = ShortTermMemory(consolidation_threshold=2)
        long_term = MemoryStore()
        
        stm.add_turn("user", "Important message")
        stm.add_turn("agent", "Response")
        stm.add_turn("user", "Another message")
        
        consolidated = stm.consolidate_to_long_term(long_term)
        
        assert consolidated > 0
        assert len(long_term.memories) > 0

    def test_consolidate_importance_threshold(self):
        """Test consolidation respects importance threshold."""
        stm = ShortTermMemory(consolidation_threshold=2)
        long_term = MemoryStore()
        
        # Add low-importance turns
        stm.add_turn("system", "Low importance")
        stm.add_turn("system", "Also low")
        stm.add_turn("system", "Still low")
        
        consolidated = stm.consolidate_to_long_term(
            long_term,
            importance_threshold=0.8,
        )
        
        # Should consolidate few or none
        assert consolidated <= 1

    def test_calculate_importance(self):
        """Test importance calculation."""
        stm = ShortTermMemory()
        
        # User turn with long content
        turn1 = ConversationTurn(
            role="user",
            content="A" * 200,
            timestamp=time.time(),
        )
        importance1 = stm._calculate_importance(turn1)
        
        # Agent turn with short content
        turn2 = ConversationTurn(
            role="agent",
            content="Short",
            timestamp=time.time(),
        )
        importance2 = stm._calculate_importance(turn2)
        
        assert importance1 > importance2

    def test_calculate_importance_with_metadata(self):
        """Test importance calculation with metadata."""
        stm = ShortTermMemory()
        
        turn = ConversationTurn(
            role="user",
            content="Test",
            timestamp=time.time(),
            metadata={"important": True},
        )
        
        importance = stm._calculate_importance(turn)
        
        assert importance >= 0.7

    def test_clear(self):
        """Test clearing short-term memory."""
        stm = ShortTermMemory()
        
        stm.add_turn("user", "Turn 1")
        stm.add_turn("agent", "Turn 2")
        stm.set_working_memory("key", "value")
        
        stm.clear()
        
        assert len(stm.turns) == 0
        assert len(stm.working_memory) == 0

    def test_get_statistics(self):
        """Test getting statistics."""
        stm = ShortTermMemory(capacity=5, consolidation_threshold=3)
        
        stm.add_turn("user", "Turn 1")
        stm.add_turn("agent", "Turn 2")
        stm.set_working_memory("key", "value")
        
        stats = stm.get_statistics()
        
        assert stats["total_turns"] == 2
        assert stats["capacity"] == 5
        assert stats["utilization"] == 0.4
        assert stats["by_role"]["user"] == 1
        assert stats["by_role"]["agent"] == 1
        assert stats["working_memory_keys"] == 1
        assert not stats["should_consolidate"]

    def test_get_statistics_empty(self):
        """Test getting statistics for empty STM."""
        stm = ShortTermMemory()
        
        stats = stm.get_statistics()
        
        assert stats["total_turns"] == 0
        assert stats["utilization"] == 0.0
