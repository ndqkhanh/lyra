"""MRAgent Cue-Tag-Episode Encoder — context-aware episode embedding.

Implements the episode encoding pathway from MRAgent (ICLR 2026 MemAgents Workshop).
Concatenates cue + tags + episode content to create context-aware embeddings that
capture the retrieval context alongside the episode content.

Key insight: Encoding the retrieval cue with the episode improves precision by
embedding the "why this was stored" signal directly into the representation.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class EpisodeEncoding:
    """Context-aware episode embedding with cue and tag information."""

    episode_id: str
    cue: str
    tags: tuple[str, ...]
    episode: str
    embedding: np.ndarray
    timestamp: float

    def to_dict(self) -> dict:
        return {
            "episode_id": self.episode_id,
            "cue": self.cue,
            "tags": list(self.tags),
            "episode": self.episode,
            "embedding": self.embedding.tolist(),
            "timestamp": self.timestamp,
        }


class CueTagEpisodeEncoder:
    """Encodes episodes with their retrieval cues and tags for context-aware retrieval.

    The cue-tag-episode encoding concatenates:
      1. Retrieval cue (query context)
      2. Tags (categorical metadata)
      3. Episode content (the actual memory)

    This creates embeddings that are aware of *why* the episode was stored,
    improving retrieval precision when the same cue is used for lookup.
    """

    def __init__(self, embedding_dim: int = 384) -> None:
        self.embedding_dim = embedding_dim

    def encode(
        self,
        cue: str,
        tags: list[str],
        episode: str,
        episode_id: str = "",
        timestamp: float | None = None,
    ) -> EpisodeEncoding:
        """Encode an episode with its cue and tags into a context-aware embedding.

        Args:
            cue: The retrieval cue (query context that triggered storage)
            tags: Categorical metadata tags
            episode: The episode content to encode
            episode_id: Optional ID (auto-generated if not provided)
            timestamp: Optional timestamp (current time if not provided)

        Returns:
            EpisodeEncoding with context-aware embedding
        """
        import time

        eid = episode_id or self._make_id(cue, tags, episode)
        ts = timestamp if timestamp is not None else time.time()

        # Concatenate cue + tags + episode for context-aware encoding
        combined_text = self._combine_cue_tags_episode(cue, tags, episode)
        embedding = self._encode_text(combined_text)

        return EpisodeEncoding(
            episode_id=eid,
            cue=cue,
            tags=tuple(tags),
            episode=episode,
            embedding=embedding,
            timestamp=ts,
        )

    def encode_batch(
        self, items: list[tuple[str, list[str], str]]
    ) -> list[EpisodeEncoding]:
        """Batch encode multiple (cue, tags, episode) tuples.

        Args:
            items: List of (cue, tags, episode) tuples

        Returns:
            List of EpisodeEncoding objects
        """
        return [self.encode(cue, tags, episode) for cue, tags, episode in items]

    def similarity(self, a: EpisodeEncoding, b: EpisodeEncoding) -> float:
        """Compute cosine similarity between two episode encodings."""
        return self._cosine_similarity(a.embedding, b.embedding)

    def retrieve(
        self,
        query_cue: str,
        query_tags: list[str],
        candidates: list[EpisodeEncoding],
        top_k: int = 10,
    ) -> list[tuple[EpisodeEncoding, float]]:
        """Retrieve top-k episodes by encoding the query with the same cue-tag pattern.

        Args:
            query_cue: The retrieval cue
            query_tags: Query tags
            candidates: List of candidate episode encodings
            top_k: Number of results to return

        Returns:
            List of (EpisodeEncoding, similarity_score) tuples, sorted by score
        """
        # Encode the query using the same cue-tag pattern
        query_text = self._combine_cue_tags_episode(query_cue, query_tags, "")
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

    def _combine_cue_tags_episode(
        self, cue: str, tags: list[str], episode: str
    ) -> str:
        """Combine cue, tags, and episode into a single text for encoding.

        Format: [CUE: {cue}] [TAGS: {tag1}, {tag2}, ...] {episode}
        """
        cue_part = f"[CUE: {cue}]" if cue else ""
        tags_part = f"[TAGS: {', '.join(tags)}]" if tags else ""
        parts = [p for p in [cue_part, tags_part, episode] if p]
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
    def _make_id(cue: str, tags: list[str], episode: str) -> str:
        """Generate a unique ID for an episode encoding."""
        combined = f"{cue}|{','.join(sorted(tags))}|{episode}"
        h = hashlib.sha256(combined.encode()).hexdigest()[:16]
        return f"episode-{h}"


__all__ = ["CueTagEpisodeEncoder", "EpisodeEncoding"]
