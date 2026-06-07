"""
Tests for unified agent registry.
"""

import pytest

from lyra.agents.base import Agent, AgentCapability
from lyra.agents.unified_registry import (
    AgentMetadata,
    AgentSource,
    UnifiedAgentRegistry,
)
from lyra.core.task import Result, Task, TaskType


class MockAgent(Agent):
    """Mock agent for testing."""

    def __init__(self, agent_id: str):
        super().__init__(agent_id)

    async def execute(self, task: Task) -> Result:
        return Result(
            task_id=task.task_id,
            agent_id=self.agent_id,
            success=True,
            data={"message": "Mock execution"},
        )

    def can_handle(self, task: Task) -> float:
        return 0.8


class TestAgentMetadata:
    """Tests for AgentMetadata class."""

    def test_metadata_creation(self):
        """Test creating agent metadata."""
        agent = MockAgent("test-agent")
        capability = AgentCapability(
            name="test",
            description="Test capability",
            task_types=[TaskType.CODE_GENERATION],
        )

        metadata = AgentMetadata(
            agent=agent,
            source=AgentSource.LYRA,
            namespace="lyra:test-agent",
            capabilities=[capability],
            languages={"python"},
            frameworks={"pytest"},
            priority=5,
        )

        assert metadata.agent == agent
        assert metadata.source == AgentSource.LYRA
        assert metadata.qualified_name == "lyra:test-agent"
        assert len(metadata.capabilities) == 1
        assert "python" in metadata.languages

    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        agent = MockAgent("test-agent")
        metadata = AgentMetadata(
            agent=agent,
            source=AgentSource.LYRA,
            namespace="lyra:test-agent",
            capabilities=[],
        )

        # No usage
        assert metadata.success_rate == 0.0

        # With usage
        metadata.usage_count = 10
        metadata.success_count = 8
        assert metadata.success_rate == 0.8


