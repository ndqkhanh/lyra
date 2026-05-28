"""Tests for the Phase 2.1 Task Decomposer."""
from __future__ import annotations

import pytest
from lyra_core.orchestration.task_decomposer import (
    CoordinationStrategy,
    DecompositionResult,
    Subtask,
    TaskDecomposer,
    TaskPriority,
)


class TestSubtask:
    def test_creation_with_valid_effort(self):
        s = Subtask(
            subtask_id="sub-001",
            name="test subtask",
            description="A test subtask",
            dependencies=(),
            priority=TaskPriority.MEDIUM,
            estimated_effort=5,
            coordination=CoordinationStrategy.SEQUENTIAL,
            agent_role="executor",
            acceptance_criteria="All tests pass",
        )
        assert s.subtask_id == "sub-001"
        assert s.estimated_effort == 5

    def test_effort_below_1_raises(self):
        with pytest.raises(ValueError):
            Subtask(
                subtask_id="sub-001",
                name="bad",
                description="bad",
                dependencies=(),
                priority=TaskPriority.LOW,
                estimated_effort=0,
                coordination=CoordinationStrategy.SEQUENTIAL,
                agent_role="executor",
                acceptance_criteria="nope",
            )

    def test_effort_above_10_raises(self):
        with pytest.raises(ValueError):
            Subtask(
                subtask_id="sub-001",
                name="bad",
                description="bad",
                dependencies=(),
                priority=TaskPriority.LOW,
                estimated_effort=11,
                coordination=CoordinationStrategy.SEQUENTIAL,
                agent_role="executor",
                acceptance_criteria="nope",
            )

    def test_frozen_dataclass(self):
        s = Subtask(
            subtask_id="sub-001",
            name="test",
            description="desc",
            dependencies=(),
            priority=TaskPriority.MEDIUM,
            estimated_effort=5,
            coordination=CoordinationStrategy.SEQUENTIAL,
            agent_role="executor",
            acceptance_criteria="ok",
        )
        with pytest.raises(Exception):
            s.name = "mutated"  # type: ignore[misc]


class TestTaskDecomposer:
    def test_decompose_returns_result(self):
        decomposer = TaskDecomposer()
        result = decomposer.decompose("Implement a login page")
        assert isinstance(result, DecompositionResult)
        assert len(result.subtasks) >= 3

    def test_decompose_implement_task(self):
        decomposer = TaskDecomposer()
        result = decomposer.decompose("Implement user authentication with OAuth2")
        names = [s.name for s in result.subtasks]
        assert any("design" in n for n in names)
        assert any("implement" in n for n in names)
        assert any("test" in n for n in names)

    def test_decompose_refactor_task(self):
        decomposer = TaskDecomposer()
        result = decomposer.decompose("Refactor the database layer")
        names = [s.name for s in result.subtasks]
        assert any("analyze" in n for n in names)

    def test_decompose_debug_task(self):
        decomposer = TaskDecomposer()
        result = decomposer.decompose("Debug the memory leak in production")
        names = [s.name for s in result.subtasks]
        assert any("reproduce" in n for n in names) or any("isolate" in n for n in names)

    def test_decompose_research_task(self):
        decomposer = TaskDecomposer()
        result = decomposer.decompose("Research GraphQL vs REST for new API")
        names = [s.name for s in result.subtasks]
        assert any("search" in n for n in names)

    def test_first_subtask_is_critical(self):
        decomposer = TaskDecomposer()
        result = decomposer.decompose("Implement a cache layer")
        assert result.subtasks[0].priority == TaskPriority.CRITICAL

    def test_sequential_dependencies_form_chain(self):
        decomposer = TaskDecomposer()
        result = decomposer.decompose("Implement a cache layer")
        for i in range(1, len(result.subtasks)):
            prev_id = result.subtasks[i - 1].subtask_id
            assert prev_id in result.subtasks[i].dependencies

    def test_parallel_strategy_for_test_heavy_tasks(self):
        decomposer = TaskDecomposer()
        result = decomposer.decompose(
            "test test test test test test test", max_subtasks=8
        )
        has_parallel = any(
            s.coordination == CoordinationStrategy.PARALLEL
            for s in result.subtasks
        )
        assert has_parallel

    def test_max_subtasks_respected(self):
        decomposer = TaskDecomposer()
        result = decomposer.decompose("Implement auth", max_subtasks=3)
        assert len(result.subtasks) <= 3

    def test_total_effort_is_sum(self):
        decomposer = TaskDecomposer()
        result = decomposer.decompose("Implement auth")
        assert result.total_effort == sum(s.estimated_effort for s in result.subtasks)

    def test_result_id_is_unique(self):
        decomposer = TaskDecomposer()
        r1 = decomposer.decompose("task a")
        r2 = decomposer.decompose("task b")
        assert r1.result_id != r2.result_id

    def test_summary_includes_task_info(self):
        decomposer = TaskDecomposer()
        result = decomposer.decompose("Implement a cache layer")
        assert "cache" in result.summary.lower()

    def test_explicit_strategy_overrides_default(self):
        decomposer = TaskDecomposer()
        result = decomposer.decompose(
            "Implement auth", strategy=CoordinationStrategy.VOTING
        )
        assert result.default_strategy == CoordinationStrategy.VOTING

    def test_default_strategy_is_sequential_for_small_tasks(self):
        decomposer = TaskDecomposer()
        result = decomposer.decompose("Implement auth")
        assert result.default_strategy == CoordinationStrategy.SEQUENTIAL


