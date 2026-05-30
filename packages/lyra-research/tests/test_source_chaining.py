"""
Integration tests for source chaining and evidence synthesis.

Tests cover:
- Citation network traversal
- Cross-source evidence linking
- Evidence quality assessment
- Contradiction detection
- Source reliability scoring
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone

from lyra_research.sources import (
    CitationTraversal,
    SourceQualityScorer,
)
from lyra_research.intelligence import ContradictionDetector
from lyra_research.synthesis import CrossSourceSynthesizer


class TestCitationNetworkTraversal:
    """Test citation network traversal and analysis."""

    @pytest.mark.integration
    def test_forward_citation_traversal(self):
        """Test traversing forward citations (papers citing this one)."""
        traversal = CitationTraversal()

        source_id = "arxiv:2605.20025"

        # Mock citation API
        with patch.object(traversal, '_fetch_forward_citations') as mock_fetch:
            mock_fetch.return_value = [
                {
                    "id": "arxiv:2606.10001",
                    "title": "Building on AutoResearchClaw",
                    "year": 2026,
                    "citations": 50
                },
                {
                    "id": "arxiv:2606.10002",
                    "title": "Extending Autonomous Research",
                    "year": 2026,
                    "citations": 30
                }
            ]

            citations = traversal.get_forward_citations(source_id, max_depth=1)

            assert len(citations) == 2
            assert all("id" in c for c in citations)
            assert all("title" in c for c in citations)

    @pytest.mark.integration
    def test_backward_citation_traversal(self):
        """Test traversing backward citations (papers this one cites)."""
        traversal = CitationTraversal()

        source_id = "arxiv:2605.20025"

        with patch.object(traversal, '_fetch_backward_citations') as mock_fetch:
            mock_fetch.return_value = [
                {
                    "id": "arxiv:2604.10001",
                    "title": "Foundation of Multi-Agent Systems",
                    "year": 2025,
                    "citations": 200
                },
                {
                    "id": "arxiv:2603.05001",
                    "title": "Self-Healing Mechanisms",
                    "year": 2025,
                    "citations": 150
                }
            ]

            references = traversal.get_backward_citations(source_id, max_depth=1)

            assert len(references) == 2
            assert all("id" in r for r in references)

    @pytest.mark.integration
    def test_multi_hop_citation_chain(self):
        """Test building multi-hop citation chains."""
        traversal = CitationTraversal()

        # Mock citation network
        citation_network = {
            "arxiv:2605.20025": [
                {"id": "arxiv:2606.10001", "title": "Paper A"},
                {"id": "arxiv:2606.10002", "title": "Paper B"}
            ],
            "arxiv:2606.10001": [
                {"id": "arxiv:2607.10001", "title": "Paper C"}
            ],
            "arxiv:2606.10002": [
                {"id": "arxiv:2607.10002", "title": "Paper D"}
            ]
        }

        def mock_fetch(paper_id):
            return citation_network.get(paper_id, [])

        with patch.object(traversal, '_fetch_forward_citations', side_effect=mock_fetch):
            chain = traversal.build_citation_chain("arxiv:2605.20025", max_depth=2)

            assert len(chain) >= 3  # Seed + hop1 + hop2
            assert chain[0]["id"] == "arxiv:2605.20025"

    @pytest.mark.integration
    def test_citation_quality_filtering(self):
        """Test filtering low-quality citations."""
        traversal = CitationTraversal(min_citation_count=10)

        citations = [
            {"id": "arxiv:2606.10001", "citations": 50},  # High quality
            {"id": "arxiv:2606.10002", "citations": 5},   # Low quality
            {"id": "arxiv:2606.10003", "citations": 20},  # High quality
        ]

        filtered = traversal.filter_by_quality(citations)

        assert len(filtered) == 2
        assert all(c["citations"] >= 10 for c in filtered)


class TestCrossSourceEvidenceLinking:
    """Test linking evidence across multiple sources."""

    @pytest.mark.integration
    def test_link_evidence_across_papers(self):
        """Test linking related evidence from multiple papers."""
        linker = EvidenceLinker()

        papers = [
            {
                "id": "arxiv:2605.20025",
                "claims": ["Multi-agent systems improve performance"],
                "evidence": ["Experiment showed 20% improvement"]
            },
            {
                "id": "arxiv:2606.10001",
                "claims": ["Multi-agent coordination is effective"],
                "evidence": ["Benchmark results: 25% better"]
            }
        ]

        links = linker.link_evidence(papers)

        assert len(links) > 0
        assert all("source_ids" in link for link in links)
        assert all("common_claim" in link for link in links)

    @pytest.mark.integration
    def test_evidence_strength_scoring(self):
        """Test scoring evidence strength across sources."""
        linker = EvidenceLinker()

        evidence = {
            "claim": "Multi-agent systems improve performance",
            "sources": [
                {"id": "arxiv:2605.20025", "evidence_type": "experimental", "sample_size": 1000},
                {"id": "arxiv:2606.10001", "evidence_type": "experimental", "sample_size": 500},
                {"id": "arxiv:2607.10001", "evidence_type": "theoretical", "sample_size": None}
            ]
        }

        strength = linker.score_evidence_strength(evidence)

        assert 0.0 <= strength <= 1.0
        assert strength > 0.7  # Strong evidence from multiple sources

    @pytest.mark.integration
    def test_cross_source_validation(self):
        """Test validating claims across multiple sources."""
        linker = EvidenceLinker()

        claim = "LLM agents can use tools effectively"

        sources = [
            {"id": "arxiv:2605.20025", "supports": True, "confidence": 0.9},
            {"id": "arxiv:2606.10001", "supports": True, "confidence": 0.85},
            {"id": "arxiv:2607.10001", "supports": True, "confidence": 0.8}
        ]

        validation = linker.validate_claim(claim, sources)

        assert validation["is_validated"]
        assert validation["confidence"] > 0.8
        assert validation["source_count"] == 3


class TestContradictionDetection:
    """Test detecting contradictions across sources."""

    @pytest.mark.integration
    def test_detect_direct_contradiction(self):
        """Test detecting direct contradictions."""
        detector = ContradictionDetector()

        sources = [
            {
                "id": "arxiv:2605.20025",
                "claim": "Method A outperforms Method B",
                "evidence": "Accuracy: A=92%, B=85%"
            },
            {
                "id": "arxiv:2606.10001",
                "claim": "Method B outperforms Method A",
                "evidence": "Accuracy: B=90%, A=82%"
            }
        ]

        contradictions = detector.detect_contradictions(sources)

        assert len(contradictions) > 0
        assert contradictions[0]["type"] == "direct"
        assert len(contradictions[0]["sources"]) == 2

    @pytest.mark.integration
    def test_detect_partial_contradiction(self):
        """Test detecting partial contradictions."""
        detector = ContradictionDetector()

        sources = [
            {
                "id": "arxiv:2605.20025",
                "claim": "Multi-agent systems always improve performance",
                "evidence": "100% of cases showed improvement"
            },
            {
                "id": "arxiv:2606.10001",
                "claim": "Multi-agent systems sometimes improve performance",
                "evidence": "70% of cases showed improvement"
            }
        ]

        contradictions = detector.detect_contradictions(sources)

        assert len(contradictions) > 0
        assert contradictions[0]["type"] == "partial"

    @pytest.mark.integration
    def test_contradiction_resolution(self):
        """Test resolving contradictions with additional evidence."""
        detector = ContradictionDetector()

        contradiction = {
            "claim": "Method effectiveness",
            "sources": [
                {"id": "arxiv:2605.20025", "position": "effective"},
                {"id": "arxiv:2606.10001", "position": "ineffective"}
            ]
        }

        # Add resolving evidence
        additional_sources = [
            {"id": "arxiv:2607.10001", "position": "effective", "quality": 0.9},
            {"id": "arxiv:2607.10002", "position": "effective", "quality": 0.85}
        ]

        resolution = detector.resolve_contradiction(contradiction, additional_sources)

        assert resolution["resolved"]
        assert resolution["consensus"] == "effective"


class TestSourceReliabilityScoring:
    """Test scoring source reliability."""

    @pytest.mark.integration
    def test_paper_reliability_score(self):
        """Test scoring paper reliability."""
        scorer = SourceQualityScorer()

        paper = {
            "id": "arxiv:2605.20025",
            "venue": "NeurIPS",
            "citations": 150,
            "year": 2026,
            "authors": ["Author A", "Author B"],
            "has_code": True,
            "has_data": True
        }

        reliability = scorer.score_reliability(paper)

        assert 0.0 <= reliability <= 1.0
        assert reliability > 0.8  # High reliability

    @pytest.mark.integration
    def test_repository_reliability_score(self):
        """Test scoring repository reliability."""
        scorer = SourceQualityScorer()

        repo = {
            "id": "github:org/repo",
            "stars": 5000,
            "forks": 800,
            "contributors": 50,
            "has_tests": True,
            "test_coverage": 85,
            "has_ci": True,
            "last_commit": "2026-05-20"
        }

        reliability = scorer.score_reliability(repo)

        assert 0.0 <= reliability <= 1.0
        assert reliability > 0.8  # High reliability

    @pytest.mark.integration
    def test_reliability_temporal_decay(self):
        """Test reliability decay over time."""
        scorer = SourceQualityScorer()

        # Recent paper
        recent_paper = {
            "id": "arxiv:2605.20025",
            "year": 2026,
            "citations": 100
        }

        # Old paper
        old_paper = {
            "id": "arxiv:2020.10001",
            "year": 2020,
            "citations": 100
        }

        recent_score = scorer.score_reliability(recent_paper)
        old_score = scorer.score_reliability(old_paper)

        # Recent should score higher (all else equal)
        assert recent_score >= old_score


class TestEvidenceSynthesis:
    """Test synthesizing evidence from multiple sources."""

    @pytest.mark.integration
    def test_synthesize_converging_evidence(self):
        """Test synthesizing evidence that converges."""
        synthesizer = CrossSourceSynthesizer()

        sources = [
            {
                "id": "arxiv:2605.20025",
                "finding": "Multi-agent systems improve performance by 20%",
                "confidence": 0.9
            },
            {
                "id": "arxiv:2606.10001",
                "finding": "Multi-agent coordination increases efficiency by 25%",
                "confidence": 0.85
            },
            {
                "id": "arxiv:2607.10001",
                "finding": "Agent collaboration boosts results by 18%",
                "confidence": 0.8
            }
        ]

        synthesis = synthesizer.synthesize_evidence(sources)

        assert synthesis["consensus"] is not None
        assert synthesis["confidence"] > 0.8
        assert len(synthesis["supporting_sources"]) == 3

    @pytest.mark.integration
    def test_synthesize_diverging_evidence(self):
        """Test synthesizing evidence that diverges."""
        synthesizer = CrossSourceSynthesizer()

        sources = [
            {
                "id": "arxiv:2605.20025",
                "finding": "Method A is best",
                "confidence": 0.9
            },
            {
                "id": "arxiv:2606.10001",
                "finding": "Method B is best",
                "confidence": 0.85
            }
        ]

        synthesis = synthesizer.synthesize_evidence(sources)

        assert synthesis["has_divergence"]
        assert len(synthesis["perspectives"]) == 2

    @pytest.mark.integration
    def test_evidence_quality_weighting(self):
        """Test weighting evidence by source quality."""
        synthesizer = CrossSourceSynthesizer()

        sources = [
            {
                "id": "arxiv:2605.20025",
                "finding": "Claim A",
                "quality": 0.95,  # High quality
                "confidence": 0.9
            },
            {
                "id": "arxiv:2606.10001",
                "finding": "Claim B",
                "quality": 0.6,   # Low quality
                "confidence": 0.9
            }
        ]

        synthesis = synthesizer.synthesize_evidence(sources, weight_by_quality=True)

        # High quality source should dominate
        assert "Claim A" in synthesis["consensus"]


class TestSourceChainIntegration:
    """Integration tests for complete source chaining workflow."""

    @pytest.mark.integration
    def test_complete_source_chain_workflow(self):
        """Test complete workflow: discovery → linking → synthesis."""
        # 1. Discover sources
        traversal = CitationTraversal()
        seed_id = "arxiv:2605.20025"

        with patch.object(traversal, '_fetch_forward_citations') as mock_fetch:
            mock_fetch.return_value = [
                {"id": "arxiv:2606.10001", "title": "Paper A"},
                {"id": "arxiv:2606.10002", "title": "Paper B"}
            ]

            sources = traversal.get_forward_citations(seed_id, max_depth=1)

        # 2. Link evidence
        linker = EvidenceLinker()
        links = linker.link_evidence(sources)

        # 3. Synthesize
        synthesizer = CrossSourceSynthesizer()
        synthesis = synthesizer.synthesize_evidence(sources)

        assert len(sources) > 0
        assert synthesis is not None

    @pytest.mark.integration
    def test_chain_with_contradiction_handling(self):
        """Test source chain with contradiction detection and resolution."""
        # Discover sources with contradictions
        sources = [
            {"id": "arxiv:2605.20025", "claim": "Method A is best"},
            {"id": "arxiv:2606.10001", "claim": "Method B is best"}
        ]

        # Detect contradictions
        detector = ContradictionDetector()
        contradictions = detector.detect_contradictions(sources)

        assert len(contradictions) > 0

        # Resolve with additional evidence
        additional = [
            {"id": "arxiv:2607.10001", "claim": "Method A is best", "quality": 0.9}
        ]

        resolution = detector.resolve_contradiction(contradictions[0], additional)

        assert resolution["resolved"]

    @pytest.mark.integration
    def test_chain_quality_filtering(self):
        """Test filtering low-quality sources in chain."""
        sources = [
            {"id": "arxiv:2605.20025", "quality": 0.9},  # Keep
            {"id": "arxiv:2606.10001", "quality": 0.4},  # Filter
            {"id": "arxiv:2607.10001", "quality": 0.85}, # Keep
        ]

        scorer = SourceQualityScorer()
        filtered = scorer.filter_by_quality(sources, min_quality=0.7)

        assert len(filtered) == 2
        assert all(s["quality"] >= 0.7 for s in filtered)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
