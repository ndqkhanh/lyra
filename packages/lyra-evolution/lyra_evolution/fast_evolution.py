"""
Lyra Fast Evolution Engine: 10-Minute Evolution Cycles

Implements cached evaluations, incremental mutations, and optimized
parallel evaluation to achieve <10 minute evolution cycles.

Phase: 1 - Speed Breakthrough
Task: T103 - 10-Minute Evolution Cycles
Target: 80% cache hit rate, <10 min cycles, maintain quality
"""

from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime
import json
import hashlib
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from lyra_evolution.parallel_exploration import ParallelExplorationEngine


@dataclass
class CacheEntry:
    """
    Cached evaluation result.

    Tracks config hash, score, and metadata for cache hit analysis.
    """
    config_hash: str
    config: Dict[str, Any]
    score: float
    timestamp: str
    hit_count: int = 0


class EvaluationCache:
    """
    Evaluation cache with LRU eviction.

    Caches evaluation results to avoid redundant computation.
    Target: 80% cache hit rate.
    """

    def __init__(self, max_size: int = 10000):
        """
        Initialize evaluation cache.

        Args:
            max_size: Maximum cache entries (default 10K)
        """
        self.max_size = max_size
        self.cache: Dict[str, CacheEntry] = {}

        # Statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    def get(self, config: Dict[str, Any]) -> Optional[float]:
        """
        Get cached evaluation result.

        Args:
            config: Agent configuration

        Returns:
            Cached score if found, None otherwise
        """
        config_hash = self._hash_config(config)

        if config_hash in self.cache:
            entry = self.cache[config_hash]
            entry.hit_count += 1
            self.hits += 1
            return entry.score

        self.misses += 1
        return None

    def put(self, config: Dict[str, Any], score: float):
        """
        Cache evaluation result.

        Args:
            config: Agent configuration
            score: Evaluation score
        """
        config_hash = self._hash_config(config)

        # Evict if at capacity (LRU)
        if len(self.cache) >= self.max_size and config_hash not in self.cache:
            self._evict_lru()

        entry = CacheEntry(
            config_hash=config_hash,
            config=config,
            score=score,
            timestamp=datetime.now().isoformat()
        )

        self.cache[config_hash] = entry

    def _evict_lru(self):
        """Evict least recently used entry."""
        if not self.cache:
            return

        # Find entry with lowest hit count
        lru_hash = min(self.cache.keys(), key=lambda h: self.cache[h].hit_count)
        del self.cache[lru_hash]
        self.evictions += 1

    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def get_statistics(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "hit_rate": self.hit_rate()
        }

    @staticmethod
    def _hash_config(config: Dict[str, Any]) -> str:
        """Generate hash for configuration."""
        content = json.dumps(config, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()


class IncrementalMutator:
    """
    Incremental mutation engine.

    Generates small, targeted mutations instead of random changes.
    Improves cache hit rate by creating similar configs.
    """

    def __init__(self):
        """Initialize incremental mutator."""
        self.mutation_history: List[Dict[str, Any]] = []

    def mutate_incremental(
        self,
        config: Dict[str, Any],
        mutation_type: str = "add_skill"
    ) -> Dict[str, Any]:
        """
        Apply incremental mutation.

        Args:
            config: Original configuration
            mutation_type: Type of mutation (add_skill, remove_skill, swap_skill)

        Returns:
            Mutated configuration
        """
        import copy
        import random

        mutated = copy.deepcopy(config)
        skills = mutated.get("skills", [])

        if mutation_type == "add_skill" or not skills:
            # Add one new skill
            new_skill = f"skill_{random.randint(1, 100)}"
            if new_skill not in skills:
                skills.append(new_skill)

        elif mutation_type == "remove_skill" and skills:
            # Remove one skill
            skills.pop(random.randint(0, len(skills) - 1))

        elif mutation_type == "swap_skill" and skills:
            # Replace one skill
            idx = random.randint(0, len(skills) - 1)
            new_skill = f"skill_{random.randint(1, 100)}"
            skills[idx] = new_skill

        mutated["skills"] = skills

        # Record mutation
        self.mutation_history.append({
            "type": mutation_type,
            "timestamp": datetime.now().isoformat(),
            "from_hash": EvaluationCache._hash_config(config),
            "to_hash": EvaluationCache._hash_config(mutated)
        })

        return mutated

    def get_statistics(self) -> Dict[str, Any]:
        """Get mutation statistics."""
        return {
            "total_mutations": len(self.mutation_history),
            "mutation_types": self._count_mutation_types()
        }

    def _count_mutation_types(self) -> Dict[str, int]:
        """Count mutations by type."""
        counts: Dict[str, int] = {}
        for mutation in self.mutation_history:
            mut_type = mutation["type"]
            counts[mut_type] = counts.get(mut_type, 0) + 1
        return counts


class FastEvolutionEngine(ParallelExplorationEngine):
    """
    Fast evolution engine with caching and optimization.

    Extends ParallelExplorationEngine with:
    - Evaluation caching (80% hit rate target)
    - Incremental mutations (better cache locality)
    - Optimized parallel evaluation
    - Hot path optimization

    Target: <10 minute evolution cycles
    """

    def __init__(self, n_workers: int = 10, cache_size: int = 10000):
        """
        Initialize fast evolution engine.

        Args:
            n_workers: Number of parallel workers
            cache_size: Maximum cache entries
        """
        super().__init__(n_workers=n_workers)

        # Caching
        self.cache = EvaluationCache(max_size=cache_size)

        # Incremental mutations
        self.mutator = IncrementalMutator()

        # Performance tracking
        self.cycle_times: List[float] = []
        self.cache_hit_rates: List[float] = []

    def explore_generation_fast(
        self,
        n_mutations: int = 10,
        mutation_types: Optional[List[str]] = None
    ) -> List[Tuple[str, float]]:
        """
        Fast generation exploration with caching.

        Args:
            n_mutations: Number of mutations per frontier node
            mutation_types: Types of mutations to apply

        Returns:
            List of (node_id, score) for new nodes
        """
        start_time = time.time()

        if mutation_types is None:
            mutation_types = ["add_skill", "remove_skill", "swap_skill"]

        # Generate incremental mutations from frontier
        mutations = []
        for node_id in self.frontier:
            node = self.nodes[node_id]
            for _ in range(n_mutations):
                import random
                mutation_type = random.choice(mutation_types)
                mutated_config = self.mutator.mutate_incremental(
                    node.config,
                    mutation_type
                )
                mutations.append((node_id, mutated_config))

        # Evaluate with caching
        results = self._evaluate_parallel_cached(mutations)

        # Add to tree
        new_nodes = []
        for (parent_id, config), score in results:
            node_id = self._add_node(parent_id, config, score)
            new_nodes.append((node_id, score))

        # Update frontier and metaproductivity
        self._update_frontier()
        self._update_metaproductivity()
        self._update_clade_diversity()
        self._record_generation_snapshot()

        self.generations_explored += 1

        # Track performance
        cycle_time = time.time() - start_time
        self.cycle_times.append(cycle_time)
        self.cache_hit_rates.append(self.cache.hit_rate())

        return new_nodes

    def _evaluate_parallel_cached(
        self,
        mutations: List[Tuple[str, Dict[str, Any]]]
    ) -> List[Tuple[Tuple[str, Dict[str, Any]], float]]:
        """
        Evaluate mutations in parallel with caching.

        Args:
            mutations: List of (parent_id, config) tuples

        Returns:
            List of ((parent_id, config), score) tuples
        """
        results = []
        to_evaluate = []

        # Check cache first
        for parent_id, config in mutations:
            cached_score = self.cache.get(config)
            if cached_score is not None:
                # Cache hit
                results.append(((parent_id, config), cached_score))
            else:
                # Cache miss - need to evaluate
                to_evaluate.append((parent_id, config))

        # Evaluate cache misses in parallel
        if to_evaluate:
            with ThreadPoolExecutor(max_workers=self.n_workers) as executor:
                future_to_mutation = {
                    executor.submit(self._evaluate_config, config): (parent_id, config)
                    for parent_id, config in to_evaluate
                }

                for future in as_completed(future_to_mutation):
                    parent_id, config = future_to_mutation[future]
                    try:
                        score = future.result()

                        # Cache result
                        self.cache.put(config, score)

                        results.append(((parent_id, config), score))
                        self.total_evaluations += 1
                    except Exception as e:
                        print(f"Evaluation failed: {e}")

        return results

    def get_performance_statistics(self) -> Dict[str, Any]:
        """
        Get performance statistics.

        Returns:
            Performance metrics including cycle times and cache stats
        """
        stats = self.get_statistics()

        # Add performance metrics
        stats["cache"] = self.cache.get_statistics()
        stats["mutations"] = self.mutator.get_statistics()

        if self.cycle_times:
            stats["cycle_times"] = {
                "avg": sum(self.cycle_times) / len(self.cycle_times),
                "min": min(self.cycle_times),
                "max": max(self.cycle_times),
                "latest": self.cycle_times[-1]
            }

        if self.cache_hit_rates:
            stats["cache_hit_rates"] = {
                "avg": sum(self.cache_hit_rates) / len(self.cache_hit_rates),
                "latest": self.cache_hit_rates[-1]
            }

        return stats

    def estimate_cycle_time(self, n_generations: int = 10) -> float:
        """
        Estimate time for N generations.

        Args:
            n_generations: Number of generations

        Returns:
            Estimated time in seconds
        """
        if not self.cycle_times:
            return 0.0

        avg_cycle_time = sum(self.cycle_times) / len(self.cycle_times)
        return avg_cycle_time * n_generations


# Example usage
if __name__ == "__main__":
    print("🚀 Fast Evolution Engine - 10-Minute Cycles")
    print("=" * 60)

    # Create fast evolution engine
    engine = FastEvolutionEngine(n_workers=10, cache_size=10000)

    # Initialize with baseline
    baseline = {
        "skills": ["skill1", "skill2", "skill3"]
    }

    root_id = engine.initialize(baseline)
    print(f"✅ Initialized with root: {root_id}")

    # Run fast evolution for 10 generations
    print("\n🔄 Running 10 generations with caching...")
    start_time = time.time()

    for gen in range(10):
        new_nodes = engine.explore_generation_fast(n_mutations=20)

        stats = engine.get_performance_statistics()
        cache_stats = stats["cache"]

        print(f"  Gen {gen + 1}: {len(new_nodes)} nodes, "
              f"cache hit rate: {cache_stats['hit_rate']:.1%}, "
              f"cycle time: {engine.cycle_times[-1]:.2f}s")

    total_time = time.time() - start_time

    # Final statistics
    print(f"\n📊 Final Statistics:")
    stats = engine.get_performance_statistics()

    print(f"   Total time: {total_time:.2f}s ({total_time/60:.2f} min)")
    print(f"   Avg cycle time: {stats['cycle_times']['avg']:.2f}s")
    print(f"   Cache hit rate: {stats['cache']['hit_rate']:.1%}")
    print(f"   Cache size: {stats['cache']['size']}/{stats['cache']['max_size']}")
    print(f"   Total evaluations: {stats['total_evaluations']}")
    print(f"   Total nodes: {stats['total_nodes']}")
    print(f"   Best score: {stats['best_score']:.3f}")
    print(f"   Best metaproductivity: {stats['best_metaproductivity']:.3f}")

    # Estimate time for 100 generations
    estimated_100 = engine.estimate_cycle_time(100)
    print(f"\n⏱️  Estimated time for 100 generations: {estimated_100:.2f}s ({estimated_100/60:.2f} min)")

    if estimated_100 < 600:  # 10 minutes
        print("✅ Target achieved: <10 minute cycles!")
    else:
        print("⚠️  Target not yet achieved, needs optimization")
