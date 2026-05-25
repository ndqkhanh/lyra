"""Tests for KV-Cache Compression (RKVHash + KVCacheCompressor)."""

from lyra_memory.pipeline.kv_cache import KVCacheCompressor, KVPair, RKVHash


class TestKVPair:
    def test_default_values(self):
        p = KVPair(key="k1", value="v1", attention_norm=0.5)
        assert p.key == "k1"
        assert p.value == "v1"
        assert p.attention_norm == 0.5
        assert p.access_count == 0

    def test_record_access(self):
        p = KVPair(key="k", value="v")
        p.record_access()
        assert p.access_count == 1


class TestRKVHash:
    def test_put_and_get(self):
        cache = RKVHash()
        cache.put("k1", "v1")
        entry = cache.get("k1")
        assert entry is not None
        assert entry.key == "k1"
        assert entry.value == "v1"

    def test_get_nonexistent(self):
        cache = RKVHash()
        assert cache.get("nope") is None

    def test_get_records_access(self):
        cache = RKVHash()
        cache.put("k1", "v1")
        cache.get("k1")
        entry = cache.get("k1")
        assert entry.access_count >= 2

    def test_deduplication_by_content_hash(self):
        cache = RKVHash()
        e1 = cache.put("k1", "v1")
        e2 = cache.put("k1", "v1")
        assert e1.id == e2.id
        assert cache.size == 1

    def test_eviction_when_full(self):
        cache = RKVHash(max_entries=2)
        cache.put("k1", "v1")
        cache.put("k2", "v2")
        assert cache.size == 2
        cache.put("k3", "v3")
        assert cache.size == 2

    def test_remove_entry(self):
        cache = RKVHash()
        cache.put("k1", "v1")
        cache.remove("k1")
        assert cache.get("k1") is None
        assert cache.size == 0

    def test_clear(self):
        cache = RKVHash()
        cache.put("k1", "v1")
        cache.put("k2", "v2")
        cache.clear()
        assert cache.size == 0

    def test_evict_lru(self):
        cache = RKVHash(max_entries=2)
        cache.put("k1", "v1")
        cache.put("k2", "v2")
        cache.get("k1")
        cache.put("k3", "v3")
        assert cache.get("k1") is not None
        assert cache.size == 2


class TestKVCacheCompressor:
    def test_add_and_compress(self):
        compressor = KVCacheCompressor(retention_ratio=0.5)
        compressor.add("k1", "v1", attention_norm=0.9)
        compressor.add("k2", "v2", attention_norm=0.3)
        compressor.add("k3", "v3", attention_norm=0.7)
        compressor.add("k4", "v4", attention_norm=0.1)

        removed = compressor.compress()
        assert removed == 2
        assert compressor.kv_cache.size == 2

    def test_compress_keeps_high_attention(self):
        compressor = KVCacheCompressor(retention_ratio=0.5)
        compressor.add("important", "high priority", attention_norm=0.95)
        compressor.add("noise", "low priority", attention_norm=0.05)

        compressor.compress()
        assert compressor.kv_cache.get("important") is not None

    def test_compress_empty_cache(self):
        compressor = KVCacheCompressor()
        removed = compressor.compress()
        assert removed == 0

    def test_compress_single_entry(self):
        compressor = KVCacheCompressor(retention_ratio=0.5)
        compressor.add("only", "entry", attention_norm=0.5)
        removed = compressor.compress()
        assert removed == 0
        assert compressor.kv_cache.size == 1

    def test_estimated_memory_bytes(self):
        compressor = KVCacheCompressor()
        compressor.add("key1", "value1", attention_norm=0.5)
        compressor.add("key_longer", "value_longer", attention_norm=0.8)
        mem = compressor.estimated_memory_bytes
        assert mem > 0
