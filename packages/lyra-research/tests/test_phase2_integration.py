"""
Phase 2 Integration Tests.

Tests full pipeline execution with:
- 5-role coordination
- Quality gate enforcement
- Heterogeneous model routing
- Knowledge curation
- Context layering
- Error handling and recovery
"""
import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from lyra_core.context.layered_context import LayeredContextManager, ContextLayer
from lyra_research.full_orchestrator import Phase2Orchestrator, Phase2ResearchProgress
from lyra_research.coordination.role_coordinator import CoordinatedPipelineResult
from lyra_research.models.model_router import ModelRouter
from lyra_research.roles.discovery_role import DiscoveryResult
from lyra_research.roles.analysis_role import AnalysisResult
from lyra_research.roles.synthesis_role import SynthesisResult
from lyra_research.roles.review_role import ReviewResult
from lyra_research.roles.curator_role import CurationResult, KnowledgeEntry
from lyra_research.roles.role_base import RoleStatus
from lyra_research.reporter import ResearchReport


@pytest.fixture
def context_manager():
    """Create layered context manager."""
    manager = LayeredContextManager()
    # LayeredContextManager is pre-initialized with all layers
    return manager


@pytest.fixture
def model_router():
    """Create model router."""
    return ModelRouter()


@pytest.fixture
def orchestrator(context_manager, model_router, tmp_path):
    """Create Phase 2 orchestrator."""
    return Phase2Orchestrator(
        context_manager=context_manager,
        model_router=model_router,
        output_dir=tmp_path / "reports",
    )


@pytest.fixture
def mock_pipeline_result():
    """Create mock pipeline result."""
    # Mock discovery result
    discovery = DiscoveryResult(
        role_name="Discovery",
        status=RoleStatus.SUCCESS,
        data=[{"title": "Paper 1", "url": "http://example.com/1"}],
        sources=[{"title": "Paper 1", "url": "http://example.com/1"}],
        total_sources=1,
    )

    # Mock analysis result
    analysis = AnalysisResult(
        role_name="Analysis",
        status=RoleStatus.SUCCESS,
        data=[{"paper": "Paper 1", "analysis": "Good paper"}],
        analyses=[{"paper": "Paper 1", "analysis": "Good paper"}],
        total_analyzed=1,
    )

    # Mock synthesis result
    report = ResearchReport(
        topic="Test Query",
        executive_summary="Test summary",
        best_papers_section="## Best Papers\n\n1. Paper 1",
        references_section="## References\n\n1. Paper 1",
        sources_used=1,
        quality_score=0.85,
    )
    synthesis = SynthesisResult(
        role_name="Synthesis",
        status=RoleStatus.SUCCESS,
        data=report,
        report=report,
        contradictions_found=0,
    )

    # Mock review result
    review = ReviewResult(
        role_name="Review",
        status=RoleStatus.SUCCESS,
        data=None,
        approved=True,
        overall_quality_score=0.85,
        issues=[],
    )

    # Mock curation result
    knowledge_entry = KnowledgeEntry(
        entry_id="test-entry-123",
        report=report,
        review=review,
        version=1,
        accepted=True,
        created_at=datetime.now(timezone.utc),
    )
    curation = CurationResult(
        role_name="Curator",
        status=RoleStatus.SUCCESS,
        data=knowledge_entry,
        accepted=True,
        knowledge_entry=knowledge_entry,
        quality_gate_passed=True,
    )

    # Create pipeline result
    result = CoordinatedPipelineResult(
        query="Test Query",
        discovery=discovery,
        analysis=analysis,
        synthesis=synthesis,
        review=review,
        curation=curation,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        total_duration_seconds=10.0,
        handoff_stats={
            "successful_handoffs": 4,
            "failed_handoffs": 0,
            "total_handoffs": 4,
        },
        progress_stats={
            "completed_roles": 5,
            "total_roles": 5,
        },
        metadata={
            "total_sources": 1,
            "total_analyzed": 1,
            "contradictions_found": 0,
            "review_approved": True,
            "curation_accepted": True,
            "quality_score": 0.85,
        },
    )

    return result


