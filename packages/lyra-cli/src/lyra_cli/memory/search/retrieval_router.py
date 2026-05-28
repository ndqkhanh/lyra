"""Tiered retrieval router with 5-tier strategy.

Routes queries through DCI grep → verbatim cache → BM25 → hybrid
BM25+Vector+RRF → knowledge graph PPR, fusing results via RRF.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import StrEnum


class RetrievalTier(StrEnum):
    DCI_GREP = "dci_grep"
    VERBATIM = "verbatim"
    BM25 = "bm25"
    HYBRID = "hybrid"
    KNOWLEDGE_GRAPH = "knowledge_graph"


@dataclass(frozen=True)
class RetrievalContext:
    query: str
    max_results: int = 10
    include_graph: bool = False
    timeout_ms: float = 200.0


@dataclass(frozen=True)
class RankedResult:
    item_id: str
    content: str
    score: float
    tier: RetrievalTier
    rank: int


@dataclass(frozen=True)
class RetrievalReport:
    results: list[RankedResult]
    tiers_used: list[RetrievalTier]
    total_ms: float
    result_count: int


class RetrievalRouter:
    """5-tier retrieval router with progressive fallback.

    Tier 0: DCI grep (exact keywords)         <1ms
    Tier 1: MemPalace verbatim cache           <1ms
    Tier 2: BM25 (keyword relevance)           5ms
    Tier 3: BM25 + Vector + RRF (hybrid)       50ms
    Tier 4: Knowledge graph PPR (multi-hop)   100ms

    Each tier can satisfy the query independently.
    Results are fused by taking the best from the first tier that
    produces results, with subsequent tiers supplementing.
    """

    FALLBACK_ORDER: list[RetrievalTier] = [
        RetrievalTier.DCI_GREP,
        RetrievalTier.VERBATIM,
        RetrievalTier.BM25,
        RetrievalTier.HYBRID,
        RetrievalTier.KNOWLEDGE_GRAPH,
    ]

    def __init__(self) -> None:
        self._searchers: dict[RetrievalTier, object] = {}
        self._stats: dict[RetrievalTier, int] = dict.fromkeys(RetrievalTier, 0)

    def register(self, tier: RetrievalTier, searcher: object) -> None:
        self._searchers[tier] = searcher

    def retrieve(self, ctx: RetrievalContext) -> RetrievalReport:
        start = time.perf_counter()
        all_results: list[RankedResult] = []
        tiers_used: list[RetrievalTier] = []

        for tier in self.FALLBACK_ORDER:
            if tier == RetrievalTier.KNOWLEDGE_GRAPH and not ctx.include_graph:
                continue
            if tier not in self._searchers:
                continue

            elapsed = (time.perf_counter() - start) * 1000
            if elapsed > ctx.timeout_ms:
                break

            tier_results = self._search_tier(tier, ctx)
            if tier_results:
                tiers_used.append(tier)
                self._stats[tier] += 1
                for i, r in enumerate(tier_results):
                    all_results.append(RankedResult(
                        item_id=r.get("id", f"{tier.value}:{i}"),
                        content=r.get("content", ""),
                        score=r.get("score", 0.5),
                        tier=tier,
                        rank=i + 1,
                    ))

            if len(all_results) >= ctx.max_results:
                break

        total_ms = (time.perf_counter() - start) * 1000
        all_results.sort(key=lambda r: -r.score)
        results = all_results[:ctx.max_results]

        return RetrievalReport(
            results=results,
            tiers_used=tiers_used,
            total_ms=round(total_ms, 2),
            result_count=len(results),
        )

    def _search_tier(
        self, tier: RetrievalTier, ctx: RetrievalContext
    ) -> list[dict]:
        searcher = self._searchers.get(tier)
        if searcher is None:
            return []

        try:
            if tier == RetrievalTier.DCI_GREP:
                return self._adapt_grep_results(searcher, ctx)
            elif tier == RetrievalTier.VERBATIM:
                return self._adapt_verbatim_results(searcher, ctx)
            elif tier == RetrievalTier.BM25:
                return self._adapt_bm25_results(searcher, ctx)
            elif tier == RetrievalTier.HYBRID:
                return self._adapt_hybrid_results(searcher, ctx)
            elif tier == RetrievalTier.KNOWLEDGE_GRAPH:
                return self._adapt_graph_results(searcher, ctx)
        except Exception:
            pass
        return []

    def _adapt_grep_results(self, searcher: object, ctx: RetrievalContext) -> list[dict]:
        results = searcher.search(ctx.query, limit=ctx.max_results)  # type: ignore[union-attr]
        return [
            {"id": f"grep:{r.file_path}:{r.line_number}", "content": r.line_content, "score": r.score}
            for r in results
        ]

    def _adapt_verbatim_results(self, searcher: object, ctx: RetrievalContext) -> list[dict]:
        content = searcher.lookup(ctx.query)  # type: ignore[union-attr]
        if content:
            return [{"id": f"verbatim:{hash(content)}", "content": str(content), "score": 1.0}]
        return []

    def _adapt_bm25_results(self, searcher: object, ctx: RetrievalContext) -> list[dict]:
        results = searcher.search(ctx.query, limit=ctx.max_results)  # type: ignore[union-attr]
        return [
            {"id": f"bm25:{getattr(r, 'id', i)}", "content": str(r), "score": 0.5}
            for i, r in enumerate(results)
        ]

    def _adapt_hybrid_results(self, searcher: object, ctx: RetrievalContext) -> list[dict]:
        results = searcher.search(ctx.query, limit=ctx.max_results)  # type: ignore[union-attr]
        return [
            {"id": f"hybrid:{getattr(r, 'id', i)}", "content": str(r), "score": 0.7}
            for i, r in enumerate(results)
        ]

    def _adapt_graph_results(self, searcher: object, ctx: RetrievalContext) -> list[dict]:
        results = searcher.query(ctx.query, limit=ctx.max_results)  # type: ignore[union-attr]
        return [
            {"id": f"graph:{getattr(r, 'id', i)}", "content": str(r), "score": 0.4}
            for i, r in enumerate(results)
        ]

    def stats(self) -> dict:
        return {
            "registered_tiers": list(self._searchers.keys()),
            "tier_usage": {t.value: c for t, c in self._stats.items()},
        }
