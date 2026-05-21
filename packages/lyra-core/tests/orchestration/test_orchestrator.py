"""Tests for team orchestrator module."""

import pytest

from lyra_core.orchestration.agent_base import (
    AgentMetadata,
    AgentRole,
    AgentStatus,
    BaseAgent,
)
from lyra_core.orchestration.message_bus import InMemoryMessageBus
from lyra_core.orchestration.orchestrator import TeamOrchestrator, TeamStatus
from lyra_core.orchestration.protocol import Message
from lyra_core.orchestration.state_store import InMemoryStateStore


class TestAgent(BaseAgent):
    """Concrete agent implementation for testing."""

    async def on_start(self) -> None:
        pass

    async def on_stop(self) -> None:
        pass

    async def on_message(self, message: Message) -> None:
        pass


@pytest.fixture
def message_bus() -> InMemoryMessageBus:
    """Create a message bus for testing."""
    return InMemoryMessageBus()


@pytest.fixture
def state_store() -> InMemoryStateStore:
    """Create a state store for testing."""
    return InMemoryStateStore()


@pytest.fixture
def orchestrator(
    message_bus: InMemoryMessageBus,
    state_store: InMemoryStateStore,
) -> TeamOrchestrator:
    """Create a team orchestrator for testing."""
    return TeamOrchestrator(message_bus, state_store)


class TestTeamStatus:
    """Tests for TeamStatus enum."""

    def test_team_statuses(self) -> None:
        """Test all team statuses are defined."""
        assert TeamStatus.INITIALIZING.value == "initializing"
        assert TeamStatus.ACTIVE.value == "active"
        assert TeamStatus.PAUSED.value == "paused"
        assert TeamStatus.COMPLETED.value == "completed"
        assert TeamStatus.FAILED.value == "failed"
        assert TeamStatus.STOPPED.value == "stopped"