class TestUnifiedAgentRegistry:
    """Tests for UnifiedAgentRegistry class."""

    def test_registry_creation(self):
        """Test creating a registry."""
        registry = UnifiedAgentRegistry()
        assert len(registry.agents) == 0

    def test_register_agent(self):
        """Test registering an agent."""
        registry = UnifiedAgentRegistry()
        agent = MockAgent("test-agent")
        capability = AgentCapability(
            name="coding",
            description="Code generation",
            task_types=[TaskType.CODE_GENERATION],
        )

        qualified_name = registry.register(
            agent=agent,
            source=AgentSource.LYRA,
            capabilities=[capability],
            languages={"python"},
            frameworks={"pytest"},
            priority=5,
        )

        assert qualified_name == "lyra:test-agent"
        assert len(registry.agents) == 1
        assert qualified_name in registry.agents

    def test_unregister_agent(self):
        """Test unregistering an agent."""
        registry = UnifiedAgentRegistry()
        agent = MockAgent("test-agent")
        capability = AgentCapability(
            name="coding",
            description="Code generation",
            task_types=[TaskType.CODE_GENERATION],
        )

        qualified_name = registry.register(
            agent=agent,
            source=AgentSource.LYRA,
            capabilities=[capability],
        )

        assert registry.unregister(qualified_name)
        assert len(registry.agents) == 0
        assert not registry.unregister("nonexistent")

    def test_get_agent(self):
        """Test getting an agent."""
        registry = UnifiedAgentRegistry()
        agent = MockAgent("test-agent")
        capability = AgentCapability(
            name="coding",
            description="Code generation",
            task_types=[TaskType.CODE_GENERATION],
        )

        qualified_name = registry.register(
            agent=agent,
            source=AgentSource.LYRA,
            capabilities=[capability],
        )

        retrieved = registry.get(qualified_name)
        assert retrieved is not None
        assert retrieved.agent_id == "test-agent"
        assert registry.get("nonexistent") is None

    def test_find_candidates(self):
        """Test finding candidate agents."""
        registry = UnifiedAgentRegistry()

        # Register multiple agents
        agent1 = MockAgent("agent1")
        capability1 = AgentCapability(
            name="coding",
            description="Code generation",
            task_types=[TaskType.CODE_GENERATION],
        )
        registry.register(
            agent=agent1,
            source=AgentSource.LYRA,
            capabilities=[capability1],
            languages={"python"},
        )

        agent2 = MockAgent("agent2")
        capability2 = AgentCapability(
            name="testing",
            description="Test generation",
            task_types=[TaskType.TEST_GENERATION],
        )
        registry.register(
            agent=agent2,
            source=AgentSource.ECC,
            capabilities=[capability2],
            languages={"python"},
        )

        # Find by task type
        task = Task(
            task_id="test-task",
            type=TaskType.CODE_GENERATION,
            description="Generate code",
        )
        candidates = registry.find_candidates(task)
        assert len(candidates) == 1
        assert candidates[0].agent.agent_id == "agent1"

        # Find with language filter
        candidates = registry.find_candidates(task, language="python")
        assert len(candidates) == 1

    def test_dispatch(self):
        """Test dispatching a task."""
        registry = UnifiedAgentRegistry()

        agent = MockAgent("test-agent")
        capability = AgentCapability(
            name="coding",
            description="Code generation",
            task_types=[TaskType.CODE_GENERATION],
        )
        registry.register(
            agent=agent,
            source=AgentSource.LYRA,
            capabilities=[capability],
            priority=10,
        )

        task = Task(
            task_id="test-task",
            type=TaskType.CODE_GENERATION,
            description="Generate code",
        )

        dispatched = registry.dispatch(task)
        assert dispatched is not None
        assert dispatched.agent_id == "test-agent"

        # Check usage count incremented
        metadata = registry.agents["lyra:test-agent"]
        assert metadata.usage_count == 1

    def test_dispatch_with_preference(self):
        """Test dispatching with source preference."""
        registry = UnifiedAgentRegistry()

        # Register Lyra agent
        agent1 = MockAgent("lyra-agent")
        capability1 = AgentCapability(
            name="coding",
            description="Code generation",
            task_types=[TaskType.CODE_GENERATION],
        )
        registry.register(
            agent=agent1,
            source=AgentSource.LYRA,
            capabilities=[capability1],
            priority=5,
        )

        # Register ECC agent with same capability
        agent2 = MockAgent("ecc-agent")
        capability2 = AgentCapability(
            name="coding",
            description="Code generation",
            task_types=[TaskType.CODE_GENERATION],
        )
        registry.register(
            agent=agent2,
            source=AgentSource.ECC,
            capabilities=[capability2],
            priority=5,
        )

        task = Task(
            task_id="test-task",
            type=TaskType.CODE_GENERATION,
            description="Generate code",
        )

        # Prefer ECC
        dispatched = registry.dispatch(task, prefer_source=AgentSource.ECC)
        assert dispatched is not None
        assert dispatched.agent_id == "ecc-agent"

    def test_record_success(self):
        """Test recording successful execution."""
        registry = UnifiedAgentRegistry()

        agent = MockAgent("test-agent")
        capability = AgentCapability(
            name="coding",
            description="Code generation",
            task_types=[TaskType.CODE_GENERATION],
        )
        qualified_name = registry.register(
            agent=agent,
            source=AgentSource.LYRA,
            capabilities=[capability],
        )

        registry.record_success(qualified_name)
        metadata = registry.agents[qualified_name]
        assert metadata.success_count == 1

    def test_get_statistics(self):
        """Test getting registry statistics."""
        registry = UnifiedAgentRegistry()

        # Register agents
        agent1 = MockAgent("agent1")
        capability1 = AgentCapability(
            name="coding",
            description="Code generation",
            task_types=[TaskType.CODE_GENERATION],
        )
        registry.register(
            agent=agent1,
            source=AgentSource.LYRA,
            capabilities=[capability1],
            languages={"python"},
        )

        agent2 = MockAgent("agent2")
        capability2 = AgentCapability(
            name="testing",
            description="Test generation",
            task_types=[TaskType.TEST_GENERATION],
        )
        registry.register(
            agent=agent2,
            source=AgentSource.ECC,
            capabilities=[capability2],
            languages={"javascript"},
        )

        stats = registry.get_statistics()
        assert stats["total_agents"] == 2
        assert stats["by_source"]["lyra"] == 1
        assert stats["by_source"]["ecc"] == 1
        assert "code_generation" in stats["by_capability"]
        assert "python" in stats["by_language"]

    def test_list_agents(self):
        """Test listing agents."""
        registry = UnifiedAgentRegistry()

        # Register agents
        agent1 = MockAgent("agent1")
        capability1 = AgentCapability(
            name="coding",
            description="Code generation",
            task_types=[TaskType.CODE_GENERATION],
        )
        registry.register(
            agent=agent1,
            source=AgentSource.LYRA,
            capabilities=[capability1],
            languages={"python"},
        )

        agent2 = MockAgent("agent2")
        capability2 = AgentCapability(
            name="testing",
            description="Test generation",
            task_types=[TaskType.TEST_GENERATION],
        )
        registry.register(
            agent=agent2,
            source=AgentSource.ECC,
            capabilities=[capability2],
            languages={"javascript"},
        )

        # List all
        all_agents = registry.list_agents()
        assert len(all_agents) == 2

        # Filter by source
        lyra_agents = registry.list_agents(source=AgentSource.LYRA)
        assert len(lyra_agents) == 1
        assert lyra_agents[0].agent.agent_id == "agent1"

        # Filter by language
        python_agents = registry.list_agents(language="python")
        assert len(python_agents) == 1

    def test_clear(self):
        """Test clearing registry."""
        registry = UnifiedAgentRegistry()

        agent = MockAgent("test-agent")
        capability = AgentCapability(
            name="coding",
            description="Code generation",
            task_types=[TaskType.CODE_GENERATION],
        )
        registry.register(
            agent=agent,
            source=AgentSource.LYRA,
            capabilities=[capability],
        )

        registry.clear()
        assert len(registry.agents) == 0
        assert len(registry._capability_index) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
