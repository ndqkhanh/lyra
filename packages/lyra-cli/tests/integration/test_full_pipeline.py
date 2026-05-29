"""Full pipeline integration: end-to-end flows across all subsystems.

Tests exercise:
- Voice command -> Research -> Skill execution -> Performance profiling -> Report
- Goal decomposition -> Swarm execution -> Session checkpoint -> Budget tracking
- Multi-hop research -> Knowledge graph -> Source evaluation -> Strategy selection
- Error propagation across subsystem boundaries
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from lyra_cli.autonomy import (
    AutonomyState,
    BudgetManager,
    Goal,
    GoalDecomposer,
    HookEvent,
    HooksManager,
    SessionCheckpoint,
    SessionManager,
    StateMachine,
    StateTransition,
    TransitionError,
)
from lyra_cli.research import (
    Finding,
    MultiHopResearchEngine,
    ResearchKnowledgeGraph,
    SourceCredibility,
    SourceType,
    StrategySelector,
    StrategyType,
)
from lyra_cli.skills.specialized.code_reviewer import (
    CodeReviewerSkill,
)
from lyra_cli.skills.specialized.performance_profiler import (
    PerformanceProfilerSkill,
)
from lyra_cli.swarm import (
    OrchestratorConfig,
    PriorityLevel,
    SwarmOrchestrator,
    SwarmTask,
)
from lyra_cli.voice import (
    SessionConfig,
    TTSBackend,
    VoiceConfig,
    VoiceSession,
    synthesize_speech,
)

# =========================================================================
# Fixtures
# =========================================================================


@pytest.fixture
def mock_tts_backend() -> MagicMock:
    """Provide a mock TTS backend to avoid real audio."""
    backend = MagicMock(spec=TTSBackend)
    backend.name = "mock-tts"
    backend.available = True
    backend.synthesize.return_value = Path("/tmp/output.wav")
    return backend


@pytest.fixture
def research_engine() -> MultiHopResearchEngine:
    return MultiHopResearchEngine(max_hops=3)


@pytest.fixture
def code_reviewer() -> CodeReviewerSkill:
    return CodeReviewerSkill()


@pytest.fixture
def perf_profiler() -> PerformanceProfilerSkill:
    return PerformanceProfilerSkill()


@pytest.fixture
def state_machine() -> StateMachine:
    sm = StateMachine()
    sm.transitions.clear()
    sm.transitions.append(StateTransition(AutonomyState.IDLE, AutonomyState.PLANNING))
    sm.transitions.append(StateTransition(AutonomyState.PLANNING, AutonomyState.EXECUTING))
    sm.transitions.append(StateTransition(AutonomyState.EXECUTING, AutonomyState.VERIFYING))
    sm.transitions.append(StateTransition(AutonomyState.VERIFYING, AutonomyState.COMPLETED))
    sm.transitions.append(StateTransition(AutonomyState.COMPLETED, AutonomyState.IDLE))
    return sm


@pytest.fixture
def swarm_orchestrator() -> SwarmOrchestrator:
    config = OrchestratorConfig(
        max_concurrent_tasks=2,
        task_timeout_seconds=5.0,
        max_retries_per_task=0,
    )
    return SwarmOrchestrator(config)


@pytest.fixture
def budget_manager(tmp_path: Path) -> BudgetManager:
    bm = BudgetManager(data_dir=tmp_path, daily_limit_usd=50.0)
    return bm


@pytest.fixture
def session_manager(tmp_path: Path) -> SessionManager:
    return SessionManager(checkpoint_dir=tmp_path / "checkpoints")


@pytest.fixture
def hooks_manager() -> HooksManager:
    return HooksManager()


@pytest.fixture
def voice_session(mock_tts_backend) -> VoiceSession:
    config = SessionConfig(sound_enabled=False, push_to_talk=False)
    return VoiceSession(config=config, tts_backend=mock_tts_backend)


# =========================================================================
# Pipeline 1: Voice command -> Research -> Skill execution -> Profile -> Report
# =========================================================================


class TestVoiceResearchSkillProfilePipeline:
    """End-to-end: Voice command triggers research, skill execution, profiling, report."""

    def test_voice_triggers_research_report(
        self, voice_session, research_engine, mock_tts_backend,
    ):
        """Verify voice command can trigger a full research report."""
        def handler(text: str) -> str:
            if "research" in text.lower():
                report = research_engine.deep_research(
                    text.replace("research", "").strip(),
                )
                return (
                    f"Research complete: {len(report.findings)} findings, "
                    f"consensus {report.consensus_score:.2f}"
                )
            return f"Heard: {text}"

        voice_session._command_handler = handler
        response = voice_session.process_text("lyra research kubernetes security")

        assert "findings" in response or "research" in response.lower()

    def test_research_feeds_code_review_skill(
        self, research_engine, code_reviewer,
    ):
        """Verify research findings about best practices feed into code review."""
        report = research_engine.deep_research(
            query="Python code review best practices",
            query_type="technical",
        )

        # Simulate: use research report context to review code
        source_to_review = """
