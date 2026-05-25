"""
KV-Cache compression utilities — R-KVHash and Norm-Guided Eviction.

R-KVHash: Retrieval-augmented KV-cache with hash-based deduplication
Norm-Guided: Priority-based KV retention using attention norm scores

Source: R-KVHash + Norm-Guided KV, ICLR 2026 MemAgent Workshop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class KVPair:
    """A single key-value pair in the cache."""

    key: str
    value: str
    attention_norm: float = 0.0
    access_count: int = 0
    id: str = field(default_factory=lambda: uuid4().hex)

    def record_access(self) -> None:
        self.access_count += 1


@dataclass
class RKVHash:
    """Retrieval-augmented KV-cache with hash-based deduplication.

    Stores KV pairs indexed by content hash. When the same key-value
    pair is encountered, it reuses the cache entry instead of storing
    a duplicate. Evicts least-accessed entries when the cache is full.
    """

    max_entries: int = 1000
    _entries: dict[str, KVPair] = field(default_factory=dict)
    _hash_index: dict[int, str] = field(default_factory=dict)

    def get(self, key: str) -> KVPair | None:
        entry = self._entries.get(key)
        if entry:
            entry.record_access()
        return entry

    def put(self, key: str, value: str, attention_norm: float = 0.0) -> KVPair:
        content_hash = hash(key + value)

        if content_hash in self._hash_index:
            existing_key = self._hash_index[content_hash]
            if existing_key in self._entries:
                self._entries[existing_key].record_access()
                return self._entries[existing_key]

        if len(self._entries) >= self.max_entries:
            self._evict_lru()

        entry = KVPair(key=key, value=value, attention_norm=attention_norm)
        entry.record_access()
        self._entries[key] = entry
        self._hash_index[content_hash] = key
        return entry

    def remove(self, key: str) -> None:
        if key in self._entries:
            entry = self._entries[key]
            content_hash = hash(entry.key + entry.value)
            self._hash_index.pop(content_hash, None)
            del self._entries[key]

    def _evict_lru(self) -> None:
        if not self._entries:
            return
        lru_key = min(self._entries, key=lambda k: self._entries[k].access_count)
        self.remove(lru_key)

    @property
    def size(self) -> int:
        return len(self._entries)

    def clear(self) -> None:
        self._entries.clear()
        self._hash_index.clear()


@dataclass
class KVCacheCompressor:
    """Norm-guided KV-cache compression.

    Retains KV pairs with the highest attention norms (indicating
    high importance to the model's attention mechanism). This is
    a lossy compression that preserves the most-attended context.
    """

    kv_cache: RKVHash = field(default_factory=RKVHash)
    retention_ratio: float = 0.5

    def add(self, key: str, value: str, attention_norm: float) -> None:
        """Add a KV pair with its attention norm score."""
        self.kv_cache.put(key, value, attention_norm)

    def compress(self) -> int:
        """Compress by removing low-attention entries.

        Returns the number of entries evicted.
        """
        entries = list(self.kv_cache._entries.values())
        if len(entries) <= 1:
            return 0

        entries.sort(key=lambda e: e.attention_norm, reverse=True)
        keep_count = max(1, int(len(entries) * self.retention_ratio))
        keep_keys = {e.key for e in entries[:keep_count]}

        removed = 0
        for key in list(self.kv_cache._entries):
            if key not in keep_keys:
                self.kv_cache.remove(key)
                removed += 1

        return removed

    @property
    def estimated_memory_bytes(self) -> int:
        total = 0
        for entry in self.kv_cache._entries.values():
            total += len(entry.key) + len(entry.value)
        return total
