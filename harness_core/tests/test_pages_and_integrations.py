"""Tests for Pages document surface + external-graph integration bridges."""
from __future__ import annotations

import pytest

from harness_core.integrations import (
    AdaptedDocument,
    AdaptedEdge,
    AdaptedGraph,
    AdaptedNode,
    adapt_graph,
    verify_graph_protocol,
)
from harness_core.multi_hop import HippoRAGRetriever, SimpleDocument, SimpleGraph
from harness_core.pages import (
    EditConflict,
    Page,
    PageEditor,
    PageHistory,
    PageSnapshot,
    line_diff_summary,
)


# --- Pages: snapshots, history, editor ----------------------------------


class TestPageSnapshot:
    def test_valid_v1(self):
        s = PageSnapshot(
            page_id="p1", content="x", author="user:alice", version=1, parent_version=None
        )
        assert s.is_user_edit is True

    def test_v1_with_parent_rejected(self):
        with pytest.raises(ValueError):
            PageSnapshot(
                page_id="p1", content="x", author="u:a", version=1, parent_version=0
            )

    def test_v_above_1_requires_parent(self):
        with pytest.raises(ValueError):
            PageSnapshot(
                page_id="p1", content="x", author="u:a", version=2, parent_version=None
            )

    def test_zero_version_rejected(self):
        with pytest.raises(ValueError):
            PageSnapshot(
                page_id="p1", content="x", author="u:a", version=0, parent_version=None
            )

    def test_empty_author_rejected(self):
        with pytest.raises(ValueError):
            PageSnapshot(
                page_id="p1", content="x", author="", version=1, parent_version=None
            )

    def test_agent_edit_flag(self):
        s = PageSnapshot(
            page_id="p1", content="x", author="agent:bot", version=1, parent_version=None
        )
        assert s.is_agent_edit is True
        assert s.is_user_edit is False


class TestLineDiffSummary:
    def test_empty(self):
        assert line_diff_summary("", "") == "+0 -0"

    def test_added_lines(self):
        assert line_diff_summary("a", "a\nb") == "+1 -0"

    def test_removed_lines(self):
        assert line_diff_summary("a\nb", "a") == "+0 -1"

    def test_replacement(self):
        assert line_diff_summary("a", "b") == "+1 -1"


class TestPageHistory:
    def test_current_empty(self):
        h = PageHistory(page_id="p1")
        assert h.current is None
        assert h.linear_chain() == []

    def test_append_and_current(self):
        h = PageHistory(page_id="p1")
        s1 = PageSnapshot(
            page_id="p1", content="hello", author="user:a", version=1, parent_version=None
        )
        h.append_snapshot(s1)
        assert h.current.version == 1

    def test_append_wrong_page_id_rejected(self):
        h = PageHistory(page_id="p1")
        bad = PageSnapshot(
            page_id="other", content="x", author="u:a", version=1, parent_version=None
        )
        with pytest.raises(ValueError):
            h.append_snapshot(bad)

    def test_duplicate_version_rejected(self):
        h = PageHistory(page_id="p1")
        h.append_snapshot(PageSnapshot(
            page_id="p1", content="a", author="u:a", version=1, parent_version=None
        ))
        with pytest.raises(ValueError):
            h.append_snapshot(PageSnapshot(
                page_id="p1", content="b", author="u:b", version=1, parent_version=None
            ))

    def test_at_version(self):
        h = PageHistory(page_id="p1")
        h.append_snapshot(PageSnapshot(
            page_id="p1", content="a", author="u:a", version=1, parent_version=None
        ))
        assert h.at_version(1).content == "a"
        assert h.at_version(99) is None

    def test_linear_chain_simple(self):
        h = PageHistory(page_id="p1")
        for v, parent in [(1, None), (2, 1), (3, 2)]:
            h.append_snapshot(PageSnapshot(
                page_id="p1", content=f"v{v}", author="u:a", version=v, parent_version=parent
            ))
        chain = h.linear_chain()
        assert [s.version for s in chain] == [1, 2, 3]

    def test_authors_chronological_unique(self):
        h = PageHistory(page_id="p1")
        h.append_snapshot(PageSnapshot(
            page_id="p1", content="a", author="user:alice", version=1, parent_version=None,
            created_at=1.0,
        ))
        h.append_snapshot(PageSnapshot(
            page_id="p1", content="b", author="agent:bot", version=2, parent_version=1,
            created_at=2.0,
        ))
        h.append_snapshot(PageSnapshot(
            page_id="p1", content="c", author="user:alice", version=3, parent_version=2,
            created_at=3.0,
        ))
        # Alice once, bot once, in chronological order.
        assert h.authors() == ["user:alice", "agent:bot"]

    def test_no_conflicts_on_linear(self):
        h = PageHistory(page_id="p1")
        for v, parent in [(1, None), (2, 1)]:
            h.append_snapshot(PageSnapshot(
                page_id="p1", content="x", author="u:a", version=v, parent_version=parent
            ))
        assert h.conflicts() == []

    def test_concurrent_edits_produce_conflict(self):
        h = PageHistory(page_id="p1")
        h.append_snapshot(PageSnapshot(
            page_id="p1", content="a", author="u:a", version=1, parent_version=None
        ))
        # Two edits both forking from version 1.
        h.append_snapshot(PageSnapshot(
            page_id="p1", content="b", author="u:b", version=2, parent_version=1
        ))
        h.append_snapshot(PageSnapshot(
            page_id="p1", content="c", author="agent:bot", version=3, parent_version=1
        ))
        conflicts = h.conflicts()
        assert len(conflicts) == 1
        assert conflicts[0].parent_version == 1
        assert set(conflicts[0].versions_in_conflict) == {2, 3}

    def test_stats(self):
        h = PageHistory(page_id="p1")
        h.append_snapshot(PageSnapshot(
            page_id="p1", content="a", author="user:alice", version=1, parent_version=None
        ))
        h.append_snapshot(PageSnapshot(
            page_id="p1", content="b", author="agent:bot", version=2, parent_version=1
        ))
        s = h.stats()
        assert s["snapshots"] == 2
        assert s["user_edits"] == 1
        assert s["agent_edits"] == 1


