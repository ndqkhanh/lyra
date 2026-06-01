"""
Tests for Multi-Level Caching System
"""

import pytest
import time
from pathlib import Path
from lyra_core.cache import (
    LRUCache,
    DiskCache,
    MultiLevelCache,
    CacheEntry,
    cached
)


class TestLRUCache:
    """Test LRU Cache"""

    def test_initialization(self):
        """Test cache initialization"""
        cache = LRUCache(capacity=100)
        assert cache.capacity == 100
        assert len(cache.cache) == 0

    def test_put_and_get(self):
        """Test basic put and get"""
        cache = LRUCache()
        cache.put("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_lru_eviction(self):
        """Test LRU eviction"""
        cache = LRUCache(capacity=2)
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")  # Should evict key1

        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"

    def test_ttl_expiration(self):
        """Test TTL expiration"""
        cache = LRUCache()
        cache.put("key1", "value1", ttl=0.1)  # 100ms TTL

        assert cache.get("key1") == "value1"
        time.sleep(0.15)
        assert cache.get("key1") is None

    def test_invalidate(self):
        """Test cache invalidation"""
        cache = LRUCache()
        cache.put("key1", "value1")
        assert cache.invalidate("key1") is True
        assert cache.get("key1") is None

    def test_clear(self):
        """Test cache clear"""
        cache = LRUCache()
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.clear()
        assert len(cache.cache) == 0


class TestDiskCache:
    """Test Disk Cache"""

    def test_initialization(self, tmp_path):
        """Test disk cache initialization"""
        cache = DiskCache(cache_dir=str(tmp_path / "cache"))
        assert cache.cache_dir.exists()

    def test_put_and_get(self, tmp_path):
        """Test basic put and get"""
        cache = DiskCache(cache_dir=str(tmp_path / "cache"))
        cache.put("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_persistence(self, tmp_path):
        """Test cache persistence"""
        cache_dir = tmp_path / "cache"
        cache1 = DiskCache(cache_dir=str(cache_dir))
        cache1.put("key1", "value1")

        # Create new cache instance
        cache2 = DiskCache(cache_dir=str(cache_dir))
        assert cache2.get("key1") == "value1"

    def test_ttl_expiration(self, tmp_path):
        """Test TTL expiration"""
        cache = DiskCache(cache_dir=str(tmp_path / "cache"))
        cache.put("key1", "value1", ttl=0.1)

        assert cache.get("key1") == "value1"
        time.sleep(0.15)
        assert cache.get("key1") is None


class TestMultiLevelCache:
    """Test Multi-Level Cache"""

    def test_initialization(self, tmp_path):
        """Test multi-level cache initialization"""
        cache = MultiLevelCache(
            l1_capacity=100,
            cache_dir=str(tmp_path / "cache")
        )
        assert cache.l1.capacity == 100
        assert cache.l2.cache_dir.exists()

    def test_l1_hit(self, tmp_path):
        """Test L1 cache hit"""
        cache = MultiLevelCache(cache_dir=str(tmp_path / "cache"))
        cache.put("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_l2_promotion(self, tmp_path):
        """Test L2 to L1 promotion"""
        cache = MultiLevelCache(
            l1_capacity=1,
            cache_dir=str(tmp_path / "cache")
        )

        # Fill L1 and L2
        cache.put("key1", "value1")
        cache.put("key2", "value2")  # Evicts key1 from L1

        # Get key1 (should promote from L2 to L1)
        assert cache.get("key1") == "value1"
        assert cache.l1.get("key1") == "value1"

    def test_invalidate_both_levels(self, tmp_path):
        """Test invalidation across both levels"""
        cache = MultiLevelCache(cache_dir=str(tmp_path / "cache"))
        cache.put("key1", "value1")
        cache.invalidate("key1")

        assert cache.l1.get("key1") is None
        assert cache.l2.get("key1") is None


class TestCachedDecorator:
    """Test cached decorator"""

    def test_function_caching(self, tmp_path):
        """Test function result caching"""
        call_count = 0

        @cached(cache=MultiLevelCache(cache_dir=str(tmp_path / "cache")))
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call
        result1 = expensive_function(5)
        assert result1 == 10
        assert call_count == 1

        # Second call (should use cache)
        result2 = expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # Not called again


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
