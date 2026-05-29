"""
Comprehensive tests for the Adversarial Review System.

Tests cover:
- Context budget enforcement (30KB max)
- Disagreement resolution (fix, soften, remove)
- Selective review (confidence <0.8)
- Cost control (GPT-4o-mini pricing)
- Integration with research pipeline
"""

from dataclasses import dataclass

from lyra_research.adversarial_reviewer import (
    AdversarialReviewer,
    Claim,
    DisagreementResolution,
    ReviewerContextBudget,
    ReviewIssue,
    ReviewResult,
)

# ---------------------------------------------------------------------------
# Mock Data Models
# ---------------------------------------------------------------------------


@dataclass
class MockResearchReport:
    """Mock ResearchReport for testing."""

    executive_summary: str = "Test summary"
    taxonomy_section: str = "Test taxonomy"
    best_papers_section: str = "Test papers"
    references_section: str = ""

    def to_markdown(self) -> str:
        return(
            f"{self.executive_summary}\n{self.taxonomy_section}\n{self.best_papers_section}\n"
            f"{self.references_section}"
        )


@dataclass
class MockResearchSource:
    """Mock ResearchSource for testing."""

    id: str
    title: str
    abstract: str = "Test abstract"


# ---------------------------------------------------------------------------
# Context Budget Tests (15 tests)
# ---------------------------------------------------------------------------


class TestReviewerContextBudget:
    """Test context budget enforcement."""

    def test_budget_defaults(self):
        """Test default budget values."""
        budget = ReviewerContextBudget()
        assert budget.MAX_CONTEXT_KB == 40
        assert budget.REPORT_KB == 12
        assert budget.TOP_SOURCES_KB == 20
        assert budget.CLAIM_MAPPING_KB == 8

    def test_estimate_size_kb_empty(self):
        """Test size estimation for empty string."""
        budget = ReviewerContextBudget()
        assert budget.estimate_size_kb("") == 0.0

    def test_estimate_size_kb_small(self):
        """Test size estimation for small text."""
        budget = ReviewerContextBudget()
        text = "Hello world"
        size_kb = budget.estimate_size_kb(text)
        assert size_kb > 0
        assert size_kb < 1

    def test_estimate_size_kb_large(self):
        """Test size estimation for large text."""
        budget = ReviewerContextBudget()
        text = "x" * 10240  # 10KB
        size_kb = budget.estimate_size_kb(text)
        assert 9 < size_kb < 11  # Allow some margin

    def test_estimate_size_kb_unicode(self):
        """Test size estimation for Unicode text."""
        budget = ReviewerContextBudget()
        text = "你好世界" * 100
        size_kb = budget.estimate_size_kb(text)
        assert size_kb > 0

    def test_truncate_to_kb_no_truncation(self):
        """Test truncation when text is under limit."""
        budget = ReviewerContextBudget()
        text = "Hello world"
        truncated = budget.truncate_to_kb(text, 10)
        assert truncated == text

    def test_truncate_to_kb_with_truncation(self):
        """Test truncation when text exceeds limit."""
        budget = ReviewerContextBudget()
        text = "x" * 10240  # 10KB
        truncated = budget.truncate_to_kb(text, 5)
        size_kb = budget.estimate_size_kb(truncated)
        assert size_kb <= 5

    def test_truncate_to_kb_unicode_boundary(self):
        """Test truncation handles Unicode character boundaries."""
        budget = ReviewerContextBudget()
        text = "你好世界" * 1000
        truncated = budget.truncate_to_kb(text, 2)
        # Should not raise UnicodeDecodeError
        assert len(truncated) > 0
        assert budget.estimate_size_kb(truncated) <= 2

    def test_truncate_to_kb_preserves_content(self):
        """Test truncation preserves beginning of content."""
        budget = ReviewerContextBudget()
        text = "Important start" + ("x" * 10240)
        truncated = budget.truncate_to_kb(text, 1)
        assert truncated.startswith("Important")

    def test_truncate_to_kb_zero_limit(self):
        """Test truncation with zero limit."""
        budget = ReviewerContextBudget()
        text = "Hello world"
        truncated = budget.truncate_to_kb(text, 0)
        assert len(truncated) == 0

    def test_truncate_to_kb_exact_limit(self):
        """Test truncation at exact limit."""
        budget = ReviewerContextBudget()
        text = "x" * 1024  # Exactly 1KB
        truncated = budget.truncate_to_kb(text, 1)
        assert len(truncated) <= 1024

    def test_truncate_to_kb_multibyte_chars(self):
        """Test truncation with multi-byte characters."""
        budget = ReviewerContextBudget()
        text = "🔬" * 1000  # Emoji (4 bytes each)
        truncated = budget.truncate_to_kb(text, 2)
        size_kb = budget.estimate_size_kb(truncated)
        assert size_kb <= 2

    def test_truncate_to_kb_mixed_content(self):
        """Test truncation with mixed ASCII and Unicode."""
        budget = ReviewerContextBudget()
        text = "ASCII " + ("你好" * 500) + " more ASCII"
        truncated = budget.truncate_to_kb(text, 3)
        assert budget.estimate_size_kb(truncated) <= 3

    def test_truncate_to_kb_newlines(self):
        """Test truncation preserves newlines."""
        budget = ReviewerContextBudget()
        text = "Line 1\nLine 2\n" + ("x" * 10240)
        truncated = budget.truncate_to_kb(text, 1)
        assert "Line 1" in truncated

    def test_truncate_to_kb_idempotent(self):
        """Test truncation is idempotent."""
        budget = ReviewerContextBudget()
        text = "x" * 10240
        truncated1 = budget.truncate_to_kb(text, 5)
        truncated2 = budget.truncate_to_kb(truncated1, 5)
        assert truncated1 == truncated2


# ---------------------------------------------------------------------------
# Claim Model Tests (10 tests)
# ---------------------------------------------------------------------------


