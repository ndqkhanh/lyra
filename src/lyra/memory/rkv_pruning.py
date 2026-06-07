"""
R-KV Pruning — redundancy-aware KV cache compression that preserves keys
for important memories.

Provides:
  - prune_redundant_keys(kv_cache, threshold) -> pruned_cache
  - RedundancyScore: cosine similarity between key vectors
  - Memory-aware: preserves keys for high-importance memories even when
    they are redundant with others
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


# ---------------------------------------------------------------------------
# Configuration defaults
# ---------------------------------------------------------------------------

DEFAULT_REDUNDANCY_THRESHOLD: float = 0.85
"""Cosine similarity above this threshold is considered redundant."""

DEFAULT_IMPORTANCE_PRESERVATION_THRESHOLD: float = 0.6
"""Keys for memories with importance >= this value are never pruned."""

MIN_KEYS_TO_KEEP: int = 4
"""Minimum number of keys to retain regardless of redundancy."""


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class RedundancyScore:
    """Redundancy assessment for a single key in the KV cache.

    Attributes:
        key_index: Position of the key in the original cache.
        max_similarity: Highest cosine similarity to any other key.
        most_similar_to: Index of the key it is most similar to.
        importance: Importance score of the associated memory (0.0-1.0).
        is_redundant: True if max_similarity >= threshold.
        preserved_as_important: True if kept due to high importance even
            when redundant.
    """

    key_index: int
    max_similarity: float = 0.0
    most_similar_to: int = -1
    importance: float = 0.0
    is_redundant: bool = False
    preserved_as_important: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "key_index": self.key_index,
            "max_similarity": round(self.max_similarity, 4),
            "most_similar_to": self.most_similar_to,
            "importance": round(self.importance, 4),
            "is_redundant": self.is_redundant,
            "preserved_as_important": self.preserved_as_important,
        }


@dataclass
class PrunedCache:
    """Result of pruning a KV cache.

    Attributes:
        keys: Pruned key tensor (n_pruned x d_model).
        values: Pruned value tensor (n_pruned x d_model).
        kept_indices: Indices of the keys that were kept.
        pruned_indices: Indices of the keys that were removed.
        redundancy_scores: Per-key redundancy assessment.
        compression_ratio: Fraction of keys removed (0.0-1.0).
    """

    keys: np.ndarray
    values: np.ndarray
    kept_indices: list[int]
    pruned_indices: list[int]
    redundancy_scores: list[RedundancyScore]
    compression_ratio: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "kept_count": len(self.kept_indices),
            "pruned_count": len(self.pruned_indices),
            "original_count": len(self.kept_indices) + len(self.pruned_indices),
            "compression_ratio": round(self.compression_ratio, 4),
        }


# ---------------------------------------------------------------------------
# Redundancy assessment
# ---------------------------------------------------------------------------


class RedundancyAssessor:
    """Compute per-key redundancy scores from a KV cache.

    Each key's redundancy is measured as the maximum cosine similarity
    it has to any other key. A high score indicates that the information
    carried by this key is largely duplicated elsewhere.
    """

    def __init__(
        self,
        threshold: float = DEFAULT_REDUNDANCY_THRESHOLD,
        importance_preservation_threshold: float = DEFAULT_IMPORTANCE_PRESERVATION_THRESHOLD,
        min_keys_to_keep: int = MIN_KEYS_TO_KEEP,
    ):
        self.threshold = threshold
        self.importance_preservation_threshold = importance_preservation_threshold
        self.min_keys_to_keep = min_keys_to_keep

    def assess(
        self,
        keys: np.ndarray,
        importance_scores: list[float] | None = None,
    ) -> list[RedundancyScore]:
        """Evaluate redundancy for every key in the cache.

        Args:
            keys: Key tensor of shape (n_keys, d_model).
            importance_scores: Per-key importance scores (0.0-1.0).
                If None, all keys are treated as having importance 0.0.

        Returns:
            A list of RedundancyScore, one per key.
        """
        n = keys.shape[0]
        if n == 0:
            return []

        if importance_scores is None:
            importance_scores = [0.0] * n
        if len(importance_scores) != n:
            raise ValueError(
                f"importance_scores length ({len(importance_scores)}) must "
                f"match number of keys ({n})"
            )

        # Normalise keys so cosine similarity = dot product
        keys_norm = keys / (np.linalg.norm(keys, axis=1, keepdims=True) + 1e-12)

        # Pairwise cosine similarity matrix (n x n)
        sim_matrix = keys_norm @ keys_norm.T

        # Mask the diagonal (similarity to self is always 1.0)
        np.fill_diagonal(sim_matrix, -1.0)

        scores: list[RedundancyScore] = []
        for i in range(n):
            max_sim = float(sim_matrix[i].max())
            most_similar = int(sim_matrix[i].argmax())

            imp = importance_scores[i]
            is_redundant = max_sim >= self.threshold
            preserved = is_redundant and imp >= self.importance_preservation_threshold

            scores.append(RedundancyScore(
                key_index=i,
                max_similarity=max_sim,
                most_similar_to=most_similar if most_similar != i else -1,
                importance=imp,
                is_redundant=is_redundant,
                preserved_as_important=preserved,
            ))

        return scores


# ---------------------------------------------------------------------------
# Pruning engine
# ---------------------------------------------------------------------------


class RKVPruner:
    """Redundancy-aware KV cache pruner with memory-importance preservation.

    Pruning strategy:
      1. Compute redundancy scores for all keys.
      2. Mark redundant keys for removal, but preserve those with high
         importance (>= importance_preservation_threshold).
      3. Always keep at least ``min_keys_to_keep`` keys.
      4. Return the pruned cache and a full redundancy report.

    Usage::

        pruner = RKVPruner()
        pruned = pruner.prune(kv_cache_keys, kv_cache_values)
        print(f"Compressed {pruned.compression_ratio:.1%}")
    """

    def __init__(
        self,
        threshold: float = DEFAULT_REDUNDANCY_THRESHOLD,
        importance_preservation_threshold: float = DEFAULT_IMPORTANCE_PRESERVATION_THRESHOLD,
        min_keys_to_keep: int = MIN_KEYS_TO_KEEP,
    ):
        self.assessor = RedundancyAssessor(
            threshold=threshold,
            importance_preservation_threshold=importance_preservation_threshold,
            min_keys_to_keep=min_keys_to_keep,
        )
        self.min_keys_to_keep = min_keys_to_keep

    def prune(
        self,
        keys: np.ndarray,
        values: np.ndarray,
        importance_scores: list[float] | None = None,
    ) -> PrunedCache:
        """Prune redundant keys from the KV cache.

        Args:
            keys: Key tensor (n_keys, d_model).
            values: Value tensor (n_keys, d_model).
            importance_scores: Per-key importance scores. If None, all
                keys get importance 0.0 (no memory-aware preservation).

        Returns:
            A PrunedCache with the compressed tensors and full report.
        """
        n = keys.shape[0]
        if n == 0:
            return PrunedCache(
                keys=np.array([]),
                values=np.array([]),
                kept_indices=[],
                pruned_indices=[],
                redundancy_scores=[],
                compression_ratio=0.0,
            )

        scores = self.assessor.assess(keys, importance_scores)
        if importance_scores is None:
            importance_scores = [0.0] * n

        # Decision logic
        keep: set[int] = set()
        prune: set[int] = set()

        for s in scores:
            if not s.is_redundant:
                keep.add(s.key_index)
            elif s.preserved_as_important:
                keep.add(s.key_index)
            else:
                prune.add(s.key_index)

        # Enforce min_keys_to_keep
        if len(keep) < self.min_keys_to_keep:
            deficit = self.min_keys_to_keep - len(keep)
            # Bring back the most important pruned keys first
            candidates = sorted(
                [s for s in scores if s.key_index in prune],
                key=lambda s: s.importance,
                reverse=True,
            )
            for s in candidates[:deficit]:
                prune.discard(s.key_index)
                keep.add(s.key_index)

        kept_indices = sorted(keep)
        pruned_indices = sorted(prune)

        compression_ratio = len(pruned_indices) / max(n, 1)

        return PrunedCache(
            keys=keys[kept_indices],
            values=values[kept_indices],
            kept_indices=kept_indices,
            pruned_indices=pruned_indices,
            redundancy_scores=scores,
            compression_ratio=compression_ratio,
        )


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------


def prune_redundant_keys(
    kv_cache: dict[str, np.ndarray],
    threshold: float = DEFAULT_REDUNDANCY_THRESHOLD,
    importance_scores: list[float] | None = None,
) -> dict[str, np.ndarray]:
    """One-shot convenience wrapper for KV cache pruning.

    Args:
        kv_cache: Dict with ``"keys"`` and ``"values"`` entries.
        threshold: Cosine similarity threshold for redundancy.
        importance_scores: Per-key importance (optional).

    Returns:
        Pruned cache dict with ``"keys"``, ``"values"``, plus
        ``"pruned_indices"`` and ``"kept_indices"``.
    """
    keys = kv_cache.get("keys", np.array([]))
    values = kv_cache.get("values", np.array([]))
    pruner = RKVPruner(threshold=threshold)
    result = pruner.prune(keys, values, importance_scores)
    return {
        "keys": result.keys,
        "values": result.values,
        "kept_indices": result.kept_indices,
        "pruned_indices": result.pruned_indices,
        "compression_ratio": result.compression_ratio,
    }
