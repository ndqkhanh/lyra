"""Grouping strategies — cluster MemoryItems for joint summarization.

Two built-ins:

    - :class:`TagGrouping` — items sharing >= ``min_shared_tags`` go together.
      Cheap; correct when memory pipelines tag items consistently.
    - :class:`TokenJaccardGrouping` — greedy single-link agglomerative on
      Jaccard token overlap. The textual fallback when tagging is sparse.

Both are deterministic and dependency-free. Production may wire embedding-
based clustering through the same :class:`GroupingStrategy` Protocol.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..memory_store import MemoryItem


@dataclass
class TagGrouping:
    """Group items by tag overlap.

    Two items belong to the same group when they share at least
    ``min_shared_tags`` tags. Untagged items each form a singleton group.

    >>> from harness_core.memory_store import MemoryItem, MemoryKind
    >>> a = MemoryItem.create(kind=MemoryKind.EPISODIC, content="x", tags=("alpha",))
    >>> b = MemoryItem.create(kind=MemoryKind.EPISODIC, content="y", tags=("alpha",))
    >>> c = MemoryItem.create(kind=MemoryKind.EPISODIC, content="z", tags=("beta",))
    >>> groups = TagGrouping().group([a, b, c])
    >>> sorted(len(g) for g in groups)
    [1, 2]
    """

    min_shared_tags: int = 1

    def __post_init__(self) -> None:
        if self.min_shared_tags < 1:
            raise ValueError(
                f"min_shared_tags must be >= 1, got {self.min_shared_tags}"
            )

    def group(self, items: list[MemoryItem]) -> list[list[MemoryItem]]:
        if not items:
            return []
        groups: list[list[MemoryItem]] = []
        for item in items:
            placed = False
            for group in groups:
                if self._shares_enough(item, group[0]):
                    group.append(item)
                    placed = True
                    break
            if not placed:
                groups.append([item])
        return groups

    def _shares_enough(self, a: MemoryItem, b: MemoryItem) -> bool:
        return len(a.tags & b.tags) >= self.min_shared_tags


@dataclass
class TokenJaccardGrouping:
    """Greedy single-link agglomerative clustering on Jaccard token overlap.

    Two items merge when ``jaccard(tokens(a), tokens(b)) >= threshold``.
    Single-link: an item joins a group if it overlaps with *any* member.

    >>> g = TokenJaccardGrouping(threshold=0.3)
    >>> g.threshold
    0.3
    """

    threshold: float = 0.4

    def __post_init__(self) -> None:
        if not 0.0 < self.threshold <= 1.0:
            raise ValueError(
                f"threshold must be in (0, 1], got {self.threshold}"
            )

    def group(self, items: list[MemoryItem]) -> list[list[MemoryItem]]:
        if not items:
            return []
        # Pre-tokenize once.
        tokens = [self._tokens(it.content) for it in items]
        groups: list[list[int]] = []  # indices into items
        for i in range(len(items)):
            placed = False
            for g in groups:
                if any(self._jaccard(tokens[i], tokens[j]) >= self.threshold for j in g):
                    g.append(i)
                    placed = True
                    break
            if not placed:
                groups.append([i])
        return [[items[i] for i in g] for g in groups]

    @staticmethod
    def _tokens(text: str) -> frozenset[str]:
        return frozenset(t for t in text.lower().split() if t)

    @staticmethod
    def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
        if not a and not b:
            return 0.0
        union = a | b
        if not union:
            return 0.0
        return len(a & b) / len(union)


__all__ = ["TagGrouping", "TokenJaccardGrouping"]