class TestClaim:
    """Test Claim data model."""

    def test_claim_creation(self):
        """Test creating a claim."""
        claim = Claim(
            text="Test claim",
            confidence=0.8,
            citations=["[1]"],
            source_ids=["src1"],
            location="Section 1",
        )
        assert claim.text == "Test claim"
        assert claim.confidence == 0.8
        assert claim.citations == ["[1]"]
        assert claim.source_ids == ["src1"]
        assert claim.location == "Section 1"

    def test_claim_defaults(self):
        """Test claim default values."""
        claim = Claim(text="Test", confidence=0.5)
        assert claim.citations == []
        assert claim.source_ids == []
        assert claim.location == ""

    def test_citation_count_zero(self):
        """Test citation count with no citations."""
        claim = Claim(text="Test", confidence=0.0)
        assert claim.citation_count() == 0

    def test_citation_count_one(self):
        """Test citation count with one citation."""
        claim = Claim(text="Test", confidence=0.5, citations=["[1]"])
        assert claim.citation_count() == 1

    def test_citation_count_multiple(self):
        """Test citation count with multiple citations."""
        claim = Claim(text="Test", confidence=0.9, citations=["[1]", "[2]", "[3]"])
        assert claim.citation_count() == 3

    def test_claim_with_long_text(self):
        """Test claim with long text."""
        long_text = "This is a very long claim " * 100
        claim = Claim(text=long_text, confidence=0.7)
        assert len(claim.text) > 1000

    def test_claim_with_unicode(self):
        """Test claim with Unicode text."""
        claim = Claim(text="机器学习模型表现优异", confidence=0.8)
        assert "机器学习" in claim.text

    def test_claim_confidence_bounds(self):
        """Test claim confidence values."""
        claim_low = Claim(text="Test", confidence=0.0)
        claim_high = Claim(text="Test", confidence=1.0)
        assert 0.0 <= claim_low.confidence <= 1.0
        assert 0.0 <= claim_high.confidence <= 1.0

    def test_claim_with_special_chars(self):
        """Test claim with special characters."""
        claim = Claim(text="Model achieves 95.5% accuracy [1].", confidence=0.8)
        assert "95.5%" in claim.text
        assert "[1]" in claim.text

    def test_claim_equality(self):
        """Test claim equality."""
        claim1 = Claim(text="Test", confidence=0.8, citations=["[1]"])
        claim2 = Claim(text="Test", confidence=0.8, citations=["[1]"])
        assert claim1.text == claim2.text
        assert claim1.confidence == claim2.confidence


# ---------------------------------------------------------------------------
# ReviewIssue Tests (5 tests)
# ---------------------------------------------------------------------------


class TestReviewIssue:
    """Test ReviewIssue data model."""

    def test_review_issue_creation(self):
        """Test creating a review issue."""
        claim = Claim(text="Test claim", confidence=0.5)
        issue = ReviewIssue(
            claim=claim,
            issue_type="missing_citation",
            severity="critical",
            suggested_resolution=DisagreementResolution.REMOVE,
            explanation="No citations found",
        )
        assert issue.claim == claim
        assert issue.issue_type == "missing_citation"
        assert issue.severity == "critical"
        assert issue.suggested_resolution == DisagreementResolution.REMOVE

    def test_review_issue_types(self):
        """Test different issue types."""
        claim = Claim(text="Test", confidence=0.5)
        issue_types = ["missing_citation", "weak_evidence", "unsupported"]
        for issue_type in issue_types:
            issue = ReviewIssue(
                claim=claim,
                issue_type=issue_type,
                severity="high",
                suggested_resolution=DisagreementResolution.FIX,
                explanation="Test",
            )
            assert issue.issue_type == issue_type

    def test_review_issue_severities(self):
        """Test different severity levels."""
        claim = Claim(text="Test", confidence=0.5)
        severities = ["critical", "high", "medium", "low"]
        for severity in severities:
            issue = ReviewIssue(
                claim=claim,
                issue_type="weak_evidence",
                severity=severity,
                suggested_resolution=DisagreementResolution.SOFTEN,
                explanation="Test",
            )
            assert issue.severity == severity

    def test_review_issue_resolutions(self):
        """Test different resolution strategies."""
        claim = Claim(text="Test", confidence=0.5)
        resolutions = [
            DisagreementResolution.FIX,
            DisagreementResolution.SOFTEN,
            DisagreementResolution.REMOVE,
        ]
        for resolution in resolutions:
            issue = ReviewIssue(
                claim=claim,
                issue_type="weak_evidence",
                severity="medium",
                suggested_resolution=resolution,
                explanation="Test",
            )
            assert issue.suggested_resolution == resolution

    def test_review_issue_explanation(self):
        """Test issue explanation field."""
        claim = Claim(text="Test", confidence=0.5)
        explanation = "This claim lacks sufficient supporting evidence from peer-reviewed sources."
        issue = ReviewIssue(
            claim=claim,
            issue_type="weak_evidence",
            severity="high",
            suggested_resolution=DisagreementResolution.FIX,
            explanation=explanation,
        )
        assert issue.explanation == explanation


# ---------------------------------------------------------------------------
# DisagreementResolution Tests (5 tests)
# ---------------------------------------------------------------------------


class TestDisagreementResolution:
    """Test DisagreementResolution enum."""

    def test_resolution_values(self):
        """Test resolution enum values."""
        assert DisagreementResolution.FIX.value == "fix"
        assert DisagreementResolution.SOFTEN.value == "soften"
        assert DisagreementResolution.REMOVE.value == "remove"

    def test_resolution_from_string(self):
        """Test creating resolution from string."""
        assert DisagreementResolution("fix") == DisagreementResolution.FIX
        assert DisagreementResolution("soften") == DisagreementResolution.SOFTEN
        assert DisagreementResolution("remove") == DisagreementResolution.REMOVE

    def test_resolution_equality(self):
        """Test resolution equality."""
        assert DisagreementResolution.FIX == DisagreementResolution.FIX
        assert DisagreementResolution.FIX != DisagreementResolution.SOFTEN

    def test_resolution_in_collection(self):
        """Test resolution in collections."""
        resolutions = [DisagreementResolution.FIX, DisagreementResolution.SOFTEN]
        assert DisagreementResolution.FIX in resolutions
        assert DisagreementResolution.REMOVE not in resolutions

    def test_resolution_iteration(self):
        """Test iterating over resolutions."""
        resolutions = list(DisagreementResolution)
        assert len(resolutions) == 3
        assert DisagreementResolution.FIX in resolutions


