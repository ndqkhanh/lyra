"""
Three-Tier Memory Architecture — Working / Ingestion / Persistent.

Per SYNTHESIS.md §10.2: Lyra's memory architecture should be a THREE-TIER system:
1. **Working Memory** (COMPASS-style) — active context curation within a single run
2. **Ingestion Memory** (ExtAgents-style) — distribute large inputs across agents for parallel indexing
3. **Persistent Memory** (TKG + Field-Theoretic hybrid) — cross-session, multi-agent reasoning

Each tier serves a different timescale and input type:
- Working: within-single-run, seconds-minutes, active context
- Ingestion: single-run, massive static knowledge (codebases, docs), minutes-hours
- Persistent: across-runs, multi-session, hours-days, emergent collective memory

This module wires the three tiers together with a unified API. The tiers themselves
are implemented separately (lyra-context, lyra-memory/ingestion.py, lyra-memory/tree.py,
lyra-memory/field_memory.py) — tiered.py provides the orchestration layer.
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MemoryTier(str, Enum):
    """The three memory tiers."""
    WORKING = "working"       # Active session context
    INGESTION = "ingestion"   # Static knowledge indexing
    PERSISTENT = "persistent" # Cross-session reasoning


class RetrievalStrategy(str, Enum):
    """How to route a query across tiers."""
    WORKING_ONLY = "working_only"       # Check working memory only (fastest)
    WORKING_THEN_PERSISTENT = "wp"      # Working first, fall back to persistent
    ALL_TIERS = "all"                   # Search all tiers, merge results
    COST_SENSITIVE = "cost_sensitive"   # Route based on query complexity/cost


@dataclass
class TieredResult:
    """A single result from the tiered memory system."""
    content: str
    tier: MemoryTier
    score: float
    source_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TieredQueryResult:
    """Aggregated result from querying the tiered memory system."""
    results: list[TieredResult]
    tiers_searched: list[MemoryTier]
    total_time_ms: float
    query: str = ""


class TieredMemoryOrchestrator:
    """Orchestrates queries across the three memory tiers.

    Routes queries to the appropriate tier(s) based on:
    - Retrieval strategy (working-first, cost-sensitive, all-tiers)
    - Query type (factual → persistent, contextual → working, code → ingestion)
    - Cost budget (cheap tiers first, escalate only if needed)

    Tiers:
    1. Working Memory — fastest, most recent, limited capacity (lyra-context)
    2. Ingestion Memory — indexed codebases/docs, parallel agent processing
    3. Persistent Memory — TKG (graph-based) + Field Memory (PDE-based) hybrid
    """

    def __init__(
        self,
        working_memory: Any = None,      # lyra-context ContextManager
        ingestion_memory: Any = None,    # lyra-memory ingestion pipeline
        persistent_graph: Any = None,    # lyra-memory TKG
        persistent_field: Any = None,    # lyra-memory SemanticField
        default_strategy: RetrievalStrategy = RetrievalStrategy.COST_SENSITIVE,
    ) -> None:
        self._working = working_memory
        self._ingestion = ingestion_memory
        self._persistent_graph = persistent_graph
        self._persistent_field = persistent_field
        self._default_strategy = default_strategy
        self._query_count: int = 0
        self._tier_hits: dict[MemoryTier, int] = {
            MemoryTier.WORKING: 0,
            MemoryTier.INGESTION: 0,
            MemoryTier.PERSISTENT: 0,
        }

    def query(
        self,
        query: str,
        strategy: RetrievalStrategy | None = None,
        max_results: int = 10,
        query_embedding: Sequence[float] | None = None,
    ) -> TieredQueryResult:
        """Query the tiered memory system.

        Args:
            query: Natural language search query.
            strategy: Retrieval strategy override.
            max_results: Maximum results to return.
            query_embedding: Optional embedding for field-memory probing.

        Returns:
            TieredQueryResult with merged results from searched tiers.
        """
        strategy = strategy or self._default_strategy
        self._query_count += 1
        start = time.time()

        results: list[TieredResult] = []
        tiers_searched: list[MemoryTier] = []

        # Tier 1: Working Memory (always searched first — cheapest)
        if strategy != RetrievalStrategy.WORKING_ONLY:
            working_results = self._search_working(query, max_results)
            if working_results:
                results.extend(working_results)
                tiers_searched.append(MemoryTier.WORKING)
                self._tier_hits[MemoryTier.WORKING] += 1

        # If working memory found enough, return early (cost-sensitive)
        if strategy == RetrievalStrategy.WORKING_ONLY:
            pass
        elif strategy == RetrievalStrategy.WORKING_THEN_PERSISTENT and len(results) >= max_results:
            pass
        else:
            # Tier 2: Ingestion Memory (for code/docs queries)
            remaining = max_results - len(results)
            if remaining > 0 and self._ingestion is not None:
                ingestion_results = self._search_ingestion(query, remaining)
                if ingestion_results:
                    results.extend(ingestion_results)
                    tiers_searched.append(MemoryTier.INGESTION)
                    self._tier_hits[MemoryTier.INGESTION] += 1

            # Tier 3: Persistent Memory (TKG + Field)
            remaining = max_results - len(results)
            if remaining > 0:
                persistent_results = self._search_persistent(
                    query, remaining, query_embedding,
                )
                if persistent_results:
                    results.extend(persistent_results)
                    tiers_searched.append(MemoryTier.PERSISTENT)
                    self._tier_hits[MemoryTier.PERSISTENT] += 1

        elapsed_ms = (time.time() - start) * 1000
        return TieredQueryResult(
            results=results[:max_results],
            tiers_searched=tiers_searched,
            total_time_ms=round(elapsed_ms, 2),
            query=query,
        )

    def store(
        self,
        content: str,
        tier: MemoryTier,
        metadata: dict[str, Any] | None = None,
        embedding: Sequence[float] | None = None,
        importance: float = 0.5,
    ) -> str:
        """Store content in the specified memory tier.

        Returns the storage ID (or empty string if tier unavailable).
        """
        if tier == MemoryTier.WORKING and self._working is not None:
            # Store in working memory (active context)
            return self._store_working(content, metadata or {})
        elif tier == MemoryTier.INGESTION and self._ingestion is not None:
            return self._store_ingestion(content, metadata or {})
        elif tier == MemoryTier.PERSISTENT:
            # Store in both TKG and Field memory
            tkg_id = self._store_graph(content, metadata or {})
            if self._persistent_field is not None and embedding is not None:
                self._persistent_field.store(
                    token=tkg_id or f"mem_{int(time.time())}",
                    embedding=embedding,
                    importance=importance,
                    metadata=metadata or {},
                )
            return tkg_id
        return ""

    # -- Per-tier search (pluggable — replace with actual implementations) --

    def _search_working(self, query: str, limit: int) -> list[TieredResult]:
        """Search working memory (active session context)."""
        if self._working is None:
            return []
        try:
            # Delegate to lyra-context ContextManager
            results = self._working.search(query, limit=limit)
            return [
                TieredResult(
                    content=getattr(r, "content", str(r)),
                    tier=MemoryTier.WORKING,
                    score=getattr(r, "score", 0.5),
                    source_id=getattr(r, "id", ""),
                )
                for r in (results if isinstance(results, list) else [])
            ]
        except Exception:
            return []

    def _search_ingestion(self, query: str, limit: int) -> list[TieredResult]:
        """Search ingestion memory (indexed codebases/docs)."""
        if self._ingestion is None:
            return []
        try:
            results = self._ingestion.query(query, top_k=limit)
            return [
                TieredResult(
                    content=getattr(r, "content", str(r)),
                    tier=MemoryTier.INGESTION,
                    score=getattr(r, "score", 0.5),
                    source_id=getattr(r, "id", ""),
                )
                for r in (results if isinstance(results, list) else [])
            ]
        except Exception:
            return []

    def _search_persistent(
        self,
        query: str,
        limit: int,
        embedding: Sequence[float] | None = None,
    ) -> list[TieredResult]:
        """Search persistent memory (TKG graph + Field memory hybrid)."""
        results: list[TieredResult] = []

        # Search TKG (graph-based, exact)
        if self._persistent_graph is not None:
            try:
                graph_results = self._persistent_graph.search(query, limit=limit)
                for r in (graph_results if isinstance(graph_results, list) else []):
                    results.append(TieredResult(
                        content=getattr(r, "content", str(r)),
                        tier=MemoryTier.PERSISTENT,
                        score=getattr(r, "score", 0.5),
                        source_id=getattr(r, "id", ""),
                    ))
            except Exception:
                pass

        # Search Field Memory (PDE-based, fuzzy/associative)
        if self._persistent_field is not None and embedding is not None:
            try:
                field_results = self._persistent_field.probe(
                    embedding, top_k=limit,
                )
                for r in field_results:
                    results.append(TieredResult(
                        content=r.token,
                        tier=MemoryTier.PERSISTENT,
                        score=r.score,
                        source_id=r.token,
                        metadata={
                            "distance": r.distance,
                            "amplitude": r.amplitude,
                            "memory_type": "field",
                        },
                    ))
            except Exception:
                pass

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    # -- Per-tier storage ---------------------------------------------------

    def _store_working(self, content: str, metadata: dict) -> str:
        try:
            return self._working.store(content, **metadata)
        except Exception:
            return ""

    def _store_ingestion(self, content: str, metadata: dict) -> str:
        try:
            return self._ingestion.index(content, **metadata)
        except Exception:
            return ""

    def _store_graph(self, content: str, metadata: dict) -> str:
        if self._persistent_graph is None:
            return ""
        try:
            return self._persistent_graph.store(content, **metadata)
        except Exception:
            return ""

    # -- Properties ---------------------------------------------------------

    @property
    def strategy(self) -> RetrievalStrategy:
        return self._default_strategy

    @strategy.setter
    def strategy(self, value: RetrievalStrategy) -> None:
        self._default_strategy = value

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "total_queries": self._query_count,
            "tier_hits": {
                tier.value: count
                for tier, count in self._tier_hits.items()
            },
            "working_available": self._working is not None,
            "ingestion_available": self._ingestion is not None,
            "persistent_graph_available": self._persistent_graph is not None,
            "persistent_field_available": self._persistent_field is not None,
        }
