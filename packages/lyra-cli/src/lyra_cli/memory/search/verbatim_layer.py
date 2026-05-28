"""Verbatim layer — wires MemPalace verbatim cache into retrieval pipeline.

Provides O(1) exact-match recall as Tier 1 retrieval before BM25/vector
search. Uses the VerbatimCache from lyra_memory for position-indexed
verbatim-first retrieval.
"""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass(frozen=True)
class VerbatimHit:
    position: int
    content: str
    access_count: int
    elapsed_us: float


class VerbatimLayer:
    """Retrieval adapter for MemPalace-style verbatim cache.

    Queries the verbatim cache first (Tier 1) before falling through
    to BM25/vector/RRF. Exact matches return in O(1); cache misses
    fall through to the next retrieval tier.
    """

    def __init__(self, verbatim_cache: object | None = None) -> None:
        self._cache = verbatim_cache
        self._hits: int = 0
        self._misses: int = 0

    def wire(self, verbatim_cache: object) -> None:
        self._cache = verbatim_cache

    def lookup(self, query: str) -> str | None:
        if self._cache is None:
            self._misses += 1
            return None

        try:
            result = self._cache.lookup(query)  # type: ignore[union-attr]
            if result:
                self._hits += 1
                return str(result)
            self._misses += 1
            return None
        except Exception:
            self._misses += 1
            return None

    def lookup_exact(self, query: str) -> VerbatimHit | None:
        if self._cache is None:
            return None

        start = time.perf_counter()
        try:
            result = self._cache.lookup_exact(query)  # type: ignore[union-attr]
            elapsed_us = (time.perf_counter() - start) * 1_000_000
            if result is not None:
                self._hits += 1
                content = result.content if hasattr(result, 'content') else str(result)
                access = result.access_count if hasattr(result, 'access_count') else 1
                return VerbatimHit(
                    position=getattr(result, 'position_index', -1),
                    content=content,
                    access_count=access,
                    elapsed_us=round(elapsed_us, 1),
                )
        except Exception:
            pass
        self._misses += 1
        return None

    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return round(self._hits / max(total, 1), 4)

    def stats(self) -> dict:
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self.hit_rate(),
            "wired": self._cache is not None,
        }
