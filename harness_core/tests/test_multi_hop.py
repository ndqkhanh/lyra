"""Tests for harness_core.multi_hop — HippoRAG-2 + decomposition cache."""
from __future__ import annotations

import pytest

from harness_core.multi_hop import (
    DecompositionCache,
    HashEmbedder,
    HippoRAGRetriever,
    PersonalizedPageRank,
    SimpleDocument,
    SimpleEdge,
    SimpleGraph,
    SimpleNode,
    TitleEntityExtractor,
    cosine,
    graph_to_adjacency,
    normalize_question,
)


class TestSimpleGraph:
    def test_add_and_query(self):
        g = SimpleGraph()
        g.add_node(SimpleNode(id="a", title="Alice"))
        g.add_node(SimpleNode(id="b", title="Bob"))
        g.add_edge(SimpleEdge(src="a", dst="b"))
        assert "a" in g
        assert "x" not in g
        assert len(list(g.all_nodes())) == 2
        assert len(list(g.all_edges())) == 1

    def test_from_pairs_auto_creates_nodes(self):
        g = SimpleGraph.from_pairs([("a", "b"), ("b", "c")])
        assert "a" in g and "b" in g and "c" in g
        assert len(list(g.all_edges())) == 2

    def test_from_pairs_with_titles(self):
        g = SimpleGraph.from_pairs([("a", "b")], titles={"a": "Alice", "b": "Bob"})
        nodes = {n.id: n.title for n in g.all_nodes()}
        assert nodes == {"a": "Alice", "b": "Bob"}


class TestCosine:
    def test_orthogonal(self):
        assert cosine([1.0, 0.0], [0.0, 1.0]) == 0.0

    def test_identical(self):
        assert cosine([0.6, 0.8], [0.6, 0.8]) == pytest.approx(1.0)

    def test_empty(self):
        assert cosine([], []) == 0.0
        assert cosine([1.0], []) == 0.0

    def test_mismatched_dim(self):
        assert cosine([1.0, 0.0], [1.0]) == 0.0


class TestHashEmbedder:
    def test_deterministic(self):
        emb = HashEmbedder(dim=64)
        a = emb.embed_batch(["hello world"])[0]
        b = emb.embed_batch(["hello world"])[0]
        assert a == b

    def test_different_inputs_differ(self):
        emb = HashEmbedder(dim=64)
        [a, b] = emb.embed_batch(["hello", "goodbye"])
        assert a != b

    def test_normalized(self):
        emb = HashEmbedder(dim=64)
        v = emb.embed_batch(["test text"])[0]
        norm = sum(x * x for x in v) ** 0.5
        assert norm == pytest.approx(1.0, abs=1e-6) or norm == 0.0

    def test_empty_text(self):
        emb = HashEmbedder(dim=64)
        v = emb.embed_batch([""])[0]
        assert all(x == 0.0 for x in v)


class TestTitleEntityExtractor:
    def test_extract_by_title(self):
        g = SimpleGraph.from_pairs([("alice", "bob")], titles={"alice": "Alice Smith", "bob": "Bob Jones"})
        ext = TitleEntityExtractor()
        out = ext.extract("who is Alice", graph=g)
        assert "alice" in out

    def test_extract_by_id_when_no_title(self):
        g = SimpleGraph()
        g.add_node(SimpleNode(id="alice", title=""))
        out = TitleEntityExtractor().extract("find alice", graph=g)
        assert "alice" in out

    def test_empty_query(self):
        g = SimpleGraph.from_pairs([("a", "b")])
        assert TitleEntityExtractor().extract("", graph=g) == ()
        assert TitleEntityExtractor().extract("   ", graph=g) == ()


class TestPersonalizedPageRank:
    def test_simple_walk(self):
        adj = {"a": ["b"], "b": ["c"], "c": []}
        ppr = PersonalizedPageRank()
        ranks = ppr.walk(adjacency=adj, seeds=["a"])
        assert set(ranks.keys()) == {"a", "b", "c"}
        # The seed should rank highest under teleport.
        assert ranks["a"] >= ranks["c"]

    def test_empty_adj(self):
        assert PersonalizedPageRank().walk(adjacency={}, seeds=["x"]) == {}

    def test_no_seeds_uniform(self):
        adj = {"a": ["b"], "b": ["a"]}
        ranks = PersonalizedPageRank().walk(adjacency=adj, seeds=[])
        # Symmetric → ranks should be roughly equal.
        assert abs(ranks["a"] - ranks["b"]) < 1e-3

    def test_unmatched_seeds_fall_back(self):
        adj = {"a": [], "b": []}
        ranks = PersonalizedPageRank().walk(adjacency=adj, seeds=["nonexistent"])
        # Falls back to uniform; both nodes get non-zero rank.
        assert ranks["a"] > 0
        assert ranks["b"] > 0


class TestGraphToAdjacency:
    def test_symmetric(self):
        g = SimpleGraph.from_pairs([("a", "b")])
        adj = graph_to_adjacency(g)
        assert "b" in adj["a"]
        assert "a" in adj["b"]  # symmetric

    def test_drops_orphan_edges(self):
        g = SimpleGraph()
        g.add_node(SimpleNode(id="a"))
        g.add_edge(SimpleEdge(src="a", dst="orphan"))  # dst not in nodes
        adj = graph_to_adjacency(g)
        # Orphan edge dropped.
        assert "orphan" not in adj.get("a", [])


