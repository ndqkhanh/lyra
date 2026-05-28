"""Verbatim Cache — exact-match first retrieval layer for memory.

Implements a lightweight verbatim-first retrieval cache that stores
recent conversation turns and tool outputs for exact-match lookup
before falling through to semantic/embedding-based retrieval.

Inspired by the MemPalace verbatim-first architecture and DCI-Agent-Lite
zero-index retrieval patterns. Provides sub-millisecond lookup for
recently accessed content without embedding model overhead.

Key concepts:
- VerbatimEntry: a single cached content item with metadata
- VerbatimCache: the main cache with TTL-based eviction and LRU overflow
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from enum import StrEnum


class CachePriority(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class VerbatimEntry:
    """A single verbatim-cached content item.

    Attributes:
        entry_id: unique content-addressable identifier
        content: the full text content cached verbatim
        content_hash: SHA-256 hash for integrity verification
        source: where this content came from (e.g. "conversation", "tool_output")
        priority: retention priority (HIGH/MEDIUM/LOW)
        token_count: estimated token count of the content
        created_at: timestamp when cached
        last_accessed: last time the entry was retrieved
        access_count: number of times this entry was retrieved
    """

    entry_id: str
    content: str
    content_hash: str
    source: str
    priority: CachePriority
    token_count: int
    created_at: float
    last_accessed: float
    access_count: int

    @property
    def age_sec(self) -> float:
        return time.time() - self.created_at

    @property
    def idle_sec(self) -> float:
        return time.time() - self.last_accessed


class VerbatimCache:
    """Verbatim-first retrieval cache with TTL eviction and LRU overflow.

    Designed as the first layer in a multi-tier retrieval pipeline.
    Queries are first checked against the verbatim cache for exact or
    substring matches before falling through to more expensive semantic
    retrieval layers.

    Usage::

        cache = VerbatimCache(max_entries=1000, ttl_sec=3600)
        cache.store("conversation", "What is the capital of France?", priority=CachePriority.HIGH)
        results = cache.lookup("capital of France")  # exact/substring match
        if not results:
            results = semantic_retrieval_layer.query("capital of France")
    """

    def __init__(
        self,
        max_entries: int = 1000,
        ttl_sec: float = 3600.0,
        max_content_length: int = 32000,
    ) -> None:
        self.max_entries = max_entries
        self.ttl_sec = ttl_sec
        self.max_content_length = max_content_length
        self._entries: dict[str, VerbatimEntry] = {}
        self._access_order: list[str] = []
        self._stats: dict[str, int] = {
            "stores": 0,
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expirations": 0,
        }
        self._total_tokens_cached: int = 0

    def store(
        self,
        source: str,
        content: str,
        priority: CachePriority = CachePriority.MEDIUM,
    ) -> VerbatimEntry | None:
        """Store content in the verbatim cache.

        Returns the entry if stored, None if content exceeds max length.
        """
        if len(content) > self.max_content_length:
            content = content[:self.max_content_length]

        if not content.strip():
            return None

        content_hash = hashlib.sha256(content.encode()).hexdigest()
        entry_id = hashlib.sha256(
            f"{source}|{content_hash}|{time.time()}".encode()
        ).hexdigest()[:16]

        token_count = self._estimate_tokens(content)
        ts = time.time()

        entry = VerbatimEntry(
            entry_id=entry_id,
            content=content,
            content_hash=content_hash,
            source=source,
            priority=priority,
            token_count=token_count,
            created_at=ts,
            last_accessed=ts,
            access_count=0,
        )

        self._entries[entry_id] = entry
        self._access_order.append(entry_id)
        self._stats["stores"] += 1
        self._total_tokens_cached += token_count

        self._evict_if_needed()
        self._expire_stale_entries()
        return entry

    def lookup(self, query: str, top_k: int = 5) -> list[VerbatimEntry]:
        """Look up content matching the query in the verbatim cache.

        Performs case-insensitive exact and substring matching.
        Returns up to top_k results sorted by recency.
        """
        query_lower = query.lower().strip()
        if not query_lower:
            return []

        matches: list[tuple[float, VerbatimEntry]] = []
        for entry in self._entries.values():
            content_lower = entry.content.lower()
            score = 0.0

            if query_lower == content_lower:
                score = 1.0
            elif query_lower in content_lower:
                score = 0.7 * (len(query_lower) / max(len(content_lower), 1))
            elif any(word in content_lower for word in query_lower.split()):
                matching_words = sum(
                    1 for w in query_lower.split() if w in content_lower
                )
                score = 0.4 * (matching_words / max(len(query_lower.split()), 1))

            if score > 0.0:
                matches.append((score, entry))

        matches.sort(key=lambda x: (-x[0], -x[1].last_accessed))
        results = [m[1] for m in matches[:top_k]]

        if results:
            self._stats["hits"] += 1
            for entry in results:
                self._touch(entry.entry_id)
        else:
            self._stats["misses"] += 1

        return results

    def lookup_exact(self, content: str) -> VerbatimEntry | None:
        """Find an entry by exact content match."""
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        for entry in self._entries.values():
            if entry.content_hash == content_hash:
                self._touch(entry.entry_id)
                return entry
        return None

    def get(self, entry_id: str) -> VerbatimEntry | None:
        """Retrieve a specific entry by ID."""
        entry = self._entries.get(entry_id)
        if entry:
            self._touch(entry_id)
        return entry

    def remove(self, entry_id: str) -> bool:
        """Remove an entry from the cache."""
        if entry_id in self._entries:
            entry = self._entries[entry_id]
            self._total_tokens_cached -= entry.token_count
            del self._entries[entry_id]
            if entry_id in self._access_order:
                self._access_order.remove(entry_id)
            return True
        return False

    def clear(self) -> None:
        """Clear all cache entries."""
        self._entries.clear()
        self._access_order.clear()
        self._total_tokens_cached = 0

    def _touch(self, entry_id: str) -> None:
        """Update access metadata for an entry."""
        entry = self._entries.get(entry_id)
        if entry is None:
            return
        self._entries[entry_id] = VerbatimEntry(
            entry_id=entry.entry_id,
            content=entry.content,
            content_hash=entry.content_hash,
            source=entry.source,
            priority=entry.priority,
            token_count=entry.token_count,
            created_at=entry.created_at,
            last_accessed=time.time(),
            access_count=entry.access_count + 1,
        )
        if entry_id in self._access_order:
            self._access_order.remove(entry_id)
        self._access_order.append(entry_id)

    def _evict_if_needed(self) -> None:
        """Evict entries when over capacity, preferring low-priority LRU."""
        while len(self._entries) > self.max_entries:
            priority_order = [CachePriority.LOW, CachePriority.MEDIUM, CachePriority.HIGH]
            evicted = False
            for priority in priority_order:
                for eid in self._access_order:
                    entry = self._entries.get(eid)
                    if entry and entry.priority == priority:
                        self.remove(eid)
                        self._stats["evictions"] += 1
                        evicted = True
                        break
                if evicted:
                    break
            if not evicted:
                if self._access_order:
                    self.remove(self._access_order[0])
                    self._stats["evictions"] += 1
                else:
                    break

    def _expire_stale_entries(self) -> None:
        """Remove entries past TTL."""
        now = time.time()
        expired = [
            eid for eid, entry in self._entries.items()
            if now - entry.last_accessed > self.ttl_sec
        ]
        for eid in expired:
            self.remove(eid)
            self._stats["expirations"] += 1

    @staticmethod
    def _estimate_tokens(content: str) -> int:
        """Rough token count estimation (~4 chars per token)."""
        return max(1, len(content) // 4)

    @property
    def size(self) -> int:
        return len(self._entries)

    @property
    def hit_rate(self) -> float:
        total = self._stats["hits"] + self._stats["misses"]
        return self._stats["hits"] / max(total, 1)

    @property
    def total_tokens_cached(self) -> int:
        return self._total_tokens_cached

    def stats(self) -> dict:
        """Get cache statistics."""
        return {
            "size": self.size,
            "max_entries": self.max_entries,
            "hit_rate": round(self.hit_rate, 3),
            "total_tokens_cached": self._total_tokens_cached,
            **self._stats,
        }
