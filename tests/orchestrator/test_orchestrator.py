"""Tests for the OrchestratorAgent module."""

import asyncio
from unittest.mock import patch

import pytest

from lyra.orchestrator.artifact import Artifact
from lyra.orchestrator.orchestrator import (
    EffortLevel,
    OrchestrationResult,
    OrchestratorAgent,
    SubTask,
    determine_effort_level,
    worker_count_for_effort,
)


class TestEffortDetection:
    """Tests for effort-level heuristics."""

    def test_simple_short_question(self) -> None:
        """Test short factoid question is SIMPLE."""
        assert determine_effort_level("What is the capital of France?") == EffortLevel.SIMPLE

    def test_comparison_question(self) -> None:
        """Test comparative question is COMPARISON."""
        q = "What is the difference between Python and JavaScript?"
        assert determine_effort_level(q) == EffortLevel.COMPARISON

    def test_complex_long_question(self) -> None:
        """Test long question with analysis keywords is COMPLEX."""
        q = "Compare and contrast the economic, social, and environmental impacts of renewable energy adoption across developed and developing nations over the past two decades."
        assert determine_effort_level(q) == EffortLevel.COMPLEX

    def test_complex_with_analyze_keyword(self) -> None:
        """Test question with 'analyze' keyword is COMPLEX."""
        q = "Analyze the impact of AI on healthcare."
        assert determine_effort_level(q) == EffortLevel.COMPLEX

    def test_complex_research_keyword(self) -> None:
        """Test question with 'research' keyword is COMPLEX."""
        q = "Research the long-term economic implications of universal basic income on labor markets and social welfare systems."
        assert determine_effort_level(q) == EffortLevel.COMPLEX

    def test_comparison_versus_keyword(self) -> None:
        """Test question with 'versus' is COMPARISON."""
        q = "React versus Angular for web development."
        assert determine_effort_level(q) == EffortLevel.COMPARISON

    def test_comparison_recommend(self) -> None:
        """Test question with 'recommend' is COMPARISON."""
        q = "Which cloud provider do you recommend?"
        assert determine_effort_level(q) == EffortLevel.COMPARISON


class TestWorkerCount:
    """Tests for worker count mapping."""

    def test_simple_worker_count(self) -> None:
        """Test SIMPLE effort uses 1 worker."""
        assert worker_count_for_effort(EffortLevel.SIMPLE) == 1

    def test_comparison_worker_count(self) -> None:
        """Test COMPARISON effort uses 3 workers."""
        assert worker_count_for_effort(EffortLevel.COMPARISON) == 3

    def test_complex_worker_count(self) -> None:
        """Test COMPLEX effort uses 10 workers."""
        assert worker_count_for_effort(EffortLevel.COMPLEX) == 10


class TestSubTask:
    """Tests for SubTask dataclass."""

    def test_create_sub_task(self) -> None:
        """Test creating a sub-task."""
        st = SubTask(subtask_id="st_1", description="Research topic X")
        assert st.subtask_id == "st_1"
        assert st.description == "Research topic X"
        assert st.perspective == ""
        assert st.dependencies == []

    def test_sub_task_with_perspective(self) -> None:
        """Test sub-task with perspective."""
        st = SubTask(subtask_id="st_2", description="test", perspective="technical")
        assert st.perspective == "technical"


class TestOrchestratorDecompose:
    """Tests for query decomposition."""

    def test_simple_decomposition(self) -> None:
        """Test simple query decomposes to 1 sub-task."""
        orch = OrchestratorAgent()
        tasks = orch.decompose_query("What is the capital of France?")
        assert len(tasks) == 1
        assert tasks[0].subtask_id == "st_1"
        assert tasks[0].perspective == "general"

    def test_comparison_decomposition(self) -> None:
        """Test comparison query decomposes to 3 sub-tasks."""
        orch = OrchestratorAgent()
        tasks = orch.decompose_query("Compare Python and JavaScript.")
        assert len(tasks) == 3
        assert tasks[0].perspective == "background"
        assert tasks[1].perspective == "analysis"
        assert tasks[2].perspective == "synthesis"

    def test_complex_decomposition(self) -> None:
        """Test complex query decomposes to 10 sub-tasks."""
        orch = OrchestratorAgent()
        q = "Comprehensively analyze and evaluate the economic, social, and environmental impacts of renewable energy adoption across developed and developing nations over the past two decades."
        tasks = orch.decompose_query(q)
        assert len(tasks) == 10
        perspectives = [t.perspective for t in tasks]
        assert "background" in perspectives
        assert "technical" in perspectives
        assert "security" in perspectives
        assert "ethical" in perspectives
        assert "synthesis" in perspectives

    def test_effort_override(self) -> None:
        """Test explicit effort level override."""
        orch = OrchestratorAgent()
        tasks = orch.decompose_query(
            "Simple question.",
            effort_level=EffortLevel.COMPLEX,
        )
        assert len(tasks) == 10


