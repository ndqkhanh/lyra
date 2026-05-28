"""Tests for graph.py — CueTagContentGraph and GraphNode."""
from __future__ import annotations

import pytest

from lyra_memory.reconstruction.graph import (
    CueTagContentGraph,
    GraphNode,
    NodeType,
)


@pytest.mark.unit
class TestGraphNode:
    """Tests for GraphNode dataclass."""

    def test_default_construction(self):
        node = GraphNode()
        assert node.id
        assert node.type == NodeType.CONTENT
        assert node.content == ""

    def test_cue_node(self):
        node = GraphNode(type=NodeType.CUE, content="Python testing")
        assert node.type == NodeType.CUE

    def test_tag_node(self):
        node = GraphNode(type=NodeType.TAG, content="testing")
        assert node.type == NodeType.TAG

    def test_content_node_with_metadata(self):
        node = GraphNode(
            type=NodeType.CONTENT,
            content="learned about pytest fixtures",
            metadata={"embedding": [0.1, 0.2], "source": "doc"},
        )
        assert node.metadata["embedding"] == [0.1, 0.2]

    def test_hash_by_id(self):
        node1 = GraphNode(id="abc", content="a")
        node2 = GraphNode(id="abc", content="b")
        assert hash(node1) == hash(node2)


@pytest.mark.unit
class TestCueTagContentGraph:
    """Tests for CueTagContentGraph."""

    def test_empty_graph(self):
        g = CueTagContentGraph()
        assert g.node_count == 0
        assert g.edge_count == 0

    def test_add_node_indexes_by_type(self):
        g = CueTagContentGraph()
        g.add_node(GraphNode(type=NodeType.CUE, content="query"))
        g.add_node(GraphNode(type=NodeType.TAG, content="tag"))
        g.add_node(GraphNode(type=NodeType.CONTENT, content="memory"))

        assert g.cue_count == 1
        assert g.tag_count == 1
        assert g.content_count == 1
        assert g.node_count == 3

    def test_add_edge_connects_nodes(self):
        g = CueTagContentGraph()
        cue = GraphNode(type=NodeType.CUE, content="test")
        tag = GraphNode(type=NodeType.TAG, content="testing")
        content = GraphNode(type=NodeType.CONTENT, content="learned")

        for n in (cue, tag, content):
            g.add_node(n)
        g.add_edge(cue.id, tag.id)
        g.add_edge(tag.id, content.id)

        assert g.edge_count == 2

    def test_add_edge_rejects_missing_nodes(self):
        g = CueTagContentGraph()
        g.add_edge("nonexistent", "also_nonexistent")
        assert g.edge_count == 0

    def test_cue_to_tag_forward_traversal(self):
        g = CueTagContentGraph()
        cue = GraphNode(type=NodeType.CUE, content="python testing")
        tag1 = GraphNode(type=NodeType.TAG, content="python")
        tag2 = GraphNode(type=NodeType.TAG, content="testing")

        for n in (cue, tag1, tag2):
            g.add_node(n)
        g.add_edge(cue.id, tag1.id)
        g.add_edge(cue.id, tag2.id)

        tags = g.get_tags(cue)
        assert len(tags) == 2

    def test_tag_to_content_forward_traversal(self):
        g = CueTagContentGraph()
        tag = GraphNode(type=NodeType.TAG, content="python")
        c1 = GraphNode(type=NodeType.CONTENT, content="pytest")
        c2 = GraphNode(type=NodeType.CONTENT, content="Django")

        for n in (tag, c1, c2):
            g.add_node(n)
        g.add_edge(tag.id, c1.id)
        g.add_edge(tag.id, c2.id)

        assert len(g.get_content(tag)) == 2

    def test_content_to_cue_reverse_traversal(self):
        g = CueTagContentGraph()
        content = GraphNode(type=NodeType.CONTENT, content="memory")
        cue1 = GraphNode(type=NodeType.CUE, content="query 1")
        cue2 = GraphNode(type=NodeType.CUE, content="query 2")

        for n in (content, cue1, cue2):
            g.add_node(n)
        g.add_edge(content.id, cue1.id)
        g.add_edge(content.id, cue2.id)

        assert len(g.get_related_cues(content)) == 2

    def test_get_tags_rejects_non_cue(self):
        g = CueTagContentGraph()
        tag = GraphNode(type=NodeType.TAG, content="test")
        g.add_node(tag)
        assert g.get_tags(tag) == []

    def test_get_content_rejects_non_tag(self):
        g = CueTagContentGraph()
        cue = GraphNode(type=NodeType.CUE, content="test")
        g.add_node(cue)
        assert g.get_content(cue) == []

    def test_get_related_cues_rejects_non_content(self):
        g = CueTagContentGraph()
        tag = GraphNode(type=NodeType.TAG, content="test")
        g.add_node(tag)
        assert g.get_related_cues(tag) == []

    def test_full_cue_tag_content_cue_path(self):
        g = CueTagContentGraph()
        cue0 = GraphNode(type=NodeType.CUE, content="how to test")
        tag = GraphNode(type=NodeType.TAG, content="testing")
        content = GraphNode(type=NodeType.CONTENT, content="use pytest")
        cue1 = GraphNode(type=NodeType.CUE, content="pytest fixtures")

        for n in (cue0, tag, content, cue1):
            g.add_node(n)
        g.add_edge(cue0.id, tag.id)
        g.add_edge(tag.id, content.id)
        g.add_edge(content.id, cue1.id)

        tags = g.get_tags(cue0)
        contents = g.get_content(tags[0])
        new_cues = g.get_related_cues(contents[0])

        assert tags[0].content == "testing"
        assert contents[0].content == "use pytest"
        assert new_cues[0].content == "pytest fixtures"

    def test_search_by_tag(self):
        g = CueTagContentGraph()
        tag = GraphNode(type=NodeType.TAG, content="python-testing")
        content = GraphNode(type=NodeType.CONTENT, content="pytest is great")
        g.add_node(tag)
        g.add_node(content)
        g.add_edge(tag.id, content.id)

        results = g.search_by_tag("python")
        assert len(results) == 1
        assert results[0].content == "pytest is great"

    def test_search_by_tag_case_insensitive(self):
        g = CueTagContentGraph()
        tag = GraphNode(type=NodeType.TAG, content="MachineLearning")
        content = GraphNode(type=NodeType.CONTENT, content="gradient descent")
        g.add_node(tag)
        g.add_node(content)
        g.add_edge(tag.id, content.id)

        assert len(g.search_by_tag("machinelearning")) == 1
        assert len(g.search_by_tag("MACHINE")) == 1
        assert len(g.search_by_tag("deep")) == 0


@pytest.mark.unit
class TestNodeType:
    """Tests for NodeType enum."""

    def test_all_node_types(self):
        assert NodeType.CUE.value == "cue"
        assert NodeType.TAG.value == "tag"
        assert NodeType.CONTENT.value == "content"

    def test_string_to_enum(self):
        assert NodeType("cue") == NodeType.CUE
        assert NodeType("tag") == NodeType.TAG
