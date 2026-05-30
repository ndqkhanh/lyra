"""Tests for swarm caching, request batching, and memory optimization."""

from __future__ import annotations

import pytest

from lyra_agent_swarm.swarm_cache import (
    CacheEntry,
    CachePolicy,
    SwarmCache,
)
from lyra_agent_swarm.request_batcher import (
    BatchConfig,
    BatchResult,
    BatchStatus,
    RequestBatcher,
    SwarmRequest,
)
from lyra_agent_swarm.memory_optimizer import (
    MemoryOptimizer,
    MemoryRegion,
    OptimizationAction,
)


# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture
def cache():
    return SwarmCache(max_entries=100, default_ttl_ms=60_000.0)


@pytest.fixture
def batcher():
    return RequestBatcher(
        config=BatchConfig(max_batch_size=5, max_wait_ms=100.0)
    )


@pytest.fixture
def memory_optimizer():
    return MemoryOptimizer(max_total_tokens=100_000, warning_threshold=0.75)


# ── TestSwarmCache ────────────────────────────────────────────


class TestCacheEntry:
    def test_entry_creation(self):
        entry = CacheEntry(key="result:task-1", value={"status": "done"})
        assert entry.key == "result:task-1"
        assert entry.value["status"] == "done"
        assert entry.hit_count == 0

    def test_entry_immutability(self):
        entry = CacheEntry(key="k", value="v")
        with pytest.raises(Exception):
            entry.key = "new"

    def test_entry_is_expired(self):
        entry = CacheEntry(key="k", value="v", ttl_ms=0.001)
        assert entry.is_expired


class TestSwarmCacheBasic:
    def test_empty_cache(self, cache):
        assert cache.size == 0

    def test_put_and_get(self, cache):
        cache.put("key1", "value1")
        assert cache.get("key1") == "value1"
        assert cache.size == 1

    def test_get_missing(self, cache):
        assert cache.get("nonexistent") is None

    def test_put_overwrite(self, cache):
        cache.put("key1", "value1")
        cache.put("key1", "value2")
        assert cache.get("key1") == "value2"
        assert cache.size == 1

    def test_delete(self, cache):
        cache.put("key1", "value1")
        assert cache.delete("key1") is True
        assert cache.get("key1") is None
        assert cache.delete("nonexistent") is False

    def test_clear(self, cache):
        cache.put("a", 1)
        cache.put("b", 2)
        cache.clear()
        assert cache.size == 0

    def test_contains(self, cache):
        cache.put("key1", "value1")
        assert ("key1" in cache) is True
        assert ("key2" in cache) is False

    def test_ttl_expiry(self, cache):
        cache.put("key1", "value1", ttl_ms=0.001)
        import time
        time.sleep(0.002)
        assert cache.get("key1") is None

    def test_lru_eviction(self):
        small_cache = SwarmCache(max_entries=3)
        small_cache.put("a", 1)
        small_cache.put("b", 2)
        small_cache.put("c", 3)
        small_cache.put("d", 4)  # Should evict "a"
        assert small_cache.get("a") is None
        assert small_cache.get("d") == 4
        assert small_cache.size == 3

    def test_lru_access_updates_order(self):
        small_cache = SwarmCache(max_entries=3)
        small_cache.put("a", 1)
        small_cache.put("b", 2)
        small_cache.put("c", 3)
        small_cache.get("a")  # Access "a" to make it recently used
        small_cache.put("d", 4)  # Should evict "b" now
        assert small_cache.get("a") == 1
        assert small_cache.get("b") is None

    def test_get_stats(self, cache):
        cache.put("a", 1)
        cache.put("b", 2)
        cache.get("a")  # hit
        cache.get("a")  # hit
        cache.get("c")  # miss
        stats = cache.get_stats()
        assert stats.hits == 2
        assert stats.misses == 1
        assert stats.size == 2

    def test_get_or_compute(self, cache):
        def compute():
            return "computed_value"

        result = cache.get_or_compute("key1", compute)
        assert result == "computed_value"
        assert cache.size == 1

    def test_get_or_compute_uses_cache(self, cache):
        cache.put("key1", "cached")
        call_count = [0]

        def compute():
            call_count[0] += 1
            return "fresh"

        result = cache.get_or_compute("key1", compute)
        assert result == "cached"
        assert call_count[0] == 0

    def test_put_with_policy(self, cache):
        cache.put("key1", "value1", policy=CachePolicy.PRIORITY)
        cache.put("key2", "value2", policy=CachePolicy.NORMAL)
        assert cache.get("key1") == "value1"