class TestOrchestratorRun:
    """Tests for full orchestrator runs."""

    @pytest.mark.asyncio
    async def test_run_simple_query(self) -> None:
        """Test orchestrator runs a simple query to completion."""
        orch = OrchestratorAgent(max_concurrency=4)

        async def worker_fn(worker_id: str, context: dict, sub_task: SubTask) -> Artifact:
            return Artifact(
                task_id=sub_task.subtask_id,
                content=f"Research on {sub_task.description}",
                summary=f"Found result for {sub_task.perspective}",
                confidence=0.9,
                sources=["https://example.com"],
            )

        result = await orch.run("What is AI?", worker_fn)
        assert isinstance(result, OrchestrationResult)
        assert result.query == "What is AI?"
        assert len(result.artifacts) == 1
        assert result.effort_level == EffortLevel.SIMPLE
        assert result.total_duration > 0
        assert result.average_confidence == 0.9

    @pytest.mark.asyncio
    async def test_run_comparison_query(self) -> None:
        """Test orchestrator runs a comparison query."""
        orch = OrchestratorAgent(max_concurrency=4)

        async def worker_fn(worker_id: str, context: dict, sub_task: SubTask) -> Artifact:
            return Artifact(
                task_id=sub_task.subtask_id,
                content=f"Results for {sub_task.perspective}",
                summary=f"Done: {sub_task.perspective}",
                confidence=0.85,
            )

        result = await orch.run("Compare A and B.", worker_fn)
        assert len(result.artifacts) == 3
        assert result.worker_count == 3
        assert result.average_confidence == 0.85

    @pytest.mark.asyncio
    async def test_run_complex_query(self) -> None:
        """Test orchestrator runs a complex query."""
        orch = OrchestratorAgent(max_concurrency=10)

        async def worker_fn(worker_id: str, context: dict, sub_task: SubTask) -> Artifact:
            return Artifact(
                task_id=sub_task.subtask_id,
                content=f"Findings from {sub_task.perspective} angle",
                summary=f"Perspective: {sub_task.perspective}",
                confidence=0.8,
            )

        q = "Analyze the impact of climate change on global agriculture, considering economic, social, and environmental factors."
        result = await orch.run(q, worker_fn)
        assert len(result.artifacts) == 10
        assert result.worker_count == 10
        assert 0 <= result.average_confidence <= 1.0

    @pytest.mark.asyncio
    async def test_run_with_metadata(self) -> None:
        """Test orchestrator passes metadata through to result."""
        orch = OrchestratorAgent()

        async def worker_fn(worker_id: str, context: dict, sub_task: SubTask) -> Artifact:
            return Artifact(
                task_id=sub_task.subtask_id,
                content="content",
                summary="summary",
                confidence=1.0,
            )

        result = await orch.run(
            "Simple query.",
            worker_fn,
            metadata={"session_id": "abc123"},
        )
        assert result.metadata["session_id"] == "abc123"

    @pytest.mark.asyncio
    async def test_synthesis_includes_sources(self) -> None:
        """Test summary includes collected sources."""
        orch = OrchestratorAgent()

        async def worker_fn(worker_id: str, context: dict, sub_task: SubTask) -> Artifact:
            return Artifact(
                task_id=sub_task.subtask_id,
                content="content",
                summary="summary",
                confidence=0.9,
                sources=[f"https://source-{sub_task.subtask_id}.com"],
            )

        result = await orch.run("Compare X and Y.", worker_fn)
        assert "https://source-" in result.summary
        assert "Sources" in result.summary

    @pytest.mark.asyncio
    async def test_result_to_dict(self) -> None:
        """Test OrchestrationResult serialization."""
        orch = OrchestratorAgent()

        async def worker_fn(worker_id: str, context: dict, sub_task: SubTask) -> Artifact:
            return Artifact(
                task_id=sub_task.subtask_id,
                content="c", summary="s", confidence=0.9,
            )

        result = await orch.run("Test query.", worker_fn)
        data = result.to_dict()
        assert data["query"] == "Test query."
        assert data["effort_level"] == "simple"
        assert data["worker_count"] == 1
        assert len(data["artifacts"]) == 1

    @pytest.mark.asyncio
    async def test_shutdown(self) -> None:
        """Test orchestrator shutdown."""
        orch = OrchestratorAgent()
        await orch.shutdown()
        assert orch.pool.active_count == 0

    @pytest.mark.asyncio
    async def test_stats(self) -> None:
        """Test orchestrator stats."""
        orch = OrchestratorAgent(orchestrator_id="test_orch", max_concurrency=8)
        stats = orch.stats()
        assert stats["orchestrator_id"] == "test_orch"
        assert stats["max_concurrency"] == 8

    @pytest.mark.asyncio
    async def test_empty_artifacts_synthesis(self) -> None:
        """Test synthesis with no artifacts produces graceful result."""
        orch = OrchestratorAgent()
        result = orch._synthesize(
            question="test",
            artifacts=[],
            effort_level=EffortLevel.SIMPLE,
            worker_count=0,
            total_duration=0.0,
        )
        assert "No artifacts were produced" in result.summary
        assert result.average_confidence == 0.0

    @pytest.mark.asyncio
    async def test_orchestrator_decompose_subtask_ids(self) -> None:
        """Test sub-task IDs follow expected pattern."""
        orch = OrchestratorAgent()
        tasks = orch.decompose_query(
            "Complex research query requiring deep analysis across multiple domains and perspectives.",
        )
        for i, task in enumerate(tasks, 1):
            assert task.subtask_id == f"st_{i}"
