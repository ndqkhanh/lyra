"""L0 Working Memory — Active context window management.

Provides a sliding-window context with configurable token budgets,
priority-based eviction, and add/remove/peek/clear operations.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from heapq import heappop, heappush
from typing import Any

from lyra_memory_stack.exceptions import MemoryCapacityError, MemoryNotFoundError


@dataclass(frozen=True)
class ContextItem:
    """An individual item in the working memory context window."""

    item_id: str
    content: str
    priority: int = 0  # Higher = more important
    timestamp: float = field(default_factory=time.time)
    token_estimate: int = 0
    source: str = "agent"
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_priority(self, new_priority: int) -> ContextItem:
        """Return a new item with an updated priority (immutable)."""
        return ContextItem(
            item_id=self.item_id,
            content=self.content,
            priority=new_priority,
            timestamp=self.timestamp,
            token_estimate=self.token_estimate,
            source=self.source,
            metadata=self.metadata,
        )

    def with_content(self, new_content: str) -> ContextItem:
        """Return a new item with updated content (immutable)."""
        return ContextItem(
            item_id=self.item_id,
            content=new_content,
            priority=self.priority,
            timestamp=time.time(),
            token_estimate=len(new_content) // 4,
            source=self.source,
            metadata=self.metadata,
        )


def estimate_tokens(text: str) -> int:
    """Estimate token count for a text string (~4 chars per token)."""
    return max(1, len(text) // 4)


class WorkingMemory:
    """Sliding-window working memory with priority-based eviction.

    Maintains a bounded-size context window. When adding items exceeds
    the max token budget, lower-priority items are evicted first.
    """

    _items: dict[str, ContextItem]
    _max_tokens: int
    _eviction_queue: list[tuple[int, float, str]]  # (priority, timestamp, item_id)

    def __init__(self, max_tokens: int = 4096) -> None:
        self._items = {}
        self._max_tokens = max_tokens
        self._eviction_queue = []

    @property
    def max_tokens(self) -> int:
        return self._max_tokens

    def set_max_tokens(self, new_max: int) -> None:
        """Resize the token budget, potentially triggering eviction."""
        self._max_tokens = new_max
        self._evict_if_over_budget()

    def add(self, item: ContextItem) -> None:
        """Add an item to working memory. Evicts lower-priority items if over budget."""
        self._items[item.item_id] = item
        heappush(self._eviction_queue, (item.priority, -item.timestamp, item.item_id))
        self._evict_if_over_budget()

    def remove(self, item_id: str) -> ContextItem:
        """Remove an item by ID. Raises MemoryNotFoundError if missing."""
        item = self._items.pop(item_id, None)
        if item is None:
            raise MemoryNotFoundError(item_id, "working_memory")
        # Rebuild eviction queue to remove stale entries
        self._rebuild_queue()
        return item

    def peek(self, item_id: str) -> ContextItem | None:
        """Get an item without removing it."""
        return self._items.get(item_id)

    def clear(self) -> None:
        """Clear all items from working memory."""
        self._items.clear()
        self._eviction_queue.clear()

    def _rebuild_queue(self) -> None:
        """Rebuild the eviction priority queue from current items."""
        self._eviction_queue = [
            (item.priority, -item.timestamp, item_id)
            for item_id, item in self._items.items()
        ]

    def _evict_if_over_budget(self) -> None:
        """Evict lowest-priority items until under the token budget."""
        while self.current_tokens > self._max_tokens and self._items:
            if not self._eviction_queue:
                self._rebuild_queue()
            if not self._eviction_queue:
                break
            _prio, _neg_ts, item_id = heappop(self._eviction_queue)
            if item_id in self._items:
                del self._items[item_id]

    @property
    def current_tokens(self) -> int:
        """Total estimated token count of all items."""
        return sum(item.token_estimate for item in self._items.values())

    @property
    def item_count(self) -> int:
        """Number of items currently in working memory."""
        return len(self._items)

    @property
    def remaining_tokens(self) -> int:
        """Token budget remaining."""
        return max(0, self._max_tokens - self.current_tokens)

    @property
    def utilization(self) -> float:
        """Fraction [0.0, 1.0] of the token budget used."""
        if self._max_tokens == 0:
            return 0.0
        return min(1.0, self.current_tokens / self._max_tokens)

    def items(self) -> list[ContextItem]:
        """Return all items, ordered by priority (highest first)."""
        return sorted(self._items.values(), key=lambda i: (-i.priority, -i.timestamp))

    def update_priority(self, item_id: str, new_priority: int) -> ContextItem:
        """Update the priority of an item (immutable pattern)."""
        old_item = self.peek(item_id)
        if old_item is None:
            raise MemoryNotFoundError(item_id, "working_memory")
        updated = old_item.with_priority(new_priority)
        self._items[item_id] = updated
        self._rebuild_queue()
        return updated

    def summary(self) -> dict[str, Any]:
        """Produce a summary of working memory state."""
        return {
            "item_count": self.item_count,
            "max_tokens": self._max_tokens,
            "current_tokens": self.current_tokens,
            "remaining_tokens": self.remaining_tokens,
            "utilization": self.utilization,
        }
