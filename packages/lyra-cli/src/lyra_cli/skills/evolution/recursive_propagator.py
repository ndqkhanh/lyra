"""Recursive Propagator - Multi-generational skill improvement through recursive application.

Applies improvement operators recursively across generations, tracking
which mutations produce fitness gains and propagating beneficial changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class PropagationStrategy(StrEnum):
    """Strategy for propagating improvements across generations."""

    BREADTH_FIRST = "breadth_first"
    DEPTH_FIRST = "depth_first"
    FITNESS_GUIDED = "fitness_guided"
    DIVERSITY_GUIDED = "diversity_guided"


@dataclass(frozen=True)
class PropagationResult:
    """Result of a recursive propagation operation."""

    original_skill: str
    total_generations: int
    total_mutations: int
    beneficial_mutations: int
    best_fitness: float
    best_skill: str
    propagation_tree: tuple[str, ...]
    duration_ms: float
    strategy: str


@dataclass(frozen=True)
class MutationRecord:
    """Record of a single mutation applied to a skill."""

    generation: int
    parent_skill: str
    child_skill: str
    mutation_type: str
    fitness_delta: float  # Positive = improvement
    trait_changes: tuple[str, ...]


class RecursivePropagator:
    """Recursively propagates skill improvements across generations.

    Features:
    - Multi-strategy propagation (BFS, DFS, fitness-guided, diversity)
    - Mutation application and fitness evaluation
    - Beneficial mutation tracking
    - Convergence detection
    - Generation limit enforcement
    """

    def __init__(
        self,
        max_generations: int = 10,
        convergence_threshold: float = 0.001,
        strategy: PropagationStrategy = PropagationStrategy.FITNESS_GUIDED,
    ):
        self.max_generations = max_generations
        self.convergence_threshold = convergence_threshold
        self.strategy = strategy
        self._history: dict[str, list[MutationRecord]] = {}
        self._fitness_cache: dict[str, float] = {}

    def propagate(
        self,
        skill_name: str,
        initial_fitness: float,
        mutation_fn,
        fitness_fn,
    ) -> PropagationResult:
        """Recursively propagate improvements starting from a skill.

        Args:
            skill_name: Name of the root skill
            initial_fitness: Starting fitness score
            mutation_fn: Callable(skill_name, generation) -> list[(new_name, mutations, traits)]
            fitness_fn: Callable(skill_name) -> float

        Returns:
            PropagationResult summarizing the propagation
        """
        start_time = datetime.now()

        self._fitness_cache[skill_name] = initial_fitness
        self._history[skill_name] = []

        best_fitness = initial_fitness
        best_skill = skill_name
        total_mutations = 0
        beneficial_mutations = 0
        all_skills = [skill_name]

        current_gen = [(skill_name, initial_fitness)]
        generation = 0

        for generation in range(1, self.max_generations + 1):
            next_gen = []

            for parent_name, parent_fitness in current_gen:
                try:
                    mutations = mutation_fn(parent_name, generation)
                except Exception:
                    continue

                for child_name, mutated_traits, trait_desc in mutations:
                    total_mutations += 1

                    try:
                        child_fitness = fitness_fn(child_name)
                    except Exception:
                        child_fitness = parent_fitness * 0.95  # Slight penalty

                    self._fitness_cache[child_name] = child_fitness

                    fitness_delta = child_fitness - parent_fitness
                    record = MutationRecord(
                        generation=generation,
                        parent_skill=parent_name,
                        child_skill=child_name,
                        mutation_type=trait_desc,
                        fitness_delta=fitness_delta,
                        trait_changes=tuple(mutated_traits),
                    )

                    if parent_name not in self._history:
                        self._history[parent_name] = []
                    self._history[parent_name].append(record)

                    if fitness_delta > 0:
                        beneficial_mutations += 1

                    if child_fitness > best_fitness:
                        best_fitness = child_fitness
                        best_skill = child_name

                    next_gen.append((child_name, child_fitness))
                    all_skills.append(child_name)

            if not next_gen:
                break

            # Sort based on strategy
            if self.strategy == PropagationStrategy.FITNESS_GUIDED:
                next_gen.sort(key=lambda x: x[1], reverse=True)
            elif self.strategy == PropagationStrategy.DIVERSITY_GUIDED:
                next_gen.sort(key=lambda x: len(self._history.get(x[0], [])), reverse=True)

            # Keep top performers
            next_gen = next_gen[: max(3, len(next_gen) // 2)]
            current_gen = next_gen

            # Check convergence
            if generation > 1 and best_fitness - initial_fitness < self.convergence_threshold:
                break

        duration_ms = (datetime.now() - start_time).total_seconds() * 1000

        return PropagationResult(
            original_skill=skill_name,
            total_generations=min(generation, self.max_generations),
            total_mutations=total_mutations,
            beneficial_mutations=beneficial_mutations,
            best_fitness=best_fitness,
            best_skill=best_skill,
            propagation_tree=tuple(all_skills),
            duration_ms=duration_ms,
            strategy=self.strategy.value,
        )

    def get_mutation_history(self, skill_name: str) -> list[MutationRecord]:
        """Get all mutations recorded for a skill."""
        return self._history.get(skill_name, [])

    def get_fitness(self, skill_name: str) -> float | None:
        """Get cached fitness score for a skill."""
        return self._fitness_cache.get(skill_name)

    def get_improvement_ratio(self, original_skill: str) -> float:
        """Get the improvement ratio from original to best descendant."""
        original = self._fitness_cache.get(original_skill, 0.0)
        descendants = [
            (name, fitness)
            for name, fitness in self._fitness_cache.items()
            if name != original_skill
        ]
        if not descendants:
            return 0.0

        best_descendant = max(descendants, key=lambda x: x[1])
        if original == 0:
            return float("inf") if best_descendant[1] > 0 else 0.0
        return (best_descendant[1] - original) / original

    def get_mutations_by_type(self, skill_name: str) -> dict[str, int]:
        """Count mutations by type for a skill."""
        counts: dict[str, int] = {}
        for record in self._history.get(skill_name, []):
            counts[record.mutation_type] = counts.get(record.mutation_type, 0) + 1
        return counts

    def clear(self) -> None:
        """Clear all propagation history."""
        self._history.clear()
        self._fitness_cache.clear()
