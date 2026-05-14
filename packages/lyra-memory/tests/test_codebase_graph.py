"""Tests for Phase C: codebase knowledge graph."""
from __future__ import annotations

import pytest

from lyra_memory.codebase_graph import CodebaseGraph, GraphEdge, GraphNode, NodeKind, EdgeKind


class TestGraphNode:
    def test_basic_creation(self):
        n = GraphNode(id="fn:foo", kind=NodeKind.function, label="foo")
        assert n.id == "fn:foo"
        assert n.kind == NodeKind.function
        assert n.label == "foo"

    def test_metadata_defaults_empty(self):
        n = GraphNode(id="m:bar", kind=NodeKind.module, label="bar")
        assert n.metadata == {}


class TestGraphEdge:
    def test_basic_creation(self):
        e = GraphEdge(source_id="fn:a", target_id="fn:b", kind=EdgeKind.calls)
        assert e.source_id == "fn:a"
        assert e.target_id == "fn:b"
        assert e.kind == EdgeKind.calls


class TestCodebaseGraph:
    def _graph_with_chain(self) -> CodebaseGraph:
        g = CodebaseGraph()
        g.add_node(GraphNode("a", NodeKind.function, "a"))
        g.add_node(GraphNode("b", NodeKind.function, "b"))
        g.add_node(GraphNode("c", NodeKind.function, "c"))
        g.add_edge(GraphEdge("a", "b", EdgeKind.calls))
        g.add_edge(GraphEdge("b", "c", EdgeKind.calls))
        return g

    def test_node_count(self):
        g = self._graph_with_chain()
        assert g.node_count == 3

    def test_edge_count(self):
        g = self._graph_with_chain()
        assert g.edge_count == 2

    def test_get_node(self):
        g = self._graph_with_chain()
        assert g.get_node("a") is not None
        assert g.get_node("missing") is None

    def test_successors(self):
        g = self._graph_with_chain()
        succs = g.successors("a")
        assert len(succs) == 1
        assert succs[0].target_id == "b"

    def test_predecessors(self):
        g = self._graph_with_chain()
        preds = g.predecessors("b")
        assert len(preds) == 1
        assert preds[0].source_id == "a"

    def test_nodes_by_kind(self):
        g = CodebaseGraph()
        g.add_node(GraphNode("f1", NodeKind.function, "f1"))
        g.add_node(GraphNode("m1", NodeKind.module, "m1"))
        g.add_node(GraphNode("f2", NodeKind.function, "f2"))
        funcs = g.nodes_by_kind(NodeKind.function)
        assert len(funcs) == 2
        mods = g.nodes_by_kind(NodeKind.module)
        assert len(mods) == 1

    def test_find_impact_direct(self):
        g = self._graph_with_chain()
        # Changing 'a' impacts 'b' and 'c' transitively
        impact = g.find_impact("a")
        assert "b" in impact
        assert "c" in impact
        assert "a" not in impact

    def test_find_impact_isolated(self):
        g = CodebaseGraph()
        g.add_node(GraphNode("x", NodeKind.function, "x"))
        assert g.find_impact("x") == set()

    def test_find_impact_max_depth(self):
        g = self._graph_with_chain()
        # max_depth=1 — only immediate successors
        impact = g.find_impact("a", max_depth=1)
        assert "b" in impact
        assert "c" not in impact

    def test_add_duplicate_node_overwrites(self):
        g = CodebaseGraph()
        g.add_node(GraphNode("x", NodeKind.function, "old"))
        g.add_node(GraphNode("x", NodeKind.function, "new"))
        assert g.node_count == 1
        node = g.get_node("x")
        assert node is not None
        assert node.label == "new"

    def test_edge_on_unknown_node_raises(self):
        g = CodebaseGraph()
        g.add_node(GraphNode("a", NodeKind.function, "a"))
        with pytest.raises((KeyError, ValueError)):
            g.add_edge(GraphEdge("a", "missing", EdgeKind.calls))