# ── TestRequestBatcher ────────────────────────────────────────


class TestSwarmRequest:
    def test_request_creation(self):
        req = SwarmRequest(
            request_id="r1",
            operation="propose",
            payload="set theme=dark",
        )
        assert req.operation == "propose"
        assert req.payload == "set theme=dark"

    def test_request_immutability(self):
        req = SwarmRequest(request_id="r1", operation="test", payload="data")
        with pytest.raises(Exception):
            req.operation = "other"


class TestRequestBatcherBasic:
    def test_empty_batcher(self, batcher):
        assert batcher.pending_count == 0
        assert batcher.batch_count == 0

    def test_enqueue_request(self, batcher):
        req = SwarmRequest(request_id="r1", operation="read", payload="get key1")
        batcher.enqueue(req)
        assert batcher.pending_count == 1

    def test_flush_creates_batch(self, batcher):
        batcher.enqueue(SwarmRequest(request_id="r1", operation="write", payload="set a=1"))
        batcher.enqueue(SwarmRequest(request_id="r2", operation="write", payload="set b=2"))
        results = batcher.flush()
        assert len(results) == 1  # One batch for same operation
        assert results[0].status == BatchStatus.COMPLETED

    def test_flush_empty(self, batcher):
        results = batcher.flush()
        assert len(results) == 0

    def test_flush_groups_by_operation(self, batcher):
        batcher.enqueue(SwarmRequest(request_id="r1", operation="read", payload="get a"))
        batcher.enqueue(SwarmRequest(request_id="r2", operation="read", payload="get b"))
        batcher.enqueue(SwarmRequest(request_id="r3", operation="write", payload="set c=1"))
        results = batcher.flush()
        assert len(results) == 2  # Two batches: reads + writes
        read_batch = [r for r in results if r.operation == "read"][0]
        assert read_batch.request_count == 2

    def test_flush_respects_max_batch_size(self):
        small_batcher = RequestBatcher(BatchConfig(max_batch_size=2))
        for i in range(5):
            small_batcher.enqueue(
                SwarmRequest(request_id=f"r{i}", operation="write", payload=f"data-{i}")
            )
        results = small_batcher.flush()
        total_requests = sum(r.request_count for r in results)
        assert total_requests == 5
        assert len(results) == 3  # 2 + 2 + 1

    def test_enqueue_above_max_pending(self):
        tiny_batcher = RequestBatcher(
            BatchConfig(max_batch_size=2, max_pending=3)
        )
        for i in range(3):
            tiny_batcher.enqueue(SwarmRequest(request_id=f"r{i}", operation="w", payload="d"))
        with pytest.raises(ValueError, match="Max pending"):
            tiny_batcher.enqueue(SwarmRequest(request_id="r4", operation="w", payload="d"))

    def test_get_batch(self, batcher):
        batcher.enqueue(SwarmRequest(request_id="r1", operation="read", payload="x"))
        batcher.enqueue(SwarmRequest(request_id="r2", operation="read", payload="y"))
        batch = batcher.get_batch("read")
        assert batch is not None
        assert len(batch) == 2

    def test_get_batch_wrong_operation(self, batcher):
        batcher.enqueue(SwarmRequest(request_id="r1", operation="read", payload="x"))
        assert batcher.get_batch("write") is None

    def test_get_status(self, batcher):
        batcher.enqueue(SwarmRequest(request_id="r1", operation="write", payload="x"))
        status = batcher.get_status()
        assert status["pending"] == 1
        assert status["batches_completed"] == 0

    def test_reset(self, batcher):
        batcher.enqueue(SwarmRequest(request_id="r1", operation="write", payload="x"))
        batcher.reset()
        assert batcher.pending_count == 0


