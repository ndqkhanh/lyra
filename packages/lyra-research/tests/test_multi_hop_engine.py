"""
Unit tests for multi-hop research engine.

Tests cover:
- Query refinement and expansion
- Multi-hop traversal logic
- Stopping criteria
- Source chaining
- Citation network traversal
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone

from lyra_research.orchestrator import ResearchOrchestrator, ResearchProgress
from lyra_research.discovery import MultiSourceDiscovery, ResearchSource
from lyra_research.sources import SourceQualityScorer


class TestQueryRefinement:
    """Test query refinement and expansion for multi-hop research."""

    def test_initial_query_normalization(self):
        """Test normalizing initial research query."""
        orchestrator = ResearchOrchestrator()

        # Test whitespace normalization
        query = orchestrator._normalize_query("  LLM agents  ")
        assert query == "LLM agents"

        # Test newline removal
        query = orchestrator._normalize_query("LLM\nagents")
        assert query == "LLM agents"

        # Test tab removal
        query = orchestrator._normalize_query("LLM\tagents")
        assert query == "LLM agents"

    def test_query_expansion_with_context(self):
        """Test expanding query with discovered context."""
        orchestrator = ResearchOrchestrator()

        initial_query = "LLM agents"
        context = ["multi-agent systems", "tool use", "memory"]

        # Expand query with context
        expanded = orchestrator._expand_query(initial_query, context)

        assert "LLM agents" in expanded
        assert any(term in expanded.lower() for term in ["multi-agent", "tool", "memory"])

    def test_query_refinement_for_next_hop(self):
        """Test refining query for next research hop."""
        orchestrator = ResearchOrchestrator()

        current_query = "LLM reasoning"
        findings = ["chain-of-thought", "self-consistency", "tree-of-thoughts"]

        refined = orchestrator._refine_query_for_hop(current_query, findings)

        assert refined != current_query
        assert any(finding in refined for finding in findings)


class TestMultiHopTraversal:
    """Test multi-hop research traversal logic."""

    def test_single_hop_research(self):
        """Test single-hop research (quick mode)."""
        orchestrator = ResearchOrchestrator()
        orchestrator.max_hops = 1

        # Mock discovery
        with patch.object(orchestrator.discovery, 'discover') as mock_discover:
            mock_discover.return_value = {
                "arxiv": [
                    ResearchSource(
                        id="arxiv:2605.20025",
                        title="Test Paper",
                        abstract="Test abstract",
                        url="https://arxiv.org/abs/2605.20025",
                        source_type="arxiv"
                    )
                ]
            }

            progress = orchestrator._execute_hop(
                query="LLM agents",
                hop_number=1,
                sources=["arxiv"]
            )

            assert progress.current_hop == 1
            assert progress.sources_found["arxiv"] > 0
            mock_discover.assert_called_once()

    def test_multi_hop_progression(self):
        """Test progression through multiple research hops."""
        orchestrator = ResearchOrchestrator()
        orchestrator.max_hops = 3

        hops_executed = []

        def mock_hop(query, hop_num, sources):
            hops_executed.append(hop_num)
            return Mock(current_hop=hop_num, should_continue=hop_num < 3)

        with patch.object(orchestrator, '_execute_hop', side_effect=mock_hop):
            orchestrator._multi_hop_research("LLM agents", ["arxiv"])

            assert len(hops_executed) == 3
            assert hops_executed == [1, 2, 3]

    def test_hop_context_accumulation(self):
        """Test accumulating context across hops."""
        orchestrator = ResearchOrchestrator()

        # Hop 1 findings
        hop1_findings = ["multi-agent", "coordination"]
        orchestrator._add_hop_findings(1, hop1_findings)

        # Hop 2 findings
        hop2_findings = ["tool use", "memory"]
        orchestrator._add_hop_findings(2, hop2_findings)

        # Get accumulated context
        context = orchestrator._get_accumulated_context()

        assert all(f in context for f in hop1_findings)
        assert all(f in context for f in hop2_findings)


class TestStoppingCriteria:
    """Test research stopping criteria."""

    def test_max_hops_reached(self):
        """Test stopping when max hops reached."""
        orchestrator = ResearchOrchestrator()
        orchestrator.max_hops = 3

        # Should stop at hop 3
        assert orchestrator._should_stop_research(
            current_hop=3,
            sources_found=10,
            quality_score=0.8
        )

        # Should continue at hop 2
        assert not orchestrator._should_stop_research(
            current_hop=2,
            sources_found=10,
            quality_score=0.8
        )

    def test_sufficient_sources_found(self):
        """Test stopping when sufficient sources found."""
        orchestrator = ResearchOrchestrator()
        orchestrator.max_hops = 5
        orchestrator.min_sources = 30

        # Should stop with 40 sources
        assert orchestrator._should_stop_research(
            current_hop=2,
            sources_found=40,
            quality_score=0.8
        )

        # Should continue with 20 sources
        assert not orchestrator._should_stop_research(
            current_hop=2,
            sources_found=20,
            quality_score=0.8
        )

    def test_quality_threshold_met(self):
        """Test stopping when quality threshold met."""
        orchestrator = ResearchOrchestrator()
        orchestrator.max_hops = 5
        orchestrator.quality_threshold = 0.85

        # Should stop with high quality
        assert orchestrator._should_stop_research(
            current_hop=2,
            sources_found=25,
            quality_score=0.90
        )

        # Should continue with low quality
        assert not orchestrator._should_stop_research(
            current_hop=2,
            sources_found=25,
            quality_score=0.70
        )

    def test_diminishing_returns_detection(self):
        """Test detecting diminishing returns in research."""
        orchestrator = ResearchOrchestrator()

        # Hop 1: 20 sources
        orchestrator._record_hop_results(1, sources_count=20)

        # Hop 2: 5 new sources (diminishing)
        orchestrator._record_hop_results(2, sources_count=5)

        # Hop 3: 2 new sources (severe diminishing)
        orchestrator._record_hop_results(3, sources_count=2)

        # Should detect diminishing returns
        assert orchestrator._has_diminishing_returns()


class TestSourceChaining:
    """Test source chaining and citation traversal."""

    def test_forward_citation_discovery(self):
        """Test discovering papers that cite a source."""
        orchestrator = ResearchOrchestrator()

        source_id = "arxiv:2605.20025"

        with patch.object(orchestrator, '_get_forward_citations') as mock_citations:
            mock_citations.return_value = [
                {"id": "arxiv:2606.10001", "title": "Citing Paper 1"},
                {"id": "arxiv:2606.10002", "title": "Citing Paper 2"},
            ]

            citations = orchestrator._discover_forward_citations(source_id)

            assert len(citations) == 2
            assert all("id" in c for c in citations)
            mock_citations.assert_called_once_with(source_id)

    def test_backward_citation_discovery(self):
        """Test discovering papers cited by a source."""
        orchestrator = ResearchOrchestrator()

        source_id = "arxiv:2605.20025"

        with patch.object(orchestrator, '_get_backward_citations') as mock_refs:
            mock_refs.return_value = [
                {"id": "arxiv:2604.10001", "title": "Referenced Paper 1"},
                {"id": "arxiv:2604.10002", "title": "Referenced Paper 2"},
            ]

            references = orchestrator._discover_backward_citations(source_id)

            assert len(references) == 2
            assert all("id" in r for r in references)
            mock_refs.assert_called_once_with(source_id)

    def test_citation_chain_building(self):
        """Test building citation chains across hops."""
        orchestrator = ResearchOrchestrator()

        # Start with seed paper
        seed_id = "arxiv:2605.20025"

        # Mock citation network
        citation_network = {
            "arxiv:2605.20025": ["arxiv:2606.10001", "arxiv:2606.10002"],
            "arxiv:2606.10001": ["arxiv:2607.10001"],
            "arxiv:2606.10002": ["arxiv:2607.10002"],
        }

        def mock_get_citations(paper_id):
            return citation_network.get(paper_id, [])

        with patch.object(orchestrator, '_get_forward_citations', side_effect=mock_get_citations):
            chain = orchestrator._build_citation_chain(seed_id, max_depth=2)

            assert len(chain) >= 3  # Seed + hop1 + hop2
            assert chain[0] == seed_id

    def test_citation_cycle_detection(self):
        """Test detecting cycles in citation networks."""
        orchestrator = ResearchOrchestrator()

        # Create circular citation
        citation_network = {
            "arxiv:2605.20025": ["arxiv:2606.10001"],
            "arxiv:2606.10001": ["arxiv:2607.10001"],
            "arxiv:2607.10001": ["arxiv:2605.20025"],  # Cycle back
        }

        def mock_get_citations(paper_id):
            return citation_network.get(paper_id, [])

        with patch.object(orchestrator, '_get_forward_citations', side_effect=mock_get_citations):
            chain = orchestrator._build_citation_chain("arxiv:2605.20025", max_depth=5)

            # Should stop at cycle
            assert len(chain) < 10  # Would be infinite without cycle detection
            assert len(set(chain)) == len(chain)  # No duplicates


class TestSourceQualityScoring:
    """Test source quality scoring for multi-hop research."""

    def test_paper_quality_score(self):
        """Test scoring paper quality."""
        scorer = SourceQualityScorer()

        high_quality_paper = {
            "id": "arxiv:2605.20025",
            "title": "AutoResearchClaw",
            "citations": 150,
            "year": 2026,
            "venue": "NeurIPS",
        }

        score = scorer.score_paper(high_quality_paper, query="autonomous research")

        assert 0.0 <= score <= 1.0
        assert score > 0.7  # High quality

    def test_repository_quality_score(self):
        """Test scoring repository quality."""
        scorer = SourceQualityScorer()

        high_quality_repo = {
            "id": "github:org/repo",
            "stars": 5000,
            "forks": 800,
            "last_updated": "2026-05-01",
            "has_readme": True,
            "has_tests": True,
            "has_ci": True,
        }

        score = scorer.score_repository(high_quality_repo)

        assert 0.0 <= score <= 1.0
        assert score > 0.7  # High quality

    def test_relevance_weighting(self):
        """Test query relevance weighting in scores."""
        scorer = SourceQualityScorer()

        paper = {
            "id": "arxiv:2605.20025",
            "title": "LLM Agent Systems",
            "abstract": "Multi-agent systems for LLM coordination",
            "citations": 100,
            "year": 2026,
        }

        # High relevance query
        score_high = scorer.score_paper(paper, query="LLM agents")

        # Low relevance query
        score_low = scorer.score_paper(paper, query="quantum computing")

        assert score_high > score_low


class TestHopCoordination:
    """Test coordination between research hops."""

    def test_hop_transition_timing(self):
        """Test timing between research hops."""
        orchestrator = ResearchOrchestrator()

        start_time = datetime.now(timezone.utc)

        # Execute hop 1
        orchestrator._start_hop(1)
        orchestrator._end_hop(1)

        # Execute hop 2
        orchestrator._start_hop(2)
        orchestrator._end_hop(2)

        # Check timing
        hop1_duration = orchestrator._get_hop_duration(1)
        hop2_duration = orchestrator._get_hop_duration(2)

        assert hop1_duration > 0
        assert hop2_duration > 0

    def test_hop_result_aggregation(self):
        """Test aggregating results across hops."""
        orchestrator = ResearchOrchestrator()

        # Hop 1 results
        orchestrator._add_hop_results(1, sources=10, papers=8, quality=0.75)

        # Hop 2 results
        orchestrator._add_hop_results(2, sources=15, papers=12, quality=0.80)

        # Aggregate
        total = orchestrator._aggregate_hop_results()

        assert total["sources"] == 25
        assert total["papers"] == 20
        assert total["avg_quality"] > 0.75


class TestErrorRecovery:
    """Test error recovery in multi-hop research."""

    def test_hop_failure_recovery(self):
        """Test recovering from hop failure."""
        orchestrator = ResearchOrchestrator()

        # Mock hop that fails
        def failing_hop(*args, **kwargs):
            raise RuntimeError("API error")

        with patch.object(orchestrator, '_execute_hop', side_effect=failing_hop):
            # Should retry and recover
            with patch.object(orchestrator, '_retry_hop') as mock_retry:
                mock_retry.return_value = Mock(success=True)

                result = orchestrator._execute_hop_with_recovery(
                    query="test",
                    hop_number=1,
                    sources=["arxiv"]
                )

                mock_retry.assert_called()

    def test_partial_hop_results(self):
        """Test handling partial results from failed hop."""
        orchestrator = ResearchOrchestrator()

        # Hop partially succeeds (some sources fail)
        partial_results = {
            "arxiv": [Mock()],  # Success
            "github": None,  # Failed
        }

        processed = orchestrator._process_partial_results(partial_results)

        assert "arxiv" in processed
        assert len(processed["arxiv"]) > 0
        # Failed sources should be excluded
        assert "github" not in processed or processed["github"] == []


class TestProgressTracking:
    """Test progress tracking during multi-hop research."""

    def test_progress_initialization(self):
        """Test initializing research progress."""
        progress = ResearchProgress(
            session_id="test-123",
            topic="LLM agents",
            depth="standard"
        )

        assert progress.session_id == "test-123"
        assert progress.topic == "LLM agents"
        assert progress.current_hop == 0
        assert not progress.is_complete

    def test_progress_updates_during_hops(self):
        """Test updating progress during research hops."""
        progress = ResearchProgress(
            session_id="test-123",
            topic="LLM agents",
            depth="standard"
        )

        # Update for hop 1
        progress.update_hop(1, sources_found=10, papers_analyzed=8)

        assert progress.current_hop == 1
        assert progress.sources_found_total == 10
        assert progress.papers_analyzed == 8

        # Update for hop 2
        progress.update_hop(2, sources_found=15, papers_analyzed=12)

        assert progress.current_hop == 2
        assert progress.sources_found_total == 25
        assert progress.papers_analyzed == 20

    def test_progress_completion(self):
        """Test marking research as complete."""
        progress = ResearchProgress(
            session_id="test-123",
            topic="LLM agents",
            depth="standard"
        )

        progress.mark_complete(
            report=Mock(),
            quality_score=0.85
        )

        assert progress.is_complete
        assert progress.report is not None
        assert progress.quality_score == 0.85


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
