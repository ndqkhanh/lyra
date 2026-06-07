"""Tests for src/ingestion/sema_rag.py and graph_rag.py."""
from __future__ import annotations

import pytest

from lyra.ingestion.pipeline import Chunk, Document, DocumentType, StubEmbedder, DictMemoryStore
from lyra.ingestion.sema_rag import (
    SEMARAGPipeline,
    StubSufficiencyJudge,
    StubQueryExpander,
    SufficiencyResult,
    HybridSearch,
    SearchResult,
    FreshnessManager,
)
from lyra.ingestion.graph_rag import (
    Entity,
    Relation,
    EntityGraph,
    GraphRAGExtractor,
)


# ---------------------------------------------------------------------------
# SEMARAGPipeline
# ---------------------------------------------------------------------------


class TestStubSufficiencyJudge:
    def test_judge_empty_chunks(self):
        judge = StubSufficiencyJudge()
        score = judge.judge("test query", [])
        assert score == 0.0

    def test_judge_keyword_overlap(self):
        judge = StubSufficiencyJudge()
        chunks = [Chunk(doc_id="d1", index=0, text="machine learning model training")]
        score = judge.judge("model training", chunks)
        assert 0.0 < score <= 1.0

    def test_judge_no_overlap(self):
        judge = StubSufficiencyJudge()
        chunks = [Chunk(doc_id="d1", index=0, text="completely unrelated content here")]
        score = judge.judge("machine learning", chunks)
        assert score == 0.0


class TestStubQueryExpander:
    def test_expand_with_synonyms(self):
        expander = StubQueryExpander(synonyms={"ml": ["machine", "learning"]})
        expanded = expander.expand("ml")
        assert "machine" in expanded or "learning" in expanded

    def test_expand_no_synonyms(self):
        expander = StubQueryExpander()
        expanded = expander.expand("test query")
        assert "expanded" in expanded


class TestSEMARAGPipeline:
    def test_retrieve_empty_store(self):
        embedder = StubEmbedder(dimension=64)
        store = DictMemoryStore()
        pipeline = SEMARAGPipeline(embedder=embedder, store=store, max_rounds=1)
        result = pipeline.retrieve("test query")
        assert isinstance(result, SufficiencyResult)
        assert result.confidence == 0.0

    def test_retrieve_with_stored_chunks(self):
        embedder = StubEmbedder(dimension=64)
        store = DictMemoryStore()
        doc = Document(path="test.md", doc_type=DocumentType.MARKDOWN, content="machine learning model training data")
        from lyra.ingestion.pipeline import SimpleChunker
        chunks = SimpleChunker(chunk_size=1000).chunk(doc)
        store.store(chunks)

        pipeline = SEMARAGPipeline(embedder=embedder, store=store, threshold=0.1)
        result = pipeline.retrieve("machine learning")
        assert len(result.chunks) > 0
        assert result.rounds >= 1

    def test_sufficiency_threshold_stops_early(self):
        embedder = StubEmbedder(dimension=64)
        store = DictMemoryStore()
        doc = Document(path="test.md", doc_type=DocumentType.MARKDOWN, content="exact match query content")
        from lyra.ingestion.pipeline import SimpleChunker
        chunks = SimpleChunker(chunk_size=1000).chunk(doc)
        store.store(chunks)

        pipeline = SEMARAGPipeline(embedder=embedder, store=store, threshold=0.9, max_rounds=5)
        result = pipeline.retrieve("exact match query content")
        assert result.rounds <= 3  # Should stop early due to threshold


# ---------------------------------------------------------------------------
# HybridSearch
# ---------------------------------------------------------------------------


