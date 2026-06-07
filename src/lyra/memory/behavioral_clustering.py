"""
Behavioral Clustering — HDBSCAN-based clustering of memory items by usage
patterns, with automatic cluster labeling.

Provides:
  - ClusterMemoryItems(items) -> dict[cluster_id, list[MemoryItem]]
  - Behavioral similarity metrics: access frequency, co-access patterns,
    temporal locality
  - ClusterLabel: auto-generate descriptive labels for clusters
"""

from __future__ import annotations

import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from lyra.memory.cascade_memory import MemoryItem

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MIN_CLUSTER_SIZE: int = 2
"""Minimum number of items for a valid cluster (passed to HDBSCAN)."""

MIN_SAMPLES: int = 1
"""Minimum samples for HDBSCAN core-point estimation."""

DEFAULT_ACCESS_WEIGHT: float = 0.35
"""Weight for access-frequency feature in the behavioral vector."""

DEFAULT_COACCESS_WEIGHT: float = 0.35
"""Weight for co-access-pattern feature."""

DEFAULT_TEMPORAL_WEIGHT: float = 0.30
"""Weight for temporal-locality feature."""

CLUSTER_SILHOUETTE_THRESHOLD: float = 0.25
"""Minimum average silhouette score for a cluster to be considered valid."""


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class ClusterLabel:
    """Descriptive label automatically generated for a memory cluster.

    Attributes:
        cluster_id: The integer cluster identifier.
        label: Human-readable label.
        top_keywords: Most distinctive keywords for this cluster.
        avg_importance: Mean importance score of items in the cluster.
        size: Number of items in the cluster.
        silhouette: Average silhouette score for the cluster (0.0-1.0).
        is_noise: True if this cluster represents noise (HDBSCAN cluster -1).
    """

    cluster_id: int
    label: str = ""
    top_keywords: list[str] = field(default_factory=list)
    avg_importance: float = 0.0
    size: int = 0
    silhouette: float = 0.0
    is_noise: bool = False


@dataclass
class BehavioralClusteringResult:
    """Result of a behavioral clustering run.

    Attributes:
        clusters: Mapping from cluster_id to list of MemoryItems.
        labels: Mapping from cluster_id to ClusterLabel.
        noise_items: Items assigned to the noise cluster (-1).
        n_clusters: Number of non-noise clusters found.
        feature_matrix: The feature vectors used for clustering (n_items x n_features).
        silhouette_score: Overall average silhouette score.
    """

    clusters: dict[int, list[MemoryItem]] = field(default_factory=dict)
    labels: dict[int, ClusterLabel] = field(default_factory=dict)
    noise_items: list[MemoryItem] = field(default_factory=list)
    n_clusters: int = 0
    feature_matrix: np.ndarray | None = None
    silhouette_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_clusters": self.n_clusters,
            "noise_count": len(self.noise_items),
            "silhouette_score": round(self.silhouette_score, 4),
            "clusters": {
                str(cid): {
                    "size": len(items),
                    "label": self.labels[cid].label if cid in self.labels else "",
                    "avg_importance": self.labels[cid].avg_importance if cid in self.labels else 0.0,
                    "silhouette": self.labels[cid].silhouette if cid in self.labels else 0.0,
                }
                for cid, items in self.clusters.items()
                if not (cid in self.labels and self.labels[cid].is_noise)
            },
            "noise_label": (
                self.labels[-1].label if -1 in self.labels else ""
            ),
        }


# ---------------------------------------------------------------------------
# Behavioral feature extraction
# ---------------------------------------------------------------------------


