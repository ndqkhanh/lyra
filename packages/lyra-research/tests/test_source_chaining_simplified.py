"""
Integration tests for source chaining and quality scoring.

Tests cover:
- Citation network traversal (CitationTraversal)
- Source quality scoring (SourceQualityScorer)
- GitHub activity scoring (GitHubActivityScorer)
- Cross-source synthesis (CrossSourceSynthesizer from reporter.py)
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock

from lyra_research.sources import (
    CitationTraversal,
    SourceQualityScorer,
    GitHubActivityScorer,
)
from lyra_research.reporter import CrossSourceSynthesizer
from lyra_research.discovery import ResearchSource, SourceType


@pytest.fixture
def mock_paper_sources():
    """Create mock paper sources for testing."""
    return [
        ResearchSource(
            id="paper-1",
            title="Multi-Agent Systems",
            source_type=SourceType.PAPER,
            url="https://arxiv.org/abs/2605.20025",
            abstract="Research on multi-agent systems",
            citations=150,
            published_date=datetime(2026, 1, 1),
            metadata={"venue": "NeurIPS", "year": 2026},
        ),
        ResearchSource(
            id="paper-2",
            title="Agent Coordination",
            source_type=SourceType.PAPER,
            url="https://arxiv.org/abs/2606.10001",
            abstract="Coordination mechanisms for agents",
            citations=80,
            published_date=datetime(2025, 6, 1),
            metadata={"venue": "ICML", "year": 2025},
        ),
    ]


class TestCitationTraversal:
    """Test citation network traversal."""

    @pytest.mark.integration
    def test_get_citations_with_mock(self):
        """Test getting forward citations (papers that cite this one)."""
        traversal = CitationTraversal()

        mock_response = {
            "data": [
                {
                    "citingPaper": {
                        "paperId": "citing-1",
                        "title": "Building on Previous Work",
                        "abstract": "This extends the original paper",
                        "authors": [{"name": "Author A"}],
                        "year": 2026,
                        "citationCount": 50,
                        "url": "https://example.com/citing-1",
                        "venue": "ACL",
                    }
                }
            ]
        }

        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_response

            citations = traversal.get_citations("test-paper-id", max_results=20)

            assert len(citations) == 1
            assert citations[0].id == "citing-1"
            assert citations[0].title == "Building on Previous Work"

    @pytest.mark.integration
    def test_get_references_with_mock(self):
        """Test getting backward references (papers this one cites)."""
        traversal = CitationTraversal()

        mock_response = {
            "data": [
                {
                    "citedPaper": {
                        "paperId": "cited-1",
                        "title": "Foundation Work",
                        "abstract": "Original research",
                        "authors": [{"name": "Author B"}],
                        "year": 2024,
                        "citationCount": 200,
                        "url": "https://example.com/cited-1",
                        "venue": "NeurIPS",
                    }
                }
            ]
        }

        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_response

            references = traversal.get_references("test-paper-id", max_results=20)

            assert len(references) == 1
            assert references[0].id == "cited-1"
            assert references[0].title == "Foundation Work"

    @pytest.mark.integration
    def test_snowball_traversal(self):
        """Test BFS citation traversal (snowball sampling)."""
        traversal = CitationTraversal()

        # Mock responses for multi-hop traversal
        def mock_get_side_effect(url, **kwargs):
            mock_resp = Mock()
            mock_resp.status_code = 200

            if "citations" in url:
                mock_resp.json.return_value = {"data": []}
            elif "references" in url:
                mock_resp.json.return_value = {"data": []}
            else:
                mock_resp.json.return_value = {"data": []}

            return mock_resp

        with patch('requests.get', side_effect=mock_get_side_effect):
            sources = traversal.snowball("seed-paper", depth=2, max_per_hop=5)

            # Should return list (may be empty with mocked responses)
            assert isinstance(sources, list)


class TestSourceQualityScoring:
    """Test source quality scoring."""

    def test_score_high_quality_paper(self, mock_paper_sources):
        """Test scoring a high-quality paper."""
        scorer = SourceQualityScorer()

        source = mock_paper_sources[0]  # NeurIPS paper with 150 citations
        score = scorer.score(source, query="multi-agent systems")

        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Should score well

    def test_score_recent_paper_higher(self):
        """Test recent papers score higher than old papers."""
        scorer = SourceQualityScorer()

        recent = ResearchSource(
            id="recent",
            title="Recent Work",
            source_type=SourceType.PAPER,
            url="https://example.com/recent",
            abstract="Recent research",
            citations=50,
            published_date=datetime(2026, 1, 1),
            metadata={"venue": "NeurIPS", "year": 2026},
        )

        old = ResearchSource(
            id="old",
            title="Old Work",
            source_type=SourceType.PAPER,
            url="https://example.com/old",
            abstract="Old research",
            citations=50,
            published_date=datetime(2020, 1, 1),
            metadata={"venue": "NeurIPS", "year": 2020},
        )

        recent_score = scorer.score(recent, query="research")
        old_score = scorer.score(old, query="research")

        assert recent_score >= old_score

    def test_rank_sources(self, mock_paper_sources):
        """Test ranking multiple sources by quality."""
        scorer = SourceQualityScorer()

        ranked = scorer.rank(mock_paper_sources, query="multi-agent")

        assert len(ranked) == 2
        assert all(isinstance(item, tuple) for item in ranked)
        assert all(len(item) == 2 for item in ranked)

        # First source should have higher score (more citations, better venue)
        assert ranked[0][1] >= ranked[1][1]


class TestGitHubActivityScoring:
    """Test GitHub repository activity scoring."""

    def test_score_repository_metadata(self):
        """Test scoring repository from metadata."""
        scorer = GitHubActivityScorer()

        repo_metadata = {
            "stars": 5000,
            "commits_per_month": 50,
            "contributors": 30,
            "closed_issues_ratio": 0.8,
        }

        score = scorer.score(repo_metadata)

        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Active repo should score well

    def test_score_inactive_repository(self):
        """Test scoring inactive repository."""
        scorer = GitHubActivityScorer()

        repo_metadata = {
            "stars": 10,
            "commits_per_month": 0,
            "contributors": 1,
            "closed_issues_ratio": 0.1,
        }

        score = scorer.score(repo_metadata)

        assert 0.0 <= score <= 1.0
        assert score < 0.3  # Inactive repo should score low


class TestCrossSourceSynthesis:
    """Test cross-source synthesis from reporter.py."""

    def test_synthesize_papers(self):
        """Test synthesizing findings from multiple papers."""
        synthesizer = CrossSourceSynthesizer()

        paper_analyses = [
            {
                "source_id": "paper-1",
                "title": "Multi-Agent Systems",
                "abstract": "Research on coordination",
                "findings": ["Finding A", "Finding B"],
            },
            {
                "source_id": "paper-2",
                "title": "Agent Coordination",
                "abstract": "Coordination mechanisms",
                "findings": ["Finding C", "Finding D"],
            },
        ]

        synthesis = synthesizer.synthesize(
            topic="Multi-agent systems",
            paper_analyses=paper_analyses,
            repo_analyses=[],
            gaps=[],
            contradictions=[],
        )

        assert synthesis is not None
        assert synthesis.topic == "Multi-agent systems"
        assert synthesis.source_count == 2

    def test_synthesis_quality_score(self):
        """Test synthesis quality scoring."""
        synthesizer = CrossSourceSynthesizer()

        # More sources should produce higher quality
        many_papers = [
            {"source_id": f"paper-{i}", "title": f"Paper {i}", "abstract": f"Abstract {i}"}
            for i in range(20)
        ]

        synthesis = synthesizer.synthesize(
            topic="Test topic",
            paper_analyses=many_papers,
            repo_analyses=[],
            gaps=[],
            contradictions=[],
        )

        assert 0.0 <= synthesis.synthesis_quality <= 1.0


class TestSourceChainIntegration:
    """Integration tests for complete source chaining workflow."""

    @pytest.mark.integration
    def test_discover_rank_synthesize_workflow(self, mock_paper_sources):
        """Test complete workflow: rank sources → synthesize."""
        # 1. Rank sources
        scorer = SourceQualityScorer()
        ranked = scorer.rank(mock_paper_sources, query="multi-agent")

        assert len(ranked) > 0

        # 2. Synthesize
        synthesizer = CrossSourceSynthesizer()
        paper_analyses = [
            {
                "source_id": s.id,
                "title": s.title,
                "abstract": s.abstract,
            }
            for s, _ in ranked
        ]

        synthesis = synthesizer.synthesize(
            topic="Multi-agent systems",
            paper_analyses=paper_analyses,
            repo_analyses=[],
            gaps=[],
            contradictions=[],
        )

        assert synthesis is not None
        assert synthesis.source_count == len(ranked)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
