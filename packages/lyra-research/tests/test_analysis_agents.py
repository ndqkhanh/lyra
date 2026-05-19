"""
Tests for specialized analysis agents.

Tests 4 analysis agents with parallel execution.
"""
import asyncio
import time
from datetime import datetime

import pytest

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)

from lyra_research.agents.analysis import (
    AnalysisAgent,
    CitationAnalysisAgent,
    PaperAnalysisAgent,
    QualityScoreAgent,
    RepoAnalysisAgent,
)
from lyra_research.agents.analysis.analysis_base import Analysis
from lyra_research.discovery import ResearchSource, SourceType


# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def paper_sources():
    """Create test paper sources."""
    return [
        ResearchSource(
            id="paper1",
            title="Deep Learning Paper",
            source_type=SourceType.PAPER,
            url="https://arxiv.org/abs/1234",
            authors=["Alice", "Bob"],
            published_date=datetime(2023, 1, 1),
            abstract="This paper presents a novel deep learning approach.",
            citations=500,
            metadata={"venue": "NeurIPS", "year": 2023},
        ),
        ResearchSource(
            id="paper2",
            title="Machine Learning Survey",
            source_type=SourceType.PAPER,
            url="https://arxiv.org/abs/5678",
            authors=["Charlie"],
            published_date=datetime(2022, 6, 1),
            abstract="A comprehensive survey of machine learning techniques.",
            citations=150,
            metadata={"venue": "ICML", "year": 2022},
        ),
        ResearchSource(
            id="paper3",
            title="Recent Advances",
            source_type=SourceType.PAPER,
            url="https://arxiv.org/abs/9999",
            authors=["Dave", "Eve"],
            published_date=datetime(2024, 1, 1),
            abstract="Recent advances in AI.",
            citations=10,
            metadata={"venue": "arXiv", "year": 2024},
        ),
    ]


@pytest.fixture
def repo_sources():
    """Create test repository sources."""
    return [
        ResearchSource(
            id="repo1",
            title="pytorch/pytorch",
            source_type=SourceType.REPOSITORY,
            url="https://github.com/pytorch/pytorch",
            authors=["pytorch"],
            published_date=datetime(2016, 1, 1),
            abstract="Tensors and Dynamic neural networks in Python",
            stars=75000,
            metadata={"language": "Python", "forks": 20000, "topics": ["deep-learning", "pytorch"]},
        ),
        ResearchSource(
            id="repo2",
            title="huggingface/transformers",
            source_type=SourceType.REPOSITORY,
            url="https://github.com/huggingface/transformers",
            authors=["huggingface"],
            published_date=datetime(2018, 1, 1),
            abstract="State-of-the-art Machine Learning for PyTorch, TensorFlow",
            stars=120000,
            metadata={"language": "Python", "forks": 25000, "topics": ["nlp", "transformers"]},
        ),
    ]


# ---------------------------------------------------------------------------
# PaperAnalysisAgent Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_paper_analysis_agent_analyze(paper_sources):
    """Test paper analysis agent."""
    agent = PaperAnalysisAgent()

    analyses = await agent.analyze(paper_sources)

    assert len(analyses) == 3
    assert all(isinstance(a, Analysis) for a in analyses)
    assert all(a.analysis_type == "paper" for a in analyses)

    # Check first paper analysis
    analysis1 = analyses[0]
    assert analysis1.source_id == "paper1"
    assert len(analysis1.findings) > 0
    assert analysis1.metadata["venue"] == "NeurIPS"
    assert analysis1.metadata["citations"] == 500


@pytest.mark.asyncio
async def test_paper_analysis_agent_filters_non_papers(paper_sources, repo_sources):
    """Test that paper agent only analyzes papers."""
    agent = PaperAnalysisAgent()

    # Mix papers and repos
    mixed_sources = paper_sources + repo_sources

    analyses = await agent.analyze(mixed_sources)

    # Should only analyze papers (3), not repos (2)
    assert len(analyses) == 3
    assert all(a.analysis_type == "paper" for a in analyses)


@pytest.mark.asyncio
async def test_paper_analysis_extracts_findings(paper_sources):
    """Test that paper analysis extracts meaningful findings."""
    agent = PaperAnalysisAgent()

    analyses = await agent.analyze(paper_sources)

    # First paper has high citations
    analysis1 = next(a for a in analyses if a.source_id == "paper1")
    findings_text = " ".join(analysis1.findings)
    assert "500 citations" in findings_text or "Highly cited" in findings_text

    # First paper is from top venue
    assert any("NeurIPS" in f for f in analysis1.findings)


