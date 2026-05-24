"""Prompt and semantic caching for Lyra AGI cost reduction.

Implements two cache layers:
- PromptCache: exact-match caching with configurable TTL (90% discount on reads).
- SemanticCache: cosine-similarity-based caching for semantically similar queries
  (30-70% savings).

Both layers track hit/miss rates for observability.
"""

from __future__ import annotations

import logging
import time
import hashlib
from collections import OrderedDict
from typing import Any

from lyra_cost.models import CacheStats

logger = logging.getLogger(__name__)


class PromptCache:
    """Exact-match prompt cache with TTL and LRU eviction.

    Cached reads incur only 10% of input token cost (90% discount on prompt cache hits).
    """

    def __init__(
        self, max_size: int = 1000, ttl_seconds: float = 300.0
    ) -> None:
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, _CacheEntry] = OrderedDict()
        self._stats = CacheStats()

    @property
    def stats(self) -> CacheStats:
        return self._stats

    @property
    def size(self) -> int:
        self._evict_expired()
        return len(self._cache)

    def get(self, prompt: str) -> tuple[str, float] | None:
        """Look up a cached response.

        Returns ``(response_text, cached_input_tokens)`` on hit, ``None`` on miss.
        The cached token count is the original prompt length so consumers can
        compute the 90% discount.
        """
        key = self._make_key(prompt)
        entry = self._cache.get(key)
        if entry is None:
            self._stats = CacheStats(hits=self._stats.hits, misses=self._stats.misses + 1)
            return None

        if time.time() > entry.expires_at:
            del self._cache[key]
            self._stats = CacheStats(hits=self._stats.hits, misses=self._stats.misses + 1)
            return None

        # Move to end (LRU)
        self._cache.move_to_end(key)
        self._stats = CacheStats(hits=self._stats.hits + 1, misses=self._stats.misses)
        return entry.response, entry.input_tokens

    def set(
        self,
        prompt: str,
        response: str,
        input_tokens: int,
    ) -> None:
        """Cache a prompt-response pair with the given input token count."""
        self._evict_expired()

        key = self._make_key(prompt)
        self._cache[key] = _CacheEntry(
            response=response,
            input_tokens=input_tokens,
            created_at=time.time(),
            expires_at=time.time() + self._ttl_seconds,
        )
        self._cache.move_to_end(key)

        if len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

        logger.debug("Cached prompt (%d tokens, TTL=%.0fs)", input_tokens, self._ttl_seconds)

    def clear(self) -> None:
        self._cache.clear()
        self._stats = CacheStats()
        logger.info("Prompt cache cleared")

    def _evict_expired(self) -> None:
        now = time.time()
        expired = [k for k, v in self._cache.items() if now > v.expires_at]
        for k in expired:
            del self._cache[k]

    @staticmethod
    def _make_key(prompt: str) -> str:
        return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


class _CacheEntry:
    """Internal cache entry with TTL tracking."""

    __slots__ = ("response", "input_tokens", "created_at", "expires_at")

    def __init__(
        self,
        response: str,
        input_tokens: int,
        created_at: float,
        expires_at: float,
    ) -> None:
        self.response = response
        self.input_tokens = input_tokens
        self.created_at = created_at
        self.expires_at = expires_at


class SemanticCache:
    """Semantic cache that matches prompts by cosine similarity.

    Uses a simple bag-of-words / TF-style embedding for similarity comparison.
    Configurable similarity threshold (0.75 default) controls how aggressively
    we return cached results.

    Typical savings: 30-70% on repeated but not identical queries.
    """

    def __init__(
        self,
        max_size: int = 500,
        similarity_threshold: float = 0.75,
    ) -> None:
        self._max_size = max_size
        self._similarity_threshold = similarity_threshold
        self._entries: list[_SemanticEntry] = []
        self._stats = CacheStats()

    @property
    def stats(self) -> CacheStats:
        return self._stats

    @property
    def size(self) -> int:
        return len(self._entries)

    def get(self, prompt: str) -> tuple[str, int, float] | None:
        """Look up a semantically similar cached response.

        Returns ``(response, input_tokens, similarity_score)`` on hit, ``None`` on miss.
        """
        query_vec = self._vectorize(prompt)
        best_score = 0.0
        best_entry: _SemanticEntry | None = None

        for entry in self._entries:
            score = self._cosine_similarity(query_vec, entry.vector)
            if score > best_score:
                best_score = score
                best_entry = entry

        if best_entry is not None and best_score >= self._similarity_threshold:
            self._stats = CacheStats(hits=self._stats.hits + 1, misses=self._stats.misses)
            logger.debug("Semantic cache HIT (score=%.3f)", best_score)
            return best_entry.response, best_entry.input_tokens, best_score

        self._stats = CacheStats(hits=self._stats.hits, misses=self._stats.misses + 1)
        return None

    def set(self, prompt: str, response: str, input_tokens: int) -> None:
        """Store a prompt-response pair in the semantic cache."""
        vector = self._vectorize(prompt)
        self._entries.append(_SemanticEntry(
            response=response,
            input_tokens=input_tokens,
            vector=vector,
        ))

        if len(self._entries) > self._max_size:
            self._entries.pop(0)

        logger.debug("Semantic cache entry added (%d tokens)", input_tokens)

    def clear(self) -> None:
        self._entries.clear()
        self._stats = CacheStats()
        logger.info("Semantic cache cleared")

    # -- Internal vectorisation / similarity ----------------------------------

    @staticmethod
    def _vectorize(text: str) -> dict[str, float]:
        """Simple TF vectorisation — token frequency map."""
        tokens = text.lower().split()
        vec: dict[str, float] = {}
        for t in tokens:
            vec[t] = vec.get(t, 0.0) + 1.0
        # Normalise by length
        total = sum(vec.values())
        if total > 0:
            for k in vec:
                vec[k] /= total
        return vec

    @staticmethod
    def _cosine_similarity(
        a: dict[str, float], b: dict[str, float]
    ) -> float:
        """Cosine similarity between two sparse vectors."""
        # Both empty vectors are identical
        if not a and not b:
            return 1.0
        if not a or not b:
            return 0.0
        intersection = set(a) & set(b)
        dot_product = sum(a[k] * b[k] for k in intersection)
        norm_a = sum(v * v for v in a.values()) ** 0.5
        norm_b = sum(v * v for v in b.values()) ** 0.5
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot_product / (norm_a * norm_b)

    @property
    def stats_dict(self) -> dict[str, Any]:
        return {
            "size": self.size,
            "max_size": self._max_size,
            "hits": self._stats.hits,
            "misses": self._stats.misses,
            "hit_rate": round(self._stats.hit_rate, 4),
            "similarity_threshold": self._similarity_threshold,
        }


class _SemanticEntry:
    """Internal semantic cache entry."""

    __slots__ = ("response", "input_tokens", "vector")

    def __init__(
        self,
        response: str,
        input_tokens: int,
        vector: dict[str, float],
    ) -> None:
        self.response = response
        self.input_tokens = input_tokens
        self.vector = vector