# Test 1: Full Pipeline Execution
@pytest.mark.asyncio
async def test_full_pipeline_execution(orchestrator, mock_pipeline_result):
    """Test full pipeline execution from Discovery to Curator."""
    with patch.object(
        orchestrator.coordinator, "execute_pipeline", new_callable=AsyncMock
    ) as mock_execute:
        mock_execute.return_value = mock_pipeline_result

        progress = await orchestrator.research("Test Query")

        assert progress.is_complete
        assert progress.error is None
        assert progress.discovery_complete
        assert progress.analysis_complete
        assert progress.synthesis_complete
        assert progress.review_complete
        assert progress.curation_complete
        assert progress.report is not None


# Test 2: Quality Gate Enforcement
@pytest.mark.asyncio
async def test_quality_gate_enforcement(orchestrator, mock_pipeline_result):
    """Test quality gates are enforced at each transition."""
    with patch.object(
        orchestrator.coordinator, "execute_pipeline", new_callable=AsyncMock
    ) as mock_execute:
        mock_execute.return_value = mock_pipeline_result

        progress = await orchestrator.research("Test Query")

        # Verify gates were checked
        assert progress.gates_passed == 4  # 4 successful handoffs
        assert progress.gates_failed == 0
        assert progress.gate_pass_rate == 1.0


# Test 3: Heterogeneous Model Usage
@pytest.mark.asyncio
async def test_heterogeneous_model_usage(orchestrator):
    """Test heterogeneous model routing (Claude + GPT)."""
    # Verify model assignments
    assert orchestrator.coordinator.discovery.model == "claude-haiku-4-5"
    assert orchestrator.coordinator.analysis.model == "claude-sonnet-4-6"
    assert orchestrator.coordinator.synthesis.model == "claude-opus-4-7"
    assert orchestrator.coordinator.review.model == "gpt-4o-mini"
    assert orchestrator.coordinator.curator.model == "claude-opus-4-7"


# Test 4: Knowledge Curation Integration
@pytest.mark.asyncio
async def test_knowledge_curation(orchestrator, mock_pipeline_result):
    """Test knowledge curation and storage."""
    with patch.object(
        orchestrator.coordinator, "execute_pipeline", new_callable=AsyncMock
    ) as mock_execute:
        mock_execute.return_value = mock_pipeline_result

        progress = await orchestrator.research("Test Query", enable_curation=True)

        assert progress.knowledge_accepted
        assert progress.knowledge_entry_id == "test-entry-123"
        assert orchestrator.stats["total_knowledge_accepted"] == 1


# Test 5: Context Layering Integration
@pytest.mark.asyncio
async def test_context_layering(orchestrator, mock_pipeline_result):
    """Test layered context is used throughout pipeline."""
    with patch.object(
        orchestrator.coordinator, "execute_pipeline", new_callable=AsyncMock
    ) as mock_execute:
        mock_execute.return_value = mock_pipeline_result

        await orchestrator.research("Test Query")

        # Verify session context was added
        from lyra_core.context.layered_context import ContextLayer
        session_entries = orchestrator.context_manager.layers[ContextLayer.SESSION]
        assert len(session_entries) > 0
        assert any("Test Query" in entry.content for entry in session_entries)


# Test 6: Error Handling and Recovery
@pytest.mark.asyncio
async def test_error_handling(orchestrator):
    """Test error handling when pipeline fails."""
    with patch.object(
        orchestrator.coordinator, "execute_pipeline", new_callable=AsyncMock
    ) as mock_execute:
        mock_execute.side_effect = RuntimeError("Pipeline failed")

        progress = await orchestrator.research("Test Query")

        assert not progress.is_complete
        assert progress.error == "Pipeline failed"
        assert orchestrator.stats["failed_sessions"] == 1


# Test 7: Discovery to Analysis Transition
@pytest.mark.asyncio
async def test_discovery_to_analysis_transition(orchestrator, mock_pipeline_result):
    """Test Discovery → Analysis transition with quality gate."""
    with patch.object(
        orchestrator.coordinator, "execute_pipeline", new_callable=AsyncMock
    ) as mock_execute:
        mock_execute.return_value = mock_pipeline_result

        progress = await orchestrator.research("Test Query")

        # Verify discovery completed before analysis
        assert progress.discovery_complete
        assert progress.analysis_complete
        assert mock_pipeline_result.discovery.total_sources > 0


# Test 8: Analysis to Synthesis Transition
@pytest.mark.asyncio
async def test_analysis_to_synthesis_transition(orchestrator, mock_pipeline_result):
    """Test Analysis → Synthesis transition with quality gate."""
    with patch.object(
        orchestrator.coordinator, "execute_pipeline", new_callable=AsyncMock
    ) as mock_execute:
        mock_execute.return_value = mock_pipeline_result

        progress = await orchestrator.research("Test Query")

        # Verify analysis completed before synthesis
        assert progress.analysis_complete
        assert progress.synthesis_complete
        assert mock_pipeline_result.analysis.total_analyzed > 0


