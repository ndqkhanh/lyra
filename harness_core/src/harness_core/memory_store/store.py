"""MemoryStore — typed CRUD + retrieval over MemoryItems.

In-process default implementation. Production wires a vector-backed
implementation through the same API surface; the keyword-based
:meth:`search` is the cold-start fallback that's testable without an
embedder.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from .types import MemoryItem, MemoryKind, RetrievalSpec


@dataclass
class MemoryStore:
    """In-memory typed memory store.

    >>> store = MemoryStore()
    >>> item = store.write(
    ...     kind=MemoryKind.SEMANTIC,
    ...     content="Paris is the capital of France.",
    ...     tags=("geography",),
    ... )
    >>> hits = store.search(RetrievalSpec(query="paris"))
    >>> hits[0].content
    'Paris is the capital of France.'
    """

    _items: dict[str, MemoryItem] = field(default_factory=dict)

    # --- CRUD -------------------------------------------------------------

    def write(
        self,
        *,
        kind: MemoryKind,
        content: str,
        namespace: str = "default",
        importance: float = 0.5,
        tags: tuple[str, ...] = (),
        metadata: Optional[dict] = None,
    ) -> MemoryItem:
        """Insert a new item; returns the created MemoryItem."""
        item = MemoryItem.create(
            kind=kind,
            content=content,
            namespace=namespace,
            importance=importance,
            tags=tags,
            metadata=metadata,
        )
        self._items[item.item_id] = item
        return item

    def insert(self, item: MemoryItem) -> MemoryItem:
        """Insert an existing MemoryItem (e.g., recovered from disk)."""
        if item.item_id in self._items:
            raise ValueError(f"item_id {item.item_id!r} already exists")
        self._items[item.item_id] = item
        return item

    def get(self, item_id: str, *, touch: bool = False) -> Optional[MemoryItem]:
        """Retrieve by id. If ``touch=True``, update accessed_at + access_count."""
        item = self._items.get(item_id)
        if item is None:
            return None
        if touch:
            updated = item.touched()
            self._items[item_id] = updated
            return updated
        return item

    def delete(self, item_id: str) -> bool:
        if item_id in self._items:
            del self._items[item_id]
            return True
        return False

    def update_importance(
        self,
        item_id: str,
        importance: float,
    ) -> Optional[MemoryItem]:
        """Update an item's importance; returns updated item or None if missing."""
        item = self._items.get(item_id)
        if item is None:
            return None
        updated = item.with_importance(importance)
        self._items[item_id] = updated
        return updated

    def __len__(self) -> int:
        return len(self._items)

    def __contains__(self, item_id: object) -> bool:
        return isinstance(item_id, str) and item_id in self._items

    # --- Retrieval --------------------------------------------------------

    def search(self, spec: RetrievalSpec) -> list[MemoryItem]:
        """Retrieve top-k items matching the spec.

        Filtering: kind + namespace + tags + min_importance.
        Scoring: substring-overlap-based when ``spec.query`` is non-empty;
        otherwise ranked by ``sort_by``.
        """
        candidates = [
            item for item in self._items.values()
            if self._passes_filter(item, spec)
        ]
        if spec.query:
            scored = [
                (self._keyword_score(item.content, spec.query), item)
                for item in candidates
            ]
            scored = [(s, i) for s, i in scored if s > 0]
            if spec.sort_by == "score":
                scored.sort(key=lambda si: (-si[0], -si[1].importance, si[1].item_id))
            else:
                scored = self._secondary_sort(scored, spec.sort_by)
            return [i for _, i in scored[:spec.top_k]]
        # No query → rank by sort_by directly.
        ranked = self._rank(candidates, spec.sort_by)
        return ranked[:spec.top_k]

    @staticmethod
    def _passes_filter(item: MemoryItem, spec: RetrievalSpec) -> bool:
        if spec.kind is not None and item.kind != spec.kind:
            return False
        if spec.namespace is not None and item.namespace != spec.namespace:
            return False
        if spec.tags and not spec.tags.issubset(item.tags):
            return False
        if item.importance < spec.min_importance:
            return False
        return True

    @staticmethod
    def _keyword_score(content: str, query: str) -> float:
        """Simple substring-overlap score in [0, 1].

        Counts how many query tokens appear in the content (case-insensitive),
        normalised by the number of query tokens. Production wires embedding-
        based retrieval; this is the deterministic cold-start fallback.
        """
        if not query.strip():
            return 0.0
        content_lower = content.lower()
        query_tokens = [t for t in query.lower().split() if t]
        if not query_tokens:
            return 0.0
        matches = sum(1 for t in query_tokens if t in content_lower)
        return matches / len(query_tokens)

    def _rank(
        self,
        items: list[MemoryItem],
        sort_by: str,
    ) -> list[MemoryItem]:
        if sort_by == "recency":
            return sorted(items, key=lambda i: -i.accessed_at)
        if sort_by == "importance":
            return sorted(items, key=lambda i: (-i.importance, -i.accessed_at))
        if sort_by == "access_count":
            return sorted(items, key=lambda i: (-i.access_count, -i.importance))
        # "score" with no query → fall back to importance-then-recency.
        return sorted(items, key=lambda i: (-i.importance, -i.accessed_at))

    @staticmethod
    def _secondary_sort(
        scored: list[tuple[float, MemoryItem]],
        sort_by: str,
    ) -> list[tuple[float, MemoryItem]]:
        if sort_by == "recency":
            return sorted(scored, key=lambda si: -si[1].accessed_at)
        if sort_by == "importance":
            return sorted(scored, key=lambda si: -si[1].importance)
        if sort_by == "access_count":
            return sorted(scored, key=lambda si: -si[1].access_count)
        return sorted(scored, key=lambda si: -si[0])

    # --- Maintenance ------------------------------------------------------

    def garbage_collect(
        self,
        *,
        max_age_seconds: Optional[float] = None,
        keep_top_k: Optional[int] = None,
        kind: Optional[MemoryKind] = None,
    ) -> int:
        """Drop stale items. Returns count removed.

        - ``max_age_seconds``: drop items whose ``accessed_at`` is older than
          this. Use to prune cold WORKING memory.
        - ``keep_top_k``: keep only the top-k by ``importance + recency``;
          drop the rest. Operates on the whole store or one ``kind``.
        - ``kind``: when set, scope GC to one memory kind.
        """
        before = len(self._items)
        now = time.time()

        # Age-based eviction.
        if max_age_seconds is not None:
            cutoff = now - max_age_seconds
            for iid in [
                i for i, item in self._items.items()
                if (kind is None or item.kind == kind) and item.accessed_at < cutoff
            ]:
                del self._items[iid]

        # Top-k cap.
        if keep_top_k is not None and keep_top_k >= 0:
            scope = (
                [i for i in self._items.values() if i.kind == kind]
                if kind is not None
                else list(self._items.values())
            )
            ranked = sorted(
                scope,
                key=lambda i: (-i.importance, -i.accessed_at),
            )
            keep_ids = {i.item_id for i in ranked[:keep_top_k]}
            for iid in list(self._items.keys()):
                in_scope = (kind is None) or (self._items[iid].kind == kind)
                if in_scope and iid not in keep_ids:
                    del self._items[iid]

        return before - len(self._items)

    def clear_namespace(self, namespace: str) -> int:
        """Drop every item in the given namespace; returns count removed."""
        ids = [i for i, item in self._items.items() if item.namespace == namespace]
        for iid in ids:
            del self._items[iid]
        return len(ids)

    # --- Observability ----------------------------------------------------

    def stats(self) -> dict[str, int]:
        c = {k.value: 0 for k in MemoryKind}
        namespaces: set[str] = set()
        tags: set[str] = set()
        for item in self._items.values():
            c[item.kind.value] += 1
            namespaces.add(item.namespace)
            tags.update(item.tags)
        c["total"] = len(self._items)
        c["namespaces"] = len(namespaces)
        c["distinct_tags"] = len(tags)
        return c


__all__ = ["MemoryStore"]
