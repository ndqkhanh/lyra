"""Tests for agent base classes."""

import asyncio

import pytest
from lyra_core.orchestration.agent_base import (
    AgentMetadata,
    AgentRole,
    AgentStatus,
    BaseAgent,
)
from lyra_core.orchestration.message_bus import InMemoryMessageBus
from lyra_core.orchestration.protocol import Message, MessageType


class TestAgent(BaseAgent):
    """Concrete agent implementation for testing."""

    def __init__(self, metadata: AgentMetadata, message_bus: InMemoryMessageBus):
        super().__init__(metadata, message_bus)
        self.started = False
        self.stopped = False
        self.messages_received: list[Message] = []
        self.errors: list[Exception] = []

    async def on_start(self) -> None:
        self.started = True

    async def on_stop(self) -> None:
        self.stopped = True

    async def on_message(self, message: Message) -> None:
        self.messages_received.append(message)

    async def on_error(self, error: Exception, message: Message | None = None) -> None:
        self.errors.append(error)


@pytest.fixture
def message_bus() -> InMemoryMessageBus:
    """Create a message bus for testing."""
    return InMemoryMessageBus()


@pytest.fixture
def agent_metadata() -> AgentMetadata:
    """Create agent metadata for testing."""
    return AgentMetadata.create(
        agent_id="test-agent-1",
        role=AgentRole.ENGINEER,
        team_id="team-1",
        capabilities=["coding", "testing"],
        config={"model": "claude-sonnet-4"},
    )


class TestAgentRole:
    """Tests for AgentRole enum."""

    def test_agent_roles(self) -> None:
        """Test all agent roles are defined."""
        assert AgentRole.PM.value == "product_manager"
        assert AgentRole.LEAD.value == "lead_engineer"
        assert AgentRole.PRINCIPAL.value == "principal_engineer"
        assert AgentRole.QA.value == "qa_engineer"
        assert AgentRole.SPEC.value == "spec_kit_specialist"
        assert AgentRole.RESEARCH.value == "research_agent"
        assert AgentRole.ENGINEER.value == "engineer"
        assert AgentRole.WRITER.value == "writer"


class TestAgentStatus:
    """Tests for AgentStatus enum."""

    def test_agent_statuses(self) -> None:
        """Test all agent statuses are defined."""
        assert AgentStatus.IDLE.value == "idle"
        assert AgentStatus.BUSY.value == "busy"
        assert AgentStatus.WAITING.value == "waiting"
        assert AgentStatus.ERROR.value == "error"
        assert AgentStatus.STOPPED.value == "stopped"


class TestAgentMetadata:
    """Tests for AgentMetadata dataclass."""

    def test_create_metadata(self) -> None:
        """Test creating agent metadata."""
        metadata = AgentMetadata.create(
            agent_id="agent-1",
            role=AgentRole.PM,
            team_id="team-1",
            capabilities=["requirements", "prd"],
            config={"model": "claude-opus-4"},
        )

        assert metadata.agent_id == "agent-1"
        assert metadata.role == AgentRole.PM
        assert metadata.team_id == "team-1"
        assert metadata.capabilities == ("requirements", "prd")
        assert metadata.config == {"model": "claude-opus-4"}
        assert metadata.spawned_at is not None

    def test_metadata_immutability(self) -> None:
        """Test that metadata is immutable."""
        metadata = AgentMetadata.create(
            agent_id="agent-1",
            role=AgentRole.QA,
            team_id="team-1",
            capabilities=["testing"],
        )

        with pytest.raises(AttributeError):
            metadata.agent_id = "agent-2"  # type: ignore

    def test_capabilities_as_tuple(self) -> None:
        """Test that capabilities are stored as immutable tuple."""
        metadata = AgentMetadata.create(
            agent_id="agent-1",
            role=AgentRole.ENGINEER,
            team_id="team-1",
            capabilities=["coding", "review"],
        )

        assert isinstance(metadata.capabilities, tuple)
        assert metadata.capabilities == ("coding", "review")


