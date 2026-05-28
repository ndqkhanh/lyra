"""Tests for VerbatimCache — verbatim-first retrieval layer."""

import time

import pytest

from lyra_memory.verbatim_cache import (
    CachePriority,
    VerbatimCache,
    VerbatimEntry,
)


class TestCachePriority:
    def test_values(self):
        assert CachePriority.HIGH.value == "high"
        assert CachePriority.MEDIUM.value == "medium"
        assert CachePriority.LOW.value == "low"

    def test_comparable(self):
        entries = [
            CachePriority.LOW,
            CachePriority.HIGH,
            CachePriority.MEDIUM,
        ]
        assert sorted(entries) == [
            CachePriority.HIGH,
            CachePriority.LOW,
            CachePriority.MEDIUM,
        ]


class TestVerbatimEntry:
    def test_create(self):
        ts = time.time()
        entry = VerbatimEntry(
            entry_id="test-1",
            content="Hello world",
            content_hash="abc123",
            source="conversation",
            priority=CachePriority.HIGH,
            token_count=10,
            created_at=ts,
            last_accessed=ts,
            access_count=0,
        )
        assert entry.entry_id == "test-1"
        assert entry.content == "Hello world"
        assert entry.priority == CachePriority.HIGH

    def test_age_sec(self):
        ts = time.time() - 100
        entry = VerbatimEntry(
            entry_id="t", content="x", content_hash="h",
            source="s", priority=CachePriority.MEDIUM,
            token_count=1, created_at=ts, last_accessed=ts, access_count=0,
        )
        assert entry.age_sec >= 100

    def test_idle_sec(self):
        ts = time.time() - 60
        entry = VerbatimEntry(
            entry_id="t", content="x", content_hash="h",
            source="s", priority=CachePriority.MEDIUM,
            token_count=1, created_at=ts, last_accessed=ts, access_count=0,
        )
        assert entry.idle_sec >= 60

    def test_immutable(self):
        ts = time.time()
        entry = VerbatimEntry(
            entry_id="t", content="x", content_hash="h",
            source="s", priority=CachePriority.MEDIUM,
            token_count=1, created_at=ts, last_accessed=ts, access_count=0,
        )
        with pytest.raises(Exception):
            entry.content = "modified"  # type: ignore[misc]


class TestVerbatimCacheStore:
    def test_store_basic(self):
        cache = VerbatimCache()
        entry = cache.store("conversation", "What is AI?")
        assert entry is not None
        assert cache.size == 1
        assert cache.stats()["stores"] == 1

    def test_store_empty_content(self):
        cache = VerbatimCache()
        entry = cache.store("conversation", "   ")
        assert entry is None
        assert cache.size == 0

    def test_store_truncates_long_content(self):
        cache = VerbatimCache(max_content_length=10)
        entry = cache.store("conversation", "a" * 100)
        assert entry is not None
        assert len(entry.content) == 10

    def test_store_returns_unique_ids(self):
        cache = VerbatimCache()
        e1 = cache.store("src", "msg A")
        e2 = cache.store("src", "msg B")
        assert e1 is not None and e2 is not None
        assert e1.entry_id != e2.entry_id

    def test_store_increments_token_count(self):
        cache = VerbatimCache()
        cache.store("src", "hello world")  # ~3 tokens
        assert cache.total_tokens_cached > 0


class TestVerbatimCacheLookup:
    def test_lookup_exact_match(self):
        cache = VerbatimCache()
        cache.store("conv", "Capital of France is Paris")
        results = cache.lookup("Capital of France is Paris")
        assert len(results) == 1
        assert results[0].content == "Capital of France is Paris"

    def test_lookup_substring_match(self):
        cache = VerbatimCache()
        cache.store("conv", "The quick brown fox jumps over the lazy dog")
        results = cache.lookup("quick brown fox")
        assert len(results) >= 1

    def test_lookup_word_match(self):
        cache = VerbatimCache()
        cache.store("conv", "Python is a great programming language")
        results = cache.lookup("programming")
        assert len(results) >= 1

    def test_lookup_case_insensitive(self):
        cache = VerbatimCache()
        cache.store("conv", "Hello World")
        results = cache.lookup("hello world")
        assert len(results) == 1

    def test_lookup_miss(self):
        cache = VerbatimCache()
        cache.store("conv", "Python programming")
        results = cache.lookup("quantum physics")
        assert results == []

    def test_lookup_empty_query(self):
        cache = VerbatimCache()
        cache.store("conv", "some content")
        results = cache.lookup("")
        assert results == []

    def test_lookup_scores_exact_higher_than_substring(self):
        cache = VerbatimCache()
        cache.store("conv", "The cat sat on the mat")
        cache.store("conv", "cat")
        results = cache.lookup("cat")
        assert len(results) >= 2
        assert results[0].content == "cat"

    def test_lookup_top_k_limit(self):
        cache = VerbatimCache()
        for i in range(10):
            cache.store("conv", f"document about topic {i}")
        # All contain "topic", should limit to top_k
        results = cache.lookup("topic", top_k=3)
        assert len(results) == 3


