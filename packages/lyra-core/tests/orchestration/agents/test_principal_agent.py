"""Tests for Principal Engineer Agent."""

from __future__ import annotations

import pytest
import pytest_asyncio

from lyra_core.orchestration.agent_base import AgentMetadata, AgentRole, AgentStatus
from lyra_core.orchestration.agents.principal_agent import PrincipalEngineerAgent
from lyra_core.orchestration.message_bus import InMemoryMessageBus
from lyra_core.orchestration.models.architecture import ArchitecturePattern
from lyra_core.orchestration.models.requirements import Priority, Requirements


@pytest_asyncio.fixture
async def message_bus() -> InMemoryMessageBus:
    """Create message bus fixture."""
    bus = InMemoryMessageBus()
    yield bus
    await bus.clear()


@pytest_asyncio.fixture
async def principal_agent(
    message_bus: InMemoryMessageBus,
) -> PrincipalEngineerAgent:
    """Create Principal Engineer agent fixture."""
    metadata = AgentMetadata.create(
        agent_id="principal-1",
        role=AgentRole.PRINCIPAL,
        team_id="team-1",
        capabilities=["architecture", "tech_stack", "scalability"],
    )
    agent = PrincipalEngineerAgent(metadata, message_bus)
    await agent.start()
    yield agent
    await agent.stop()


@pytest.fixture
def sample_requirements() -> Requirements:
    """Create sample requirements."""
    return Requirements.create(
        id="req-1",
        description="Build a scalable web application",
        goals=["High performance", "Scalability"],
        constraints=["Budget", "Timeline"],
        priority=Priority.HIGH,
    )


@pytest.mark.asyncio
async def test_principal_agent_initialization(
    principal_agent: PrincipalEngineerAgent,
) -> None:
    """Test Principal Engineer agent initialization."""
    assert principal_agent.agent_id == "principal-1"
    assert principal_agent.role == AgentRole.PRINCIPAL
    assert principal_agent.status == AgentStatus.IDLE


@pytest.mark.asyncio
async def test_design_architecture(
    principal_agent: PrincipalEngineerAgent, sample_requirements: Requirements
) -> None:
    """Test architecture design."""
    architecture = await principal_agent.design_architecture(sample_requirements)

    assert architecture.pattern in ArchitecturePattern
    assert len(architecture.components) > 0
    assert architecture.tech_stack is not None
    assert architecture.data_flow
    assert architecture.scalability_notes
    assert architecture.security_notes


@pytest.mark.asyncio
async def test_select_tech_stack(
    principal_agent: PrincipalEngineerAgent, sample_requirements: Requirements
) -> None:
    """Test tech stack selection."""
    tech_stack = await principal_agent.select_tech_stack(sample_requirements)

    assert len(tech_stack.languages) > 0
    assert len(tech_stack.frameworks) > 0
    assert len(tech_stack.databases) > 0


@pytest.mark.asyncio
async def test_design_scalability(
    principal_agent: PrincipalEngineerAgent, sample_requirements: Requirements
) -> None:
    """Test scalability design."""
    architecture = await principal_agent.design_architecture(sample_requirements)
    scalability_plan = await principal_agent.design_scalability(architecture)

    assert scalability_plan.architecture_id == architecture.id
    assert scalability_plan.horizontal_scaling
    assert scalability_plan.vertical_scaling
    assert scalability_plan.caching_strategy
    assert scalability_plan.load_balancing


@pytest.mark.asyncio
async def test_create_tech_spec(
    principal_agent: PrincipalEngineerAgent, sample_requirements: Requirements
) -> None:
    """Test tech spec creation."""
    architecture = await principal_agent.design_architecture(sample_requirements)
    tech_spec = await principal_agent.create_tech_spec(architecture)

    assert tech_spec.architecture_id == architecture.id
    assert tech_spec.title
    assert tech_spec.overview
    assert len(tech_spec.api_contracts) > 0
    assert len(tech_spec.data_models) > 0


@pytest.mark.asyncio
async def test_handle_design_architecture_message(
    principal_agent: PrincipalEngineerAgent,
    message_bus: InMemoryMessageBus,
    sample_requirements: Requirements,
) -> None:
    """Test handling design architecture message."""
    response = await message_bus.request(
        sender="orchestrator",
        receiver="principal-1",
        payload={
            "action": "design_architecture",
            "requirements": {
                "id": sample_requirements.id,
                "description": sample_requirements.description,
                "goals": list(sample_requirements.goals),
                "constraints": list(sample_requirements.constraints),
                "stakeholders": list(sample_requirements.stakeholders),
                "priority": sample_requirements.priority.value,
                "created_at": sample_requirements.created_at,
            },
        },
        timeout=5.0,
    )

    assert response.payload["status"] == "success"
    assert "architecture" in response.payload
    assert response.payload["architecture"]["pattern"] in [
        p.value for p in ArchitecturePattern
    ]


@pytest.mark.asyncio
async def test_handle_unknown_action(
    principal_agent: PrincipalEngineerAgent, message_bus: InMemoryMessageBus
) -> None:
    """Test handling unknown action."""
    response = await message_bus.request(
        sender="orchestrator",
        receiver="principal-1",
        payload={"action": "unknown_action"},
        timeout=5.0,
    )

    assert response.payload["status"] == "error"
    assert "Unknown action" in response.payload["error"]