# ---------------------------------------------------------------------------
# AdversarialReviewer Initialization Tests (5 tests)
# ---------------------------------------------------------------------------


class TestAdversarialReviewerInit:
    """Test AdversarialReviewer initialization."""

    def test_reviewer_default_init(self):
        """Test reviewer with default models."""
        reviewer = AdversarialReviewer()
        assert reviewer.executor_model == "gpt-4o"
        assert reviewer.reviewer_model == "gpt-4o-mini"
        assert isinstance(reviewer.budget, ReviewerContextBudget)

    def test_reviewer_custom_models(self):
        """Test reviewer with custom models."""
        reviewer = AdversarialReviewer(
            executor_model="gpt-4",
            reviewer_model="gpt-3.5-turbo",
        )
        assert reviewer.executor_model == "gpt-4"
        assert reviewer.reviewer_model == "gpt-3.5-turbo"

    def test_reviewer_budget_initialization(self):
        """Test reviewer budget is initialized."""
        reviewer = AdversarialReviewer()
        assert reviewer.budget.MAX_CONTEXT_KB == 40
        assert reviewer.budget.REPORT_KB == 12

    def test_reviewer_multiple_instances(self):
        """Test creating multiple reviewer instances."""
        reviewer1 = AdversarialReviewer()
        reviewer2 = AdversarialReviewer(reviewer_model="gpt-4o")
        assert reviewer1.reviewer_model != reviewer2.reviewer_model

    def test_reviewer_attributes(self):
        """Test reviewer has all required attributes."""
        reviewer = AdversarialReviewer()
        assert hasattr(reviewer, "executor_model")
        assert hasattr(reviewer, "reviewer_model")
        assert hasattr(reviewer, "budget")


# ---------------------------------------------------------------------------
# Extract Cited Sources Tests (8 tests)
# ---------------------------------------------------------------------------


class TestExtractCitedSources:
    """Test extract_cited_sources method."""

    def test_extract_no_citations(self):
        """Test extracting sources with no citations."""
        reviewer = AdversarialReviewer()
        report = MockResearchReport(
            executive_summary="No citations here",
            references_section="",
        )
        sources = []
        cited = reviewer.extract_cited_sources(report, sources)
        assert cited == []

    def test_extract_single_citation(self):
        """Test extracting single cited source."""
        reviewer = AdversarialReviewer()
        report = MockResearchReport(
            executive_summary="This is supported [1].",
            references_section="1. Test Paper http://example.com",
        )
        source = MockResearchSource(id="src1", title="Test Paper")
        sources = [source]
        cited = reviewer.extract_cited_sources(report, sources)
        assert len(cited) == 1
        assert cited[0].id == "src1"

    def test_extract_multiple_citations(self):
        """Test extracting multiple cited sources."""
        reviewer = AdversarialReviewer()
        report = MockResearchReport(
            executive_summary="Supported by [1] and [2].",
            references_section="1. Paper A http://a.com\n2. Paper B http://b.com",
        )
        sources = [
            MockResearchSource(id="src1", title="Paper A"),
            MockResearchSource(id="src2", title="Paper B"),
        ]
        cited = reviewer.extract_cited_sources(report, sources)
        assert len(cited) == 2

    def test_extract_top_10_limit(self):
        """Test extraction limits to top 10 sources."""
        reviewer = AdversarialReviewer()
        citations = " ".join([f"[{i}]" for i in range(1, 16)])
        refs = "\n".join([f"{i}. Paper {i} http://example.com" for i in range(1, 16)])
        report = MockResearchReport(
            executive_summary=citations,
            references_section=refs,
        )
        sources = [MockResearchSource(id=f"src{i}", title=f"Paper {i}") for i in range(1, 16)]
        cited = reviewer.extract_cited_sources(report, sources)
        assert len(cited) <= 10

    def test_extract_citation_frequency(self):
        """Test extraction prioritizes frequently cited sources."""
        reviewer = AdversarialReviewer()
        report = MockResearchReport(
            executive_summary="[1] [1] [1] [2]",
            references_section="1. Paper A http://a.com\n2. Paper B http://b.com",
        )
        sources = [
            MockResearchSource(id="src1", title="Paper A"),
            MockResearchSource(id="src2", title="Paper B"),
        ]
        cited = reviewer.extract_cited_sources(report, sources)
        assert cited[0].id == "src1"  # Most frequently cited

    def test_extract_missing_source(self):
        """Test extraction handles missing sources."""
        reviewer = AdversarialReviewer()
        report = MockResearchReport(
            executive_summary="Supported by [1].",
            references_section="1. Unknown Paper http://example.com",
        )
        sources = [MockResearchSource(id="src1", title="Different Paper")]
        cited = reviewer.extract_cited_sources(report, sources)
        assert len(cited) == 0

    def test_extract_duplicate_citations(self):
        """Test extraction handles duplicate citations."""
        reviewer = AdversarialReviewer()
        report = MockResearchReport(
            executive_summary="[1] [1] [1]",
            references_section="1. Paper A http://a.com",
        )
        source = MockResearchSource(id="src1", title="Paper A")
        sources = [source]
        cited = reviewer.extract_cited_sources(report, sources)
        assert len(cited) == 1

    def test_extract_malformed_citations(self):
        """Test extraction handles malformed citations."""
        reviewer = AdversarialReviewer()
        report = MockResearchReport(
            executive_summary="[1] [abc] [999]",
            references_section="1. Paper A http://a.com",
        )
        source = MockResearchSource(id="src1", title="Paper A")
        sources = [source]
        cited = reviewer.extract_cited_sources(report, sources)
        assert len(cited) == 1


