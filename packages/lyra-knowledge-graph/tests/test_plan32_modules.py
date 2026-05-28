"""Tests for graph_querier, graph_visualizer, and kg_consolidator modules."""

from __future__ import annotations

import json

import pytest

from lyra_knowledge_graph.graph_builder import (
    EdgeRelation,
    KnowledgeEdge,
    KnowledgeGraph,
    KnowledgeNode,
    NodeType,
)
from lyra_knowledge_graph.graph_querier import (
    GraphQuerier,
    PathResult,
    QueryStrategy,
    SortOrder,
    SubgraphResult,
)
from lyra_knowledge_graph.graph_visualizer import (
    ExportFormat,
    GraphVisualizer,
    VisualStyle,
)
from lyra_knowledge_graph.kg_consolidator import (
    KGConsolidator,
    MergeStrategy,
)


def _make_graph() -> KnowledgeGraph:
    g = KnowledgeGraph()
    g = g.add_node(KnowledgeNode("a", NodeType.CONCEPT, "Alpha", confidence=0.9))
    g = g.add_node(KnowledgeNode("b", NodeType.CONCEPT, "Beta", confidence=0.8))
    g = g.add_node(KnowledgeNode("c", NodeType.INSIGHT, "Gamma", confidence=0.7))
    g = g.add_node(KnowledgeNode("d", NodeType.SOURCE, "Delta", confidence=0.6))
    g = g.add_edge(KnowledgeEdge("a->b", "a", "b", EdgeRelation.SUPPORTS, weight=1.0))
    g = g.add_edge(KnowledgeEdge("b->c", "b", "c", EdgeRelation.EXTENDS, weight=0.8))
    g = g.add_edge(KnowledgeEdge("c->d", "c", "d", EdgeRelation.CITES, weight=0.5))
    g = g.add_edge(KnowledgeEdge("a->c", "a", "c", EdgeRelation.RELATES_TO, weight=0.6))
    return g


class TestGraphQuerier:
    def test_find_paths_bfs_direct(self):
        g = _make_graph()
        q = GraphQuerier(g)
        paths = q.find_paths("a", "c")
        assert len(paths) >= 1
        assert any(p.path == ["a", "c"] for p in paths)

    def test_find_paths_bfs_multihop(self):
        g = _make_graph()
        q = GraphQuerier(g)
        paths = q.find_paths("a", "d")
        assert len(paths) >= 1

    def test_find_paths_nonexistent_raises(self):
        g = _make_graph()
        q = GraphQuerier(g)
        with pytest.raises(Exception):
            q.find_paths("nonexistent", "d")

    def test_find_paths_dfs(self):
        g = _make_graph()
        q = GraphQuerier(g)
        paths = q.find_paths("a", "d", strategy=QueryStrategy.DFS)
        assert len(paths) >= 1

    def test_extract_subgraph(self):
        g = _make_graph()
        q = GraphQuerier(g)
        sg = q.extract_subgraph("a", depth=2)
        assert isinstance(sg, SubgraphResult)
        assert sg.root_id == "a"
        assert sg.node_count >= 1

    def test_extract_subgraph_nonexistent_raises(self):
        g = _make_graph()
        q = GraphQuerier(g)
        with pytest.raises(Exception):
            q.extract_subgraph("nonexistent")

    def test_find_by_pattern_type(self):
        g = _make_graph()
        q = GraphQuerier(g)
        results = q.find_by_pattern(node_type=NodeType.CONCEPT)
        assert len(results) == 2

    def test_find_by_pattern_relation(self):
        g = _make_graph()
        q = GraphQuerier(g)
        results = q.find_by_pattern(relation=EdgeRelation.SUPPORTS)
        assert len(results) >= 1

    def test_find_by_pattern_min_confidence(self):
        g = _make_graph()
        q = GraphQuerier(g)
        results = q.find_by_pattern(min_confidence=0.8)
        assert len(results) >= 1

    def test_ranked_search(self):
        g = _make_graph()
        q = GraphQuerier(g)
        result = q.ranked_search("alpha")
        assert len(result.nodes) >= 1
        assert result.total_matches >= 1

    def test_ranked_search_by_degree(self):
        g = _make_graph()
        q = GraphQuerier(g)
        result = q.ranked_search("a", sort_by=SortOrder.DEGREE)
        assert result.total_matches > 0

    def test_ranked_search_by_pagerank(self):
        g = _make_graph()
        q = GraphQuerier(g)
        result = q.ranked_search("a", sort_by=SortOrder.PAGE_RANK)
        assert result.total_matches > 0

    def test_path_result_properties(self):
        p = PathResult(path=["a", "b", "c"], length=2, total_weight=1.8)
        assert p.node_count == 3

    def test_stats(self):
        g = _make_graph()
        q = GraphQuerier(g)
        s = q.stats()
        assert s["graph_nodes"] == 4
        assert s["graph_edges"] == 4


