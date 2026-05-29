"""
Tests for Citation Verification System
"""

import pytest
from lyra_autoresearch.citations import (
    Citation,
    CitationVerifier,
    VerifyStatus,
    compute_title_similarity,
    parse_citations,
)


class TestTitleSimilarity:
    """Test title similarity computation"""

    def test_identical_titles(self):
        """Identical titles should have similarity 1.0"""
        title = "Deep Learning for Natural Language Processing"
        assert compute_title_similarity(title, title) == 1.0

    def test_completely_different(self):
        """Completely different titles should have similarity 0.0"""
        title_a = "Deep Learning for NLP"
        title_b = "Quantum Computing Algorithms"
        assert compute_title_similarity(title_a, title_b) == 0.0

    def test_partial_overlap(self):
        """Partial overlap should give intermediate similarity"""
        title_a = "Deep Learning for Natural Language Processing"
        title_b = "Deep Learning for Computer Vision"
        similarity = compute_title_similarity(title_a, title_b)
        assert 0.3 < similarity < 0.7

    def test_case_insensitive(self):
        """Should be case insensitive"""
        title_a = "Deep Learning"
        title_b = "deep learning"
        assert compute_title_similarity(title_a, title_b) == 1.0

    def test_punctuation_ignored(self):
        """Should ignore punctuation"""
        title_a = "Deep Learning: A Survey"
        title_b = "Deep Learning A Survey"
        assert compute_title_similarity(title_a, title_b) == 1.0


class TestCitationParsing:
    """Test citation parsing"""

    def test_parse_author_year(self):
        """Parse [Author, Year] format"""
        text = "As shown in [Smith et al., 2023], deep learning works."
        citations = parse_citations(text)
        assert len(citations) == 1
        assert citations[0].year == 2023

    def test_parse_arxiv_id(self):
        """Parse arXiv:XXXX.XXXXX format"""
        text = "See arXiv:2301.12345 for details."
        citations = parse_citations(text)
        assert len(citations) == 1
        assert citations[0].arxiv_id == "2301.12345"

    def test_parse_doi(self):
        """Parse doi:XX.XXXX/... format"""
        text = "Published as doi:10.1234/example.2023"
        citations = parse_citations(text)
        assert len(citations) == 1
        assert citations[0].doi == "10.1234/example.2023"

    def test_parse_multiple(self):
        """Parse multiple citations"""
        text = "[Smith, 2023] and arXiv:2301.12345 and doi:10.1234/test"
        citations = parse_citations(text)
        assert len(citations) == 3


@pytest.mark.integration
class TestCitationVerifier:
    """Integration tests for citation verifier (requires network)"""

    def test_verify_valid_arxiv(self):
        """Verify a valid arXiv citation"""
        citation = Citation(
            raw_text="arXiv:2301.12345",
            title="Attention Is All You Need",
            arxiv_id="1706.03762",
        )

        verifier = CitationVerifier()
        result = verifier.verify_citation(citation)

        # Should verify successfully
        assert result.status in [VerifyStatus.VERIFIED, VerifyStatus.SUSPICIOUS]
        assert result.similarity_score > 0.5

    def test_verify_hallucinated(self):
        """Verify a hallucinated citation"""
        citation = Citation(
            raw_text="fake",
            title="This Paper Does Not Exist At All",
            arxiv_id="9999.99999",
        )

        verifier = CitationVerifier()
        result = verifier.verify_citation(citation)

        # Should detect hallucination
        assert result.status == VerifyStatus.HALLUCINATED

    def test_skip_no_title(self):
        """Skip citation with no title"""
        citation = Citation(raw_text="unknown")

        verifier = CitationVerifier()
        result = verifier.verify_citation(citation)

        assert result.status == VerifyStatus.SKIPPED


class TestVerificationReport:
    """Test verification report generation"""

    def test_integrity_score(self):
        """Test integrity score computation"""
        citations = [
            Citation(raw_text="c1", title="Paper 1", arxiv_id="1111.11111"),
            Citation(raw_text="c2", title="Paper 2", arxiv_id="2222.22222"),
            Citation(raw_text="c3"),  # No title - skipped
        ]

        verifier = CitationVerifier()

        # Mock results
        from unittest.mock import patch

        def mock_verify(citation):
            if citation.title:
                from lyra_autoresearch.citations import VerificationResult
                return VerificationResult(
                    citation=citation,
                    status=VerifyStatus.VERIFIED,
                    similarity_score=0.9,
                )
            else:
                from lyra_autoresearch.citations import VerificationResult
                return VerificationResult(
                    citation=citation,
                    status=VerifyStatus.SKIPPED,
                    similarity_score=0.0,
                )

        with patch.object(verifier, 'verify_citation', side_effect=mock_verify):
            report = verifier.verify_document(citations)

        # 2 verified out of 2 verifiable (1 skipped)
        assert report.integrity_score == 1.0
        assert report.verified_count == 2
        assert report.skipped_count == 1
        assert report.total_count == 3
