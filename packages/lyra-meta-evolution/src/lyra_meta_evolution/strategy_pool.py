"""Strategy Pool — Strategy library for evolution with encoding, similarity,
diversity, performance tracking, lineage, and novelty search.

Manages a pool of strategies that the genetic optimizer draws from,
providing encoding, similarity metrics, performance tracking, and
exploration through novelty search.
"""

from __future__ import annotations

import hashlib
import logging
import math
import random
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Optional, Sequence

from .meta_evolution import AgentGenome

logger = logging.getLogger(__name__)


# ── Exceptions ──────────────────────────────────────────────────────────────────


class StrategyPoolError(Exception):
    """Base exception for strategy pool errors."""


class StrategyNotFoundError(StrategyPoolError):
    """Raised when a requested strategy is not in the pool."""


class PoolCapacityError(StrategyPoolError):
    """Raised when the strategy pool is at capacity."""


# ── Strategy Encoding ───────────────────────────────────────────────────────────


@dataclass
class StrategyEncoding:
    """Encoded representation of a strategy for comparison and storage."""

    strategy_id: str
    signature: str  # Hash-based compact representation
    feature_vector: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_genome(cls, genome: AgentGenome) -> StrategyEncoding:
        """Encode a genome into a strategy representation."""
        features: list[float] = []

        # Encode hyperparameters as feature vector
        hp_keys = sorted(genome.hyperparameters.keys())
        for key in hp_keys:
            features.append(genome.hyperparameters.get(key, 0.0))

        # Encode strategy weights
        sw_keys = sorted(genome.strategy_weights.keys())
        for key in sw_keys:
            features.append(genome.strategy_weights.get(key, 0.0))

        # Encode objective weights
        obj_keys = sorted(genome.objective_weights.keys())
        for key in obj_keys:
            features.append(genome.objective_weights.get(key, 0.0))

        # Generate signature
        raw = "|".join(f"{v:.6f}" for v in features)
        signature = hashlib.sha256(raw.encode()).hexdigest()[:16]

        return cls(
            strategy_id=genome.agent_id,
            signature=signature,
            feature_vector=features,
            metadata={
                "generation": genome.generation,
                "active_strategies": genome.active_strategies,
                "parent_ids": genome.parent_ids,
            },
        )


# ── Strategy Record ─────────────────────────────────────────────────────────────


@dataclass
class StrategyRecord:
    """Full tracking record for a strategy in the pool."""

    strategy_id: str
    encoding: StrategyEncoding
    fitness: float = 0.0
    fitness_history: list[float] = field(default_factory=list)
    usage_count: int = 0
    success_count: int = 0
    created_at: float = field(default_factory=time.time)
    last_used_at: float = field(default_factory=time.time)
    parent_ids: list[str] = field(default_factory=list)
    children_ids: list[str] = field(default_factory=list)
    tags: set[str] = field(default_factory=set)
    lineage_depth: int = 0
    archived: bool = False

    @property
    def success_rate(self) -> float:
        if self.usage_count == 0:
            return 0.0
        return self.success_count / self.usage_count

    @property
    def avg_fitness(self) -> float:
        if not self.fitness_history:
            return self.fitness
        return sum(self.fitness_history) / len(self.fitness_history)

    def record_result(self, fitness: float, success: bool) -> None:
        """Record a usage outcome."""
        self.fitness = fitness
        self.fitness_history.append(fitness)
        self.usage_count += 1
        if success:
            self.success_count += 1
        self.last_used_at = time.time()


# ── Similarity Metrics ──────────────────────────────────────────────────────────


class SimilarityMetrics:
    """Compute similarity and distance between strategy encodings."""

    @staticmethod
    def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
        """Cosine similarity between two feature vectors."""
        if not vec1 or not vec2:
            return 0.0

        # Pad shorter vector
        max_len = max(len(vec1), len(vec2))
        v1 = vec1 + [0.0] * (max_len - len(vec1))
        v2 = vec2 + [0.0] * (max_len - len(vec2))

        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot / (norm1 * norm2)

    @staticmethod
    def euclidean_distance(vec1: list[float], vec2: list[float]) -> float:
        """Euclidean distance between two feature vectors."""
        if not vec1 or not vec2:
            return float("inf")

        max_len = max(len(vec1), len(vec2))
        v1 = vec1 + [0.0] * (max_len - len(vec1))
        v2 = vec2 + [0.0] * (max_len - len(vec2))

        return math.sqrt(sum((a - b) ** 2 for a, b in zip(v1, v2)))

    @staticmethod
    def jaccard_signature(sig1: str, sig2: str) -> float:
        """Jaccard similarity of strategy signatures."""
        s1 = set(sig1[i:i + 2] for i in range(0, len(sig1), 2))
        s2 = set(sig2[i:i + 2] for i in range(0, len(sig2), 2))
        intersection = len(s1 & s2)
        union = len(s1 | s2)
        return intersection / union if union > 0 else 0.0


# ── Strategy Pool ───────────────────────────────────────────────────────────────


