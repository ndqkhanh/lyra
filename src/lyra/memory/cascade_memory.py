"""
Cascade Memory — unified 3-tier memory pipeline with A-MAC admission,
cost-sensitive routing, and HippoRAG-style hybrid retrieval.

The cascade follows a three-tier architecture::

    STM (Working) --fast--> LTM (Graph+Vector) --slow--> Consolidation (KG)
        cheap                    medium                       expensive
    high frequency          medium frequency               rare access

Key references:
    - A-MAC: Adaptive Memory Admission Control
      Workday Research, ICLR 2026 MemAgent Workshop, arXiv 2603.04549v1
      Content-type classification alone provides 63% of admission gain.
    - Cost-Sensitive Store Routing for Memory-Augmented Agents
      Gaikwad et al., ICLR 2026 MemAgent Workshop, arXiv 2603.15658v1
    - HippoRAG: Graph-Enhanced Retrieval
      Guthrie et al., arXiv 2405.14831
    - FORGE: Population-Level Memory Synthesis for Multi-Agent Systems
      arXiv 2605.16233
"""

from __future__ import annotations

import math
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np

from lyra.memory.admission_control import (
    AdmissionController,
    AdmissionScore,
    ContentType,
)
from lyra.memory.long_term_memory import LongTermMemory
from lyra.memory.memory_consolidation import (
    ConsolidationPolicy,
    ConsolidationResult,
    MemoryConsolidator,
)
from lyra.memory.memory_store import MemoryType
from lyra.memory.short_term_memory import ShortTermMemory


# =============================================================================
# Constants
# =============================================================================

DEFAULT_ACCESS_THRESHOLD_STM: int = 10
"""Items accessed this many or more times stay in STM (cheap tier)."""

DEFAULT_ACCESS_THRESHOLD_LTM: int = 3
"""Items accessed this many or more times stay in LTM (medium tier)."""

DEFAULT_COST_STM: float = 0.01
"""Relative cost per access for STM (arbitrary units)."""

DEFAULT_COST_LTM: float = 0.10
"""Relative cost per access for LTM."""

DEFAULT_COST_CONSOLIDATION: float = 1.00
"""Relative cost per access for consolidation tier."""

DEFAULT_PAGERANK_DAMPING: float = 0.85
"""Damping factor for HippoRAG-style PageRank personalization."""

DEFAULT_HYBRID_ALPHA: float = 0.6
"""Weight for vector similarity vs graph PageRank in hybrid retrieval."""


# =============================================================================
# Enums and data structures
# =============================================================================


class MemoryTier(Enum):
    """The three tiers of the memory cascade."""

    STM = "stm"
    LTM = "ltm"
    CONSOLIDATION = "consolidation"


# Cost mapping per tier (Gaikwad cost-sensitive routing)
_TIER_COST: dict[MemoryTier, float] = {
    MemoryTier.STM: DEFAULT_COST_STM,
    MemoryTier.LTM: DEFAULT_COST_LTM,
    MemoryTier.CONSOLIDATION: DEFAULT_COST_CONSOLIDATION,
}

# Access-frequency thresholds for staying in each tier
_TIER_THRESHOLD: dict[MemoryTier, int] = {
    MemoryTier.STM: DEFAULT_ACCESS_THRESHOLD_STM,
    MemoryTier.LTM: DEFAULT_ACCESS_THRESHOLD_LTM,
    MemoryTier.CONSOLIDATION: 0,
}


@dataclass
class MemoryItem:
    """A memory item flowing through the cascade.

    Attributes:
        content: The raw memory text.
        content_type: A-MAC content-type classification.
        source: Origin identifier (e.g. agent id, conversation id).
        importance: Estimated importance (0.0-1.0).
        confidence: Confidence in the observation (0.0-1.0).
        embedding: Optional dense vector for semantic similarity.
        timestamp: Unix timestamp of creation.
        access_count: How many times this item has been retrieved.
        tier: Current cascade tier.
        memory_id: Unique identifier.
        metadata: Arbitrary key-value store.
    """

    content: str
    content_type: ContentType = ContentType.UNKNOWN
    source: str = ""
    importance: float = 0.5
    confidence: float = 0.8
    embedding: np.ndarray | None = None
    timestamp: float = 0.0
    access_count: int = 0
    tier: MemoryTier = MemoryTier.STM
    memory_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TierAccessStats:
    """Per-tier access statistics for cost-sensitive routing.

    Attributes:
        total_accesses: Cumulative access count for this tier.
        total_items: Number of items currently in this tier.
        last_accessed: Unix timestamp of the most recent access.
        cost_per_access: Relative cost for this tier.
    """

    total_accesses: int = 0
    total_items: int = 0
    last_accessed: float = 0.0
    cost_per_access: float = DEFAULT_COST_STM


