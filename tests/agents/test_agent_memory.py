"""
Tests for memory-integrated Agent base class.
"""

import asyncio
import pytest
import tempfile
import os
from pathlib import Path

from src.agents.base import Agent, AgentCapability, AgentStatus
from src.core.task import Task, TaskType, Result
from src.memory import MemoryType, RetrievalStrategy


class TestAgent(Agent):
    """Concrete test agent for testing."""

    async def execute(self, task: Task) -> Result:
        """Execute a task."""
        self.status = AgentStatus.BUSY
        self.current_task = task
        
        # Simulate work
        await asyncio.sleep(0.01)
        
        result = Result(
            task_id=task.task_id,
            success=True,
            data={"result": "completed"},
            agent_id=self.agent_id,
        )
        
        self.record_execution(result)
        self.status = AgentStatus.IDLE
        self.current_task = None
        
        return result

    def can_handle(self, task: Task) -> float:
        """Check if agent can handle task."""
        capability = self.get_capability(task.type)
        return capability.confidence if capability else 0.0


class TestMemoryIntegratedAgent:
    """Test memory integration in Agent base class."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for memory storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create data/memory directory
            memory_dir = Path(tmpdir) / "data" / "memory"
            memory_dir.mkdir(parents=True, exist_ok=True)
            
            # Change to temp directory
            old_cwd = os.getcwd()
            os.chdir(tmpdir)
            
            yield tmpdir
            
            # Restore directory
            os.chdir(old_cwd)

    @pytest.fixture
    def agent(self, temp_dir):
        """Create a test agent."""
        capabilities = [
            AgentCapability(
                name="test",
                description="Test capability",
                task_types=[TaskType.CODE_GENERATION],
                confidence=0.9,
            )
        ]
        return TestAgent("test_agent", capabilities)

    def test_agent_has_memory_components(self, agent):
        """Test that agent has memory system components."""
        assert agent.short_term_memory is not None
        assert agent.long_term_memory is not None
        assert agent.memory_retriever is not None
        assert agent.memory_consolidator is not None

    def test_remember(self, agent):
        """Test storing memories."""
        agent.remember(
            "Python uses indentation",
            memory_type=MemoryType.SEMANTIC,
            importance=0.8,
            tags=["python", "syntax"],
        )
        
        # Verify memory was stored
        stats = agent.long_term_memory.get_statistics()
        assert stats["total_memories"] == 1

    def test_recall(self, agent):
        """Test retrieving memories."""
        # Add some memories
        agent.remember("Python uses indentation", MemoryType.SEMANTIC, tags=["python"])
        agent.remember("Python has dynamic typing", MemoryType.SEMANTIC, tags=["python"])
        agent.remember("JavaScript uses braces", MemoryType.SEMANTIC, tags=["javascript"])
        
        # Recall Python-related memories with lower threshold
        results = agent.recall("Python", limit=5, min_score=0.3)
        
        assert len(results) >= 2
        assert any("Python" in r.memory.content for r in results)

    def test_recall_with_filters(self, agent):
        """Test recall with filters."""
        agent.remember("Python fact", MemoryType.SEMANTIC, tags=["python"])
        agent.remember("Python event", MemoryType.EPISODIC, tags=["python"])
        
        # Filter by type
        results = agent.recall(
            "Python",
            filters={"type": MemoryType.SEMANTIC}
        )
        
        assert len(results) == 1
        assert results[0].memory.memory_type == MemoryType.SEMANTIC

    def test_add_conversation_turn(self, agent):
        """Test adding conversation turns."""
        agent.add_conversation_turn("user", "Hello!")
        agent.add_conversation_turn("agent", "Hi! How can I help?")
        
        stats = agent.short_term_memory.get_statistics()
        assert stats["total_turns"] == 2

    def test_get_conversation_context(self, agent):
        """Test getting conversation context."""
        agent.add_conversation_turn("user", "What is Python?")
        agent.add_conversation_turn("agent", "Python is a programming language.")
        
        context = agent.get_conversation_context(max_turns=2)
        
        assert "user: What is Python?" in context
        assert "agent: Python is a programming language." in context

    def test_auto_consolidation(self, agent):
        """Test automatic memory consolidation."""
        # Add enough turns to trigger consolidation
        for i in range(6):
            agent.add_conversation_turn("user", f"Message {i}")
        
        # Check that consolidation happened
        ltm_stats = agent.long_term_memory.get_statistics()
        assert ltm_stats["total_memories"] > 0

    def test_manual_consolidation(self, agent):
        """Test manual memory consolidation."""
        # Add some turns
        agent.add_conversation_turn("user", "Important message")
        agent.add_conversation_turn("agent", "Noted")
        
        # Manually consolidate
        result = agent.consolidate_memories()
        
        # Should not consolidate if threshold not met
        # (threshold is 5, we only added 2)
        assert result is None

    def test_working_memory(self, agent):
        """Test working memory operations."""
        agent.set_working_memory("current_task", "testing")
        agent.set_working_memory("step", 1)
        
        assert agent.get_working_memory("current_task") == "testing"
        assert agent.get_working_memory("step") == 1
        assert agent.get_working_memory("nonexistent", "default") == "default"

    def test_save_and_load_memories(self, agent):
        """Test saving and loading memories."""
        # Add memories
        agent.remember("Test memory 1", MemoryType.SEMANTIC)
        agent.remember("Test memory 2", MemoryType.EPISODIC)
        
        # Save
        agent.save_memories()
        
        # Create new agent with same ID
        new_agent = TestAgent("test_agent", [])
        
        # Load memories
        new_agent.load_memories()
        
        # Verify memories loaded
        stats = new_agent.long_term_memory.get_statistics()
        assert stats["total_memories"] == 2

    def test_memory_statistics(self, agent):
        """Test getting memory statistics."""
        agent.remember("Test", MemoryType.SEMANTIC)
        agent.add_conversation_turn("user", "Hello")
        
        stats = agent.get_memory_statistics()
        
        assert "short_term" in stats
        assert "long_term" in stats
        assert "consolidation" in stats
        
        assert stats["short_term"]["total_turns"] == 1
        assert stats["long_term"]["total_memories"] == 1

    def test_memory_with_task_execution(self, agent):
        """Test memory integration with task execution."""
        # Create and execute task
        task = Task(
            task_id="test_task",
            type=TaskType.CODE_GENERATION,
            description="Generate code",
            priority=1,
        )
        
        # Add conversation about the task
        agent.add_conversation_turn("user", "Please generate code for sorting")
        
        # Execute task
        result = asyncio.run(agent.execute(task))
        
        # Remember the result
        agent.remember(
            f"Completed task: {task.description}",
            memory_type=MemoryType.EPISODIC,
            importance=0.7,
            tags=["task", "code_generation"],
        )
        
        # Recall task-related memories
        memories = agent.recall("code generation", limit=5, min_score=0.3)
        
        assert len(memories) > 0
        assert any("task" in m.memory.content.lower() for m in memories)

    def test_retrieval_strategies(self, agent):
        """Test different retrieval strategies."""
        # Add memories
        agent.remember("Recent Python info", MemoryType.SEMANTIC, importance=0.5)
        agent.remember("Important Python info", MemoryType.SEMANTIC, importance=0.9)
        
        # Test keyword strategy
        results_keyword = agent.recall(
            "Python",
            strategy=RetrievalStrategy.KEYWORD,
        )
        
        # Test importance strategy
        results_importance = agent.recall(
            "Python",
            strategy=RetrievalStrategy.IMPORTANCE,
        )
        
        # Test hybrid strategy
        results_hybrid = agent.recall(
            "Python",
            strategy=RetrievalStrategy.HYBRID,
        )
        
        assert len(results_keyword) > 0
        assert len(results_importance) > 0
        assert len(results_hybrid) > 0

    def test_memory_with_metadata(self, agent):
        """Test conversation turns with metadata."""
        agent.add_conversation_turn(
            "user",
            "Important question",
            metadata={"important": True, "category": "question"}
        )
        
        turns = agent.short_term_memory.turns
        assert len(turns) == 1
        assert turns[0].metadata["important"] is True

    def test_memory_persistence_path(self, agent):
        """Test that memory files use agent ID."""
        # The path should include the agent ID
        expected_path = f"data/memory/{agent.agent_id}_ltm.json"
        assert agent.long_term_memory.store.storage_path == expected_path

    def test_multiple_agents_separate_memories(self, temp_dir):
        """Test that different agents have separate memories."""
        agent1 = TestAgent("agent1", [])
        agent2 = TestAgent("agent2", [])
        
        agent1.remember("Agent 1 memory", MemoryType.SEMANTIC)
        agent2.remember("Agent 2 memory", MemoryType.SEMANTIC)
        
        # Each agent should have only their own memory
        stats1 = agent1.long_term_memory.get_statistics()
        stats2 = agent2.long_term_memory.get_statistics()
        
        assert stats1["total_memories"] == 1
        assert stats2["total_memories"] == 1
        
        # Verify content
        results1 = agent1.recall("memory")
        results2 = agent2.recall("memory")
        
        assert "Agent 1" in results1[0].memory.content
        assert "Agent 2" in results2[0].memory.content
