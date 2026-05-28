"""Tests for the goal decomposer."""

from __future__ import annotations

import pytest

from lyra_cli.autonomy.goal_decomposer import (
    CyclicDependencyError,
    DependencyGraph,
    Goal,
    GoalDecomposer,
    Subtask,
)


class TestGoalDecomposer:
    """Suite: GoalDecomposer decomposition and topological sort."""

    def test_decompose_produces_execution_order(self) -> None:
        goal = Goal(id="test01", description="Build feature X")
        decomposer = GoalDecomposer()
        graph = decomposer.decompose(goal)

        assert isinstance(graph, DependencyGraph)
        assert graph.goal.id == "test01"
        assert len(graph.subtasks) == 3
        assert len(graph.execution_order) == 3

    def test_execution_order_respects_dependencies(self) -> None:
        goal = Goal(id="order_test", description="Check order")
        decomposer = GoalDecomposer()
        graph = decomposer.decompose(goal)

        # research must come before implement, implement before verify
        order = graph.execution_order
        assert order.index("order_test_research") < order.index("order_test_implement")
        assert order.index("order_test_implement") < order.index("order_test_verify")

    def test_custom_subtask_generation(self) -> None:
        class CustomDecomposer(GoalDecomposer):
            def _generate_subtasks(self, goal: Goal) -> list[Subtask]:
                return [
                    Subtask(id="a", description="Step A"),
                    Subtask(id="b", description="Step B", depends_on=("a",)),
                    Subtask(id="c", description="Step C", depends_on=("b",)),
                    Subtask(id="d", description="Step D", depends_on=("a",)),
                ]

        goal = Goal(id="custom", description="Custom plan")
        decomposer = CustomDecomposer()
        graph = decomposer.decompose(goal)

        assert len(graph.subtasks) == 4
        # a must come before b, c, d
        order = graph.execution_order
        assert order.index("a") < order.index("b")
        assert order.index("a") < order.index("d")
        assert order.index("b") < order.index("c")

    def test_cyclic_dependency_raises(self) -> None:
        class CyclicDecomposer(GoalDecomposer):
            def _generate_subtasks(self, goal: Goal) -> list[Subtask]:
                return [
                    Subtask(id="x", description="X", depends_on=("y",)),
                    Subtask(id="y", description="Y", depends_on=("x",)),
                ]

        goal = Goal(id="cycle", description="Cycle test")
        decomposer = CyclicDecomposer()
        with pytest.raises(CyclicDependencyError):
            decomposer.decompose(goal)

    def test_missing_dependency_raises(self) -> None:
        class MissingDepDecomposer(GoalDecomposer):
            def _generate_subtasks(self, goal: Goal) -> list[Subtask]:
                return [
                    Subtask(id="a", description="A", depends_on=("nonexistent",)),
                ]

        goal = Goal(id="missing", description="Missing dep")
        decomposer = MissingDepDecomposer()
        with pytest.raises(CyclicDependencyError, match="unknown"):
            decomposer.decompose(goal)

    def test_subtask_by_id_lookup(self) -> None:
        goal = Goal(id="lookup", description="Lookup test")
        decomposer = GoalDecomposer()
        graph = decomposer.decompose(goal)

        sub = graph.subtask_by_id("lookup_research")
        assert sub is not None
        assert sub.id == "lookup_research"

        missing = graph.subtask_by_id("does_not_exist")
        assert missing is None

    def test_single_subtask_no_deps(self) -> None:
        class SingleDecomposer(GoalDecomposer):
            def _generate_subtasks(self, goal: Goal) -> list[Subtask]:
                return [Subtask(id="only", description="Only step")]

        goal = Goal(id="single", description="Single task")
        decomposer = SingleDecomposer()
        graph = decomposer.decompose(goal)

        assert graph.execution_order == ("only",)

    def test_goal_metadata_preserved(self) -> None:
        goal = Goal(id="meta", description="With metadata", metadata={"priority": "high"})
        decomposer = GoalDecomposer()
        graph = decomposer.decompose(goal)
        assert graph.goal.metadata["priority"] == "high"