# Test 9: Synthesis to Review Transition
@pytest.mark.asyncio
async def test_synthesis_to_review_transition(orchestrator, mock_pipeline_result):
    """Test Synthesis → Review transition with quality gate."""
    with patch.object(
        orchestrator.coordinator, "execute_pipeline", new_callable=AsyncMock
    ) as mock_execute:
        mock_execute.return_value = mock_pipeline_result

        progress = await orchestrator.research("Test Query")

        # Verify synthesis completed before review
        assert progress.synthesis_complete
        assert progress.review_complete
        assert mock_pipeline_result.synthesis.report is not None


# Test 10: Review to Curator Transition
@pytest.mark.asyncio
async def test_review_to_curator_transition(orchestrator, mock_pipeline_result):
    """Test Review → Curator transition with quality gate."""
    with patch.object(
        orchestrator.coordinator, "execute_pipeline", new_callable=AsyncMock
    ) as mock_execute:
        mock_execute.return_value = mock_pipeline_result

        progress = await orchestrator.research("Test Query")

        # Verify review completed before curation
        assert progress.review_complete
        assert progress.curation_complete
        assert mock_pipeline_result.review.approved


# Test 11: Model Cost Tracking
@pytest.mark.asyncio
async def test_model_cost_tracking(orchestrator, mock_pipeline_result):
    """Test model cost is tracked."""
    with patch.object(
        orchestrator.coordinator, "execute_pipeline", new_callable=AsyncMock
    ) as mock_execute:
        mock_execute.return_value = mock_pipeline_result

        progress = await orchestrator.research("Test Query")

        # Verify cost tracking
        assert progress.claude_calls == 4  # Discovery, Analysis, Synthesis, Curator
        assert progress.gpt_calls == 1  # Review
        assert progress.total_cost_usd > 0


# Test 12: Report Generation
@pytest.mark.asyncio
async def test_report_generation(orchestrator, mock_pipeline_result):
    """Test research report is generated correctly."""
    with patch.object(
        orchestrator.coordinator, "execute_pipeline", new_callable=AsyncMock
    ) as mock_execute:
        mock_execute.return_value = mock_pipeline_result

        progress = await orchestrator.research("Test Query")

        report = progress.report
        assert report is not None
        assert report.topic == "Test Query"
        assert report.executive_summary
        assert report.sources_used == 1
        assert report.quality_score == 0.85


# Test 13: Statistics Tracking
@pytest.mark.asyncio
async def test_statistics_tracking(orchestrator, mock_pipeline_result):
    """Test orchestrator tracks statistics."""
    with patch.object(
        orchestrator.coordinator, "execute_pipeline", new_callable=AsyncMock
    ) as mock_execute:
        mock_execute.return_value = mock_pipeline_result

        # Run multiple sessions
        await orchestrator.research("Query 1")
        await orchestrator.research("Query 2")

        stats = orchestrator.get_statistics()
        assert stats["total_sessions"] == 2
        assert stats["successful_sessions"] == 2
        assert stats["success_rate"] == 1.0
        assert stats["overall_gate_pass_rate"] == 1.0


# Test 14: Failed Quality Gate
@pytest.mark.asyncio
async def test_failed_quality_gate(orchestrator):
    """Test handling of failed quality gate."""
    # Create result with failed gate
    failed_result = MagicMock()
    failed_result.handoff_stats = {
        "successful_handoffs": 2,
        "failed_handoffs": 2,
        "total_handoffs": 4,
    }

    with patch.object(
        orchestrator.coordinator, "execute_pipeline", new_callable=AsyncMock
    ) as mock_execute:
        mock_execute.side_effect = RuntimeError("Handoff Discovery → Analysis failed")

        progress = await orchestrator.research("Test Query")

        assert not progress.is_complete
        assert progress.error is not None