class TestHippoRAGRetriever:
    def _build(self):
        g = SimpleGraph.from_pairs(
            [("alice", "bob"), ("bob", "casablanca"), ("casablanca", "1942")],
            titles={"alice": "Alice", "bob": "Bob Smith", "casablanca": "Casablanca", "1942": "1942"},
        )
        retriever = HippoRAGRetriever(graph=g)
        retriever.build_index([
            SimpleDocument(doc_id="d1", text="alice is married to bob", anchor_node_id="alice"),
            SimpleDocument(doc_id="d2", text="bob directed the film casablanca", anchor_node_id="bob"),
            SimpleDocument(doc_id="d3", text="casablanca was released in 1942", anchor_node_id="casablanca"),
            SimpleDocument(doc_id="d4", text="unrelated coffee shop trivia", anchor_node_id=None),
        ])
        return retriever

    def test_retrieve_returns_top_k(self):
        r = self._build()
        hits = r.retrieve("casablanca director", top_k=2)
        assert len(hits) == 2

    def test_unrelated_ranks_lower(self):
        r = self._build()
        hits = r.retrieve("casablanca director", top_k=4)
        ids = [h.document.doc_id for h in hits]
        # The unrelated doc ('d4') should not be at the top.
        assert ids[0] in {"d2", "d3"}

    def test_empty_index_returns_empty(self):
        r = HippoRAGRetriever(graph=SimpleGraph())
        r.build_index([])
        assert r.retrieve("anything") == []

    def test_min_score_filter(self):
        r = self._build()
        hits = r.retrieve("casablanca", top_k=10, min_score=0.99)
        # Almost no docs reach 0.99; expect empty or very small.
        assert all(h.score >= 0.99 for h in hits)

    def test_alpha_pure_dense(self):
        g = SimpleGraph.from_pairs([("alice", "bob")])
        r = HippoRAGRetriever(graph=g, alpha=1.0)
        r.build_index([
            SimpleDocument(doc_id="d1", text="alice", anchor_node_id="alice"),
        ])
        hit = r.retrieve("alice", top_k=1)[0]
        # alpha=1.0 → score = cosine_score; ppr_score is informational only.
        assert hit.score == pytest.approx(hit.cosine_score, abs=1e-6)

    def test_alpha_pure_ppr(self):
        g = SimpleGraph.from_pairs([("alice", "bob")])
        r = HippoRAGRetriever(graph=g, alpha=0.0)
        r.build_index([
            SimpleDocument(doc_id="d1", text="alice", anchor_node_id="alice"),
        ])
        hit = r.retrieve("alice", top_k=1)[0]
        assert hit.score == pytest.approx(hit.ppr_score, abs=1e-6)


class TestNormalizeQuestion:
    def test_lowercase_strip(self):
        assert normalize_question("WHO directed Casablanca?") == "who directed casablanca"

    def test_punctuation_dropped(self):
        assert normalize_question("hello, world!") == "hello world"

    def test_whitespace_collapsed(self):
        assert normalize_question("  a   b  ") == "a b"

    def test_empty(self):
        assert normalize_question("") == ""
        assert normalize_question("   ") == ""


class TestDecompositionCache:
    def test_put_and_get(self):
        cache = DecompositionCache()
        cache.put(question="Who directed Casablanca?", sub_questions=("who is the director?",))
        entry = cache.get("WHO DIRECTED CASABLANCA?")  # different case → same normalised key
        assert entry is not None
        assert entry.sub_questions == ("who is the director?",)

    def test_miss(self):
        cache = DecompositionCache()
        assert cache.get("anything") is None

    def test_empty_sub_questions_rejected(self):
        with pytest.raises(ValueError):
            DecompositionCache().put(question="q", sub_questions=())

    def test_namespace_isolation(self):
        cache = DecompositionCache()
        cache.put(question="q", sub_questions=("a",), namespace="proj-A")
        cache.put(question="q", sub_questions=("b",), namespace="proj-B")
        assert cache.get("q", namespace="proj-A").sub_questions == ("a",)
        assert cache.get("q", namespace="proj-B").sub_questions == ("b",)

    def test_invalidate(self):
        cache = DecompositionCache()
        cache.put(question="q", sub_questions=("a",))
        assert cache.invalidate("q") is True
        assert cache.invalidate("q") is False  # already gone
        assert cache.get("q") is None

    def test_clear_namespace(self):
        cache = DecompositionCache()
        cache.put(question="q1", sub_questions=("a",), namespace="A")
        cache.put(question="q2", sub_questions=("b",), namespace="A")
        cache.put(question="q3", sub_questions=("c",), namespace="B")
        n = cache.clear_namespace("A")
        assert n == 2
        assert len(cache) == 1
        assert cache.get("q3", namespace="B") is not None

    def test_hit_count(self):
        cache = DecompositionCache()
        cache.put(question="q", sub_questions=("a",))
        for _ in range(3):
            cache.get("q")
        assert cache.stats()["hits"] == 3

    def test_lru_eviction(self):
        cache = DecompositionCache(max_entries=2)
        cache.put(question="q1", sub_questions=("a",))
        cache.put(question="q2", sub_questions=("b",))
        # Touch q1 so q2 becomes LRU.
        import time as _t
        _t.sleep(0.001)
        cache.get("q1")
        _t.sleep(0.001)
        cache.put(question="q3", sub_questions=("c",))
        assert len(cache) == 2
        assert cache.get("q2") is None  # evicted
        assert cache.get("q1") is not None
        assert cache.get("q3") is not None

    def test_ttl_expiry(self):
        cache = DecompositionCache(ttl_seconds=0.05)
        cache.put(question="q", sub_questions=("a",))
        assert cache.get("q") is not None
        import time as _t
        _t.sleep(0.07)
        assert cache.get("q") is None
        # And the entry should be evicted on the failed get.
        assert len(cache) == 0
