"""
Tests for Memory Retrieval.
"""

import time

from lyra.memory.long_term_memory import LongTermMemory
from lyra.memory.memory_retrieval import (
    MemoryRetriever,
    RelevanceScorer,
    RetrievalResult,
    RetrievalStrategy,
)
from lyra.memory.memory_store import MemoryType


class TestRelevanceScorer:
    """Test RelevanceScorer class."""

    def test_scorer_creation(self):
        """Test creating a relevance scorer."""
        scorer = RelevanceScorer()

        assert scorer.importance_weight == 0.3
        assert scorer.recency_weight == 0.3
        assert scorer.frequency_weight == 0.2
        assert scorer.content_weight == 0.2

    def test_score_calculation(self):
        """Test calculating relevance score."""
        from lyra.memory.memory_store import Memory

        scorer = RelevanceScorer()
        memory = Memory(
            memory_id="test-1",
            content="Python programming",
            memory_type=MemoryType.SEMANTIC,
            timestamp=time.time(),
            importance=0.8,
        )

        score = scorer.score(memory, query="Python")

        assert 0.0 <= score <= 1.0

    def test_score_with_high_importance(self):
        """Test scoring with high importance."""
        from lyra.memory.memory_store import Memory

        scorer = RelevanceScorer(
            importance_weight=1.0, recency_weight=0.0, frequency_weight=0.0, content_weight=0.0
        )

        memory = Memory(
            memory_id="test-1",
            content="Test",
            memory_type=MemoryType.SEMANTIC,
            timestamp=time.time(),
            importance=0.9,
        )

        score = scorer.score(memory)

        assert score == 0.9

    def test_score_with_recency(self):
        """Test scoring with recency."""
        from lyra.memory.memory_store import Memory

        scorer = RelevanceScorer(
            importance_weight=0.0, recency_weight=1.0, frequency_weight=0.0, content_weight=0.0
        )

        recent = Memory("m1", "Test", MemoryType.SEMANTIC, time.time(), importance=0.5)
        old = Memory("m2", "Test", MemoryType.SEMANTIC, time.time() - 86400 * 30, importance=0.5)

        recent_score = scorer.score(recent)
        old_score = scorer.score(old)

        assert recent_score > old_score

    def test_score_with_frequency(self):
        """Test scoring with access frequency."""
        from lyra.memory.memory_store import Memory

        scorer = RelevanceScorer(
            importance_weight=0.0, recency_weight=0.0, frequency_weight=1.0, content_weight=0.0
        )

        frequent = Memory("m1", "Test", MemoryType.SEMANTIC, time.time(), importance=0.5)
        frequent.access_count = 10

        rare = Memory("m2", "Test", MemoryType.SEMANTIC, time.time(), importance=0.5)
        rare.access_count = 1

        frequent_score = scorer.score(frequent)
        rare_score = scorer.score(rare)

        assert frequent_score > rare_score

    def test_content_similarity(self):
        """Test content similarity calculation."""
        scorer = RelevanceScorer()

        similarity = scorer._calculate_content_similarity(
            "Python programming language", "Python language"
        )

        assert similarity > 0.0