class TestPageEditor:
    def test_create_then_edit(self):
        editor = PageEditor(history=PageHistory(page_id="p1"))
        s1 = editor.create(content="hello", author="user:alice")
        s2 = editor.edit(content="hello world", author="agent:bot")
        assert s1.version == 1
        assert s2.version == 2
        assert s2.parent_version == 1
        assert s2.diff_summary == "+1 -1"

    def test_create_on_nonempty_raises(self):
        editor = PageEditor(history=PageHistory(page_id="p1"))
        editor.create(content="x", author="u:a")
        with pytest.raises(RuntimeError):
            editor.create(content="y", author="u:b")

    def test_edit_on_empty_raises(self):
        editor = PageEditor(history=PageHistory(page_id="p1"))
        with pytest.raises(RuntimeError):
            editor.edit(content="x", author="u:a")

    def test_concurrent_edit_via_explicit_parent(self):
        editor = PageEditor(history=PageHistory(page_id="p1"))
        editor.create(content="a", author="u:alice")
        editor.edit(content="b", author="user:alice")
        # Concurrent edit forking from version 1.
        s3 = editor.edit(content="c", author="agent:bot", parent_version=1)
        assert s3.parent_version == 1
        # Conflict detected.
        assert len(editor.history.conflicts()) == 1

    def test_revert_to(self):
        editor = PageEditor(history=PageHistory(page_id="p1"))
        editor.create(content="a", author="u:a")
        editor.edit(content="b", author="u:a")
        editor.edit(content="c", author="u:a")
        rev = editor.revert_to(version=1, author="u:a")
        assert rev.content == "a"
        assert "reverted" in rev.note

    def test_revert_to_invalid_version(self):
        editor = PageEditor(history=PageHistory(page_id="p1"))
        editor.create(content="a", author="u:a")
        with pytest.raises(ValueError):
            editor.revert_to(version=99, author="u:a")

    def test_diff_between_versions(self):
        editor = PageEditor(history=PageHistory(page_id="p1"))
        editor.create(content="a\nb\nc", author="u:a")
        editor.edit(content="a\nb", author="u:a")
        d = editor.diff(from_version=1, to_version=2)
        assert d == "+0 -1"


class TestPage:
    def test_page_wraps_history(self):
        p = Page(page_id="p1")
        assert p.history.page_id == "p1"
        assert p.history.snapshots == []


# --- Integrations: external graph adapter -------------------------------


class _ForeignNode:
    """Simulates an external node with non-default attribute names."""

    def __init__(self, name: str, label: str = ""):
        self.name = name
        self.label = label


class _ForeignEdge:
    def __init__(self, src: str, dst: str):
        self.src_id = src
        self.dst_id = dst


class _ForeignGraph:
    def __init__(self, nodes, edges):
        self._nodes = nodes
        self._edges = edges

    def all_nodes(self):
        return self._nodes

    def all_edges(self):
        return self._edges

    def __contains__(self, node_id):
        return any(n.name == node_id for n in self._nodes)


class TestAdaptedNode:
    def test_wrap_default_attrs(self):
        class N:
            def __init__(self): self.id, self.title = "x", "X"
        adapted = AdaptedNode.wrap(N())
        assert adapted.id == "x"
        assert adapted.title == "X"

    def test_wrap_custom_attrs(self):
        n = _ForeignNode(name="y", label="Y label")
        adapted = AdaptedNode.wrap(n, id_attr="name", title_attr="label")
        assert adapted.id == "y"
        assert adapted.title == "Y label"

    def test_wrap_missing_id_raises(self):
        class N: pass
        with pytest.raises(AttributeError):
            AdaptedNode.wrap(N())


