"""
Tests for specialized discovery agents.

Tests 6 discovery agents with parallel execution and rate limiting.
"""
import asyncio
import time
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)

from lyra_research.agents.discovery import (
    ArxivAgent,
    DiscoveryAgent,
    GithubAgent,
    HuggingFaceAgent,
    OpenReviewAgent,
    SemanticScholarAgent,
    WebAgent,
)
from lyra_research.agents.discovery.discovery_base import RateLimiter
from lyra_research.discovery import ResearchSource, SourceType


# ---------------------------------------------------------------------------
# RateLimiter Tests
# ---------------------------------------------------------------------------


def test_rate_limiter_calculate_backoff():
    """Test exponential backoff calculation."""
    limiter = RateLimiter(max_retries=5, base_delay=1.0)

    assert limiter.calculate_backoff(0) == 1.0  # 2^0 = 1
    assert limiter.calculate_backoff(1) == 2.0  # 2^1 = 2
    assert limiter.calculate_backoff(2) == 4.0  # 2^2 = 4
    assert limiter.calculate_backoff(3) == 8.0  # 2^3 = 8
    assert limiter.calculate_backoff(4) == 16.0  # 2^4 = 16


def test_rate_limiter_handle_rate_limit():
    """Test rate limit handling with sleep."""
    limiter = RateLimiter(max_retries=3, base_delay=0.1)

    start = time.time()
    limiter.handle_rate_limit(0, "test_source")
    elapsed = time.time() - start

    # Should sleep for ~0.1s (2^0 * 0.1)
    assert 0.08 < elapsed < 0.15


def test_rate_limiter_max_retries_exceeded():
    """Test that max retries raises error."""
    limiter = RateLimiter(max_retries=3, base_delay=0.1)

    with pytest.raises(RuntimeError, match="rate limit exceeded"):
        limiter.handle_rate_limit(3, "test_source")


# ---------------------------------------------------------------------------
# DiscoveryAgent Base Tests
# ---------------------------------------------------------------------------


def test_discovery_agent_initialization():
    """Test discovery agent base initialization."""

    class TestAgent(DiscoveryAgent):
        async def discover(self, query: str, max_results: int = 50):
            return []

    agent = TestAgent(source_name="test", model="claude-haiku-4-5")

    assert agent.source_name == "test"
    assert agent.model == "claude-haiku-4-5"
    assert agent.rate_limiter.max_retries == 5


# ---------------------------------------------------------------------------
# ArxivAgent Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_arxiv_agent_discover():
    """Test ArXiv agent discovery."""
    agent = ArxivAgent()

    # Mock ArXiv search
    mock_source = ResearchSource(
        id="arxiv:1234",
        title="Test Paper",
        source_type=SourceType.PAPER,
        url="https://arxiv.org/abs/1234",
        abstract="Test abstract",
    )

    with patch.object(agent.arxiv, "search", return_value=[mock_source]):
        sources = await agent.discover("machine learning", max_results=10)

    assert len(sources) == 1
    assert sources[0].title == "Test Paper"
    assert sources[0].source_type == SourceType.PAPER


@pytest.mark.asyncio
async def test_arxiv_agent_retry_on_failure():
    """Test ArXiv agent retries on failure."""
    agent = ArxivAgent()
    agent.rate_limiter.max_retries = 2
    agent.rate_limiter.base_delay = 0.01  # Fast retry for testing

    # Mock to fail once, then succeed
    call_count = 0

    def mock_search(query, max_results):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("Temporary failure")
        return [
            ResearchSource(
                id="arxiv:1234",
                title="Test Paper",
                source_type=SourceType.PAPER,
                url="https://arxiv.org/abs/1234",
            )
        ]

    with patch.object(agent.arxiv, "search", side_effect=mock_search):
        sources = await agent.discover("test", max_results=10)

    assert len(sources) == 1
    assert call_count == 2  # Failed once, succeeded on retry


