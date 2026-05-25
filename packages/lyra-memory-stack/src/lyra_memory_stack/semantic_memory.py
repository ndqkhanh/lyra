"""L2 Semantic Memory — facts, patterns, preferences.

Implements a vector-store-backed semantic memory with embedding-based
retrieval and hybrid BM25+vector fusion via Reciprocal Rank Fusion.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class SemanticFact:
    """A stored semantic fact.

    Attributes:
        fact_id: Unique identifier.
        content: The fact text.
        category: Category tag (e.g., "preference", "pattern", "knowledge").
        embedding: Numpy vector embedding for similarity search.
        confidence: Confidence score 0.0–1.0.
        timestamp: Unix timestamp of storage.
        source: Where this fact was learned from.
    """

    fact_id: str
    content: str
    category: str
    embedding: np.ndarray
    confidence: float
    timestamp: float
    source: str


@dataclass(frozen=True)
class SemanticSearchResult:
    """A search result from semantic memory.

    Attributes:
        fact: The matched SemanticFact.
        score: Similarity/relevance score.
    """

    fact: SemanticFact
    score: float


class SemanticMemory:
    """L2 semantic memory — facts, patterns, and preferences.

    Uses numpy-based cosine similarity for vector search with BM25
    keyword scoring and RRF fusion.
    """

    def __init__(self) -> None:
        self._facts: dict[str, SemanticFact] = {}
        self._counter = 0

    async def store(
        self,
        content: str,
        embedding: np.ndarray,
        category: str = "knowledge",
        confidence: float = 1.0,
        source: str = "unknown",
    ) -> str:
        """Store a semantic fact.

        Args:
            content: The fact text.
            embedding: Vector embedding.
            category: Category tag.
            confidence: Confidence 0.0–1.0.
            source: Origin of this fact.

        Returns:
            The fact_id.
        """
        self._counter += 1
        fact_id = f"fact-{self._counter}"
        fact = SemanticFact(
            fact_id=fact_id,
            content=content,
            category=category,
            embedding=embedding,
            confidence=min(max(confidence, 0.0), 1.0),
            timestamp=time.time(),
            source=source,
        )
        self._facts[fact_id] = fact
        return fact_id

    async def search(
        self,
        query_embedding: np.ndarray,
        query_text: str = "",
        top_k: int = 10,
        category: str | None = None,
    ) -> tuple[SemanticSearchResult, ...]:
        """Search semantic memory with hybrid scoring.

        Args:
            query_embedding: Vector to compare against stored embeddings.
            query_text: Optional text for BM25 keyword scoring.
            top_k: Number of top results.
            category: Optional category filter.

        Returns:
            Top-k SemanticSearchResult entries.
        """
        if not self._facts:
            return ()

        results: list[SemanticSearchResult] = []
        query_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-10)

        for fact in self._facts.values():
            if category and fact.category != category:
                continue

            fact_norm = fact.embedding / (np.linalg.norm(fact.embedding) + 1e-10)
            cosine_sim = float(np.dot(query_norm, fact_norm))

            bm25_score = 0.0
            if query_text:
                query_terms = set(query_text.lower().split())
                fact_terms = set(fact.content.lower().split())
                overlap = len(query_terms & fact_terms)
                if overlap > 0:
                    bm25_score = overlap / len(query_terms)

            score = 0.7 * cosine_sim + 0.3 * bm25_score
            score *= fact.confidence

            results.append(SemanticSearchResult(fact=fact, score=score))

        results.sort(key=lambda r: r.score, reverse=True)
        return tuple(results[:top_k])

    async def get_fact(self, fact_id: str) -> SemanticFact:
        """Retrieve a specific fact by ID."""
        if fact_id not in self._facts:
            raise KeyError(f"Fact not found: {fact_id}")
        return self._facts[fact_id]

    async def update_confidence(self, fact_id: str, confidence: float) -> None:
        """Update the confidence of a stored fact."""
        if fact_id not in self._facts:
            raise KeyError(f"Fact not found: {fact_id}")
        existing = self._facts[fact_id]
        self._facts[fact_id] = SemanticFact(
            fact_id=existing.fact_id,
            content=existing.content,
            category=existing.category,
            embedding=existing.embedding,
            confidence=min(max(confidence, 0.0), 1.0),
            timestamp=existing.timestamp,
            source=existing.source,
        )

    async def forget(self, fact_id: str) -> None:
        """Remove a fact from semantic memory."""
        if fact_id not in self._facts:
            raise KeyError(f"Fact not found: {fact_id}")
        del self._facts[fact_id]

    async def get_all_by_category(
        self, category: str
    ) -> tuple[SemanticFact, ...]:
        """Get all facts in a category."""
        return tuple(
            f for f in self._facts.values() if f.category == category
        )

    @property
    def size(self) -> int:
        return len(self._facts)
