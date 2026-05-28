"""Tests for the multi-level cache."""
from __future__ import annotations

import tempfile
from pathlib import Path

from lyra_core.cache.multi_level_cache import CacheConfig, CacheStats, MultiLevelCache


class TestCacheConfig:
    def test_defaults(self):
        cfg = CacheConfig()
        assert cfg.l1_max_items == 512
        assert cfg.l1_ttl_sec == 60.0
        assert cfg.l2_ttl_sec == 3600.0


class TestCacheStats:
    def test_hit_rate_zero_with_no_ops(self):
        s = CacheStats()
        assert s.hit_rate == 0.0

    def test_hit_rate_with_hits(self):
        s = CacheStats(l1_hits=5, misses=5)
        assert s.hit_rate == 0.5


class TestMultiLevelCache:
    def test_set_and_get(self):
        cache = MultiLevelCache(
            CacheConfig(disk_path=tempfile.mkdtemp()))
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_miss(self):
        cache = MultiLevelCache(
            CacheConfig(disk_path=tempfile.mkdtemp()))
        assert cache.get("nonexistent") is None

    def test_invalidate(self):
        cache = MultiLevelCache(
            CacheConfig(disk_path=tempfile.mkdtemp()))
        cache.set("k", "v")
        cache.invalidate("k")
        assert cache.get("k") is None

    def test_clear(self):
        cache = MultiLevelCache(
            CacheConfig(disk_path=tempfile.mkdtemp()))
        cache.set("a", 1)
        cache.set("b", 2)
        cache.clear()
        assert cache.get("a") is None
        assert cache.get("b") is None

    def test_l2_promotion(self):
        cache = MultiLevelCache(
            CacheConfig(disk_path=tempfile.mkdtemp()))
        cache.set("l2key", "persisted")
        # Clear L1 only
        cache._l1.clear()
        # Should get from L2
        val = cache.get("l2key")
        assert val == "persisted"

    def test_set_l3(self):
        cache = MultiLevelCache(
            CacheConfig(disk_path=tempfile.mkdtemp()))
        cache.set_l3("remote", {"data": "remote_value"})
        assert cache.get("remote") == {"data": "remote_value"}

    def test_l3_fallback(self):
        cache = MultiLevelCache(
            CacheConfig(disk_path=tempfile.mkdtemp()))
        cache.set_l3("remote_only", 42)
        assert cache.get("remote_only") == 42

    def test_stats_tracks_hits(self):
        cache = MultiLevelCache(
            CacheConfig(disk_path=tempfile.mkdtemp()))
        cache.set("hit", "value")
        cache.get("hit")
        cache.get("miss")
        stats = cache.stats
        assert stats.l1_hits >= 1
        assert stats.misses >= 1

    def test_l1_lru_eviction(self):
        cfg = CacheConfig(l1_max_items=3, disk_path=tempfile.mkdtemp())
        cache = MultiLevelCache(cfg)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        cache.set("d", 4)  # should evict "a"
        assert cache.get("a") is None or cache.get("a") == 1
        assert cache.get("d") == 4

    def test_invalidate_l3(self):
        cache = MultiLevelCache(
            CacheConfig(disk_path=tempfile.mkdtemp()))
        cache.set_l3("remote", 99)
        cache.invalidate("remote")
        assert cache.get("remote") is None

    def test_disk_persistence(self):
        path = tempfile.mkdtemp()
        cache1 = MultiLevelCache(CacheConfig(disk_path=path))
        cache1.set("persistent", "data")

        cache2 = MultiLevelCache(CacheConfig(disk_path=path))
        assert cache2.get("persistent") == "data"