class StrategyPool:
    """Pool of strategies with encoding, similarity, and lineage tracking.

    Manages a library of strategy encodings for the evolution system,
    supporting similarity queries, diversity measurement, novelty search,
    and performance-based ranking.

    Usage::

        pool = StrategyPool(max_size=1000)
        encoding = StrategyEncoding.from_genome(genome)
        pool.add_strategy(encoding)

        # Find similar strategies
        similar = pool.find_similar(encoding, top_k=5)

        # Compute diversity
        diversity = pool.compute_diversity()

        # Search for novel strategies
        novel = pool.novelty_search(population_encodings, k=3)
    """

    def __init__(self, max_size: int = 1000):
        self._max_size = max_size
        self._strategies: dict[str, StrategyRecord] = {}
        self._encodings: dict[str, StrategyEncoding] = {}
        self._lineage: dict[str, list[str]] = defaultdict(list)  # parent -> [children]
        self._metrics = SimilarityMetrics()
        self._tag_index: dict[str, set[str]] = defaultdict(set)

        self._add_count: int = 0
        self._prune_count: int = 0

    def add_strategy(
        self,
        encoding: StrategyEncoding,
        fitness: float = 0.0,
        tags: Optional[set[str]] = None,
        parent_ids: Optional[list[str]] = None,
    ) -> StrategyRecord:
        """Add a strategy encoding to the pool."""
        if len(self._strategies) >= self._max_size:
            self._prune_lowest_fitness()

        record = StrategyRecord(
            strategy_id=encoding.strategy_id,
            encoding=encoding,
            fitness=fitness,
            parent_ids=parent_ids or encoding.metadata.get("parent_ids", []),
            tags=tags or set(),
        )

        # Update lineage
        for parent_id in record.parent_ids:
            self._lineage[parent_id].append(encoding.strategy_id)
            if parent_id in self._strategies:
                self._strategies[parent_id].children_ids.append(encoding.strategy_id)
                record.lineage_depth = self._strategies[parent_id].lineage_depth + 1

        # Update tag index
        for tag in record.tags:
            self._tag_index[tag].add(encoding.strategy_id)

        self._strategies[encoding.strategy_id] = record
        self._encodings[encoding.strategy_id] = encoding
        self._add_count += 1

        logger.debug("Added strategy %s to pool (size=%d)", encoding.strategy_id, len(self._strategies))
        return record

    def get_strategy(self, strategy_id: str) -> StrategyRecord:
        """Retrieve a strategy by ID."""
        record = self._strategies.get(strategy_id)
        if record is None:
            raise StrategyNotFoundError(f"Strategy '{strategy_id}' not in pool")
        return record

    def record_result(
        self,
        strategy_id: str,
        fitness: float,
        success: bool,
    ) -> None:
        """Record an evaluation result for a strategy."""
        record = self.get_strategy(strategy_id)
        record.record_result(fitness, success)

    def find_similar(
        self,
        query: StrategyEncoding,
        top_k: int = 5,
        threshold: float = 0.7,
    ) -> list[tuple[StrategyRecord, float]]:
        """Find strategies similar to the query encoding."""
        results: list[tuple[StrategyRecord, float]] = []

        for sid, encoding in self._encodings.items():
            if sid == query.strategy_id:
                continue

            similarity = self._metrics.cosine_similarity(
                query.feature_vector,
                encoding.feature_vector,
            )

            if similarity >= threshold:
                record = self._strategies[sid]
                results.append((record, similarity))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def compute_diversity(self) -> float:
        """Compute overall diversity of the strategy pool.

        Returns a value between 0.0 (homogeneous) and 1.0 (diverse).
        """
        if len(self._encodings) < 2:
            return 1.0

        encodings = list(self._encodings.values())
        total_dist = 0.0
        comparisons = 0

        # Use a sampled approach for large pools
        sample_size = min(len(encodings), 100)
        sampled = encodings if len(encodings) <= sample_size else random.sample(encodings, sample_size)

        for i in range(len(sampled)):
            for j in range(i + 1, len(sampled)):
                dist = self._metrics.cosine_similarity(
                    sampled[i].feature_vector,
                    sampled[j].feature_vector,
                )
                total_dist += 1.0 - dist  # Convert similarity to distance
                comparisons += 1

        avg_distance = total_dist / max(comparisons, 1)
        return min(avg_distance, 1.0)

    def novelty_search(
        self,
        population: list[StrategyEncoding],
        k: int = 3,
    ) -> list[StrategyEncoding]:
        """Find the most novel strategies in a population.

        Novelty is measured by average distance to k-nearest neighbors
        in the existing pool.
        """
        if not self._encodings:
            return list(population[:k])

        pool_encodings = list(self._encodings.values())
        scores: list[tuple[StrategyEncoding, float]] = []

        for candidate in population:
            # Compute distances to all pool members
            distances = [
                self._metrics.euclidean_distance(
                    candidate.feature_vector,
                    pool_enc.feature_vector,
                )
                for pool_enc in pool_encodings
            ]

            # Novelty = average distance to k nearest neighbors
            distances.sort()
            k_nearest = distances[:min(k, len(distances))]
            novelty = sum(k_nearest) / max(len(k_nearest), 1)
            scores.append((candidate, novelty))

        # Return most novel (highest average distance)
        scores.sort(key=lambda x: x[1], reverse=True)
        return [enc for enc, _ in scores[:k]]

    def get_lineage(self, strategy_id: str, depth: int = 5) -> dict[str, Any]:
        """Trace the lineage of a strategy (ancestors and descendants)."""
        record = self._strategies.get(strategy_id)
        if record is None:
            return {"strategy_id": strategy_id, "error": "not found"}

        # Trace ancestors
        ancestors: list[str] = []
        to_visit = list(record.parent_ids)
        visited: set[str] = set()
        current_depth = 0
        while to_visit and current_depth < depth:
            next_visit: list[str] = []
            for pid in to_visit:
                if pid in visited:
                    continue
                visited.add(pid)
                ancestors.append(pid)
                if pid in self._strategies:
                    next_visit.extend(self._strategies[pid].parent_ids)
            to_visit = next_visit
            current_depth += 1

        # Trace descendants
        descendants: list[str] = []
        to_visit = list(record.children_ids)
        visited = set()
        current_depth = 0
        while to_visit and current_depth < depth:
            next_visit: list[str] = []
            for cid in to_visit:
                if cid in visited:
                    continue
                visited.add(cid)
                descendants.append(cid)
                if cid in self._strategies:
                    next_visit.extend(self._strategies[cid].children_ids)
            to_visit = next_visit
            current_depth += 1

        return {
            "strategy_id": strategy_id,
            "depth": record.lineage_depth,
            "parent_ids": record.parent_ids,
            "ancestors": ancestors,
            "children_ids": record.children_ids,
            "descendants": descendants,
            "total_ancestors": len(ancestors),
            "total_descendants": len(descendants),
        }

    def get_top_strategies(
        self,
        top_k: int = 10,
        min_usage: int = 1,
    ) -> list[StrategyRecord]:
        """Get the top-performing strategies."""
        candidates = [
            r for r in self._strategies.values()
            if r.usage_count >= min_usage and not r.archived
        ]
        candidates.sort(key=lambda r: r.avg_fitness, reverse=True)
        return candidates[:top_k]

    def by_tag(self, tag: str) -> list[StrategyRecord]:
        """Get all strategies with a specific tag."""
        ids = self._tag_index.get(tag, set())
        return [self._strategies[sid] for sid in ids if sid in self._strategies]

    def archive_strategy(self, strategy_id: str) -> None:
        """Archive a strategy (soft-delete from active pool)."""
        record = self.get_strategy(strategy_id)
        record.archived = True

    def unarchive_strategy(self, strategy_id: str) -> None:
        """Restore an archived strategy."""
        record = self.get_strategy(strategy_id)
        record.archived = False

    # ── Internal ─────────────────────────────────────────────────────────────

    def _prune_lowest_fitness(self) -> None:
        """Remove the lowest-fitness strategies to make room."""
        if not self._strategies:
            return

        # Sort by fitness, keep top 80%
        keep_count = int(self._max_size * 0.8)
        sorted_records = sorted(
            self._strategies.values(),
            key=lambda r: r.avg_fitness,
            reverse=True,
        )

        to_remove = sorted_records[keep_count:]
        for record in to_remove:
            sid = record.strategy_id
            self._strategies.pop(sid, None)
            self._encodings.pop(sid, None)
            for tag in record.tags:
                self._tag_index[tag].discard(sid)

        self._prune_count += len(to_remove)
        logger.info("Pruned %d low-fitness strategies from pool", len(to_remove))

    # ── Serialization ────────────────────────────────────────────────────────

    def export_pool(self) -> dict[str, Any]:
        """Export pool state for persistence."""
        return {
            "strategies": {
                sid: {
                    "fitness": r.fitness,
                    "fitness_history": r.fitness_history[-100:],
                    "usage_count": r.usage_count,
                    "success_count": r.success_count,
                    "tags": list(r.tags),
                    "parent_ids": r.parent_ids,
                    "lineage_depth": r.lineage_depth,
                    "archived": r.archived,
                    "encoding": {
                        "signature": r.encoding.signature,
                        "feature_vector": r.encoding.feature_vector,
                        "metadata": r.encoding.metadata,
                    },
                }
                for sid, r in self._strategies.items()
            },
            "stats": {
                "total_added": self._add_count,
                "total_pruned": self._prune_count,
                "current_size": len(self._strategies),
            },
        }

    # ── Properties ───────────────────────────────────────────────────────────

    @property
    def size(self) -> int:
        return len(self._strategies)

    @property
    def active_size(self) -> int:
        return sum(1 for r in self._strategies.values() if not r.archived)

    @property
    def avg_fitness(self) -> float:
        if not self._strategies:
            return 0.0
        return sum(r.avg_fitness for r in self._strategies.values()) / len(self._strategies)


