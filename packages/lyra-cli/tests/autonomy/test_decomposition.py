"""Tests for goal decomposition sub-components (Step 5.1)."""

from __future__ import annotations

import pytest

from lyra_cli.autonomy.decomposition.dependency_graph import (
    DependencyGraphBuilder,
    GraphNode,
    NodeStatus,
)
from lyra_cli.autonomy.decomposition.strategy_selector import (
    DecompositionStrategy,
    StrategySelector,
)


# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture
def selector():
    return StrategySelector()


@pytest.fixture
def graph_builder():
    return DependencyGraphBuilder()


# ── TestStrategySelector ──────────────────────────────────────


class TestDecompositionStrategy:
    def test_strategy_values(self):
        assert DecompositionStrategy.TOP_DOWN is not None
        assert DecompositionStrategy.BOTTOM_UP is not None
        assert DecompositionStrategy.PARALLEL is not None


class TestStrategySelectorBasic:
    def test_select_default(self, selector):
        rec = selector.select()
        assert rec.strategy is not None
        assert rec.confidence > 0

    def test_select_architecture_design(self, selector):
        rec = selector.select(goal_type="architecture_design", complexity=0.8)
        assert rec.strategy == DecompositionStrategy.TOP_DOWN
        assert rec.confidence > 0.8

    def test_select_implementation(self, selector):
        rec = selector.select(goal_type="implementation", complexity=0.3)
        assert rec.strategy in (DecompositionStrategy.BOTTOM_UP, DecompositionStrategy.DEPTH_FIRST)

    def test_select_research(self, selector):
        rec = selector.select(goal_type="research", complexity=0.5)
        assert rec.strategy == DecompositionStrategy.BREADTH_FIRST

    def test_select_debugging(self, selector):
        rec = selector.select(goal_type="debugging", complexity=0.7)
        assert rec.strategy == DecompositionStrategy.DEPTH_FIRST

    def test_select_testing(self, selector):
        rec = selector.select(goal_type="testing", is_parallelizable=True)
        assert rec.strategy == DecompositionStrategy.PARALLEL

    def test_select_with_dependencies(self, selector):
        rec = selector.select(goal_type="planning", has_dependencies=True)
        assert rec.strategy == DecompositionStrategy.SEQUENTIAL

    def test_select_parallel_when_parallelizable(self, selector):
        rec = selector.select(goal_type="data_processing", is_parallelizable=True)
        assert rec.strategy == DecompositionStrategy.PARALLEL

    def test_select_high_complexity(self, selector):
        rec = selector.select(goal_type="system_design", complexity=0.9)
        assert rec.strategy in (DecompositionStrategy.TOP_DOWN, DecompositionStrategy.HYBRID)

    def test_estimated_subgoals(self, selector):
        rec = selector.select(estimated_scope=10)
        assert rec.estimated_subgoals == 10

    def test_reasoning_included(self, selector):
        rec = selector.select(goal_type="architecture_design")
        assert rec.reasoning


# ── TestDependencyGraphBuilder ────────────────────────────────


class TestGraphNode:
    def test_node_creation(self):
        n = GraphNode(node_id="g1", label="Design API")
        assert n.node_id == "g1"
        assert n.label == "Design API"
        assert n.status == NodeStatus.PENDING

    def test_node_immutability(self):
        n = GraphNode(node_id="g1", label="Test")
        with pytest.raises(Exception):
            n.status = NodeStatus.COMPLETED