class TestAdaptedEdge:
    def test_wrap_default_attrs(self):
        class E:
            def __init__(self): self.src, self.dst = "a", "b"
        adapted = AdaptedEdge.wrap(E())
        assert adapted.src == "a"
        assert adapted.dst == "b"

    def test_wrap_custom_attrs(self):
        e = _ForeignEdge("a", "b")
        adapted = AdaptedEdge.wrap(e, src_attr="src_id", dst_attr="dst_id")
        assert adapted.src == "a"
        assert adapted.dst == "b"


class TestAdaptedDocument:
    def test_wrap_with_doc_id(self):
        class D:
            def __init__(self): self.doc_id, self.text = "d1", "hello"
        adapted = AdaptedDocument.wrap(D())
        assert adapted.doc_id == "d1"
        assert adapted.text == "hello"
        assert adapted.anchor_node_id is None

    def test_wrap_falls_back_to_id(self):
        class D:
            def __init__(self): self.id, self.text = "d1", "x"
        adapted = AdaptedDocument.wrap(D())
        assert adapted.doc_id == "d1"

    def test_wrap_with_anchor(self):
        class D:
            def __init__(self):
                self.doc_id, self.text, self.anchor_node_id = "d1", "x", "alice"
        adapted = AdaptedDocument.wrap(D())
        assert adapted.anchor_node_id == "alice"


class TestAdaptedGraph:
    def test_wrap_foreign_graph(self):
        g = _ForeignGraph(
            nodes=[_ForeignNode("a", "Alice"), _ForeignNode("b", "Bob")],
            edges=[_ForeignEdge("a", "b")],
        )
        adapted = adapt_graph(
            g,
            node_id_attr="name",
            node_title_attr="label",
            edge_src_attr="src_id",
            edge_dst_attr="dst_id",
        )
        node_ids = sorted(n.id for n in adapted.all_nodes())
        assert node_ids == ["a", "b"]
        edges = list(adapted.all_edges())
        assert edges[0].src == "a"
        assert edges[0].dst == "b"

    def test_contains_via_external(self):
        g = _ForeignGraph(
            nodes=[_ForeignNode("a")],
            edges=[],
        )
        adapted = adapt_graph(g, node_id_attr="name")
        assert "a" in adapted
        assert "x" not in adapted

    def test_skips_malformed_edges(self):
        # Edge missing src/dst should be silently skipped.
        class BadEdge: pass
        g = _ForeignGraph(
            nodes=[_ForeignNode("a"), _ForeignNode("b")],
            edges=[_ForeignEdge("a", "b"), BadEdge()],
        )
        adapted = adapt_graph(g, node_id_attr="name", edge_src_attr="src_id", edge_dst_attr="dst_id")
        edges = list(adapted.all_edges())
        # Only the valid edge survives.
        assert len(edges) == 1


class TestVerifyGraphProtocol:
    def test_simple_graph_satisfies(self):
        g = SimpleGraph.from_pairs([("a", "b")])
        ok, missing = verify_graph_protocol(g)
        assert ok is True
        assert missing == []

    def test_missing_methods(self):
        class Stub: pass
        ok, missing = verify_graph_protocol(Stub())
        assert ok is False
        assert "all_nodes()" in missing

    def test_node_missing_title(self):
        class N:
            def __init__(self): self.id = "x"
            # no title
        class G:
            def all_nodes(self): return [N()]
            def all_edges(self): return []
            def __contains__(self, x): return False
        ok, missing = verify_graph_protocol(G())
        assert ok is False
        assert "Node.title" in missing

    def test_edge_missing_dst(self):
        class N:
            def __init__(self): self.id, self.title = "x", "X"
        class E:
            def __init__(self): self.src = "x"
            # no dst
        class G:
            def all_nodes(self): return [N()]
            def all_edges(self): return [E()]
            def __contains__(self, x): return False
        ok, missing = verify_graph_protocol(G())
        assert ok is False
        assert "Edge.dst" in missing


class TestEndToEndAdaptedGraphWithHippoRAG:
    """Adapted graphs should drop into HippoRAGRetriever transparently."""

    def test_hipporag_consumes_adapted_graph(self):
        foreign = _ForeignGraph(
            nodes=[_ForeignNode("alice", "Alice"), _ForeignNode("bob", "Bob")],
            edges=[_ForeignEdge("alice", "bob")],
        )
        adapted = adapt_graph(
            foreign,
            node_id_attr="name", node_title_attr="label",
            edge_src_attr="src_id", edge_dst_attr="dst_id",
        )
        retriever = HippoRAGRetriever(graph=adapted)
        retriever.build_index([
            SimpleDocument(doc_id="d1", text="alice knows bob", anchor_node_id="alice"),
            SimpleDocument(doc_id="d2", text="unrelated", anchor_node_id=None),
        ])
        hits = retriever.retrieve("alice")
        assert len(hits) >= 1
        # The doc anchored at alice should rank highly.
        assert hits[0].document.doc_id == "d1"