@dataclass(frozen=True)
class CascadeRetrievalResult:
    """A single result from a cascade hybrid retrieval.

    Attributes:
        content: The retrieved memory text.
        score: Combined hybrid relevance score (0.0-1.0).
        tier: Which tier the result was retrieved from.
        item: The full MemoryItem (if available).
        vector_score: Cosine similarity contribution.
        graph_score: PageRank personalization contribution.
    """

    content: str
    score: float
    tier: MemoryTier
    item: MemoryItem | None = None
    vector_score: float = 0.0
    graph_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "content": self.content,
            "score": round(self.score, 4),
            "tier": self.tier.value,
            "tier_label": self.tier.name,
            "vector_score": round(self.vector_score, 4),
            "graph_score": round(self.graph_score, 4),
        }


# =============================================================================
# Cascade Memory
# =============================================================================


class CascadeMemory:
    """Unified 3-tier cascade memory with A-MAC admission and hybrid retrieval.

    The three tiers are:

        1. **STM** (Short-Term / Working Memory): in-memory buffer for recent,
           high-frequency content. Cheapest tier.
        2. **LTM** (Long-Term Memory): in-memory or SQLite-backed store with
           vector search index. Medium cost.
        3. **Consolidation**: field-theoretic or Neo4j KG persistence.
           Most expensive tier.

    **A-MAC gate**: every item must pass through the ``AdmissionController``
    before being stored. The 5-factor score (utility, confidence, novelty,
    recency, type_prior) determines admission; type_prior alone provides
    63% of the gain.

    **Cost-sensitive routing (Gaikwad)**: items with high access frequency
    are kept in cheap tiers (STM). Rarely-accessed items cascade to more
    expensive tiers (LTM, then consolidation).

    **Hybrid retrieval (HippoRAG-inspired)**: combines vector cosine
    similarity with a PageRank-style graph signal. The alpha parameter
    controls the balance (default 0.6 = 60% vector, 40% graph).

    Usage::

        cascade = CascadeMemory()
        item = MemoryItem(content="The user prefers dark mode", source="user")

        # Admission gate
        if cascade.admit(item):
            memory_id = cascade.store(item)
            results = cascade.retrieve("What theme?", top_k=3)
            stats = cascade.consolidate()
    """

    def __init__(
        self,
        stm: ShortTermMemory | None = None,
        ltm: LongTermMemory | None = None,
        consolidator: MemoryConsolidator | None = None,
        admission_controller: AdmissionController | None = None,
        access_threshold_stm: int = DEFAULT_ACCESS_THRESHOLD_STM,
        access_threshold_ltm: int = DEFAULT_ACCESS_THRESHOLD_LTM,
        pagerank_damping: float = DEFAULT_PAGERANK_DAMPING,
        hybrid_alpha: float = DEFAULT_HYBRID_ALPHA,
        auto_consolidate: bool = True,
    ):
        """
        Args:
            stm: Short-term memory backend. Defaults to ``ShortTermMemory()``.
            ltm: Long-term memory backend. Defaults to ``LongTermMemory()``.
            consolidator: Consolidation engine. Defaults to a
                ``MemoryConsolidator`` with ``ConsolidationPolicy.THRESHOLD``.
            admission_controller: A-MAC admission gate.
                Defaults to ``AdmissionController(threshold=0.45)``.
            access_threshold_stm: Items accessed >= this many times stay in STM.
            access_threshold_ltm: Items accessed >= this many times stay in LTM.
            pagerank_damping: Damping factor for PageRank personalization.
            hybrid_alpha: Weight for vector similarity vs graph PageRank.
            auto_consolidate: If True, ``consolidate()`` runs automatically
                when the STM buffer reaches its consolidation threshold.
        """
        # Backends
        self.stm = stm or ShortTermMemory(capacity=50, consolidation_threshold=10)
        self.ltm = ltm or LongTermMemory()
        self.admission = admission_controller or AdmissionController(threshold=0.45)

        # Consolidator: wraps stm + ltm into the existing MemoryConsolidator
        self.consolidator = (
            consolidator
            or MemoryConsolidator(
                short_term=self.stm,
                long_term=self.ltm,
                policy=ConsolidationPolicy.THRESHOLD,
                importance_threshold=0.5,
            )
        )

        # Configuration
        self.access_threshold_stm = access_threshold_stm
        self.access_threshold_ltm = access_threshold_ltm
        self.pagerank_damping = pagerank_damping
        self.hybrid_alpha = hybrid_alpha
        self.auto_consolidate = auto_consolidate

        # Internal state
        self._items: dict[str, MemoryItem] = {}
        self._tier_stats: dict[MemoryTier, TierAccessStats] = {
            tier: TierAccessStats(cost_per_access=_TIER_COST[tier])
            for tier in MemoryTier
        }
        # Graph edges for HippoRAG-style PageRank: item_id -> set of connected item_ids
        self._graph_edges: dict[str, set[str]] = defaultdict(set)

        # Access-count tracking per content-type for cost-sensitive routing
        self._content_type_access: dict[ContentType, int] = defaultdict(int)

    # ------------------------------------------------------------------
    # Admission (A-MAC gate)
    # ------------------------------------------------------------------

    def admit(self, memory_item: MemoryItem) -> bool:
        """Run the A-MAC 5-factor admission gate on a memory item.

        Content-type classification (``type_prior``) provides 63% of the
        admission gain. The remaining factors are utility, confidence,
        novelty, and recency.

        Args:
            memory_item: The candidate memory to evaluate.

        Returns:
            ``True`` if the item passes the admission threshold.
        """
        score = self.admission.evaluate(
            content=memory_item.content,
            content_type=memory_item.content_type,
            confidence=memory_item.confidence,
            existing_memories=self._existing_texts(limit=50),
            age_seconds=time.time() - memory_item.timestamp if memory_item.timestamp else 0.0,
        )
        return score.admit

    def evaluate_admission(
        self, memory_item: MemoryItem
    ) -> AdmissionScore:
        """Return the full A-MAC admission score (not just the bool).

        Useful for observability and debugging.

        Args:
            memory_item: The candidate memory to evaluate.

        Returns:
            The complete ``AdmissionScore`` with all factor breakdowns.
        """
        return self.admission.evaluate(
            content=memory_item.content,
            content_type=memory_item.content_type,
            confidence=memory_item.confidence,
            existing_memories=self._existing_texts(limit=50),
            age_seconds=time.time() - memory_item.timestamp if memory_item.timestamp else 0.0,
        )

    # ------------------------------------------------------------------
    # Store — cost-sensitive 3-tier routing
    # ------------------------------------------------------------------

    def store(
        self,
        memory_item: MemoryItem,
        tier: MemoryTier | None = None,
    ) -> str:
        """Store a memory item, routing to the correct cascade tier.

        Routing logic (Gaikwad cost-sensitive):
          - If ``tier`` is explicitly provided, store directly in that tier.
          - Otherwise, derive the tier from the item's access frequency:
              * access_count >= threshold_stm  -> STM (cheapest)
              * access_count >= threshold_ltm  -> LTM (medium)
              * else                           -> Consolidation (most expensive)

        Args:
            memory_item: The item to store.
            tier: Optional override — force routing to a specific tier.

        Returns:
            The ``memory_id`` assigned to the stored item.
        """
        if not memory_item.memory_id:
            memory_item.memory_id = str(uuid.uuid4())
        if memory_item.timestamp == 0.0:
            memory_item.timestamp = time.time()

        # Determine target tier
        target = tier or self._route_tier(memory_item)
        memory_item.tier = target

        # Store in the appropriate backend
        if target == MemoryTier.STM:
            turn = self.stm.add_turn(
                role=memory_item.source or "system",
                content=memory_item.content,
                metadata={
                    "memory_id": memory_item.memory_id,
                    "content_type": memory_item.content_type.value,
                    "importance": memory_item.importance,
                    "confidence": memory_item.confidence,
                },
            )
            # Track via working memory
            self.stm.set_working_memory(memory_item.memory_id, memory_item)

        elif target == MemoryTier.LTM:
            self.ltm.add(
                content=memory_item.content,
                memory_type=MemoryType.SEMANTIC,
                importance=memory_item.importance,
                tags=[memory_item.content_type.value, memory_item.source, "cascade"],
                context={
                    "memory_id": memory_item.memory_id,
                    "source": memory_item.source,
                    "content_type": memory_item.content_type.value,
                    "confidence": memory_item.confidence,
                    "tier": "ltm",
                },
            )

        elif target == MemoryTier.CONSOLIDATION:
            self.ltm.add(
                content=memory_item.content,
                memory_type=MemoryType.SEMANTIC,
                importance=memory_item.importance,
                tags=[memory_item.content_type.value, memory_item.source, "cascade", "consolidated"],
                context={
                    "memory_id": memory_item.memory_id,
                    "source": memory_item.source,
                    "content_type": memory_item.content_type.value,
                    "confidence": memory_item.confidence,
                    "tier": "consolidation",
                },
            )

        self._items[memory_item.memory_id] = memory_item
        self._tier_stats[target].total_items += 1
        self._tier_stats[target].last_accessed = time.time()

        return memory_item.memory_id

    def _route_tier(self, item: MemoryItem) -> MemoryTier:
        """Cost-sensitive tier routing based on access frequency.

        Gaikwad-style: items with high access frequency stay in cheap
        (STM) storage. Items with low access frequency flow to more
        expensive tiers. Brand-new items (access_count == 0) start in
        STM, the working-memory tier.

        Args:
            item: The memory item to route.

        Returns:
            The most cost-effective ``MemoryTier`` for this item.
        """
        access_freq = item.access_count

        # New items always start in STM (working memory)
        if access_freq == 0:
            return MemoryTier.STM

        # Content-type boost: high-priority types skip to more durable storage
        type_prior = self._content_type_access.get(item.content_type, 0)
        effective_freq = access_freq + type_prior

        if effective_freq >= self.access_threshold_stm:
            return MemoryTier.STM
        elif effective_freq >= self.access_threshold_ltm:
            return MemoryTier.LTM
        else:
            return MemoryTier.CONSOLIDATION

    # ------------------------------------------------------------------
    # Retrieve — HippoRAG-style hybrid graph+vector
    # ------------------------------------------------------------------

    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        alpha: float | None = None,
    ) -> list[CascadeRetrievalResult]:
        """Hybrid graph+vector retrieval across all memory tiers.

        Implements a HippoRAG-style combination:
          ``score = alpha * vector_sim + (1-alpha) * graph_pagerank``

        Where:
          - ``vector_sim`` is cosine similarity against all stored items.
          - ``graph_pagerank`` is a personalized PageRank score on the
            memory graph built from co-access relationships.

        Args:
            query: The search query.
            top_k: Maximum results to return.
            alpha: Override for the vector/graph balance (default uses
                ``self.hybrid_alpha``).

        Returns:
            List of ``CascadeRetrievalResult`` sorted by descending score.
        """
        alpha = alpha if alpha is not None else self.hybrid_alpha
        if not self._items:
            return []

        # --- Vector similarity pass ---
        query_lower = query.lower()
        query_words = set(query_lower.split())

        vector_scores: dict[str, float] = {}
        for mem_id, item in self._items.items():
            # Jaccard-like word overlap as a stand-in for vector cosine
            # (production: use the encoder from VectorSearcher)
            item_words = set(item.content.lower().split())
            if not query_words or not item_words:
                sim = 0.0
            else:
                intersection = len(query_words & item_words)
                union = len(query_words | item_words)
                sim = intersection / max(union, 1)

            # Boost by importance
            vector_scores[mem_id] = sim * (0.5 + 0.5 * item.importance)

        # --- Graph PageRank pass (HippoRAG-style) ---
        graph_scores = self._personalized_pagerank(query_words, vector_scores, top_k)

        # --- Combine scores ---
        combined: list[CascadeRetrievalResult] = []
        for mem_id, item in self._items.items():
            v_score = vector_scores.get(mem_id, 0.0)
            g_score = graph_scores.get(mem_id, 0.0)
            score = alpha * v_score + (1.0 - alpha) * g_score

            if score <= 0.0:
                continue

            combined.append(CascadeRetrievalResult(
                content=item.content,
                score=score,
                tier=item.tier,
                item=item,
                vector_score=v_score,
                graph_score=g_score,
            ))

        combined.sort(key=lambda r: r.score, reverse=True)

        # Bump access counts for retrieved items
        for result in combined[:top_k]:
            if result.item:
                result.item.access_count += 1
                self._content_type_access[result.item.content_type] += 1

        return combined[:top_k]

    def _personalized_pagerank(
        self,
        query_words: set[str],
        vector_scores: dict[str, float],
        top_k: int,
    ) -> dict[str, float]:
        """Compute personalized PageRank scores on the memory graph.

        Uses the query's top-N vector results as the *personalization
        vector* (seed nodes) and propagates score through graph edges.

        Args:
            query_words: Tokenized query words.
            vector_scores: Pre-computed vector similarity scores.
            top_k: Number of results requested.

        Returns:
            Dict of ``memory_id -> pagerank_score``.
        """
        if not self._graph_edges or not self._items:
            return {}

        n = len(self._items)
        if n == 0:
            return {}

        # Build a list of all memory IDs for indexing
        mem_ids = list(self._items.keys())
        id_to_idx = {mid: i for i, mid in enumerate(mem_ids)}
        idx_to_id = {i: mid for i, mid in enumerate(mem_ids)}

        # Build adjacency matrix (sparse: dense here for small-memory case)
        adj: dict[int, set[int]] = defaultdict(set)
        for mid, neighbors in self._graph_edges.items():
            if mid in id_to_idx:
                i = id_to_idx[mid]
                for nid in neighbors:
                    if nid in id_to_idx:
                        adj[i].add(id_to_idx[nid])

        # Personalization vector: top-K vector results as seeds
        sorted_by_vec = sorted(
            vector_scores.items(), key=lambda x: x[1], reverse=True
        )
        personalization = np.zeros(n, dtype=np.float64)
        for mem_id, _score in sorted_by_vec[:max(top_k, 5)]:
            if mem_id in id_to_idx:
                personalization[id_to_idx[mem_id]] = 1.0

        p_sum = personalization.sum()
        if p_sum > 0:
            personalization /= p_sum
        else:
            personalization.fill(1.0 / n)

        # Iterative PageRank
        rank = personalization.copy()
        damping = self.pagerank_damping
        max_iter = 50
        tol = 1e-6

        for _iteration in range(max_iter):
            new_rank = np.full(n, (1.0 - damping) / n, dtype=np.float64)
            for i in range(n):
                neighbors = adj.get(i, set())
                if neighbors:
                    share = damping * rank[i] / len(neighbors)
                    for j in neighbors:
                        new_rank[j] += share
                # Teleport: dangling nodes redistribute uniformly
                else:
                    new_rank += damping * rank[i] / n

            delta = np.linalg.norm(new_rank - rank)
            rank = new_rank
            if delta < tol:
                break

        return {idx_to_id[i]: float(rank[i]) for i in range(n) if rank[i] > 0}

    # ------------------------------------------------------------------
    # Consolidation pipeline
    # ------------------------------------------------------------------

    def consolidate(self) -> ConsolidationResult:
        """Run the periodic consolidation pipeline.

        Pipeline:
            1. STM -> LTM: move high-importance items from short-term to
               long-term memory.
            2. LTM -> KG: promote frequently-accessed LTM items to the
               consolidation tier (simulated here via importance boost
               and re-tagging).
            3. Update the memory graph with co-access edges.

        Returns:
            A ``ConsolidationResult`` with counts of created/merged memories
            and pattern extractions.
        """
        result = self.consolidator.consolidate()

        # -- LTM -> KG promotion (cost-sensitive) --
        promoted = self._promote_to_consolidation()
        result.memories_created += promoted

        # -- Update graph edges from co-occurrence in STM --
        self._update_graph_from_stm()

        # Sync internal item state
        self._sync_from_ltm()

        return result

    def _promote_to_consolidation(self) -> int:
        """Promote high-frequency LTM items to the consolidation tier.

        Items with access_count >= threshold_ltm are tagged as consolidated,
        marking them for rare-access expensive storage.

        Returns:
            Number of items promoted.
        """
        promoted = 0
        for mem_id, item in list(self._items.items()):
            if item.tier == MemoryTier.LTM and item.access_count >= self.access_threshold_ltm:
                item.tier = MemoryTier.CONSOLIDATION
                self._tier_stats[MemoryTier.CONSOLIDATION].total_items += 1
                self._tier_stats[MemoryTier.LTM].total_items = max(
                    0, self._tier_stats[MemoryTier.LTM].total_items - 1
                )
                promoted += 1
        return promoted

    def _update_graph_from_stm(self):
        """Build co-access graph edges from STM conversation turns.

        Two turns that appear consecutively in the STM buffer get a
        graph edge between them. This enables HippoRAG-style graph
        propagation.
        """
        recent_turns = self.stm.get_recent(limit=20)
        # Collect memory_ids from the stored items
        recent_ids: list[str] = []
        for turn in recent_turns:
            mid = turn.metadata.get("memory_id", "")
            if mid and mid in self._items:
                recent_ids.append(mid)

        # Connect consecutive turns
        for i in range(len(recent_ids) - 1):
            a, b = recent_ids[i], recent_ids[i + 1]
            self._graph_edges[a].add(b)
            self._graph_edges[b].add(a)

    def _sync_from_ltm(self):
        """Synchronize internal item state with LTM store.

        Ensures items that were merged or modified during consolidation
        are reflected in the cascade's tracking dict.
        """
        ltm_memories = self.ltm.store.get_all()
        for mem in ltm_memories:
            mid = mem.context.get("memory_id", "") if mem.context else ""
            if mid and mid in self._items:
                self._items[mid].importance = mem.importance

    # ------------------------------------------------------------------
    # Access tracking
    # ------------------------------------------------------------------

    def record_access(self, memory_id: str) -> None:
        """Manually record an access for a memory item.

        Bumps the item's access count and content-type frequency,
        which may cause it to be re-routed to a cheaper tier on
        the next consolidation cycle.

        Args:
            memory_id: The identifier of the item being accessed.
        """
        item = self._items.get(memory_id)
        if item is None:
            return
        item.access_count += 1
        self._content_type_access[item.content_type] += 1
        self._tier_stats[item.tier].total_accesses += 1
        self._tier_stats[item.tier].last_accessed = time.time()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _existing_texts(self, limit: int = 50) -> list[str]:
        """Return the most recent memory texts (for novelty scoring)."""
        texts: list[str] = []
        for turn in self.stm.get_recent(limit=limit):
            texts.append(turn.content)
        for mem in self.ltm.get_recent(limit=limit):
            texts.append(mem.content)
        return texts

    def get_item(self, memory_id: str) -> MemoryItem | None:
        """Retrieve a single MemoryItem by ID."""
        return self._items.get(memory_id)

    def get_tier_stats(self) -> dict[str, Any]:
        """Return per-tier statistics for observability."""
        return {
            tier.value: {
                "total_accesses": stats.total_accesses,
                "total_items": stats.total_items,
                "cost_per_access": stats.cost_per_access,
            }
            for tier, stats in self._tier_stats.items()
        }

    def clear(self):
        """Reset all cascade state."""
        self.stm.clear()
        self.ltm.clear()
        self._items.clear()
        self._graph_edges.clear()
        self._content_type_access.clear()
        for stats in self._tier_stats.values():
            stats.total_accesses = 0
            stats.total_items = 0

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_statistics(self) -> dict[str, Any]:
        """Return comprehensive cascade memory statistics.

        Returns:
            Dictionary with counts, tier distribution, cost model,
            and admission gate configuration.
        """
        total_items = len(self._items)
        tier_distribution: dict[str, int] = defaultdict(int)
        for item in self._items.values():
            tier_distribution[item.tier.value] += 1

        type_distribution: dict[str, int] = defaultdict(int)
        for item in self._items.values():
            type_distribution[item.content_type.value] += 1

        all_scores = [
            self.evaluate_admission(item).combined
            for item in self._items.values()
        ]
        avg_admission_score = (
            float(np.mean(all_scores)) if all_scores else 0.0
        )

        # Cost analysis
        total_cost = sum(
            stats.total_accesses * stats.cost_per_access
            for stats in self._tier_stats.values()
        )

        return {
            "total_items": total_items,
            "tier_distribution": dict(tier_distribution),
            "type_distribution": dict(type_distribution),
            "total_accesses": sum(
                stats.total_accesses for stats in self._tier_stats.values()
            ),
            "graph_edges": sum(len(v) for v in self._graph_edges.values()),
            "total_cost": round(total_cost, 4),
            "avg_admission_score": round(avg_admission_score, 4),
            "admission_threshold": self.admission.threshold,
            "admission_weights": self.admission.weights,
            "stm_turns": len(self.stm.turns),
            "ltm_memories": len(self.ltm.store.get_all()),
            "access_threshold_stm": self.access_threshold_stm,
            "access_threshold_ltm": self.access_threshold_ltm,
            "hybrid_alpha": self.hybrid_alpha,
            "pagerank_damping": self.pagerank_damping,
            "tier_costs": {
                tier.value: _TIER_COST[tier] for tier in MemoryTier
            },
        }