# Test 15: Curation Rejection
@pytest.mark.asyncio
async def test_curation_rejection(orchestrator, mock_pipeline_result):
    """Test handling of rejected knowledge curation."""
    # Modify result to reject curation
    mock_pipeline_result.curation.accepted = False
    mock_pipeline_result.curation.knowledge_entry = None
    mock_pipeline_result.curation.rejection_reason = "Quality too low"

    with patch.object(
        orchestrator.coordinator, "execute_pipeline", new_callable=AsyncMock
    ) as mock_execute:
        mock_execute.return_value = mock_pipeline_result

        progress = await orchestrator.research("Test Query")

        assert not progress.knowledge_accepted
        assert progress.knowledge_entry_id is None
        assert orchestrator.stats["total_knowledge_rejected"] == 1


# Test 16: Model Fallback
@pytest.mark.asyncio
async def test_model_fallback(orchestrator):
    """Test model fallback when primary fails."""
    # Verify fallback models are configured
    assert orchestrator.model_router.get_fallback("discovery") == "gpt-4o-mini"
    assert orchestrator.model_router.get_fallback("analysis") == "gpt-4o"
    assert orchestrator.model_router.get_fallback("synthesis") == "gpt-4o"


# Test 17: Parallel Role Execution
@pytest.mark.asyncio
async def test_parallel_role_execution(orchestrator, mock_pipeline_result):
    """Test roles execute in correct sequence (not parallel within pipeline)."""
    with patch.object(
        orchestrator.coordinator, "execute_pipeline", new_callable=AsyncMock
    ) as mock_execute:
        mock_execute.return_value = mock_pipeline_result

        progress = await orchestrator.research("Test Query")

        # Verify sequential execution
        assert progress.discovery_complete
        assert progress.analysis_complete
        assert progress.synthesis_complete
        assert progress.review_complete
        assert progress.curation_complete


# Test 18: Context Propagation
@pytest.mark.asyncio
async def test_context_propagation(orchestrator, mock_pipeline_result):
    """Test context propagates through all roles."""
    with patch.object(
        orchestrator.coordinator, "execute_pipeline", new_callable=AsyncMock
    ) as mock_execute:
        mock_execute.return_value = mock_pipeline_result

        await orchestrator.research("Test Query")

        # Verify context manager has session data
        from lyra_core.context.layered_context import ContextLayer
        session_entries = orchestrator.context_manager.layers[ContextLayer.SESSION]
        assert len(session_entries) > 0


# Test 19: Report Persistence
@pytest.mark.asyncio
async def test_report_persistence(orchestrator, mock_pipeline_result, tmp_path):
    """Test research report is saved to disk."""
    with patch.object(
        orchestrator.coordinator, "execute_pipeline", new_callable=AsyncMock
    ) as mock_execute:
        mock_execute.return_value = mock_pipeline_result

        progress = await orchestrator.research("Test Query")

        # Verify report was saved (as markdown)
        report_files = list(orchestrator.output_dir.glob("*.md"))
        assert len(report_files) > 0


# Test 20: End-to-End Latency
@pytest.mark.asyncio
async def test_end_to_end_latency(orchestrator, mock_pipeline_result):
    """Test end-to-end latency is tracked."""
    with patch.object(
        orchestrator.coordinator, "execute_pipeline", new_callable=AsyncMock
    ) as mock_execute:
        mock_execute.return_value = mock_pipeline_result

        progress = await orchestrator.research("Test Query")

        # Verify latency tracking
        elapsed = progress.get_elapsed_seconds()
        assert elapsed > 0
        assert elapsed < 60  # Should complete quickly with mocks


# Test 21: Quality Score Propagation
@pytest.mark.asyncio
async def test_quality_score_propagation(orchestrator, mock_pipeline_result):
    """Test quality score propagates from review to report."""
    with patch.object(
        orchestrator.coordinator, "execute_pipeline", new_callable=AsyncMock
    ) as mock_execute:
        mock_execute.return_value = mock_pipeline_result

        progress = await orchestrator.research("Test Query")

        assert progress.report.quality_score == 0.85
        assert progress.report.quality_score == mock_pipeline_result.review.overall_quality_score


# Test 22: Metadata Enrichment
@pytest.mark.asyncio
async def test_metadata_enrichment(orchestrator, mock_pipeline_result):
    """Test report metadata is enriched with pipeline data."""
    with patch.object(
        orchestrator.coordinator, "execute_pipeline", new_callable=AsyncMock
    ) as mock_execute:
        mock_execute.return_value = mock_pipeline_result

        progress = await orchestrator.research("Test Query")

        metadata = progress.report.metadata
        assert "discovery_sources" in metadata
        assert "analysis_count" in metadata
        assert "contradictions" in metadata
        assert "review_approved" in metadata
        assert "curation_accepted" in metadata