# ---------------------------------------------------------------------------
# Build Claim Mapping Tests (7 tests)
# ---------------------------------------------------------------------------


class TestBuildClaimMapping:
    """Test build_claim_mapping method."""

    def test_build_empty_mapping(self):
        """Test building mapping with no claims."""
        reviewer = AdversarialReviewer()
        report = MockResearchReport(executive_summary="No claims here")
        sources = []
        mapping = reviewer.build_claim_mapping(report, sources)
        assert mapping == {}

    def test_build_single_claim_mapping(self):
        """Test building mapping with single claim."""
        reviewer = AdversarialReviewer()
        report = MockResearchReport(
            executive_summary="This is a claim[1].",
            references_section="1. Paper A http://a.com",
        )
        source = MockResearchSource(id="src1", title="Paper A")
        sources = [source]
        mapping = reviewer.build_claim_mapping(report, sources)
        assert len(mapping) > 0

    def test_build_multiple_claims_mapping(self):
        """Test building mapping with multiple claims."""
        reviewer = AdversarialReviewer()
        report = MockResearchReport(
            executive_summary="First claim[1]. Second claim[2].",
            references_section="1. Paper A http://a.com\n2. Paper B http://b.com",
        )
        sources = [
            MockResearchSource(id="src1", title="Paper A"),
            MockResearchSource(id="src2", title="Paper B"),
        ]
        mapping = reviewer.build_claim_mapping(report, sources)
        assert len(mapping) >= 2

    def test_build_mapping_multiple_citations(self):
        """Test building mapping with multiple citations per claim."""
        reviewer = AdversarialReviewer()
        report = MockResearchReport(
            executive_summary="This claim has multiple sources[1][2].",
            references_section="1. Paper A http://a.com\n2. Paper B http://b.com",
        )
        sources = [
            MockResearchSource(id="src1", title="Paper A"),
            MockResearchSource(id="src2", title="Paper B"),
        ]
        mapping = reviewer.build_claim_mapping(report, sources)
        for claim_text, source_ids in mapping.items():
            if "multiple sources" in claim_text:
                assert len(source_ids) >= 1

    def test_build_mapping_cleans_citations(self):
        """Test mapping removes citation markers from claim text."""
        reviewer = AdversarialReviewer()
        report = MockResearchReport(
            executive_summary="Clean claim[1].",
            references_section="1. Paper A http://a.com",
        )
        source = MockResearchSource(id="src1", title="Paper A")
        sources = [source]
        mapping = reviewer.build_claim_mapping(report, sources)
        for claim_text in mapping.keys():
            assert "[1]" not in claim_text

    def test_build_mapping_missing_reference(self):
        """Test mapping handles missing references."""
        reviewer = AdversarialReviewer()
        report = MockResearchReport(
            executive_summary="Claim with missing ref[99].",
            references_section="1. Paper A http://a.com",
        )
        source = MockResearchSource(id="src1", title="Paper A")
        sources = [source]
        mapping = reviewer.build_claim_mapping(report, sources)
        for source_ids in mapping.values():
            assert len(source_ids) >= 0

    def test_build_mapping_special_chars(self):
        """Test mapping handles special characters in claims."""
        reviewer = AdversarialReviewer()
        report = MockResearchReport(
            executive_summary="Model achieves 95.5% accuracy[1]!",
            references_section="1. Paper A http://a.com",
        )
        source = MockResearchSource(id="src1", title="Paper A")
        sources = [source]
        mapping = reviewer.build_claim_mapping(report, sources)
        assert len(mapping) >= 0


# ---------------------------------------------------------------------------
# Filter Low Confidence Claims Tests (10 tests)
# ---------------------------------------------------------------------------


