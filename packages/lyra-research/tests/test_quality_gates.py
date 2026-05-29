"""Tests for quality gates and verification system."""

from datetime import datetime, timezone

import pytest
from lyra_research.agents.analysis import Analysis
from lyra_research.discovery import ResearchSource, SourceType
from lyra_research.quality import (
    AnalysisGate,
    CurationGate,
    DiscoveryGate,
    GateEnforcer,
    QualityCriterion,
    ReviewGate,
    SynthesisGate,
    VerificationResult,
    Verifier,
)
from lyra_research.reporter import ResearchReport
from lyra_research.roles.curator_role import KnowledgeEntry
from lyra_research.roles.review_role import ReviewIssue, ReviewResult

# ============================================================================
# Quality Criterion Tests
# ============================================================================


def test_quality_criterion_creation():
    """Test creating a quality criterion."""
    criterion = QualityCriterion(
        name="test_criterion",
        check_fn=lambda x: float(len(x)),
        severity="high",
        threshold=5.0,
    )
    assert criterion.name == "test_criterion"
    assert criterion.severity == "high"
    assert criterion.threshold == 5.0


def test_quality_criterion_invalid_severity():
    """Test that invalid severity raises error."""
    with pytest.raises(ValueError, match="Invalid severity"):
        QualityCriterion(
            name="test",
            check_fn=lambda x: 1.0,
            severity="invalid",
            threshold=1.0,
        )


def test_quality_criterion_evaluate_pass():
    """Test criterion evaluation that passes."""
    criterion = QualityCriterion(
        name="min_length",
        check_fn=lambda x: float(len(x)),
        severity="high",
        threshold=5.0,
    )
    result = criterion.evaluate("hello world")
    assert result.passed is True
    assert result.score == 11.0
    assert result.name == "min_length"


def test_quality_criterion_evaluate_fail():
    """Test criterion evaluation that fails."""
    criterion = QualityCriterion(
        name="min_length",
        check_fn=lambda x: float(len(x)),
        severity="critical",
        threshold=10.0,
    )
    result = criterion.evaluate("short")
    assert result.passed is False
    assert result.score == 5.0
    assert "failed" in result.message.lower()


def test_quality_criterion_evaluate_error():
    """Test criterion evaluation with error."""

    def failing_check(x):
        raise ValueError("Check failed")

    criterion = QualityCriterion(
        name="test",
        check_fn=failing_check,
        severity="high",
        threshold=1.0,
    )
    result = criterion.evaluate("data")
    assert result.passed is False
    assert result.severity == "critical"  # Errors are critical
    assert "error" in result.message.lower()


# ============================================================================
# Discovery Gate Tests
# ============================================================================


def test_discovery_gate_pass():
    """Test discovery gate with passing data."""
    gate = DiscoveryGate()

    # Create 15 sources with 4 different types
    source_types = [
        SourceType.PAPER,
        SourceType.REPOSITORY,
        SourceType.BLOG,
        SourceType.DOCUMENTATION,
    ]
    sources = [
        ResearchSource(
            id=f"src_{i}",
            title=f"Source {i}",
            url=f"https://example.com/{i}",
            source_type=source_types[i % 4],
            metadata={"quality_score": 0.7},
        )
        for i in range(15)
    ]

    result = gate.check(sources)
    assert result.passed is True
    assert result.gate_name == "DiscoveryGate"


def test_discovery_gate_fail_min_sources():
    """Test discovery gate failing on minimum sources."""
    gate = DiscoveryGate()

    # Only 5 sources (need 10)
    sources = [
        ResearchSource(
            id=f"src_{i}",
            title=f"Source {i}",
            url=f"https://example.com/{i}",
            source_type=SourceType.PAPER,
            metadata={"quality_score": 0.7},
        )
        for i in range(5)
    ]

    result = gate.check(sources)
    assert result.passed is False
    assert result.has_critical_failures() is True


def test_discovery_gate_fail_diversity():
    """Test discovery gate failing on source diversity."""
    gate = DiscoveryGate()

    # 15 sources but only 2 types (need 3)
    sources = [
        ResearchSource(
            id=f"src_{i}",
            title=f"Source {i}",
            url=f"https://example.com/{i}",
            source_type=SourceType.PAPER if i % 2 == 0 else SourceType.REPOSITORY,
            metadata={"quality_score": 0.7},
        )
        for i in range(15)
    ]

    result = gate.check(sources)
    assert result.passed is False
    assert result.has_high_failures() is True