class TestVerbatimCacheLookupExact:
    def test_lookup_exact_finds_match(self):
        cache = VerbatimCache()
        cache.store("src", "unique content string")
        result = cache.lookup_exact("unique content string")
        assert result is not None
        assert result.content == "unique content string"

    def test_lookup_exact_no_match(self):
        cache = VerbatimCache()
        cache.store("src", "some content")
        result = cache.lookup_exact("different content")
        assert result is None


class TestVerbatimCacheAccessTracking:
    def test_lookup_updates_hit_count(self):
        cache = VerbatimCache()
        cache.store("src", "test content")
        cache.lookup("test")
        assert cache.stats()["hits"] == 1

    def test_lookup_miss_increments_misses(self):
        cache = VerbatimCache()
        cache.store("src", "hello")
        cache.lookup("nonexistent")
        assert cache.stats()["misses"] == 1

    def test_hit_rate(self):
        cache = VerbatimCache()
        cache.store("src", "hello")
        cache.lookup("hello")  # hit
        cache.lookup("nope")   # miss
        assert cache.hit_rate == 0.5


class TestVerbatimCacheGetAndRemove:
    def test_get_existing(self):
        cache = VerbatimCache()
        entry = cache.store("src", "test")
        assert entry is not None
        retrieved = cache.get(entry.entry_id)
        assert retrieved is not None
        assert retrieved.entry_id == entry.entry_id

    def test_get_nonexistent(self):
        cache = VerbatimCache()
        assert cache.get("nonexistent") is None

    def test_remove_entry(self):
        cache = VerbatimCache()
        entry = cache.store("src", "test")
        assert entry is not None
        assert cache.remove(entry.entry_id) is True
        assert cache.size == 0

    def test_remove_nonexistent(self):
        cache = VerbatimCache()
        assert cache.remove("fake-id") is False


class TestVerbatimCacheEviction:
    def test_eviction_by_priority(self):
        cache = VerbatimCache(max_entries=3)
        cache.store("src", "low 1", priority=CachePriority.LOW)
        cache.store("src", "low 2", priority=CachePriority.LOW)
        cache.store("src", "high 1", priority=CachePriority.HIGH)
        cache.store("src", "high 2", priority=CachePriority.HIGH)
        assert cache.size == 3
        # Low priority entries should be evicted first
        assert cache.stats()["evictions"] == 1

    def test_eviction_falls_back_to_lru(self):
        cache = VerbatimCache(max_entries=2)
        cache.store("src", "a", priority=CachePriority.HIGH)
        cache.store("src", "b", priority=CachePriority.HIGH)
        cache.store("src", "c", priority=CachePriority.HIGH)
        assert cache.size == 2


class TestVerbatimCacheExpiration:
    def test_expire_stale_entries(self):
        cache = VerbatimCache(ttl_sec=0.01)
        cache.store("src", "ephemeral")
        assert cache.size == 1
        time.sleep(0.02)
        cache.store("src", "trigger")  # triggers _expire_stale_entries
        assert cache.stats()["expirations"] >= 1


class TestVerbatimCacheClear:
    def test_clear_removes_all(self):
        cache = VerbatimCache()
        cache.store("src", "a")
        cache.store("src", "b")
        cache.store("src", "c")
        cache.clear()
        assert cache.size == 0
        assert cache.total_tokens_cached == 0


class TestVerbatimCacheStats:
    def test_stats_returns_dict(self):
        cache = VerbatimCache()
        s = cache.stats()
        assert "size" in s
        assert "max_entries" in s
        assert "hit_rate" in s
        assert "stores" in s
        assert "hits" in s
        assert "misses" in s
        assert "evictions" in s
        assert "expirations" in s


class TestVerbatimCacheEdgeCases:
    def test_store_very_long_message_truncates(self):
        cache = VerbatimCache()
        long_msg = "x" * 100_000
        entry = cache.store("src", long_msg)
        assert entry is not None
        assert len(entry.content) == cache.max_content_length
