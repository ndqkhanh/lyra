"""Token-Native Memory Index — retrieval via token overlap, no embeddings, no vector DB.

Based on ContextFit (⭐7) — the third memory paradigm alongside vector and graph.
Works directly in LLM token space for fast, cheap, embedding-free retrieval.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional

logger = logging.getLogger(__name__)

__all__ = [
    "MemoryTier",
    "TokenNativeIndex",
    "MemoryTierRouter",
]


class MemoryTier(Enum):
    TOKEN_NATIVE = auto()
    VECTOR = auto()
    GRAPH = auto()


class TokenNativeIndex:
    """Memory index using token overlap scoring — no embeddings needed."""

    def __init__(self, tokenizer: Callable[[str], list[int]] | None = None):
        self.tokenizer = tokenizer or self._simple_tokenize
        self.token_to_docs: dict[int, set[str]] = {}
        self.doc_store: dict[str, str] = {}
        self.doc_token_counts: dict[str, int] = {}

    def _simple_tokenize(self, text: str) -> list[int]:
        """Simple hash-based tokenizer when no LLM tokenizer is available."""
        return [hash(word) & 0xFFFFFFFF for word in text.lower().split()]

    def index(self, doc_id: str, text: str) -> None:
        """Index a document by its tokens."""
        tokens = set(self.tokenizer(text))
        self.doc_store[doc_id] = text
        self.doc_token_counts[doc_id] = len(tokens)
        for token in tokens:
            if token not in self.token_to_docs:
                self.token_to_docs[token] = set()
            self.token_to_docs[token].add(doc_id)

    def index_batch(self, documents: dict[str, str]) -> int:
        """Index multiple documents at once. Returns count."""
        for doc_id, text in documents.items():
            self.index(doc_id, text)
        return len(documents)

    def retrieve(self, query: str, top_k: int = 5) -> list[tuple[str, float]]:
        """Retrieve documents by token intersection scoring (BM25-style)."""
        query_tokens = set(self.tokenizer(query))
        if not query_tokens:
            return []

        # Compute scores using TF-IDF-like token overlap
        scores: dict[str, float] = defaultdict(float)
        for token in query_tokens:
            doc_ids = self.token_to_docs.get(token, set())
            idf = 1.0 / max(len(doc_ids), 1)
            for doc_id in doc_ids:
                scores[doc_id] += idf

        # Normalize by document length
        for doc_id in scores:
            doc_len = self.doc_token_counts.get(doc_id, 1)
            scores[doc_id] /= doc_len**0.5

        ranked = sorted(scores.items(), key=lambda x: -x[1])
        return [(doc_id, score) for doc_id, score in ranked[:top_k]]

    def get_document(self, doc_id: str) -> str | None:
        return self.doc_store.get(doc_id)

    def remove(self, doc_id: str) -> bool:
        """Remove a document from the index."""
        if doc_id not in self.doc_store:
            return False
        text = self.doc_store.pop(doc_id)
        tokens = set(self.tokenizer(text))
        for token in tokens:
            if token in self.token_to_docs:
                self.token_to_docs[token].discard(doc_id)
        self.doc_token_counts.pop(doc_id, None)
        return True

    @property
    def memory_footprint_bytes(self) -> int:
        """Estimated memory footprint — no vector storage."""
        return sum(len(docs) * 8 for docs in self.token_to_docs.values())

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "documents": len(self.doc_store),
            "unique_tokens": len(self.token_to_docs),
            "memory_bytes": self.memory_footprint_bytes,
        }


class MemoryTierRouter:
    """Routes queries to optimal memory tier based on latency budget and query type."""

    def route(
        self, query: str, latency_budget_ms: float, query_type: str = "general"
    ) -> MemoryTier:
        if latency_budget_ms < 50:
            return MemoryTier.TOKEN_NATIVE
        if query_type == "entity" or "relationship" in query.lower():
            return MemoryTier.GRAPH
        return MemoryTier.VECTOR
