"""
Memory Retrieval - Intelligent memory search and retrieval with 3-signal
fusion (semantic + temporal + behavioral).
"""

from __future__ import annotations

import statistics
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from lyra.memory.long_term_memory import LongTermMemory
from lyra.memory.memory_store import Memory


class RetrievalStrategy(Enum):
    """Memory retrieval strategies."""
    SEMANTIC = "semantic"          # Semantic similarity (requires embeddings)
    KEYWORD = "keyword"            # Keyword matching
    TEMPORAL = "temporal"          # Time-based
    IMPORTANCE = "importance"      # Importance-weighted
    HYBRID = "hybrid"              # Combine multiple strategies
    FUSION = "fusion"              # 3-signal fusion (semantic+temporal+behavioral)


@dataclass
class RetrievalResult:
    """
    A memory retrieval result.

    Attributes:
        memory: Retrieved memory
        score: Relevance score (0.0 - 1.0)
        strategy: Strategy used
        metadata: Additional metadata
    """
    memory: Memory
    score: float
    strategy: str
    metadata: dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class FusionWeights:
    """Learnable weights for the 3-signal fusion retriever.

    Attributes:
        semantic: Weight for the semantic (embedding) signal.
        temporal: Weight for the temporal (recency) signal.
        behavioral: Weight for the behavioral (cluster) signal.
    """

    semantic: float = 0.40
    temporal: float = 0.35
    behavioral: float = 0.25

    def normalize(self) -> FusionWeights:
        """Return a new FusionWeights with weights that sum to 1.0."""
        total = self.semantic + self.temporal + self.behavioral
        if total <= 0.0:
            return FusionWeights()
        return FusionWeights(
            semantic=self.semantic / total,
            temporal=self.temporal / total,
            behavioral=self.behavioral / total,
        )

    def to_dict(self) -> dict[str, float]:
        return {
            "semantic": round(self.semantic, 4),
            "temporal": round(self.temporal, 4),
            "behavioral": round(self.behavioral, 4),
        }


# =============================================================================
# Fusion Retriever — 3-signal fusion (semantic + temporal + behavioral)
# =============================================================================