# ---------------------------------------------------------------------------
# RepoAnalysisAgent Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_repo_analysis_agent_analyze(repo_sources):
    """Test repository analysis agent."""
    agent = RepoAnalysisAgent()

    analyses = await agent.analyze(repo_sources)

    assert len(analyses) == 2
    assert all(isinstance(a, Analysis) for a in analyses)
    assert all(a.analysis_type == "repo" for a in analyses)

    # Check first repo analysis
    analysis1 = analyses[0]
    assert analysis1.source_id == "repo1"
    assert analysis1.metadata["stars"] == 75000
    assert analysis1.metadata["language"] == "Python"


@pytest.mark.asyncio
async def test_repo_analysis_agent_filters_non_repos(paper_sources, repo_sources):
    """Test that repo agent only analyzes repositories."""
    agent = RepoAnalysisAgent()

    # Mix papers and repos
    mixed_sources = paper_sources + repo_sources

    analyses = await agent.analyze(mixed_sources)

    # Should only analyze repos (2), not papers (3)
    assert len(analyses) == 2
    assert all(a.analysis_type == "repo" for a in analyses)


@pytest.mark.asyncio
async def test_repo_analysis_extracts_insights(repo_sources):
    """Test that repo analysis extracts meaningful insights."""
    agent = RepoAnalysisAgent()

    analyses = await agent.analyze(repo_sources)

    # PyTorch has high stars
    pytorch_analysis = next(a for a in analyses if a.source_id == "repo1")
    findings_text = " ".join(pytorch_analysis.findings)
    assert "75,000 stars" in findings_text or "popular" in findings_text.lower()

    # Check language is mentioned
    assert any("Python" in f for f in pytorch_analysis.findings)


# ---------------------------------------------------------------------------
# CitationAnalysisAgent Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_citation_analysis_agent_analyze(paper_sources):
    """Test citation analysis agent."""
    agent = CitationAnalysisAgent()

    analyses = await agent.analyze(paper_sources)

    assert len(analyses) == 3
    assert all(isinstance(a, Analysis) for a in analyses)
    assert all(a.analysis_type == "citation" for a in analyses)

    # Check citation metadata
    analysis1 = analyses[0]
    assert "citations" in analysis1.metadata
    assert "citation_rank" in analysis1.metadata
    assert "total_papers" in analysis1.metadata


@pytest.mark.asyncio
async def test_citation_analysis_ranks_papers(paper_sources):
    """Test that citation analysis ranks papers correctly."""
    agent = CitationAnalysisAgent()

    analyses = await agent.analyze(paper_sources)

    # Paper1 has 500 citations (rank 1)
    # Paper2 has 150 citations (rank 2)
    # Paper3 has 10 citations (rank 3)

    paper1_analysis = next(a for a in analyses if a.source_id == "paper1")
    paper2_analysis = next(a for a in analyses if a.source_id == "paper2")
    paper3_analysis = next(a for a in analyses if a.source_id == "paper3")

    assert paper1_analysis.metadata["citation_rank"] == 1
    assert paper2_analysis.metadata["citation_rank"] == 2
    assert paper3_analysis.metadata["citation_rank"] == 3


@pytest.mark.asyncio
async def test_citation_analysis_generates_insights(paper_sources):
    """Test that citation analysis generates meaningful insights."""
    agent = CitationAnalysisAgent()

    analyses = await agent.analyze(paper_sources)

    # High citation paper should have "influential" or similar
    paper1_analysis = next(a for a in analyses if a.source_id == "paper1")
    findings_text = " ".join(paper1_analysis.findings).lower()
    assert "500" in findings_text
    assert any(word in findings_text for word in ["influential", "cited", "seminal"])


# ---------------------------------------------------------------------------
# QualityScoreAgent Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_quality_score_agent_analyze(paper_sources):
    """Test quality scoring agent."""
    agent = QualityScoreAgent()

    analyses = await agent.analyze(paper_sources)

    assert len(analyses) == 3
    assert all(isinstance(a, Analysis) for a in analyses)
    assert all(a.analysis_type == "quality" for a in analyses)

    # Check quality score metadata
    for analysis in analyses:
        assert "quality_score" in analysis.metadata
        assert 0.0 <= analysis.metadata["quality_score"] <= 1.0


@pytest.mark.asyncio
async def test_quality_score_agent_scores_correctly(paper_sources):
    """Test that quality scores reflect source quality."""
    agent = QualityScoreAgent()

    analyses = await agent.analyze(paper_sources)

    # Paper1: NeurIPS venue, 500 citations, recent → high score
    paper1_analysis = next(a for a in analyses if a.source_id == "paper1")
    paper1_score = paper1_analysis.metadata["quality_score"]

    # Paper3: arXiv, 10 citations → lower score
    paper3_analysis = next(a for a in analyses if a.source_id == "paper3")
    paper3_score = paper3_analysis.metadata["quality_score"]

    # Paper1 should have higher quality score than Paper3
    assert paper1_score > paper3_score


