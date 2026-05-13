"""
Tests for research discovery engines.
"""

import pytest
from lyra_research.discovery import (
    ArXivDiscovery,
    GitHubDiscovery,
    MultiSourceDiscovery,
    SemanticScholarDiscovery,
    SourceType,
)


def test_arxiv_discovery():
    """Test ArXiv discovery."""
    discovery = ArXivDiscovery()
    results = discovery.search("transformer architecture", max_results=5)

    assert isinstance(results, list)
    if results:  # May be empty if API is down
        assert results[0].source_type == SourceType.PAPER
        assert results[0].title
        assert results[0].url


def test_semantic_scholar_discovery():
    """Test Semantic Scholar discovery."""
    discovery = SemanticScholarDiscovery()
    results = discovery.search("attention mechanism", max_results=5)

    assert isinstance(results, list)
    if results:
        assert results[0].source_type == SourceType.PAPER
        assert results[0].title


def test_github_discovery():
    """Test GitHub discovery."""
    discovery = GitHubDiscovery()
    results = discovery.search("machine learning", max_results=5)

    assert isinstance(results, list)
    if results:
        assert results[0].source_type == SourceType.REPOSITORY
        assert results[0].title
        assert results[0].stars >= 0


def test_multi_source_discovery():
    """Test multi-source discovery."""
    discovery = MultiSourceDiscovery()
    results = discovery.discover(
        "neural networks",
        sources=["arxiv", "github"],
        max_per_source=3,
    )

    assert isinstance(results, dict)
    assert "arxiv" in results or "github" in results


def test_discover_all():
    """Test discover_all method."""
    discovery = MultiSourceDiscovery()
    results = discovery.discover_all("deep learning", max_per_source=3)

    assert isinstance(results, list)
    # Should have results from multiple sources
    if results:
        source_types = {r.source_type for r in results}
        assert len(source_types) >= 1
