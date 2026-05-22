"""Team orchestrator for spawning and managing agent teams.

Provides the main orchestration logic for creating teams, managing
agent lifecycles, and coordinating workflow execution.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from lyra_core.orchestration.agent_base import AgentMetadata, AgentRole, BaseAgent
from lyra_core.orchestration.message_bus import MessageBus
from lyra_core.orchestration.state_store import StateStore


class TeamStatus(Enum):
    """Status of a team."""

    INITIALIZING = "initializing"  # Team is being created
    ACTIVE = "active"  # Team is actively working
    PAUSED = "paused"  # Team is paused
    COMPLETED = "completed"  # Team has completed its work
    FAILED = "failed"  # Team encountered a fatal error
    STOPPED = "stopped"  # Team was manually stopped


@dataclass(frozen=True)
class TeamMetadata:
    """Immutable metadata about a team.

    Attributes:
        team_id: Unique team identifier
        name: Human-readable team name
        created_at: ISO 8601 timestamp when team was created
        config: Team-specific configuration
    """

    team_id: str
    name: str
    created_at: str
    config: dict[str, Any]

    @staticmethod
    def create(
        name: str,
        config: dict[str, Any] | None = None,
    ) -> TeamMetadata:
        """Create team metadata with auto-generated ID and timestamp.

        Args:
            name: Team name
            config: Optional configuration

        Returns:
            New TeamMetadata instance
        """
        return TeamMetadata(
            team_id=str(uuid.uuid4()),
            name=name,
            created_at=datetime.now(timezone.utc).isoformat(),
            config=config or {},
        )


class TeamOrchestrator:
    """Orchestrator for managing agent teams.

    The orchestrator is responsible for:
    - Spawning and stopping agents
    - Managing team lifecycle
    - Coordinating workflow execution
    - Tracking team state
    """

    def __init__(
        self,
        message_bus: MessageBus,
        state_store: StateStore,
    ) -> None:
        """Initialize team orchestrator.

        Args:
            message_bus: Message bus for agent communication
            state_store: State store for team data
        """
        self._message_bus = message_bus
        self._state_store = state_store
        self._teams: dict[str, TeamMetadata] = {}
        self._agents: dict[str, BaseAgent] = {}
        self._team_status: dict[str, TeamStatus] = {}
        self._lock = asyncio.Lock()

    async def create_team(
        self,
        name: str,
        config: dict[str, Any] | None = None,
    ) -> str:
        """Create a new team.

        Args:
            name: Team name
            config: Optional team configuration

        Returns:
            Team ID
        """
        async with self._lock:
            metadata = TeamMetadata.create(name=name, config=config)
            self._teams[metadata.team_id] = metadata
            self._team_status[metadata.team_id] = TeamStatus.INITIALIZING

            # Store team metadata in state store
            await self._state_store.set(
                f"team:{metadata.team_id}:metadata",
                {
                    "team_id": metadata.team_id,
                    "name": metadata.name,
                    "created_at": metadata.created_at,
                    "config": metadata.config,
                },
            )

            return metadata.team_id

    async def spawn_agent(
        self,
        team_id: str,
        role: AgentRole,
        agent_class: type[BaseAgent],
        capabilities: list[str],
        config: dict[str, Any] | None = None,
    ) -> str:
        """Spawn a new agent in a team.

        Args:
            team_id: Team ID
            role: Agent role
            agent_class: Agent class to instantiate
            capabilities: List of agent capabilities
            config: Optional agent configuration

        Returns:
            Agent ID

        Raises:
            ValueError: If team doesn't exist
        """
        async with self._lock:
            if team_id not in self._teams:
                raise ValueError(f"Team {team_id} does not exist")

            # Generate agent ID
            agent_id = f"{role.value}-{uuid.uuid4().hex[:8]}"

            # Create agent metadata
            metadata = AgentMetadata.create(
                agent_id=agent_id,
                role=role,
                team_id=team_id,
                capabilities=capabilities,
                config=config,
            )

            # Instantiate agent
            agent = agent_class(metadata=metadata, message_bus=self._message_bus)

            # Store agent
            self._agents[agent_id] = agent

            # Start agent
            await agent.start()

            # Store agent metadata in state store
            await self._state_store.set(
                f"team:{team_id}:agent:{agent_id}",
                {
                    "agent_id": agent_id,
                    "role": role.value,
                    "team_id": team_id,
                    "capabilities": capabilities,
                    "spawned_at": metadata.spawned_at,
                    "config": metadata.config,
                },
            )

            return agent_id

    async def stop_agent(self, agent_id: str) -> None:
        """Stop an agent.

        Args:
            agent_id: Agent ID

        Raises:
            ValueError: If agent doesn't exist
        """
        async with self._lock:
            if agent_id not in self._agents:
                raise ValueError(f"Agent {agent_id} does not exist")

            agent = self._agents[agent_id]
            await agent.stop()
            del self._agents[agent_id]

    async def get_team_status(self, team_id: str) -> dict[str, Any]:
        """Get the status of a team.

        Args:
            team_id: Team ID

        Returns:
            Dictionary containing team status information

        Raises:
            ValueError: If team doesn't exist
        """
        async with self._lock:
            if team_id not in self._teams:
                raise ValueError(f"Team {team_id} does not exist")

            metadata = self._teams[team_id]
            status = self._team_status[team_id]

            # Get agents in this team
            team_agents = [
                {
                    "agent_id": agent.agent_id,
                    "role": agent.role.value,
                    "status": agent.status.value,
                }
                for agent in self._agents.values()
                if agent.team_id == team_id
            ]

            return {
                "team_id": team_id,
                "name": metadata.name,
                "status": status.value,
                "created_at": metadata.created_at,
                "agents": team_agents,
                "agent_count": len(team_agents),
            }

    async def set_team_status(self, team_id: str, status: TeamStatus) -> None:
        """Set the status of a team.

        Args:
            team_id: Team ID
            status: New status

        Raises:
            ValueError: If team doesn't exist
        """
        async with self._lock:
            if team_id not in self._teams:
                raise ValueError(f"Team {team_id} does not exist")

            self._team_status[team_id] = status

            # Update state store
            await self._state_store.set(
                f"team:{team_id}:status",
                status.value,
            )

    async def stop_team(self, team_id: str) -> None:
        """Stop all agents in a team.

        Args:
            team_id: Team ID

        Raises:
            ValueError: If team doesn't exist
        """
        async with self._lock:
            if team_id not in self._teams:
                raise ValueError(f"Team {team_id} does not exist")

            # Stop all agents in the team
            agent_ids = [
                agent_id
                for agent_id, agent in self._agents.items()
                if agent.team_id == team_id
            ]

        # Stop agents outside the lock to avoid deadlock
        for agent_id in agent_ids:
            await self.stop_agent(agent_id)

        # Update team status
        await self.set_team_status(team_id, TeamStatus.STOPPED)

    async def list_teams(self) -> list[dict[str, Any]]:
        """List all teams.

        Returns:
            List of team information dictionaries
        """
        async with self._lock:
            return [
                {
                    "team_id": metadata.team_id,
                    "name": metadata.name,
                    "status": self._team_status[metadata.team_id].value,
                    "created_at": metadata.created_at,
                }
                for metadata in self._teams.values()
            ]

    async def get_agent(self, agent_id: str) -> BaseAgent:
        """Get an agent by ID.

        Args:
            agent_id: Agent ID

        Returns:
            Agent instance

        Raises:
            ValueError: If agent doesn't exist
        """
        async with self._lock:
            if agent_id not in self._agents:
                raise ValueError(f"Agent {agent_id} does not exist")
            return self._agents[agent_id]

    async def list_agents(self, team_id: str | None = None) -> list[dict[str, Any]]:
        """List all agents, optionally filtered by team.

        Args:
            team_id: Optional team ID to filter by

        Returns:
            List of agent information dictionaries
        """
        async with self._lock:
            agents = self._agents.values()
            if team_id:
                agents = [a for a in agents if a.team_id == team_id]

            return [
                {
                    "agent_id": agent.agent_id,
                    "role": agent.role.value,
                    "team_id": agent.team_id,
                    "status": agent.status.value,
                }
                for agent in agents
            ]


__all__ = ["TeamOrchestrator", "TeamStatus", "TeamMetadata"]