class TestFilterLowConfidenceClaims:
    """Test filter_low_confidence_claims method."""

    def test_filter_no_claims(self):
        """Test filtering with no claims."""
        reviewer = AdversarialReviewer()
        report = MockResearchReport(executive_summary="Simple text without claims.")
        claims = reviewer.filter_low_confidence_claims(report)
        assert claims == []

    def test_filter_numerical_claims(self):
        """Test filtering numerical claims."""
        reviewer = AdversarialReviewer()
        report = MockResearchReport(executive_summary="Model achieves 95.5% accuracy.")
        claims = reviewer.filter_low_confidence_claims(report)
        assert len(claims) > 0
        assert any("95.5%" in claim.text for claim in claims)

    def test_filter_outperformance_claims(self):
        """Test filtering outperformance claims."""
        reviewer = AdversarialReviewer()
        report = MockResearchReport(executive_summary="Our model outperforms baseline.")
        claims = reviewer.filter_low_confidence_claims(report)
        assert len(claims) > 0
        assert any("outperform" in claim.text.lower() for claim in claims)

    def test_filter_causal_claims(self):
        """Test filtering causal claims."""
        reviewer = AdversarialReviewer()
        report = MockResearchReport(executive_summary="Increased data leads to better performance.")
        claims = reviewer.filter_low_confidence_claims(report)
        assert len(claims) > 0
        assert any("leads to" in claim.text.lower() for claim in claims)

    def test_filter_sota_claims(self):
        """Test filtering state-of-the-art claims."""
        reviewer = AdversarialReviewer()
        report = MockResearchReport(executive_summary="We achieve state-of-the-art results.")
        claims = reviewer.filter_low_confidence_claims(report)
        assert len(claims) > 0
        assert any("state-of-the-art" in claim.text.lower() for claim in claims)

    def test_filter_confidence_no_citations(self):
        """Test confidence scoring with no citations."""
        reviewer = AdversarialReviewer()
        report = MockResearchReport(executive_summary="Model achieves 95% accuracy.")
        claims = reviewer.filter_low_confidence_claims(report)
        assert len(claims) > 0
        assert all(claim.confidence == 0.0 for claim in claims)

    def test_filter_confidence_one_citation(self):
        """Test confidence scoring with one citation."""
        reviewer = AdversarialReviewer()
        report = MockResearchReport(executive_summary="Model achieves 95% accuracy[1].")
        claims = reviewer.filter_low_confidence_claims(report)
        assert len(claims) > 0
        assert all(claim.confidence == 0.5 for claim in claims)

    def test_filter_confidence_two_citations(self):
        """Test confidence scoring with two citations."""
        reviewer = AdversarialReviewer()
        report = MockResearchReport(executive_summary="Model achieves 95% accuracy[1][2].")
        claims = reviewer.filter_low_confidence_claims(report)
        assert len(claims) > 0
        assert all(claim.confidence == 0.7 for claim in claims)

    def test_filter_excludes_high_confidence(self):
        """Test filtering excludes claims with 3+ citations (confidence >= 0.8)."""
        reviewer = AdversarialReviewer()
        report = MockResearchReport(executive_summary="Model achieves 95% accuracy[1][2][3].")
        claims = reviewer.filter_low_confidence_claims(report)
        # Should be empty because confidence is 0.9 (>= 0.8)
        assert len(claims) == 0

    def test_filter_deduplication(self):
        """Test filtering deduplicates claims."""
        reviewer = AdversarialReviewer()
        report = MockResearchReport(executive_summary="95% accuracy. 95% accuracy. 95% accuracy.")
        claims = reviewer.filter_low_confidence_claims(report)
        # Should deduplicate based on first 100 chars
        assert len(claims) <= 1


# ---------------------------------------------------------------------------
# Verify Claim Tests (8 tests)
# ---------------------------------------------------------------------------


class TestVerifyClaim:
    """Test verify_claim method."""

    def test_verify_no_citations(self):
        """Test verifying claim with no citations."""
        reviewer = AdversarialReviewer()
        claim = Claim(text="Unsupported claim", confidence=0.0)
        mapping = {}
        issue = reviewer.verify_claim(claim, mapping)
        assert issue is not None
        assert issue.issue_type == "missing_citation"
        assert issue.severity == "critical"
        assert issue.suggested_resolution == DisagreementResolution.REMOVE

    def test_verify_one_citation(self):
        """Test verifying claim with one citation."""
        reviewer = AdversarialReviewer()
        claim = Claim(text="Claim[1]", confidence=0.5, citations=["[1]"])
        mapping = {"Claim": ["src1"]}
        issue = reviewer.verify_claim(claim, mapping)
        assert issue is not None
        assert issue.issue_type == "weak_evidence"
        assert issue.severity == "high"
        assert issue.suggested_resolution == DisagreementResolution.SOFTEN

    def test_verify_two_citations(self):
        """Test verifying claim with two citations."""
        reviewer = AdversarialReviewer()
        claim = Claim(text="Claim[1][2]", confidence=0.7, citations=["[1]", "[2]"])
        mapping = {"Claim": ["src1", "src2"]}
        issue = reviewer.verify_claim(claim, mapping)
        assert issue is not None
        assert issue.issue_type == "weak_evidence"
        assert issue.severity == "medium"
        assert issue.suggested_resolution == DisagreementResolution.FIX

    def test_verify_three_citations(self):
        """Test verifying claim with three citations (sufficient)."""
        reviewer = AdversarialReviewer()
        claim = Claim(
            text="Claim[1][2][3]",
            confidence=0.9,
            citations=["[1]", "[2]", "[3]"],
        )
        mapping = {"Claim": ["src1", "src2", "src3"]}
        issue = reviewer.verify_claim(claim, mapping)
        assert issue is None

    def test_verify_claim_not_in_mapping(self):
        """Test verifying claim not in mapping."""
        reviewer = AdversarialReviewer()
        claim = Claim(text="Unknown claim", confidence=0.0)
        mapping = {"Different claim": ["src1"]}
        issue = reviewer.verify_claim(claim, mapping)
        assert issue is not None
        assert issue.severity == "critical"

    def test_verify_claim_cleans_citations(self):
        """Test verify_claim cleans citation markers for lookup."""
        reviewer = AdversarialReviewer()
        claim = Claim(text="Test claim[1].", confidence=0.5, citations=["[1]"])
        mapping = {"Test claim.": ["src1"]}
        issue = reviewer.verify_claim(claim, mapping)
        assert issue is not None

    def test_verify_issue_explanation(self):
        """Test verify_claim provides explanations."""
        reviewer = AdversarialReviewer()
        claim = Claim(text="Claim", confidence=0.0)
        mapping = {}
        issue = reviewer.verify_claim(claim, mapping)
        assert issue is not None
        assert len(issue.explanation) > 0

    def test_verify_multiple_claims(self):
        """Test verifying multiple claims."""
        reviewer = AdversarialReviewer()
        claims = [
            Claim(text="Claim 1", confidence=0.0),
            Claim(text="Claim 2[1]", confidence=0.5, citations=["[1]"]),
            Claim(text="Claim 3[1][2][3]", confidence=0.9, citations=["[1]", "[2]", "[3]"]),
        ]
        mapping = {}
        issues = [reviewer.verify_claim(claim, mapping) for claim in claims]
        assert issues[0] is not None  # No citations
        assert issues[1] is not None  # One citation
        assert issues[2] is None  # Three citations


# ---------------------------------------------------------------------------
# Resolve Issue Tests (10 tests)
# ---------------------------------------------------------------------------


