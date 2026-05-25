"""L0 Working Memory — active context window management.

Manages the current session's active working context with configurable
capacity limits and priority-based eviction.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from .exceptions import MemoryStackError


@dataclass(frozen=True)
class WorkingMemoryEntry:
    """An entry in working memory.

    Attributes:
        entry_id: Unique identifier.
        content: The stored content.
        priority: Numeric priority (higher = more important).
        timestamp: Unix timestamp of creation.
        ttl: Time-to-live in seconds, or 0 for no expiry.
    """

    entry_id: str
    content: str
    priority: float
    timestamp: float
    ttl: float


@dataclass(frozen=True)
class WorkingMemoryConfig:
    """Configuration for working memory.

    Attributes:
        max_entries: Maximum number of entries before eviction.
        max_tokens_estimate: Rough token capacity estimate.
        default_ttl: Default time-to-live in seconds.
    """

    max_entries: int = 100
    max_tokens_estimate: int = 100_000
    default_ttl: float = 3600.0


class WorkingMemory:
    """L0 working memory — active context for the current session.

    Provides add, get, evict, and clear operations with priority-based
    eviction and TTL expiry.
    """

    def __init__(self, config: WorkingMemoryConfig | None = None) -> None:
        self._config = config or WorkingMemoryConfig()
        self._entries: dict[str, WorkingMemoryEntry] = {}
        self._counter = 0

    @property
    def config(self) -> WorkingMemoryConfig:
        return self._config

    @property
    def size(self) -> int:
        return len(self._entries)

    async def add(
        self, content: str, priority: float = 1.0, ttl: float | None = None
    ) -> str:
        """Add an entry to working memory.

        Args:
            content: The content to store.
            priority: Numeric priority (higher = keep longer).
            ttl: Time-to-live in seconds. Uses config default if None.

        Returns:
            The entry_id of the new entry.
        """
        if not content.strip():
            raise MemoryStackError("Content cannot be empty")

        if self.size >= self._config.max_entries:
            self._evict_lowest_priority()

        self._counter += 1
        entry_id = f"wm-{self._counter}"
        actual_ttl = ttl if ttl is not None else self._config.default_ttl
        entry = WorkingMemoryEntry(
            entry_id=entry_id,
            content=content.strip(),
            priority=priority,
            timestamp=time.time(),
            ttl=actual_ttl,
        )
        self._entries[entry_id] = entry
        return entry_id

    async def get(self, entry_id: str) -> WorkingMemoryEntry:
        """Retrieve an entry by ID.

        Args:
            entry_id: The entry identifier.

        Returns:
            The WorkingMemoryEntry.

        Raises:
            MemoryStackError: If entry is not found.
        """
        if entry_id not in self._entries:
            raise MemoryStackError(f"Entry not found: {entry_id}")
        return self._entries[entry_id]

    async def get_all(self) -> tuple[WorkingMemoryEntry, ...]:
        """Get all non-expired entries sorted by priority descending."""
        now = time.time()
        active = [
            e
            for e in self._entries.values()
            if e.ttl == 0 or (now - e.timestamp) < e.ttl
        ]
        active.sort(key=lambda e: e.priority, reverse=True)
        return tuple(active)

    async def update_priority(self, entry_id: str, priority: float) -> None:
        """Update the priority of an entry.

        Args:
            entry_id: The entry identifier.
            priority: New priority value.
        """
        if entry_id not in self._entries:
            raise MemoryStackError(f"Entry not found: {entry_id}")
        existing = self._entries[entry_id]
        self._entries[entry_id] = WorkingMemoryEntry(
            entry_id=existing.entry_id,
            content=existing.content,
            priority=priority,
            timestamp=existing.timestamp,
            ttl=existing.ttl,
        )

    async def remove(self, entry_id: str) -> None:
        """Remove an entry from working memory."""
        if entry_id not in self._entries:
            raise MemoryStackError(f"Entry not found: {entry_id}")
        del self._entries[entry_id]

    async def clear(self) -> None:
        """Clear all entries from working memory."""
        self._entries.clear()

    async def estimate_tokens(self) -> int:
        """Estimate total tokens across all entries."""
        total = sum(len(e.content) // 4 for e in self._entries.values())
        return total

    def _evict_lowest_priority(self) -> None:
        """Evict the entry with the lowest priority."""
        if not self._entries:
            return
        now = time.time()

        candidates = [
            (eid, e) for eid, e in self._entries.items()
            if e.ttl > 0 and (now - e.timestamp) >= e.ttl
        ]
        if candidates:
            expired_id = candidates[0][0]
            del self._entries[expired_id]
            return

        lowest = min(self._entries.items(), key=lambda x: x[1].priority)
        del self._entries[lowest[0]]
