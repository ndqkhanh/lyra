"""Tests for Lead Engineer Agent."""

from __future__ import annotations

import pytest
import pytest_asyncio
from lyra_core.orchestration.agent_base import AgentMetadata, AgentRole, AgentStatus
from lyra_core.orchestration.agents.lead_agent import LeadEngineerAgent
from lyra_core.orchestration.message_bus import InMemoryMessageBus
from lyra_core.orchestration.models.architecture import (
    Architecture,
    ArchitecturePattern,
    ReviewStatus,
    TechStack,
)
from lyra_core.orchestration.models.code_review import PRStatus, PullRequest


@pytest_asyncio.fixture
async def message_bus() -> InMemoryMessageBus:
    """Create message bus fixture."""
    bus = InMemoryMessageBus()
    yield bus
    await bus.clear()


@pytest_asyncio.fixture
async def lead_agent(message_bus: InMemoryMessageBus) -> LeadEngineerAgent:
    """Create Lead Engineer agent fixture."""
    metadata = AgentMetadata.create(
        agent_id="lead-1",
        role=AgentRole.LEAD,
        team_id="team-1",
        capabilities=["architecture_review", "code_review", "coordination"],
    )
    agent = LeadEngineerAgent(metadata, message_bus)
    await agent.start()
    yield agent
    await agent.stop()


@pytest.fixture
def sample_architecture() -> Architecture:
    """Create sample architecture."""
    tech_stack = TechStack.create(
        languages=["Python"],
        frameworks=["FastAPI"],
        databases=["PostgreSQL"],
    )
    return Architecture.create(
        id="arch-1",
        pattern=ArchitecturePattern.LAYERED,
        components=["API", "Service", "Database"],
        tech_stack=tech_stack,
        data_flow="Client -> API -> Service -> Database",
        scalability_notes="Horizontal scaling",
        security_notes="Authentication at API layer",
    )


@pytest.fixture
def sample_pull_request() -> PullRequest:
    """Create sample pull request."""
    return PullRequest.create(
        id="pr-1",
        title="Add user authentication",
        description="Implements user authentication with JWT",
        author="engineer-1",
        files_changed=["auth.py", "models.py", "tests/test_auth.py"],
        additions=150,
        deletions=20,
        status=PRStatus.OPEN,
    )


@pytest.mark.asyncio
async def test_lead_agent_initialization(lead_agent: LeadEngineerAgent) -> None:
    """Test Lead Engineer agent initialization."""
    assert lead_agent.agent_id == "lead-1"
    assert lead_agent.role == AgentRole.LEAD
    assert lead_agent.status == AgentStatus.IDLE


@pytest.mark.asyncio
async def test_review_architecture(
    lead_agent: LeadEngineerAgent, sample_architecture: Architecture
) -> None:
    """Test architecture review."""
    review = await lead_agent.review_architecture(sample_architecture)

    assert review.architecture_id == sample_architecture.id
    assert review.status in ReviewStatus
    assert review.feedback
    assert review.reviewer_id == lead_agent.agent_id


@pytest.mark.asyncio
async def test_review_code(
    lead_agent: LeadEngineerAgent, sample_pull_request: PullRequest
) -> None:
    """Test code review."""
    review = await lead_agent.review_code(sample_pull_request)

    assert review.pr_id == sample_pull_request.id
    assert review.status in PRStatus
    assert review.summary
    assert review.reviewer_id == lead_agent.agent_id


@pytest.mark.asyncio
async def test_make_tech_decision(lead_agent: LeadEngineerAgent) -> None:
    """Test technical decision making."""
    options = [
        {"name": "Option A", "pros": ["Fast"], "cons": ["Complex"]},
        {"name": "Option B", "pros": ["Simple"], "cons": ["Slow"]},
    ]

    decision = await lead_agent.make_tech_decision(options)

    assert "selected" in decision
    assert "rationale" in decision


@pytest.mark.asyncio
async def test_coordinate_work(lead_agent: LeadEngineerAgent) -> None:
    """Test work coordination."""
    tasks = [
        {"id": "task-1", "name": "Setup database"},
        {"id": "task-2", "name": "Implement API"},
        {"id": "task-3", "name": "Write tests"},
    ]

    work_plan = await lead_agent.coordinate_work(tasks)

    assert "phases" in work_plan
    assert len(work_plan["phases"]) > 0


@pytest.mark.asyncio
async def test_handle_review_code_message(
    lead_agent: LeadEngineerAgent,
    message_bus: InMemoryMessageBus,
    sample_pull_request: PullRequest,
) -> None:
    """Test handling code review message."""
    response = await message_bus.request(
        sender="orchestrator",
        receiver="lead-1",
        payload={
            "action": "review_code",
            "pull_request": {
                "id": sample_pull_request.id,
                "title": sample_pull_request.title,
                "description": sample_pull_request.description,
                "author": sample_pull_request.author,
                "files_changed": list(sample_pull_request.files_changed),
                "additions": sample_pull_request.additions,
                "deletions": sample_pull_request.deletions,
                "status": sample_pull_request.status.value,
                "created_at": sample_pull_request.created_at,
            },
        },
        timeout=5.0,
    )

    assert response.payload["status"] == "success"
    assert "review" in response.payload
    assert response.payload["review"]["pr_id"] == sample_pull_request.id
