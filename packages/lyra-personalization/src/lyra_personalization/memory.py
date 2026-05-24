"""
Tripartite memory system for Lyra personalization.

Implements SPARK-inspired three-tier memory architecture:
- Working Memory: current session, active task context, recent tool calls
- Episodic Memory: recent project interactions, past conversations, resolved issues
- Semantic Memory: long-term user knowledge, coding conventions, preferences, goals
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from lyra_personalization.models import (
    InteractionRecord,
)

logger = logging.getLogger(__name__)

DEFAULT_SEMANTIC_COOLDOWN = timedelta(hours=24)
DEFAULT_IMPORTANCE_THRESHOLD = 0.3
DEFAULT_MAX_EPISODIC = 1000


@dataclass
class MemoryEntry:
    """A single entry stored in one of the memory tiers."""
    content: str
    memory_type: str  # "working", "episodic", or "semantic"
    importance: float = 0.5
    timestamp: datetime = field(default_factory=datetime.now)
    source_interaction_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class TripartiteMemory:
    """
    Three-tier memory system with automatic promotion and consolidation.

    Manages working, episodic, and semantic memory tiers with:
    - TTL-based working memory expiry
    - Importance-scored episodic memory with automatic pruning
    - Episodic-to-semantic consolidation
    - Cross-tier search
    """

    def __init__(
        self,
        max_episodic: int = DEFAULT_MAX_EPISODIC,
        importance_threshold: float = DEFAULT_IMPORTANCE_THRESHOLD,
        semantic_cooldown: timedelta = DEFAULT_SEMANTIC_COOLDOWN,
    ) -> None:
        self._working: Dict[str, MemoryEntry] = {}
        self._episodic: List[MemoryEntry] = []
        self._semantic: List[MemoryEntry] = []
        self._max_episodic = max_episodic
        self._importance_threshold = importance_threshold
        self._semantic_cooldown = semantic_cooldown
        self._last_consolidation: Optional[datetime] = None

    @property
    def working_count(self) -> int:
        """Number of entries in working memory."""
        return len(self._working)

    @property
    def episodic_count(self) -> int:
        """Number of entries in episodic memory."""
        return len(self._episodic)

    @property
    def semantic_count(self) -> int:
        """Number of entries in semantic memory."""
        return len(self._semantic)

    def add_to_working(self, entry: MemoryEntry) -> None:
        """
        Add an entry to working memory.

        Working memory holds the current session context.
        Entries are keyed by content for deduplication.

        Args:
            entry: The memory entry to add.
        """
        key = self._working_key(entry)
        self._working[key] = entry
        logger.debug("Added entry to working memory: %s", key)

    def promote_to_episodic(self, entry: MemoryEntry) -> None:
        """
        Promote a working memory entry to episodic memory.

        Episodic memory stores important session events that
        should persist beyond the current session.

        Args:
            entry: The memory entry to promote.
        """
        key = self._working_key(entry)
        self._working.pop(key, None)

        promoted = MemoryEntry(
            content=entry.content,
            memory_type="episodic",
            importance=entry.importance,
            timestamp=entry.timestamp,
            source_interaction_id=entry.source_interaction_id,
            metadata=dict(entry.metadata),
        )
        self._episodic.append(promoted)
        self._trim_episodic()
        logger.debug("Promoted entry to episodic memory: %s", entry.content[:50])

    def consolidate_to_semantic(self, entries: List[MemoryEntry]) -> None:
        """
        Consolidate episodic entries into semantic memory.

        Episodic entries that exceed the importance threshold
        are merged into durable semantic knowledge.

        Semantic consolidation respects a cooldown period to
        prevent rapid oscillation of long-term knowledge.

        Args:
            entries: Episodic entries to consolidate.
        """
        now = datetime.now()
        if (
            self._last_consolidation is not None
            and now - self._last_consolidation < self._semantic_cooldown
        ):
            logger.debug("Semantic consolidation skipped: within cooldown")
            return

        for entry in entries:
            if entry.importance < self._importance_threshold:
                continue

            semantic_entry = MemoryEntry(
                content=entry.content,
                memory_type="semantic",
                importance=entry.importance,
                timestamp=now,
                source_interaction_id=entry.source_interaction_id,
                metadata=dict(entry.metadata),
            )
            self._semantic.append(semantic_entry)

            if entry in self._episodic:
                self._episodic.remove(entry)

        self._last_consolidation = now
        logger.info(
            "Consolidated %d entries to semantic memory",
            len(entries),
        )

    def search_memory(
        self,
        query: str,
        memory_type: str = "all",
    ) -> List[MemoryEntry]:
        """
        Search across a specific memory tier or all tiers.

        Performs simple keyword matching against entry content.

        Args:
            query: Search query string.
            memory_type: One of "working", "episodic", "semantic", or "all".

        Returns:
            List of matching MemoryEntry objects, sorted by importance.
        """
        query_lower = query.lower()
        results: List[MemoryEntry] = []
        sources: Dict[str, List[MemoryEntry]] = {
            "working": list(self._working.values()),
            "episodic": list(self._episodic),
            "semantic": list(self._semantic),
        }

        if memory_type == "all":
            candidates = (
                list(self._working.values())
                + list(self._episodic)
                + list(self._semantic)
            )
        else:
            candidates = sources.get(memory_type, [])

        for entry in candidates:
            if query_lower in entry.content.lower():
                results.append(entry)

        results.sort(key=lambda e: e.importance, reverse=True)
        return results

    def forget_old_entries(self, threshold: timedelta) -> int:
        """
        Prune entries older than the given threshold.

        Removes episodic and semantic entries whose timestamp
        falls before (now - threshold). Returns count of removed
        entries.

        Args:
            threshold: Maximum age for entries to keep.

        Returns:
            Number of entries pruned.
        """
        cutoff = datetime.now() - threshold
        pruned = 0

        before = len(self._episodic)
        self._episodic = [
            e for e in self._episodic
            if e.timestamp >= cutoff or e.importance >= self._importance_threshold
        ]
        pruned += before - len(self._episodic)

        before = len(self._semantic)
        self._semantic = [
            e for e in self._semantic
            if e.timestamp >= cutoff
        ]
        pruned += before - len(self._semantic)

        if pruned > 0:
            logger.info("Pruned %d old entries from memory", pruned)

        return pruned

    def clear_working_memory(self) -> int:
        """
        Clear all entries from working memory.

        Returns:
            Number of entries cleared.
        """
        count = len(self._working)
        self._working.clear()
        logger.info("Cleared %d entries from working memory", count)
        return count

    def add_interaction(
        self,
        interaction: InteractionRecord,
    ) -> None:
        """
        Add an interaction record to the appropriate memory tiers.

        Automatically creates working and episodic entries from
        an interaction based on its importance score.

        Args:
            interaction: The interaction to record.
        """
        working_entry = MemoryEntry(
            content=interaction.content,
            memory_type="working",
            importance=interaction.importance,
            timestamp=interaction.timestamp,
            source_interaction_id=interaction.id,
        )
        self.add_to_working(working_entry)

        if interaction.importance >= self._importance_threshold:
            episodic_entry = MemoryEntry(
                content=interaction.content,
                memory_type="episodic",
                importance=interaction.importance,
                timestamp=interaction.timestamp,
                source_interaction_id=interaction.id,
                metadata=dict(interaction.metadata),
            )
            self._episodic.append(episodic_entry)
            self._trim_episodic()

    def get_episodic_highlights(self, limit: int = 10) -> List[MemoryEntry]:
        """
        Get the most important episodic entries.

        Args:
            limit: Maximum number of highlights to return.

        Returns:
            List of top episodic entries by importance.
        """
        sorted_episodic = sorted(
            self._episodic,
            key=lambda e: e.importance,
            reverse=True,
        )
        return sorted_episodic[:limit]

    def get_all_working_entries(self) -> Dict[str, MemoryEntry]:
        """Get all working memory entries."""
        return dict(self._working)

    def _working_key(self, entry: MemoryEntry) -> str:
        """Generate a deduplication key for a working memory entry."""
        return hashlib_md5(entry.content)[:16]

    def _trim_episodic(self) -> None:
        """Trim episodic memory to max capacity, keeping most important."""
        if len(self._episodic) <= self._max_episodic:
            return
        self._episodic.sort(key=lambda e: e.importance, reverse=True)
        self._episodic = self._episodic[:self._max_episodic]


def hashlib_md5(content: str) -> str:
    """Compute MD5 hash of content (using hashlib)."""
    import hashlib
    return hashlib.md5(content.encode()).hexdigest()
