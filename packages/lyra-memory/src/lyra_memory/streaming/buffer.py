"""Ring buffer for streaming memory events with backpressure handling.

Provides a bounded circular buffer for memory events with:
  - Fixed capacity with automatic overwrite of oldest entries
  - Async-safe operations for concurrent producers/consumers
  - Backpressure signaling when buffer approaches capacity
  - Batch retrieval for efficient downstream processing
  - Memory deduplication based on content hash
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class BufferState(Enum):
    """Buffer operational state."""

    READY = "ready"
    BACKPRESSURE = "backpressure"
    FULL = "full"
    DRAINING = "draining"


@dataclass(frozen=True)
class MemoryEvent:
    """A single memory event in the streaming buffer."""

    event_id: str
    content: str
    content_hash: str
    session_id: str
    timestamp: float
    memory_type: str
    confidence: float
    entities: tuple[str, ...] = field(default_factory=tuple)
    metadata: tuple[tuple[str, str], ...] = field(default_factory=tuple)

    @classmethod
    def create(
        cls,
        content: str,
        session_id: str,
        memory_type: str = "episodic",
        confidence: float = 0.7,
        entities: list[str] | None = None,
        metadata: dict[str, str] | None = None,
    ) -> MemoryEvent:
        """Create a new memory event with computed hash."""
        content_hash = _compute_hash(content)
        event_id = f"evt-{int(time.time() * 1000000)}"

        return cls(
            event_id=event_id,
            content=content,
            content_hash=content_hash,
            session_id=session_id,
            timestamp=time.time(),
            memory_type=memory_type,
            confidence=confidence,
            entities=tuple(entities or []),
            metadata=tuple(sorted((metadata or {}).items())),
        )


@dataclass
class StreamBuffer:
    """Ring buffer for streaming memory events.

    Implements a bounded circular buffer with automatic overwrite of oldest
    entries when capacity is reached. Provides backpressure signaling and
    deduplication based on content hash.

    Usage::

        buffer = StreamBuffer(capacity=1000, backpressure_threshold=0.8)

        # Producer
        event = MemoryEvent.create("Important fact", session_id="sess-123")
        buffer.push(event)

        # Consumer
        batch = buffer.pop_batch(size=10)
        for event in batch:
            process(event)

    Args:
        capacity: Maximum number of events in buffer.
        backpressure_threshold: Fill ratio (0.0-1.0) triggering backpressure.
        enable_dedup: Whether to deduplicate events by content hash.
        dedup_window_size: Number of recent hashes to track for dedup.
    """

    capacity: int = 1000
    backpressure_threshold: float = 0.8
    enable_dedup: bool = True
    dedup_window_size: int = 500

    _buffer: deque[MemoryEvent] = field(default_factory=deque)
    _seen_hashes: deque[str] = field(default_factory=deque)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    _total_pushed: int = 0
    _total_popped: int = 0
    _total_duplicates: int = 0
    _total_overwrites: int = 0

    def __post_init__(self) -> None:
        """Initialize buffer with capacity constraints."""
        if self.capacity <= 0:
            raise ValueError("capacity must be positive")
        if not 0.0 <= self.backpressure_threshold <= 1.0:
            raise ValueError("backpressure_threshold must be in [0.0, 1.0]")

    def push(self, event: MemoryEvent) -> bool:
        """Push an event to the buffer.

        Args:
            event: Memory event to push.

        Returns:
            True if event was added, False if deduplicated.
        """
        # Deduplication check
        if self.enable_dedup and event.content_hash in self._seen_hashes:
            self._total_duplicates += 1
            return False

        # Add to buffer
        if len(self._buffer) >= self.capacity:
            # Overwrite oldest
            oldest = self._buffer.popleft()
            self._total_overwrites += 1
            # Remove oldest hash from dedup window
            if self.enable_dedup and oldest.content_hash in self._seen_hashes:
                # Remove from deque (linear scan, but dedup_window_size is bounded)
                try:
                    self._seen_hashes.remove(oldest.content_hash)
                except ValueError:
                    pass

        self._buffer.append(event)
        self._total_pushed += 1

        # Update dedup window
        if self.enable_dedup:
            self._seen_hashes.append(event.content_hash)
            if len(self._seen_hashes) > self.dedup_window_size:
                self._seen_hashes.popleft()

        return True

    async def push_async(self, event: MemoryEvent) -> bool:
        """Async version of push with lock protection.

        Args:
            event: Memory event to push.

        Returns:
            True if event was added, False if deduplicated.
        """
        async with self._lock:
            return self.push(event)

    def pop_batch(self, size: int) -> list[MemoryEvent]:
        """Pop a batch of events from the buffer.

        Args:
            size: Maximum number of events to pop.

        Returns:
            List of events (may be smaller than size if buffer has fewer).
        """
        batch: list[MemoryEvent] = []
        actual_size = min(size, len(self._buffer))

        for _ in range(actual_size):
            if self._buffer:
                batch.append(self._buffer.popleft())
                self._total_popped += 1

        return batch

    async def pop_batch_async(self, size: int) -> list[MemoryEvent]:
        """Async version of pop_batch with lock protection.

        Args:
            size: Maximum number of events to pop.

        Returns:
            List of events.
        """
        async with self._lock:
            return self.pop_batch(size)

    def peek(self, count: int = 1) -> list[MemoryEvent]:
        """Peek at events without removing them.

        Args:
            count: Number of events to peek at.

        Returns:
            List of events (oldest first).
        """
        actual_count = min(count, len(self._buffer))
        return list(self._buffer)[:actual_count]

    def clear(self) -> int:
        """Clear all events from buffer.

        Returns:
            Number of events cleared.
        """
        count = len(self._buffer)
        self._buffer.clear()
        self._seen_hashes.clear()
        return count

    async def clear_async(self) -> int:
        """Async version of clear with lock protection.

        Returns:
            Number of events cleared.
        """
        async with self._lock:
            return self.clear()

    @property
    def size(self) -> int:
        """Current number of events in buffer."""
        return len(self._buffer)

    @property
    def fill_ratio(self) -> float:
        """Current fill ratio (0.0 to 1.0)."""
        return len(self._buffer) / self.capacity if self.capacity > 0 else 0.0

    @property
    def state(self) -> BufferState:
        """Current buffer state based on fill ratio."""
        ratio = self.fill_ratio
        if ratio >= 1.0:
            return BufferState.FULL
        elif ratio >= self.backpressure_threshold:
            return BufferState.BACKPRESSURE
        else:
            return BufferState.READY

    @property
    def has_backpressure(self) -> bool:
        """Whether buffer is in backpressure state."""
        return self.state in (BufferState.BACKPRESSURE, BufferState.FULL)

    @property
    def stats(self) -> dict[str, Any]:
        """Buffer statistics."""
        return {
            "size": self.size,
            "capacity": self.capacity,
            "fill_ratio": self.fill_ratio,
            "state": self.state.value,
            "total_pushed": self._total_pushed,
            "total_popped": self._total_popped,
            "total_duplicates": self._total_duplicates,
            "total_overwrites": self._total_overwrites,
            "dedup_enabled": self.enable_dedup,
            "dedup_window_size": len(self._seen_hashes),
        }


def _compute_hash(content: str) -> str:
    """Compute SHA-256 hash of content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


__all__ = [
    "BufferState",
    "MemoryEvent",
    "StreamBuffer",
]
