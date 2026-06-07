"""Swarm Cache — LRU cache with TTL expiry for swarm operation results.

Provides a caching layer for swarm operations:
  - LRU eviction with configurable max entries
  - TTL-based expiry per cache entry
  - Hit/miss statistics tracking
  - get_or_compute pattern for lazy population
  - Priority-based entry retention
"""

from __future__ import annotations

import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum


class CachePolicy(StrEnum):
    """Retention policy for cache entries."""

    NORMAL = "normal"
    PRIORITY = "priority"


@dataclass(frozen=True)
class CacheEntry:
    """A single cache entry with TTL and access tracking."""

    key: str
    value: object
    created_at: float = field(default_factory=time.monotonic)
    ttl_ms: float = 60_000.0
    hit_count: int = 0
    policy: CachePolicy = CachePolicy.NORMAL

    @property
    def is_expired(self) -> bool:
        return (time.monotonic() - self.created_at) * 1000 > self.ttl_ms


@dataclass
class CacheStats:
    """Statistics for the swarm cache."""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size: int = 0
    max_size: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class SwarmCache:
    """LRU cache with TTL expiry for swarm operation results.

    Caches intermediate and final results of swarm operations
    to avoid redundant computation.

    Usage::

        cache = SwarmCache(max_entries=500, default_ttl_ms=30_000)
        cache.put("agent:task-1:result", {"status": "done"})
        result = cache.get("agent:task-1:result")
        # Or with compute:
        result = cache.get_or_compute("expensive-key", lambda: compute_expensive())
    """

    def __init__(
        self,
        max_entries: int = 1000,
        default_ttl_ms: float = 60_000.0,
    ) -> None:
        self.max_entries = max_entries
        self.default_ttl_ms = default_ttl_ms
        self._store: OrderedDict[str, CacheEntry] = OrderedDict()
        self._stats = CacheStats(max_size=max_entries)

    # ── Properties ───────────────────────────────────────────────

    @property
    def size(self) -> int:
        return len(self._store)

    # ── Operations ───────────────────────────────────────────────

    def get(self, key: str) -> object | None:
        """Get a cached value. Returns None if missing or expired."""
        entry = self._store.get(key)
        if entry is None:
            self._stats.misses += 1
            return None
        if entry.is_expired:
            del self._store[key]
            self._stats.misses += 1
            return None

        self._stats.hits += 1
        # Move to end for LRU tracking (MutableMapping pattern — rebuild)
        self._store.move_to_end(key)
        return entry.value

    def put(
        self,
        key: str,
        value: object,
        ttl_ms: float | None = None,
        policy: CachePolicy = CachePolicy.NORMAL,
    ) -> None:
        """Store a value in the cache."""
        self._evict_if_needed()

        if key in self._store:
            del self._store[key]

        entry = CacheEntry(
            key=key,
            value=value,
            ttl_ms=ttl_ms if ttl_ms is not None else self.default_ttl_ms,
            policy=policy,
        )
        self._store[key] = entry
        self._store.move_to_end(key)
        self._stats.size = self.size

    def delete(self, key: str) -> bool:
        """Remove an entry from the cache. Returns True if it existed."""
        if key in self._store:
            del self._store[key]
            self._stats.size = self.size
            return True
        return False

    def clear(self) -> None:
        """Remove all entries."""
        self._store.clear()
        self._stats.size = 0

    def get_or_compute(
        self,
        key: str,
        compute: Callable[[], object],
        ttl_ms: float | None = None,
    ) -> object:
        """Get from cache, or compute and store if missing."""
        cached = self.get(key)
        if cached is not None:
            return cached
        value = compute()
        self.put(key, value, ttl_ms=ttl_ms)
        return value

    def get_stats(self) -> CacheStats:
        """Get current cache statistics."""
        self._stats.size = self.size
        return self._stats

    def __contains__(self, key: str) -> bool:
        entry = self._store.get(key)
        return entry is not None and not entry.is_expired

    def __len__(self) -> int:
        return self.size

    # ── Private ───────────────────────────────────────────────────

    def _evict_if_needed(self) -> None:
        """Evict entries if cache is at capacity."""
        while len(self._store) >= self.max_entries:
            # Try to evict normal entries before priority ones
            evicted = False
            for k in list(self._store.keys()):
                entry = self._store[k]
                if entry.policy != CachePolicy.PRIORITY or entry.is_expired:
                    del self._store[k]
                    self._stats.evictions += 1
                    evicted = True
                    break
            if not evicted:
                # All entries are priority — evict oldest
                oldest_key = next(iter(self._store))
                del self._store[oldest_key]
                self._stats.evictions += 1
