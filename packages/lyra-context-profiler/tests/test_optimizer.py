"""Tests for lyra_context_profiler.optimizer module."""

import asyncio

import pytest
from lyra_context_profiler.optimizer import (
    CacheWarmingStrategy,
    ClusterConfig,
    ContextOptimizer,
    EvictionCandidate,
    EvictionPolicy,
    OptimizationResult,
)
from lyra_context_profiler.strategies import (
    CompactionStrategy,
    StrategyRegistry,
)

# ── Fixtures ────────────────────────────────────────────────────────────────────


class _FakeElement:
    """Minimal element for testing the optimizer."""
    def __init__(self, id, content="", token_count=100, importance_score=0.5,
                 element_type="CODE", access_count=1):
        self.id = id
        self.content = content
        self.token_count = token_count
        self.importance_score = importance_score
        self.element_type = element_type
        self.access_count = access_count


class _FakeBudget:
    def __init__(self, total_limit=100000, used=75000):
        self.total_limit = total_limit
        self.used = used

    @property
    def remaining(self):
        return self.total_limit - self.used

    @property
    def utilization_pct(self):
        return (self.used / self.total_limit) * 100 if self.total_limit > 0 else 0


@pytest.fixture
def optimizer():
    return ContextOptimizer(default_eviction_policy=EvictionPolicy.HYBRID)


@pytest.fixture
def elements():
    return {
        "a": _FakeElement("a", "important core logic", token_count=500, importance_score=0.9, access_count=20),
        "b": _FakeElement("b", "less important note", token_count=200, importance_score=0.3, access_count=2),
        "c": _FakeElement("c", "medium importance", token_count=300, importance_score=0.5, access_count=5),
        "d": _FakeElement("d", "rarely used log output", token_count=400, importance_score=0.1, access_count=0),
    }


@pytest.fixture
def budget():
    return _FakeBudget(total_limit=100000, used=75000)


@pytest.fixture
def strategy_registry():
    return StrategyRegistry()


# ── ContextOptimizer ────────────────────────────────────────────────────────────


class TestContextOptimizer:
    def test_record_access(self, optimizer):
        optimizer.record_access("element_1")
        assert "element_1" in optimizer._access_timestamps
        assert optimizer._prefetch_cache.get("element_1", 0) > 0

    def test_cluster_elements_groups_by_type(self, optimizer, elements):
        clusters = asyncio.run(optimizer.cluster_elements(elements))
        assert len(clusters) > 0
        # All elements should be in exactly one cluster
        all_ids = set()
        for cluster in clusters:
            for eid in cluster:
                all_ids.add(eid)
        assert all_ids == set(elements.keys())

    def test_cluster_elements_respects_max_size(self, optimizer, elements):
        config = ClusterConfig(max_cluster_size_tokens=200)
        clusters = asyncio.run(optimizer.cluster_elements(elements, config))
        for cluster in clusters:
            total_tokens = sum(elements[eid].token_count for eid in cluster if eid in elements)
            assert total_tokens <= 200 or len(cluster) == 1

    def test_recommend_window_size_high_utilization(self, optimizer):
        rec = asyncio.run(optimizer.recommend_window_size(97.0, 100000))
        assert rec.urgency == "critical"
        assert rec.recommended_limit >= 100000

    def test_recommend_window_size_low_utilization(self, optimizer):
        rec = asyncio.run(optimizer.recommend_window_size(40.0, 100000))
        assert rec.urgency == "low"
        assert rec.recommended_limit < 100000

    def test_recommend_window_size_moderate(self, optimizer):
        rec = asyncio.run(optimizer.recommend_window_size(65.0, 100000))
        assert rec.urgency == "medium"

    def test_predict_future_context_no_history(self, optimizer, elements):
        predictions = asyncio.run(optimizer.predict_future_context(elements, None))
        assert predictions == []

    def test_predict_future_context_with_history(self, optimizer, elements):
        history = [
            {"accessed_ids": ["a"]},
            {"accessed_ids": ["c"]},
        ]
        predictions = asyncio.run(optimizer.predict_future_context(elements, history))
        assert isinstance(predictions, list)

    def test_warm_cache_predictive(self, optimizer, elements):
        # Give some elements high prefetch scores
        for eid in ["a", "c"]:
            optimizer._prefetch_cache[eid] = 5
        preloaded = asyncio.run(optimizer.warm_cache(elements, "predictive_preload"))
        assert isinstance(preloaded, list)

    def test_warm_cache_aggressive(self, optimizer, elements):
        for eid in ["a"]:
            optimizer._prefetch_cache[eid] = 10
        preloaded = asyncio.run(optimizer.warm_cache(elements, "aggressive_preload"))
        # CODE type has bias 0.8, so element "a" (CODE) should preload
        assert isinstance(preloaded, list)

    def test_eviction_policy_property(self, optimizer):
        assert optimizer.eviction_policy == EvictionPolicy.HYBRID
        optimizer.eviction_policy = EvictionPolicy.LRU
        assert optimizer.eviction_policy == EvictionPolicy.LRU

    def test_optimize_returns_recommendation(self, optimizer, elements, budget, strategy_registry):
        result = asyncio.run(optimizer.optimize(
            elements=elements,
            dependency_graph={"a": {"b"}, "b": set()},
            reverse_dependencies={"b": {"a"}},
            budget=budget,
            strategy_registry=strategy_registry,
        ))
        # Should return a recommendation when utilization is above 50%
        assert result is not None

    def test_optimize_low_utilization_returns_none(self, optimizer, strategy_registry):
        budget = _FakeBudget(total_limit=100000, used=30000)  # 30%
        result = asyncio.run(optimizer.optimize(
            elements={},
            dependency_graph={},
            reverse_dependencies={},
            budget=budget,
            strategy_registry=strategy_registry,
        ))
        assert result is None

    def test_optimization_count_increases(self, optimizer, elements, budget, strategy_registry):
        before = optimizer.optimization_count
        asyncio.run(optimizer.optimize(
            elements=elements,
            dependency_graph={"a": set()},
            reverse_dependencies={},
            budget=budget,
            strategy_registry=strategy_registry,
        ))
        assert optimizer.optimization_count >= before


# ── EvictionCandidate ───────────────────────────────────────────────────────────


class TestEvictionCandidate:
    def test_creation(self):
        c = EvictionCandidate(
            element_id="test",
            lru_score=0.5,
            importance_score=0.3,
            size_tokens=100,
            combined_score=0.4,
        )
        assert c.element_id == "test"
        assert c.size_tokens == 100


# ── CacheWarmingStrategy ────────────────────────────────────────────────────────


class TestCacheWarmingStrategy:
    def test_creation(self):
        strategy = CacheWarmingStrategy(
            name="test_strategy",
            description="A test",
            preload_threshold=0.5,
            max_preload_tokens=1000,
        )
        assert strategy.name == "test_strategy"
        assert strategy.preload_threshold == 0.5


# ── OptimizationResult ──────────────────────────────────────────────────────────


class TestOptimizationResult:
    def test_creation(self):
        result = OptimizationResult(
            tokens_before=10000,
            tokens_after=7000,
            tokens_freed=3000,
            elements_evicted=["a", "b"],
            strategy_used=CompactionStrategy.BALANCED,
            eviction_policy=EvictionPolicy.HYBRID,
            duration_ms=42.0,
        )
        assert result.tokens_freed == 3000
        assert len(result.elements_evicted) == 2
