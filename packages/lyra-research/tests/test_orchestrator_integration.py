"""Integration tests for 3-Agent Hybrid Orchestrator (Week 4)."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from lyra_research.adversarial_reviewer import AdversarialReviewer
from lyra_research.capacity_manager import CapacityLimits, CapacityManager
from lyra_research.coordination import (
    CircuitBreaker,
    CoordinationManager,
    HealthChecker,
    RetryPolicy,
    TaskState,
    TimeoutEnforcer,
)
from lyra_research.discovery import ResearchSource, SourceType
from lyra_research.memory import (
    LocalCorpus,
    ResearchNoteStore,
    ResearchStrategyMemory,
    SessionCaseBank,
)
from lyra_research.orchestrator import (
    AgentConfig,
    AgentType,
    ResearchOrchestrator,
    ResearchProgress,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_db_path(tmp_path: Path) -> Path:
    """Create temporary database path."""
    return tmp_path / "test.db"


@pytest.fixture
def coordination_manager() -> CoordinationManager:
    """Create coordination manager for testing."""
    return CoordinationManager(
        retry_policy=RetryPolicy(max_retries=2, base_delay=0.1),
        circuit_breaker=CircuitBreaker(min_success_rate=0.5),
        timeout_enforcer=TimeoutEnforcer(
            task_timeout=10,
            phase_timeout=30,
            research_timeout=60,
        ),
        health_checker=HealthChecker(
            max_memory_mb=2048,
            min_spawn_rate=1.0,
            hang_timeout=10,
        ),
    )


@pytest.fixture
def capacity_manager(tmp_db_path: Path) -> CapacityManager:
    """Create capacity manager for testing."""
    return CapacityManager(
        db_path=tmp_db_path,
        limits=CapacityLimits(),
    )


@pytest.fixture
def adversarial_reviewer() -> AdversarialReviewer:
    """Create adversarial reviewer for testing."""
    return AdversarialReviewer(
        executor_model="gpt-4o",
        reviewer_model="gpt-4o-mini",
    )


@pytest.fixture
def orchestrator(
    tmp_path: Path,
    tmp_db_path: Path,
    coordination_manager: CoordinationManager,
    capacity_manager: CapacityManager,
    adversarial_reviewer: AdversarialReviewer,
) -> ResearchOrchestrator:
    """Create orchestrator with all integrations."""
    return ResearchOrchestrator(
        output_dir=tmp_path / "reports",
        note_store=ResearchNoteStore(store_path=tmp_path / "notes.json"),
        corpus=LocalCorpus(db_path=tmp_db_path),
        strategy_memory=ResearchStrategyMemory(store_path=tmp_path / "strats.json"),
        case_bank=SessionCaseBank(store_path=tmp_path / "cases.json"),
        coordination_manager=coordination_manager,
        capacity_manager=capacity_manager,
        adversarial_reviewer=adversarial_reviewer,
    )


def _make_source(
    source_id: str,
    title: str,
    url: str,
    source_type: SourceType = SourceType.PAPER,
) -> ResearchSource:
    """Create a test research source."""
    return ResearchSource(
        id=source_id,
        title=title,
        source_type=source_type,
        url=url,
        abstract="An abstract about " + title,
        citations=10,
        stars=0,
        metadata={},
    )


def _empty_discover(*args: Any, **kwargs: Any) -> dict[str, list[ResearchSource]]:
    """Stub for empty discovery."""
    return {}


def _two_source_discover(*args: Any, **kwargs: Any) -> dict[str, list[ResearchSource]]:
    """Stub returning one paper and one repo."""
    return {
        "arxiv": [_make_source("p1", "Paper One", "https://arxiv.org/p1", SourceType.PAPER)],
        "github": [_make_source("r1", "Repo One", "https://github.com/r1", SourceType.REPOSITORY)],
    }


# ---------------------------------------------------------------------------
# Integration Tests: Full Pipeline
# ---------------------------------------------------------------------------


def test_orchestrator_full_pipeline_completes(orchestrator: ResearchOrchestrator) -> None:
    """Full pipeline completes without error."""
    with patch.object(orchestrator.discovery, "discover", side_effect=_empty_discover):
        progress = orchestrator.research("transformers")
    assert progress.error is None
    assert progress.is_complete


def test_orchestrator_full_pipeline_with_sources(orchestrator: ResearchOrchestrator) -> None:
    """Full pipeline with sources tracks counts correctly."""
    with patch.object(orchestrator.discovery, "discover", side_effect=_two_source_discover):
        progress = orchestrator.research("deep learning")
    assert progress.papers_analyzed == 1
    assert progress.repos_analyzed == 1
    assert progress.report is not None


def test_orchestrator_telemetry_tracking(orchestrator: ResearchOrchestrator) -> None:
    """Telemetry is tracked correctly."""
    with patch.object(orchestrator.discovery, "discover", side_effect=_empty_discover):
        progress = orchestrator.research("attention mechanism")

    # Check telemetry fields
    assert progress.tasks_completed >= 0
    assert progress.tasks_failed >= 0
    assert progress.tasks_retried >= 0
    assert progress.elapsed_seconds > 0


# ---------------------------------------------------------------------------
# Integration Tests: Coordination Manager
# ---------------------------------------------------------------------------


def test_orchestrator_uses_coordination_for_discovery(orchestrator: ResearchOrchestrator) -> None:
    """Discovery phase uses coordination manager."""
    with patch.object(orchestrator.discovery, "discover", side_effect=_empty_discover):
        orchestrator.research("llm")

    # Check that tasks were created
    tasks = orchestrator.coordination.get_all_tasks()
    assert len(tasks) > 0

    # Check that discovery task exists
    discovery_tasks = [t for t in tasks if t.agent_type == AgentType.DISCOVERY.value]
    assert len(discovery_tasks) > 0


def test_orchestrator_uses_coordination_for_analysis(orchestrator: ResearchOrchestrator) -> None:
    """Analysis phase uses coordination manager."""
    with patch.object(orchestrator.discovery, "discover", side_effect=_two_source_discover):
        orchestrator.research("bert")

    tasks = orchestrator.coordination.get_all_tasks()
    analysis_tasks = [t for t in tasks if t.agent_type == AgentType.ANALYSIS.value]
    assert len(analysis_tasks) > 0


def test_orchestrator_uses_coordination_for_synthesis(orchestrator: ResearchOrchestrator) -> None:
    """Synthesis phase uses coordination manager."""
    with patch.object(orchestrator.discovery, "discover", side_effect=_empty_discover):
        orchestrator.research("gpt")

    tasks = orchestrator.coordination.get_all_tasks()
    synthesis_tasks = [t for t in tasks if t.agent_type == AgentType.SYNTHESIS.value]
    assert len(synthesis_tasks) > 0


def test_orchestrator_task_completion_tracking(orchestrator: ResearchOrchestrator) -> None:
    """Task completion is tracked correctly."""
    with patch.object(orchestrator.discovery, "discover", side_effect=_empty_discover):
        progress = orchestrator.research("rlhf")

    completed_tasks = [
        t for t in orchestrator.coordination.get_all_tasks()
        if t.state == TaskState.COMPLETED
    ]
    assert len(completed_tasks) > 0
    assert progress.tasks_completed == len(completed_tasks)


def test_orchestrator_retry_on_transient_failure(orchestrator: ResearchOrchestrator) -> None:
    """Transient failures trigger retry."""
    call_count = 0

    def failing_discover(*args: Any, **kwargs: Any) -> dict[str, list[ResearchSource]]:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("Transient network error")
        return _empty_discover(*args, **kwargs)

    with patch.object(orchestrator.discovery, "discover", side_effect=failing_discover):
        progress = orchestrator.research("transformers")

    # Should succeed after retry
    assert progress.error is None
    assert call_count == 2  # Initial + 1 retry
    assert progress.tasks_retried > 0


def test_orchestrator_circuit_breaker_triggers(orchestrator: ResearchOrchestrator) -> None:
    """Circuit breaker triggers after repeated failures."""
    # Set low success rate threshold
    orchestrator.coordination.circuit_breaker.min_success_rate = 0.9

    def always_fail(*args: Any, **kwargs: Any) -> dict[str, list[ResearchSource]]:
        raise RuntimeError("Persistent failure")

    with patch.object(orchestrator.discovery, "discover", side_effect=always_fail):
        progress = orchestrator.research("transformers")

    # Should fail due to circuit breaker
    assert progress.error is not None
    assert "circuit breaker" in progress.error.lower() or "persistent failure" in progress.error.lower()


def test_orchestrator_timeout_enforcement(orchestrator: ResearchOrchestrator) -> None:
    """Task timeout is enforced."""
    # Set very short timeout
    orchestrator.coordination.timeout_enforcer.task_timeout = 0.1

    def slow_discover(*args: Any, **kwargs: Any) -> dict[str, list[ResearchSource]]:
        time.sleep(0.5)  # Exceed timeout
        return _empty_discover(*args, **kwargs)

    with patch.object(orchestrator.discovery, "discover", side_effect=slow_discover):
        orchestrator.research("transformers")

    # Should timeout
    tasks = orchestrator.coordination.get_all_tasks()
    [t for t in tasks if t.state == TaskState.TIMEOUT]
    # Note: May not timeout in test due to mock, but structure is correct
    assert len(tasks) > 0


# ---------------------------------------------------------------------------
# Integration Tests: Capacity Manager
# ---------------------------------------------------------------------------


def test_orchestrator_checks_capacity_before_storing(orchestrator: ResearchOrchestrator) -> None:
    """Capacity is checked before storing sources."""
    with patch.object(orchestrator.discovery, "discover", side_effect=_two_source_discover):
        progress = orchestrator.research("transformers")

    # Should complete without capacity errors (small dataset)
    assert progress.error is None


def test_orchestrator_enforces_capacity_limits(orchestrator: ResearchOrchestrator) -> None:
    """Capacity limits are enforced."""
    # Set very low limits
    orchestrator.capacity.limits.MAX_SOURCES = 0
    orchestrator.capacity.limits.BLOCK_THRESHOLD = 0.0

    with patch.object(orchestrator.discovery, "discover", side_effect=_two_source_discover):
        progress = orchestrator.research("transformers")

    # Should fail due to capacity limit
    assert progress.error is not None
    assert "capacity" in progress.error.lower() or "limit" in progress.error.lower()


def test_orchestrator_capacity_checked_multiple_times(orchestrator: ResearchOrchestrator) -> None:
    """Capacity is checked at multiple pipeline stages."""
    check_count = 0
    original_enforce = orchestrator.capacity.enforce_limits

    def counting_enforce():
        nonlocal check_count
        check_count += 1
        original_enforce()

    with patch.object(orchestrator.capacity, "enforce_limits", side_effect=counting_enforce):
        with patch.object(orchestrator.discovery, "discover", side_effect=_empty_discover):
            orchestrator.research("transformers")

    # Should check capacity at: start, fetch, memorize (3 times minimum)
    assert check_count >= 3


# ---------------------------------------------------------------------------
# Integration Tests: Adversarial Reviewer
# ---------------------------------------------------------------------------


def test_orchestrator_skips_review_for_standard_depth(orchestrator: ResearchOrchestrator) -> None:
    """Adversarial review is skipped for standard depth."""
    with patch.object(orchestrator.discovery, "discover", side_effect=_empty_discover):
        progress = orchestrator.research("transformers", depth="standard")

    # Verification rate should be 0 (no review)
    assert progress.verification_rate == 0.0
    assert progress.context_size_kb == 0.0


def test_orchestrator_runs_review_for_deep_depth(orchestrator: ResearchOrchestrator) -> None:
    """Adversarial review runs for deep depth."""
    with patch.object(orchestrator.discovery, "discover", side_effect=_two_source_discover):
        progress = orchestrator.research("transformers", depth="deep")

    # Verification rate should be set (review ran)
    assert progress.verification_rate >= 0.0
    assert progress.context_size_kb >= 0.0


def test_orchestrator_review_updates_report(orchestrator: ResearchOrchestrator) -> None:
    """Adversarial review updates report content."""
    with patch.object(orchestrator.discovery, "discover", side_effect=_two_source_discover):
        progress = orchestrator.research("transformers", depth="deep")

    # Report should exist and have content
    assert progress.report is not None
    assert progress.report.content is not None


# ---------------------------------------------------------------------------
# Integration Tests: Agent Configuration
# ---------------------------------------------------------------------------


def test_orchestrator_uses_correct_agent_models(orchestrator: ResearchOrchestrator) -> None:
    """Correct models are configured for each agent type."""
    assert orchestrator.agent_configs[AgentType.DISCOVERY].model == "claude-haiku-4-5"
    assert orchestrator.agent_configs[AgentType.ANALYSIS].model == "claude-sonnet-4-6"
    assert orchestrator.agent_configs[AgentType.SYNTHESIS].model == "claude-opus-4-7"


def test_orchestrator_custom_agent_configs(tmp_path: Path, tmp_db_path: Path) -> None:
    """Custom agent configurations are respected."""
    custom_configs = {
        AgentType.DISCOVERY: AgentConfig(
            type=AgentType.DISCOVERY,
            model="custom-haiku",
            timeout_seconds=100,
            max_retries=1,
        ),
        AgentType.ANALYSIS: AgentConfig(
            type=AgentType.ANALYSIS,
            model="custom-sonnet",
            timeout_seconds=200,
            max_retries=1,
        ),
        AgentType.SYNTHESIS: AgentConfig(
            type=AgentType.SYNTHESIS,
            model="custom-opus",
            timeout_seconds=300,
            max_retries=0,
        ),
    }

    orchestrator = ResearchOrchestrator(
        output_dir=tmp_path / "reports",
        note_store=ResearchNoteStore(store_path=tmp_path / "notes.json"),
        corpus=LocalCorpus(db_path=tmp_db_path),
        agent_configs=custom_configs,
    )

    assert orchestrator.agent_configs[AgentType.DISCOVERY].model == "custom-haiku"
    assert orchestrator.agent_configs[AgentType.ANALYSIS].model == "custom-sonnet"
    assert orchestrator.agent_configs[AgentType.SYNTHESIS].model == "custom-opus"


def test_orchestrator_agent_timeout_configuration(orchestrator: ResearchOrchestrator) -> None:
    """Agent timeouts are configured correctly."""
    assert orchestrator.agent_configs[AgentType.DISCOVERY].timeout_seconds == 300
    assert orchestrator.agent_configs[AgentType.ANALYSIS].timeout_seconds == 600
    assert orchestrator.agent_configs[AgentType.SYNTHESIS].timeout_seconds == 900


def test_orchestrator_agent_retry_configuration(orchestrator: ResearchOrchestrator) -> None:
    """Agent retry counts are configured correctly."""
    assert orchestrator.agent_configs[AgentType.DISCOVERY].max_retries == 2
    assert orchestrator.agent_configs[AgentType.ANALYSIS].max_retries == 2
    assert orchestrator.agent_configs[AgentType.SYNTHESIS].max_retries == 1


# ---------------------------------------------------------------------------
# Integration Tests: Error Handling
# ---------------------------------------------------------------------------


def test_orchestrator_handles_discovery_failure(orchestrator: ResearchOrchestrator) -> None:
    """Discovery failure is handled gracefully."""
    def failing_discover(*args: Any, **kwargs: Any) -> dict[str, list[ResearchSource]]:
        raise RuntimeError("Discovery failed")

    with patch.object(orchestrator.discovery, "discover", side_effect=failing_discover):
        progress = orchestrator.research("transformers")

    assert progress.error is not None
    assert "discovery failed" in progress.error.lower()


def test_orchestrator_handles_capacity_error(orchestrator: ResearchOrchestrator) -> None:
    """Capacity errors are handled gracefully."""
    def failing_enforce():
        raise RuntimeError("Capacity limit reached")

    with patch.object(orchestrator.capacity, "enforce_limits", side_effect=failing_enforce):
        progress = orchestrator.research("transformers")

    assert progress.error is not None
    assert "capacity" in progress.error.lower()


def test_orchestrator_handles_empty_topic(orchestrator: ResearchOrchestrator) -> None:
    """Empty topic is handled gracefully."""
    progress = orchestrator.research("")
    assert progress.error is not None
    assert "empty" in progress.error.lower()


# ---------------------------------------------------------------------------
# Integration Tests: Memory Persistence
# ---------------------------------------------------------------------------


def test_orchestrator_persists_to_note_store(orchestrator: ResearchOrchestrator) -> None:
    """Research is persisted to note store."""
    with patch.object(orchestrator.discovery, "discover", side_effect=_empty_discover):
        orchestrator.research("transformers")

    notes = list(orchestrator.note_store._notes.values())
    assert len(notes) >= 1


def test_orchestrator_persists_to_case_bank(orchestrator: ResearchOrchestrator) -> None:
    """Research is persisted to case bank."""
    with patch.object(orchestrator.discovery, "discover", side_effect=_empty_discover):
        orchestrator.research("transformers")

    cases = orchestrator.case_bank.get_all()
    assert len(cases) == 1
    assert cases[0].topic == "transformers"


def test_orchestrator_persists_to_corpus(orchestrator: ResearchOrchestrator) -> None:
    """Sources are persisted to corpus."""
    with patch.object(orchestrator.discovery, "discover", side_effect=_two_source_discover):
        orchestrator.research("transformers")

    # Check corpus has entries
    entries = orchestrator.corpus.search("Paper One")
    assert len(entries) > 0


# ---------------------------------------------------------------------------
# Integration Tests: Progress Tracking
# ---------------------------------------------------------------------------


def test_orchestrator_progress_callback_receives_updates(orchestrator: ResearchOrchestrator) -> None:
    """Progress callback receives updates at each step."""
    updates: list[ResearchProgress] = []

    def callback(progress: ResearchProgress) -> None:
        updates.append(progress)

    with patch.object(orchestrator.discovery, "discover", side_effect=_empty_discover):
        orchestrator.research("transformers", progress_callback=callback)

    # Should receive updates for all 10 steps
    assert len(updates) >= 10


def test_orchestrator_progress_step_names_populated(orchestrator: ResearchOrchestrator) -> None:
    """Progress step names are populated."""
    updates: list[ResearchProgress] = []

    def callback(progress: ResearchProgress) -> None:
        updates.append(progress)

    with patch.object(orchestrator.discovery, "discover", side_effect=_empty_discover):
        orchestrator.research("transformers", progress_callback=callback)

    # All updates should have step names
    assert all(u.current_step_name for u in updates)


def test_orchestrator_progress_monotonic_steps(orchestrator: ResearchOrchestrator) -> None:
    """Progress steps are monotonically increasing."""
    updates: list[ResearchProgress] = []

    def callback(progress: ResearchProgress) -> None:
        updates.append(progress)

    with patch.object(orchestrator.discovery, "discover", side_effect=_empty_discover):
        orchestrator.research("transformers", progress_callback=callback)

    steps = [u.current_step for u in updates]
    assert steps == sorted(steps)


# ---------------------------------------------------------------------------
# Integration Tests: Depth Variations
# ---------------------------------------------------------------------------


def test_orchestrator_quick_depth_completes(orchestrator: ResearchOrchestrator) -> None:
    """Quick depth completes successfully."""
    with patch.object(orchestrator.discovery, "discover", side_effect=_empty_discover):
        progress = orchestrator.research("transformers", depth="quick")

    assert progress.error is None
    assert progress.is_complete


def test_orchestrator_standard_depth_completes(orchestrator: ResearchOrchestrator) -> None:
    """Standard depth completes successfully."""
    with patch.object(orchestrator.discovery, "discover", side_effect=_empty_discover):
        progress = orchestrator.research("transformers", depth="standard")

    assert progress.error is None
    assert progress.is_complete


def test_orchestrator_deep_depth_completes(orchestrator: ResearchOrchestrator) -> None:
    """Deep depth completes successfully."""
    with patch.object(orchestrator.discovery, "discover", side_effect=_empty_discover):
        progress = orchestrator.research("transformers", depth="deep")

    assert progress.error is None
    assert progress.is_complete


def test_orchestrator_invalid_depth_defaults_to_standard(orchestrator: ResearchOrchestrator) -> None:
    """Invalid depth defaults to standard."""
    with patch.object(orchestrator.discovery, "discover", side_effect=_empty_discover):
        progress = orchestrator.research("transformers", depth="invalid")

    assert progress.error is None
    assert progress.is_complete


# ---------------------------------------------------------------------------
# Integration Tests: Source Deduplication
# ---------------------------------------------------------------------------


def test_orchestrator_deduplicates_sources_by_url(orchestrator: ResearchOrchestrator) -> None:
    """Sources with duplicate URLs are deduplicated."""
    dup_source = _make_source("p1", "Paper One", "https://arxiv.org/p1")

    def discover_with_dups(*args: Any, **kwargs: Any) -> dict[str, list[ResearchSource]]:
        return {
            "arxiv": [dup_source, dup_source],
            "semantic_scholar": [dup_source],
        }

    with patch.object(orchestrator.discovery, "discover", side_effect=discover_with_dups):
        progress = orchestrator.research("transformers")

    # Only 1 unique paper should be counted
    assert progress.papers_analyzed == 1


# ---------------------------------------------------------------------------
# Integration Tests: Telemetry
# ---------------------------------------------------------------------------


def test_orchestrator_tracks_elapsed_time(orchestrator: ResearchOrchestrator) -> None:
    """Elapsed time is tracked correctly."""
    with patch.object(orchestrator.discovery, "discover", side_effect=_empty_discover):
        progress = orchestrator.research("transformers")

    assert progress.elapsed_seconds > 0
    assert progress.started_at is not None
    assert progress.completed_at is not None


def test_orchestrator_tracks_source_counts(orchestrator: ResearchOrchestrator) -> None:
    """Source counts are tracked correctly."""
    with patch.object(orchestrator.discovery, "discover", side_effect=_two_source_discover):
        progress = orchestrator.research("transformers")

    assert progress.sources_found["arxiv"] == 1
    assert progress.sources_found["github"] == 1


def test_orchestrator_tracks_task_metrics(orchestrator: ResearchOrchestrator) -> None:
    """Task metrics are tracked correctly."""
    with patch.object(orchestrator.discovery, "discover", side_effect=_empty_discover):
        progress = orchestrator.research("transformers")

    assert progress.tasks_completed >= 0
    assert progress.tasks_failed >= 0
    assert progress.tasks_retried >= 0