def test_discovery_gate_fail_quality():
    """Test discovery gate failing on average quality."""
    gate = DiscoveryGate()

    # 15 sources with 4 types but low quality
    source_types = [
        SourceType.PAPER,
        SourceType.REPOSITORY,
        SourceType.BLOG,
        SourceType.DOCUMENTATION,
    ]
    sources = [
        ResearchSource(
            id=f"src_{i}",
            title=f"Source {i}",
            url=f"https://example.com/{i}",
            source_type=source_types[i % 4],
            metadata={"quality_score": 0.3},  # Below 0.6 threshold
        )
        for i in range(15)
    ]

    result = gate.check(sources)
    assert result.passed is False


# ============================================================================
# Analysis Gate Tests
# ============================================================================


def test_analysis_gate_pass():
    """Test analysis gate with passing data."""
    gate = AnalysisGate()

    # Create 10 analyses with good quality
    analyses = [
        Analysis(
            source_id=f"src_{i}",
            analysis_type="paper",
            quality_score=0.7,
            findings={"key": "value"},
        )
        for i in range(10)
    ]

    result = gate.check(analyses)
    assert result.passed is True


def test_analysis_gate_fail_min_analyses():
    """Test analysis gate failing on minimum analyses."""
    gate = AnalysisGate()

    # Only 3 analyses (need 5)
    analyses = [
        Analysis(
            source_id=f"src_{i}",
            analysis_type="paper",
            quality_score=0.7,
            findings={},
        )
        for i in range(3)
    ]

    result = gate.check(analyses)
    assert result.passed is False
    assert result.has_critical_failures() is True


def test_analysis_gate_fail_quality():
    """Test analysis gate failing on average quality."""
    gate = AnalysisGate()

    # 10 analyses but low quality
    analyses = [
        Analysis(
            source_id=f"src_{i}",
            analysis_type="paper",
            quality_score=0.3,  # Below 0.5 threshold
            findings={},
        )
        for i in range(10)
    ]

    result = gate.check(analyses)
    assert result.passed is False


def test_analysis_gate_fail_coverage():
    """Test analysis gate failing on quality coverage."""
    gate = AnalysisGate()

    # 10 analyses but only 5 have quality scores
    analyses = [
        Analysis(
            source_id=f"src_{i}",
            analysis_type="paper",
            quality_score=0.7 if i < 5 else 0.0,  # Only 50% coverage (need 80%)
            findings={},
        )
        for i in range(10)
    ]

    result = gate.check(analyses)
    assert result.passed is False


# ============================================================================
# Synthesis Gate Tests
# ============================================================================


def test_synthesis_gate_pass():
    """Test synthesis gate with passing report."""
    gate = SynthesisGate()

    report = ResearchReport(
        topic="Test Topic",
        executive_summary="A" * 150,  # > 100 chars
        taxonomy_section="Taxonomy",
        best_papers_section="B" * 250,  # > 200 chars
        gaps_section="Gaps",
        contested_claims_section="",
        references_section="Refs",
        sources_used=5,
        quality_score=0.7,
    )

    result = gate.check(report)
    assert result.passed is True


def test_synthesis_gate_fail_summary():
    """Test synthesis gate failing on executive summary."""
    gate = SynthesisGate()

    report = ResearchReport(
        topic="Test",
        executive_summary="Short",  # < 100 chars
        taxonomy_section="Tax",
        best_papers_section="B" * 250,
        gaps_section="",
        contested_claims_section="",
        references_section="",
        sources_used=5,
        quality_score=0.7,
    )

    result = gate.check(report)
    assert result.passed is False
    assert result.has_critical_failures() is True


def test_synthesis_gate_fail_findings():
    """Test synthesis gate failing on findings section."""
    gate = SynthesisGate()

    report = ResearchReport(
        topic="Test",
        executive_summary="A" * 150,
        taxonomy_section="Tax",
        best_papers_section="Short",  # < 200 chars
        gaps_section="",
        contested_claims_section="",
        references_section="",
        sources_used=5,
        quality_score=0.7,
    )

    result = gate.check(report)
    assert result.passed is False


def test_synthesis_gate_fail_sources():
    """Test synthesis gate failing on sources used."""
    gate = SynthesisGate()

    report = ResearchReport(
        topic="Test",
        executive_summary="A" * 150,
        taxonomy_section="Tax",
        best_papers_section="B" * 250,
        gaps_section="",
        contested_claims_section="",
        references_section="",
        sources_used=2,  # < 3
        quality_score=0.7,
    )

    result = gate.check(report)
    assert result.passed is False


