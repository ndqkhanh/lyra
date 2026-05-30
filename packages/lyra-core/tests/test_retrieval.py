"""
Tests for Context Retrieval System
"""

import pytest
import time
from lyra_core.retrieval import (
    RetrievalStrategy,
    RetrievalResult,
    RetrievalQuery,
    ContextRetriever,
    RankedRetriever,
    FilteredRetriever
)


class TestRetrievalQuery:
    """Test RetrievalQuery"""

    def test_initialization(self):
        """Test query initialization"""
        query = RetrievalQuery(
            query="test",
            strategy=RetrievalStrategy.HYBRID,
            limit=5
        )
        assert query.query == "test"
        assert query.limit == 5


class TestContextRetriever:
    """Test ContextRetriever"""

    def test_initialization(self):
        """Test retriever initialization"""
        retriever = ContextRetriever()
        assert len(retriever.items) == 0

    def test_add_item(self):
        """Test adding items"""
        retriever = ContextRetriever()
        retriever.add_item({"id": "1", "content": "test"})
        assert len(retriever.items) == 1

    def test_retrieve_by_recency(self):
        """Test recency-based retrieval"""
        retriever = ContextRetriever()
        retriever.add_item({"id": "1", "content": "old"})
        time.sleep(0.01)
        retriever.add_item({"id": "2", "content": "new"})

        query = RetrievalQuery(
            query="",
            strategy=RetrievalStrategy.RECENCY,
            limit=2
        )
        results = retriever.retrieve(query)

        assert len(results) == 2
        # Newer item should have higher score
        assert results[0].item["id"] == "2"

    def test_retrieve_by_frequency(self):
        """Test frequency-based retrieval"""
        retriever = ContextRetriever()
        retriever.add_item({"id": "1", "content": "frequent"})
        retriever.add_item({"id": "2", "content": "rare"})

        # Access first item multiple times
        retriever.record_access("1")
        retriever.record_access("1")
        retriever.record_access("1")

        query = RetrievalQuery(
            query="",
            strategy=RetrievalStrategy.FREQUENCY,
            limit=2
        )
        results = retriever.retrieve(query)

        assert len(results) == 2
        # More frequent item should have higher score
        assert results[0].item["id"] == "1"

    def test_retrieve_by_relevance(self):
        """Test relevance-based retrieval"""
        retriever = ContextRetriever()
        retriever.add_item({"id": "1", "content": "python programming"})
        retriever.add_item({"id": "2", "content": "java development"})

        query = RetrievalQuery(
            query="python",
            strategy=RetrievalStrategy.RELEVANCE,
            limit=2
        )
        results = retriever.retrieve(query)

        assert len(results) >= 1
        # Python item should be first
        assert "python" in results[0].item["content"].lower()

    def test_retrieve_hybrid(self):
        """Test hybrid retrieval"""
        retriever = ContextRetriever()
        retriever.add_item({"id": "1", "content": "test content"})

        query = RetrievalQuery(
            query="test",
            strategy=RetrievalStrategy.HYBRID,
            limit=1
        )
        results = retriever.retrieve(query)

        assert len(results) == 1
        assert results[0].strategy == RetrievalStrategy.HYBRID

    def test_filtering(self):
        """Test result filtering"""
        retriever = ContextRetriever()
        retriever.add_item({"id": "1", "type": "A", "content": "test"})
        retriever.add_item({"id": "2", "type": "B", "content": "test"})

        query = RetrievalQuery(
            query="test",
            strategy=RetrievalStrategy.RELEVANCE,
            filters={"type": "A"}
        )
        results = retriever.retrieve(query)

        assert len(results) == 1
        assert results[0].item["type"] == "A"

    def test_min_score_threshold(self):
        """Test minimum score threshold"""
        retriever = ContextRetriever()
        retriever.add_item({"id": "1", "content": "test"})

        query = RetrievalQuery(
            query="test",
            strategy=RetrievalStrategy.RELEVANCE,
            min_score=0.5
        )
        results = retriever.retrieve(query)

        # All results should have score >= 0.5
        assert all(r.score >= 0.5 for r in results)

    def test_record_access(self):
        """Test access recording"""
        retriever = ContextRetriever()
        retriever.add_item({"id": "1", "content": "test"})

        retriever.record_access("1")
        assert retriever.access_counts["1"] == 1

    def test_get_stats(self):
        """Test statistics"""
        retriever = ContextRetriever()
        retriever.add_item({"id": "1", "content": "test"})
        retriever.record_access("1")

        stats = retriever.get_stats()
        assert stats['total_items'] == 1
        assert stats['total_accesses'] == 1


class TestRankedRetriever:
    """Test RankedRetriever"""

    def test_initialization(self):
        """Test retriever initialization"""
        retriever = RankedRetriever()
        assert len(retriever.items) == 0

    def test_add_scoring_function(self):
        """Test adding scoring function"""
        retriever = RankedRetriever()

        def score_func(item):
            return item.get('score', 0.0)

        retriever.add_scoring_function(score_func)
        assert len(retriever.scoring_functions) == 1

    def test_retrieve_with_scoring(self):
        """Test retrieval with custom scoring"""
        retriever = RankedRetriever()
        retriever.add_item({"id": "1", "score": 0.5})
        retriever.add_item({"id": "2", "score": 0.9})

        def score_func(item):
            return item.get('score', 0.0)

        retriever.add_scoring_function(score_func)

        results = retriever.retrieve("", limit=2)
        assert len(results) == 2
        # Higher score should be first
        assert results[0].item["id"] == "2"

    def test_weighted_scoring(self):
        """Test weighted scoring"""
        retriever = RankedRetriever()
        retriever.add_item({"id": "1", "score1": 1.0, "score2": 0.0})

        retriever.add_scoring_function(lambda item: item.get('score1', 0.0))
        retriever.add_scoring_function(lambda item: item.get('score2', 0.0))

        results = retriever.retrieve("", weights=[0.8, 0.2])
        assert len(results) == 1


class TestFilteredRetriever:
    """Test FilteredRetriever"""

    def test_initialization(self):
        """Test retriever initialization"""
        retriever = FilteredRetriever()
        assert len(retriever.items) == 0

    def test_retrieve_with_filters(self):
        """Test filtered retrieval"""
        retriever = FilteredRetriever()
        retriever.add_item({"id": "1", "type": "A"})
        retriever.add_item({"id": "2", "type": "B"})

        results = retriever.retrieve(filters={"type": "A"})
        assert len(results) == 1
        assert results[0]["type"] == "A"

    def test_retrieve_with_sorting(self):
        """Test sorted retrieval"""
        retriever = FilteredRetriever()
        retriever.add_item({"id": "1", "score": 0.5})
        retriever.add_item({"id": "2", "score": 0.9})

        results = retriever.retrieve(sort_by="score", reverse=True)
        assert results[0]["score"] == 0.9

    def test_retrieve_with_predicate(self):
        """Test predicate-based retrieval"""
        retriever = FilteredRetriever()
        retriever.add_item({"id": "1", "value": 10})
        retriever.add_item({"id": "2", "value": 20})

        results = retriever.retrieve_with_predicate(
            lambda item: item.get('value', 0) > 15
        )
        assert len(results) == 1
        assert results[0]["id"] == "2"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
