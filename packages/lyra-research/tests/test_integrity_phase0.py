"""
Tests for Integrity Gates (Phase 0)

Tests mandatory integrity gates, multi-layer citation verification,
and temporal verification.
"""

import pytest
from lyra_research.integrity.citation_verifier import (
    Citation,
    MultiLayerCitationVerifier,
)
from lyra_research.integrity.integrity_gate import IntegrityGate, Severity
from lyra_research.integrity.temporal_verifier import (
    TemporalVerifier,
    TemporalViolationType,
)
from lyra_research.integrity.validators import (
    CitationFidelityValidator,
    ClaimVerificationValidator,
    MinimumSourceCountValidator,
    SourceDiversityValidator,
    TemporalConsistencyValidator,
)


class TestIntegrityGate:
    """Test integrity gate functionality"""

    def test_stage_2_5_gate_passes_with_sufficient_sources(self):
        """Test stage 2.5 passes with sufficient sources"""
        gate = IntegrityGate(
            stage="2.5",
            validators=[
                MinimumSourceCountValidator(min_sources=10),
                SourceDiversityValidator(min_source_types=3),
            ],
        )

        research_state = {
            "sources": [{"id": f"s{i}", "source_type": "arxiv"} for i in range(5)]
            + [{"id": f"s{i}", "source_type": "github"} for i in range(5, 10)]
            + [{"id": f"s{i}", "source_type": "semantic_scholar"} for i in range(10, 15)]
        }

        result = gate.validate(research_state)
        assert result.passed
        assert result.stage == "2.5"
        assert len(result.blocking_issues) == 0

    def test_stage_2_5_gate_blocks_with_insufficient_sources(self):
        """Test stage 2.5 blocks with insufficient sources"""
        gate = IntegrityGate(stage="2.5", validators=[MinimumSourceCountValidator(min_sources=10)])

        research_state = {"sources": [{"id": f"s{i}"} for i in range(5)]}

        result = gate.validate(research_state)
        assert not result.passed
        assert len(result.blocking_issues) > 0
        assert result.blocking_issues[0].severity == Severity.CRITICAL

    def test_stage_4_5_gate_passes_with_valid_report(self):
        """Test stage 4.5 passes with valid report"""
        gate = IntegrityGate(
            stage="4.5",
            validators=[
                CitationFidelityValidator(min_fidelity=1.0),
                ClaimVerificationValidator(min_verification=0.95),
                TemporalConsistencyValidator(),
            ],
        )

        research_state = {
            "report": {
                "citations": [
                    {"id": "c1", "valid": True},
                    {"id": "c2", "valid": True},
                ],
                "claims": [
                    {"text": "Claim 1", "verified": True},
                    {"text": "Claim 2", "verified": True},
                ],
                "temporal_violations": [],
            }
        }

        result = gate.validate(research_state)
        assert result.passed
        assert result.stage == "4.5"

    def test_gate_cannot_be_skipped(self):
        """Test that gate cannot be skipped"""
        gate = IntegrityGate(stage="2.5", validators=[])
        assert gate.can_skip is False


class TestMultiLayerCitationVerifier:
    """Test multi-layer citation verification"""

    def test_verify_citation_with_all_layers(self):
        """Test citation verification with all 3 layers"""
        verifier = MultiLayerCitationVerifier()
        # Mock the API clients to simulate real behavior
        verifier.semantic_scholar = True
        verifier.openalex = True
        verifier.crossref = True

        citation = Citation(
            id="test1",
            title="Test Paper",
            authors=["Author 1"],
            year=2023,
            doi="10.1234/test",
            arxiv_id="2301.00000",
        )

        result = verifier.verify_citation(citation, "Test claim")
        # With mocked APIs, should pass all layers
        assert result.valid
        assert result.layers_passed == 3

    def test_citation_exists_layer(self):
        """Test layer 1: citation existence"""
        verifier = MultiLayerCitationVerifier()
        # Mock at least one API client
        verifier.semantic_scholar = True

        citation = Citation(
            id="test1", title="Test Paper", authors=["Author 1"], year=2023, doi="10.1234/test"
        )

        exists = verifier.verify_citation_exists(citation)
        assert exists  # Should find in at least one index

    def test_cross_index_triangulation(self):
        """Test layer 2: cross-index triangulation"""
        verifier = MultiLayerCitationVerifier()
        # Mock multiple API clients for triangulation
        verifier.semantic_scholar = True
        verifier.openalex = True

        citation = Citation(
            id="test1",
            title="Test Paper",
            authors=["Author 1"],
            year=2023,
            doi="10.1234/test",
            arxiv_id="2301.00000",
        )

        triangulated = verifier.cross_index_triangulation(citation)
        assert triangulated  # Should find in 2+ indexes