class TestDependencyGraph:
    def test_entry_points_have_no_dependencies(self):
        decomposer = TaskDecomposer()
        result = decomposer.decompose("Implement auth")
        for entry_id in result.graph.entry_points:
            subtask = next(s for s in result.subtasks if s.subtask_id == entry_id)
            assert len(subtask.dependencies) == 0

    def test_max_depth_is_positive(self):
        decomposer = TaskDecomposer()
        result = decomposer.decompose("Implement auth with full test coverage")
        assert result.graph.max_depth >= 1

    def test_adjacency_maps_all_subtasks(self):
        decomposer = TaskDecomposer()
        result = decomposer.decompose("Implement auth")
        assert len(result.graph.adjacency) == len(result.subtasks)


class TestExecutionOrder:
    def test_topological_order_starts_with_entry_points(self):
        decomposer = TaskDecomposer()
        result = decomposer.decompose("Implement auth")
        order = decomposer.get_execution_order(result)
        assert order[0].subtask_id in result.graph.entry_points

    def test_topological_order_contains_all_subtasks(self):
        decomposer = TaskDecomposer()
        result = decomposer.decompose("Implement auth")
        order = decomposer.get_execution_order(result)
        assert len(order) == len(result.subtasks)

    def test_get_next_available_returns_entry_points_initially(self):
        decomposer = TaskDecomposer()
        result = decomposer.decompose("Implement auth")
        available = decomposer.get_next_available(result, set())
        entry_ids = {s.subtask_id for s in available}
        assert entry_ids == set(result.graph.entry_points)

    def test_get_next_available_after_first_completed(self):
        decomposer = TaskDecomposer()
        result = decomposer.decompose("Implement auth")
        first = result.subtasks[0].subtask_id
        available = decomposer.get_next_available(result, {first})
        if len(result.subtasks) > 1:
            assert result.subtasks[1].subtask_id in {s.subtask_id for s in available}

    def test_get_next_available_all_completed(self):
        decomposer = TaskDecomposer()
        result = decomposer.decompose("Implement auth")
        all_ids = {s.subtask_id for s in result.subtasks}
        available = decomposer.get_next_available(result, all_ids)
        assert len(available) == 0


class TestCriticalPath:
    def test_critical_path_is_non_empty(self):
        decomposer = TaskDecomposer()
        result = decomposer.decompose("Implement auth")
        assert len(result.critical_path) > 0

    def test_critical_path_starts_at_entry_point(self):
        decomposer = TaskDecomposer()
        result = decomposer.decompose("Implement auth")
        assert result.critical_path[0] == result.graph.entry_points[0]


class TestCustomPhaseGenerators:
    def test_register_and_use_custom_generator(self):
        decomposer = TaskDecomposer()

        def custom_gen(task: str, _domain: str) -> list:
            return [
                Subtask(
                    subtask_id="custom-1",
                    name="[custom] step1",
                    description="Custom step 1",
                    dependencies=(),
                    priority=TaskPriority.HIGH,
                    estimated_effort=3,
                    coordination=CoordinationStrategy.SEQUENTIAL,
                    agent_role="executor",
                    acceptance_criteria="done",
                )
            ]

        decomposer.register_phase_generator("custom", custom_gen)
        assert "custom" in decomposer._phase_generators


class TestUnknownDomain:
    def test_unknown_domain_defaults_to_implement(self):
        decomposer = TaskDecomposer()
        result = decomposer.decompose("Do something mysterious and unknown")
        assert len(result.subtasks) >= 3