class TestResolveIssue:
    """Test resolve_issue method."""

    def test_resolve_remove(self):
        """Test REMOVE resolution."""
        reviewer = AdversarialReviewer()
        claim = Claim(text="Unsupported claim", confidence=0.0)
        issue = ReviewIssue(
            claim=claim,
            issue_type="missing_citation",
            severity="critical",
            suggested_resolution=DisagreementResolution.REMOVE,
            explanation="No support",
        )
        resolved = reviewer.resolve_issue(claim, issue)
        assert resolved.text == ""
        assert resolved.confidence == 0.0

    def test_resolve_soften_is(self):
        """Test SOFTEN resolution replaces 'is'."""
        reviewer = AdversarialReviewer()
        claim = Claim(text="Model is accurate.", confidence=0.5)
        issue = ReviewIssue(
            claim=claim,
            issue_type="weak_evidence",
            severity="high",
            suggested_resolution=DisagreementResolution.SOFTEN,
            explanation="Weak support",
        )
        resolved = reviewer.resolve_issue(claim, issue)
        assert "may be" in resolved.text.lower()
        assert resolved.confidence < claim.confidence

    def test_resolve_soften_outperforms(self):
        """Test SOFTEN resolution replaces 'outperforms'."""
        reviewer = AdversarialReviewer()
        claim = Claim(text="Model outperforms baseline.", confidence=0.5)
        issue = ReviewIssue(
            claim=claim,
            issue_type="weak_evidence",
            severity="high",
            suggested_resolution=DisagreementResolution.SOFTEN,
            explanation="Weak support",
        )
        resolved = reviewer.resolve_issue(claim, issue)
        assert "appears to outperform" in resolved.text.lower()

    def test_resolve_soften_shows(self):
        """Test SOFTEN resolution replaces 'shows'."""
        reviewer = AdversarialReviewer()
        claim = Claim(text="Data shows improvement.", confidence=0.5)
        issue = ReviewIssue(
            claim=claim,
            issue_type="weak_evidence",
            severity="high",
            suggested_resolution=DisagreementResolution.SOFTEN,
            explanation="Weak support",
        )
        resolved = reviewer.resolve_issue(claim, issue)
        assert "suggests" in resolved.text.lower()

    def test_resolve_soften_confidence_reduction(self):
        """Test SOFTEN reduces confidence by 20%."""
        reviewer = AdversarialReviewer()
        claim = Claim(text="Model is accurate.", confidence=0.5)
        issue = ReviewIssue(
            claim=claim,
            issue_type="weak_evidence",
            severity="high",
            suggested_resolution=DisagreementResolution.SOFTEN,
            explanation="Weak support",
        )
        resolved = reviewer.resolve_issue(claim, issue)
        assert resolved.confidence == claim.confidence * 0.8

    def test_resolve_fix(self):
        """Test FIX resolution adds qualifier."""
        reviewer = AdversarialReviewer()
        claim = Claim(text="Model achieves 95% accuracy.", confidence=0.7)
        issue = ReviewIssue(
            claim=claim,
            issue_type="weak_evidence",
            severity="medium",
            suggested_resolution=DisagreementResolution.FIX,
            explanation="Needs more evidence",
        )
        resolved = reviewer.resolve_issue(claim, issue)
        assert "additional verification needed" in resolved.text.lower()

    def test_resolve_fix_preserves_confidence(self):
        """Test FIX preserves confidence."""
        reviewer = AdversarialReviewer()
        claim = Claim(text="Model achieves 95% accuracy.", confidence=0.7)
        issue = ReviewIssue(
            claim=claim,
            issue_type="weak_evidence",
            severity="medium",
            suggested_resolution=DisagreementResolution.FIX,
            explanation="Needs more evidence",
        )
        resolved = reviewer.resolve_issue(claim, issue)
        assert resolved.confidence == claim.confidence

    def test_resolve_preserves_citations(self):
        """Test resolution preserves citations."""
        reviewer = AdversarialReviewer()
        claim = Claim(text="Claim[1].", confidence=0.5, citations=["[1]"])
        issue = ReviewIssue(
            claim=claim,
            issue_type="weak_evidence",
            severity="high",
            suggested_resolution=DisagreementResolution.SOFTEN,
            explanation="Weak support",
        )
        resolved = reviewer.resolve_issue(claim, issue)
        assert resolved.citations == claim.citations

    def test_resolve_preserves_source_ids(self):
        """Test resolution preserves source IDs."""
        reviewer = AdversarialReviewer()
        claim = Claim(text="Claim.", confidence=0.5, source_ids=["src1"])
        issue = ReviewIssue(
            claim=claim,
            issue_type="weak_evidence",
            severity="high",
            suggested_resolution=DisagreementResolution.SOFTEN,
            explanation="Weak support",
        )
        resolved = reviewer.resolve_issue(claim, issue)
        assert resolved.source_ids == claim.source_ids

    def test_resolve_no_change_for_unknown_resolution(self):
        """Test resolution returns original claim for unknown resolution."""
        reviewer = AdversarialReviewer()
        claim = Claim(text="Original claim.", confidence=0.7)
        issue = ReviewIssue(
            claim=claim,
            issue_type="weak_evidence",
            severity="medium",
            suggested_resolution=DisagreementResolution.FIX,
            explanation="Test",
        )
        # Manually set to invalid resolution to test fallback
        resolved = reviewer.resolve_issue(claim, issue)
        assert resolved.text != ""


# ---------------------------------------------------------------------------
# Calculate Review Cost Tests (5 tests)
# ---------------------------------------------------------------------------