class TestMemoryRetriever:
    """Test MemoryRetriever class."""

    def test_retriever_creation(self):
        """Test creating a memory retriever."""
        ltm = LongTermMemory()
        retriever = MemoryRetriever(ltm)

        assert retriever.default_strategy == RetrievalStrategy.HYBRID

    def test_retrieve_keyword(self):
        """Test keyword retrieval."""
        ltm = LongTermMemory()
        ltm.add("Python is great", MemoryType.SEMANTIC, importance=0.8)
        ltm.add("JavaScript is useful", MemoryType.SEMANTIC, importance=0.7)
        ltm.add("Python and JavaScript", MemoryType.SEMANTIC, importance=0.9)

        retriever = MemoryRetriever(ltm)
        results = retriever.retrieve("Python", strategy=RetrievalStrategy.KEYWORD)

        assert len(results) > 0
        assert all(isinstance(r, RetrievalResult) for r in results)

    def test_retrieve_with_limit(self):
        """Test retrieval with limit."""
        ltm = LongTermMemory()

        for i in range(10):
            ltm.add(f"Test memory {i}", MemoryType.SEMANTIC, importance=0.8)

        retriever = MemoryRetriever(ltm)
        results = retriever.retrieve("Test", limit=5)

        assert len(results) <= 5

    def test_retrieve_with_min_score(self):
        """Test retrieval with minimum score."""
        ltm = LongTermMemory()
        ltm.add("Relevant content", MemoryType.SEMANTIC, importance=0.9)
        ltm.add("Less relevant", MemoryType.SEMANTIC, importance=0.3)

        retriever = MemoryRetriever(ltm)
        results = retriever.retrieve("Relevant", min_score=0.5)

        assert all(r.score >= 0.5 for r in results)

    def test_retrieve_temporal(self):
        """Test temporal retrieval."""
        ltm = LongTermMemory()

        for i in range(5):
            ltm.add(f"Memory {i}", MemoryType.EPISODIC, importance=0.7)
            time.sleep(0.01)

        retriever = MemoryRetriever(ltm)
        results = retriever.retrieve("Memory", strategy=RetrievalStrategy.TEMPORAL, limit=3)

        assert len(results) <= 3

    def test_retrieve_importance(self):
        """Test importance-based retrieval."""
        ltm = LongTermMemory()
        ltm.add("High importance", MemoryType.SEMANTIC, importance=0.9)
        ltm.add("Medium importance", MemoryType.SEMANTIC, importance=0.6)
        ltm.add("Low importance", MemoryType.SEMANTIC, importance=0.3)

        retriever = MemoryRetriever(ltm)
        results = retriever.retrieve("importance", strategy=RetrievalStrategy.IMPORTANCE)

        # Should prioritize high importance
        if results:
            assert results[0].memory.importance >= 0.5

    def test_retrieve_hybrid(self):
        """Test hybrid retrieval."""
        ltm = LongTermMemory()

        ltm.add("Python programming", MemoryType.SEMANTIC, importance=0.8, tags=["python"])
        ltm.add("JavaScript coding", MemoryType.SEMANTIC, importance=0.7, tags=["javascript"])
        ltm.add(
            "Python and JavaScript",
            MemoryType.SEMANTIC,
            importance=0.9,
            tags=["python", "javascript"],
        )

        retriever = MemoryRetriever(ltm)
        results = retriever.retrieve("Python", strategy=RetrievalStrategy.HYBRID)

        assert len(results) > 0

    def test_retrieve_with_type_filter(self):
        """Test retrieval with type filter."""
        ltm = LongTermMemory()
        ltm.add("Episodic memory", MemoryType.EPISODIC, importance=0.8)
        ltm.add("Semantic memory", MemoryType.SEMANTIC, importance=0.8)

        retriever = MemoryRetriever(ltm)
        results = retriever.retrieve("memory", filters={"type": MemoryType.SEMANTIC})

        assert all(r.memory.memory_type == MemoryType.SEMANTIC for r in results)

    def test_retrieve_with_tags_filter(self):
        """Test retrieval with tags filter."""
        ltm = LongTermMemory()
        ltm.add("Test 1", MemoryType.SEMANTIC, tags=["tag1", "tag2"])
        ltm.add("Test 2", MemoryType.SEMANTIC, tags=["tag2", "tag3"])
        ltm.add("Test 3", MemoryType.SEMANTIC, tags=["tag3"])

        retriever = MemoryRetriever(ltm)
        results = retriever.retrieve(
            "Test", filters={"tags": ["tag1", "tag2"], "match_all_tags": False}
        )

        assert len(results) == 2

    def test_retrieve_with_time_range_filter(self):
        """Test retrieval with time range filter."""
        ltm = LongTermMemory()

        now = time.time()
        m1 = ltm.add("Old", MemoryType.EPISODIC)
        m1.timestamp = now - 200

        m2 = ltm.add("Recent", MemoryType.EPISODIC)
        m2.timestamp = now - 50

        # Rebuild index after modifying timestamps
        ltm._rebuild_index()

        retriever = MemoryRetriever(ltm)
        results = retriever.retrieve("memory", filters={"time_range": {"start": now - 100}})

        assert len(results) == 1

    def test_retrieve_similar(self):
        """Test retrieving similar memories."""
        ltm = LongTermMemory()

        m1 = ltm.add(
            "Python programming language", MemoryType.SEMANTIC, tags=["python", "programming"]
        )
        ltm.add("Python web development", MemoryType.SEMANTIC, tags=["python", "web"])
        ltm.add("JavaScript programming", MemoryType.SEMANTIC, tags=["javascript", "programming"])

        retriever = MemoryRetriever(ltm)
        results = retriever.retrieve_similar(m1, limit=2)

        # Should not include the reference memory itself
        assert all(r.memory.memory_id != m1.memory_id for r in results)
        assert len(results) <= 2

    def test_get_statistics(self):
        """Test getting retriever statistics."""
        ltm = LongTermMemory()
        retriever = MemoryRetriever(ltm, default_strategy=RetrievalStrategy.KEYWORD)

        stats = retriever.get_statistics()

        assert stats["default_strategy"] == "keyword"
        assert "scorer_weights" in stats


class TestRetrievalResult:
    """Test RetrievalResult class."""

    def test_result_creation(self):
        """Test creating a retrieval result."""
        from lyra.memory.memory_store import Memory

        memory = Memory(
            memory_id="test-1",
            content="Test",
            memory_type=MemoryType.SEMANTIC,
            timestamp=time.time(),
        )

        result = RetrievalResult(
            memory=memory,
            score=0.85,
            strategy="keyword",
        )

        assert result.memory == memory
        assert result.score == 0.85
        assert result.strategy == "keyword"
        assert result.metadata == {}

    def test_result_with_metadata(self):
        """Test creating a result with metadata."""
        from lyra.memory.memory_store import Memory

        memory = Memory(
            memory_id="test-1",
            content="Test",
            memory_type=MemoryType.SEMANTIC,
            timestamp=time.time(),
        )

        result = RetrievalResult(
            memory=memory,
            score=0.85,
            strategy="hybrid",
            metadata={"source": "test"},
        )

        assert result.metadata["source"] == "test"