class TestHybridSearch:
    def test_weight_validation(self):
        with pytest.raises(ValueError):
            HybridSearch(vector_weight=1.0, keyword_weight=1.0, graph_weight=1.0)

    def test_no_backends_returns_empty(self):
        hs = HybridSearch()
        results = hs.search("test")
        assert results == []

    def test_vector_only_search(self):
        hs = HybridSearch(vector_weight=1.0, keyword_weight=0.0, graph_weight=0.0)

        def vector_fn(q, k):
            return [SearchResult(chunk_id="v1", score=0.9, text="vec result", sources={"vector"})]

        hs.set_vector_backend(vector_fn)
        results = hs.search("test")
        assert len(results) == 1
        assert results[0].chunk_id == "v1"
        assert results[0].score == 0.9

    def test_fused_search(self):
        hs = HybridSearch(vector_weight=0.5, keyword_weight=0.5, graph_weight=0.0)

        def vector_fn(q, k):
            return [SearchResult(chunk_id="v1", score=0.9, text="vec", sources={"vector"})]

        def keyword_fn(q, k):
            return [SearchResult(chunk_id="k1", score=0.8, text="kw", sources={"keyword"})]

        hs.set_vector_backend(vector_fn)
        hs.set_keyword_backend(keyword_fn)
        results = hs.search("test")
        assert len(results) == 2


# ---------------------------------------------------------------------------
# FreshnessManager
# ---------------------------------------------------------------------------


class TestFreshnessManager:
    def test_track_and_check_fresh(self):
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False) as f:
            f.write("content")
            tmp_path = f.name

        mgr = FreshnessManager(max_age_days=30)
        entry = mgr.track("doc1", tmp_path)
        assert entry.doc_id == "doc1"
        assert not mgr.check_stale("doc1")

    def test_check_stale_unknown_raises(self):
        mgr = FreshnessManager()
        with pytest.raises(KeyError):
            mgr.check_stale("unknown")

    def test_list_stale_empty(self):
        mgr = FreshnessManager()
        assert mgr.list_stale() == []

    def test_mark_fresh(self):
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False) as f:
            f.write("content")
            tmp_path = f.name

        mgr = FreshnessManager(max_age_days=0)
        mgr.track("doc1", tmp_path)
        mgr.check_stale("doc1")
        mgr.mark_fresh("doc1")
        entry = mgr.get_freshness("doc1")
        assert entry is not None
        assert not entry.is_stale

    def test_remove(self):
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False) as f:
            f.write("content")
            tmp_path = f.name

        mgr = FreshnessManager()
        mgr.track("doc1", tmp_path)
        assert mgr.remove("doc1") is True
        assert mgr.remove("nonexistent") is False

    def test_get_freshness_unknown(self):
        mgr = FreshnessManager()
        assert mgr.get_freshness("unknown") is None

    def test_all_freshness(self):
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False) as f:
            f.write("content")
            tmp_path = f.name

        mgr = FreshnessManager()
        mgr.track("d1", tmp_path)
        mgr.track("d2", tmp_path)
        assert len(mgr.all_freshness()) == 2


# ---------------------------------------------------------------------------
# GraphRAGExtractor
# ---------------------------------------------------------------------------


class TestGraphRAGExtractor:
    def test_extract_returns_entity_graph(self):
        extractor = GraphRAGExtractor()
        graph = extractor.extract("Alice works at Acme Corp. Bob uses Python.")
        assert isinstance(graph, EntityGraph)
        assert graph.entity_count() > 0

    def test_extract_from_document(self):
        extractor = GraphRAGExtractor()
        doc = Document(path="test.md", doc_type=DocumentType.MARKDOWN, content="Alice works at Acme Corp.")
        graph = extractor.extract_from_document(doc)
        assert graph.source_doc_id == doc.doc_id

    def test_extract_batch(self):
        extractor = GraphRAGExtractor()
        graphs = extractor.extract_batch(["Alice works at Acme.", "Bob uses Python."])
        assert len(graphs) == 2

    def test_entity_graph_merge(self):
        g1 = EntityGraph(
            entities=[Entity(name="Alice", type="person")],
            relations=[Relation(source="Alice", target="Acme", relation_type="works_at")],
            source_doc_id="doc1",
        )
        g2 = EntityGraph(
            entities=[Entity(name="Bob", type="person")],
            relations=[Relation(source="Bob", target="Python", relation_type="uses")],
            source_doc_id="doc2",
        )
        g1.merge(g2)
        assert g1.entity_count() == 2
        assert g1.relation_count() == 2

    def test_get_relations(self):
        graph = EntityGraph(
            entities=[Entity(name="A", type="concept"), Entity(name="B", type="concept")],
            relations=[
                Relation(source="A", target="B", relation_type="depends_on"),
            ],
        )
        rels = graph.get_relations("A")
        assert len(rels) == 1
        assert rels[0].relation_type == "depends_on"
