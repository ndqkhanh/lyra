"""Tests for lyra-memory-token."""
from lyra_memory_token import MemoryTier, MemoryTierRouter, TokenNativeIndex


class TestTokenNativeIndex:
    def test_index_and_retrieve(self):
        idx = TokenNativeIndex()
        idx.index("doc1", "Python list comprehensions are efficient")
        idx.index("doc2", "JavaScript arrow functions are concise")
        results = idx.retrieve("Python list", top_k=5)
        assert len(results) >= 1
        doc_id, score = results[0]
        assert doc_id == "doc1"

    def test_batch_index(self):
        idx = TokenNativeIndex()
        count = idx.index_batch({
            "d1": "Machine learning is a subset of AI",
            "d2": "Deep learning uses neural networks",
            "d3": "Natural language processing is a field",
        })
        assert count == 3
        assert idx.stats["documents"] == 3

    def test_remove(self):
        idx = TokenNativeIndex()
        idx.index("doc1", "Test document")
        assert idx.remove("doc1")
        assert not idx.remove("nonexistent")

    def test_retrieve_empty(self):
        idx = TokenNativeIndex()
        results = idx.retrieve("nothing", top_k=5)
        assert results == []


class TestMemoryTierRouter:
    def test_route_low_latency(self):
        router = MemoryTierRouter()
        tier = router.route("quick lookup", latency_budget_ms=30)
        assert tier == MemoryTier.TOKEN_NATIVE

    def test_route_entity(self):
        router = MemoryTierRouter()
        tier = router.route("entity relationship graph", latency_budget_ms=200, query_type="entity")
        assert tier == MemoryTier.GRAPH

    def test_route_default(self):
        router = MemoryTierRouter()
        tier = router.route("general semantic search", latency_budget_ms=200)
        assert tier == MemoryTier.VECTOR
