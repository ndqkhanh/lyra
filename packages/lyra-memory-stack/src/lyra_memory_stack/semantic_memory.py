"""L2 Semantic Memory — Facts, patterns, and embeddings-based retrieval.

Stores semantic facts with optional vector embeddings for cosine-similarity
retrieval, keyword matching, privacy tier support, and hybrid search.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any

from lyra_memory_stack.exceptions import MemoryNotFoundError
from lyra_memory_stack.privacy_tiers import PrivacyTier, PrivacyManager


@dataclass(frozen=True)
class Fact:
    """A semantic fact stored in semantic memory."""

    fact_id: str
    domain: str
    statement: str
    confidence: float = 0.5
    source: str = "agent"
    timestamp: float = field(default_factory=time.time)
    tier: PrivacyTier = PrivacyTier.PRIVATE
    embedding: tuple[float, ...] = ()
    tags: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FactQueryResult:
    """Result from a semantic fact query."""

    fact: Fact
    score: float  # similarity/relevance score


def _cosine_similarity(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    """Compute cosine similarity between two embedding vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _keyword_score(statement: str, query: str) -> float:
    """Compute a simple keyword matching score."""
    statement_lower = statement.lower()
    query_lower = query.lower()
    query_words = query_lower.split()
    if not query_words:
        return 0.0
    matches = sum(1 for w in query_words if w in statement_lower)
    return matches / len(query_words)


class SemanticMemory:
    """In-memory semantic memory with vector and keyword retrieval.

    Supports hybrid retrieval (vector similarity + keyword matching),
    domain-scoped queries, privacy filtering, and fact updates.
    """

    _facts: dict[str, Fact]
    _embedding_dim: int
    _privacy_manager: PrivacyManager

    def __init__(
        self,
        embedding_dim: int = 128,
        privacy_manager: PrivacyManager | None = None,
    ) -> None:
        self._facts = {}
        self._embedding_dim = embedding_dim
        self._privacy_manager = privacy_manager or PrivacyManager()

    def add_fact(self, fact: Fact) -> str:
        """Add a fact to semantic memory. Returns the fact_id."""
        self._facts[fact.fact_id] = fact
        return fact.fact_id

    def get_fact(self, fact_id: str) -> Fact:
        """Get a fact by ID. Raises MemoryNotFoundError if missing."""
        fact = self._facts.get(fact_id)
        if fact is None:
            raise MemoryNotFoundError(fact_id, "semantic")
        return fact

    def update_fact(
        self,
        fact_id: str,
        *,
        statement: str | None = None,
        confidence: float | None = None,
        embedding: tuple[float, ...] | None = None,
        tags: tuple[str, ...] | None = None,
        tier: PrivacyTier | None = None,
    ) -> Fact:
        """Update fields of an existing fact (immutable pattern).

        Returns the new Fact. Raises MemoryNotFoundError if fact_id is unknown.
        """
        old = self.get_fact(fact_id)
        new_fact = Fact(
            fact_id=old.fact_id,
            domain=old.domain,
            statement=statement if statement is not None else old.statement,
            confidence=confidence if confidence is not None else old.confidence,
            source=old.source,
            timestamp=time.time(),
            tier=tier if tier is not None else old.tier,
            embedding=embedding if embedding is not None else old.embedding,
            tags=tags if tags is not None else old.tags,
            metadata=old.metadata,
        )
        self._facts[fact_id] = new_fact
        return new_fact

    def delete_fact(self, fact_id: str) -> bool:
        """Delete a fact by ID. Returns True if deleted."""
        return self._facts.pop(fact_id, None) is not None

    def query_facts(
        self,
        query: str,
        domain: str | None = None,
        limit: int = 10,
        min_confidence: float = 0.0,
        tier_filter: PrivacyTier | None = None,
    ) -> list[FactQueryResult]:
        """Hybrid query: keyword + optional vector similarity.

        Filters by domain, confidence, and privacy tier.
        """
        candidates = self._facts.values()

        # Filter by domain
        if domain:
            candidates = [f for f in candidates if f.domain == domain]

        # Filter by tier
        if tier_filter:
            candidates = [
                f for f in candidates
                if f.tier == tier_filter or f.tier.rank >= tier_filter.rank
            ]

        # Score candidates
        results: list[FactQueryResult] = []
        for fact in candidates:
            if fact.confidence < min_confidence:
                continue

            kw_score = _keyword_score(fact.statement, query)
            vec_score = 0.0
            if fact.embedding:
                # If no query embedding, we just use keyword
                vec_score = 0.0
            combined = kw_score * 0.6 + vec_score * 0.4

            # Boost by confidence
            combined = combined * (0.5 + fact.confidence * 0.5)

            if combined > 0:
                results.append(FactQueryResult(fact=fact, score=combined))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    def query_by_embedding(
        self,
        query_embedding: tuple[float, ...],
        limit: int = 10,
        domain: str | None = None,
    ) -> list[FactQueryResult]:
        """Query facts by embedding vector similarity."""
        candidates = self._facts.values()
        if domain:
            candidates = [f for f in candidates if f.domain == domain]

        results: list[FactQueryResult] = []
        for fact in candidates:
            if not fact.embedding:
                continue
            sim = _cosine_similarity(query_embedding, fact.embedding)
            if sim > 0:
                results.append(FactQueryResult(fact=fact, score=sim))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    def query_by_domain(self, domain: str) -> list[Fact]:
        """Get all facts in a domain."""
        return [f for f in self._facts.values() if f.domain == domain]

    def count(self) -> int:
        """Total number of facts stored."""
        return len(self._facts)

    def clear(self) -> None:
        """Clear all facts."""
        self._facts.clear()

    def all_facts(self) -> list[Fact]:
        """Return all stored facts."""
        return list(self._facts.values())

    def summary(self) -> dict[str, Any]:
        """Produce a summary of semantic memory state."""
        domains: dict[str, int] = {}
        total_confidence = 0.0
        for fact in self._facts.values():
            domains[fact.domain] = domains.get(fact.domain, 0) + 1
            total_confidence += fact.confidence
        return {
            "total_facts": self.count(),
            "domains": domains,
            "average_confidence": total_confidence / self.count() if self._facts else 0.0,
            "facts_with_embeddings": sum(1 for f in self._facts.values() if f.embedding),
            "embedding_dimension": self._embedding_dim,
        }
