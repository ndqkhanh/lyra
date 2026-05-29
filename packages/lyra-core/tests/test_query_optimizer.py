"""
Tests for Query Optimization System
"""

import pytest
from lyra_core.query_optimizer import (
    QueryType,
    QueryPlan,
    QueryResult,
    QueryOptimizer,
    QueryExecutor,
    QueryCache
)


class TestQueryPlan:
    """Test QueryPlan"""

    def test_initialization(self):
        """Test plan initialization"""
        plan = QueryPlan(
            query_type=QueryType.EXACT_MATCH,
            estimated_cost=1.0
        )
        assert plan.query_type == QueryType.EXACT_MATCH
        assert plan.estimated_cost == 1.0

    def test_add_optimization(self):
        """Test adding optimizations"""
        plan = QueryPlan(
            query_type=QueryType.EXACT_MATCH,
            estimated_cost=1.0
        )
        plan.add_optimization("index_lookup")
        assert "index_lookup" in plan.optimizations


class TestQueryOptimizer:
    """Test QueryOptimizer"""

    def test_initialization(self):
        """Test optimizer initialization"""
        optimizer = QueryOptimizer()
        assert len(optimizer.indexes) == 0

    def test_create_index(self):
        """Test index creation"""
        optimizer = QueryOptimizer()
        optimizer.create_index("test_index", ["key1", "key2"])
        assert "test_index" in optimizer.indexes
        assert len(optimizer.indexes["test_index"]) == 2

    def test_analyze_query(self):
        """Test query analysis"""
        optimizer = QueryOptimizer()
        plan = optimizer.analyze_query("test", QueryType.EXACT_MATCH)
        assert plan.query_type == QueryType.EXACT_MATCH
        assert plan.estimated_cost > 0

    def test_index_optimization(self):
        """Test index-based optimization"""
        optimizer = QueryOptimizer()
        optimizer.create_index("test_index", ["test_key"])

        plan = optimizer.optimize_query("test_key", QueryType.EXACT_MATCH)
        assert plan.use_index is True
        assert plan.index_name == "test_index"

    def test_record_execution(self):
        """Test execution recording"""
        optimizer = QueryOptimizer()
        optimizer.record_execution("query1", 0.5)
        optimizer.record_execution("query1", 0.3)

        assert "query1" in optimizer.query_stats
        assert len(optimizer.query_stats["query1"]) == 2

    def test_get_slow_queries(self):
        """Test slow query detection"""
        optimizer = QueryOptimizer()
        optimizer.record_execution("fast", 0.1)
        optimizer.record_execution("slow", 2.0)

        slow = optimizer.get_slow_queries(threshold=1.0)
        assert len(slow) == 1
        assert slow[0][0] == "slow"


class TestQueryExecutor:
    """Test QueryExecutor"""

    def test_initialization(self):
        """Test executor initialization"""
        executor = QueryExecutor()
        assert len(executor.data) == 0

    def test_add_data(self):
        """Test adding data"""
        executor = QueryExecutor()
        data = [{"key": "test1"}, {"key": "test2"}]
        executor.add_data(data)
        assert len(executor.data) == 2

    def test_exact_match_query(self):
        """Test exact match query"""
        executor = QueryExecutor()
        executor.add_data([
            {"key": "test1", "value": "value1"},
            {"key": "test2", "value": "value2"}
        ])

        result = executor.execute("test1", QueryType.EXACT_MATCH)
        assert len(result.results) == 1
        assert result.results[0]["key"] == "test1"

    def test_fuzzy_match_query(self):
        """Test fuzzy match query"""
        executor = QueryExecutor()
        executor.add_data([
            {"key": "test123", "value": "value1"},
            {"key": "other", "value": "value2"}
        ])

        result = executor.execute("test", QueryType.FUZZY_MATCH)
        assert len(result.results) == 1
        assert "test" in result.results[0]["key"]

    def test_index_creation(self):
        """Test index creation"""
        executor = QueryExecutor()
        executor.add_data([
            {"key": "test1"},
            {"key": "test2"}
        ])
        executor.create_index("test_index")

        assert "test_index" in executor.optimizer.indexes

    def test_indexed_query(self):
        """Test query with index"""
        executor = QueryExecutor()
        executor.add_data([{"key": "test1"}])
        executor.create_index("test_index")

        result = executor.execute("test1", QueryType.EXACT_MATCH)
        assert result.plan.use_index is True


class TestQueryCache:
    """Test QueryCache"""

    def test_initialization(self):
        """Test cache initialization"""
        cache = QueryCache(max_size=100)
        assert cache.max_size == 100
        assert len(cache.cache) == 0

    def test_put_and_get(self):
        """Test caching"""
        cache = QueryCache()
        result = QueryResult(
            results=[{"key": "test"}],
            execution_time=0.1,
            plan=QueryPlan(QueryType.EXACT_MATCH, 1.0)
        )

        cache.put("query1", result)
        cached = cache.get("query1")

        assert cached is not None
        assert cached.cache_hit is True

    def test_cache_miss(self):
        """Test cache miss"""
        cache = QueryCache()
        result = cache.get("nonexistent")
        assert result is None
        assert cache.misses == 1

    def test_cache_eviction(self):
        """Test cache eviction"""
        cache = QueryCache(max_size=2)

        for i in range(3):
            result = QueryResult(
                results=[],
                execution_time=0.1,
                plan=QueryPlan(QueryType.EXACT_MATCH, 1.0)
            )
            cache.put(f"query{i}", result)

        assert len(cache.cache) == 2

    def test_get_stats(self):
        """Test statistics"""
        cache = QueryCache()
        result = QueryResult(
            results=[],
            execution_time=0.1,
            plan=QueryPlan(QueryType.EXACT_MATCH, 1.0)
        )

        cache.put("query1", result)
        cache.get("query1")  # Hit
        cache.get("query2")  # Miss

        stats = cache.get_stats()
        assert stats['hits'] == 1
        assert stats['misses'] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
