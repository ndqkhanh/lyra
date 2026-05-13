"""
Tests for enhanced source adapters (sources.py).

All HTTP calls are mocked so tests run fully offline.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from lyra_research.discovery import ResearchSource, SourceType
from lyra_research.sources import (
    ACLAnthologyDiscovery,
    CitationTraversal,
    GitHubActivityScorer,
    HuggingFacePapersDiscovery,
    OpenReviewDiscovery,
    PapersWithCodeDiscovery,
    SourceQualityScorer,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_response(json_data, status_code=200):
    """Return a mock requests.Response with the given JSON body."""
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = json_data
    mock.headers = {}
    return mock


# ---------------------------------------------------------------------------
# OpenReview
# ---------------------------------------------------------------------------

class TestOpenReviewDiscovery:
    def test_openreview_discovery_returns_list(self):
        """search() returns a list of ResearchSource on success."""
        payload = {
            "notes": [
                {
                    "id": "abc123",
                    "cdate": int(datetime(2024, 1, 1).timestamp() * 1000),
                    "content": {
                        "title": "Test Paper",
                        "abstract": "An abstract.",
                        "authors": ["Alice", "Bob"],
                        "venue": "ICLR.cc",
                    },
                }
            ]
        }
        with patch("requests.get", return_value=_mock_response(payload)):
            discovery = OpenReviewDiscovery()
            results = discovery.search("transformers", max_results=5)

        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0].source_type == SourceType.PAPER
        assert results[0].title == "Test Paper"
        assert results[0].id == "abc123"
        assert results[0].authors == ["Alice", "Bob"]
        assert results[0].metadata["venue"] == "ICLR.cc"

    def test_openreview_discovery_returns_empty_on_error(self):
        """search() returns [] when the API returns a non-200 status."""
        with patch("requests.get", return_value=_mock_response({}, status_code=500)):
            discovery = OpenReviewDiscovery()
            results = discovery.search("anything")

        assert results == []

    def test_openreview_discovery_returns_empty_on_exception(self):
        """search() returns [] when requests raises an exception."""
        with patch("requests.get", side_effect=Exception("network error")):
            discovery = OpenReviewDiscovery()
            results = discovery.search("anything")

        assert results == []


# ---------------------------------------------------------------------------
# HuggingFace Papers
# ---------------------------------------------------------------------------

class TestHuggingFacePapersDiscovery:
    def test_huggingface_papers_discovery_returns_list(self):
        """search() returns a list of ResearchSource on success."""
        payload = [
            {
                "id": "2401.00001",
                "title": "HF Test Paper",
                "summary": "HF abstract.",
                "authors": [{"name": "Carol"}],
                "publishedAt": "2024-01-15T00:00:00Z",
                "upvotes": 42,
            }
        ]
        with patch("requests.get", return_value=_mock_response(payload)):
            discovery = HuggingFacePapersDiscovery()
            results = discovery.search("language model", max_results=5)

        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0].source_type == SourceType.PAPER
        assert results[0].title == "HF Test Paper"
        assert results[0].citations == 42
        assert results[0].id == "2401.00001"

    def test_huggingface_discovery_returns_empty_on_error(self):
        """search() returns [] on non-200 response."""
        with patch("requests.get", return_value=_mock_response({}, status_code=404)):
            discovery = HuggingFacePapersDiscovery()
            results = discovery.search("anything")

        assert results == []

    def test_huggingface_discovery_returns_empty_on_exception(self):
        """search() returns [] on network exception."""
        with patch("requests.get", side_effect=Exception("timeout")):
            discovery = HuggingFacePapersDiscovery()
            results = discovery.search("anything")

        assert results == []

    def test_huggingface_daily_papers_returns_list(self):
        """get_daily_papers() returns a list of ResearchSource."""
        payload = [
            {
                "id": "2401.99999",
                "title": "Daily Paper",
                "summary": "Daily abstract.",
                "authors": [],
                "publishedAt": "2024-06-01T00:00:00Z",
                "upvotes": 10,
            }
        ]
        with patch("requests.get", return_value=_mock_response(payload)):
            discovery = HuggingFacePapersDiscovery()
            results = discovery.get_daily_papers()

        assert isinstance(results, list)
        assert results[0].title == "Daily Paper"


# ---------------------------------------------------------------------------
# Papers with Code
# ---------------------------------------------------------------------------

class TestPapersWithCodeDiscovery:
    def test_papers_with_code_discovery_returns_list(self):
        """search() returns a list of ResearchSource on success."""
        payload = {
            "results": [
                {
                    "id": "pwc-001",
                    "title": "PWC Paper",
                    "abstract": "PWC abstract.",
                    "authors": ["Dave"],
                    "published": "2023-05-10",
                    "url_abs": "https://paperswithcode.com/paper/pwc-001",
                    "repositories": [{"url": "https://github.com/foo/bar"}],
                    "tasks": ["image classification"],
                    "methods": ["ResNet"],
                    "sota": True,
                }
            ]
        }
        with patch("requests.get", return_value=_mock_response(payload)):
            discovery = PapersWithCodeDiscovery()
            results = discovery.search("image classification", max_results=5)

        assert isinstance(results, list)
        assert len(results) == 1
        src = results[0]
        assert src.source_type == SourceType.PAPER
        assert src.title == "PWC Paper"
        assert src.metadata["github_links"] == ["https://github.com/foo/bar"]
        assert src.metadata["sota_results"] is True

    def test_papers_with_code_returns_empty_on_error(self):
        """search() returns [] on non-200 response."""
        with patch("requests.get", return_value=_mock_response({}, status_code=503)):
            discovery = PapersWithCodeDiscovery()
            results = discovery.search("anything")

        assert results == []

    def test_papers_with_code_returns_empty_on_exception(self):
        """search() returns [] on exception."""
        with patch("requests.get", side_effect=RuntimeError("conn refused")):
            discovery = PapersWithCodeDiscovery()
            results = discovery.search("anything")

        assert results == []


# ---------------------------------------------------------------------------
# ACL Anthology
# ---------------------------------------------------------------------------

class TestACLAnthologyDiscovery:
    def test_acl_anthology_discovery_returns_list(self):
        """search() returns ACL-venue papers only."""
        payload = {
            "data": [
                {
                    "paperId": "ss-acl-001",
                    "title": "ACL Paper",
                    "abstract": "ACL abstract.",
                    "authors": [{"name": "Eve"}],
                    "year": 2023,
                    "citationCount": 15,
                    "url": "https://example.com/paper1",
                    "venue": "ACL",
                    "externalIds": {"ACL": "2023.acl-main.1"},
                },
                {
                    "paperId": "ss-neurips-001",
                    "title": "NeurIPS Paper",
                    "abstract": "NeurIPS abstract.",
                    "authors": [{"name": "Frank"}],
                    "year": 2023,
                    "citationCount": 50,
                    "url": "https://example.com/paper2",
                    "venue": "NeurIPS",
                    "externalIds": {},
                },
            ]
        }
        with patch("requests.get", return_value=_mock_response(payload)):
            discovery = ACLAnthologyDiscovery()
            results = discovery.search("machine translation", max_results=10)

        # Only ACL-venue paper should be returned
        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0].title == "ACL Paper"
        assert results[0].metadata["anthology_id"] == "2023.acl-main.1"

    def test_acl_anthology_returns_empty_on_error(self):
        """search() returns [] on non-200 response."""
        with patch("requests.get", return_value=_mock_response({}, status_code=429)):
            discovery = ACLAnthologyDiscovery()
            results = discovery.search("anything")

        assert results == []

    def test_acl_anthology_returns_empty_on_exception(self):
        """search() returns [] on exception."""
        with patch("requests.get", side_effect=Exception("timeout")):
            discovery = ACLAnthologyDiscovery()
            results = discovery.search("anything")

        assert results == []


# ---------------------------------------------------------------------------
# Citation traversal
# ---------------------------------------------------------------------------

class TestCitationTraversal:
    def _make_paper(self, paper_id: str, title: str) -> dict:
        return {
            "paperId": paper_id,
            "title": title,
            "abstract": "",
            "authors": [],
            "year": 2023,
            "citationCount": 0,
            "url": f"https://example.com/{paper_id}",
            "venue": "",
        }

    def test_citation_traversal_get_citations(self):
        """get_citations() returns papers that cite the seed."""
        payload = {
            "data": [
                {"citingPaper": self._make_paper("citing-001", "Citing Paper 1")},
                {"citingPaper": self._make_paper("citing-002", "Citing Paper 2")},
            ]
        }
        with patch("requests.get", return_value=_mock_response(payload)):
            traversal = CitationTraversal()
            results = traversal.get_citations("seed-001", max_results=10)

        assert isinstance(results, list)
        assert len(results) == 2
        assert results[0].title == "Citing Paper 1"
        assert results[0].source_type == SourceType.PAPER

    def test_citation_traversal_get_references(self):
        """get_references() returns papers cited by the seed."""
        payload = {
            "data": [
                {"citedPaper": self._make_paper("ref-001", "Reference Paper 1")},
            ]
        }
        with patch("requests.get", return_value=_mock_response(payload)):
            traversal = CitationTraversal()
            results = traversal.get_references("seed-001", max_results=10)

        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0].title == "Reference Paper 1"

    def test_citation_traversal_get_citations_returns_empty_on_error(self):
        """get_citations() returns [] on non-200 response."""
        with patch("requests.get", return_value=_mock_response({}, status_code=404)):
            traversal = CitationTraversal()
            results = traversal.get_citations("bad-id")

        assert results == []

    def test_citation_traversal_snowball(self):
        """snowball() does BFS and deduplicates results."""
        # First call: citations for seed
        citations_payload = {
            "data": [{"citingPaper": self._make_paper("hop1-001", "Hop1 Citing")}]
        }
        # Second call: references for seed
        refs_payload = {
            "data": [{"citedPaper": self._make_paper("hop1-002", "Hop1 Reference")}]
        }
        # Subsequent calls for depth-2 hops return empty
        empty_payload = {"data": []}

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _mock_response(citations_payload)
            elif call_count == 2:
                return _mock_response(refs_payload)
            else:
                return _mock_response(empty_payload)

        with patch("requests.get", side_effect=side_effect):
            traversal = CitationTraversal()
            results = traversal.snowball("seed-001", depth=2, max_per_hop=5)

        assert isinstance(results, list)
        # Should contain the two hop-1 papers (deduplicated)
        ids = {r.id for r in results}
        assert "hop1-001" in ids
        assert "hop1-002" in ids

    def test_citation_traversal_snowball_deduplicates(self):
        """snowball() does not include the same paper twice."""
        same_paper = self._make_paper("dup-001", "Duplicate Paper")
        citations_payload = {"data": [{"citingPaper": same_paper}]}
        refs_payload = {"data": [{"citedPaper": same_paper}]}

        responses = [
            _mock_response(citations_payload),
            _mock_response(refs_payload),
            _mock_response({"data": []}),
            _mock_response({"data": []}),
        ]

        with patch("requests.get", side_effect=responses):
            traversal = CitationTraversal()
            results = traversal.snowball("seed-001", depth=1, max_per_hop=10)

        ids = [r.id for r in results]
        assert ids.count("dup-001") == 1


# ---------------------------------------------------------------------------
# GitHub activity scorer
# ---------------------------------------------------------------------------

class TestGitHubActivityScorer:
    def test_github_activity_scorer_score(self):
        """score() returns a float in [0.0, 1.0]."""
        scorer = GitHubActivityScorer()
        result = scorer.score(
            {
                "stars": 5000,
                "commits_per_month": 50,
                "contributors": 25,
                "closed_issues_ratio": 0.8,
            }
        )
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0

    def test_github_activity_scorer_score_zero(self):
        """score() returns 0.0 for a repo with no activity."""
        scorer = GitHubActivityScorer()
        result = scorer.score(
            {
                "stars": 0,
                "commits_per_month": 0,
                "contributors": 0,
                "closed_issues_ratio": 0.0,
            }
        )
        assert result == 0.0

    def test_github_activity_scorer_score_max(self):
        """score() returns 1.0 for a maximally active repo."""
        scorer = GitHubActivityScorer()
        result = scorer.score(
            {
                "stars": 100_000,
                "commits_per_month": 1_000,
                "contributors": 500,
                "closed_issues_ratio": 1.0,
            }
        )
        assert result == pytest.approx(1.0, abs=1e-9)

    def test_github_activity_scorer_uses_stargazers_count_key(self):
        """score() accepts 'stargazers_count' as an alias for 'stars'."""
        scorer = GitHubActivityScorer()
        result = scorer.score({"stargazers_count": 10_000, "commits_per_month": 100})
        assert result > 0.0

    def test_enrich_source_adds_activity_score(self):
        """enrich_source() enriches metadata with activity_score."""
        source = ResearchSource(
            id="123",
            title="my/repo",
            source_type=SourceType.REPOSITORY,
            url="https://github.com/myorg/myrepo",
            stars=500,
        )

        commits_response = _mock_response([{"sha": "a"}, {"sha": "b"}])
        contributors_response = _mock_response([{"login": "u1"}, {"login": "u2"}, {"login": "u3"}])
        repo_response = _mock_response({"open_issues_count": 5})
        closed_issues_response = _mock_response([])
        closed_issues_response.headers = {}

        responses = [commits_response, contributors_response, repo_response, closed_issues_response]

        with patch("requests.get", side_effect=responses):
            scorer = GitHubActivityScorer()
            enriched = scorer.enrich_source(source)

        assert "activity_score" in enriched.metadata
        assert isinstance(enriched.metadata["activity_score"], float)
        assert 0.0 <= enriched.metadata["activity_score"] <= 1.0
        # Original source is not mutated
        assert "activity_score" not in source.metadata


# ---------------------------------------------------------------------------
# Source quality scorer
# ---------------------------------------------------------------------------

class TestSourceQualityScorer:
    def _make_source(
        self,
        title: str = "Test Paper",
        abstract: str = "test abstract",
        citations: int = 100,
        published_year: int = 2024,
        venue: str = "NeurIPS",
    ) -> ResearchSource:
        return ResearchSource(
            id="test-001",
            title=title,
            source_type=SourceType.PAPER,
            url="https://example.com",
            abstract=abstract,
            citations=citations,
            published_date=datetime(published_year, 1, 1),
            metadata={"venue": venue},
        )

    def test_source_quality_scorer_rank(self):
        """rank() returns sources sorted by score descending."""
        scorer = SourceQualityScorer()
        high = self._make_source(
            title="attention mechanism", citations=5000, venue="NeurIPS", published_year=2024
        )
        low = self._make_source(
            title="unrelated topic", citations=0, venue="arXiv", published_year=2010
        )
        ranked = scorer.rank([low, high], query="attention mechanism")

        assert isinstance(ranked, list)
        assert len(ranked) == 2
        # High-quality source should rank first
        assert ranked[0][0].title == "attention mechanism"
        # Scores are in descending order
        assert ranked[0][1] >= ranked[1][1]

    def test_source_quality_scorer_score_range(self):
        """score() always returns a value in [0.0, 1.0]."""
        scorer = SourceQualityScorer()
        source = self._make_source()
        s = scorer.score(source, "test query")
        assert 0.0 <= s <= 1.0

    def test_source_quality_scorer_venue_tiers(self):
        """Higher-tier venues yield higher venue scores."""
        scorer = SourceQualityScorer()
        neurips = self._make_source(venue="NeurIPS")
        arxiv = self._make_source(venue="arXiv")

        score_neurips = scorer._venue_score(neurips)
        score_arxiv = scorer._venue_score(arxiv)

        assert score_neurips > score_arxiv

    def test_source_quality_scorer_recency(self):
        """Recent papers yield higher recency scores than old ones."""
        scorer = SourceQualityScorer()
        recent = self._make_source(published_year=2024)
        old = self._make_source(published_year=2010)

        assert scorer._recency_score(recent) > scorer._recency_score(old)

    def test_source_quality_scorer_citation_score(self):
        """Papers with more citations yield higher citation scores."""
        scorer = SourceQualityScorer()
        highly_cited = self._make_source(citations=5000)
        low_cited = self._make_source(citations=1)

        assert scorer._citation_score(highly_cited) > scorer._citation_score(low_cited)

    def test_source_quality_scorer_relevance(self):
        """Relevance score increases when query terms appear in title/abstract."""
        scorer = SourceQualityScorer()
        relevant = self._make_source(title="attention is all you need", abstract="transformer attention")
        irrelevant = self._make_source(title="cooking recipes", abstract="pasta and sauce")

        r_score = scorer._relevance_score(relevant, "attention transformer")
        i_score = scorer._relevance_score(irrelevant, "attention transformer")

        assert r_score > i_score

    def test_source_quality_scorer_rank_returns_tuples(self):
        """rank() returns list of (ResearchSource, float) tuples."""
        scorer = SourceQualityScorer()
        sources = [self._make_source(citations=10), self._make_source(citations=100)]
        ranked = scorer.rank(sources, query="test")

        assert all(isinstance(item, tuple) for item in ranked)
        assert all(isinstance(item[0], ResearchSource) for item in ranked)
        assert all(isinstance(item[1], float) for item in ranked)