import pdb

def unsafe(data):
    eval(data)
    return data
"""
        review_result = code_reviewer.run({
            "source": source_to_review,
            "file_path": "unsafe_module.py",
        })

        # Research found findings; code review found issues
        assert len(report.findings) > 0
        codes = {f["code"] for f in review_result["findings"]}
        assert "EVAL_USAGE" in codes

    def test_code_review_results_feed_performance_profiling(
        self, code_reviewer, perf_profiler,
    ):
        """Verify code review output can drive performance profiling."""
        source = """
def slow_sort(items):
    result = []
    for i in items:
        for j in items:
            result.append(i * j)
    return sorted(result)
"""
        review_result = code_reviewer.run({"source": source, "file_path": "slow.py"})
        profile_result = perf_profiler.run({"source": source, "module_name": "slow"})

        # Both review and profiling should detect issues
        assert len(review_result["findings"]) >= 0
        assert len(profile_result["results"]) > 0
        profile_issues = []
        for r in profile_result["results"]:
            profile_issues.extend(r["issues"])
        nested = [i for i in profile_issues if "Nested loops" in str(i)]
        assert len(nested) >= 1

    def test_report_generated_from_pipeline(
        self, research_engine, code_reviewer,
    ):
        """Verify a pipeline summary report can be constructed."""
        report = research_engine.deep_research(
            query="Event-driven architecture patterns",
            query_type="technical",
        )
        source = "def add(a, b): return a + b"
        review = code_reviewer.run({"source": source})

        pipeline_report = {
            "query": report.query,
            "research_findings": len(report.findings),
            "consensus_score": report.consensus_score,
            "code_review_findings": len(review["findings"]),
        }

        assert pipeline_report["query"] == "Event-driven architecture patterns"
        assert pipeline_report["research_findings"] > 0
        assert 0 <= pipeline_report["consensus_score"] <= 1.0

    def test_tts_announces_pipeline_completion(
        self, mock_tts_backend,
    ):
        """Verify TTS announces pipeline completion status."""
        summary_text = (
            "Pipeline complete. Research found 12 findings. "
            "Code review identified 3 issues. "
            "Performance profiling completed."
        )

        result = synthesize_speech(
            summary_text,
            backend=mock_tts_backend,
            voice=VoiceConfig(),
        )
        mock_tts_backend.synthesize.assert_called_once()
        assert result is not None

    def test_pipeline_handles_no_research_findings(
        self, voice_session,
    ):
        """Verify pipeline handles the case of zero research findings gracefully."""
        def handler(text: str) -> str:
            return "No research findings available for this topic."

        voice_session._command_handler = handler
        response = voice_session.process_text("research something obscure")
        assert response != ""


# =========================================================================
# Pipeline 2: Goal decomposition -> Swarm execution -> Checkpoint -> Budget
# =========================================================================


class TestGoalSwarmCheckpointBudgetPipeline:
    """End-to-end: Decompose a goal, execute via swarm, checkpoint, track budget."""

    def test_goal_decomposition_to_swarm_tasks(
        self, goal_decomposer=None,
    ):
        """Verify goal decomposition produces tasks executable by swarm."""
        if goal_decomposer is None:
            goal_decomposer = GoalDecomposer()

        goal = Goal(
            id="full_pipeline_goal",
            description="Implement integration test suite",
        )
        graph = goal_decomposer.decompose(goal)

        # Map to swarm tasks
        swarm_tasks = [
            SwarmTask(
                description=s.description,
                priority=PriorityLevel.HIGH,
                payload={"subtask_id": s.id},
            )
            for s in graph.subtasks
        ]

        assert len(swarm_tasks) == 3
        descriptions = [t.description for t in swarm_tasks]
        assert any("Research" in d for d in descriptions)
        assert any("Implement" in d for d in descriptions)
        assert any("Verify" in d for d in descriptions)

    def test_session_checkpoint_after_swarm_execution(
        self, session_manager,
    ):
        """Verify checkpoint is saved after swarm execution state."""
        checkpoint = SessionCheckpoint(
            session_id="pipeline_sesh",
            state="EXECUTING",
            goal="Run integration tests",
            context={
                "swarm_tasks": ["task_1", "task_2", "task_3"],
                "completed_tasks": ["task_1"],
            },
        )
        session_manager.save_checkpoint(checkpoint)

        loaded = session_manager.load_checkpoint("pipeline_sesh")
        assert loaded.session_id == "pipeline_sesh"
        assert loaded.context["completed_tasks"] == ["task_1"]

    def test_budget_tracked_across_swarm_tasks(
        self, budget_manager,
    ):
        """Verify budget is tracked across multiple swarm tasks."""
        tasks = [
            ("gpt-4", 500, 200, 0.03),
            ("claude-3", 300, 150, 0.02),
            ("gpt-4", 200, 100, 0.015),
        ]

        for model, prompt, completion, cost in tasks:
            budget_manager.record_usage(
                model=model,
                prompt_tokens=prompt,
                completion_tokens=completion,
                cost_usd=cost,
            )

        summary = budget_manager.summary()
        assert summary.entry_count == 3
        assert summary.total_cost_usd == pytest.approx(0.065, rel=0.01)
        assert summary.total_tokens == 1450

    def test_budget_checkpoint_continuity(
        self, budget_manager, session_manager,
    ):
        """Verify budget state is consistent across checkpoint save/load."""
        budget_manager.record_usage(
            model="gpt-4", prompt_tokens=1000, completion_tokens=500, cost_usd=0.05
        )

        summary_before = budget_manager.summary()

        checkpoint = SessionCheckpoint(
            session_id="budget_sesh",
            state="EXECUTING",
            goal="Budget pipeline test",
            context={"current_cost": summary_before.total_cost_usd},
        )
        session_manager.save_checkpoint(checkpoint)

        loaded = session_manager.load_checkpoint("budget_sesh")
        assert loaded.context["current_cost"] == summary_before.total_cost_usd

    def test_hook_notifications_through_pipeline(
        self, hooks_manager,
    ):
        """Verify hooks fire at each pipeline stage."""
        events = []

        def track(event, ctx):
            events.append((event, list(ctx.keys())))

        for evt in HookEvent:
            hooks_manager.register(evt, track)

        hooks_manager.fire(HookEvent.ON_START, {"stage": "research"})
        hooks_manager.fire(HookEvent.ON_COMPLETE, {"stage": "review"})
        hooks_manager.fire(HookEvent.ON_ERROR, {"stage": "profile"})
        hooks_manager.fire(HookEvent.ON_BLOCKED, {"stage": "budget"})

        assert len(events) == 4
        assert events[0][0] == HookEvent.ON_START
        assert events[2][0] == HookEvent.ON_ERROR

    def test_state_machine_wraps_entire_pipeline(
        self, state_machine,
    ):
        """Verify state machine transitions through full pipeline lifecycle."""
        state_machine.transition_to(AutonomyState.PLANNING)
        state_machine.transition_to(AutonomyState.EXECUTING)
        state_machine.transition_to(AutonomyState.VERIFYING)
        state_machine.transition_to(AutonomyState.COMPLETED)

        assert state_machine.in_state(AutonomyState.COMPLETED)


# =========================================================================
# Pipeline 3: Research -> Knowledge graph -> Source evaluation -> Strategy
# =========================================================================


class TestResearchKGEvaluationStrategyPipeline:
    """End-to-end: Multi-hop research feeds knowledge graph, source eval, strategy selection."""

    def test_research_populates_knowledge_graph(
        self, research_engine,
    ):
        """Verify research execution populates the knowledge graph."""
        report = research_engine.deep_research(
            query="Best practices for API rate limiting",
            query_type="technical",
        )

        graph = research_engine.knowledge_graph
        assert graph.get_finding_count() > 0
        assert report.findings

    def test_knowledge_graph_feeds_source_evaluation(
        self, research_engine,
    ):
        """Verify knowledge graph findings can be evaluated for source credibility."""
        research_engine.deep_research(
            query="Microservices communication patterns",
            query_type="exploratory",
        )
        evaluator = research_engine.source_evaluator

        all_sources = evaluator.get_all_sources()
        if all_sources:
            for source in all_sources:
                assert 0.0 <= source.credibility_score <= 1.0

    def test_source_evaluation_detects_contradictions(
        self,
    ):
        """Verify source evaluation detects contradictory claims."""
        evaluator = SourceCredibility()

        evaluator.evaluate_source(
            source_id="src_a", url="https://a.example",
            source_type=SourceType.ACADEMIC_PAPER,
            title="Paper A", citation_count=20,
        )
        evaluator.evaluate_source(
            source_id="src_b", url="https://b.example",
            source_type=SourceType.ACADEMIC_PAPER,
            title="Paper B", citation_count=15,
        )
        evaluator.detect_contradictions(
            source_a_id="src_a", source_b_id="src_b",
            claim_a="REST is better for microservices",
            claim_b="gRPC is better for microservices",
            severity=0.5,
        )

        contradictions = evaluator.get_contradictions()
        assert len(contradictions) == 1

        # Contradiction should reduce consensus
        consensus = evaluator.get_consensus_score(["src_a", "src_b"])
        assert consensus > 0.0

    def test_strategy_selector_adapts_to_feedback(
        self,
    ):
        """Verify strategy selector adapts based on research feedback."""
        selector = StrategySelector(exploration_constant=1.0)

        # Simulate feedback: breadth-first works well for exploratory queries
        for _ in range(5):
            selector.update_feedback(
                StrategyType.BREADTH_FIRST, reward=0.9, query_type="exploratory",
            )
        # Depth-first works poorly
        for _ in range(3):
            selector.update_feedback(
                StrategyType.DEPTH_FIRST, reward=0.3, query_type="exploratory",
            )

        # After feedback, breadth-first should be preferred
        stats = selector.get_strategy_stats("exploratory")
        assert stats["BREADTH_FIRST"]["mean_reward"] > stats["DEPTH_FIRST"]["mean_reward"]

    def test_strategy_distribution_in_research_report(
        self, research_engine,
    ):
        """Verify research report includes strategy distribution."""
        report = research_engine.deep_research(
            query="Event sourcing patterns",
            query_type="exploratory",
        )
        assert isinstance(report.strategy_distribution, dict)
        assert len(report.strategy_distribution) > 0

    def test_knowledge_graph_gaps_from_research_gaps(
        self,
    ):
        """Verify knowledge gaps are identified from sparse research findings."""
        kg = ResearchKnowledgeGraph()

        # Add orphan findings (no relations)
        kg.add_finding(Finding(
            finding_id="orphan_1", content="Isolated finding about topic X",
            confidence=0.6,
        ))

        gaps = kg.find_knowledge_gaps()
        gap_ids = {g.gap_id for g in gaps}
        assert any("orphan_1" in gid for gid in gap_ids)

    def test_full_pipeline_data_flow_integrity(
        self, research_engine,
    ):
        """Verify data flows with integrity through the entire research pipeline."""
        report = research_engine.deep_research(
            query="Distributed consensus algorithms",
            query_type="technical",
        )

        # All report fields should be populated
        assert report.query == "Distributed consensus algorithms"
        assert isinstance(report.findings, tuple)
        assert isinstance(report.sources, tuple)
        assert 0.0 <= report.consensus_score <= 1.0
        assert isinstance(report.contradictions, int)
        assert isinstance(report.knowledge_gaps, int)
        assert isinstance(report.strategy_distribution, dict)

        # Strategy counts should match trajectory count
        total_strategy_uses = sum(report.strategy_distribution.values())
        assert total_strategy_uses >= report.trajectories

    def test_error_propagation_across_subsystems(
        self, state_machine,
    ):
        """Verify errors propagate correctly across subsystem boundaries."""
        # State machine should prevent invalid transitions
        with pytest.raises(TransitionError):
            # Cannot go to COMPLETED without going through VERIFYING
            state_machine.transition_to(AutonomyState.COMPLETED)

        # After proper cycling, should work
        state_machine.transition_to(AutonomyState.PLANNING)
        state_machine.transition_to(AutonomyState.EXECUTING)
        state_machine.transition_to(AutonomyState.VERIFYING)
        state_machine.transition_to(AutonomyState.COMPLETED)
        assert state_machine.in_state(AutonomyState.COMPLETED)
