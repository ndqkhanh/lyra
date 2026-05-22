"""
Memory Retrieval - Intelligent memory search and retrieval.
"""

import time
from typing import List, Dict, Optional
from enum import Enum
from dataclasses import dataclass

from src.memory.memory_store import Memory
from src.memory.long_term_memory import LongTermMemory


class RetrievalStrategy(Enum):
    """Memory retrieval strategies."""
    SEMANTIC = "semantic"          # Semantic similarity (requires embeddings)
    KEYWORD = "keyword"            # Keyword matching
    TEMPORAL = "temporal"          # Time-based
    IMPORTANCE = "importance"      # Importance-weighted
    HYBRID = "hybrid"              # Combine multiple strategies


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
    metadata: Dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


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
        query: Optional[str] = None,
        current_time: Optional[float] = None,
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
        strategy: Optional[RetrievalStrategy] = None,
        limit: int = 10,
        min_score: float = 0.0,
        filters: Optional[Dict] = None,
    ) -> List[RetrievalResult]:
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
        filters: Optional[Dict],
    ) -> List[RetrievalResult]:
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
        filters: Optional[Dict],
    ) -> List[RetrievalResult]:
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
        filters: Optional[Dict],
    ) -> List[RetrievalResult]:
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

    def _retrieve_hybrid(
        self,
        query: str,
        limit: int,
        min_score: float,
        filters: Optional[Dict],
    ) -> List[RetrievalResult]:
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

    def _get_candidates(self, filters: Optional[Dict]) -> List[Memory]:
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
    ) -> List[RetrievalResult]:
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

    def get_statistics(self) -> Dict:
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
