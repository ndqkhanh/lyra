"""Named knowledge blocks that survive compaction cycles.

Knowledge blocks are named, priority-ranked data units that the compaction
system must preserve according to their priority level.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from .exceptions import KnowledgeBlockNotFoundError


class PriorityLevel(Enum):
    """Priority levels for knowledge blocks.

    CRITICAL: Never compacted — always preserved verbatim.
    HIGH: Compacted last, only when absolutely necessary.
    NORMAL: Compacted if context pressure is moderate or higher.
    LOW: Compacted first when any compaction is needed.
    """

    CRITICAL = auto()
    HIGH = auto()
    NORMAL = auto()
    LOW = auto()


@dataclass(frozen=True)
class KnowledgeBlock:
    """An immutable knowledge block that can survive compaction cycles.

    Attributes:
        block_id: Unique identifier for the block.
        name: Human-readable name.
        content: The actual block content.
        priority: Priority level controlling compaction behavior.
        tags: Categorization tags for grouping and filtering.
        created_at: Unix timestamp of creation.
        last_accessed: Unix timestamp of last access.
        compaction_survival_count: Number of compaction cycles survived.
    """

    block_id: str
    name: str
    content: str
    priority: PriorityLevel = PriorityLevel.NORMAL
    tags: tuple[str, ...] = field(default_factory=tuple)
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    compaction_survival_count: int = 0

    def touch(self) -> KnowledgeBlock:
        """Return a new KnowledgeBlock with updated last_accessed time."""
        return KnowledgeBlock(
            block_id=self.block_id,
            name=self.name,
            content=self.content,
            priority=self.priority,
            tags=self.tags,
            created_at=self.created_at,
            last_accessed=time.time(),
            compaction_survival_count=self.compaction_survival_count,
        )

    def mark_survived(self) -> KnowledgeBlock:
        """Return a new KnowledgeBlock incremented survival count."""
        return KnowledgeBlock(
            block_id=self.block_id,
            name=self.name,
            content=self.content,
            priority=self.priority,
            tags=self.tags,
            created_at=self.created_at,
            last_accessed=self.last_accessed,
            compaction_survival_count=self.compaction_survival_count + 1,
        )

    @property
    def token_estimate(self) -> int:
        """Rough token estimate (4 chars per token)."""
        return max(1, len(self.content) // 4)

    @property
    def age_seconds(self) -> float:
        """Age of the block in seconds."""
        return time.time() - self.created_at


class KnowledgeBlockRegistry:
    """Registry that manages knowledge blocks across compaction cycles.

    Provides registration, lookup, filtering, and survival tracking.
    """

    def __init__(self) -> None:
        self._blocks: dict[str, KnowledgeBlock] = {}
        self._compaction_history: list[dict[str, Any]] = []

    def register(self, block: KnowledgeBlock) -> KnowledgeBlock:
        """Register a knowledge block.

        Args:
            block: The block to register. If block_id already exists, replaces it.

        Returns:
            The registered block.
        """
        self._blocks[block.block_id] = block
        return block

    def unregister(self, block_id: str) -> bool:
        """Unregister a knowledge block.

        Args:
            block_id: ID of the block to remove.

        Returns:
            True if removed, False if not found.
        """
        if block_id in self._blocks:
            del self._blocks[block_id]
            return True
        return False

    def get(self, block_id: str) -> KnowledgeBlock:
        """Get a knowledge block by ID.

        Args:
            block_id: The block ID.

        Returns:
            The knowledge block.

        Raises:
            KnowledgeBlockNotFoundError: If block_id is not registered.
        """
        block = self._blocks.get(block_id)
        if block is None:
            raise KnowledgeBlockNotFoundError(block_id)
        return block

    def get_or_none(self, block_id: str) -> KnowledgeBlock | None:
        """Get a knowledge block, returning None if not found."""
        return self._blocks.get(block_id)

    def list(self, priority: PriorityLevel | None = None) -> list[KnowledgeBlock]:
        """List all blocks, optionally filtered by priority.

        Args:
            priority: Optional priority filter.

        Returns:
            List of matching blocks sorted by priority (CRITICAL first).
        """
        blocks = list(self._blocks.values())
        if priority is not None:
            blocks = [b for b in blocks if b.priority == priority]
        order = {
            PriorityLevel.CRITICAL: 0,
            PriorityLevel.HIGH: 1,
            PriorityLevel.NORMAL: 2,
            PriorityLevel.LOW: 3,
        }
        return sorted(blocks, key=lambda b: (order.get(b.priority, 99), b.name))

    def find_by_tag(self, tag: str) -> list[KnowledgeBlock]:
        """Find blocks with a specific tag.

        Args:
            tag: Tag to search for.

        Returns:
            List of blocks with the given tag.
        """
        return [b for b in self._blocks.values() if tag in b.tags]

    def get_total_tokens(self) -> int:
        """Get total estimated tokens for all registered blocks."""
        return sum(b.token_estimate for b in self._blocks.values())

    def get_count(self) -> int:
        """Get number of registered blocks."""
        return len(self._blocks)

    def record_compaction_cycle(
        self, blocks_before: int, tokens_before: int, blocks_after: int, tokens_after: int
    ) -> None:
        """Record a compaction cycle for tracking.

        Args:
            blocks_before: Number of blocks before compaction.
            tokens_before: Total tokens before compaction.
            blocks_after: Number of blocks after compaction.
            tokens_after: Total tokens after compaction.
        """
        self._compaction_history.append({
            "timestamp": time.time(),
            "blocks_before": blocks_before,
            "tokens_before": tokens_before,
            "blocks_after": blocks_after,
            "tokens_after": tokens_after,
            "blocks_removed": blocks_before - blocks_after,
            "tokens_saved": tokens_before - tokens_after,
        })

    @property
    def compaction_history(self) -> list[dict[str, Any]]:
        """Get compaction cycle history."""
        return list(self._compaction_history)

    @property
    def summary(self) -> dict[str, Any]:
        """Get registry summary."""
        return {
            "total_blocks": self.get_count(),
            "total_tokens": self.get_total_tokens(),
            "by_priority": {
                p.name: len([b for b in self._blocks.values() if b.priority == p])
                for p in PriorityLevel
            },
            "compaction_cycles": len(self._compaction_history),
            "total_tokens_saved": sum(
                c["tokens_saved"] for c in self._compaction_history
            ),
        }