@pytest.mark.asyncio
async def test_quality_score_agent_generates_insights(paper_sources):
    """Test that quality scoring generates insights."""
    agent = QualityScoreAgent()

    analyses = await agent.analyze(paper_sources)

    # High quality paper should have positive insights
    paper1_analysis = next(a for a in analyses if a.source_id == "paper1")
    findings_text = " ".join(paper1_analysis.findings).lower()

    assert any(
        word in findings_text
        for word in ["excellent", "good", "quality", "top-tier", "strong"]
    )


# ---------------------------------------------------------------------------
# Parallel Execution Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_parallel_analysis_execution(paper_sources, repo_sources):
    """Test parallel execution of multiple analysis agents."""
    agents = [
        PaperAnalysisAgent(),
        RepoAnalysisAgent(),
        CitationAnalysisAgent(),
        QualityScoreAgent(),
    ]

    all_sources = paper_sources + repo_sources

    # Execute all agents in parallel
    start = time.time()
    results = await asyncio.gather(
        *[agent.analyze(all_sources) for agent in agents]
    )
    elapsed = time.time() - start

    # All agents should complete
    assert len(results) == 4

    # Parallel execution should be fast
    assert elapsed < 1.0


@pytest.mark.asyncio
async def test_analysis_agents_complete_under_40s(paper_sources, repo_sources):
    """Test that 4 analysis agents complete in <40s (mocked)."""
    agents = [
        PaperAnalysisAgent(),
        RepoAnalysisAgent(),
        CitationAnalysisAgent(),
        QualityScoreAgent(),
    ]

    all_sources = paper_sources + repo_sources

    start = time.time()
    results = await asyncio.gather(
        *[agent.analyze(all_sources) for agent in agents]
    )
    elapsed = time.time() - start

    # Should complete quickly (no real API calls)
    assert elapsed < 1.0
    assert len(results) == 4


@pytest.mark.asyncio
async def test_mixed_agent_pipeline(paper_sources, repo_sources):
    """Test full pipeline: discovery → analysis."""
    # Simulate discovery phase (already have sources)
    all_sources = paper_sources + repo_sources

    # Analysis phase: run all 4 agents in parallel
    paper_agent = PaperAnalysisAgent()
    repo_agent = RepoAnalysisAgent()
    citation_agent = CitationAnalysisAgent()
    quality_agent = QualityScoreAgent()

    results = await asyncio.gather(
        paper_agent.analyze(all_sources),
        repo_agent.analyze(all_sources),
        citation_agent.analyze(all_sources),
        quality_agent.analyze(all_sources),
    )

    paper_analyses, repo_analyses, citation_analyses, quality_analyses = results

    # Verify results
    assert len(paper_analyses) == 3  # 3 papers
    assert len(repo_analyses) == 2  # 2 repos
    assert len(citation_analyses) == 3  # 3 papers (only papers have citations)
    assert len(quality_analyses) == 5  # All sources


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_10_agent_pipeline():
    """Test full pipeline with 6 discovery + 4 analysis agents."""
    # This is a high-level integration test
    # In production, this would coordinate all 10 agents

    # Simulate 6 discovery agents finding sources
    discovery_results = [
        [
            ResearchSource(
                id=f"source_{i}",
                title=f"Source {i}",
                source_type=SourceType.PAPER if i % 2 == 0 else SourceType.REPOSITORY,
                url=f"https://example.com/{i}",
                citations=100 * i if i % 2 == 0 else 0,
                stars=1000 * i if i % 2 == 1 else 0,
            )
        ]
        for i in range(6)
    ]

    # Flatten all sources
    all_sources = [s for sublist in discovery_results for s in sublist]

    # Run 4 analysis agents in parallel
    paper_agent = PaperAnalysisAgent()
    repo_agent = RepoAnalysisAgent()
    citation_agent = CitationAnalysisAgent()
    quality_agent = QualityScoreAgent()

    start = time.time()
    analyses = await asyncio.gather(
        paper_agent.analyze(all_sources),
        repo_agent.analyze(all_sources),
        citation_agent.analyze(all_sources),
        quality_agent.analyze(all_sources),
    )
    elapsed = time.time() - start

    # Verify all analyses completed
    assert len(analyses) == 4
    assert elapsed < 1.0  # Fast with mocked data

    # Verify analysis counts
    paper_analyses, repo_analyses, citation_analyses, quality_analyses = analyses
    assert len(paper_analyses) == 3  # 3 papers (even indices)
    assert len(repo_analyses) == 3  # 3 repos (odd indices)
    assert len(citation_analyses) == 3  # 3 papers
    assert len(quality_analyses) == 6  # All sources
