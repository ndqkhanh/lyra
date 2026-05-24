"""Tests for PromptCache and SemanticCache."""

from __future__ import annotations

import time

import pytest

from lyra_cost import CacheStats, PromptCache, SemanticCache


class TestPromptCache:
    """Tests for the exact-match PromptCache."""

    def test_miss_on_empty_cache(self) -> None:
        cache = PromptCache()
        assert cache.get("hello") is None
        assert cache.stats.hits == 0
        assert cache.stats.misses == 1

    def test_hit_after_set(self) -> None:
        cache = PromptCache()
        cache.set("hello", "world", input_tokens=10)
        result = cache.get("hello")
        assert result is not None
        response, tokens = result
        assert response == "world"
        assert tokens == 10
        assert cache.stats.hits == 1

    def test_miss_on_different_prompt(self) -> None:
        cache = PromptCache()
        cache.set("hello", "world", input_tokens=5)
        assert cache.get("goodbye") is None
        assert cache.stats.hits == 0
        assert cache.stats.misses == 1

    def test_lru_eviction(self) -> None:
        cache = PromptCache(max_size=2)
        cache.set("a", "1", input_tokens=1)
        cache.set("b", "2", input_tokens=1)
        cache.set("c", "3", input_tokens=1)  # evicts "a"
        assert cache.get("a") is None
        assert cache.get("b") is not None
        assert cache.get("c") is not None

    def test_lru_move_to_end_on_access(self) -> None:
        cache = PromptCache(max_size=2)
        cache.set("a", "1", input_tokens=1)
        cache.set("b", "2", input_tokens=1)
        # Access "a" to move it to end
        assert cache.get("a") is not None
        cache.set("c", "3", input_tokens=1)  # evicts "b" (LRU is now "b")
        assert cache.get("a") is not None
        assert cache.get("b") is None
        assert cache.get("c") is not None

    def test_ttl_expiry(self) -> None:
        cache = PromptCache(max_size=100, ttl_seconds=0.01)
        cache.set("hello", "world", input_tokens=10)
        time.sleep(0.02)
        assert cache.get("hello") is None
        # Should count as a miss (expired entry)
        assert cache.stats.misses == 1

    def test_clear(self) -> None:
        cache = PromptCache()
        cache.set("a", "1", input_tokens=1)
        cache.set("b", "2", input_tokens=1)
        assert cache.size == 2
        cache.clear()
        assert cache.size == 0
        assert cache.stats.hits == 0
        assert cache.stats.misses == 0

    def test_cache_stats(self) -> None:
        cache = PromptCache()
        assert isinstance(cache.stats, CacheStats)
        assert cache.stats.hit_rate == 0.0

        cache.set("a", "1", input_tokens=1)
        cache.get("a")  # hit
        cache.get("b")  # miss
        assert cache.stats.hits == 1
        assert cache.stats.misses == 1
        assert cache.stats.hit_rate == pytest.approx(0.5)

    def test_duplicate_set_updates(self) -> None:
        cache = PromptCache()
        cache.set("key", "first", input_tokens=10)
        cache.set("key", "second", input_tokens=20)
        result = cache.get("key")
        assert result is not None
        assert result[0] == "second"
        assert result[1] == 20


class TestSemanticCache:
    """Tests for the similarity-based SemanticCache."""

    def test_miss_on_empty(self) -> None:
        cache = SemanticCache()
        assert cache.get("anything") is None

    def test_hit_on_exact_match(self) -> None:
        cache = SemanticCache(similarity_threshold=0.75)
        cache.set("what is the weather", "sunny", input_tokens=10)
        result = cache.get("what is the weather")
        assert result is not None
        response, tokens, score = result
        assert response == "sunny"
        assert tokens == 10
        assert score >= 0.99  # exact match should be near 1.0

    def test_hit_on_similar_query(self) -> None:
        cache = SemanticCache(similarity_threshold=0.3)
        cache.set("how is the weather today", "sunny", input_tokens=10)
        # High overlap query
        result = cache.get("how is weather today")
        assert result is not None
        assert result[0] == "sunny"

    def test_miss_on_dissimilar_query(self) -> None:
        cache = SemanticCache(similarity_threshold=0.75)
        cache.set("what is the weather", "sunny", input_tokens=10)
        assert cache.get("tell me a story about dragons") is None

    def test_stats_tracking(self) -> None:
        cache = SemanticCache()
        cache.set("hello", "world", input_tokens=5)
        cache.get("hello")  # hit
        cache.get("goodbye")  # miss
        assert cache.stats.hits == 1
        assert cache.stats.misses == 1

    def test_clear(self) -> None:
        cache = SemanticCache()
        cache.set("a", "1", input_tokens=1)
        cache.set("b", "2", input_tokens=1)
        assert cache.size == 2
        cache.clear()
        assert cache.size == 0

    def test_max_size(self) -> None:
        cache = SemanticCache(max_size=2)
        cache.set("a", "1", input_tokens=1)
        cache.set("b", "2", input_tokens=1)
        cache.set("c", "3", input_tokens=1)  # evicts "a"
        assert cache.size == 2

    def test_stop_words_and_empty(self) -> None:
        cache = SemanticCache()
        # Should not crash on empty string
        assert cache.get("") is None
        cache.set("", "empty", input_tokens=0)
        result = cache.get("")
        assert result is not None
        assert result[0] == "empty"
        assert result[1] == 0
        assert result[2] == pytest.approx(1.0)  # exact match on empty vectors

    def test_stats_dict(self) -> None:
        cache = SemanticCache()
        cache.set("hello", "world", input_tokens=5)
        cache.get("hello")
        sd = cache.stats_dict
        assert sd["hits"] == 1
        assert sd["misses"] == 0
        assert sd["hit_rate"] == 1.0
        assert sd["size"] == 1
        assert sd["similarity_threshold"] == 0.75
