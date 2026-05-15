"""Memory backend Protocol + in-memory default (Phase CE.3, P2-5).

Lyra's existing L5 memory tools (``memory_tools.py``) couple search /
write / get directly to whatever store is in front of them. That's
fine for single-user local mode; it isn't enough once team-mode wants
a shared external vector DB.

This module names the contract — :class:`MemoryBackend` — so future
adapters (chroma-remote, pinecone, qdrant, …) can plug in without
touching call sites. An :class:`InMemoryBackend` ships as the
default; it's authoritative for tests and small sessions and serves
as the reference behaviour every adapter must reproduce.

No real third-party backends ship today. The point of the file is
the *contract* — adapters are a v2 work item.
"""
from __future__ import annotations

import time
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class MemoryRecord:
    """One stored memory item."""

    id: str
    kind: str  # fact | decision | mistake | preference | trace_summary | …
    content: str
    ts: float
    tags: tuple[str, ...] = ()
    is_private: bool = False
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id or not self.id.strip():
            raise ValueError("MemoryRecord.id must be non-empty")
        if not self.kind or not self.kind.strip():
            raise ValueError("MemoryRecord.kind must be non-empty")


@dataclass(frozen=True)
class SearchHit:
    """One search result — minimal envelope around a record."""

    record: MemoryRecord
    score: float
    source: str = "fts"  # fts | semantic | both

    def __post_init__(self) -> None:
        if self.score < 0.0:
            raise ValueError("SearchHit.score must be >= 0")


# ────────────────────────────────────────────────────────────────
# Protocol — every backend implements this
# ────────────────────────────────────────────────────────────────


class MemoryBackend(Protocol):
    """Storage interface for L5 memory records.

    Backends must be deterministic for a fixed input sequence. The
    private-tag rule (``is_private`` records are excluded from
    :meth:`search` and :meth:`timeline` results) is part of the
    contract — implementations that proxy a third-party DB must
    enforce it client-side if the DB cannot.
    """

    def write(self, record: MemoryRecord) -> MemoryRecord: ...
    def get(self, record_id: str) -> MemoryRecord | None: ...
    def delete(self, record_id: str) -> bool: ...
    def search(
        self, query: str, *, limit: int = 5, include_private: bool = False
    ) -> list[SearchHit]: ...
    def timeline(
        self,
        *,
        tag: str | None = None,
        since: float | None = None,
        until: float | None = None,
        limit: int = 10,
        include_private: bool = False,
    ) -> list[MemoryRecord]: ...


# ────────────────────────────────────────────────────────────────
# InMemoryBackend — the default + reference implementation
# ────────────────────────────────────────────────────────────────


class InMemoryBackend:
    """Authoritative reference implementation.

    Thread-safety: single-writer assumed; callers serialise. Good
    enough for v1 and for tests; real concurrent backends override.
    """

    def __init__(self) -> None:
        self._store: dict[str, MemoryRecord] = {}

    # ------------------------------------------------------------------ write
    def write(self, record: MemoryRecord) -> MemoryRecord:
        """Insert or overwrite. Idempotent by ``record.id``."""
        self._store[record.id] = record
        return record

    def get(self, record_id: str) -> MemoryRecord | None:
        return self._store.get(record_id)

    def delete(self, record_id: str) -> bool:
        return self._store.pop(record_id, None) is not None

    # ------------------------------------------------------------------ query
    def search(
        self, query: str, *, limit: int = 5, include_private: bool = False
    ) -> list[SearchHit]:
        if limit <= 0:
            raise ValueError(f"limit must be > 0, got {limit}")
        query = query.strip().lower()
        if not query:
            return []
        terms = [t for t in query.split() if t]
        hits: list[SearchHit] = []
        for record in self._store.values():
            if record.is_private and not include_private:
                continue
            haystack = record.content.lower()
            tag_haystack = " ".join(record.tags).lower()
            overlap = sum(
                1 for t in terms if t in haystack or t in tag_haystack
            )
            if overlap == 0:
                continue
            score = overlap / max(1, len(terms))
            hits.append(SearchHit(record=record, score=score, source="fts"))
        hits.sort(key=lambda h: (-h.score, h.record.ts))
        return hits[:limit]

    def timeline(
        self,
        *,
        tag: str | None = None,
        since: float | None = None,
        until: float | None = None,
        limit: int = 10,
        include_private: bool = False,
    ) -> list[MemoryRecord]:
        if limit <= 0:
            raise ValueError(f"limit must be > 0, got {limit}")
        rows = list(self._store.values())
        if tag is not None:
            rows = [r for r in rows if tag in r.tags]
        if since is not None:
            rows = [r for r in rows if r.ts >= since]
        if until is not None:
            rows = [r for r in rows if r.ts <= until]
        if not include_private:
            rows = [r for r in rows if not r.is_private]
        rows.sort(key=lambda r: -r.ts)
        return rows[:limit]

    # ------------------------------------------------------------------ admin
    def __len__(self) -> int:
        return len(self._store)

    def all(self) -> Iterable[MemoryRecord]:
        return self._store.values()


def make_record(
    *,
    id: str,
    kind: str,
    content: str,
    tags: tuple[str, ...] = (),
    is_private: bool = False,
    ts: float | None = None,
    metadata: dict[str, str] | None = None,
) -> MemoryRecord:
    """Builder with a now() default — saves callers a small ritual."""
    return MemoryRecord(
        id=id,
        kind=kind,
        content=content,
        tags=tags,
        is_private=is_private,
        ts=time.time() if ts is None else ts,
        metadata=dict(metadata or {}),
    )


__all__ = [
    "InMemoryBackend",
    "MemoryBackend",
    "MemoryRecord",
    "SearchHit",
    "make_record",
]