class TestDependencyGraphBuilderBasic:
    def test_empty_builder(self, graph_builder):
        assert graph_builder.node_count == 0

    def test_add_node(self, graph_builder):
        graph_builder.add_node("g1", "Design API")
        assert graph_builder.node_count == 1

    def test_add_duplicate_node(self, graph_builder):
        graph_builder.add_node("g1")
        with pytest.raises(ValueError, match="already exists"):
            graph_builder.add_node("g1")

    def test_add_edge(self, graph_builder):
        graph_builder.add_node("g1", "Design")
        graph_builder.add_node("g2", "Implement")
        graph_builder.add_edge("g1", "g2")
        deps = graph_builder.get_dependencies("g2")
        assert "g1" in deps

    def test_add_edge_missing_source(self, graph_builder):
        graph_builder.add_node("g2")
        with pytest.raises(ValueError, match="Source node"):
            graph_builder.add_edge("g1", "g2")

    def test_add_edge_missing_target(self, graph_builder):
        graph_builder.add_node("g1")
        with pytest.raises(ValueError, match="Target node"):
            graph_builder.add_edge("g1", "g2")

    def test_mark_completed(self, graph_builder):
        graph_builder.add_node("g1", "Task 1")
        graph_builder.mark_completed("g1")
        deps = graph_builder.get_dependencies("g1")
        assert len(deps) == 0  # No dependencies

    def test_mark_completed_unblocks(self, graph_builder):
        graph_builder.add_node("g1", "Design")
        graph_builder.add_node("g2", "Implement")
        graph_builder.add_edge("g1", "g2")
        graph_builder.mark_completed("g1")
        ready = graph_builder.get_ready_nodes()
        assert "g2" in ready

    def test_mark_failed_blocks_dependents(self, graph_builder):
        graph_builder.add_node("g1", "Design")
        graph_builder.add_node("g2", "Implement")
        graph_builder.add_edge("g1", "g2")
        graph_builder.mark_completed("g1")
        ready_before = graph_builder.get_ready_nodes()
        assert "g2" in ready_before
        # Re-mark g1 as failed by creating a new scenario
        graph_builder.add_node("g3", "Deploy")
        graph_builder.add_edge("g2", "g3")
        graph_builder.mark_failed("g2")
        blocked = graph_builder.get_blocked_nodes()
        assert "g3" in blocked

    def test_get_ready_nodes_empty_initially(self, graph_builder):
        graph_builder.add_node("g1", "Task 1")
        graph_builder.add_node("g2", "Task 2")
        graph_builder.add_edge("g1", "g2")
        ready = graph_builder.get_ready_nodes()
        assert "g1" in ready  # No deps, should be ready
        assert "g2" not in ready  # Blocked by g1

    def test_get_execution_order(self, graph_builder):
        graph_builder.add_node("design", "Design System")
        graph_builder.add_node("implement", "Implement")
        graph_builder.add_node("test", "Test")
        graph_builder.add_node("deploy", "Deploy")
        graph_builder.add_edge("design", "implement")
        graph_builder.add_edge("implement", "test")
        graph_builder.add_edge("test", "deploy")
        order = graph_builder.get_execution_order()
        assert order == ["design", "implement", "test", "deploy"]

    def test_get_execution_order_diamond(self, graph_builder):
        graph_builder.add_node("a", "A")
        graph_builder.add_node("b1", "B1")
        graph_builder.add_node("b2", "B2")
        graph_builder.add_node("c", "C")
        graph_builder.add_edge("a", "b1")
        graph_builder.add_edge("a", "b2")
        graph_builder.add_edge("b1", "c")
        graph_builder.add_edge("b2", "c")
        order = graph_builder.get_execution_order()
        assert order[0] == "a"
        assert order[-1] == "c"

    def test_get_dependents(self, graph_builder):
        graph_builder.add_node("a", "A")
        graph_builder.add_node("b", "B")
        graph_builder.add_edge("a", "b")
        deps = graph_builder.get_dependents("a")
        assert "b" in deps

    def test_get_dependencies(self, graph_builder):
        graph_builder.add_node("a", "A")
        graph_builder.add_node("b", "B")
        graph_builder.add_edge("a", "b")
        deps = graph_builder.get_dependencies("b")
        assert "a" in deps

    def test_build(self, graph_builder):
        graph_builder.add_node("a", "A")
        graph_builder.add_node("b", "B")
        graph_builder.add_edge("a", "b")
        g = graph_builder.build()
        assert g.node_count == 2
        assert g.edge_count == 1

    def test_mark_node_missing(self, graph_builder):
        with pytest.raises(ValueError, match="not found"):
            graph_builder.mark_completed("nonexistent")


class TestNodeStatus:
    def test_status_values(self):
        assert NodeStatus.PENDING is not None
        assert NodeStatus.READY is not None
        assert NodeStatus.IN_PROGRESS is not None
        assert NodeStatus.COMPLETED is not None
        assert NodeStatus.FAILED is not None
        assert NodeStatus.BLOCKED is not None
