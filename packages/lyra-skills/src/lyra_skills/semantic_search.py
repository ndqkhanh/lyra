"""Semantic search for skills using NLP embeddings.

This module provides semantic skill discovery using sentence embeddings
instead of keyword matching. Skills are encoded into vector representations
and matched using cosine similarity.

Architecture:
- SkillEmbedder: Generates embeddings using sentence-transformers
- EmbeddingCache: Caches embeddings to avoid recomputation
- SemanticSkillSearch: Main search engine with hybrid scoring

Usage:
    >>> from lyra_skills.semantic_search import get_semantic_searcher
    >>> searcher = get_semantic_searcher()
    >>> results = searcher.search("write unit tests", skills, utility_scores)
    >>> for result in results:
    ...     print(f"{result.skill_id}: {result.hybrid_score:.2f}")

Dependencies:
    - sentence-transformers (optional, graceful fallback)
    - numpy
    - torch (via sentence-transformers)

Install with: pip install lyra[semantic]
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import numpy as np

logger = logging.getLogger(__name__)

# Global singleton
_EMBEDDER: Optional["SkillEmbedder"] = None
_CACHE: Optional["EmbeddingCache"] = None
_SEARCHER: Optional["SemanticSkillSearch"] = None


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_MODEL = "all-MiniLM-L6-v2"  # 384 dims, 80MB, fast
DEFAULT_THRESHOLD = 0.3  # Minimum similarity score
DEFAULT_TOP_K = 10  # Max results to return

# Hybrid scoring weights
WEIGHT_SEMANTIC = 0.5  # Semantic similarity
WEIGHT_UTILITY = 0.3  # Historical utility score
WEIGHT_RECENCY = 0.2  # Recency boost


# ---------------------------------------------------------------------------
# Embedding Generator
# ---------------------------------------------------------------------------


class SkillEmbedder:
    """Generate embeddings for skill descriptions using sentence-transformers.

    Uses the all-MiniLM-L6-v2 model by default (384 dimensions, 80MB).
    This model provides a good balance of speed and quality for semantic search.
    """

    def __init__(self, model_name: str = DEFAULT_MODEL):
        """Initialize embedder with specified model.

        Args:
            model_name: HuggingFace model name (default: all-MiniLM-L6-v2)

        Raises:
            ImportError: If sentence-transformers is not installed
        """
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise ImportError(
                "sentence-transformers not installed. "
                "Install with: pip install lyra[semantic]"
            ) from e

        logger.info(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.model_name = model_name

    def encode(self, text: str) -> np.ndarray:
        """Generate embedding for a single text.

        Args:
            text: Text to encode

        Returns:
            Embedding vector (384 dimensions for default model)
        """
        return self.model.encode(text, convert_to_numpy=True)

    def encode_batch(self, texts: list[str]) -> np.ndarray:
        """Generate embeddings for multiple texts (faster than sequential).

        Args:
            texts: List of texts to encode

        Returns:
            Array of embeddings (shape: [len(texts), 384])
        """
        return self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)


# ---------------------------------------------------------------------------
# Embedding Cache
# ---------------------------------------------------------------------------


class EmbeddingCache:
    """Cache pre-computed embeddings to avoid recomputation.

    Embeddings are stored in JSON format at $LYRA_HOME/skill_embeddings.json.
    Each embedding is keyed by skill_id and includes a hash of the text to
    detect when the skill description has changed.

    Format:
        {
          "version": 1,
          "model": "all-MiniLM-L6-v2",
          "embeddings": {
            "skill-id": {
              "skill_id": "skill-id",
              "text": "description...",
              "embedding": [0.123, -0.456, ...],
              "hash": "sha256_of_text",
              "created_at": 1748899200.0
            }
          }
        }
    """

    def __init__(self, cache_path: Path, model_name: str = DEFAULT_MODEL):
        """Initialize cache.

        Args:
            cache_path: Path to cache file
            model_name: Model name (embeddings are model-specific)
        """
        self.cache_path = cache_path
        self.model_name = model_name
        self.cache = self._load()

    def _load(self) -> dict:
        """Load cache from disk."""
        if not self.cache_path.exists():
            return {
                "version": 1,
                "model": self.model_name,
                "embeddings": {}
            }

        try:
            with open(self.cache_path, "r") as f:
                cache = json.load(f)

            # Invalidate if model changed
            if cache.get("model") != self.model_name:
                logger.warning(
                    f"Model changed from {cache.get('model')} to {self.model_name}, "
                    "invalidating cache"
                )
                return {
                    "version": 1,
                    "model": self.model_name,
                    "embeddings": {}
                }

            return cache

        except Exception as e:
            logger.error(f"Failed to load embedding cache: {e}")
            return {
                "version": 1,
                "model": self.model_name,
                "embeddings": {}
            }

    def _save(self) -> None:
        """Save cache to disk atomically."""
        try:
            # Ensure directory exists
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)

            # Write to temp file first
            import tempfile
            fd, temp_path = tempfile.mkstemp(
                dir=self.cache_path.parent,
                prefix=".skill_embeddings_",
                suffix=".json"
            )

            with os.fdopen(fd, "w") as f:
                json.dump(self.cache, f, indent=2)

            # Atomic replace
            os.replace(temp_path, self.cache_path)

        except Exception as e:
            logger.error(f"Failed to save embedding cache: {e}")

    def get(self, skill_id: str, text: str) -> Optional[np.ndarray]:
        """Get cached embedding if text hasn't changed.

        Args:
            skill_id: Skill identifier
            text: Current skill text

        Returns:
            Cached embedding or None if not found/stale
        """
        if skill_id not in self.cache["embeddings"]:
            return None

        entry = self.cache["embeddings"][skill_id]
        text_hash = hashlib.sha256(text.encode()).hexdigest()

        # Check if text changed
        if entry["hash"] != text_hash:
            logger.debug(f"Skill {skill_id} text changed, cache miss")
            return None

        return np.array(entry["embedding"], dtype=np.float32)

    def set(self, skill_id: str, text: str, embedding: np.ndarray) -> None:
        """Cache embedding for skill.

        Args:
            skill_id: Skill identifier
            text: Skill text
            embedding: Embedding vector
        """
        text_hash = hashlib.sha256(text.encode()).hexdigest()

        self.cache["embeddings"][skill_id] = {
            "skill_id": skill_id,
            "text": text[:200],  # Store truncated text for debugging
            "embedding": embedding.tolist(),
            "hash": text_hash,
            "created_at": time.time()
        }

        self._save()

    def clear(self) -> None:
        """Clear all cached embeddings."""
        self.cache["embeddings"] = {}
        self._save()

    def stats(self) -> dict:
        """Get cache statistics."""
        return {
            "model": self.cache["model"],
            "count": len(self.cache["embeddings"]),
            "size_mb": self.cache_path.stat().st_size / 1024 / 1024
            if self.cache_path.exists() else 0
        }


# ---------------------------------------------------------------------------
# Search Result
# ---------------------------------------------------------------------------


@dataclass
class SearchResult:
    """Result from semantic skill search.

    Attributes:
        skill_id: Skill identifier
        skill: Skill object
        semantic_score: Cosine similarity (0-1)
        utility_score: Historical utility (0-1)
        recency_boost: Recency boost (0-1)
        hybrid_score: Combined score (0-1)
        reason: Human-readable explanation
    """

    skill_id: str
    skill: Any
    semantic_score: float
    utility_score: float
    recency_boost: float
    hybrid_score: float
    reason: str


# ---------------------------------------------------------------------------
# Semantic Search Engine
# ---------------------------------------------------------------------------


class SemanticSkillSearch:
    """Semantic skill search engine using embeddings and hybrid scoring.

    Combines three signals:
    1. Semantic similarity (cosine similarity of embeddings)
    2. Utility score (historical success rate from ledger)
    3. Recency boost (recently used skills ranked higher)

    The hybrid score is a weighted combination:
        hybrid = 0.5 * semantic + 0.3 * utility + 0.2 * recency
    """

    def __init__(
        self,
        embedder: SkillEmbedder,
        cache: EmbeddingCache,
        threshold: float = DEFAULT_THRESHOLD,
        top_k: int = DEFAULT_TOP_K
    ):
        """Initialize search engine.

        Args:
            embedder: Embedding generator
            cache: Embedding cache
            threshold: Minimum similarity score (default: 0.3)
            top_k: Maximum results to return (default: 10)
        """
        self.embedder = embedder
        self.cache = cache
        self.threshold = threshold
        self.top_k = top_k

    def search(
        self,
        query: str,
        skills: list[Any],
        utility_scores: Optional[dict[str, float]] = None,
        recency_boosts: Optional[dict[str, float]] = None
    ) -> list[SearchResult]:
        """Search skills using semantic similarity.

        Args:
            query: Search query
            skills: List of skill objects
            utility_scores: Optional utility scores from ledger
            recency_boosts: Optional recency boosts

        Returns:
            List of SearchResult objects, sorted by hybrid score
        """
        if not skills:
            return []

        utility_scores = utility_scores or {}
        recency_boosts = recency_boosts or {}

        # 1. Generate query embedding
        query_embedding = self.embedder.encode(query)

        # 2. Get/compute skill embeddings
        skill_embeddings = []
        for skill in skills:
            text = self._skill_to_text(skill)
            embedding = self.cache.get(skill.id, text)

            if embedding is None:
                embedding = self.embedder.encode(text)
                self.cache.set(skill.id, text, embedding)

            skill_embeddings.append(embedding)

        # 3. Compute cosine similarities
        similarities = self._cosine_similarity_batch(
            query_embedding,
            np.array(skill_embeddings)
        )

        # 4. Build results with hybrid scoring
        results = []
        for skill, similarity in zip(skills, similarities):
            if similarity < self.threshold:
                continue

            utility = utility_scores.get(skill.id, 0.5)
            recency = recency_boosts.get(skill.id, 0.0)
            hybrid = self._hybrid_score(similarity, utility, recency)

            results.append(SearchResult(
                skill_id=skill.id,
                skill=skill,
                semantic_score=float(similarity),
                utility_score=utility,
                recency_boost=recency,
                hybrid_score=hybrid,
                reason=self._format_reason(similarity, utility, recency)
            ))

        # 5. Sort by hybrid score
        results.sort(key=lambda r: r.hybrid_score, reverse=True)

        return results[:self.top_k]

    def _cosine_similarity_batch(
        self,
        query: np.ndarray,
        embeddings: np.ndarray
    ) -> np.ndarray:
        """Compute cosine similarity between query and all embeddings.

        Args:
            query: Query embedding (shape: [dim])
            embeddings: Skill embeddings (shape: [n_skills, dim])

        Returns:
            Similarity scores (shape: [n_skills])
        """
        # Normalize vectors
        query_norm = query / np.linalg.norm(query)
        embeddings_norm = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

        # Dot product = cosine similarity for normalized vectors
        return np.dot(embeddings_norm, query_norm)

    def _hybrid_score(
        self,
        semantic: float,
        utility: float,
        recency: float
    ) -> float:
        """Combine semantic similarity, utility, and recency into hybrid score.

        Args:
            semantic: Semantic similarity (0-1)
            utility: Utility score (0-1)
            recency: Recency boost (0-1)

        Returns:
            Hybrid score (0-1)
        """
        return (
            WEIGHT_SEMANTIC * semantic +
            WEIGHT_UTILITY * utility +
            WEIGHT_RECENCY * recency
        )

    def _format_reason(
        self,
        semantic: float,
        utility: float,
        recency: float
    ) -> str:
        """Format human-readable explanation of score."""
        parts = [f"semantic: {semantic:.2f}"]

        if utility > 0.5:
            parts.append(f"utility: {utility:.2f}")

        if recency > 0.05:
            parts.append(f"recent: {recency:.2f}")

        return ", ".join(parts)

    def _skill_to_text(self, skill: Any) -> str:
        """Convert skill to searchable text.

        Combines name, description, tags, and category into a single string.
        """
        parts = []

        if hasattr(skill, "name") and skill.name:
            parts.append(skill.name)

        if hasattr(skill, "description") and skill.description:
            parts.append(skill.description)

        if hasattr(skill, "tags") and skill.tags:
            parts.append(" ".join(skill.tags))

        if hasattr(skill, "category") and skill.category:
            parts.append(skill.category)

        return " ".join(p for p in parts if p)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_semantic_searcher(
    cache_path: Optional[Path] = None,
    model_name: str = DEFAULT_MODEL
) -> SemanticSkillSearch:
    """Get or create the global semantic searcher singleton.

    Args:
        cache_path: Optional cache path (default: $LYRA_HOME/skill_embeddings.json)
        model_name: Optional model name (default: all-MiniLM-L6-v2)

    Returns:
        SemanticSkillSearch instance

    Raises:
        ImportError: If sentence-transformers is not installed
    """
    global _EMBEDDER, _CACHE, _SEARCHER

    if _SEARCHER is not None:
        return _SEARCHER

    # Determine cache path
    if cache_path is None:
        lyra_home = os.environ.get("LYRA_HOME")
        base = Path(lyra_home) if lyra_home else Path.home() / ".lyra"
        cache_path = base / "skill_embeddings.json"

    # Create components
    _EMBEDDER = SkillEmbedder(model_name)
    _CACHE = EmbeddingCache(cache_path, model_name)
    _SEARCHER = SemanticSkillSearch(_EMBEDDER, _CACHE)

    return _SEARCHER


def is_semantic_search_available() -> bool:
    """Check if semantic search dependencies are installed."""
    try:
        import sentence_transformers  # noqa: F401
        import torch  # noqa: F401
        return True
    except ImportError:
        return False