# ============================================================================
# Review Gate Tests
# ============================================================================


def test_review_gate_pass():
    """Test review gate with passing review."""
    gate = ReviewGate()

    review = ReviewResult(
        role_name="Review",
        status="success",
        data={},
        approved=True,
        issues=[],
        suggestions=[],
        overall_quality_score=0.85,
    )

    result = gate.check(review)
    assert result.passed is True


def test_review_gate_fail_critical():
    """Test review gate failing on critical issues."""
    gate = ReviewGate()

    review = ReviewResult(
        role_name="Review",
        status="success",
        data={},
        approved=False,
        issues=[
            ReviewIssue(
                severity="critical",
                category="accuracy",
                description="Critical issue",
                suggestion="Fix it",
            )
        ],
        suggestions=[],
        overall_quality_score=0.7,
    )

    result = gate.check(review)
    assert result.passed is False
    assert result.has_critical_failures() is True


def test_review_gate_fail_quality():
    """Test review gate failing on quality score."""
    gate = ReviewGate()

    review = ReviewResult(
        role_name="Review",
        status="success",
        data={},
        approved=False,
        issues=[],
        suggestions=[],
        overall_quality_score=0.5,  # < 0.7
    )

    result = gate.check(review)
    assert result.passed is False


def test_review_gate_fail_high_issues():
    """Test review gate failing on too many high issues."""
    gate = ReviewGate()

    review = ReviewResult(
        role_name="Review",
        status="success",
        data={},
        approved=False,
        issues=[
            ReviewIssue(
                severity="high",
                category="completeness",
                description=f"Issue {i}",
                suggestion="Fix",
            )
            for i in range(5)  # > 2 high issues
        ],
        suggestions=[],
        overall_quality_score=0.7,
    )

    result = gate.check(review)
    assert result.passed is False


# ============================================================================
# Curation Gate Tests
# ============================================================================


def test_curation_gate_pass():
    """Test curation gate with accepted entry."""
    gate = CurationGate()

    review = ReviewResult(
        role_name="Review",
        status="success",
        data={},
        approved=True,
        issues=[],
        suggestions=[],
        overall_quality_score=0.85,
    )

    entry = KnowledgeEntry(
        entry_id="test_entry_123",
        report=ResearchReport(
            topic="Test",
            executive_summary="Summary",
            taxonomy_section="",
            best_papers_section="",
            gaps_section="",
            contested_claims_section="",
            references_section="",
            sources_used=5,
            quality_score=0.7,
        ),
        review=review,
        version=1,
        accepted=True,
        created_at=datetime.now(timezone.utc),
    )

    result = gate.check(entry)
    assert result.passed is True


def test_curation_gate_fail_not_accepted():
    """Test curation gate failing on rejected entry."""
    gate = CurationGate()

    result = gate.check(None)
    assert result.passed is False
    assert result.has_critical_failures() is True


def test_curation_gate_fail_quality():
    """Test curation gate failing on low quality."""
    gate = CurationGate()

    review = ReviewResult(
        role_name="Review",
        status="success",
        data={},
        approved=False,
        issues=[],
        suggestions=[],
        overall_quality_score=0.5,  # < 0.7
    )

    entry = KnowledgeEntry(
        entry_id="test_entry",
        report=ResearchReport(
            topic="Test",
            executive_summary="Summary",
            taxonomy_section="",
            best_papers_section="",
            gaps_section="",
            contested_claims_section="",
            references_section="",
            sources_used=5,
            quality_score=0.7,
        ),
        review=review,
        version=1,
        accepted=True,
        created_at=datetime.now(timezone.utc),
    )

    result = gate.check(entry)
    assert result.passed is False


# ============================================================================
# Gate Enforcer Tests
# ============================================================================


def test_gate_enforcer_creation():
    """Test creating gate enforcer."""
    enforcer = GateEnforcer()
    assert len(enforcer.gates) == 5
    assert "discovery" in enforcer.gates
    assert "analysis" in enforcer.gates
    assert "synthesis" in enforcer.gates
    assert "review" in enforcer.gates
    assert "curation" in enforcer.gates


def test_gate_enforcer_pass():
    """Test gate enforcer with passing data."""
    enforcer = GateEnforcer()

    source_types = [
        SourceType.PAPER,
        SourceType.REPOSITORY,
        SourceType.BLOG,
        SourceType.DOCUMENTATION,
    ]
    sources = [
        ResearchSource(
            id=f"src_{i}",
            title=f"Source {i}",
            url=f"https://example.com/{i}",
            source_type=source_types[i % 4],
            metadata={"quality_score": 0.7},
        )
        for i in range(15)
    ]

    result = enforcer.enforce("discovery", sources)
    assert result.passed is True
    assert result.action == "pass"