class TestBaseAgent:
    """Tests for BaseAgent class."""

    @pytest.mark.asyncio
    async def test_agent_initialization(
        self,
        agent_metadata: AgentMetadata,
        message_bus: InMemoryMessageBus,
    ) -> None:
        """Test agent initialization."""
        agent = TestAgent(agent_metadata, message_bus)

        assert agent.agent_id == "test-agent-1"
        assert agent.role == AgentRole.ENGINEER
        assert agent.team_id == "team-1"
        assert agent.status == AgentStatus.IDLE
        assert agent.current_task is None

    @pytest.mark.asyncio
    async def test_agent_start(
        self,
        agent_metadata: AgentMetadata,
        message_bus: InMemoryMessageBus,
    ) -> None:
        """Test starting an agent."""
        agent = TestAgent(agent_metadata, message_bus)
        await agent.start()

        assert agent.started is True
        assert await message_bus.get_subscriber_count() == 1

    @pytest.mark.asyncio
    async def test_agent_stop(
        self,
        agent_metadata: AgentMetadata,
        message_bus: InMemoryMessageBus,
    ) -> None:
        """Test stopping an agent."""
        agent = TestAgent(agent_metadata, message_bus)
        await agent.start()
        await agent.stop()

        assert agent.stopped is True
        assert agent.status == AgentStatus.STOPPED

    @pytest.mark.asyncio
    async def test_agent_receive_message(
        self,
        agent_metadata: AgentMetadata,
        message_bus: InMemoryMessageBus,
    ) -> None:
        """Test agent receiving a message."""
        agent = TestAgent(agent_metadata, message_bus)
        await agent.start()

        # Send message to agent
        message = Message.create(
            type=MessageType.TASK,
            sender="orchestrator",
            receiver=agent.agent_id,
            payload={"task": "implement_feature"},
        )
        await message_bus.publish(message)

        # Wait for message processing
        await asyncio.sleep(0.1)

        assert len(agent.messages_received) == 1
        assert agent.messages_received[0].id == message.id

    @pytest.mark.asyncio
    async def test_agent_send_message(
        self,
        agent_metadata: AgentMetadata,
        message_bus: InMemoryMessageBus,
    ) -> None:
        """Test agent sending a message."""
        agent = TestAgent(agent_metadata, message_bus)
        await agent.start()

        # Create another agent to receive
        receiver_metadata = AgentMetadata.create(
            agent_id="receiver",
            role=AgentRole.QA,
            team_id="team-1",
            capabilities=["testing"],
        )
        receiver = TestAgent(receiver_metadata, message_bus)
        await receiver.start()

        # Send message
        message = Message.create(
            type=MessageType.EVENT,
            sender=agent.agent_id,
            receiver="receiver",
            payload={"event": "code_complete"},
        )
        await agent.send_message(message)

        # Wait for message processing
        await asyncio.sleep(0.1)

        assert len(receiver.messages_received) == 1

    @pytest.mark.asyncio
    async def test_agent_request_response(
        self,
        agent_metadata: AgentMetadata,
        message_bus: InMemoryMessageBus,
    ) -> None:
        """Test agent request-response pattern."""
        agent = TestAgent(agent_metadata, message_bus)
        await agent.start()

        # Create responder agent
        responder_metadata = AgentMetadata.create(
            agent_id="responder",
            role=AgentRole.LEAD,
            team_id="team-1",
            capabilities=["review"],
        )

        class ResponderAgent(TestAgent):
            async def on_message(self, message: Message) -> None:
                await super().on_message(message)
                if message.type == MessageType.REQUEST:
                    await self.send_response(message, {"status": "approved"})

        responder = ResponderAgent(responder_metadata, message_bus)
        await responder.start()

        # Send request
        response = await agent.send_request(
            receiver="responder",
            payload={"action": "review_code"},
            timeout=5.0,
        )

        assert response.type == MessageType.RESPONSE
        assert response.payload["status"] == "approved"

    @pytest.mark.asyncio
    async def test_agent_status_transitions(
        self,
        agent_metadata: AgentMetadata,
        message_bus: InMemoryMessageBus,
    ) -> None:
        """Test agent status transitions."""
        agent = TestAgent(agent_metadata, message_bus)

        assert agent.status == AgentStatus.IDLE

        agent._set_status(AgentStatus.BUSY)
        assert agent.status == AgentStatus.BUSY

        agent._set_status(AgentStatus.WAITING)
        assert agent.status == AgentStatus.WAITING

        agent._set_status(AgentStatus.IDLE)
        assert agent.status == AgentStatus.IDLE

    @pytest.mark.asyncio
    async def test_agent_current_task(
        self,
        agent_metadata: AgentMetadata,
        message_bus: InMemoryMessageBus,
    ) -> None:
        """Test setting and clearing current task."""
        agent = TestAgent(agent_metadata, message_bus)

        assert agent.current_task is None

        task = {"task_id": "task-1", "description": "Implement feature"}
        agent._set_current_task(task)
        assert agent.current_task == task

        agent._set_current_task(None)
        assert agent.current_task is None

    @pytest.mark.asyncio
    async def test_agent_error_handling(
        self,
        agent_metadata: AgentMetadata,
        message_bus: InMemoryMessageBus,
    ) -> None:
        """Test agent error handling."""

        class ErrorAgent(TestAgent):
            async def on_message(self, message: Message) -> None:
                raise ValueError("Test error")

        agent = ErrorAgent(agent_metadata, message_bus)
        await agent.start()

        # Send message that will cause error
        message = Message.create(
            type=MessageType.TASK,
            sender="orchestrator",
            receiver=agent.agent_id,
            payload={},
        )
        await message_bus.publish(message)

        # Wait for error processing
        await asyncio.sleep(0.1)

        assert agent.status == AgentStatus.ERROR
        assert len(agent.errors) == 1
        assert isinstance(agent.errors[0], ValueError)

    @pytest.mark.asyncio
    async def test_multiple_agents_communication(
        self,
        message_bus: InMemoryMessageBus,
    ) -> None:
        """Test multiple agents communicating."""
        # Create multiple agents
        agents = []
        for i in range(3):
            metadata = AgentMetadata.create(
                agent_id=f"agent-{i}",
                role=AgentRole.ENGINEER,
                team_id="team-1",
                capabilities=["coding"],
            )
            agent = TestAgent(metadata, message_bus)
            await agent.start()
            agents.append(agent)

        # Agent 0 broadcasts to all
        message = Message.create(
            type=MessageType.EVENT,
            sender="agent-0",
            receiver="broadcast",
            payload={"event": "meeting_started"},
        )
        await agents[0].send_message(message)

        # Wait for message processing
        await asyncio.sleep(0.1)

        # Agent 0 should not receive its own broadcast
        assert len(agents[0].messages_received) == 0
        # Other agents should receive it
        assert len(agents[1].messages_received) == 1
        assert len(agents[2].messages_received) == 1
