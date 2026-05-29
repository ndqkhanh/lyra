"""Base classes for agents in the orchestration system.

Defines agent roles, status, metadata, and the abstract base agent class
that all specialized agents inherit from.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from lyra_core.orchestration.message_bus import MessageBus
from lyra_core.orchestration.protocol import Message


class AgentRole(Enum):
    """Role of an agent in the team."""

    PM = "product_manager"  # Product Manager
    LEAD = "lead_engineer"  # Lead Engineer
    PRINCIPAL = "principal_engineer"  # Principal Engineer
    QA = "qa_engineer"  # QA Engineer
    SPEC = "spec_kit_specialist"  # Spec-Kit Specialist
    RESEARCH = "research_agent"  # Research Agent
    ENGINEER = "engineer"  # Generic Engineer
    WRITER = "writer"  # Technical Writer


class AgentStatus(Enum):
    """Current status of an agent."""

    IDLE = "idle"  # Agent is idle, waiting for work
    BUSY = "busy"  # Agent is actively working on a task
    WAITING = "waiting"  # Agent is waiting for response/input
    ERROR = "error"  # Agent encountered an error
    STOPPED = "stopped"  # Agent has been stopped


@dataclass(frozen=True)
class AgentMetadata:
    """Immutable metadata about an agent.

    Attributes:
        agent_id: Unique agent identifier
        role: Agent's role in the team
        team_id: ID of the team this agent belongs to
        capabilities: List of capabilities this agent has
        spawned_at: ISO 8601 timestamp when agent was spawned
        config: Agent-specific configuration
    """

    agent_id: str
    role: AgentRole
    team_id: str
    capabilities: tuple[str, ...]
    spawned_at: str
    config: dict[str, Any]

    @staticmethod
    def create(
        agent_id: str,
        role: AgentRole,
        team_id: str,
        capabilities: list[str],
        config: dict[str, Any] | None = None,
    ) -> AgentMetadata:
        """Create agent metadata with auto-generated timestamp.

        Args:
            agent_id: Unique agent identifier
            role: Agent's role
            team_id: Team ID
            capabilities: List of capabilities
            config: Optional configuration

        Returns:
            New AgentMetadata instance
        """
        return AgentMetadata(
            agent_id=agent_id,
            role=role,
            team_id=team_id,
            capabilities=tuple(capabilities),
            spawned_at=datetime.now(timezone.utc).isoformat(),
            config=config or {},
        )


class BaseAgent(ABC):
    """Abstract base class for all agents in the orchestration system.

    Agents are autonomous entities that communicate via the message bus,
    perform specialized tasks, and coordinate with other agents.
    """

    def __init__(
        self,
        metadata: AgentMetadata,
        message_bus: MessageBus,
    ) -> None:
        """Initialize base agent.

        Args:
            metadata: Agent metadata
            message_bus: Message bus for communication
        """
        self._metadata = metadata
        self._message_bus = message_bus
        self._status = AgentStatus.IDLE
        self._current_task: dict[str, Any] | None = None

    @property
    def agent_id(self) -> str:
        """Get agent ID."""
        return self._metadata.agent_id

    @property
    def role(self) -> AgentRole:
        """Get agent role."""
        return self._metadata.role

    @property
    def team_id(self) -> str:
        """Get team ID."""
        return self._metadata.team_id

    @property
    def status(self) -> AgentStatus:
        """Get current agent status."""
        return self._status

    @property
    def metadata(self) -> AgentMetadata:
        """Get agent metadata."""
        return self._metadata

    @property
    def current_task(self) -> dict[str, Any] | None:
        """Get current task being executed."""
        return self._current_task

    async def start(self) -> None:
        """Start the agent and subscribe to message bus.

        This method should be called after agent creation to begin
        receiving messages.
        """
        await self._message_bus.subscribe(self.agent_id, self._handle_message)
        await self.on_start()

    async def stop(self) -> None:
        """Stop the agent and unsubscribe from message bus.

        This method should be called to gracefully shut down the agent.
        """
        self._status = AgentStatus.STOPPED
        await self._message_bus.unsubscribe(self.agent_id)
        await self.on_stop()

    async def _handle_message(self, message: Message) -> None:
        """Internal message handler that delegates to on_message.

        Args:
            message: Received message
        """
        try:
            await self.on_message(message)
        except Exception as e:
            self._status = AgentStatus.ERROR
            await self.on_error(e, message)

    def _set_status(self, status: AgentStatus) -> None:
        """Set agent status.

        Args:
            status: New status
        """
        self._status = status

    def _set_current_task(self, task: dict[str, Any] | None) -> None:
        """Set current task.

        Args:
            task: Task data or None to clear
        """
        self._current_task = task

    @abstractmethod
    async def on_start(self) -> None:
        """Called when agent starts.

        Subclasses should implement initialization logic here.
        """
        pass

    @abstractmethod
    async def on_stop(self) -> None:
        """Called when agent stops.

        Subclasses should implement cleanup logic here.
        """
        pass

    @abstractmethod
    async def on_message(self, message: Message) -> None:
        """Called when agent receives a message.

        Subclasses must implement message handling logic.

        Args:
            message: Received message
        """
        pass

    async def on_error(self, error: Exception, message: Message | None = None) -> None:
        """Called when agent encounters an error.

        Default implementation does nothing. Subclasses can override
        for custom error handling.

        Args:
            error: Exception that occurred
            message: Message being processed when error occurred (if any)
        """
        return None

    async def send_message(self, message: Message) -> None:
        """Send a message via the message bus.

        Args:
            message: Message to send
        """
        await self._message_bus.publish(message)

    async def send_request(
        self,
        receiver: str,
        payload: dict[str, Any],
        timeout: float = 30.0,
    ) -> Message:
        """Send a request and wait for response.

        Args:
            receiver: Agent ID of receiver
            payload: Request payload
            timeout: Timeout in seconds

        Returns:
            Response message

        Raises:
            TimeoutError: If no response received within timeout
        """
        return await self._message_bus.request(
            sender=self.agent_id,
            receiver=receiver,
            payload=payload,
            timeout=timeout,
        )

    async def send_response(self, request: Message, payload: dict[str, Any]) -> None:
        """Send a response to a request.

        Args:
            request: Original request message
            payload: Response payload
        """
        await self._message_bus.respond(request, payload)


__all__ = ["BaseAgent", "AgentRole", "AgentStatus", "AgentMetadata"]
