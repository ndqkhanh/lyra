"""Embedding-based Dead-End Registry — semantic similarity via TF-IDF cosine similarity.

Upgrades the keyword-overlap DeadEndRegistry with embedding vectors for
more accurate semantic matching of hypotheses against known dead ends.
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from lyra_core.collective import DeadEndEntry, DeadEndRegistry


@dataclass
class EmbeddingDeadEndEntry(DeadEndEntry):
    """DeadEndEntry extended with an embedding vector for cosine similarity."""

    embedding: list[float] = field(default_factory=list)


class TFIDFVectorizer:
    """Lightweight TF-IDF vectorizer — no external ML dependencies.

    Computes sparse TF-IDF vectors from text documents using pure Python,
    suitable for cosine similarity comparison in the dead-end registry.
    """

    def __init__(self) -> None:
        self._vocabulary: dict[str, int] = {}
        self._idf: dict[str, float] = {}
        self._doc_count: int = 0

    def fit(self, documents: list[str]) -> TFIDFVectorizer:
        """Build vocabulary and compute IDF from a corpus of documents."""
        df: dict[str, int] = defaultdict(int)
        self._doc_count = len(documents)

        for doc in documents:
            terms = set(self._tokenize(doc))
            for term in terms:
                df[term] = df.get(term, 0) + 1

        self._vocabulary = {term: idx for idx, term in enumerate(sorted(df))}
        self._idf = {
            term: math.log((self._doc_count + 1) / (freq + 1)) + 1.0
            for term, freq in df.items()
        }

        return self

    def fit_transform(self, documents: list[str]) -> list[list[float]]:
        """Fit vocabulary and transform documents in one step."""
        self.fit(documents)
        return self.transform(documents)

    def transform(self, documents: list[str]) -> list[list[float]]:
        """Convert documents to TF-IDF vectors."""
        vectors: list[list[float]] = []
        vocab_size = len(self._vocabulary)

        for doc in documents:
            vec = [0.0] * vocab_size
            term_counts: dict[str, int] = defaultdict(int)
            tokens = self._tokenize(doc)
            for token in tokens:
                if token in self._vocabulary:
                    term_counts[token] += 1

            norm = len(tokens) or 1
            for term, count in term_counts.items():
                idx = self._vocabulary[term]
                tf = count / norm
                vec[idx] = tf * self._idf.get(term, 0.0)

            vectors.append(vec)

        return vectors

    def transform_one(self, text: str) -> list[float]:
        """Transform a single document to a TF-IDF vector."""
        return self.transform([text])[0]

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Simple word tokenizer — lowercase, split on non-alphanumeric."""
        return [t for t in re.split(r"[^a-zA-Z0-9]+", text.lower()) if t]

    @staticmethod
    def cosine_similarity(a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if not a or not b:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b, strict=False))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)

    @property
    def vocab_size(self) -> int:
        return len(self._vocabulary)


