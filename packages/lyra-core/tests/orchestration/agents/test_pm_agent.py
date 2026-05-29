"""Tests for Product Manager Agent."""

from __future__ import annotations

import pytest
import pytest_asyncio
from lyra_core.orchestration.agent_base import AgentMetadata, AgentRole, AgentStatus
from lyra_core.orchestration.agents.pm_agent import ProductManagerAgent
from lyra_core.orchestration.message_bus import InMemoryMessageBus
from lyra_core.orchestration.models.requirements import Priority
from lyra_core.orchestration.protocol import Message, MessageType


@pytest_asyncio.fixture
async def message_bus() -> InMemoryMessageBus:
    """Create message bus fixture."""
    bus = InMemoryMessageBus()
    yield bus
    await bus.clear()


@pytest_asyncio.fixture
async def pm_agent(message_bus: InMemoryMessageBus) -> ProductManagerAgent:
    """Create PM agent fixture."""
    metadata = AgentMetadata.create(
        agent_id="pm-1",
        role=AgentRole.PM,
        team_id="team-1",
        capabilities=["requirements", "user_stories", "prd"],
    )
    agent = ProductManagerAgent(metadata, message_bus)
    await agent.start()
    yield agent
    await agent.stop()


@pytest.mark.asyncio
async def test_pm_agent_initialization(pm_agent: ProductManagerAgent) -> None:
    """Test PM agent initialization."""
    assert pm_agent.agent_id == "pm-1"
    assert pm_agent.role == AgentRole.PM
    assert pm_agent.status == AgentStatus.IDLE


@pytest.mark.asyncio
async def test_gather_requirements(pm_agent: ProductManagerAgent) -> None:
    """Test requirements gathering."""
    requirements = await pm_agent.gather_requirements(
        "Build a user authentication system", "high"
    )

    assert requirements.description == "Build a user authentication system"
    assert requirements.priority == Priority.HIGH
    assert len(requirements.goals) > 0
    assert len(requirements.constraints) > 0


@pytest.mark.asyncio
async def test_create_user_stories(pm_agent: ProductManagerAgent) -> None:
    """Test user story creation."""
    requirements = await pm_agent.gather_requirements(
        "Build a user authentication system", "high"
    )

    stories = await pm_agent.create_user_stories(requirements)

    assert len(stories) > 0
    for story in stories:
        assert story.requirements_id == requirements.id
        assert len(story.acceptance_criteria) > 0
        assert story.priority == requirements.priority


@pytest.mark.asyncio
async def test_generate_prd(pm_agent: ProductManagerAgent) -> None:
    """Test PRD generation."""
    requirements = await pm_agent.gather_requirements(
        "Build a user authentication system", "high"
    )
    stories = await pm_agent.create_user_stories(requirements)

    prd = await pm_agent.generate_prd(requirements, stories)

    assert prd.requirements == requirements
    assert prd.user_stories == tuple(stories)
    assert len(prd.success_metrics) > 0
    assert prd.timeline
    assert len(prd.risks) > 0


@pytest.mark.asyncio
async def test_review_design(pm_agent: ProductManagerAgent) -> None:
    """Test design review."""
    design = {
        "architecture": "microservices",
        "components": ["api", "database", "cache"],
    }

    review = await pm_agent.review_design(design)

    assert "approved" in review
    assert "feedback" in review
    assert isinstance(review["approved"], bool)


@pytest.mark.asyncio
async def test_handle_gather_requirements_message(
    pm_agent: ProductManagerAgent, message_bus: InMemoryMessageBus
) -> None:
    """Test handling gather requirements message."""
    Message.create(
        type=MessageType.REQUEST,
        sender="orchestrator",
        receiver="pm-1",
        payload={
            "action": "gather_requirements",
            "user_input": "Build a REST API",
            "priority": "medium",
        },
    )

    response = await message_bus.request(
        sender="orchestrator",
        receiver="pm-1",
        payload={
            "action": "gather_requirements",
            "user_input": "Build a REST API",
            "priority": "medium",
        },
        timeout=5.0,
    )

    assert response.payload["status"] == "success"
    assert "requirements" in response.payload
    assert response.payload["requirements"]["description"] == "Build a REST API"


@pytest.mark.asyncio
async def test_handle_unknown_action(
    pm_agent: ProductManagerAgent, message_bus: InMemoryMessageBus
) -> None:
    """Test handling unknown action."""
    response = await message_bus.request(
        sender="orchestrator",
        receiver="pm-1",
        payload={"action": "unknown_action"},
        timeout=5.0,
    )

    assert response.payload["status"] == "error"
    assert "Unknown action" in response.payload["error"]


@pytest.mark.asyncio
async def test_pm_agent_status_transitions(pm_agent: ProductManagerAgent) -> None:
    """Test agent status transitions."""
    assert pm_agent.status == AgentStatus.IDLE

    # Status should change to BUSY during operation
    await pm_agent.gather_requirements("Test", "low")

    # Status should return to IDLE after operation
    assert pm_agent.status == AgentStatus.IDLE