# ---------------------------------------------------------------------------
# SemanticScholarAgent Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_semantic_scholar_agent_discover():
    """Test Semantic Scholar agent discovery."""
    agent = SemanticScholarAgent()

    mock_source = ResearchSource(
        id="ss:5678",
        title="Test Paper",
        source_type=SourceType.PAPER,
        url="https://semanticscholar.org/paper/5678",
        citations=100,
    )

    with patch.object(agent.semantic_scholar, "search", return_value=[mock_source]):
        sources = await agent.discover("deep learning", max_results=10)

    assert len(sources) == 1
    assert sources[0].citations == 100


@pytest.mark.asyncio
async def test_semantic_scholar_agent_empty_results():
    """Test Semantic Scholar agent with no results."""
    agent = SemanticScholarAgent()

    with patch.object(agent.semantic_scholar, "search", return_value=[]):
        sources = await agent.discover("nonexistent topic", max_results=10)

    assert len(sources) == 0


# ---------------------------------------------------------------------------
# GithubAgent Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_github_agent_discover():
    """Test GitHub agent discovery."""
    agent = GithubAgent()

    mock_source = ResearchSource(
        id="gh:123",
        title="test/repo",
        source_type=SourceType.REPOSITORY,
        url="https://github.com/test/repo",
        stars=1000,
    )

    with patch.object(agent.github, "search", return_value=[mock_source]):
        sources = await agent.discover("pytorch", max_results=10)

    assert len(sources) == 1
    assert sources[0].source_type == SourceType.REPOSITORY
    assert sources[0].stars == 1000


@pytest.mark.asyncio
async def test_github_agent_rate_limit_handling():
    """Test GitHub agent handles rate limits."""
    agent = GithubAgent()
    agent.rate_limiter.max_retries = 2
    agent.rate_limiter.base_delay = 0.01

    call_count = 0

    def mock_search(query, max_results):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("rate limit exceeded")
        return []

    with patch.object(agent.github, "search", side_effect=mock_search):
        sources = await agent.discover("test", max_results=10)

    assert call_count == 2  # Retried after rate limit


# ---------------------------------------------------------------------------
# WebAgent Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_web_agent_discover():
    """Test web agent discovery (placeholder)."""
    agent = WebAgent()

    sources = await agent.discover("test query", max_results=10)

    # Web agent is a placeholder, returns empty list
    assert len(sources) == 0


# ---------------------------------------------------------------------------
# OpenReviewAgent Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_openreview_agent_discover():
    """Test OpenReview agent discovery."""
    agent = OpenReviewAgent()

    mock_source = ResearchSource(
        id="or:abc123",
        title="Test Paper",
        source_type=SourceType.PAPER,
        url="https://openreview.net/forum?id=abc123",
        metadata={"venue": "ICLR.cc"},
    )

    with patch.object(agent.openreview, "search", return_value=[mock_source]):
        sources = await agent.discover("transformers", max_results=10)

    assert len(sources) == 1
    assert sources[0].metadata["venue"] == "ICLR.cc"


# ---------------------------------------------------------------------------
# HuggingFaceAgent Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_huggingface_agent_discover():
    """Test HuggingFace agent discovery."""
    agent = HuggingFaceAgent()

    mock_source = ResearchSource(
        id="hf:2301.12345",
        title="Test Paper",
        source_type=SourceType.PAPER,
        url="https://huggingface.co/papers/2301.12345",
        citations=50,
    )

    with patch.object(agent.huggingface, "search", return_value=[mock_source]):
        sources = await agent.discover("llm", max_results=10)

    assert len(sources) == 1
    assert sources[0].id == "hf:2301.12345"


@pytest.mark.asyncio
async def test_huggingface_agent_rate_limit_retry():
    """Test HuggingFace agent retries on rate limit."""
    agent = HuggingFaceAgent()
    agent.rate_limiter.max_retries = 2
    agent.rate_limiter.base_delay = 0.01

    call_count = 0

    def mock_search(query, max_results):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("Rate limit exceeded")
        return []

    with patch.object(agent.huggingface, "search", side_effect=mock_search):
        sources = await agent.discover("test", max_results=10)

    assert call_count == 2