def test_gate_enforcer_reject():
    """Test gate enforcer rejecting on critical failure."""
    enforcer = GateEnforcer()

    # Only 3 sources (critical failure)
    sources = [
        ResearchSource(
            id=f"src_{i}",
            title=f"Source {i}",
            url=f"https://example.com/{i}",
            source_type=SourceType.PAPER,
            metadata={"quality_score": 0.7},
        )
        for i in range(3)
    ]

    result = enforcer.enforce("discovery", sources)
    assert result.passed is False
    assert result.action == "reject"


def test_gate_enforcer_retry():
    """Test gate enforcer retry on non-critical failure."""
    enforcer = GateEnforcer()

    # 15 sources but only 2 types (high severity, not critical)
    sources = [
        ResearchSource(
            id=f"src_{i}",
            title=f"Source {i}",
            url=f"https://example.com/{i}",
            source_type=SourceType.PAPER if i % 2 == 0 else SourceType.REPOSITORY,
            metadata={"quality_score": 0.7},
        )
        for i in range(15)
    ]

    result = enforcer.enforce("discovery", sources, max_retries=2)
    assert result.passed is False
    assert result.action == "retry"


def test_gate_enforcer_escalate():
    """Test gate enforcer escalating after max retries."""
    enforcer = GateEnforcer()

    # Data that fails non-critically
    sources = [
        ResearchSource(
            id=f"src_{i}",
            title=f"Source {i}",
            url=f"https://example.com/{i}",
            source_type=SourceType.PAPER if i % 2 == 0 else SourceType.REPOSITORY,
            metadata={"quality_score": 0.7},
        )
        for i in range(15)
    ]

    # First attempt: retry
    result1 = enforcer.enforce("discovery", sources, max_retries=1)
    assert result1.action == "retry"

    # Second attempt: escalate (max retries reached)
    result2 = enforcer.enforce("discovery", sources, max_retries=1)
    assert result2.action == "escalate"


def test_gate_enforcer_invalid_gate():
    """Test gate enforcer with invalid gate name."""
    enforcer = GateEnforcer()

    with pytest.raises(ValueError, match="Invalid gate name"):
        enforcer.enforce("invalid_gate", {})


def test_gate_enforcer_stats():
    """Test gate enforcer statistics."""
    enforcer = GateEnforcer()

    # Run some enforcements
    source_types = [
        SourceType.PAPER,
        SourceType.REPOSITORY,
        SourceType.BLOG,
        SourceType.DOCUMENTATION,
    ]
    sources = [
        ResearchSource(
            id=f"src_{i}",
            title=f"Source {i}",
            url=f"https://example.com/{i}",
            source_type=source_types[i % 4],
            metadata={"quality_score": 0.7},
        )
        for i in range(15)
    ]

    enforcer.enforce("discovery", sources)
    enforcer.enforce("discovery", sources)

    stats = enforcer.get_gate_stats("discovery")
    assert stats["total_attempts"] == 2
    assert stats["pass_rate"] == 1.0


# ============================================================================
# Verifier Tests
# ============================================================================


def test_verifier_completeness_pass():
    """Test verifier completeness check passing."""
    verifier = Verifier()

    report = ResearchReport(
        topic="Test Topic",
        executive_summary="A" * 150,
        taxonomy_section="Taxonomy",
        best_papers_section="Papers",
        gaps_section="Gaps",
        contested_claims_section="",
        references_section="References",
        sources_used=10,
        quality_score=0.7,
    )

    result = verifier.verify_completeness(report)
    assert result.passed is True
    assert result.check_name == "completeness"


def test_verifier_completeness_fail():
    """Test verifier completeness check failing."""
    verifier = Verifier()

    report = ResearchReport(
        topic="Test",
        executive_summary="Short",  # Too brief
        taxonomy_section="",  # Missing
        best_papers_section="",  # Missing
        gaps_section="",
        contested_claims_section="",
        references_section="",  # Missing
        sources_used=2,  # Too few
        quality_score=0.7,
    )

    result = verifier.verify_completeness(report)
    assert result.passed is False
    assert len(result.issues) > 0


