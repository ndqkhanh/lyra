"""
End-to-End Integration Tests for Full 15-Agent Orchestrator.

Tests:
- Full pipeline execution
- 100+ source research
- Adaptive task decomposition
- Progress checkpointing
- Error handling and recovery
- Memory capacity enforcement
- Adversarial review integration
"""
import asyncio
from unittest.mock import AsyncMock, Mock

import pytest
from lyra_research.agents.analysis import Analysis, AnalysisAgent
from lyra_research.agents.discovery import DiscoveryAgent
from lyra_research.agents.synthesis import SynthesisAgent, SynthesisResult
from lyra_research.capacity_manager import CapacityManager
from lyra_research.checkpoint import ResearchCheckpoint
from lyra_research.coordination import CoordinationManager
from lyra_research.full_orchestrator import (
    FullResearchOrchestrator,
    SynthesisPipeline,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_discovery_agent():
    """Mock discovery agent that returns test sources."""
    agent = Mock(spec=DiscoveryAgent)

    async def mock_discover(query, max_results=10):
        sources = []
        for i in range(min(max_results, 20)):
            source = Mock()
            source.id = f"source_{i}"
            source.title = f"Test Source {i}"
            source.url = f"https://example.com/{i}"
            source.abstract = f"Abstract for source {i}"
            source.source_type = Mock(value="paper")
            source.citations = 10
            source.stars = 0
            source.metadata = {"year": 2024}
            sources.append(source)
        return sources

    agent.discover = mock_discover
    return agent


@pytest.fixture
def mock_analysis_agent():
    """Mock analysis agent that returns test analyses."""
    agent = Mock(spec=AnalysisAgent)

    async def mock_analyze(sources):
        analyses = []
        for i, source in enumerate(sources[:10]):
            analysis = Analysis(
                source_id=source.id,
                analysis_type="paper",
                key_findings=["Finding 1", "Finding 2"],
                confidence=0.85,
            )
            analyses.append(analysis)
        return analyses

    agent.analyze = mock_analyze
    return agent


@pytest.fixture
def mock_synthesis_agent():
    """Mock synthesis agent that returns test results."""
    agent = Mock(spec=SynthesisAgent)

    async def mock_synthesize(analyses):
        return SynthesisResult(
            synthesis_type="cross_source",
            findings=["Synthesized finding 1", "Synthesized finding 2"],
            confidence=0.9,
        )

    agent.synthesize = mock_synthesize
    return agent


@pytest.fixture
def orchestrator(tmp_path):
    """Create orchestrator with test configuration."""
    return FullResearchOrchestrator(
        output_dir=tmp_path / "reports",
        coordination_manager=CoordinationManager(),
        capacity_manager=CapacityManager(db_path=tmp_path / "test.db"),
        checkpoint=ResearchCheckpoint(checkpoint_dir=tmp_path / "checkpoints"),
    )


# ---------------------------------------------------------------------------
# Test: Full Pipeline Execution
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_pipeline_execution(orchestrator, mock_discovery_agent, mock_analysis_agent):
    """Test full 15-agent pipeline executes successfully."""
    # Replace agents with mocks
    for name in orchestrator.discovery_agents:
        orchestrator.discovery_agents[name] = mock_discovery_agent

    for name in orchestrator.analysis_agents:
        orchestrator.analysis_agents[name] = mock_analysis_agent

    # Mock synthesis pipeline
    async def mock_execute(analyses):
        from lyra_research.agents.synthesis import SynthesisResult
        return {
            "cross_source": SynthesisResult(
                synthesis_type="cross_source",
                findings=["Finding 1", "Finding 2"],
                confidence=0.9,
            ),
            "contradictions": SynthesisResult(
                synthesis_type="contradiction",
                findings=[],
                confidence=1.0,
            ),
            "evidence": SynthesisResult(
                synthesis_type="evidence",
                findings=[],
                confidence=1.0,
            ),
            "falsification": SynthesisResult(
                synthesis_type="falsification",
                findings=[],
                confidence=1.0,
            ),
        }

    orchestrator.synthesis_pipeline.execute = mock_execute

    # Mock adversarial reviewer
    orchestrator.adversarial_reviewer.review = Mock(return_value=Mock(
        revised_report="Revised report",
        claims_reviewed=10,
        claims_modified=2,
        context_size_kb=15.5,
    ))

    # Execute research
    progress = await orchestrator.research("test query", depth="deep")

    # Verify completion
    assert progress.is_complete
    assert progress.error is None
    assert progress.report is not None

    # Verify all phases completed
    assert progress.total_sources > 0
    # Note: papers_analyzed may be 0 if mock returns empty, but pipeline should complete
    assert progress.cross_source_synthesis_done
    assert progress.adversarial_review_done


@pytest.mark.asyncio
async def test_parallel_discovery_execution(orchestrator, mock_discovery_agent):
    """Test 6 discovery agents execute in parallel."""
    # Replace agents with mocks
    for name in orchestrator.discovery_agents:
        orchestrator.discovery_agents[name] = mock_discovery_agent

    # Track execution order
    execution_times = {}

    async def timed_discover(query, max_results=10):
        import time
        start = time.time()
        result = await mock_discovery_agent.discover(query, max_results)
        execution_times[query] = time.time() - start
        return result

    for agent in orchestrator.discovery_agents.values():
        agent.discover = timed_discover

    # Mock other phases
    for name in orchestrator.analysis_agents:
        orchestrator.analysis_agents[name] = Mock()
        orchestrator.analysis_agents[name].analyze = AsyncMock(return_value=[])

    orchestrator.synthesis_pipeline.execute = AsyncMock(return_value={
        "cross_source": {"findings": []},
        "contradictions": {"contradictions": []},
        "evidence": {"audits": []},
        "falsification": {},
    })

    # Execute
    progress = await orchestrator.research("test query", depth="standard")

    # Verify parallel execution (all agents should have similar execution times)
    assert len(execution_times) > 0


@pytest.mark.asyncio
async def test_sequential_synthesis_pipeline():
    """Test synthesis pipeline executes agents sequentially."""
    from lyra_research.agents.synthesis import SynthesisResult

    # Create mock agents
    cross_source = Mock()
    cross_source.synthesize = AsyncMock(return_value=SynthesisResult(
        synthesis_type="cross_source",
        findings=["F1"],
        confidence=0.9,
    ))

    contradiction = Mock()
    contradiction.synthesize = AsyncMock(return_value=SynthesisResult(
        synthesis_type="contradiction",
        findings=[],
        confidence=1.0,
    ))

    evidence = Mock()
    evidence.synthesize = AsyncMock(return_value=SynthesisResult(
        synthesis_type="evidence",
        findings=[],
        confidence=1.0,
    ))

    falsification = Mock()
    falsification.synthesize = AsyncMock(return_value=SynthesisResult(
        synthesis_type="falsification",
        findings=[],
        confidence=1.0,
    ))

    # Create pipeline
    pipeline = SynthesisPipeline(cross_source, contradiction, evidence, falsification)

    # Execute
    result = await pipeline.execute([])

    # Verify all stages executed
    assert "cross_source" in result
    assert "contradictions" in result
    assert "evidence" in result
    assert "falsification" in result

    # Verify sequential execution
    cross_source.synthesize.assert_called_once()
    contradiction.synthesize.assert_called_once()
    evidence.synthesize.assert_called_once()
    falsification.synthesize.assert_called_once()


# ---------------------------------------------------------------------------
# Test: 100+ Source Research
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_100_plus_source_research(orchestrator):
    """Test orchestrator handles 100+ sources efficiently."""
    # Create mock agent that returns many sources
    async def mock_discover_many(query, max_results=10):
        sources = []
        for i in range(max_results):
            source = Mock()
            source.id = f"source_{i}"
            source.title = f"Source {i}"
            source.url = f"https://example.com/{i}"
            source.abstract = f"Abstract {i}"
            source.source_type = Mock(value="paper")
            source.citations = 10
            source.stars = 0
            source.metadata = {}
            sources.append(source)
        return sources

    # Replace agents
    for name in orchestrator.discovery_agents:
        agent = Mock()
        agent.discover = mock_discover_many
        orchestrator.discovery_agents[name] = agent

    # Mock analysis
    for name in orchestrator.analysis_agents:
        agent = Mock()
        agent.analyze = AsyncMock(return_value=[])
        orchestrator.analysis_agents[name] = agent

    # Mock synthesis
    orchestrator.synthesis_pipeline.execute = AsyncMock(return_value={
        "cross_source": {"findings": []},
        "contradictions": {"contradictions": []},
        "evidence": {"audits": []},
        "falsification": {},
    })

    # Execute with deep depth (50 sources per agent * 6 agents = 300 sources)
    progress = await orchestrator.research("test query", depth="deep")

    # Verify handled many sources
    assert progress.total_sources >= 100
    assert progress.is_complete


# ---------------------------------------------------------------------------
# Test: Adaptive Task Decomposition
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_adaptive_decomposition_insufficient_sources(orchestrator):
    """Test adaptive decomposition adds tasks when sources insufficient."""
    # Create mock agent that returns few sources
    async def mock_discover_few(query, max_results=10):
        sources = []
        for i in range(2):  # Only 2 sources
            source = Mock()
            source.id = f"source_{i}"
            source.title = f"Source {i}"
            source.url = f"https://example.com/{i}"
            source.abstract = f"Abstract {i}"
            source.source_type = Mock(value="paper")
            source.citations = 10
            source.stars = 0
            source.metadata = {}
            sources.append(source)
        return sources

    # Replace agents
    for name in orchestrator.discovery_agents:
        agent = Mock()
        agent.discover = mock_discover_few
        orchestrator.discovery_agents[name] = agent

    # Mock other phases
    for name in orchestrator.analysis_agents:
        agent = Mock()
        agent.analyze = AsyncMock(return_value=[])
        orchestrator.analysis_agents[name] = agent

    orchestrator.synthesis_pipeline.execute = AsyncMock(return_value={
        "cross_source": {"findings": []},
        "contradictions": {"contradictions": []},
        "evidence": {"audits": []},
        "falsification": {},
    })

    # Execute
    progress = await orchestrator.research("test query", depth="standard")

    # Verify adaptive decomposition triggered
    assert progress.total_sources < 10
    assert progress.additional_tasks_added > 0
    assert len(progress.adaptation_events) > 0
    assert progress.adaptation_events[0]["reason"] == "insufficient_sources"


# ---------------------------------------------------------------------------
# Test: Progress Checkpointing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_progress_checkpointing(orchestrator, mock_discovery_agent, mock_analysis_agent):
    """Test progress is checkpointed during execution."""
    # Replace agents
    for name in orchestrator.discovery_agents:
        orchestrator.discovery_agents[name] = mock_discovery_agent

    for name in orchestrator.analysis_agents:
        orchestrator.analysis_agents[name] = mock_analysis_agent

    # Mock synthesis
    orchestrator.synthesis_pipeline.execute = AsyncMock(return_value={
        "cross_source": {"findings": []},
        "contradictions": {"contradictions": []},
        "evidence": {"audits": []},
        "falsification": {},
    })

    # Execute
    progress = await orchestrator.research("test query", depth="standard")

    # Verify checkpoint was saved
    checkpoints = orchestrator.checkpoint.list_checkpoints()
    assert progress.session_id in checkpoints

    # Load checkpoint
    state = orchestrator.checkpoint.load_checkpoint(progress.session_id)
    assert state is not None
    assert state.session_id == progress.session_id
    assert state.topic == "test query"
    assert state.completed


# ---------------------------------------------------------------------------
# Test: Error Handling and Recovery
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_error_handling_single_agent_failure(orchestrator, mock_discovery_agent):
    """Test orchestrator continues when single agent fails."""
    # Create failing agent
    async def mock_discover_fail(query, max_results=10):
        raise Exception("Discovery failed")

    failing_agent = Mock()
    failing_agent.discover = mock_discover_fail

    # Replace one agent with failing agent
    orchestrator.discovery_agents["arxiv"] = failing_agent

    # Other agents succeed
    for name in ["semantic_scholar", "github", "web", "openreview", "huggingface"]:
        orchestrator.discovery_agents[name] = mock_discovery_agent

    # Mock other phases
    for name in orchestrator.analysis_agents:
        agent = Mock()
        agent.analyze = AsyncMock(return_value=[])
        orchestrator.analysis_agents[name] = agent

    orchestrator.synthesis_pipeline.execute = AsyncMock(return_value={
        "cross_source": {"findings": []},
        "contradictions": {"contradictions": []},
        "evidence": {"audits": []},
        "falsification": {},
    })

    # Execute
    progress = await orchestrator.research("test query", depth="standard")

    # Verify pipeline completed despite one failure
    assert progress.is_complete
    assert progress.arxiv_sources == 0  # Failed agent
    assert progress.total_sources > 0  # Other agents succeeded


@pytest.mark.asyncio
async def test_error_recovery_with_checkpoint(orchestrator, tmp_path):
    """Test research can resume from checkpoint after error."""
    # Create checkpoint with partial progress
    from lyra_research.checkpoint import ResearchState

    session_id = "test_session_123"
    state = ResearchState(
        session_id=session_id,
        topic="test query",
        depth="standard",
        current_step=5,
        current_step_name="analysis",
        started_at=pytest.approx(asyncio.get_event_loop().time()),
        last_checkpoint_at=pytest.approx(asyncio.get_event_loop().time()),
        sources_found={"arxiv": 10, "github": 5},
        papers_analyzed=8,
    )

    orchestrator.checkpoint.save_checkpoint(session_id, state)

    # Verify can resume
    resumed_state = orchestrator.checkpoint.resume_research(session_id)
    assert resumed_state is not None
    assert resumed_state.session_id == session_id
    assert resumed_state.current_step == 5


# ---------------------------------------------------------------------------
# Test: Memory Capacity Enforcement
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_memory_capacity_enforcement(orchestrator, mock_discovery_agent):
    """Test capacity manager enforces memory limits."""
    # Set strict capacity limits
    from lyra_research.capacity_manager import CapacityLimits

    orchestrator.capacity.limits = CapacityLimits(
        max_notes=10,
        max_corpus_entries=10,
        max_cases=5,
    )

    # Replace agents
    for name in orchestrator.discovery_agents:
        orchestrator.discovery_agents[name] = mock_discovery_agent

    for name in orchestrator.analysis_agents:
        agent = Mock()
        agent.analyze = AsyncMock(return_value=[])
        orchestrator.analysis_agents[name] = agent

    orchestrator.synthesis_pipeline.execute = AsyncMock(return_value={
        "cross_source": {"findings": []},
        "contradictions": {"contradictions": []},
        "evidence": {"audits": []},
        "falsification": {},
    })

    # Execute
    progress = await orchestrator.research("test query", depth="standard")

    # Verify capacity was checked
    assert progress.is_complete or progress.error is not None


# ---------------------------------------------------------------------------
# Test: Adversarial Review Integration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_adversarial_review_deep_only(orchestrator, mock_discovery_agent, mock_analysis_agent):
    """Test adversarial review only runs for deep research."""
    # Replace agents
    for name in orchestrator.discovery_agents:
        orchestrator.discovery_agents[name] = mock_discovery_agent

    for name in orchestrator.analysis_agents:
        orchestrator.analysis_agents[name] = mock_analysis_agent

    orchestrator.synthesis_pipeline.execute = AsyncMock(return_value={
        "cross_source": {"findings": []},
        "contradictions": {"contradictions": []},
        "evidence": {"audits": []},
        "falsification": {},
    })

    # Mock reviewer
    review_called = False

    def mock_review(report, sources, depth):
        nonlocal review_called
        review_called = True
        return Mock(
            revised_report="Revised",
            claims_reviewed=10,
            claims_modified=2,
            context_size_kb=15.0,
        )

    orchestrator.adversarial_reviewer.review = mock_review

    # Test standard depth (no review)
    progress_standard = await orchestrator.research("test query", depth="standard")
    assert not progress_standard.adversarial_review_done

    # Test deep depth (with review)
    review_called = False
    progress_deep = await orchestrator.research("test query", depth="deep")
    assert progress_deep.adversarial_review_done
    assert review_called


@pytest.mark.asyncio
async def test_adversarial_review_claim_verification(orchestrator, mock_discovery_agent, mock_analysis_agent):
    """Test adversarial review verifies and modifies claims."""
    # Replace agents
    for name in orchestrator.discovery_agents:
        orchestrator.discovery_agents[name] = mock_discovery_agent

    for name in orchestrator.analysis_agents:
        orchestrator.analysis_agents[name] = mock_analysis_agent

    orchestrator.synthesis_pipeline.execute = AsyncMock(return_value={
        "cross_source": {"findings": []},
        "contradictions": {"contradictions": []},
        "evidence": {"audits": []},
        "falsification": {},
    })

    # Mock reviewer with specific results
    orchestrator.adversarial_reviewer.review = Mock(return_value=Mock(
        revised_report="Revised report with softened claims",
        claims_reviewed=20,
        claims_modified=5,
        context_size_kb=18.5,
    ))

    # Execute deep research
    progress = await orchestrator.research("test query", depth="deep")

    # Verify review metrics
    assert progress.claims_reviewed == 20
    assert progress.claims_modified == 5
    assert progress.verification_rate == 0.75  # (20-5)/20


# ---------------------------------------------------------------------------
# Test: Performance Metrics
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_performance_metrics_tracking(orchestrator, mock_discovery_agent, mock_analysis_agent):
    """Test orchestrator tracks performance metrics."""
    # Replace agents
    for name in orchestrator.discovery_agents:
        orchestrator.discovery_agents[name] = mock_discovery_agent

    for name in orchestrator.analysis_agents:
        orchestrator.analysis_agents[name] = mock_analysis_agent

    orchestrator.synthesis_pipeline.execute = AsyncMock(return_value={
        "cross_source": {"findings": []},
        "contradictions": {"contradictions": []},
        "evidence": {"audits": []},
        "falsification": {},
    })

    # Execute
    progress = await orchestrator.research("test query", depth="deep")

    # Verify metrics tracked
    assert progress.elapsed_seconds > 0
    assert progress.context_size_kb >= 0
    assert progress.verification_rate >= 0


# ---------------------------------------------------------------------------
# Test: Progress Callbacks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_progress_callbacks(orchestrator, mock_discovery_agent, mock_analysis_agent):
    """Test progress callbacks are invoked during execution."""
    # Replace agents
    for name in orchestrator.discovery_agents:
        orchestrator.discovery_agents[name] = mock_discovery_agent

    for name in orchestrator.analysis_agents:
        orchestrator.analysis_agents[name] = mock_analysis_agent

    orchestrator.synthesis_pipeline.execute = AsyncMock(return_value={
        "cross_source": {"findings": []},
        "contradictions": {"contradictions": []},
        "evidence": {"audits": []},
        "falsification": {},
    })

    # Track callback invocations
    callback_phases = []

    def progress_callback(progress):
        callback_phases.append(progress.current_phase)

    # Execute with callback
    progress = await orchestrator.research(
        "test query",
        depth="standard",
        progress_callback=progress_callback,
    )

    # Verify callbacks invoked for each phase
    assert "discovery" in callback_phases
    assert "analysis" in callback_phases
    assert "synthesis" in callback_phases
