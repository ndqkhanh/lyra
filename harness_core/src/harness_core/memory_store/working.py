"""WorkingMemory — bounded scratchpad for current-task state.

Distinct from :class:`MemoryStore` because the working-memory contract is
*temporal* (FIFO with capacity cap) rather than *retrieval-driven*. Use for:

    - Current-task scratchpad (recent tool outputs, intermediate reasoning).
    - Per-turn dialog state.
    - Bounded thought-trail buffer.

For retrieval-style access (find-by-content), use :class:`MemoryStore` with
``kind=MemoryKind.WORKING``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .types import MemoryItem, MemoryKind


@dataclass
class WorkingMemory:
    """FIFO bounded buffer for current-task scratchpad.

    >>> wm = WorkingMemory(capacity=3)
    >>> wm.push(content="thought 1")
    >>> wm.push(content="thought 2")
    >>> wm.push(content="thought 3")
    >>> wm.push(content="thought 4")  # evicts thought 1
    >>> [i.content for i in wm.recent()]
    ['thought 4', 'thought 3', 'thought 2']
    """

    capacity: int = 50
    namespace: str = "default"
    _items: list[MemoryItem] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.capacity < 1:
            raise ValueError(f"capacity must be >= 1, got {self.capacity}")

    def push(
        self,
        *,
        content: str,
        importance: float = 0.5,
        tags: tuple[str, ...] = (),
        metadata: Optional[dict] = None,
    ) -> MemoryItem:
        """Append a new item; oldest evicted when capacity exceeded."""
        item = MemoryItem.create(
            kind=MemoryKind.WORKING,
            content=content,
            namespace=self.namespace,
            importance=importance,
            tags=tags,
            metadata=metadata,
        )
        self._items.append(item)
        # Evict oldest when over capacity.
        while len(self._items) > self.capacity:
            self._items.pop(0)
        return item

    def recent(self, n: int = 10) -> list[MemoryItem]:
        """Return the n most recent items, newest first."""
        if n < 0:
            raise ValueError(f"n must be >= 0, got {n}")
        return list(reversed(self._items[-n:]))

    def all(self) -> list[MemoryItem]:
        """Return all items, oldest first (insertion order)."""
        return list(self._items)

    def peek(self) -> Optional[MemoryItem]:
        """Look at the most recent item without removing it."""
        return self._items[-1] if self._items else None

    def clear(self) -> int:
        """Remove all items; returns count removed."""
        n = len(self._items)
        self._items.clear()
        return n

    def __len__(self) -> int:
        return len(self._items)

    def at_capacity(self) -> bool:
        return len(self._items) >= self.capacity

    @property
    def utilization(self) -> float:
        """Fraction of capacity used in [0, 1]."""
        return len(self._items) / self.capacity if self.capacity > 0 else 0.0


__all__ = ["WorkingMemory"]