class FusionRetriever:
    """3-signal fusion retrieval that combines semantic (embedding), temporal
    (recency), and behavioral (cluster) signals into a single relevance score.

    Signal weights are learnable via feedback: after each retrieval call,
    ``record_feedback(retrieved_items, clicked_item)`` adjusts the weights
    to increase the weight of the signal that correctly predicted the
    user-preferred item.

    Usage::

        retriever = FusionRetriever(memory_store)
        results = retriever.retrieve_fused("user query", top_k=5)
        # Feedback loop
        retriever.record_feedback(results, preferred_result)
        print(retriever.get_weights())
    """

    def __init__(
        self,
        memory_store: MemoryStore | LongTermMemory,
        weights: FusionWeights | None = None,
        learning_rate: float = 0.05,
        cluster_lookup: dict[str, int] | None = None,
    ):
        """
        Args:
            memory_store: Memory store or long-term memory to search.
            weights: Initial signal weights. Auto-normalized.
            learning_rate: Step size for weight updates from feedback.
            cluster_lookup: Optional mapping from memory_id (str) to
                cluster_id (int) from behavioral clustering. If provided,
                items in the same cluster as the query's nearest neighbors
                get a behavioral boost.
        """
        self.store = memory_store
        self.weights = (weights or FusionWeights()).normalize()
        self.learning_rate = learning_rate
        self.cluster_lookup = cluster_lookup or {}

        # Tracking for weight adaptation
        self._feedback_history: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def retrieve_fused(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.0,
    ) -> list[RetrievalResult]:
        """Run 3-signal fusion retrieval.

        Args:
            query: The search query.
            top_k: Maximum number of results to return.
            min_score: Minimum combined score to include a result.

        Returns:
            Ranked list of RetrievalResult with scores from the fusion.
        """
        # Get all candidate memories
        if hasattr(self.store, "get_all"):
            candidates = self.store.get_all()
        elif hasattr(self.store, "store") and hasattr(self.store.store, "get_all"):
            candidates = self.store.store.get_all()
        else:
            candidates = []

        if not candidates:
            return []

        # Compute per-memory signal scores
        scored: list[tuple[Memory, float, float, float, float]] = []
        for mem in candidates:
            sem_score = self._semantic_signal(mem, query)
            temp_score = self._temporal_signal(mem)
            beh_score = self._behavioral_signal(mem, query)

            combined = (
                self.weights.semantic * sem_score
                + self.weights.temporal * temp_score
                + self.weights.behavioral * beh_score
            )

            if combined < min_score:
                continue

            scored.append((mem, combined, sem_score, temp_score, beh_score))

        # Sort by combined score descending
        scored.sort(key=lambda x: x[1], reverse=True)

        results: list[RetrievalResult] = []
        for mem, combined, sem, temp, beh in scored[:top_k]:
            results.append(RetrievalResult(
                memory=mem,
                score=combined,
                strategy="fusion",
                metadata={
                    "semantic_score": round(sem, 4),
                    "temporal_score": round(temp, 4),
                    "behavioral_score": round(beh, 4),
                    "fusion_weights": self.weights.to_dict(),
                },
            ))

        return results

    # ------------------------------------------------------------------
    # Signal computation
    # ------------------------------------------------------------------

    def _semantic_signal(self, memory: Memory, query: str) -> float:
        """Semantic similarity between memory content and query.

        Uses Jaccard word overlap as a lightweight stand-in for embedding
        cosine similarity.
        """
        query_words = set(query.lower().split())
        content_words = set(memory.content.lower().split())
        if not query_words or not content_words:
            return 0.0
        intersection = query_words & content_words
        union = query_words | content_words
        jaccard = len(intersection) / max(len(union), 1)
        # Blend with importance
        return jaccard * (0.5 + 0.5 * memory.importance)

    def _temporal_signal(self, memory: Memory) -> float:
        """Recency-based temporal signal.

        Returns 1.0 for memories created just now, decaying exponentially
        over a 30-day window.
        """
        age_days = (time.time() - memory.timestamp) / 86400.0
        return max(0.0, 1.0 - (age_days / 30.0))

    def _behavioral_signal(self, memory: Memory, query: str) -> float:
        """Behavioral (cluster) signal.

        If cluster_lookup is available, items whose cluster matches the
        query's nearest-cluster receive a boost. Otherwise, normalized
        access frequency is used as a behavioral proxy.
        """
        if self.cluster_lookup:
            # Use the memory's cluster membership
            mem_cluster = self.cluster_lookup.get(memory.memory_id, -1)
            if mem_cluster >= 0:
                # Boost based on cluster size (popular clusters = stronger signal)
                cluster_size = sum(
                    1 for c in self.cluster_lookup.values() if c == mem_cluster
                )
                return min(1.0, cluster_size / 20.0)

        # Fallback: normalized access frequency
        return min(1.0, memory.access_count / 10.0)

    # ------------------------------------------------------------------
    # Feedback-driven weight adaptation
    # ------------------------------------------------------------------

    def record_feedback(
        self,
        retrieved: list[RetrievalResult],
        selected_index: int,
    ) -> FusionWeights:
        """Update signal weights based on which result the user selected.

        The weight of each signal is adjusted proportionally to how well
        that signal predicted the selected item vs. the average.

        Args:
            retrieved: The list of results from a ``retrieve_fused`` call.
            selected_index: Index (in ``retrieved``) of the item the user
                selected / found most relevant.

        Returns:
            The updated (normalized) FusionWeights.
        """
        if not retrieved or selected_index < 0 or selected_index >= len(retrieved):
            return self.weights

        selected = retrieved[selected_index]
        sem_scores = [r.metadata.get("semantic_score", 0.0) for r in retrieved]
        temp_scores = [r.metadata.get("temporal_score", 0.0) for r in retrieved]
        beh_scores = [r.metadata.get("behavioral_score", 0.0) for r in retrieved]

        # How much better/worse each signal predicted the selected item
        avg_sem = statistics.mean(sem_scores) if sem_scores else 0.0
        avg_temp = statistics.mean(temp_scores) if temp_scores else 0.0
        avg_beh = statistics.mean(beh_scores) if beh_scores else 0.0

        sem_error = selected.metadata.get("semantic_score", 0.0) - avg_sem
        temp_error = selected.metadata.get("temporal_score", 0.0) - avg_temp
        beh_error = selected.metadata.get("behavioral_score", 0.0) - avg_beh

        # Update weights: increase weight of the signal that best predicted
        # the selection
        self.weights = FusionWeights(
            semantic=self.weights.semantic + self.learning_rate * sem_error,
            temporal=self.weights.temporal + self.learning_rate * temp_error,
            behavioral=self.weights.behavioral + self.learning_rate * beh_error,
        ).normalize()

        # Log feedback
        self._feedback_history.append({
            "query": "",
            "selected_index": selected_index,
            "selected_score": selected.score,
            "weights_before": {
                "semantic": round(self.weights.semantic - self.learning_rate * sem_error, 4),
                "temporal": round(self.weights.temporal - self.learning_rate * temp_error, 4),
                "behavioral": round(self.weights.behavioral - self.learning_rate * beh_error, 4),
            },
            "weights_after": self.weights.to_dict(),
        })

        return self.weights

    def get_weights(self) -> FusionWeights:
        """Return the current signal weights."""
        return FusionWeights(
            semantic=self.weights.semantic,
            temporal=self.weights.temporal,
            behavioral=self.weights.behavioral,
        )

    def get_feedback_history(
        self, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Return recent feedback events for observability."""
        return self._feedback_history[-limit:]

    def reset_weights(self, weights: FusionWeights | None = None):
        """Reset signal weights to defaults or a specific set.

        Args:
            weights: New weights (auto-normalized). If None, resets to
                ``FusionWeights()`` defaults.
        """
        self.weights = (weights or FusionWeights()).normalize()
        self._feedback_history.clear()


# =============================================================================
# Legacy RelevanceScorer (unchanged)
# =============================================================================


class RelevanceScorer:
    """
    Calculate relevance scores for memories.

    Combines multiple signals:
    - Content similarity
    - Importance
    - Recency
    - Access frequency
    """

    def __init__(
        self,
        importance_weight: float = 0.3,
        recency_weight: float = 0.3,
        frequency_weight: float = 0.2,
        content_weight: float = 0.2,
    ):
        """
        Initialize relevance scorer.

        Args:
            importance_weight: Weight for importance score
            recency_weight: Weight for recency score
            frequency_weight: Weight for access frequency
            content_weight: Weight for content similarity
        """
        self.importance_weight = importance_weight
        self.recency_weight = recency_weight
        self.frequency_weight = frequency_weight
        self.content_weight = content_weight

    def score(
        self,
        memory: Memory,
        query: str | None = None,
        current_time: float | None = None,
    ) -> float:
        """
        Calculate relevance score for a memory.

        Args:
            memory: Memory to score
            query: Search query (for content similarity)
            current_time: Current timestamp

        Returns:
            Relevance score (0.0 - 1.0)
        """
        if current_time is None:
            current_time = time.time()

        # Importance score (already 0-1)
        importance_score = memory.importance

        # Recency score (exponential decay)
        age_days = (current_time - memory.timestamp) / 86400
        recency_score = max(0.0, 1.0 - (age_days / 30))  # Decay over 30 days

        # Frequency score (normalized access count)
        frequency_score = min(1.0, memory.access_count / 10)

        # Content similarity score
        content_score = 0.5  # Default
        if query:
            content_score = self._calculate_content_similarity(memory.content, query)

        # Weighted combination
        total_score = (
            self.importance_weight * importance_score +
            self.recency_weight * recency_score +
            self.frequency_weight * frequency_score +
            self.content_weight * content_score
        )

        return total_score

    def _calculate_content_similarity(self, content: str, query: str) -> float:
        """
        Calculate content similarity (simple keyword matching).

        Args:
            content: Memory content
            query: Search query

        Returns:
            Similarity score (0.0 - 1.0)
        """
        content_lower = content.lower()
        query_lower = query.lower()

        # Simple keyword matching
        query_words = set(query_lower.split())
        content_words = set(content_lower.split())

        if not query_words:
            return 0.0

        # Jaccard similarity
        intersection = query_words & content_words
        union = query_words | content_words

        if not union:
            return 0.0

        return len(intersection) / len(union)


# =============================================================================
# Legacy MemoryRetriever (unchanged)
# =============================================================================


class MemoryRetriever:
    """
    Intelligent memory retrieval system.

    Responsibilities:
    - Search memories using various strategies
    - Rank results by relevance
    - Combine multiple search methods
    """

    def __init__(
        self,
        long_term_memory: LongTermMemory,
        default_strategy: RetrievalStrategy = RetrievalStrategy.HYBRID,
    ):
        """
        Initialize memory retriever.

        Args:
            long_term_memory: Long-term memory store
            default_strategy: Default retrieval strategy
        """
        self.long_term_memory = long_term_memory
        self.default_strategy = default_strategy
        self.scorer = RelevanceScorer()

    def retrieve(
        self,
        query: str,
        strategy: RetrievalStrategy | None = None,
        limit: int = 10,
        min_score: float = 0.0,
        filters: dict | None = None,
    ) -> list[RetrievalResult]:
        """
        Retrieve relevant memories.

        Args:
            query: Search query
            strategy: Retrieval strategy to use
            limit: Maximum results to return
            min_score: Minimum relevance score
            filters: Additional filters (type, tags, time_range)

        Returns:
            List of retrieval results
        """
        strategy = strategy or self.default_strategy

        if strategy == RetrievalStrategy.KEYWORD:
            return self._retrieve_keyword(query, limit, min_score, filters)
        elif strategy == RetrievalStrategy.TEMPORAL:
            return self._retrieve_temporal(query, limit, min_score, filters)
        elif strategy == RetrievalStrategy.IMPORTANCE:
            return self._retrieve_importance(query, limit, min_score, filters)
        elif strategy == RetrievalStrategy.FUSION:
            return self._retrieve_fusion(query, limit, min_score, filters)
        elif strategy == RetrievalStrategy.HYBRID:
            return self._retrieve_hybrid(query, limit, min_score, filters)
        else:
            # Default to keyword
            return self._retrieve_keyword(query, limit, min_score, filters)

    def _retrieve_keyword(
        self,
        query: str,
        limit: int,
        min_score: float,
        filters: dict | None,
    ) -> list[RetrievalResult]:
        """Retrieve using keyword matching."""
        # Get candidate memories
        candidates = self._get_candidates(filters)

        # Score and filter
        results = []
        for memory in candidates:
            score = self.scorer.score(memory, query)

            if score >= min_score:
                results.append(RetrievalResult(
                    memory=memory,
                    score=score,
                    strategy="keyword",
                ))

        # Sort by score
        results.sort(key=lambda r: r.score, reverse=True)

        return results[:limit]

    def _retrieve_temporal(
        self,
        query: str,
        limit: int,
        min_score: float,
        filters: dict | None,
    ) -> list[RetrievalResult]:
        """Retrieve using temporal ordering."""
        # Get candidate memories (respects all filters)
        candidates = self._get_candidates(filters)

        # Sort by recency
        candidates.sort(key=lambda m: m.timestamp, reverse=True)

        # Take top candidates
        candidates = candidates[:limit * 2]

        # Score and filter
        results = []
        for memory in candidates:
            score = self.scorer.score(memory, query)

            if score >= min_score:
                results.append(RetrievalResult(
                    memory=memory,
                    score=score,
                    strategy="temporal",
                ))

        # Sort by score
        results.sort(key=lambda r: r.score, reverse=True)

        return results[:limit]

    def _retrieve_importance(
        self,
        query: str,
        limit: int,
        min_score: float,
        filters: dict | None,
    ) -> list[RetrievalResult]:
        """Retrieve using importance weighting."""
        # Get candidate memories (respects all filters)
        candidates = self._get_candidates(filters)

        # Filter by importance
        important = [m for m in candidates if m.importance >= 0.5]

        # Score and filter
        results = []
        for memory in important:
            score = self.scorer.score(memory, query)

            if score >= min_score:
                results.append(RetrievalResult(
                    memory=memory,
                    score=score,
                    strategy="importance",
                ))

        # Sort by score
        results.sort(key=lambda r: r.score, reverse=True)

        return results[:limit]

    def _retrieve_fusion(
        self,
        query: str,
        limit: int,
        min_score: float,
        filters: dict | None,
    ) -> list[RetrievalResult]:
        """Retrieve using 3-signal fusion (semantic + temporal + behavioral).

        Falls back to the MemoryRetriever's own scorer with an additional
        behavioral boost from normalized access frequency.
        """
        # Get candidate memories
        candidates = self._get_candidates(filters)
        if not candidates:
            return []

        current_time = time.time()

        scored: list[tuple[Memory, float]] = []
        for memory in candidates:
            # Semantic: use existing content scorer
            sem_score = self.scorer._calculate_content_similarity(memory.content, query)

            # Temporal: recency score
            age_days = (current_time - memory.timestamp) / 86400
            temp_score = max(0.0, 1.0 - (age_days / 30))

            # Behavioral: normalized access frequency as proxy
            beh_score = min(1.0, memory.access_count / 10)

            # Equal-weight fusion
            combined = (sem_score + temp_score + beh_score) / 3.0

            if combined >= min_score:
                scored.append((memory, combined, sem_score, temp_score, beh_score))

        scored.sort(key=lambda x: x[1], reverse=True)

        results: list[RetrievalResult] = []
        for mem, combined, sem, temp, beh in scored[:limit]:
            results.append(RetrievalResult(
                memory=mem,
                score=combined,
                strategy="fusion",
                metadata={
                    "semantic_score": round(sem, 4),
                    "temporal_score": round(temp, 4),
                    "behavioral_score": round(beh, 4),
                },
            ))

        return results

    def _retrieve_hybrid(
        self,
        query: str,
        limit: int,
        min_score: float,
        filters: dict | None,
    ) -> list[RetrievalResult]:
        """Retrieve using hybrid approach."""
        # Get results from multiple strategies
        keyword_results = self._retrieve_keyword(query, limit, min_score, filters)
        temporal_results = self._retrieve_temporal(query, limit, min_score, filters)
        importance_results = self._retrieve_importance(query, limit, min_score, filters)

        # Combine and deduplicate
        seen = set()
        combined = []

        for result in keyword_results + temporal_results + importance_results:
            if result.memory.memory_id not in seen:
                seen.add(result.memory.memory_id)
                result.strategy = "hybrid"
                combined.append(result)

        # Re-score and sort
        combined.sort(key=lambda r: r.score, reverse=True)

        return combined[:limit]

    def _get_candidates(self, filters: dict | None) -> list[Memory]:
        """
        Get candidate memories based on filters.

        Args:
            filters: Filter criteria

        Returns:
            List of candidate memories
        """
        if not filters:
            return self.long_term_memory.store.get_all()

        candidates = None

        # Filter by type
        if "type" in filters:
            candidates = self.long_term_memory.search_by_type(filters["type"])

        # Filter by tags
        if "tags" in filters:
            tag_results = self.long_term_memory.search_by_tags(
                filters["tags"],
                match_all=filters.get("match_all_tags", False),
            )

            if candidates is None:
                candidates = tag_results
            else:
                # Intersection
                candidate_ids = {m.memory_id for m in candidates}
                candidates = [m for m in tag_results if m.memory_id in candidate_ids]

        # Filter by time range
        if "time_range" in filters:
            time_results = self.long_term_memory.search_by_time_range(
                start_time=filters["time_range"].get("start"),
                end_time=filters["time_range"].get("end"),
            )

            if candidates is None:
                candidates = time_results
            else:
                # Intersection
                candidate_ids = {m.memory_id for m in candidates}
                candidates = [m for m in time_results if m.memory_id in candidate_ids]

        return candidates or self.long_term_memory.store.get_all()

    def retrieve_similar(
        self,
        memory: Memory,
        limit: int = 5,
        min_score: float = 0.5,
    ) -> list[RetrievalResult]:
        """
        Retrieve memories similar to a given memory.

        Args:
            memory: Reference memory
            limit: Maximum results
            min_score: Minimum similarity score

        Returns:
            List of similar memories
        """
        # Use memory content as query
        query = memory.content

        # Filter by same type and tags
        filters = {
            "type": memory.memory_type,
            "tags": memory.tags,
            "match_all_tags": False,
        }

        results = self.retrieve(
            query=query,
            strategy=RetrievalStrategy.HYBRID,
            limit=limit + 1,  # +1 to account for self
            min_score=min_score,
            filters=filters,
        )

        # Remove the reference memory itself
        results = [r for r in results if r.memory.memory_id != memory.memory_id]

        return results[:limit]

    def get_statistics(self) -> dict:
        """
        Get retrieval statistics.

        Returns:
            Statistics dictionary
        """
        return {
            "default_strategy": self.default_strategy.value,
            "scorer_weights": {
                "importance": self.scorer.importance_weight,
                "recency": self.scorer.recency_weight,
                "frequency": self.scorer.frequency_weight,
                "content": self.scorer.content_weight,
            },
        }
