"""Tests for Spec-Kit Specialist Agent."""

from __future__ import annotations

import pytest
import pytest_asyncio

from lyra_core.orchestration.agent_base import AgentMetadata, AgentRole, AgentStatus
from lyra_core.orchestration.agents.spec_agent import SpecKitSpecialistAgent
from lyra_core.orchestration.message_bus import InMemoryMessageBus
from lyra_core.orchestration.models.documentation import DocStatus, DocType


@pytest_asyncio.fixture
async def message_bus() -> InMemoryMessageBus:
    """Create message bus fixture."""
    bus = InMemoryMessageBus()
    yield bus
    await bus.clear()


@pytest_asyncio.fixture
async def spec_agent(message_bus: InMemoryMessageBus) -> SpecKitSpecialistAgent:
    """Create Spec-Kit Specialist agent fixture."""
    metadata = AgentMetadata.create(
        agent_id="spec-1",
        role=AgentRole.SPEC,
        team_id="team-1",
        capabilities=["documentation", "api_docs", "specifications"],
    )
    agent = SpecKitSpecialistAgent(metadata, message_bus)
    await agent.start()
    yield agent
    await agent.stop()


@pytest.mark.asyncio
async def test_spec_agent_initialization(spec_agent: SpecKitSpecialistAgent) -> None:
    """Test Spec-Kit Specialist agent initialization."""
    assert spec_agent.agent_id == "spec-1"
    assert spec_agent.role == AgentRole.SPEC
    assert spec_agent.status == AgentStatus.IDLE


@pytest.mark.asyncio
async def test_write_api_docs(spec_agent: SpecKitSpecialistAgent) -> None:
    """Test API documentation writing."""
    api = {
        "title": "User API",
        "version": "1.0.0",
        "endpoints": ["/users", "/users/{id}"],
    }

    docs = await spec_agent.write_api_docs(api)

    assert docs.title
    assert len(docs.endpoints) > 0
    assert docs.authentication
    assert len(docs.examples) > 0
    assert len(docs.error_codes) > 0


@pytest.mark.asyncio
async def test_create_spec(spec_agent: SpecKitSpecialistAgent) -> None:
    """Test specification creation."""
    component = {
        "name": "Authentication Module",
        "type": "service",
    }

    spec = await spec_agent.create_spec(component)

    assert spec.title
    assert spec.type in DocType
    assert spec.overview
    assert spec.status in DocStatus


@pytest.mark.asyncio
async def test_generate_contracts(spec_agent: SpecKitSpecialistAgent) -> None:
    """Test contract generation."""
    interfaces = [
        {"name": "IUserRepository", "methods": ["findById", "save"]},
        {"name": "IAuthService", "methods": ["login", "logout"]},
    ]

    contracts = await spec_agent.generate_contracts(interfaces)

    assert len(contracts) == len(interfaces)
    for contract in contracts:
        assert "interface" in contract
        assert "methods" in contract


@pytest.mark.asyncio
async def test_review_docs(spec_agent: SpecKitSpecialistAgent) -> None:
    """Test documentation review."""
    docs = {
        "id": "doc-1",
        "title": "API Documentation",
        "overview": "Complete API documentation",
        "sections": ["Introduction", "Endpoints", "Examples"],
    }

    review = await spec_agent.review_docs(docs)

    assert review.doc_id == docs["id"]
    assert review.status in DocStatus
    assert review.feedback
    assert isinstance(review.approved, bool)
    assert review.reviewer_id == spec_agent.agent_id


@pytest.mark.asyncio
async def test_handle_write_api_docs_message(
    spec_agent: SpecKitSpecialistAgent, message_bus: InMemoryMessageBus
) -> None:
    """Test handling write API docs message."""
    response = await message_bus.request(
        sender="orchestrator",
        receiver="spec-1",
        payload={
            "action": "write_api_docs",
            "api": {
                "title": "User API",
                "version": "1.0.0",
            },
        },
        timeout=5.0,
    )

    assert response.payload["status"] == "success"
    assert "api_documentation" in response.payload
    assert response.payload["api_documentation"]["title"]


@pytest.mark.asyncio
async def test_handle_create_spec_message(
    spec_agent: SpecKitSpecialistAgent, message_bus: InMemoryMessageBus
) -> None:
    """Test handling create spec message."""
    response = await message_bus.request(
        sender="orchestrator",
        receiver="spec-1",
        payload={
            "action": "create_spec",
            "component": {
                "name": "Authentication Module",
            },
        },
        timeout=5.0,
    )

    assert response.payload["status"] == "success"
    assert "specification" in response.payload
    assert response.payload["specification"]["title"]


@pytest.mark.asyncio
async def test_review_docs_with_missing_fields(
    spec_agent: SpecKitSpecialistAgent,
) -> None:
    """Test documentation review with missing fields."""
    docs = {
        "id": "doc-1",
        # Missing title and overview
    }

    review = await spec_agent.review_docs(docs)

    assert not review.approved
    assert len(review.issues) > 0
    assert "Missing title" in review.issues or "Missing overview" in review.issues


@pytest.mark.asyncio
async def test_handle_unknown_action(
    spec_agent: SpecKitSpecialistAgent, message_bus: InMemoryMessageBus
) -> None:
    """Test handling unknown action."""
    response = await message_bus.request(
        sender="orchestrator",
        receiver="spec-1",
        payload={"action": "unknown_action"},
        timeout=5.0,
    )

    assert response.payload["status"] == "error"
    assert "Unknown action" in response.payload["error"]
