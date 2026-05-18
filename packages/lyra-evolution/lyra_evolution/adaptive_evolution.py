"""
Lyra Adaptive Mutation Engine: Dynamic Mutation Rates

Implements adaptive mutation rates that adjust based on evolution progress
to escape local optima and reduce plateau generations.

Phase: 1 - Speed Breakthrough
Task: T104 - Adaptive Mutation Rates
Target: 50% fewer plateau generations, automatic escape from local optima
"""

from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from lyra_evolution.fast_evolution import FastEvolutionEngine


@dataclass
class EvolutionState:
    """
    Tracks evolution state for adaptive mutation.

    Monitors progress, plateaus, and improvement trends.
    """
    generation: int = 0
    best_score: float = 0.0
    best_score_generation: int = 0
    plateau_count: int = 0
    improvement_history: List[float] = field(default_factory=list)
    mutation_rate_history: List[float] = field(default_factory=list)

    def update(self, current_best: float):
        """
        Update state with current best score.

        Args:
            current_best: Current generation's best score
        """
        self.generation += 1

        # Calculate improvement
        improvement = current_best - self.best_score

        # Update best score if improved
        if improvement > 0.001:  # Threshold for meaningful improvement
            self.best_score = current_best
            self.best_score_generation = self.generation
            self.plateau_count = 0
        else:
            # No improvement - increment plateau counter
            self.plateau_count += 1

        # Track improvement history (last 10 generations)
        self.improvement_history.append(improvement)
        if len(self.improvement_history) > 10:
            self.improvement_history.pop(0)

    def is_plateaued(self, threshold: int = 3) -> bool:
        """
        Check if evolution is plateaued.

        Args:
            threshold: Number of generations without improvement

        Returns:
            True if plateaued
        """
        return self.plateau_count >= threshold

    def is_severely_plateaued(self, threshold: int = 5) -> bool:
        """
        Check if evolution is severely plateaued.

        Args:
            threshold: Number of generations for severe plateau

        Returns:
            True if severely plateaued
        """
        return self.plateau_count >= threshold

    def recent_improvement_rate(self) -> float:
        """
        Calculate recent improvement rate.

        Returns:
            Average improvement over recent generations
        """
        if not self.improvement_history:
            return 0.0

        return sum(self.improvement_history) / len(self.improvement_history)


