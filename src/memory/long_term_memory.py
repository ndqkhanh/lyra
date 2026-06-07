"""
Long-Term Memory — persistent knowledge base.

Provides two implementations:

* ``LongTermMemory`` — original in-memory store with in-memory index.
* ``SQLiteLongTermMemory`` — SQLite-backed persistence with deduplication and
  Ebbinghaus importance decay.
"""

import json
import math
import time
import uuid
from collections import defaultdict
from typing import Any

import aiosqlite

from src.memory.memory_store import (
    LongTermRecord,
    Memory,
    MemoryStore,
    MemoryType,
    SQLiteStore,
)
from src.memory.vector_search import VectorSearcher


# =============================================================================
# In-memory MemoryIndex
# =============================================================================


class MemoryIndex:
    """
    Fast retrieval index for memories.

    Maintains indices for:
    - Tags
    - Memory types
    - Time ranges
    """

    def __init__(self):
        self.tag_index: dict[str, set[str]] = defaultdict(set)
        self.type_index: dict[MemoryType, set[str]] = defaultdict(set)
        self.time_index: list[tuple] = []

    def add_memory(self, memory: Memory):
        """Add memory to index."""
        for tag in memory.tags:
            self.tag_index[tag].add(memory.memory_id)
        self.type_index[memory.memory_type].add(memory.memory_id)
        self.time_index.append((memory.timestamp, memory.memory_id))
        self.time_index.sort(reverse=True)

    def remove_memory(self, memory: Memory):
        """Remove memory from index."""
        for tag in memory.tags:
            self.tag_index[tag].discard(memory.memory_id)
        self.type_index[memory.memory_type].discard(memory.memory_id)
        self.time_index = [(ts, mid) for ts, mid in self.time_index if mid != memory.memory_id]

    def find_by_tags(self, tags: list[str], match_all: bool = False) -> set[str]:
        """Find memory IDs by tags."""
        if not tags:
            return set()
        if match_all:
            result = self.tag_index[tags[0]].copy()
            for tag in tags[1:]:
                result &= self.tag_index[tag]
            return result
        else:
            result = set()
            for tag in tags:
                result |= self.tag_index[tag]
            return result

    def find_by_type(self, memory_type: MemoryType) -> set[str]:
        """Find memory IDs by type."""
        return self.type_index[memory_type].copy()

    def find_by_time_range(self, start_time: float | None = None, end_time: float | None = None) -> list[str]:
        """Find memory IDs in time range (sorted, most recent first)."""
        result = []
        for timestamp, memory_id in self.time_index:
            if start_time and timestamp < start_time:
                continue
            if end_time and timestamp > end_time:
                continue
            result.append(memory_id)
        return result

    def clear(self):
        """Clear all indices."""
        self.tag_index.clear()
        self.type_index.clear()
        self.time_index.clear()


# =============================================================================
# In-memory LongTermMemory (original)
# =============================================================================