class TestTeamOrchestrator:
    """Tests for TeamOrchestrator."""

    @pytest.mark.asyncio
    async def test_create_team(self, orchestrator: TeamOrchestrator) -> None:
        """Test creating a new team."""
        team_id = await orchestrator.create_team(
            name="SDLC Team",
            config={"workflow": "sdlc"},
        )

        assert team_id is not None
        assert isinstance(team_id, str)

        # Verify team status
        status = await orchestrator.get_team_status(team_id)
        assert status["team_id"] == team_id
        assert status["name"] == "SDLC Team"
        assert status["status"] == TeamStatus.INITIALIZING.value

    @pytest.mark.asyncio
    async def test_spawn_agent(
        self,
        orchestrator: TeamOrchestrator,
        state_store: InMemoryStateStore,
    ) -> None:
        """Test spawning an agent in a team."""
        team_id = await orchestrator.create_team("Test Team")

        agent_id = await orchestrator.spawn_agent(
            team_id=team_id,
            role=AgentRole.PM,
            agent_class=TestAgent,
            capabilities=["requirements", "prd"],
            config={"model": "claude-sonnet-4"},
        )

        assert agent_id is not None
        assert agent_id.startswith("product_manager-")

        # Verify agent was stored in state
        agent_data = await state_store.get(f"team:{team_id}:agent:{agent_id}")
        assert agent_data is not None
        assert agent_data["agent_id"] == agent_id
        assert agent_data["role"] == "product_manager"

    @pytest.mark.asyncio
    async def test_spawn_agent_nonexistent_team(
        self,
        orchestrator: TeamOrchestrator,
    ) -> None:
        """Test spawning agent in non-existent team raises error."""
        with pytest.raises(ValueError, match="Team .* does not exist"):
            await orchestrator.spawn_agent(
                team_id="nonexistent",
                role=AgentRole.QA,
                agent_class=TestAgent,
                capabilities=["testing"],
            )

    @pytest.mark.asyncio
    async def test_stop_agent(self, orchestrator: TeamOrchestrator) -> None:
        """Test stopping an agent."""
        team_id = await orchestrator.create_team("Test Team")
        agent_id = await orchestrator.spawn_agent(
            team_id=team_id,
            role=AgentRole.ENGINEER,
            agent_class=TestAgent,
            capabilities=["coding"],
        )

        # Stop the agent
        await orchestrator.stop_agent(agent_id)

        # Verify agent is no longer in orchestrator
        with pytest.raises(ValueError, match="Agent .* does not exist"):
            await orchestrator.get_agent(agent_id)

    @pytest.mark.asyncio
    async def test_stop_nonexistent_agent(
        self,
        orchestrator: TeamOrchestrator,
    ) -> None:
        """Test stopping non-existent agent raises error."""
        with pytest.raises(ValueError, match="Agent .* does not exist"):
            await orchestrator.stop_agent("nonexistent")

    @pytest.mark.asyncio
    async def test_get_team_status(self, orchestrator: TeamOrchestrator) -> None:
        """Test getting team status."""
        team_id = await orchestrator.create_team(
            name="Test Team",
            config={"key": "value"},
        )

        # Spawn some agents
        await orchestrator.spawn_agent(
            team_id=team_id,
            role=AgentRole.PM,
            agent_class=TestAgent,
            capabilities=["requirements"],
        )
        await orchestrator.spawn_agent(
            team_id=team_id,
            role=AgentRole.LEAD,
            agent_class=TestAgent,
            capabilities=["architecture"],
        )

        status = await orchestrator.get_team_status(team_id)

        assert status["team_id"] == team_id
        assert status["name"] == "Test Team"
        assert status["status"] == TeamStatus.INITIALIZING.value
        assert status["agent_count"] == 2
        assert len(status["agents"]) == 2

    @pytest.mark.asyncio
    async def test_get_team_status_nonexistent(
        self,
        orchestrator: TeamOrchestrator,
    ) -> None:
        """Test getting status of non-existent team raises error."""
        with pytest.raises(ValueError, match="Team .* does not exist"):
            await orchestrator.get_team_status("nonexistent")

    @pytest.mark.asyncio
    async def test_set_team_status(
        self,
        orchestrator: TeamOrchestrator,
        state_store: InMemoryStateStore,
    ) -> None:
        """Test setting team status."""
        team_id = await orchestrator.create_team("Test Team")

        await orchestrator.set_team_status(team_id, TeamStatus.ACTIVE)

        status = await orchestrator.get_team_status(team_id)
        assert status["status"] == TeamStatus.ACTIVE.value

        # Verify status was stored
        stored_status = await state_store.get(f"team:{team_id}:status")
        assert stored_status == TeamStatus.ACTIVE.value

    @pytest.mark.asyncio
    async def test_set_team_status_nonexistent(
        self,
        orchestrator: TeamOrchestrator,
    ) -> None:
        """Test setting status of non-existent team raises error."""
        with pytest.raises(ValueError, match="Team .* does not exist"):
            await orchestrator.set_team_status("nonexistent", TeamStatus.ACTIVE)

    @pytest.mark.asyncio
    async def test_stop_team(self, orchestrator: TeamOrchestrator) -> None:
        """Test stopping an entire team."""
        team_id = await orchestrator.create_team("Test Team")

        # Spawn multiple agents
        agent_ids = []
        for role in [AgentRole.PM, AgentRole.LEAD, AgentRole.QA]:
            agent_id = await orchestrator.spawn_agent(
                team_id=team_id,
                role=role,
                agent_class=TestAgent,
                capabilities=["test"],
            )
            agent_ids.append(agent_id)

        # Stop the team
        await orchestrator.stop_team(team_id)

        # Verify team status is stopped
        status = await orchestrator.get_team_status(team_id)
        assert status["status"] == TeamStatus.STOPPED.value

        # Verify all agents are stopped
        for agent_id in agent_ids:
            with pytest.raises(ValueError, match="Agent .* does not exist"):
                await orchestrator.get_agent(agent_id)

    @pytest.mark.asyncio
    async def test_stop_team_nonexistent(
        self,
        orchestrator: TeamOrchestrator,
    ) -> None:
        """Test stopping non-existent team raises error."""
        with pytest.raises(ValueError, match="Team .* does not exist"):
            await orchestrator.stop_team("nonexistent")

    @pytest.mark.asyncio
    async def test_list_teams(self, orchestrator: TeamOrchestrator) -> None:
        """Test listing all teams."""
        # Create multiple teams
        team_id_1 = await orchestrator.create_team("Team 1")
        team_id_2 = await orchestrator.create_team("Team 2")
        team_id_3 = await orchestrator.create_team("Team 3")

        teams = await orchestrator.list_teams()

        assert len(teams) == 3
        team_ids = [t["team_id"] for t in teams]
        assert team_id_1 in team_ids
        assert team_id_2 in team_ids
        assert team_id_3 in team_ids

    @pytest.mark.asyncio
    async def test_list_teams_empty(self, orchestrator: TeamOrchestrator) -> None:
        """Test listing teams when none exist."""
        teams = await orchestrator.list_teams()
        assert teams == []

    @pytest.mark.asyncio
    async def test_get_agent(self, orchestrator: TeamOrchestrator) -> None:
        """Test getting an agent by ID."""
        team_id = await orchestrator.create_team("Test Team")
        agent_id = await orchestrator.spawn_agent(
            team_id=team_id,
            role=AgentRole.ENGINEER,
            agent_class=TestAgent,
            capabilities=["coding"],
        )

        agent = await orchestrator.get_agent(agent_id)

        assert agent.agent_id == agent_id
        assert agent.role == AgentRole.ENGINEER
        assert agent.team_id == team_id

    @pytest.mark.asyncio
    async def test_get_agent_nonexistent(
        self,
        orchestrator: TeamOrchestrator,
    ) -> None:
        """Test getting non-existent agent raises error."""
        with pytest.raises(ValueError, match="Agent .* does not exist"):
            await orchestrator.get_agent("nonexistent")

    @pytest.mark.asyncio
    async def test_list_agents_all(self, orchestrator: TeamOrchestrator) -> None:
        """Test listing all agents across teams."""
        team_id_1 = await orchestrator.create_team("Team 1")
        team_id_2 = await orchestrator.create_team("Team 2")

        # Spawn agents in different teams
        await orchestrator.spawn_agent(
            team_id=team_id_1,
            role=AgentRole.PM,
            agent_class=TestAgent,
            capabilities=["requirements"],
        )
        await orchestrator.spawn_agent(
            team_id=team_id_1,
            role=AgentRole.LEAD,
            agent_class=TestAgent,
            capabilities=["architecture"],
        )
        await orchestrator.spawn_agent(
            team_id=team_id_2,
            role=AgentRole.QA,
            agent_class=TestAgent,
            capabilities=["testing"],
        )

        agents = await orchestrator.list_agents()

        assert len(agents) == 3

    @pytest.mark.asyncio
    async def test_list_agents_by_team(
        self,
        orchestrator: TeamOrchestrator,
    ) -> None:
        """Test listing agents filtered by team."""
        team_id_1 = await orchestrator.create_team("Team 1")
        team_id_2 = await orchestrator.create_team("Team 2")

        # Spawn agents in different teams
        await orchestrator.spawn_agent(
            team_id=team_id_1,
            role=AgentRole.PM,
            agent_class=TestAgent,
            capabilities=["requirements"],
        )
        await orchestrator.spawn_agent(
            team_id=team_id_1,
            role=AgentRole.LEAD,
            agent_class=TestAgent,
            capabilities=["architecture"],
        )
        await orchestrator.spawn_agent(
            team_id=team_id_2,
            role=AgentRole.QA,
            agent_class=TestAgent,
            capabilities=["testing"],
        )

        # List agents for team 1
        agents_team_1 = await orchestrator.list_agents(team_id=team_id_1)
        assert len(agents_team_1) == 2
        assert all(a["team_id"] == team_id_1 for a in agents_team_1)

        # List agents for team 2
        agents_team_2 = await orchestrator.list_agents(team_id=team_id_2)
        assert len(agents_team_2) == 1
        assert agents_team_2[0]["team_id"] == team_id_2

    @pytest.mark.asyncio
    async def test_multiple_agents_same_role(
        self,
        orchestrator: TeamOrchestrator,
    ) -> None:
        """Test spawning multiple agents with the same role."""
        team_id = await orchestrator.create_team("Test Team")

        # Spawn multiple engineers
        agent_id_1 = await orchestrator.spawn_agent(
            team_id=team_id,
            role=AgentRole.ENGINEER,
            agent_class=TestAgent,
            capabilities=["coding"],
        )
        agent_id_2 = await orchestrator.spawn_agent(
            team_id=team_id,
            role=AgentRole.ENGINEER,
            agent_class=TestAgent,
            capabilities=["coding"],
        )

        # Both should have unique IDs
        assert agent_id_1 != agent_id_2
        assert agent_id_1.startswith("engineer-")
        assert agent_id_2.startswith("engineer-")

        agents = await orchestrator.list_agents(team_id=team_id)
        assert len(agents) == 2