class BehavioralFeatureExtractor:
    """Build feature vectors from memory-item usage patterns.

    Three signal types are encoded:
      1. **Access frequency**: how often each item is retrieved.
      2. **Co-access patterns**: pairwise co-occurrence of items in
         retrieval results (Jaccard similarity over access sets).
      3. **Temporal locality**: recency and regularity of access times.
    """

    def __init__(
        self,
        access_weight: float = DEFAULT_ACCESS_WEIGHT,
        coaccess_weight: float = DEFAULT_COACCESS_WEIGHT,
        temporal_weight: float = DEFAULT_TEMPORAL_WEIGHT,
    ):
        if not abs(access_weight + coaccess_weight + temporal_weight - 1.0) < 1e-6:
            raise ValueError(
                "Feature weights must sum to 1.0, got "
                f"({access_weight}, {coaccess_weight}, {temporal_weight})"
            )
        self.access_weight = access_weight
        self.coaccess_weight = coaccess_weight
        self.temporal_weight = temporal_weight

    def extract(self, items: list[MemoryItem]) -> np.ndarray:
        """Build a feature matrix of shape ``(len(items), 3)``.

        Each row is a 3-dimensional behavioral vector:
          [access_norm, coaccess_norm, temporal_norm]

        Args:
            items: Memory items to featurize.

        Returns:
            Float array of shape (n_items, 3).
        """
        n = len(items)
        if n == 0:
            return np.zeros((0, 3), dtype=np.float64)

        # --- 1. Access frequency ---
        access_feat = np.array([item.access_count for item in items], dtype=np.float64)
        max_access = access_feat.max()
        if max_access > 0:
            access_feat /= max_access

        # --- 2. Co-access patterns ---
        # Compute co-access Jaccard between each pair of items based on
        # shared content-type metadata.
        coaccess_feat = np.zeros(n, dtype=np.float64)
        for i, a in enumerate(items):
            shared = 0
            for b in items:
                if a is b:
                    continue
                # Co-access signal: same content-type + both accessed recently
                if (
                    a.content_type == b.content_type
                    and a.access_count > 0
                    and b.access_count > 0
                ):
                    shared += 1
            coaccess_feat[i] = shared / max(n - 1, 1)

        # --- 3. Temporal locality ---
        temporal_feat = np.array(
            [item.timestamp for item in items], dtype=np.float64
        )
        now = time.time()
        # Convert to recency: 1.0 = just now, 0.0 = very old
        temporal_feat = np.clip(1.0 - (now - temporal_feat) / 86400.0, 0.0, 1.0)

        # Combine with weights
        combined = np.column_stack([
            self.access_weight * access_feat,
            self.coaccess_weight * coaccess_feat,
            self.temporal_weight * temporal_feat,
        ])
        return combined


# ---------------------------------------------------------------------------
# Cluster labeling
# ---------------------------------------------------------------------------


class ClusterLabelGenerator:
    """Auto-generate descriptive labels for behavioral clusters.

    Labels are built from the most distinctive keywords across cluster
    members, filtered by TF-IDF-like distinctiveness against the corpus
    of all items.
    """

    def __init__(self, max_keywords: int = 5):
        self.max_keywords = max_keywords

    def generate(
        self,
        cluster_id: int,
        cluster_items: list[MemoryItem],
        all_items: list[MemoryItem],
    ) -> ClusterLabel:
        """Generate a descriptive label for a single cluster.

        Args:
            cluster_id: The cluster identifier.
            cluster_items: Items assigned to this cluster.
            all_items: The full set of items (used for distinctiveness).

        Returns:
            A ClusterLabel with auto-generated fields.
        """
        if not cluster_items:
            return ClusterLabel(cluster_id=cluster_id, size=0, is_noise=(cluster_id == -1))

        # Collect words from all cluster content
        cluster_words: Counter[str] = Counter()
        for item in cluster_items:
            words = re.findall(r"\b[a-zA-Z]{4,}\b", item.content.lower())
            cluster_words.update(words)

        # Collect words from all items (corpus)
        corpus_words: Counter[str] = Counter()
        for item in all_items:
            words = re.findall(r"\b[a-zA-Z]{4,}\b", item.content.lower())
            corpus_words.update(words)

        # TF-IDF-like scoring: term frequency in cluster / document frequency in corpus
        keyword_scores: dict[str, float] = {}
        for word, cfreq in cluster_words.items():
            dfreq = corpus_words.get(word, 0)
            tf = cfreq / max(cluster_words.most_common(1)[0][1], 1)
            idf = np.log(len(all_items) / max(dfreq, 1) + 1.0)
            keyword_scores[word] = tf * idf

        top_keywords = sorted(keyword_scores, key=keyword_scores.get, reverse=True)[
            : self.max_keywords
        ]

        # Build a human-readable label
        if top_keywords:
            label = " / ".join(top_keywords[:3])
        elif cluster_id == -1:
            label = "Noise / Unclustered"
        else:
            label = f"Cluster-{cluster_id}"

        avg_imp = float(np.mean([item.importance for item in cluster_items]))

        return ClusterLabel(
            cluster_id=cluster_id,
            label=label,
            top_keywords=top_keywords,
            avg_importance=round(avg_imp, 3),
            size=len(cluster_items),
            is_noise=(cluster_id == -1),
        )


# ---------------------------------------------------------------------------
# Main clustering engine
# ---------------------------------------------------------------------------


