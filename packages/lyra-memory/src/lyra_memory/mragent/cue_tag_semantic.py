"""MRAgent Cue-Tag-Semantic Encoder — fact-aware semantic embedding.

Implements the semantic encoding pathway from MRAgent (ICLR 2026 MemAgents Workshop).
Concatenates cue + tags + semantic fact to create fact-aware embeddings optimized
for knowledge retrieval rather than episodic recall.

Key distinction from episode encoding:
- Episode: "What happened?" (temporal, contextual, narrative)
- Semantic: "What is true?" (factual, declarative, timeless)
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class SemanticEncoding:
    """Fact-aware semantic embedding with cue and tag information."""

    fact_id: str
    cue: str
    tags: tuple[str, ...]
    fact: str
    embedding: np.ndarray
    timestamp: float

    def to_dict(self) -> dict:
        return {
            "fact_id": self.fact_id,
            "cue": self.cue,
            "tags": list(self.tags),
            "fact": self.fact,
            "embedding": self.embedding.tolist(),
            "timestamp": self.timestamp,
        }


class CueTagSemanticEncoder:
    """Encodes semantic facts with their retrieval cues and tags.

    The cue-tag-semantic encoding concatenates:
      1. Retrieval cue (knowledge domain context)
      2. Tags (categorical metadata)
      3. Semantic fact (declarative knowledge)

    This creates embeddings optimized for factual knowledge retrieval,
    distinct from episodic memory which captures temporal narratives.
    """

    def __init__(self, embedding_dim: int = 384) -> None:
        self.embedding_dim = embedding_dim

    def encode(
        self,
        cue: str,
        tags: list[str],
        fact: str,
        fact_id: str = "",
        timestamp: float | None = None,
    ) -> SemanticEncoding:
        """Encode a semantic fact with its cue and tags.

        Args:
            cue: The retrieval cue (knowledge domain context)
            tags: Categorical metadata tags
            fact: The semantic fact to encode
            fact_id: Optional ID (auto-generated if not provided)
            timestamp: Optional timestamp (current time if not provided)

        Returns:
            SemanticEncoding with fact-aware embedding
        """
        import time

        fid = fact_id or self._make_id(cue, tags, fact)
        ts = timestamp if timestamp is not None else time.time()

        # Concatenate cue + tags + fact for fact-aware encoding
        combined_text = self._combine_cue_tags_fact(cue, tags, fact)
        embedding = self._encode_text(combined_text)

        return SemanticEncoding(
            fact_id=fid,
            cue=cue,
            tags=tuple(tags),
            fact=fact,
            embedding=embedding,
            timestamp=ts,
        )

    def encode_batch(
        self, items: list[tuple[str, list[str], str]]
    ) -> list[SemanticEncoding]:
        """Batch encode multiple (cue, tags, fact) tuples.

        Args:
            items: List of (cue, tags, fact) tuples

        Returns:
            List of SemanticEncoding objects
        """
        return [self.encode(cue, tags, fact) for cue, tags, fact in items]

    def similarity(self, a: SemanticEncoding, b: SemanticEncoding) -> float:
        """Compute cosine similarity between two semantic encodings."""
        return self._cosine_similarity(a.embedding, b.embedding)

    def retrieve(
        self,
        query_cue: str,
        query_tags: list[str],
        candidates: list[SemanticEncoding],
        top_k: int = 10,
    ) -> list[tuple[SemanticEncoding, float]]:
        """Retrieve top-k facts by encoding the query with the same cue-tag pattern.

        Args:
            query_cue: The retrieval cue
            query_tags: Query tags
            candidates: List of candidate semantic encodings
            top_k: Number of results to return

        Returns:
            List of (SemanticEncoding, similarity_score) tuples, sorted by score
        """
        # Encode the query using the same cue-tag pattern
        query_text = self._combine_cue_tags_fact(query_cue, query_tags, "")
        query_embedding = self._encode_text(query_text)

        # Score all candidates
        scored = [
            (candidate, self._cosine_similarity(query_embedding, candidate.embedding))
            for candidate in candidates
        ]

        # Sort by score descending and return top-k
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    # ── internal methods ──────────────────────────────────────────────────

    def _combine_cue_tags_fact(self, cue: str, tags: list[str], fact: str) -> str:
        """Combine cue, tags, and fact into a single text for encoding.

        Format: [CUE: {cue}] [TAGS: {tag1}, {tag2}, ...] [FACT: {fact}]
        """
        cue_part = f"[CUE: {cue}]" if cue else ""
        tags_part = f"[TAGS: {', '.join(tags)}]" if tags else ""
        fact_part = f"[FACT: {fact}]" if fact else ""
        parts = [p for p in [cue_part, tags_part, fact_part] if p]
        return " ".join(parts)

    def _encode_text(self, text: str) -> np.ndarray:
        """Encode text into a dense embedding vector.

        Uses a deterministic hash-based projection for reproducibility.
        In production, replace with a trained transformer encoder (e.g., BERT, MPNet).
        """
        dim = self.embedding_dim
        values: list[float] = []
        base_hash = hashlib.sha256(text.encode()).digest()

        for i in range(dim):
            seed = (base_hash[(i * 7) % len(base_hash)] + i) & 0xFF
            h = hashlib.sha256(bytes([seed]) + base_hash).digest()
            val = int.from_bytes(h[:4], "big") / 0xFFFFFFFF
            values.append(val * 2.0 - 1.0)

        # L2 normalize
        norm = math.sqrt(sum(v * v for v in values))
        if norm > 0:
            values = [v / norm for v in values]

        return np.array(values, dtype=np.float32)

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        dot = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return float(dot / (norm_a * norm_b))

    @staticmethod
    def _make_id(cue: str, tags: list[str], fact: str) -> str:
        """Generate a unique ID for a semantic encoding."""
        combined = f"{cue}|{','.join(sorted(tags))}|{fact}"
        h = hashlib.sha256(combined.encode()).hexdigest()[:16]
        return f"fact-{h}"


__all__ = ["CueTagSemanticEncoder", "SemanticEncoding"]
