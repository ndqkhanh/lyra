"""Tests for Research Agent."""

from __future__ import annotations

import pytest
import pytest_asyncio
from lyra_core.orchestration.agent_base import AgentMetadata, AgentRole, AgentStatus
from lyra_core.orchestration.agents.research_agent import ResearchAgent
from lyra_core.orchestration.message_bus import InMemoryMessageBus
from lyra_core.orchestration.models.research import PaperSource, ProjectQuality


@pytest_asyncio.fixture
async def message_bus() -> InMemoryMessageBus:
    """Create message bus fixture."""
    bus = InMemoryMessageBus()
    yield bus
    await bus.clear()


@pytest_asyncio.fixture
async def research_agent(message_bus: InMemoryMessageBus) -> ResearchAgent:
    """Create Research agent fixture."""
    metadata = AgentMetadata.create(
        agent_id="research-1",
        role=AgentRole.RESEARCH,
        team_id="team-1",
        capabilities=["paper_search", "repo_analysis", "project_evaluation"],
    )
    agent = ResearchAgent(metadata, message_bus)
    await agent.start()
    yield agent
    await agent.stop()


@pytest.mark.asyncio
async def test_research_agent_initialization(research_agent: ResearchAgent) -> None:
    """Test Research agent initialization."""
    assert research_agent.agent_id == "research-1"
    assert research_agent.role == AgentRole.RESEARCH
    assert research_agent.status == AgentStatus.IDLE


@pytest.mark.asyncio
async def test_search_papers(research_agent: ResearchAgent) -> None:
    """Test paper search."""
    query = "machine learning"

    papers = await research_agent.search_papers(query)

    assert len(papers) > 0
    for paper in papers:
        assert paper.title
        assert len(paper.authors) > 0
        assert paper.abstract
        assert paper.url
        assert paper.source in PaperSource


@pytest.mark.asyncio
async def test_analyze_github_repos(research_agent: ResearchAgent) -> None:
    """Test GitHub repository analysis."""
    query = "python web framework"

    repos = await research_agent.analyze_github_repos(query)

    assert len(repos) > 0
    for repo in repos:
        assert repo.name
        assert repo.repo_url
        assert repo.description
        assert repo.stars >= 0
        assert repo.forks >= 0
        assert repo.language


@pytest.mark.asyncio
async def test_evaluate_projects(research_agent: ResearchAgent) -> None:
    """Test project evaluation."""
    projects = [
        {"name": "Project A", "url": "https://github.com/example/project-a"},
        {"name": "Project B", "url": "https://github.com/example/project-b"},
    ]

    evaluations = await research_agent.evaluate_projects(projects)

    assert len(evaluations) == len(projects)
    for evaluation in evaluations:
        assert evaluation.project_name
        assert evaluation.project_url
        assert evaluation.quality in ProjectQuality
        assert len(evaluation.strengths) > 0
        assert evaluation.recommendation
        assert 0 <= evaluation.score <= 100


@pytest.mark.asyncio
async def test_synthesize_findings(research_agent: ResearchAgent) -> None:
    """Test research synthesis."""
    papers = await research_agent.search_papers("deep learning")
    repos = await research_agent.analyze_github_repos("deep learning")
    evaluations = await research_agent.evaluate_projects(
        [{"name": "DL Framework", "url": "https://github.com/example/dl"}]
    )

    data = {
        "query": "deep learning",
        "papers": [
            {
                "id": p.id,
                "title": p.title,
                "authors": list(p.authors),
                "abstract": p.abstract,
                "url": p.url,
                "source": p.source.value,
                "published_date": p.published_date,
                "citations": p.citations,
                "relevance_score": p.relevance_score,
                "created_at": p.created_at,
            }
            for p in papers
        ],
        "repositories": [
            {
                "id": r.id,
                "repo_url": r.repo_url,
                "name": r.name,
                "description": r.description,
                "stars": r.stars,
                "forks": r.forks,
                "language": r.language,
                "topics": list(r.topics),
                "last_updated": r.last_updated,
                "license": r.license,
                "relevance_score": r.relevance_score,
                "created_at": r.created_at,
            }
            for r in repos
        ],
        "evaluations": [
            {
                "id": e.id,
                "project_name": e.project_name,
                "project_url": e.project_url,
                "quality": e.quality.value,
                "strengths": list(e.strengths),
                "weaknesses": list(e.weaknesses),
                "use_cases": list(e.use_cases),
                "recommendation": e.recommendation,
                "score": e.score,
                "created_at": e.created_at,
            }
            for e in evaluations
        ],
    }

    report = await research_agent.synthesize_findings(data)

    assert report.title
    assert report.query == "deep learning"
    assert len(report.papers) > 0
    assert len(report.repos) > 0
    assert len(report.evaluations) > 0
    assert report.summary
    assert len(report.key_findings) > 0
    assert len(report.recommendations) > 0


@pytest.mark.asyncio
async def test_handle_search_papers_message(
    research_agent: ResearchAgent, message_bus: InMemoryMessageBus
) -> None:
    """Test handling search papers message."""
    response = await message_bus.request(
        sender="orchestrator",
        receiver="research-1",
        payload={
            "action": "search_papers",
            "query": "neural networks",
        },
        timeout=5.0,
    )

    assert response.payload["status"] == "success"
    assert "papers" in response.payload
    assert len(response.payload["papers"]) > 0


@pytest.mark.asyncio
async def test_handle_analyze_github_repos_message(
    research_agent: ResearchAgent, message_bus: InMemoryMessageBus
) -> None:
    """Test handling analyze GitHub repos message."""
    response = await message_bus.request(
        sender="orchestrator",
        receiver="research-1",
        payload={
            "action": "analyze_github_repos",
            "query": "python framework",
        },
        timeout=5.0,
    )

    assert response.payload["status"] == "success"
    assert "repositories" in response.payload
    assert len(response.payload["repositories"]) > 0


@pytest.mark.asyncio
async def test_handle_evaluate_projects_message(
    research_agent: ResearchAgent, message_bus: InMemoryMessageBus
) -> None:
    """Test handling evaluate projects message."""
    response = await message_bus.request(
        sender="orchestrator",
        receiver="research-1",
        payload={
            "action": "evaluate_projects",
            "projects": [
                {"name": "Test Project", "url": "https://github.com/test/project"}
            ],
        },
        timeout=5.0,
    )

    assert response.payload["status"] == "success"
    assert "evaluations" in response.payload
    assert len(response.payload["evaluations"]) > 0


@pytest.mark.asyncio
async def test_handle_unknown_action(
    research_agent: ResearchAgent, message_bus: InMemoryMessageBus
) -> None:
    """Test handling unknown action."""
    response = await message_bus.request(
        sender="orchestrator",
        receiver="research-1",
        payload={"action": "unknown_action"},
        timeout=5.0,
    )

    assert response.payload["status"] == "error"
    assert "Unknown action" in response.payload["error"]