class LongTermMemory:
    """
    Long-term persistent memory (in-memory store).

    Responsibilities:
    - Store unlimited memories
    - Fast indexed retrieval
    - Importance-based management
    - Knowledge consolidation
    """

    def __init__(self, storage_path: str | None = None):
        self.store = MemoryStore(storage_path)
        self.index = MemoryIndex()
        self._rebuild_index()

    def add(
        self,
        content: str,
        memory_type: MemoryType,
        importance: float = 0.5,
        tags: list[str] | None = None,
        context: dict | None = None,
    ) -> Memory:
        """Add a memory to long-term storage."""
        memory = self.store.add(
            content=content,
            memory_type=memory_type,
            importance=importance,
            tags=tags,
            context=context,
        )
        self.index.add_memory(memory)
        return memory

    def get(self, memory_id: str) -> Memory | None:
        return self.store.get(memory_id)

    def search_by_tags(self, tags: list[str], match_all: bool = False, limit: int | None = None) -> list[Memory]:
        """Search memories by tags."""
        memory_ids = self.index.find_by_tags(tags, match_all)
        memories = []
        for mid in memory_ids:
            memory = self.store.get(mid)
            if memory:
                memories.append(memory)
        memories.sort(key=lambda m: m.importance, reverse=True)
        if limit:
            memories = memories[:limit]
        return memories

    def search_by_type(self, memory_type: MemoryType, limit: int | None = None) -> list[Memory]:
        """Search memories by type."""
        memory_ids = self.index.find_by_type(memory_type)
        memories = []
        for mid in memory_ids:
            memory = self.store.get(mid)
            if memory:
                memories.append(memory)
        memories.sort(key=lambda m: m.importance, reverse=True)
        if limit:
            memories = memories[:limit]
        return memories

    def search_by_time_range(self, start_time: float | None = None, end_time: float | None = None, limit: int | None = None) -> list[Memory]:
        """Search memories by time range."""
        memory_ids = self.index.find_by_time_range(start_time, end_time)
        memories = []
        for mid in memory_ids:
            memory = self.store.get(mid)
            if memory:
                memories.append(memory)
        if limit:
            memories = memories[:limit]
        return memories

    def search_by_content(self, query: str, limit: int | None = None) -> list[Memory]:
        """Search memories by content (simple keyword search)."""
        query_lower = query.lower()
        matches = []
        for memory in self.store.get_all():
            if query_lower in memory.content.lower():
                matches.append(memory)
        matches.sort(key=lambda m: m.importance, reverse=True)
        if limit:
            matches = matches[:limit]
        return matches

    def get_recent(self, limit: int = 10) -> list[Memory]:
        return self.store.get_recent(limit)

    def get_important(self, threshold: float = 0.7, limit: int = 10) -> list[Memory]:
        return self.store.get_important(threshold, limit)

    def merge_similar(self, similarity_threshold: float = 0.8) -> int:
        """Merge memories with identical content."""
        content_map: dict[str, list[Memory]] = defaultdict(list)
        for memory in self.store.get_all():
            content_map[memory.content].append(memory)

        merged = 0
        for _content, memories in content_map.items():
            if len(memories) > 1:
                memories.sort(key=lambda m: m.importance, reverse=True)
                primary = memories[0]
                for other in memories[1:]:
                    primary.tags = list(set(primary.tags + other.tags))
                    primary.context.update(other.context)
                    primary.importance = min(1.0, primary.importance + 0.1)
                    self.store.delete(other.memory_id)
                    self.index.remove_memory(other)
                    merged += 1
        return merged

    def apply_decay(self, decay_rate: float = 0.01):
        self.store.apply_decay(decay_rate)

    def apply_ebbinghaus_decay(self, half_life_hours: float = 24.0):
        self.store.apply_ebbinghaus_decay(half_life_hours)

    def prune(self, min_importance: float = 0.1) -> int:
        """Remove low-importance memories."""
        to_remove = []
        for memory in self.store.get_all():
            if memory.importance < min_importance:
                to_remove.append(memory)
        for memory in to_remove:
            self.store.delete(memory.memory_id)
            self.index.remove_memory(memory)
        return len(to_remove)

    def save(self):
        self.store.save()

    def load(self):
        self.store.load()
        self._rebuild_index()

    def _rebuild_index(self):
        self.index.clear()
        for memory in self.store.get_all():
            self.index.add_memory(memory)

    def clear(self):
        self.store.clear()
        self.index.clear()

    def get_statistics(self) -> dict:
        stats = self.store.get_statistics()
        stats["indexed_tags"] = len(self.index.tag_index)
        stats["indexed_types"] = len(self.index.type_index)
        return stats


# =============================================================================
# SQLite-backed LongTermMemory
# =============================================================================