class TestTemporalVerifier:
    """Test temporal verification"""

    def test_detect_anachronistic_citations(self):
        """Test detection of anachronistic citations"""
        verifier = TemporalVerifier()
        report = {
            "claims": [
                {
                    "text": "X is better than Y",
                    "date": "2020-01-01",
                    "citations": [{"id": "c1", "published_date": "2023-01-01"}],  # Future citation!
                }
            ]
        }

        violations = verifier.detect_anachronistic_citations(report)
        assert len(violations) == 1
        assert violations[0].type == TemporalViolationType.ANACHRONISTIC_CITATION

    def test_detect_deictic_present(self):
        """Test detection of ambiguous temporal references"""
        verifier = TemporalVerifier()
        report = {
            "claims": [
                {"text": "Currently, X is the state-of-the-art"},
                {"text": "Recently, Y was proposed"},
            ]
        }

        violations = verifier.detect_deictic_present(report)
        assert len(violations) == 2
        assert all(v.type == TemporalViolationType.DEICTIC_PRESENT for v in violations)

    def test_no_violations_for_valid_report(self):
        """Test no violations for temporally consistent report"""
        verifier = TemporalVerifier()
        report = {
            "claims": [
                {
                    "text": "X was proposed in 2020",
                    "date": "2023-01-01",
                    "citations": [{"id": "c1", "published_date": "2020-01-01"}],
                }
            ]
        }

        violations = verifier.verify_temporal_consistency(report)
        # Should have no anachronistic citations
        anachronistic = [
            v for v in violations if v.type == TemporalViolationType.ANACHRONISTIC_CITATION
        ]
        assert len(anachronistic) == 0


class TestValidators:
    """Test individual validators"""

    def test_minimum_source_count_validator(self):
        """Test minimum source count validation"""
        validator = MinimumSourceCountValidator(min_sources=10)

        # Test pass
        result = validator.validate({"sources": [{"id": f"s{i}"} for i in range(15)]})
        assert result.passed

        # Test fail
        result = validator.validate({"sources": [{"id": f"s{i}"} for i in range(5)]})
        assert not result.passed
        assert result.severity == Severity.CRITICAL

    def test_source_diversity_validator(self):
        """Test source diversity validation"""
        validator = SourceDiversityValidator(min_source_types=3)

        # Test pass
        result = validator.validate(
            {
                "sources": [
                    {"source_type": "arxiv"},
                    {"source_type": "github"},
                    {"source_type": "semantic_scholar"},
                ]
            }
        )
        assert result.passed

        # Test fail
        result = validator.validate(
            {
                "sources": [
                    {"source_type": "arxiv"},
                    {"source_type": "arxiv"},
                ]
            }
        )
        assert not result.passed

    def test_citation_fidelity_validator(self):
        """Test citation fidelity validation"""
        validator = CitationFidelityValidator(min_fidelity=1.0)

        # Test pass
        result = validator.validate(
            {
                "report": {
                    "citations": [
                        {"id": "c1", "valid": True},
                        {"id": "c2", "valid": True},
                    ]
                }
            }
        )
        assert result.passed

        # Test fail
        result = validator.validate(
            {
                "report": {
                    "citations": [
                        {"id": "c1", "valid": True},
                        {"id": "c2", "valid": False},
                    ]
                }
            }
        )
        assert not result.passed
        assert result.severity == Severity.CRITICAL


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