class TestGraphVisualizer:
    def test_export_dot(self):
        g = _make_graph()
        v = GraphVisualizer(g)
        dot = v.export(ExportFormat.DOT)
        assert "digraph KnowledgeGraph" in dot
        assert "Alpha" in dot

    def test_export_mermaid(self):
        g = _make_graph()
        v = GraphVisualizer(g)
        md = v.export(ExportFormat.MERMAID)
        assert "graph TD" in md
        assert "Alpha" in md

    def test_export_json_tree(self):
        g = _make_graph()
        v = GraphVisualizer(g)
        tree = v.export(ExportFormat.JSON_TREE)
        data = json.loads(tree)
        assert "roots" in data
        assert "graph_summary" in data

    def test_export_ascii(self):
        g = _make_graph()
        v = GraphVisualizer(g)
        ascii_out = v.export(ExportFormat.ASCII)
        assert "Knowledge Graph" in ascii_out
        assert "Alpha" in ascii_out

    def test_custom_style(self):
        g = _make_graph()
        style = VisualStyle(
            node_colors={"concept": "#FFF"},
            edge_styles={"supports": "bold"},
            font_size=14,
            direction="TB",
        )
        v = GraphVisualizer(g, style=style)
        dot = v.export(ExportFormat.DOT)
        assert "rankdir=TB" in dot

    def test_stats(self):
        g = _make_graph()
        v = GraphVisualizer(g)
        s = v.stats()
        assert s["nodes_visualizable"] == 4


class TestKGConsolidator:
    def test_consolidate_empty(self):
        c = KGConsolidator()
        report = c.consolidate([])
        assert report.graphs_merged == 0
        assert report.nodes_after == 0

    def test_consolidate_single(self):
        c = KGConsolidator()
        g = _make_graph()
        report = c.consolidate([g])
        assert report.graphs_merged == 1
        assert report.nodes_after == 4

    def test_consolidate_duplicates(self):
        c = KGConsolidator()
        g1 = _make_graph()
        g2 = _make_graph()
        report = c.consolidate([g1, g2])
        assert report.duplicates_resolved == 4
        assert report.nodes_after == 4

    def test_consolidate_keep_last(self):
        c = KGConsolidator(merge_strategy=MergeStrategy.KEEP_LAST)
        g1 = KnowledgeGraph()
        g1 = g1.add_node(KnowledgeNode("x", NodeType.CONCEPT, "Test", confidence=0.5))
        g2 = KnowledgeGraph()
        g2 = g2.add_node(KnowledgeNode("y", NodeType.CONCEPT, "Test", confidence=0.9))
        report = c.consolidate([g1, g2])
        assert report.duplicates_resolved == 1

    def test_consolidate_average_confidence(self):
        c = KGConsolidator(merge_strategy=MergeStrategy.AVERAGE_CONFIDENCE)
        g1 = KnowledgeGraph()
        g1 = g1.add_node(KnowledgeNode("x", NodeType.CONCEPT, "Unique", confidence=0.8))
        g2 = KnowledgeGraph()
        g2 = g2.add_node(KnowledgeNode("y", NodeType.CONCEPT, "Unique", confidence=0.4))
        report = c.consolidate([g1, g2])
        assert report.nodes_after == 1

    def test_merge_edges_deduplicate(self):
        c = KGConsolidator()
        g = _make_graph()
        compacted = c.merge_edges(g, deduplicate=True)
        assert compacted.edge_count == g.edge_count

    def test_compact_by_confidence(self):
        c = KGConsolidator()
        g = _make_graph()
        compacted = c.compact(g, min_confidence=0.8)
        assert compacted.node_count <= g.node_count

    def test_get_reports(self):
        c = KGConsolidator()
        c.consolidate([_make_graph()])
        reports = c.get_reports()
        assert len(reports) == 1

    def test_stats(self):
        c = KGConsolidator()
        c.consolidate([_make_graph()])
        s = c.stats()
        assert s["total_consolidations"] == 1
        assert "merge_strategy" in s

    def test_report_properties(self):
        c = KGConsolidator()
        g = _make_graph()
        report = c.consolidate([g])
        assert report.node_reduction_pct == 0.0
        assert isinstance(report.duration_ms, float)