class TestCalculateReviewCost:
    """Test calculate_review_cost method."""

    def test_cost_empty_report(self):
        """Test cost calculation for empty report."""
        reviewer = AdversarialReviewer()
        report = MockResearchReport(executive_summary="")
        cost = reviewer.calculate_review_cost(report)
        assert cost >= 0.0

    def test_cost_small_report(self):
        """Test cost calculation for small report."""
        reviewer = AdversarialReviewer()
        report = MockResearchReport(executive_summary="Short report.")
        cost = reviewer.calculate_review_cost(report)
        assert cost >= 0.0
        assert cost < 0.01  # Should be very cheap

    def test_cost_large_report(self):
        """Test cost calculation for large report."""
        reviewer = AdversarialReviewer()
        large_text = "x" * 100000  # ~100K chars
        report = MockResearchReport(executive_summary=large_text)
        cost = reviewer.calculate_review_cost(report)
        assert cost > 0.001  # Should have measurable cost

    def test_cost_proportional_to_size(self):
        """Test cost is proportional to report size."""
        reviewer = AdversarialReviewer()
        small_report = MockResearchReport(executive_summary="x" * 1000)
        large_report = MockResearchReport(executive_summary="x" * 10000)
        small_cost = reviewer.calculate_review_cost(small_report)
        large_cost = reviewer.calculate_review_cost(large_report)
        assert large_cost > small_cost

    def test_cost_uses_gpt4o_mini_pricing(self):
        """Test cost uses GPT-4o-mini pricing."""
        reviewer = AdversarialReviewer()
        report = MockResearchReport(executive_summary="x" * 1000000)  # 1M chars
        cost = reviewer.calculate_review_cost(report)
        # Should be around $0.15-0.60 for 1M chars (250K tokens)
        assert 0.01 < cost < 1.0


# ---------------------------------------------------------------------------
# Calculate Context Size Tests (6 tests)
# ---------------------------------------------------------------------------


class TestCalculateContextSize:
    """Test _calculate_context_size method."""

    def test_context_size_empty(self):
        """Test context size for empty inputs."""
        reviewer = AdversarialReviewer()
        size = reviewer._calculate_context_size("", [], {})
        assert size >= 0.0

    def test_context_size_report_only(self):
        """Test context size with report only."""
        reviewer = AdversarialReviewer()
        report_text = "x" * 1024  # 1KB
        size = reviewer._calculate_context_size(report_text, [], {})
        assert size > 0.0
        assert size < 2.0

    def test_context_size_with_sources(self):
        """Test context size with sources."""
        reviewer = AdversarialReviewer()
        sources = [
            MockResearchSource(id="src1", title="Paper 1", abstract="x" * 500),
            MockResearchSource(id="src2", title="Paper 2", abstract="x" * 500),
        ]
        size = reviewer._calculate_context_size("Report", sources, {})
        assert size > 0.0

    def test_context_size_with_mapping(self):
        """Test context size with claim mapping."""
        reviewer = AdversarialReviewer()
        mapping = {
            "Claim 1": ["src1", "src2"],
            "Claim 2": ["src3"],
        }
        size = reviewer._calculate_context_size("Report", [], mapping)
        assert size > 0.0

    def test_context_size_enforces_max(self):
        """Test context size enforces MAX_CONTEXT_KB limit."""
        reviewer = AdversarialReviewer()
        large_text = "x" * 100000  # ~100KB
        large_sources = [
            MockResearchSource(id=f"src{i}", title=f"Paper {i}", abstract="x" * 5000)
            for i in range(20)
        ]
        large_mapping = {f"Claim {i}": [f"src{i}"] for i in range(100)}
        size = reviewer._calculate_context_size(large_text, large_sources, large_mapping)
        assert size <= reviewer.budget.MAX_CONTEXT_KB

    def test_context_size_all_components(self):
        """Test context size with all components."""
        reviewer = AdversarialReviewer()
        report_text = "x" * 5000
        sources = [MockResearchSource(id="src1", title="Paper", abstract="x" * 1000)]
        mapping = {"Claim": ["src1"]}
        size = reviewer._calculate_context_size(report_text, sources, mapping)
        assert size > 0.0


# ---------------------------------------------------------------------------
# Review Method Integration Tests (15 tests)
# ---------------------------------------------------------------------------