class BehavioralClusterEngine:
    """HDBSCAN-based clustering of memory items by behavioral patterns.

    Usage::

        engine = BehavioralClusterEngine()
        result = engine.cluster(items)
        for cid, members in result.clusters.items():
            print(result.labels[cid].label, len(members))
    """

    def __init__(
        self,
        min_cluster_size: int = MIN_CLUSTER_SIZE,
        min_samples: int = MIN_SAMPLES,
        feature_extractor: BehavioralFeatureExtractor | None = None,
        label_generator: ClusterLabelGenerator | None = None,
    ):
        self.min_cluster_size = min_cluster_size
        self.min_samples = min_samples
        self.feature_extractor = feature_extractor or BehavioralFeatureExtractor()
        self.label_generator = label_generator or ClusterLabelGenerator()

    def cluster(self, items: list[MemoryItem]) -> BehavioralClusteringResult:
        """Run HDBSCAN clustering on the behavioral feature vectors.

        Args:
            items: Memory items to cluster.

        Returns:
            A BehavioralClusteringResult with cluster assignments and labels.
        """
        result = BehavioralClusteringResult()

        if len(items) < self.min_cluster_size:
            # Not enough items to form a cluster — everything is noise
            result.noise_items = list(items)
            result.labels[-1] = self.label_generator.generate(-1, items, items)
            return result

        # Build feature matrix
        features = self.feature_extractor.extract(items)
        result.feature_matrix = features

        # Run HDBSCAN
        try:
            import hdbscan

            clusterer = hdbscan.HDBSCAN(
                min_cluster_size=self.min_cluster_size,
                min_samples=self.min_samples,
                metric="euclidean",
                cluster_selection_epsilon=0.0,
            )
            cluster_labels = clusterer.fit_predict(features)
        except ImportError:
            # Fallback: simple threshold-based clustering when hdbscan is
            # not available. This divides items into coarse behavioral groups.
            cluster_labels = self._fallback_clustering(features)

        # Assign items to clusters
        n_clusters_found = len(set(cluster_labels) - {-1})
        result.n_clusters = n_clusters_found

        for idx, cid in enumerate(cluster_labels):
            if cid == -1:
                result.noise_items.append(items[idx])
            else:
                if cid not in result.clusters:
                    result.clusters[cid] = []
                result.clusters[cid].append(items[idx])

        # Ensure noise cluster exists in labels
        if -1 not in result.labels:
            result.labels[-1] = self.label_generator.generate(
                -1, result.noise_items, items
            )

        # Generate labels for each non-noise cluster
        for cid, cluster_items in result.clusters.items():
            result.labels[cid] = self.label_generator.generate(
                cid, cluster_items, items
            )

        # Compute overall silhouette score
        result.silhouette_score = self._silhouette_score(
            features, cluster_labels, result.clusters
        )

        return result

    def _fallback_clustering(
        self, features: np.ndarray
    ) -> np.ndarray:
        """Simple threshold-based fallback when hdbscan is unavailable.

        Clusters by threshold on the access-frequency component.
        """
        n = features.shape[0]
        labels = np.full(n, -1, dtype=np.intp)

        # Single dimension: use access-frequency (column 0, but after
        # weighting it's the first column of the combined matrix).
        access_dim = features[:, 0]
        threshold = float(np.median(access_dim))

        high_freq = np.where(access_dim >= threshold)[0]
        low_freq = np.where(access_dim < threshold)[0]

        if len(high_freq) >= self.min_cluster_size:
            labels[high_freq] = 0
        if len(low_freq) >= self.min_cluster_size:
            labels[low_freq] = 1

        return labels

    @staticmethod
    def _silhouette_score(
        features: np.ndarray,
        labels: np.ndarray,
        clusters: dict[int, list],
    ) -> float:
        """Compute a simple silhouette-like score for validation.

        Falls back to 0.0 if clustering produced no structure.
        """
        if len(clusters) < 2 or features.shape[0] < 3:
            return 0.0

        from sklearn.metrics import silhouette_score as sklearn_silhouette

        try:
            return float(sklearn_silhouette(features, labels))
        except Exception:
            return 0.0


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------


def cluster_memory_items(
    items: list[MemoryItem],
    min_cluster_size: int = MIN_CLUSTER_SIZE,
) -> dict[int, list[MemoryItem]]:
    """One-shot convenience wrapper: cluster items and return their groups.

    Args:
        items: Memory items to cluster.
        min_cluster_size: Minimum items for a valid cluster.

    Returns:
        Dict mapping cluster_id to list of MemoryItems.
    """
    engine = BehavioralClusterEngine(min_cluster_size=min_cluster_size)
    result = engine.cluster(items)
    # Merge noise items under key -1 for the caller
    groups: dict[int, list[MemoryItem]] = dict(result.clusters)
    if result.noise_items:
        groups[-1] = groups.get(-1, []) + result.noise_items
    return groups