class SQLiteLongTermMemory:
    """
    SQLite-backed long-term memory with deduplication and Ebbinghaus decay.

    Parameters:
        db_path: Path to the SQLite database file.
        half_life_hours: Hours after which importance is halved (Ebbinghaus curve).
        dedup_content: If ``True``, ``add_memory`` checks content hashes and
                       merges/boosts instead of inserting a duplicate row.
    """

    def __init__(
        self,
        db_path: str,
        half_life_hours: float = 24.0,
        dedup_content: bool = True,
    ):
        self.db = SQLiteStore(db_path)
        self.half_life_hours = half_life_hours
        self.dedup_content = dedup_content

        # In-memory vector searcher for semantic similarity (lazy-built)
        self._vector_searcher: VectorSearcher | None = None
        self._vector_index_dirty: bool = True

    async def init(self):
        """Ensure SQLite tables exist."""
        await self.db.init_db()

    async def close(self):
        pass

    # ------------------------------------------------------------------
    # Add / fetch
    # ------------------------------------------------------------------

    async def add_memory(
        self,
        content: str,
        memory_type: str = "semantic",
        tags: list[str] | None = None,
        importance: float = 0.5,
        embedding: bytes | None = None,
    ) -> LongTermRecord:
        """Add a long-term memory with optional deduplication.

        When ``dedup_content`` is enabled and a record with the same content
        already exists, the existing record's importance is boosted by 10%
        (up to 1.0) instead of inserting a duplicate.
        """
        if self.dedup_content:
            existing = await self.db.search_long_term_keyword(content)
            for record in existing:
                if record.content.strip() == content.strip():
                    # Dedup: boost importance
                    new_imp = min(1.0, record.importance_score + 0.1)
                    await self.db.update_long_term_importance(record.id, new_imp)
                    await self.db.update_long_term_access(record.id)
                    record.importance_score = new_imp
                    record.access_count += 1
                    return record

        record_id = str(uuid.uuid4())
        now = time.time()
        record = LongTermRecord(
            id=record_id,
            content=content,
            memory_type=memory_type,
            tags=tags or [],
            embedding=embedding,
            importance_score=importance,
            created_at=now,
            last_accessed=now,
            access_count=0,
        )
        await self.db.add_long_term(record)

        # Mark vector index as stale; rebuild lazily on next semantic search
        self._vector_index_dirty = True
        return record

    async def get_memory(self, memory_id: str) -> LongTermRecord | None:
        """Fetch a single memory and bump its access count."""
        record = await self.db.get_long_term(memory_id)
        if record:
            await self.db.update_long_term_access(memory_id)
        return record

    async def get_all(self) -> list[LongTermRecord]:
        """Return all long-term memories (newest first)."""
        return await self.db.get_all_long_term()

    async def get_recent(self, limit: int = 10) -> list[LongTermRecord]:
        """Return the *limit* most recent memories."""
        return await self.db.get_long_term_recent(limit)

    async def get_important(self, min_importance: float = 0.7, limit: int = 20) -> list[LongTermRecord]:
        """Return memories with importance >= *min_importance*."""
        return await self.db.get_important_long_term(min_importance, limit)

    async def count(self) -> int:
        return await self.db.count_long_term()

    # ------------------------------------------------------------------
    # Delete / clear
    # ------------------------------------------------------------------

    async def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory by ID."""
        deleted = await self.db.delete_long_term(memory_id)
        if deleted:
            self._vector_index_dirty = True
        return deleted

    async def clear_all(self):
        """Remove all long-term memories by truncating the table."""
        async with aiosqlite.connect(self.db.db_path) as conn:
            await conn.execute("DELETE FROM long_term")
            await conn.commit()
        self._vector_searcher = None
        self._vector_index_dirty = True

    # ------------------------------------------------------------------
    # Keyword search
    # ------------------------------------------------------------------

    async def search_by_keyword(self, query: str) -> list[LongTermRecord]:
        """SQL ``LIKE`` search."""
        return await self.db.search_long_term_keyword(query)

    # ------------------------------------------------------------------
    # Decay
    # ------------------------------------------------------------------

    async def apply_ebbinghaus_decay(self, half_life_hours: float | None = None):
        """
        Apply the Ebbinghaus forgetting curve to all long-term memories.

        Updates ``importance_score`` in-place::

            new_importance = old_importance * exp(-elapsed_hours / half_life)
        """
        h = half_life_hours or self.half_life_hours
        now = time.time()
        records = await self.db.get_all_long_term()
        for rec in records:
            elapsed_hours = (now - rec.last_accessed) / 3600.0
            decay_factor = math.exp(-elapsed_hours / h)
            new_imp = max(0.0, rec.importance_score * decay_factor)
            await self.db.update_long_term_importance(rec.id, new_imp)

    async def apply_deterministic_decay(self, half_life_hours: float | None = None, current_time: float | None = None):
        """
        Deterministic variant of Ebbinghaus decay (useful for tests).

        Unlike ``apply_ebbinghaus_decay``, this accepts an explicit *current_time*
        so results are reproducible.
        """
        h = half_life_hours or self.half_life_hours
        now = current_time or time.time()
        records = await self.db.get_all_long_term()
        for rec in records:
            elapsed_hours = (now - rec.last_accessed) / 3600.0
            decay_factor = math.exp(-elapsed_hours / h)
            new_imp = max(0.0, rec.importance_score * decay_factor)
            await self.db.update_long_term_importance(rec.id, new_imp)

    # ------------------------------------------------------------------
    # Vector / semantic search
    # ------------------------------------------------------------------

    async def build_vector_index(self, encoder=None):
        """
        Build or rebuild the in-memory ``VectorSearcher`` index from all
        stored long-term records.
        """
        records = await self.db.get_all_long_term()
        if not records:
            self._vector_searcher = VectorSearcher(encoder=encoder)
            return

        texts = [r.content for r in records]
        searcher = VectorSearcher(encoder=encoder)
        searcher.index(texts)
        self._vector_searcher = searcher
        self._vector_index_dirty = False

    async def search_semantic(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> list[tuple[LongTermRecord, float]]:
        """Search by semantic (cosine) similarity via the vector index.

        The vector index is rebuilt lazily whenever it has been marked dirty
        (i.e. after additions or deletions).

        Returns ``(record, score)`` pairs.
        """
        if self._vector_index_dirty or self._vector_searcher is None:
            await self.build_vector_index()
        if self._vector_searcher is None or self._vector_searcher.count == 0:
            return []

        results = self._vector_searcher.search(query, top_k=top_k, min_score=min_score)
        records = await self.db.get_all_long_term()
        text_to_record = {r.content: r for r in records}
        return [(text_to_record[t], s) for t, s in results if t in text_to_record]

    # ------------------------------------------------------------------
    # Consolidation helpers
    # ------------------------------------------------------------------

    async def consolidate_from_conversations(
        self,
        turns: list[Any],  # ConversationTurn-like objects with role, content
        min_importance: float = 0.6,
        memory_type: str = "episodic",
    ) -> int:
        """Convert a list of conversation turns into LTM records.

        Each turn's content is stored as ``{role}: {content}``.
        Returns the number of memories created (after dedup).
        """
        created = 0
        for turn in turns:
            content = f"{turn.role}: {turn.content}"
            imp = getattr(turn, "metadata", {}) and turn.metadata.get("importance_score", 0.5)
            if isinstance(imp, dict):
                imp = 0.5
            if imp < min_importance:
                continue
            await self.add_memory(
                content=content,
                memory_type=memory_type,
                tags=[turn.role, "conversation"],
                importance=imp,
            )
            created += 1
        return created

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    async def get_statistics(self) -> dict:
        """Return aggregate statistics."""
        count = await self.db.count_long_term()
        records = await self.db.get_all_long_term()
        imp_values = [r.importance_score for r in records]
        avg_imp = sum(imp_values) / len(imp_values) if imp_values else 0.0
        max_imp = max(imp_values) if imp_values else 0.0
        min_imp = min(imp_values) if imp_values else 0.0
        return {
            "total_memories": count,
            "average_importance": round(avg_imp, 4),
            "max_importance": round(max_imp, 4),
            "min_importance": round(min_imp, 4),
            "half_life_hours": self.half_life_hours,
            "dedup_enabled": self.dedup_content,
        }