def test_verifier_accuracy_pass():
    """Test verifier accuracy check passing."""
    verifier = Verifier()

    report = ResearchReport(
        topic="Test",
        executive_summary="Summary",
        taxonomy_section="",
        best_papers_section="",
        gaps_section="",
        contested_claims_section="",
        references_section="References",
        sources_used=5,
        quality_score=0.7,
    )

    source_types = [SourceType.PAPER, SourceType.REPOSITORY, SourceType.BLOG]
    sources = [
        ResearchSource(
            id=f"src_{i}",
            title=f"Source {i}",
            url=f"https://example.com/{i}",
            source_type=source_types[i % 3],
            metadata={"quality_score": 0.7},
        )
        for i in range(5)
    ]

    result = verifier.verify_accuracy(report, sources)
    assert result.passed is True


def test_verifier_accuracy_fail():
    """Test verifier accuracy check failing."""
    verifier = Verifier()

    report = ResearchReport(
        topic="Test",
        executive_summary="Summary",
        taxonomy_section="",
        best_papers_section="",
        gaps_section="",
        contested_claims_section="",
        references_section="",  # No references
        sources_used=5,
        quality_score=0.7,
    )

    sources = [
        ResearchSource(
            id=f"src_{i}",
            title=f"Source {i}",
            url=f"https://example.com/{i}",
            source_type=SourceType.PAPER,  # Only one type
            metadata={"quality_score": 0.7},  # Low quality
        )
        for i in range(5)
    ]

    result = verifier.verify_accuracy(report, sources)
    assert result.passed is False
    assert len(result.issues) > 0


def test_verifier_consistency_pass():
    """Test verifier consistency check passing."""
    verifier = Verifier()

    report = ResearchReport(
        topic="Test Topic",
        executive_summary="Summary",
        taxonomy_section="",
        best_papers_section="Papers",
        gaps_section="Gaps analysis",
        contested_claims_section="Minor claims",
        references_section="",
        sources_used=5,
        quality_score=0.7,
    )

    result = verifier.verify_consistency(report)
    assert result.passed is True


def test_verifier_consistency_fail():
    """Test verifier consistency check failing."""
    verifier = Verifier()

    report = ResearchReport(
        topic="",  # Missing topic
        executive_summary="Summary",
        taxonomy_section="",
        best_papers_section="Papers",
        gaps_section="",  # Missing gaps
        contested_claims_section="C" * 1500,  # Too many contested claims
        references_section="",
        sources_used=5,
        quality_score=0.7,
    )

    result = verifier.verify_consistency(report)
    assert result.passed is False
    assert len(result.issues) > 0


def test_verifier_all():
    """Test running all verifications."""
    verifier = Verifier()

    report = ResearchReport(
        topic="Test Topic",
        executive_summary="A" * 150,
        taxonomy_section="Taxonomy",
        best_papers_section="Papers",
        gaps_section="Gaps",
        contested_claims_section="",
        references_section="References",
        sources_used=5,
        quality_score=0.7,
    )

    source_types = [SourceType.PAPER, SourceType.REPOSITORY, SourceType.BLOG]
    sources = [
        ResearchSource(
            id=f"src_{i}",
            title=f"Source {i}",
            url=f"https://example.com/{i}",
            source_type=source_types[i % 3],
            metadata={"quality_score": 0.7},
        )
        for i in range(5)
    ]

    results = verifier.verify_all(report, sources)
    assert len(results) == 3
    assert all(isinstance(r, VerificationResult) for r in results)


def test_verifier_overall_score():
    """Test calculating overall verification score."""
    verifier = Verifier()

    results = [
        VerificationResult(
            check_name="test1",
            passed=True,
            score=0.9,
            issues=[],
        ),
        VerificationResult(
            check_name="test2",
            passed=True,
            score=0.8,
            issues=[],
        ),
        VerificationResult(
            check_name="test3",
            passed=False,
            score=0.6,
            issues=["issue"],
        ),
    ]

    score = verifier.get_overall_score(results)
    assert score == pytest.approx(0.7667, rel=0.01)


def test_verifier_all_passed():
    """Test checking if all verifications passed."""
    verifier = Verifier()

    results_pass = [
        VerificationResult(check_name="test1", passed=True, score=0.9, issues=[]),
        VerificationResult(check_name="test2", passed=True, score=0.8, issues=[]),
    ]

    results_fail = [
        VerificationResult(check_name="test1", passed=True, score=0.9, issues=[]),
        VerificationResult(check_name="test2", passed=False, score=0.5, issues=["issue"]),
    ]

    assert verifier.all_passed(results_pass) is True
    assert verifier.all_passed(results_fail) is False