class TestBatchResult:
    def test_batch_result_creation(self):
        result = BatchResult(
            batch_id="b1",
            operation="write",
            request_count=3,
            status=BatchStatus.COMPLETED,
        )
        assert result.request_count == 3

    def test_batch_result_immutability(self):
        result = BatchResult(
            batch_id="b1",
            operation="read",
            request_count=1,
            status=BatchStatus.COMPLETED,
        )
        with pytest.raises(Exception):
            result.status = BatchStatus.FAILED


# ── TestMemoryOptimizer ───────────────────────────────────────


class TestMemoryRegion:
    def test_region_creation(self):
        region = MemoryRegion(
            name="swarm_context",
            token_count=5000,
            max_tokens=10000,
        )
        assert region.utilization == 0.5

    def test_region_high_utilization(self):
        region = MemoryRegion(
            name="system_prompt",
            token_count=9000,
            max_tokens=10000,
        )
        assert region.is_critical


class TestMemoryOptimizerBasic:
    def test_empty_optimizer(self, memory_optimizer):
        assert memory_optimizer.total_used == 0

    def test_register_region(self, memory_optimizer):
        memory_optimizer.register_region("context", token_count=5000, max_tokens=10000)
        assert memory_optimizer.region_count == 1

    def test_register_duplicate_region(self, memory_optimizer):
        memory_optimizer.register_region("ctx", token_count=1000, max_tokens=5000)
        with pytest.raises(ValueError, match="already registered"):
            memory_optimizer.register_region("ctx", token_count=2000, max_tokens=5000)

    def test_update_region(self, memory_optimizer):
        memory_optimizer.register_region("ctx", token_count=5000, max_tokens=10000)
        memory_optimizer.update_region("ctx", token_count=8000)
        region = memory_optimizer.get_region("ctx")
        assert region.token_count == 8000

    def test_update_missing_region(self, memory_optimizer):
        with pytest.raises(ValueError, match="not found"):
            memory_optimizer.update_region("unknown", token_count=100)

    def test_total_used(self, memory_optimizer):
        memory_optimizer.register_region("a", token_count=3000, max_tokens=10000)
        memory_optimizer.register_region("b", token_count=5000, max_tokens=10000)
        assert memory_optimizer.total_used == 8000

    def test_get_utilization(self, memory_optimizer):
        memory_optimizer.register_region("a", token_count=3000, max_tokens=10000)
        memory_optimizer.register_region("b", token_count=5000, max_tokens=10000)
        util = memory_optimizer.get_utilization()
        assert pytest.approx(util) == 8000 / 100_000

    def test_is_warning(self, memory_optimizer):
        memory_optimizer.register_region("a", token_count=80_000, max_tokens=100_000)
        assert memory_optimizer.is_warning

    def test_optimize_returns_actions(self, memory_optimizer):
        memory_optimizer.register_region("context", token_count=40_000, max_tokens=50_000)
        memory_optimizer.register_region("history", token_count=35_000, max_tokens=50_000)
        memory_optimizer.register_region("system", token_count=10_000, max_tokens=20_000)
        actions = memory_optimizer.optimize()
        assert len(actions) > 0

    def test_optimize_no_action_when_healthy(self, memory_optimizer):
        memory_optimizer.register_region("context", token_count=5000, max_tokens=50000)
        actions = memory_optimizer.optimize()
        assert len(actions) == 0

    def test_get_memory_stats(self, memory_optimizer):
        memory_optimizer.register_region("a", token_count=3000, max_tokens=10000)
        memory_optimizer.register_region("b", token_count=5000, max_tokens=10000)
        stats = memory_optimizer.get_memory_stats()
        assert stats.total_used == 8000
        assert stats.total_max == 100_000
        assert stats.region_count == 2

    def test_reset(self, memory_optimizer):
        memory_optimizer.register_region("a", token_count=5000, max_tokens=10000)
        memory_optimizer.reset()
        assert memory_optimizer.region_count == 0

    def test_optimization_action_types(self, memory_optimizer):
        memory_optimizer.register_region("context", token_count=45_000, max_tokens=50_000)
        memory_optimizer.register_region("history", token_count=40_000, max_tokens=50_000)
        actions = memory_optimizer.optimize()
        action_types = {a.action for a in actions}
        assert OptimizationAction.COMPACT in action_types or OptimizationAction.TRUNCATE in action_types