class AdaptiveMutationEngine:
    """
    Adaptive mutation rate controller.

    Adjusts mutation rates based on evolution progress:
    - Low rate when improving (exploit)
    - Medium rate when slight plateau (explore)
    - High rate when severe plateau (escape)
    """

    def __init__(
        self,
        base_rate: float = 0.1,
        min_rate: float = 0.05,
        max_rate: float = 0.5
    ):
        """
        Initialize adaptive mutation engine.

        Args:
            base_rate: Default mutation rate
            min_rate: Minimum mutation rate (when improving)
            max_rate: Maximum mutation rate (when severely plateaued)
        """
        self.base_rate = base_rate
        self.min_rate = min_rate
        self.max_rate = max_rate

        # Evolution state
        self.state = EvolutionState()

        # Statistics
        self.rate_changes: List[Dict[str, Any]] = []

    def get_mutation_rate(self, current_best: float) -> float:
        """
        Get adaptive mutation rate based on current state.

        Args:
            current_best: Current generation's best score

        Returns:
            Adaptive mutation rate
        """
        # Update state
        self.state.update(current_best)

        # Determine mutation rate based on plateau status
        if self.state.is_severely_plateaued(threshold=5):
            # Severe plateau - high mutation to escape
            rate = self.max_rate
            reason = "severe_plateau"

        elif self.state.is_plateaued(threshold=3):
            # Moderate plateau - medium mutation to explore
            rate = (self.base_rate + self.max_rate) / 2
            reason = "moderate_plateau"

        elif self.state.recent_improvement_rate() > 0.01:
            # Good improvement - low mutation to exploit
            rate = self.min_rate
            reason = "improving"

        else:
            # Default - base mutation rate
            rate = self.base_rate
            reason = "default"

        # Record rate change
        self.state.mutation_rate_history.append(rate)
        self.rate_changes.append({
            "generation": self.state.generation,
            "rate": rate,
            "reason": reason,
            "plateau_count": self.state.plateau_count,
            "best_score": self.state.best_score
        })

        return rate

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get adaptive mutation statistics.

        Returns:
            Statistics dictionary
        """
        return {
            "generation": self.state.generation,
            "best_score": self.state.best_score,
            "plateau_count": self.state.plateau_count,
            "current_rate": self.state.mutation_rate_history[-1] if self.state.mutation_rate_history else self.base_rate,
            "rate_changes": len(self.rate_changes),
            "avg_rate": sum(self.state.mutation_rate_history) / len(self.state.mutation_rate_history) if self.state.mutation_rate_history else self.base_rate,
            "plateau_escapes": sum(1 for change in self.rate_changes if change["reason"] == "severe_plateau")
        }


class AdaptiveEvolutionEngine(FastEvolutionEngine):
    """
    Evolution engine with adaptive mutation rates.

    Extends FastEvolutionEngine with automatic mutation rate adjustment
    based on evolution progress.
    """

    def __init__(
        self,
        n_workers: int = 10,
        cache_size: int = 10000,
        base_mutation_rate: float = 0.1
    ):
        """
        Initialize adaptive evolution engine.

        Args:
            n_workers: Number of parallel workers
            cache_size: Maximum cache entries
            base_mutation_rate: Base mutation rate
        """
        super().__init__(n_workers=n_workers, cache_size=cache_size)

        # Adaptive mutation controller
        self.adaptive_mutation = AdaptiveMutationEngine(base_rate=base_mutation_rate)

        # Track plateau statistics
        self.plateau_generations = 0
        self.total_generations = 0
        self.escapes = 0

    def explore_generation_adaptive(
        self,
        n_mutations: int = 10,
        mutation_types: Optional[List[str]] = None
    ) -> List[Tuple[str, float]]:
        """
        Explore generation with adaptive mutation rate.

        Args:
            n_mutations: Number of mutations per frontier node
            mutation_types: Types of mutations to apply

        Returns:
            List of (node_id, score) for new nodes
        """
        # Get current best score
        current_best = max(
            (n.immediate_score for n in self.nodes.values() if n.evaluated),
            default=0.0
        )

        # Get adaptive mutation rate
        mutation_rate = self.adaptive_mutation.get_mutation_rate(current_best)

        # Track plateau statistics
        self.total_generations += 1
        if self.adaptive_mutation.state.is_plateaued():
            self.plateau_generations += 1

        # Track escapes (when rate increases significantly)
        if len(self.adaptive_mutation.state.mutation_rate_history) >= 2:
            prev_rate = self.adaptive_mutation.state.mutation_rate_history[-2]
            if mutation_rate > prev_rate * 1.5:
                self.escapes += 1

        # Generate mutations with adaptive rate
        import random
        import copy

        mutations = []
        if mutation_types is None:
            mutation_types = ["add_skill", "remove_skill", "swap_skill"]

        for node_id in self.frontier:
            node = self.nodes[node_id]
            for _ in range(n_mutations):
                # Apply mutation with adaptive probability
                if random.random() < mutation_rate:
                    mutation_type = random.choice(mutation_types)
                    mutated_config = self.mutator.mutate_incremental(
                        node.config,
                        mutation_type
                    )
                    mutations.append((node_id, mutated_config))
                else:
                    # No mutation - use original config
                    mutations.append((node_id, copy.deepcopy(node.config)))

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

        return new_nodes

    def get_adaptive_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive adaptive evolution statistics.

        Returns:
            Statistics including adaptive mutation metrics
        """
        stats = self.get_performance_statistics()

        # Add adaptive mutation stats
        stats["adaptive_mutation"] = self.adaptive_mutation.get_statistics()

        # Add plateau statistics
        plateau_rate = self.plateau_generations / self.total_generations if self.total_generations > 0 else 0.0
        stats["plateau_statistics"] = {
            "plateau_generations": self.plateau_generations,
            "total_generations": self.total_generations,
            "plateau_rate": plateau_rate,
            "escapes": self.escapes
        }

        return stats

    def plateau_reduction_percentage(self, baseline_rate: float = 0.5) -> float:
        """
        Calculate plateau reduction vs baseline.

        Args:
            baseline_rate: Expected plateau rate without adaptation

        Returns:
            Percentage reduction in plateau generations
        """
        if self.total_generations == 0:
            return 0.0

        actual_rate = self.plateau_generations / self.total_generations
        reduction = (baseline_rate - actual_rate) / baseline_rate * 100

        return max(0.0, reduction)


# Example usage
if __name__ == "__main__":
    print("🧬 Adaptive Mutation Engine - Automatic Plateau Escape")
    print("=" * 60)

    # Create adaptive evolution engine
    engine = AdaptiveEvolutionEngine(n_workers=4, cache_size=5000)

    # Initialize with baseline
    baseline = {
        "skills": ["skill1", "skill2", "skill3"]
    }

    root_id = engine.initialize(baseline)
    print(f"✅ Initialized with root: {root_id}")

    # Run adaptive evolution for 20 generations
    print("\n🔄 Running 20 generations with adaptive mutation...")

    for gen in range(20):
        new_nodes = engine.explore_generation_adaptive(n_mutations=15)

        stats = engine.get_adaptive_statistics()
        adaptive_stats = stats["adaptive_mutation"]

        print(f"  Gen {gen + 1}: {len(new_nodes)} nodes, "
              f"rate: {adaptive_stats['current_rate']:.2f}, "
              f"plateau: {adaptive_stats['plateau_count']}, "
              f"best: {adaptive_stats['best_score']:.3f}")

    # Final statistics
    print(f"\n📊 Final Statistics:")
    stats = engine.get_adaptive_statistics()
    adaptive_stats = stats["adaptive_mutation"]
    plateau_stats = stats["plateau_statistics"]

    print(f"   Total generations: {stats['generations_explored']}")
    print(f"   Best score: {stats['best_score']:.3f}")
    print(f"   Plateau generations: {plateau_stats['plateau_generations']}")
    print(f"   Plateau rate: {plateau_stats['plateau_rate']:.1%}")
    print(f"   Escapes: {plateau_stats['escapes']}")
    print(f"   Avg mutation rate: {adaptive_stats['avg_rate']:.2f}")

    # Calculate plateau reduction
    reduction = engine.plateau_reduction_percentage(baseline_rate=0.5)
    print(f"\n🎯 Plateau Reduction: {reduction:.1f}%")

    if reduction >= 50:
        print("✅ Target achieved: 50%+ plateau reduction!")
    else:
        print(f"⚠️  Target not yet achieved, current: {reduction:.1f}%")