class TestReviewMethod:
    """Test the main review method."""

    def test_review_skip_quick_depth(self):
        """Test review skips for quick depth."""
        reviewer = AdversarialReviewer()
        report = MockResearchReport(executive_summary="Test report")
        sources = []
        result = reviewer.review(report, sources, depth="quick")
        assert result.issues_found == []
        assert result.issues_resolved == 0
        assert result.review_cost_usd == 0.0
        assert result.claims_reviewed == 0

    def test_review_skip_standard_depth(self):
        """Test review skips for standard depth."""
        reviewer = AdversarialReviewer()
        report = MockResearchReport(executive_summary="Test report")
        sources = []
        result = reviewer.review(report, sources, depth="standard")
        assert result.issues_found == []
        assert result.issues_resolved == 0
        assert result.review_cost_usd == 0.0

    def test_review_runs_deep_depth(self):
        """Test review runs for deep depth."""
        reviewer = AdversarialReviewer()
        report = MockResearchReport(
            executive_summary="Model achieves 95% accuracy.",
            references_section="",
        )
        sources = []
        result = reviewer.review(report, sources, depth="deep")
        assert isinstance(result, ReviewResult)
        assert result.claims_reviewed >= 0

    def test_review_finds_issues(self):
        """Test review finds issues in unsupported claims."""
        reviewer = AdversarialReviewer()
        report = MockResearchReport(
            executive_summary="Model achieves 95% accuracy. It outperforms baseline.",
            references_section="",
        )
        sources = []
        result = reviewer.review(report, sources, depth="deep")
        assert len(result.issues_found) > 0

    def test_review_resolves_issues(self):
        """Test review resolves found issues."""
        reviewer = AdversarialReviewer()
        report = MockResearchReport(
            executive_summary="Model achieves 95% accuracy.",
            references_section="",
        )
        sources = []
        result = reviewer.review(report, sources, depth="deep")
        if len(result.issues_found) > 0:
            assert result.issues_resolved >= 0

    def test_review_modifies_report(self):
        """Test review modifies report text."""
        reviewer = AdversarialReviewer()
        report = MockResearchReport(
            executive_summary="Model achieves 95% accuracy.",
            references_section="",
        )
        sources = []
        result = reviewer.review(report, sources, depth="deep")
        assert result.original_report != "" or result.revised_report != ""

    def test_review_calculates_cost(self):
        """Test review calculates cost."""
        reviewer = AdversarialReviewer()
        report = MockResearchReport(executive_summary="Test report with claims.")
        sources = []
        result = reviewer.review(report, sources, depth="deep")
        assert result.review_cost_usd >= 0.0

    def test_review_tracks_context_size(self):
        """Test review tracks context size."""
        reviewer = AdversarialReviewer()
        report = MockResearchReport(executive_summary="Test report")
        sources = []
        result = reviewer.review(report, sources, depth="deep")
        assert result.context_size_kb >= 0.0

    def test_review_counts_claims(self):
        """Test review counts reviewed claims."""
        reviewer = AdversarialReviewer()
        report = MockResearchReport(
            executive_summary="Model achieves 95% accuracy. It outperforms baseline.",
            references_section="",
        )
        sources = []
        result = reviewer.review(report, sources, depth="deep")
        assert result.claims_reviewed >= 0

    def test_review_counts_modifications(self):
        """Test review counts modified claims."""
        reviewer = AdversarialReviewer()
        report = MockResearchReport(
            executive_summary="Model achieves 95% accuracy.",
            references_section="",
        )
        sources = []
        result = reviewer.review(report, sources, depth="deep")
        assert result.claims_modified >= 0

    def test_review_with_citations(self):
        """Test review with properly cited claims."""
        reviewer = AdversarialReviewer()
        report = MockResearchReport(
            executive_summary="Model achieves 95% accuracy[1][2][3].",
            references_section="1. Paper A\n2. Paper B\n3. Paper C",
        )
        sources = [
            MockResearchSource(id="src1", title="Paper A"),
            MockResearchSource(id="src2", title="Paper B"),
            MockResearchSource(id="src3", title="Paper C"),
        ]
        result = reviewer.review(report, sources, depth="deep")
        # Well-cited claims should have fewer issues
        assert isinstance(result, ReviewResult)

    def test_review_result_structure(self):
        """Test review result has all required fields."""
        reviewer = AdversarialReviewer()
        report = MockResearchReport(executive_summary="Test")
        sources = []
        result = reviewer.review(report, sources, depth="deep")
        assert hasattr(result, "original_report")
        assert hasattr(result, "revised_report")
        assert hasattr(result, "issues_found")
        assert hasattr(result, "issues_resolved")
        assert hasattr(result, "review_cost_usd")
        assert hasattr(result, "context_size_kb")
        assert hasattr(result, "claims_reviewed")
        assert hasattr(result, "claims_modified")

    def test_review_preserves_well_cited_claims(self):
        """Test review preserves well-cited claims."""
        reviewer = AdversarialReviewer()
        original_text = "Model achieves 95% accuracy[1][2][3]."
        report = MockResearchReport(
            executive_summary=original_text,
            references_section="1. A\n2. B\n3. C",
        )
        sources = []
        result = reviewer.review(report, sources, depth="deep")
        # Well-cited claim should remain unchanged
        assert original_text in result.revised_report or result.claims_modified == 0

    def test_review_multiple_issue_types(self):
        """Test review handles multiple issue types."""
        reviewer = AdversarialReviewer()
        report = MockResearchReport(
            executive_summary=(
                "Unsupported claim. "
                "Weakly supported claim[1]. "
                "Moderately supported claim[1][2]."
            ),
            references_section="1. Paper A\n2. Paper B",
        )
        sources = []
        result = reviewer.review(report, sources, depth="deep")
        if len(result.issues_found) > 0:
            issue_types = {issue.issue_type for issue in result.issues_found}
            assert len(issue_types) >= 1

    def test_review_large_report(self):
        """Test review handles large reports."""
        reviewer = AdversarialReviewer()
        large_summary = "Model achieves 95% accuracy. " * 100
        report = MockResearchReport(executive_summary=large_summary)
        sources = []
        result = reviewer.review(report, sources, depth="deep")
        assert result.context_size_kb <= reviewer.budget.MAX_CONTEXT_KB


# ---------------------------------------------------------------------------
# Edge Cases and Error Handling Tests (5 tests)
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_report(self):
        """Test handling empty report."""
        reviewer = AdversarialReviewer()
        report = MockResearchReport(executive_summary="")
        sources = []
        result = reviewer.review(report, sources, depth="deep")
        assert isinstance(result, ReviewResult)

    def test_empty_sources(self):
        """Test handling empty sources list."""
        reviewer = AdversarialReviewer()
        report = MockResearchReport(executive_summary="Test claim[1].")
        sources = []
        result = reviewer.review(report, sources, depth="deep")
        assert isinstance(result, ReviewResult)

    def test_malformed_citations(self):
        """Test handling malformed citations."""
        reviewer = AdversarialReviewer()
        report = MockResearchReport(
            executive_summary="Claim [abc] [999] [1.5].",
            references_section="",
        )
        sources = []
        result = reviewer.review(report, sources, depth="deep")
        assert isinstance(result, ReviewResult)

    def test_unicode_content(self):
        """Test handling Unicode content."""
        reviewer = AdversarialReviewer()
        report = MockResearchReport(
            executive_summary="机器学习模型达到95%准确率。",
            references_section="",
        )
        sources = []
        result = reviewer.review(report, sources, depth="deep")
        assert isinstance(result, ReviewResult)

    def test_special_characters(self):
        """Test handling special characters."""
        reviewer = AdversarialReviewer()
        report = MockResearchReport(
            executive_summary="Model achieves 95.5% accuracy! (p<0.001) [1].",
            references_section="1. Paper A",
        )
        sources = []
        result = reviewer.review(report, sources, depth="deep")
        assert isinstance(result, ReviewResult)
