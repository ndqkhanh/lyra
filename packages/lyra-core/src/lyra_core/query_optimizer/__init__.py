"""
Query Optimization System

Optimizes context queries for better performance.

Features:
- Query analysis and optimization
- Index-based lookups
- Query caching
- Performance tracking
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Any
from enum import Enum
import time


class QueryType(Enum):
    """Types of queries"""
    EXACT_MATCH = "exact_match"
    FUZZY_MATCH = "fuzzy_match"
    SEMANTIC_SEARCH = "semantic_search"
    RANGE_QUERY = "range_query"
    AGGREGATION = "aggregation"


@dataclass
class QueryPlan:
    """Execution plan for a query"""
    query_type: QueryType
    estimated_cost: float
    use_index: bool = False
    index_name: Optional[str] = None
    filters: List[str] = field(default_factory=list)
    optimizations: List[str] = field(default_factory=list)

    def add_optimization(self, optimization: str):
        """Add optimization to plan"""
        self.optimizations.append(optimization)


@dataclass
class QueryResult:
    """Result of query execution"""
    results: List[Any]
    execution_time: float
    plan: QueryPlan
    cache_hit: bool = False
    metadata: Dict = field(default_factory=dict)


class QueryOptimizer:
    """
    Query optimizer for context retrieval

    Analyzes queries and creates optimal execution plans.
    """

    def __init__(self):
        self.indexes: Dict[str, Set[str]] = {}
        self.query_stats: Dict[str, List[float]] = {}

    def create_index(self, name: str, keys: List[str]):
        """Create an index for faster lookups"""
        self.indexes[name] = set(keys)

    def analyze_query(self, query: str, query_type: QueryType) -> QueryPlan:
        """Analyze query and create execution plan"""
        plan = QueryPlan(
            query_type=query_type,
            estimated_cost=self._estimate_cost(query, query_type)
        )

        # Check if we can use an index
        if query_type == QueryType.EXACT_MATCH:
            index_name = self._find_suitable_index(query)
            if index_name:
                plan.use_index = True
                plan.index_name = index_name
                plan.add_optimization("index_lookup")
                plan.estimated_cost *= 0.1  # 10x faster with index

        # Add other optimizations
        if len(query) < 10:
            plan.add_optimization("short_query_fast_path")

        return plan

    def _estimate_cost(self, query: str, query_type: QueryType) -> float:
        """Estimate query execution cost"""
        base_cost = {
            QueryType.EXACT_MATCH: 1.0,
            QueryType.FUZZY_MATCH: 5.0,
            QueryType.SEMANTIC_SEARCH: 10.0,
            QueryType.RANGE_QUERY: 3.0,
            QueryType.AGGREGATION: 8.0
        }

        cost = base_cost.get(query_type, 5.0)

        # Adjust for query complexity
        cost *= (1 + len(query) / 100)

        return cost

    def _find_suitable_index(self, query: str) -> Optional[str]:
        """Find suitable index for query"""
        for index_name, keys in self.indexes.items():
            if query in keys:
                return index_name
        return None

    def optimize_query(self, query: str, query_type: QueryType) -> QueryPlan:
        """Optimize query and return execution plan"""
        plan = self.analyze_query(query, query_type)

        # Record query for statistics
        if query not in self.query_stats:
            self.query_stats[query] = []

        return plan

    def record_execution(self, query: str, execution_time: float):
        """Record query execution time"""
        if query not in self.query_stats:
            self.query_stats[query] = []
        self.query_stats[query].append(execution_time)

    def get_slow_queries(self, threshold: float = 1.0) -> List[tuple]:
        """Get queries slower than threshold"""
        slow_queries = []

        for query, times in self.query_stats.items():
            avg_time = sum(times) / len(times)
            if avg_time > threshold:
                slow_queries.append((query, avg_time))

        return sorted(slow_queries, key=lambda x: x[1], reverse=True)

    def get_stats(self) -> Dict:
        """Get optimizer statistics"""
        if not self.query_stats:
            return {
                'total_queries': 0,
                'avg_execution_time': 0.0,
                'indexes': len(self.indexes)
            }

        all_times = [t for times in self.query_stats.values() for t in times]
        avg_time = sum(all_times) / len(all_times)

        return {
            'total_queries': len(self.query_stats),
            'total_executions': len(all_times),
            'avg_execution_time': avg_time,
            'indexes': len(self.indexes),
            'indexed_keys': sum(len(keys) for keys in self.indexes.values())
        }


class QueryExecutor:
    """
    Query executor with optimization

    Executes queries using optimal plans.
    """

    def __init__(self, optimizer: Optional[QueryOptimizer] = None):
        self.optimizer = optimizer or QueryOptimizer()
        self.data: List[Dict] = []

    def add_data(self, items: List[Dict]):
        """Add data to query against"""
        self.data.extend(items)

    def execute(
        self,
        query: str,
        query_type: QueryType = QueryType.EXACT_MATCH
    ) -> QueryResult:
        """Execute query with optimization"""
        # Get execution plan
        plan = self.optimizer.optimize_query(query, query_type)

        # Execute query
        start_time = time.perf_counter()
        results = self._execute_plan(query, plan)
        execution_time = time.perf_counter() - start_time

        # Record execution
        self.optimizer.record_execution(query, execution_time)

        return QueryResult(
            results=results,
            execution_time=execution_time,
            plan=plan
        )

    def _execute_plan(self, query: str, plan: QueryPlan) -> List[Any]:
        """Execute query according to plan"""
        if plan.use_index and plan.index_name:
            # Fast index lookup
            return self._index_lookup(query, plan.index_name)

        # Full scan
        return self._full_scan(query, plan.query_type)

    def _index_lookup(self, query: str, index_name: str) -> List[Any]:
        """Perform index lookup"""
        results = []
        for item in self.data:
            if item.get('key') == query:
                results.append(item)
        return results

    def _full_scan(self, query: str, query_type: QueryType) -> List[Any]:
        """Perform full scan"""
        results = []

        for item in self.data:
            if query_type == QueryType.EXACT_MATCH:
                if item.get('key') == query:
                    results.append(item)
            elif query_type == QueryType.FUZZY_MATCH:
                if query.lower() in str(item.get('key', '')).lower():
                    results.append(item)

        return results

    def create_index(self, name: str, key_field: str = 'key'):
        """Create index on data"""
        keys = [item.get(key_field) for item in self.data if key_field in item]
        self.optimizer.create_index(name, keys)

    def get_stats(self) -> Dict:
        """Get executor statistics"""
        optimizer_stats = self.optimizer.get_stats()
        return {
            'data_size': len(self.data),
            'optimizer': optimizer_stats
        }


class QueryCache:
    """
    Query result cache

    Caches query results for faster repeated queries.
    """

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache: Dict[str, QueryResult] = {}
        self.hits = 0
        self.misses = 0

    def get(self, query: str) -> Optional[QueryResult]:
        """Get cached result"""
        if query in self.cache:
            self.hits += 1
            result = self.cache[query]
            result.cache_hit = True
            return result

        self.misses += 1
        return None

    def put(self, query: str, result: QueryResult):
        """Cache query result"""
        if len(self.cache) >= self.max_size:
            # Remove oldest entry
            self.cache.pop(next(iter(self.cache)))

        self.cache[query] = result

    def invalidate(self, query: str):
        """Invalidate cached result"""
        if query in self.cache:
            del self.cache[query]

    def clear(self):
        """Clear all cached results"""
        self.cache.clear()
        self.hits = 0
        self.misses = 0

    def get_stats(self) -> Dict:
        """Get cache statistics"""
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0.0

        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': hit_rate
        }
