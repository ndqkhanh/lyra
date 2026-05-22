"""
Tests for Task Allocator.
"""

import pytest
from src.coordination import TaskAllocator, AllocationStrategy
from src.agents import CodeAgent, ResearchAgent, TestAgent
from src.core.task import Task, TaskType, TaskPriority


class TestTaskAllocator:
    """Test TaskAllocator class."""

    def test_allocator_creation(self):
        """Test allocator creation."""
        allocator = TaskAllocator()
        
        assert allocator.strategy == AllocationStrategy.CAPABILITY_BASED
        assert len(allocator.allocation_history) == 0

    def test_allocator_with_strategy(self):
        """Test allocator with specific strategy."""
        allocator = TaskAllocator(strategy=AllocationStrategy.LOAD_BALANCED)
        
        assert allocator.strategy == AllocationStrategy.LOAD_BALANCED

    def test_allocate_by_capability(self):
        """Test allocation based on capability."""
        allocator = TaskAllocator(strategy=AllocationStrategy.CAPABILITY_BASED)
        
        agents = [CodeAgent(), ResearchAgent(), TestAgent()]
        task = Task(type=TaskType.CODE_GENERATION, description="Generate code")
        
        selected = allocator.allocate(task, agents)
        
        assert selected is not None
        assert selected.agent_id == "code_agent"

    def test_allocate_load_balanced(self):
        """Test load-balanced allocation."""
        allocator = TaskAllocator(strategy=AllocationStrategy.LOAD_BALANCED)
        
        agents = [CodeAgent(), ResearchAgent()]
        task = Task(type=TaskType.GENERIC, description="Generic task")
        
        selected = allocator.allocate(task, agents)
        
        assert selected is not None

    def test_allocate_with_exclusion(self):
        """Test allocation with excluded agents."""
        allocator = TaskAllocator()
        
        agents = [CodeAgent(), ResearchAgent(), TestAgent()]
        task = Task(type=TaskType.CODE_GENERATION, description="Generate code")
        
        selected = allocator.allocate(task, agents, exclude=["code_agent"])
        
        assert selected is not None
        assert selected.agent_id != "code_agent"

    def test_allocate_no_agents(self):
        """Test allocation with no agents."""
        allocator = TaskAllocator()
        
        task = Task(type=TaskType.GENERIC, description="Task")
        selected = allocator.allocate(task, [])
        
        assert selected is None

    def test_allocate_all_excluded(self):
        """Test allocation when all agents excluded."""
        allocator = TaskAllocator()
        
        agents = [CodeAgent(), ResearchAgent()]
        task = Task(type=TaskType.GENERIC, description="Task")
        
        selected = allocator.allocate(
            task,
            agents,
            exclude=["code_agent", "research_agent"]
        )
        
        assert selected is None

    def test_allocation_history(self):
        """Test allocation history tracking."""
        allocator = TaskAllocator()
        
        agents = [CodeAgent(), ResearchAgent()]
        
        for i in range(5):
            task = Task(type=TaskType.CODE_GENERATION, description=f"Task {i}")
            allocator.allocate(task, agents)
        
        assert len(allocator.allocation_history) == 5

    def test_allocation_history_limit(self):
        """Test allocation history is limited to 100."""
        allocator = TaskAllocator()
        
        agents = [CodeAgent()]
        
        for i in range(150):
            task = Task(type=TaskType.CODE_GENERATION, description=f"Task {i}")
            allocator.allocate(task, agents)
        
        assert len(allocator.allocation_history) == 100

    def test_get_statistics(self):
        """Test getting allocation statistics."""
        allocator = TaskAllocator()
        
        agents = [CodeAgent(), ResearchAgent()]
        
        for i in range(10):
            task = Task(type=TaskType.CODE_GENERATION, description=f"Task {i}")
            allocator.allocate(task, agents)
        
        stats = allocator.get_statistics()
        
        assert stats["total_allocations"] == 10
        assert stats["strategy"] == AllocationStrategy.CAPABILITY_BASED.value
        assert "average_score" in stats
        assert "allocations_by_agent" in stats

    def test_get_statistics_empty(self):
        """Test statistics with no allocations."""
        allocator = TaskAllocator()
        
        stats = allocator.get_statistics()
        
        assert stats["total_allocations"] == 0

    def test_set_strategy(self):
        """Test changing allocation strategy."""
        allocator = TaskAllocator()
        
        assert allocator.strategy == AllocationStrategy.CAPABILITY_BASED
        
        allocator.set_strategy(AllocationStrategy.LOAD_BALANCED)
        
        assert allocator.strategy == AllocationStrategy.LOAD_BALANCED

    def test_priority_based_allocation(self):
        """Test priority-based allocation."""
        allocator = TaskAllocator(strategy=AllocationStrategy.PRIORITY_FIRST)
        
        agents = [CodeAgent(), ResearchAgent()]
        
        high_priority = Task(
            type=TaskType.CODE_GENERATION,
            description="High priority",
            priority=TaskPriority.HIGH
        )
        
        selected = allocator.allocate(high_priority, agents)
        
        assert selected is not None

    def test_round_robin_strategy(self):
        """Test round-robin allocation."""
        allocator = TaskAllocator(strategy=AllocationStrategy.ROUND_ROBIN)
        
        agents = [CodeAgent(), ResearchAgent()]
        task = Task(type=TaskType.GENERIC, description="Task")
        
        selected = allocator.allocate(task, agents)
        
        assert selected is not None
