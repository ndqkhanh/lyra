"""Tests for 5 specialized roles (Phase 2 Week 5).

Tests:
- Role base class (5 tests)
- Discovery role (5 tests)
- Analysis role (5 tests)
- Synthesis role (5 tests)
- Review role (5 tests)
- Curator role (5 tests)
- Role orchestrator (5 tests)

Total: 35 tests
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from lyra_core.context.layered_context import LayeredContextManager
from lyra_research.agents.analysis import Analysis
from lyra_research.discovery import ResearchSource, SourceType
from lyra_research.reporter import ResearchReport
from lyra_research.roles import (
    AnalysisResult,
    AnalysisRole,
    CurationResult,
    CuratorRole,
    DiscoveryResult,
    DiscoveryRole,
    PipelineResult,
    ReviewIssue,
    ReviewResult,
    ReviewRole,
    Role,
    RoleOrchestrator,
    RoleResult,
    RoleStatus,
    SynthesisResult,
    SynthesisRole,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def context_manager():
    """Create a layered context manager."""
    return LayeredContextManager(max_tokens=100_000)


@pytest.fixture
def sample_source():
    """Create a sample research source."""
    return ResearchSource(
        id="test-source-1",
        title="Test Paper on AI",
        url="https://arxiv.org/abs/2401.00001",
        source_type=SourceType.PAPER,
        published_date=datetime.now(timezone.utc),
        citations=100,
        metadata={"venue": "NeurIPS 2024"},
    )


@pytest.fixture
def sample_sources(sample_source):
    """Create multiple sample sources."""
    sources = [sample_source]
    for i in range(2, 6):
        sources.append(
            ResearchSource(
                id=f"test-source-{i}",
                title=f"Test Paper {i}",
                url=f"https://arxiv.org/abs/2401.0000{i}",
                source_type=SourceType.PAPER,
                published_date=datetime.now(timezone.utc),
                citations=50 * i,
            )
        )
    return sources


@pytest.fixture
def sample_analysis():
    """Create a sample analysis."""
    return Analysis(
        source_id="test-source-1",
        analysis_type="quality",
        findings=["High quality paper", "Strong citations"],
        metadata={"quality_score": 0.85},
        confidence=0.9,
        quality_score=0.85,
    )


@pytest.fixture
def sample_analyses(sample_analysis):
    """Create multiple sample analyses."""
    analyses = [sample_analysis]
    for i in range(2, 6):
        analyses.append(
            Analysis(
                source_id=f"test-source-{i}",
                analysis_type="quality",
                findings=[f"Finding {i}"],
                metadata={"quality_score": 0.7 + i * 0.05},
                confidence=0.8,
                quality_score=0.7 + i * 0.05,
            )
        )
    return analyses


@pytest.fixture
def sample_report():
    """Create a sample research report."""
    return ResearchReport(
        topic="Test Research Report",
        executive_summary="This is a comprehensive test report on AI research. " * 10,  # Make it long enough
        taxonomy_section="Taxonomy content",
        best_papers_section="Paper 1\nPaper 2\nPaper 3",
        gaps_section="Gap analysis",
        contested_claims_section="",
        references_section="Ref 1\nRef 2",
        sources_used=5,
        quality_score=0.85,
    )


# ============================================================================
# Role Base Class Tests (5 tests)
# ============================================================================


def test_role_result_creation():
    """Test RoleResult creation."""
    result = RoleResult(
        role_name="TestRole",
        status=RoleStatus.SUCCESS,
        data={"test": "data"},
    )

    assert result.role_name == "TestRole"
    assert result.status == RoleStatus.SUCCESS
    assert result.data == {"test": "data"}
    assert result.error is None
    assert result.completed_at is None


def test_role_result_mark_complete():
    """Test marking result as complete."""
    result = RoleResult(
        role_name="TestRole",
        status=RoleStatus.SUCCESS,
        data=None,
    )

    assert result.completed_at is None
    result.mark_complete()
    assert result.completed_at is not None


def test_role_result_duration():
    """Test duration calculation."""
    result = RoleResult(
        role_name="TestRole",
        status=RoleStatus.SUCCESS,
        data=None,
    )

    # Before completion
    assert result.duration_seconds() == 0.0

    # After completion
    result.mark_complete()
    duration = result.duration_seconds()
    assert duration >= 0.0


def test_role_status_enum():
    """Test RoleStatus enum values."""
    assert RoleStatus.PENDING.value == "pending"
    assert RoleStatus.RUNNING.value == "running"
    assert RoleStatus.SUCCESS.value == "success"
    assert RoleStatus.FAILED.value == "failed"
    assert RoleStatus.VALIDATION_ERROR.value == "validation_error"


def test_role_base_initialization(context_manager):
    """Test Role base class initialization."""

    class TestRole(Role):
        async def execute(self, input_data):
            return RoleResult(
                role_name=self.name, status=RoleStatus.SUCCESS, data=input_data
            )

        def validate_input(self, input_data):
            return True

        def validate_output(self, output):
            return True

    role = TestRole("TestRole", "claude-sonnet-4-6", context_manager)

    assert role.name == "TestRole"
    assert role.model == "claude-sonnet-4-6"
    assert role.context_manager == context_manager


# ============================================================================
# Discovery Role Tests (5 tests)
# ============================================================================


@pytest.mark.asyncio
async def test_discovery_role_initialization(context_manager):
    """Test DiscoveryRole initialization."""
    role = DiscoveryRole(context_manager)

    assert role.name == "Discovery"
    assert role.model == "claude-haiku-4-5"
    assert len(role.discovery_agents) == 6  # 6 discovery agents


@pytest.mark.asyncio
async def test_discovery_role_validate_input():
    """Test DiscoveryRole input validation."""
    role = DiscoveryRole(LayeredContextManager())

    # Valid inputs
    assert role.validate_input("test query") is True
    assert role.validate_input("a" * 100) is True

    # Invalid inputs
    assert role.validate_input("") is False
    assert role.validate_input("   ") is False
    assert role.validate_input(123) is False
    assert role.validate_input("a" * 1001) is False  # Too long


@pytest.mark.asyncio
async def test_discovery_role_validate_output(sample_sources):
    """Test DiscoveryRole output validation."""
    role = DiscoveryRole(LayeredContextManager())

    # Valid outputs
    assert role.validate_output(sample_sources) is True
    assert role.validate_output([]) is True  # Empty is valid

    # Invalid outputs
    assert role.validate_output("not a list") is False
    assert role.validate_output([{"not": "a source"}]) is False


@pytest.mark.asyncio
async def test_discovery_role_execute_success(context_manager, sample_sources):
    """Test DiscoveryRole execution success."""
    role = DiscoveryRole(context_manager)

    # Mock discovery agents
    for agent in role.discovery_agents:
        agent.discover = AsyncMock(return_value=sample_sources[:2])

    result = await role.execute("test query")

    assert result.status == RoleStatus.RUNNING
    assert len(result.sources) > 0
    assert result.total_sources > 0
    assert "query" in result.metadata


@pytest.mark.asyncio
async def test_discovery_role_execute_with_errors(context_manager):
    """Test DiscoveryRole handles agent errors gracefully."""
    role = DiscoveryRole(context_manager)

    # Mock some agents to fail
    role.discovery_agents[0].discover = AsyncMock(side_effect=Exception("API error"))
    role.discovery_agents[1].discover = AsyncMock(return_value=[])

    result = await role.execute("test query")

    # Should not fail completely
    assert result.status == RoleStatus.RUNNING
    assert isinstance(result.sources, list)


# ============================================================================
# Analysis Role Tests (5 tests)
# ============================================================================


@pytest.mark.asyncio
async def test_analysis_role_initialization(context_manager):
    """Test AnalysisRole initialization."""
    role = AnalysisRole(context_manager)

    assert role.name == "Analysis"
    assert role.model == "claude-sonnet-4-6"
    assert len(role.analysis_agents) == 4  # 4 analysis agents


@pytest.mark.asyncio
async def test_analysis_role_validate_input(sample_sources):
    """Test AnalysisRole input validation."""
    role = AnalysisRole(LayeredContextManager())

    # Valid inputs
    assert role.validate_input(sample_sources) is True
    assert role.validate_input([]) is True  # Empty is valid

    # Invalid inputs
    assert role.validate_input("not a list") is False
    assert role.validate_input([{"not": "a source"}]) is False


@pytest.mark.asyncio
async def test_analysis_role_validate_output(sample_analyses):
    """Test AnalysisRole output validation."""
    role = AnalysisRole(LayeredContextManager())

    # Valid outputs
    assert role.validate_output(sample_analyses) is True
    assert role.validate_output([]) is True

    # Invalid outputs
    assert role.validate_output("not a list") is False

    # Invalid analysis (bad quality score)
    bad_analysis = Analysis(
        source_id="test",
        analysis_type="quality",
        quality_score=1.5,  # Invalid: > 1.0
    )
    assert role.validate_output([bad_analysis]) is False


@pytest.mark.asyncio
async def test_analysis_role_select_agents_for_source(context_manager, sample_source):
    """Test agent selection based on source type."""
    role = AnalysisRole(context_manager)

    # ArXiv source should get paper + citation + quality agents
    agents = role._select_agents_for_source(sample_source)
    assert len(agents) >= 2  # At least quality + paper


@pytest.mark.asyncio
async def test_analysis_role_execute_success(context_manager, sample_sources, sample_analysis):
    """Test AnalysisRole execution success."""
    role = AnalysisRole(context_manager)

    # Mock analysis agents
    for agent in role.analysis_agents:
        agent.analyze = AsyncMock(return_value=sample_analysis)

    result = await role.execute(sample_sources)

    assert result.status == RoleStatus.RUNNING
    assert len(result.analyses) > 0
    assert result.total_analyzed > 0
    assert result.average_quality_score >= 0.0


# ============================================================================
# Synthesis Role Tests (5 tests)
# ============================================================================


@pytest.mark.asyncio
async def test_synthesis_role_initialization(context_manager):
    """Test SynthesisRole initialization."""
    role = SynthesisRole(context_manager)

    assert role.name == "Synthesis"
    assert role.model == "claude-opus-4-7"
    assert role.cross_source_synthesizer is not None
    assert role.contradiction_detector is not None


@pytest.mark.asyncio
async def test_synthesis_role_validate_input(sample_analyses):
    """Test SynthesisRole input validation."""
    role = SynthesisRole(LayeredContextManager())

    # Valid inputs
    assert role.validate_input(sample_analyses) is True

    # Invalid inputs
    assert role.validate_input([]) is False  # Requires at least one analysis
    assert role.validate_input("not a list") is False


@pytest.mark.asyncio
async def test_synthesis_role_validate_output(sample_report):
    """Test SynthesisRole output validation."""
    role = SynthesisRole(LayeredContextManager())

    # Valid output
    assert role.validate_output(sample_report) is True

    # Invalid outputs
    assert role.validate_output(None) is False
    assert role.validate_output("not a report") is False

    # Invalid report (missing required fields)
    bad_report = ResearchReport(
        topic="",  # Empty topic
        executive_summary="test",
    )
    assert role.validate_output(bad_report) is False


@pytest.mark.asyncio
async def test_synthesis_role_execute_success(context_manager, sample_analyses):
    """Test SynthesisRole execution success."""
    role = SynthesisRole(context_manager)

    # Mock synthesis agents
    role.cross_source_synthesizer.synthesize = AsyncMock(
        return_value={
            "title": "Test Report",
            "summary": "Test summary",
            "findings": ["Finding 1"],
            "taxonomy": {"cat1": ["item1"]},
        }
    )
    role.contradiction_detector.detect = AsyncMock(return_value=[])
    role.evidence_auditor.audit = AsyncMock(return_value={"verified": ["ev1"]})
    role.falsification_checker.check = AsyncMock(return_value={"tests": ["test1"]})

    result = await role.execute(sample_analyses)

    assert result.status == RoleStatus.RUNNING
    assert result.report is not None
    assert result.report.title == "Test Report"


@pytest.mark.asyncio
async def test_synthesis_role_execute_empty_analyses(context_manager):
    """Test SynthesisRole with empty analyses."""
    role = SynthesisRole(context_manager)

    result = await role.execute([])

    # Should handle gracefully
    assert result.data is None


# ============================================================================
# Review Role Tests (5 tests)
# ============================================================================


@pytest.mark.asyncio
async def test_review_role_initialization(context_manager):
    """Test ReviewRole initialization."""
    role = ReviewRole(context_manager)

    assert role.name == "Review"
    assert role.model == "gpt-4o-mini"  # Heterogeneous model


@pytest.mark.asyncio
async def test_review_role_validate_input(sample_report):
    """Test ReviewRole input validation."""
    role = ReviewRole(LayeredContextManager())

    # Valid input
    assert role.validate_input(sample_report) is True

    # Invalid inputs
    assert role.validate_input(None) is False
    assert role.validate_input("not a report") is False

    # Invalid report (missing fields)
    bad_report = ResearchReport(
        title="",
        summary="",
        findings=[],
        taxonomy={},
        contradictions=[],
        evidence={},
        falsification_tests={},
        sources_analyzed=0,
    )
    assert role.validate_input(bad_report) is False


@pytest.mark.asyncio
async def test_review_role_validate_output():
    """Test ReviewRole output validation."""
    role = ReviewRole(LayeredContextManager())

    # Valid output
    valid_output = {
        "approved": True,
        "issues": [],
        "quality_score": 0.85,
    }
    assert role.validate_output(valid_output) is True

    # Invalid outputs
    assert role.validate_output({}) is False  # Missing fields
    assert role.validate_output({"approved": True}) is False  # Missing fields
    assert role.validate_output({"approved": True, "issues": [], "quality_score": 1.5}) is False  # Bad score


@pytest.mark.asyncio
async def test_review_role_execute_success(context_manager, sample_report):
    """Test ReviewRole execution success."""
    role = ReviewRole(context_manager)

    result = await role.execute(sample_report)

    assert result.status == RoleStatus.RUNNING
    assert isinstance(result.approved, bool)
    assert isinstance(result.issues, list)
    assert 0.0 <= result.overall_quality_score <= 1.0


@pytest.mark.asyncio
async def test_review_role_quality_scoring(context_manager):
    """Test ReviewRole quality scoring logic."""
    role = ReviewRole(context_manager)

    # High quality report
    good_report = ResearchReport(
        topic="Excellent Report",
        executive_summary="A" * 200,
        taxonomy_section="Taxonomy",
        best_papers_section="Papers",
        gaps_section="Gaps",
        references_section="References",
        sources_used=10,
        quality_score=0.9,
    )

    result = await role.execute(good_report)
    assert result.overall_quality_score >= 0.7


# ============================================================================
# Curator Role Tests (5 tests)
# ============================================================================


@pytest.mark.asyncio
async def test_curator_role_initialization(context_manager):
    """Test CuratorRole initialization."""
    role = CuratorRole(context_manager)

    assert role.name == "Curator"
    assert role.model == "claude-opus-4-7"
    assert role.MIN_QUALITY_SCORE == 0.7
    assert role.MIN_SOURCES_ANALYZED == 5


@pytest.mark.asyncio
async def test_curator_role_validate_input(sample_report):
    """Test CuratorRole input validation."""
    role = CuratorRole(LayeredContextManager())

    review_result = ReviewResult(
        role_name="Review",
        status=RoleStatus.SUCCESS,
        data={},
        approved=True,
        overall_quality_score=0.85,
    )

    # Valid input
    assert role.validate_input((sample_report, review_result)) is True

    # Invalid inputs
    assert role.validate_input("not a tuple") is False
    assert role.validate_input((sample_report,)) is False  # Wrong length
    assert role.validate_input((sample_report, "not a review")) is False


@pytest.mark.asyncio
async def test_curator_role_quality_gates(context_manager, sample_report):
    """Test CuratorRole quality gate checks."""
    role = CuratorRole(context_manager)

    review_result = ReviewResult(
        role_name="Review",
        status=RoleStatus.SUCCESS,
        data={},
        approved=True,
        overall_quality_score=0.85,
        issues=[],
    )

    checks = role._run_quality_gates(sample_report, review_result)

    assert isinstance(checks, dict)
    assert "review_approved" in checks
    assert "quality_score" in checks
    assert "source_coverage" in checks


@pytest.mark.asyncio
async def test_curator_role_execute_accept(context_manager, sample_report):
    """Test CuratorRole accepts high-quality report."""
    role = CuratorRole(context_manager)

    review_result = ReviewResult(
        role_name="Review",
        status=RoleStatus.SUCCESS,
        data={},
        approved=True,
        overall_quality_score=0.85,
        issues=[],
    )

    result = await role.execute(sample_report, review_result)

    assert result.status == RoleStatus.SUCCESS
    assert result.accepted is True
    assert result.knowledge_entry is not None
    assert result.quality_gate_passed is True


@pytest.mark.asyncio
async def test_curator_role_execute_reject(context_manager):
    """Test CuratorRole rejects low-quality report."""
    role = CuratorRole(context_manager)

    # Low quality report
    bad_report = ResearchReport(
        topic="Bad Report",
        executive_summary="Too short",
        sources_used=2,  # Too few sources
        quality_score=0.3,
    )

    review_result = ReviewResult(
        role_name="Review",
        status=RoleStatus.SUCCESS,
        data={},
        approved=False,
        overall_quality_score=0.5,  # Low score
        issues=[
            ReviewIssue(
                severity="critical",
                category="completeness",
                description="No findings",
                suggestion="Add findings",
            )
        ],
    )

    result = await role.execute(bad_report, review_result)

    assert result.accepted is False
    assert result.rejection_reason is not None
    assert result.quality_gate_passed is False


# ============================================================================
# Role Orchestrator Tests (5 tests)
# ============================================================================


@pytest.mark.asyncio
async def test_role_orchestrator_initialization(context_manager):
    """Test RoleOrchestrator initialization."""
    orchestrator = RoleOrchestrator(context_manager)

    assert orchestrator.discovery is not None
    assert orchestrator.analysis is not None
    assert orchestrator.synthesis is not None
    assert orchestrator.review is not None
    assert orchestrator.curator is not None


@pytest.mark.asyncio
async def test_role_orchestrator_execute_pipeline_mocked(context_manager, sample_sources, sample_analyses, sample_report):
    """Test RoleOrchestrator full pipeline with mocks."""
    orchestrator = RoleOrchestrator(context_manager)

    # Mock all roles
    orchestrator.discovery.run = AsyncMock(
        return_value=DiscoveryResult(
            role_name="Discovery",
            status=RoleStatus.SUCCESS,
            data=sample_sources,
            sources=sample_sources,
            total_sources=len(sample_sources),
        )
    )

    orchestrator.analysis.run = AsyncMock(
        return_value=AnalysisResult(
            role_name="Analysis",
            status=RoleStatus.SUCCESS,
            data=sample_analyses,
            analyses=sample_analyses,
            total_analyzed=len(sample_analyses),
            average_quality_score=0.8,
        )
    )

    orchestrator.synthesis.run = AsyncMock(
        return_value=SynthesisResult(
            role_name="Synthesis",
            status=RoleStatus.SUCCESS,
            data=sample_report,
            report=sample_report,
        )
    )

    orchestrator.review.run = AsyncMock(
        return_value=ReviewResult(
            role_name="Review",
            status=RoleStatus.SUCCESS,
            data={},
            approved=True,
            overall_quality_score=0.85,
        )
    )

    orchestrator.curator.run = AsyncMock(
        return_value=CurationResult(
            role_name="Curator",
            status=RoleStatus.SUCCESS,
            data=None,
            accepted=True,
            quality_gate_passed=True,
        )
    )

    result = await orchestrator.execute_pipeline("test query")

    assert result.query == "test query"
    assert result.discovery is not None
    assert result.analysis is not None
    assert result.synthesis is not None
    assert result.review is not None
    assert result.curation is not None
    assert result.total_duration_seconds >= 0.0


@pytest.mark.asyncio
async def test_role_orchestrator_execute_partial_pipeline(context_manager, sample_sources):
    """Test RoleOrchestrator partial pipeline execution."""
    orchestrator = RoleOrchestrator(context_manager)

    # Mock discovery
    orchestrator.discovery.run = AsyncMock(
        return_value=DiscoveryResult(
            role_name="Discovery",
            status=RoleStatus.SUCCESS,
            data=sample_sources,
            sources=sample_sources,
            total_sources=len(sample_sources),
        )
    )

    result = await orchestrator.execute_partial_pipeline("test query", stop_at="discovery")

    assert "discovery" in result
    assert "analysis" not in result


@pytest.mark.asyncio
async def test_role_orchestrator_get_pipeline_stats(context_manager, sample_sources, sample_analyses, sample_report):
    """Test RoleOrchestrator pipeline statistics."""
    orchestrator = RoleOrchestrator(context_manager)

    # Create mock pipeline result
    pipeline_result = PipelineResult(
        query="test query",
        discovery=DiscoveryResult(
            role_name="Discovery",
            status=RoleStatus.SUCCESS,
            data=sample_sources,
            sources=sample_sources,
            total_sources=5,
        ),
        analysis=AnalysisResult(
            role_name="Analysis",
            status=RoleStatus.SUCCESS,
            data=sample_analyses,
            analyses=sample_analyses,
            total_analyzed=5,
            average_quality_score=0.8,
        ),
        synthesis=SynthesisResult(
            role_name="Synthesis",
            status=RoleStatus.SUCCESS,
            data=sample_report,
            report=sample_report,
            contradictions_found=0,
            evidence_verified=2,
        ),
        review=ReviewResult(
            role_name="Review",
            status=RoleStatus.SUCCESS,
            data={},
            approved=True,
            overall_quality_score=0.85,
            issues=[],
        ),
        curation=CurationResult(
            role_name="Curator",
            status=RoleStatus.SUCCESS,
            data=None,
            accepted=True,
        ),
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        total_duration_seconds=10.5,
    )

    stats = orchestrator.get_pipeline_stats(pipeline_result)

    assert stats["query"] == "test query"
    assert stats["total_duration_seconds"] == 10.5
    assert stats["sources_discovered"] == 5
    assert stats["sources_analyzed"] == 5
    assert stats["review_approved"] is True
    assert stats["curation_accepted"] is True
    assert "role_durations" in stats


@pytest.mark.asyncio
async def test_role_orchestrator_handles_role_failure(context_manager):
    """Test RoleOrchestrator handles role failures."""
    orchestrator = RoleOrchestrator(context_manager)

    # Mock discovery to fail
    orchestrator.discovery.run = AsyncMock(
        return_value=DiscoveryResult(
            role_name="Discovery",
            status=RoleStatus.FAILED,
            data=None,
            error="Discovery failed",
        )
    )

    with pytest.raises(RuntimeError, match="Discovery failed"):
        await orchestrator.execute_pipeline("test query")