class EmbeddingDeadEndRegistry(DeadEndRegistry):
    """Dead-end registry using TF-IDF embedding cosine similarity.

    Extends the keyword-overlap DeadEndRegistry with semantic matching:
    - Maintains a TF-IDF vectorizer trained on all registered dead ends
    - Uses cosine similarity instead of Jaccard keyword overlap
    - Falls back to keyword matching when vocabulary is insufficient
    - Supports incremental updates when new dead ends are registered

    Like AutoScientists' query_nearest(hypothesis) → distance → if < ρ: skip,
    but with embedding-based distance instead of keyword overlap.
    """

    def __init__(self, similarity_threshold: float = 0.7) -> None:
        super().__init__(similarity_threshold=similarity_threshold)
        self._vectorizer = TFIDFVectorizer()
        self._embeddings: dict[str, list[float]] = {}
        self._dirty: bool = False

    def register(self, entry: DeadEndEntry) -> None:
        """Record a dead end with embedding support.

        Converts the entry to an EmbeddingDeadEndEntry if needed and
        builds its TF-IDF vector from hypothesis + approach + tags.
        """
        super().register(entry)
        doc = f"{entry.hypothesis} {entry.approach} {' '.join(entry.tags)}"
        self._dirty = True

        if not isinstance(entry, EmbeddingDeadEndEntry):
            embedding_entry = EmbeddingDeadEndEntry(
                id=entry.id,
                hypothesis=entry.hypothesis,
                approach=entry.approach,
                failure_reason=entry.failure_reason,
                discovered_by=entry.discovered_by,
                discovered_at=entry.discovered_at,
                severity=entry.severity,
                tags=entry.tags,
                related_threads=entry.related_threads,
                embedding=[],
            )
            self._entries[entry.id] = embedding_entry

        self._embeddings[entry.id] = self._vectorizer.transform_one(doc)

    def _rebuild_index(self) -> None:
        """Rebuild the TF-IDF index from all registered entries."""
        if not self._dirty:
            return
        docs = []
        for entry in self._entries.values():
            docs.append(
                f"{entry.hypothesis} {entry.approach} {' '.join(entry.tags)}"
            )
        if docs:
            self._vectorizer.fit(docs)
            self._embeddings = {}
            for entry in self._entries.values():
                doc = f"{entry.hypothesis} {entry.approach} {' '.join(entry.tags)}"
                self._embeddings[entry.id] = self._vectorizer.transform_one(doc)
        self._dirty = False

    def is_known_dead_end(self, hypothesis: str, approach: str = "",
                          threshold: float | None = None) -> tuple[bool, DeadEndEntry | None]:
        """Check using embedding cosine similarity (fallback to keyword)."""
        if not self._entries:
            return False, None

        self._rebuild_index()

        limit = threshold if threshold is not None else self._similarity_threshold

        if self._vectorizer.vocab_size < 3:
            return super().is_known_dead_end(hypothesis, approach, threshold)

        query_vec = self._vectorizer.transform_one(
            f"{hypothesis} {approach}"
        )

        best_entry: DeadEndEntry | None = None
        best_score = 0.0

        for entry_id, entry_vec in self._embeddings.items():
            sim = TFIDFVectorizer.cosine_similarity(query_vec, entry_vec)
            if sim > best_score:
                best_score = sim
                best_entry = self._entries.get(entry_id)

        if best_score >= limit and best_entry is not None:
            return True, best_entry
        return False, None

    def query_similar(self, text: str, top_k: int = 5) -> list[DeadEndEntry]:
        """Find semantically similar dead ends using cosine similarity."""
        if not self._entries:
            return []

        self._rebuild_index()

        if self._vectorizer.vocab_size < 3:
            return super().query_similar(text, top_k)

        query_vec = self._vectorizer.transform_one(text)
        scored: list[tuple[float, DeadEndEntry]] = []

        for entry_id, entry_vec in self._embeddings.items():
            sim = TFIDFVectorizer.cosine_similarity(query_vec, entry_vec)
            if sim > 0:
                entry = self._entries.get(entry_id)
                if entry is not None:
                    scored.append((sim, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:top_k]]

    @property
    def embedding_dim(self) -> int:
        """Current embedding dimensionality (vocabulary size)."""
        return self._vectorizer.vocab_size

    def to_dict(self) -> dict[str, Any]:
        """Serialize registry state for persistence."""
        return {
            "similarity_threshold": self._similarity_threshold,
            "entries": [
                {
                    "id": e.id,
                    "hypothesis": e.hypothesis,
                    "approach": e.approach,
                    "failure_reason": e.failure_reason,
                    "discovered_by": e.discovered_by,
                    "discovered_at": e.discovered_at,
                    "severity": e.severity,
                    "tags": e.tags,
                    "related_threads": e.related_threads,
                }
                for e in self._entries.values()
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EmbeddingDeadEndRegistry:
        """Deserialize registry from persisted state."""
        registry = cls(
            similarity_threshold=data.get("similarity_threshold", 0.7),
        )
        for entry_data in data.get("entries", []):
            entry = DeadEndEntry(
                id=entry_data["id"],
                hypothesis=entry_data["hypothesis"],
                approach=entry_data["approach"],
                failure_reason=entry_data["failure_reason"],
                discovered_by=entry_data["discovered_by"],
                discovered_at=entry_data.get("discovered_at", 0.0),
                severity=entry_data.get("severity", "moderate"),
                tags=entry_data.get("tags", []),
                related_threads=entry_data.get("related_threads", []),
            )
            registry.register(entry)
        return registry


__all__ = [
    "EmbeddingDeadEndEntry",
    "EmbeddingDeadEndRegistry",
    "TFIDFVectorizer",
]