# ---------------------------------------------------------------------------
# Parallel Execution Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_parallel_discovery_execution():
    """Test parallel execution of multiple discovery agents."""
    agents = [
        ArxivAgent(),
        SemanticScholarAgent(),
        GithubAgent(),
        OpenReviewAgent(),
        HuggingFaceAgent(),
        WebAgent(),
    ]

    # Mock all agents to return one source each
    mock_sources = [
        [
            ResearchSource(
                id=f"source_{i}",
                title=f"Source {i}",
                source_type=SourceType.PAPER,
                url=f"https://example.com/{i}",
            )
        ]
        for i in range(6)
    ]

    with patch.object(ArxivAgent, "discover", return_value=mock_sources[0]), patch.object(
        SemanticScholarAgent, "discover", return_value=mock_sources[1]
    ), patch.object(GithubAgent, "discover", return_value=mock_sources[2]), patch.object(
        OpenReviewAgent, "discover", return_value=mock_sources[3]
    ), patch.object(
        HuggingFaceAgent, "discover", return_value=mock_sources[4]
    ), patch.object(
        WebAgent, "discover", return_value=mock_sources[5]
    ):

        # Execute all agents in parallel
        start = time.time()
        results = await asyncio.gather(
            *[agent.discover("test query", max_results=10) for agent in agents]
        )
        elapsed = time.time() - start

    # All agents should complete
    assert len(results) == 6

    # Parallel execution should be fast (< 1s for mocked calls)
    assert elapsed < 1.0


@pytest.mark.asyncio
async def test_parallel_discovery_with_failures():
    """Test parallel discovery handles individual agent failures."""
    agents = [ArxivAgent(), SemanticScholarAgent(), GithubAgent()]

    # Mock: first succeeds, second fails, third succeeds
    with patch.object(
        ArxivAgent,
        "discover",
        return_value=[
            ResearchSource(
                id="1", title="Paper 1", source_type=SourceType.PAPER, url="url1"
            )
        ],
    ), patch.object(
        SemanticScholarAgent, "discover", side_effect=Exception("API error")
    ), patch.object(
        GithubAgent,
        "discover",
        return_value=[
            ResearchSource(
                id="2", title="Repo 1", source_type=SourceType.REPOSITORY, url="url2"
            )
        ],
    ):

        results = await asyncio.gather(
            *[agent.discover("test", max_results=10) for agent in agents],
            return_exceptions=True,
        )

    # First and third succeed, second fails
    assert len(results) == 3
    assert len(results[0]) == 1  # ArXiv succeeded
    assert isinstance(results[1], Exception)  # Semantic Scholar failed
    assert len(results[2]) == 1  # GitHub succeeded


@pytest.mark.asyncio
async def test_discovery_agents_complete_under_20s():
    """Test that 6 discovery agents complete in <20s (mocked)."""
    agents = [
        ArxivAgent(),
        SemanticScholarAgent(),
        GithubAgent(),
        OpenReviewAgent(),
        HuggingFaceAgent(),
        WebAgent(),
    ]

    # Mock the underlying discovery engines to return empty results quickly
    with patch.object(agents[0].arxiv, "search", return_value=[]), \
         patch.object(agents[1].semantic_scholar, "search", return_value=[]), \
         patch.object(agents[2].github, "search", return_value=[]), \
         patch.object(agents[3].openreview, "search", return_value=[]), \
         patch.object(agents[4].huggingface, "search", return_value=[]):

        start = time.time()
        results = await asyncio.gather(
            *[agent.discover("test", max_results=50) for agent in agents]
        )
        elapsed = time.time() - start

    # Should complete very quickly with mocks
    assert elapsed < 1.0
    assert len(results) == 6
