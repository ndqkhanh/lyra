"""
Tests for agent base classes.
"""

import pytest
from src.agents.base import Agent, AgentCapability, AgentStatus, Message, MessageType
from src.core.task import Task, TaskType, Result


class MockAgent(Agent):
    """Mock agent for testing."""

    async def execute(self, task: Task) -> Result:
        """Mock execute method."""
        return Result(
            task_id=task.task_id,
            success=True,
            data="mock result",
            agent_id=self.agent_id,
        )

    def can_handle(self, task: Task) -> float:
        """Mock can_handle method."""
        return 0.8


class TestAgentCapability:
    """Test AgentCapability class."""

    def test_capability_creation(self):
        """Test capability creation."""
        cap = AgentCapability(
            name="test_capability",
            description="Test capability",
            task_types=[TaskType.CODE_GENERATION],
            confidence=0.9,
        )
        
        assert cap.name == "test_capability"
        assert cap.description == "Test capability"
        assert TaskType.CODE_GENERATION in cap.task_types
        assert cap.confidence == 0.9

    def test_capability_validation(self):
        """Test capability validation."""
        with pytest.raises(ValueError):
            AgentCapability(
                name="test",
                description="Test",
                task_types=[TaskType.GENERIC],
                confidence=1.5,  # Invalid confidence
            )


class TestAgent:
    """Test Agent base class."""

    def test_agent_creation(self):
        """Test agent creation."""
        agent = MockAgent("test_agent")
        
        assert agent.agent_id == "test_agent"
        assert agent.status == AgentStatus.IDLE
        assert agent.current_task is None
        assert len(agent.execution_history) == 0

    def test_agent_with_capabilities(self):
        """Test agent with capabilities."""
        cap = AgentCapability(
            name="test_cap",
            description="Test",
            task_types=[TaskType.CODE_GENERATION],
        )
        agent = MockAgent("test_agent", capabilities=[cap])
        
        assert len(agent.capabilities) == 1
        assert agent.capabilities[0].name == "test_cap"

    @pytest.mark.asyncio
    async def test_agent_execute(self):
        """Test agent task execution."""
        agent = MockAgent("test_agent")
        task = Task(type=TaskType.GENERIC, description="Test task")
        
        result = await agent.execute(task)
        
        assert result.success is True
        assert result.agent_id == "test_agent"
        assert result.task_id == task.task_id

    def test_agent_can_handle(self):
        """Test agent can_handle method."""
        agent = MockAgent("test_agent")
        task = Task(type=TaskType.GENERIC, description="Test task")
        
        confidence = agent.can_handle(task)
        
        assert confidence == 0.8

    def test_get_capability(self):
        """Test getting capability by task type."""
        cap = AgentCapability(
            name="code_gen",
            description="Generate code",
            task_types=[TaskType.CODE_GENERATION],
        )
        agent = MockAgent("test_agent", capabilities=[cap])
        
        found_cap = agent.get_capability(TaskType.CODE_GENERATION)
        assert found_cap is not None
        assert found_cap.name == "code_gen"
        
        not_found = agent.get_capability(TaskType.RESEARCH)
        assert not_found is None

    def test_record_execution(self):
        """Test recording execution results."""
        agent = MockAgent("test_agent")
        
        result = Result(
            task_id="task_1",
            success=True,
            data="output",
            agent_id="test_agent",
        )
        
        agent.record_execution(result)
        
        assert len(agent.execution_history) == 1
        assert agent.execution_history[0] == result

    def test_execution_history_limit(self):
        """Test execution history is limited to 100 entries."""
        agent = MockAgent("test_agent")
        
        # Add 150 results
        for i in range(150):
            result = Result(
                task_id=f"task_{i}",
                success=True,
                data="output",
                agent_id="test_agent",
            )
            agent.record_execution(result)
        
        # Should only keep last 100
        assert len(agent.execution_history) == 100

    def test_get_success_rate(self):
        """Test calculating success rate."""
        agent = MockAgent("test_agent")
        
        # Add some successful and failed results
        for i in range(8):
            agent.record_execution(
                Result(task_id=f"task_{i}", success=True, agent_id="test_agent")
            )
        
        for i in range(2):
            agent.record_execution(
                Result(
                    task_id=f"task_fail_{i}",
                    success=False,
                    error="Failed",
                    agent_id="test_agent",
                )
            )
        
        success_rate = agent.get_success_rate()
        assert success_rate == 0.8  # 8 out of 10

    def test_get_success_rate_empty(self):
        """Test success rate with no history."""
        agent = MockAgent("test_agent")
        
        success_rate = agent.get_success_rate()
        assert success_rate == 0.0


class TestMessage:
    """Test Message class."""

    def test_message_creation(self):
        """Test message creation."""
        msg = Message(
            from_agent="agent_1",
            to_agent="agent_2",
            message_type=MessageType.PROGRESS,
            content={"progress": 0.5},
        )
        
        assert msg.from_agent == "agent_1"
        assert msg.to_agent == "agent_2"
        assert msg.message_type == MessageType.PROGRESS
        assert msg.content["progress"] == 0.5
