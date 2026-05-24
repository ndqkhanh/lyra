"""MemoryItem + MemoryKind + RetrievalSpec — typed memory data model."""
from __future__ import annotations

import enum
import time
import uuid
from dataclasses import dataclass, field, replace
from typing import Any, Optional


class MemoryKind(str, enum.Enum):
    """The four canonical memory kinds.

    Per [docs/184] §"layered memory" synthesis — these mirror cognitive-
    architecture conventions. Procedural memory typically lives in
    :mod:`harness_core.skill_auto` (PromotedSkill); the kind is here for
    completeness when projects choose to store skill-shaped items in the
    same memory store.
    """

    SEMANTIC = "semantic"
    EPISODIC = "episodic"
    WORKING = "working"
    PROCEDURAL = "procedural"


@dataclass(frozen=True)
class MemoryItem:
    """One immutable memory item.

    >>> item = MemoryItem.create(
    ...     kind=MemoryKind.SEMANTIC,
    ...     content="The capital of France is Paris.",
    ...     namespace="default",
    ...     importance=0.8,
    ...     tags=("geography", "europe"),
    ... )
    >>> item.kind == MemoryKind.SEMANTIC
    True
    """

    item_id: str
    kind: MemoryKind
    content: str
    namespace: str = "default"
    created_at: float = 0.0
    accessed_at: float = 0.0
    access_count: int = 0
    importance: float = 0.5
    tags: frozenset[str] = field(default_factory=frozenset)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.item_id:
            raise ValueError("item_id must be non-empty")
        if not self.content:
            raise ValueError("content must be non-empty")
        if not self.namespace:
            raise ValueError("namespace must be non-empty")
        if not 0.0 <= self.importance <= 1.0:
            raise ValueError(f"importance must be in [0, 1], got {self.importance}")
        if self.access_count < 0:
            raise ValueError(f"access_count must be >= 0, got {self.access_count}")

    @classmethod
    def create(
        cls,
        *,
        kind: MemoryKind,
        content: str,
        namespace: str = "default",
        importance: float = 0.5,
        tags: tuple[str, ...] = (),
        metadata: Optional[dict[str, Any]] = None,
        item_id: Optional[str] = None,
        timestamp: Optional[float] = None,
    ) -> "MemoryItem":
        """Construct with auto-generated ``item_id`` (UUID4) and current time."""
        ts = timestamp if timestamp is not None else time.time()
        return cls(
            item_id=item_id or str(uuid.uuid4()),
            kind=kind,
            content=content,
            namespace=namespace,
            created_at=ts,
            accessed_at=ts,
            access_count=0,
            importance=importance,
            tags=frozenset(tags),
            metadata=dict(metadata or {}),
        )

    def touched(self, *, timestamp: Optional[float] = None) -> "MemoryItem":
        """Return a copy with ``accessed_at`` updated + ``access_count`` incremented."""
        return replace(
            self,
            accessed_at=timestamp if timestamp is not None else time.time(),
            access_count=self.access_count + 1,
        )

    def with_importance(self, importance: float) -> "MemoryItem":
        """Return a copy with ``importance`` updated; raises on invalid input."""
        if not 0.0 <= importance <= 1.0:
            raise ValueError(f"importance must be in [0, 1], got {importance}")
        return replace(self, importance=importance)


@dataclass(frozen=True)
class RetrievalSpec:
    """Filter spec for memory retrieval queries.

    >>> spec = RetrievalSpec(query="paris", kind=MemoryKind.SEMANTIC, top_k=5)
    >>> spec.top_k
    5
    """

    query: str = ""  # keyword / substring; empty = no text filter
    kind: Optional[MemoryKind] = None
    namespace: Optional[str] = None
    tags: frozenset[str] = field(default_factory=frozenset)
    min_importance: float = 0.0
    top_k: int = 10
    sort_by: str = "score"  # "score" | "recency" | "importance" | "access_count"

    def __post_init__(self) -> None:
        if self.top_k < 1:
            raise ValueError(f"top_k must be >= 1, got {self.top_k}")
        if not 0.0 <= self.min_importance <= 1.0:
            raise ValueError(
                f"min_importance must be in [0, 1], got {self.min_importance}"
            )
        if self.sort_by not in ("score", "recency", "importance", "access_count"):
            raise ValueError(f"unknown sort_by: {self.sort_by!r}")


__all__ = ["MemoryItem", "MemoryKind", "RetrievalSpec"]
