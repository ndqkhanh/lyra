"""
Cost-Sensitive Retrieval Store Routing.

Implements the "Did You Check the Right Pocket?" paper pattern (Gaikwad, ICLR 2026
MemAgent Workshop): route memory queries to the cheapest store that can answer them,
avoiding expensive LLM calls when a cheaper approach suffices.

Routing cascade:
  1. **Working Memory** (0ms, $0) — Exact match via cache key
  2. **Episodic Memory** (<5ms, $0) — Embedding similarity against recent notes
  3. **Semantic Memory** (<50ms, <$0.001) — Graph traversal + keyword match
  4. **Archive** (<200ms, ~$0.001) — Full hybrid BM25 + vector search
  5. **LLM Fallback** (>500ms, >$0.01) — LLM re-answer if all stores miss

Expected distribution (from memory-architecture.md):
- 40% of queries: Working Memory (exact match, $0)
- 40% of queries: Episodic/Semantic (similar query, <10% cost)
- 20% of queries: LLM (novel query, full cost)
→ 52% overall cost reduction

Design rationale: The insight from the paper is that retrieval can be formulated
as a cost-sensitive routing problem — choose the cheapest store that is LIKELY to
contain the answer, with escalating cost as confidence decreases.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


class StoreTier(str, Enum):
    """Memory store tiers in order of cost (cheapest first)."""

    WORKING = "working"     # In-memory cache, <1ms, $0
    EPISODIC = "episodic"   # Recent sessions, <5ms, $0
    SEMANTIC = "semantic"   # Long-term patterns, <50ms, <$0.001
    ARCHIVE = "archive"     # Cold storage, <200ms, ~$0.001
    LLM_FALLBACK = "llm"    # Re-answer with LLM, >500ms, >$0.01


@dataclass
class RetrievalResult:
    """Result from a retrieval attempt."""

    content: str
    store: StoreTier
    confidence: float  # 0.0–1.0
    latency_ms: float
    cost_usd: float
    found: bool
    metadata: dict = field(default_factory=dict)


@dataclass
class StoreRoutingDecision:
    """Decision about which store to query next."""

    store: StoreTier
    confidence_threshold: float  # Minimum confidence to accept result from this store
    estimated_cost_usd: float
    estimated_latency_ms: float


class CostSensitiveRouter:
    """
    Routes memory queries to the cheapest store that can answer them.

    Implements the cascading pattern:
    - Try Working Memory first (0ms, $0)
    - If miss, try Episodic (<5ms)
    - If miss, try Semantic (<50ms)
    - If miss, try Archive (<200ms)
    - If miss, escalate to LLM (>500ms)

    Usage::

        router = CostSensitiveRouter()
        result = router.retrieve(
            query="What was the JWT auth pattern we used?",
            working_store=wm,
            episodic_store=em,
            semantic_store=sm,
            archive_store=am,
        )
        if result.found:
            return result.content
        else:
            return await llm.re_answer(query)
    """

    # Confidence thresholds for accepting a result from each tier
    WORKING_CONFIDENCE_THRESHOLD = 0.95   # Exact match only
    EPISODIC_CONFIDENCE_THRESHOLD = 0.70  # High similarity
    SEMANTIC_CONFIDENCE_THRESHOLD = 0.50  # Moderate similarity
    ARCHIVE_CONFIDENCE_THRESHOLD = 0.30   # Low similarity — still worth trying

    # Cost estimates per tier (USD)
    _COST_PER_TIER: dict[StoreTier, float] = {
        StoreTier.WORKING: 0.0,
        StoreTier.EPISODIC: 0.0,
        StoreTier.SEMANTIC: 0.0005,
        StoreTier.ARCHIVE: 0.001,
        StoreTier.LLM_FALLBACK: 0.01,
    }

    def __init__(self) -> None:
        self._stats: dict[StoreTier, int] = {t: 0 for t in StoreTier}
        self._total_queries: int = 0
        self._total_cost_saved: float = 0.0

    def retrieve(
        self,
        query: str,
        working_store: object | None = None,
        episodic_store: object | None = None,
        semantic_store: object | None = None,
        archive_store: object | None = None,
        llm_fallback: object | None = None,
        max_cost_usd: float = 0.05,
    ) -> RetrievalResult:
        """
        Route a query through the cost-sensitive cascade.

        Each store must have a `search(query) -> RetrievalResult` method.
        The cascade stops at the first store whose result meets the confidence
        threshold for that tier.

        Args:
            query: The search query.
            working_store: In-memory cache with O(1) lookup.
            episodic_store: Recent session store with embedding similarity.
            semantic_store: Long-term pattern store with graph traversal.
            archive_store: Cold storage with full hybrid search.
            llm_fallback: LLM re-answer function (expensive, last resort).
            max_cost_usd: Maximum total cost for this retrieval.

        Returns:
            A RetrievalResult, possibly with found=False if all stores missed.
        """
        self._total_queries += 1
        total_cost = 0.0
        start = time.perf_counter()

        # ── Tier 1: Working Memory (exact match) ─────────────
        if working_store:
            result = self._try_store(
                working_store, query, StoreTier.WORKING,
                self.WORKING_CONFIDENCE_THRESHOLD,
            )
            total_cost += result.cost_usd
            if result.found and result.confidence >= self.WORKING_CONFIDENCE_THRESHOLD:
                self._record_hit(StoreTier.WORKING, result, start)
                return result

        # ── Tier 2: Episodic Memory (similarity match) ───────
        if episodic_store and total_cost < max_cost_usd:
            result = self._try_store(
                episodic_store, query, StoreTier.EPISODIC,
                self.EPISODIC_CONFIDENCE_THRESHOLD,
            )
            total_cost += result.cost_usd
            if result.found and result.confidence >= self.EPISODIC_CONFIDENCE_THRESHOLD:
                self._record_hit(StoreTier.EPISODIC, result, start)
                return result

        # ── Tier 3: Semantic Memory (graph traversal) ────────
        if semantic_store and total_cost < max_cost_usd:
            result = self._try_store(
                semantic_store, query, StoreTier.SEMANTIC,
                self.SEMANTIC_CONFIDENCE_THRESHOLD,
            )
            total_cost += result.cost_usd
            if result.found and result.confidence >= self.SEMANTIC_CONFIDENCE_THRESHOLD:
                self._record_hit(StoreTier.SEMANTIC, result, start)
                return result

        # ── Tier 4: Archive (full search) ────────────────────
        if archive_store and total_cost < max_cost_usd:
            result = self._try_store(
                archive_store, query, StoreTier.ARCHIVE,
                self.ARCHIVE_CONFIDENCE_THRESHOLD,
            )
            total_cost += result.cost_usd
            if result.found and result.confidence >= self.ARCHIVE_CONFIDENCE_THRESHOLD:
                self._record_hit(StoreTier.ARCHIVE, result, start)
                return result

        # ── Tier 5: LLM Fallback ─────────────────────────────
        if llm_fallback and total_cost < max_cost_usd:
            try:
                llm_start = time.perf_counter()
                content = llm_fallback(query) if callable(llm_fallback) else str(llm_fallback)
                llm_elapsed = (time.perf_counter() - llm_start) * 1000
                result = RetrievalResult(
                    content=content,
                    store=StoreTier.LLM_FALLBACK,
                    confidence=0.60,  # LLM answers are uncertain by default
                    latency_ms=llm_elapsed,
                    cost_usd=self._COST_PER_TIER[StoreTier.LLM_FALLBACK],
                    found=True,
                )
                self._record_hit(StoreTier.LLM_FALLBACK, result, start)
                return result
            except Exception:
                pass

        # ── Complete miss ────────────────────────────────────
        elapsed = (time.perf_counter() - start) * 1000
        return RetrievalResult(
            content="",
            store=StoreTier.ARCHIVE,  # Last tried
            confidence=0.0,
            latency_ms=elapsed,
            cost_usd=total_cost,
            found=False,
        )

    def should_skip_llm(self, query: str, max_budget_usd: float) -> bool:
        """Check whether we should skip the LLM tier based on remaining budget."""
        return max_budget_usd < self._COST_PER_TIER[StoreTier.LLM_FALLBACK]

    @property
    def stats(self) -> dict:
        """Return retrieval statistics."""
        return {
            "total_queries": self._total_queries,
            "hits_by_tier": {t.value: c for t, c in self._stats.items()},
            "total_cost_saved": round(self._total_cost_saved, 6),
            "working_hit_rate": self._hit_rate(StoreTier.WORKING),
            "episodic_hit_rate": self._hit_rate(StoreTier.EPISODIC),
        }

    # ── Internal ─────────────────────────────────────────────────

    @staticmethod
    def _try_store(
        store: object,
        query: str,
        tier: StoreTier,
        threshold: float,
    ) -> RetrievalResult:
        """Try to retrieve from a single store."""
        try:
            if hasattr(store, "search"):
                return store.search(query)  # type: ignore[union-attr]
            return RetrievalResult(
                content="",
                store=tier,
                confidence=0.0,
                latency_ms=0.0,
                cost_usd=0.0,
                found=False,
            )
        except Exception:
            return RetrievalResult(
                content="",
                store=tier,
                confidence=0.0,
                latency_ms=0.0,
                cost_usd=0.0,
                found=False,
            )

    def _record_hit(
        self,
        tier: StoreTier,
        result: RetrievalResult,
        start_time: float,
    ) -> None:
        """Record a successful retrieval for statistics."""
        self._stats[tier] += 1
        # Estimate cost saved vs LLM fallback
        llm_cost = self._COST_PER_TIER[StoreTier.LLM_FALLBACK]
        self._total_cost_saved += llm_cost - result.cost_usd

    def _hit_rate(self, tier: StoreTier) -> float:
        """Calculate hit rate for a tier."""
        if self._total_queries == 0:
            return 0.0
        return self._stats[tier] / self._total_queries
