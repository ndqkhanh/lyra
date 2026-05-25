"""Genetic Optimizer — Population-based optimization for agent evolution.

Provides population management, selection strategies (tournament, roulette,
rank), crossover operations for agent strategies, mutation operations for
exploration, and fitness evaluation with multi-objective support.
"""

from __future__ import annotations

import asyncio
import logging
import math
import random
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Sequence, TypeVar

from .meta_evolution import (
    AgentGenome,
    EvolutionResult,
    EvolutionTrigger,
    FitnessFunction,
    MetaEvolutionError,
)

logger = logging.getLogger(__name__)


# ── Exceptions ──────────────────────────────────────────────────────────────────


class GeneticOptimizerError(MetaEvolutionError):
    """Base exception for genetic optimizer errors."""


class PopulationEmptyError(GeneticOptimizerError):
    """Raised when operating on an empty population."""


class SelectionError(GeneticOptimizerError):
    """Raised when selection fails."""


class CrossoverError(GeneticOptimizerError):
    """Raised when crossover fails."""


# ── Types ───────────────────────────────────────────────────────────────────────

T = TypeVar("T", bound=AgentGenome)


@dataclass
class SelectionResult:
    """Result of a selection operation."""

    selected: list[AgentGenome]
    rejected: list[AgentGenome]
    selection_pressure: float  # ratio of selected to total
    diversity_score: float     # population diversity after selection


@dataclass
class CrossoverResult:
    """Result of a crossover operation."""

    parent_ids: list[str]
    offspring: AgentGenome
    crossover_points: list[str]  # which fields were crossed
    inheritance_map: dict[str, str]  # child_field -> parent_id


@dataclass
class GeneticOptimizationResult:
    """Full result of a genetic optimization cycle."""

    generation: int
    population_size_before: int
    population_size_after: int
    avg_fitness_before: float
    avg_fitness_after: float
    best_fitness_before: float
    best_fitness_after: float
    diversity_before: float
    diversity_after: float
    selection_result: SelectionResult
    mutation_count: int
    crossover_count: int
    duration_ms: float
    metadata: dict[str, Any] = field(default_factory=dict)


# ── Selection Strategies ────────────────────────────────────────────────────────


class SelectionStrategy(ABC):
    """Abstract base for selection strategies."""

    @abstractmethod
    def select(
        self,
        population: list[AgentGenome],
        fitness_scores: dict[str, float],
        count: int,
    ) -> list[AgentGenome]:
        """Select `count` individuals from the population."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Strategy name."""
        ...


class TournamentSelection(SelectionStrategy):
    """Tournament selection: pick K random individuals, keep the best.

    Higher tournament size = higher selection pressure.
    """

    def __init__(self, tournament_size: int = 3, elite_count: int = 2):
        self.tournament_size = tournament_size
        self.elite_count = elite_count

    @property
    def name(self) -> str:
        return "tournament"

    def select(
        self,
        population: list[AgentGenome],
        fitness_scores: dict[str, float],
        count: int,
    ) -> list[AgentGenome]:
        if not population:
            return []

        # Elite preservation
        sorted_pop = sorted(
            population,
            key=lambda g: fitness_scores.get(g.agent_id, 0.0),
            reverse=True,
        )

        selected_ids: set[str] = set()
        selected: list[AgentGenome] = []

        # Keep elite individuals
        for elite in sorted_pop[:self.elite_count]:
            selected.append(elite)
            selected_ids.add(elite.agent_id)

        # Tournament selection for remaining
        remaining = count - len(selected)
        for _ in range(remaining):
            if len(population) < self.tournament_size:
                break

            tournament = random.sample(population, min(self.tournament_size, len(population)))
            winner = max(tournament, key=lambda g: fitness_scores.get(g.agent_id, 0.0))

            if winner.agent_id not in selected_ids:
                selected.append(winner)
                selected_ids.add(winner.agent_id)
            else:
                # Pick another random non-selected
                alternatives = [g for g in population if g.agent_id not in selected_ids]
                if alternatives:
                    selected.append(random.choice(alternatives))
                    selected_ids.add(selected[-1].agent_id)

        return selected[:count]


class RouletteSelection(SelectionStrategy):
    """Fitness-proportionate (roulette wheel) selection.

    Individuals with higher fitness have higher probability of selection.
    """

    def __init__(self, elite_count: int = 2):
        self.elite_count = elite_count

    @property
    def name(self) -> str:
        return "roulette"

    def select(
        self,
        population: list[AgentGenome],
        fitness_scores: dict[str, float],
        count: int,
    ) -> list[AgentGenome]:
        if not population:
            return []

        # Elite preservation
        sorted_pop = sorted(
            population,
            key=lambda g: fitness_scores.get(g.agent_id, 0.0),
            reverse=True,
        )

        selected: list[AgentGenome] = []
        selected_ids: set[str] = set()

        for elite in sorted_pop[:self.elite_count]:
            selected.append(elite)
            selected_ids.add(elite.agent_id)

        # Roulette wheel for remaining
        remaining = count - len(selected)
        if remaining <= 0:
            return selected

        # Build cumulative distribution
        pop_fitness = [max(fitness_scores.get(g.agent_id, 0.0), 1e-8) for g in population]
        total_fitness = sum(pop_fitness)

        for _ in range(remaining):
            pick = random.uniform(0, total_fitness)
            cumulative = 0.0
            for i, fit in enumerate(pop_fitness):
                cumulative += fit
                if cumulative >= pick:
                    candidate = population[i]
                    if candidate.agent_id not in selected_ids:
                        selected.append(candidate)
                        selected_ids.add(candidate.agent_id)
                    break

        return selected[:count]


class RankSelection(SelectionStrategy):
    """Rank-based selection: selection probability based on rank, not raw fitness.

    More robust against fitness outliers than roulette selection.
    """

    def __init__(self, selection_pressure: float = 1.5):
        self.selection_pressure = selection_pressure

    @property
    def name(self) -> str:
        return "rank"

    def select(
        self,
        population: list[AgentGenome],
        fitness_scores: dict[str, float],
        count: int,
    ) -> list[AgentGenome]:
        if not population:
            return []

        n = len(population)
        ranked = sorted(
            population,
            key=lambda g: fitness_scores.get(g.agent_id, 0.0),
        )  # Ascending (worst first)

        # Linear rank probabilities
        rank_weights = [
            (2 - self.selection_pressure) / n
            + 2 * rank * (self.selection_pressure - 1) / (n * (n - 1))
            for rank in range(n)
        ]

        selected: list[AgentGenome] = []
        selected_ids: set[str] = set()

        for _ in range(count):
            idx = random.choices(range(n), weights=rank_weights, k=1)[0]
            candidate = ranked[idx]
            if candidate.agent_id not in selected_ids:
                selected.append(candidate)
                selected_ids.add(candidate.agent_id)

        return selected


# ── Crossover Operations ────────────────────────────────────────────────────────


class CrossoverOperator:
    """Crossover operations for combining parent genomes.

    Supports multiple crossover strategies for different genome components.
    """

    @staticmethod
    def uniform_crossover(
        parent1: AgentGenome,
        parent2: AgentGenome,
        crossover_rate: float = 0.5,
    ) -> AgentGenome:
        """Uniform crossover: each gene randomly from either parent."""
        child = AgentGenome(
            agent_id=f"{parent1.agent_id}_x_{parent2.agent_id}",
            generation=max(parent1.generation, parent2.generation) + 1,
            parent_ids=[parent1.agent_id, parent2.agent_id],
        )

        # Crossover hyperparameters
        all_keys = set(parent1.hyperparameters.keys()) | set(parent2.hyperparameters.keys())
        for key in all_keys:
            if random.random() < crossover_rate:
                child.hyperparameters[key] = parent1.hyperparameters.get(
                    key, parent2.hyperparameters.get(key, 0.5)
                )
            else:
                child.hyperparameters[key] = parent2.hyperparameters.get(
                    key, parent1.hyperparameters.get(key, 0.5)
                )

        # Crossover strategy weights
        all_weights = set(parent1.strategy_weights.keys()) | set(parent2.strategy_weights.keys())
        for key in all_weights:
            child.strategy_weights[key] = (
                (parent1.strategy_weights.get(key, 0.0) + parent2.strategy_weights.get(key, 0.0)) / 2
            )

        # Blend active strategies
        child.active_strategies = list(
            set(parent1.active_strategies) | set(parent2.active_strategies)
        )

        # Crossover objective weights (average)
        all_objectives = set(parent1.objective_weights.keys()) | set(parent2.objective_weights.keys())
        for key in all_objectives:
            child.objective_weights[key] = (
                (parent1.objective_weights.get(key, 0.0) + parent2.objective_weights.get(key, 0.0)) / 2
            )

        return child

    @staticmethod
    def single_point_crossover(
        parent1: AgentGenome,
        parent2: AgentGenome,
        crossover_point: Optional[str] = None,
    ) -> AgentGenome:
        """Single-point crossover: split at a point, swap halves."""
        fields = [
            "hyperparameters",
            "strategy_weights",
            "active_strategies",
            "objective_weights",
            "constraints",
        ]
        point = crossover_point or random.choice(fields)
        point_idx = fields.index(point) if point in fields else len(fields) // 2

        child = AgentGenome(
            agent_id=f"{parent1.agent_id}_spx_{parent2.agent_id}",
            generation=max(parent1.generation, parent2.generation) + 1,
            parent_ids=[parent1.agent_id, parent2.agent_id],
        )

        for i, field_name in enumerate(fields):
            source = parent1 if i < point_idx else parent2
            value = getattr(source, field_name)
            setattr(child, field_name, value)

        return child

    @staticmethod
    def arithmetic_crossover(
        parent1: AgentGenome,
        parent2: AgentGenome,
        alpha: float = 0.5,
    ) -> AgentGenome:
        """Arithmetic crossover: weighted average of parent values."""
        child = AgentGenome(
            agent_id=f"{parent1.agent_id}_ax_{parent2.agent_id}",
            generation=max(parent1.generation, parent2.generation) + 1,
            parent_ids=[parent1.agent_id, parent2.agent_id],
        )

        for key in set(parent1.hyperparameters.keys()) | set(parent2.hyperparameters.keys()):
            v1 = parent1.hyperparameters.get(key, 0.0)
            v2 = parent2.hyperparameters.get(key, 0.0)
            child.hyperparameters[key] = alpha * v1 + (1 - alpha) * v2

        for key in set(parent1.objective_weights.keys()) | set(parent2.objective_weights.keys()):
            v1 = parent1.objective_weights.get(key, 0.0)
            v2 = parent2.objective_weights.get(key, 0.0)
            child.objective_weights[key] = alpha * v1 + (1 - alpha) * v2

        return child


# ── Mutation Operations ─────────────────────────────────────────────────────────


class MutationOperator:
    """Mutation operations for introducing variation.

    Supports Gaussian mutation, uniform mutation, and swap mutation
    for different genome components.
    """

    def __init__(
        self,
        mutation_rate: float = 0.1,
        mutation_strength: float = 0.1,
    ):
        self.mutation_rate = mutation_rate
        self.mutation_strength = mutation_strength
        self._mutation_history: list[dict[str, Any]] = []

    def mutate(self, genome: AgentGenome) -> tuple[AgentGenome, list[str]]:
        """Apply mutations to a genome. Returns (mutated_genome, change_log)."""
        changes: list[str] = []

        # Mutate hyperparameters (Gaussian perturbation)
        for key in list(genome.hyperparameters.keys()):
            if random.random() < self.mutation_rate:
                old = genome.hyperparameters[key]
                noise = random.gauss(0, self.mutation_strength)
                genome.hyperparameters[key] = max(0.0, old + noise * abs(old))
                if abs(genome.hyperparameters[key] - old) > 1e-8:
                    changes.append(f"mut_hp[{key}]: {old:.6f} -> {genome.hyperparameters[key]:.6f}")

        # Mutate strategy weights (perturbation)
        for key in list(genome.strategy_weights.keys()):
            if random.random() < self.mutation_rate:
                old = genome.strategy_weights[key]
                noise = random.uniform(-self.mutation_strength, self.mutation_strength)
                genome.strategy_weights[key] = max(0.0, min(1.0, old + noise))
                if abs(genome.strategy_weights[key] - old) > 0.001:
                    changes.append(f"mut_sw[{key}]: {old:.4f} -> {genome.strategy_weights[key]:.4f}")

        # Swap mutation: swap two active strategies
        if (
            len(genome.active_strategies) > 1
            and random.random() < self.mutation_rate * 0.5
        ):
            i, j = random.sample(range(len(genome.active_strategies)), 2)
            genome.active_strategies[i], genome.active_strategies[j] = (
                genome.active_strategies[j],
                genome.active_strategies[i],
            )
            changes.append(f"mut_swap: strategies[{i}] <-> [{j}]")

        # Mutate objective weights
        for key in list(genome.objective_weights.keys()):
            if random.random() < self.mutation_rate:
                old = genome.objective_weights[key]
                noise = random.uniform(-self.mutation_strength, self.mutation_strength)
                genome.objective_weights[key] = max(0.0, old + noise)

        # Re-normalize objective weights
        total_obj = sum(genome.objective_weights.values())
        if total_obj > 0:
            for key in genome.objective_weights:
                genome.objective_weights[key] /= total_obj

        genome.generation += 1
        self._mutation_history.append({
            "agent_id": genome.agent_id,
            "generation": genome.generation,
            "changes": len(changes),
        })

        return genome, changes

    def mutate_population(
        self,
        population: list[AgentGenome],
    ) -> list[tuple[AgentGenome, list[str]]]:
        """Apply mutations to an entire population."""
        return [self.mutate(genome) for genome in population]

    @property
    def total_mutations(self) -> int:
        return len(self._mutation_history)


# ── Genetic Optimizer ───────────────────────────────────────────────────────────


class GeneticOptimizer:
    """Population-based genetic optimization engine.

    Manages a population of agent genomes, applying selection, crossover,
    and mutation iteratively to optimize for a fitness function.

    Usage::

        optimizer = GeneticOptimizer(
            population_size=100,
            selection=TournamentSelection(tournament_size=4),
        )

        for generation in range(50):
            result = await optimizer.evolve_generation(fitness_fn)
    """

    def __init__(
        self,
        population_size: int = 100,
        selection: Optional[SelectionStrategy] = None,
        crossover_rate: float = 0.7,
        mutation_rate: float = 0.1,
        elite_count: int = 2,
        crossover: Optional[CrossoverOperator] = None,
        mutation: Optional[MutationOperator] = None,
    ):
        self.population_size = population_size
        self.selection = selection or TournamentSelection(elite_count=elite_count)
        self.crossover_rate = crossover_rate
        self.elite_count = elite_count

        self._crossover = crossover or CrossoverOperator()
        self._mutation = mutation or MutationOperator(mutation_rate=mutation_rate)

        self._population: list[AgentGenome] = []
        self._fitness_cache: dict[str, float] = {}
        self._generation: int = 0
        self._history: list[GeneticOptimizationResult] = []

    def initialize_population(
        self,
        base_genome: Optional[AgentGenome] = None,
        variant_count: int = 0,
    ) -> None:
        """Initialize or seed the population.

        Args:
            base_genome: A seed genome to derive variants from.
            variant_count: If 0, creates random genomes.
        """
        self._population = []

        if base_genome:
            self._population.append(base_genome)
            # Create variants
            for i in range(min(variant_count or self.population_size - 1, self.population_size)):
                variant = base_genome.clone(f"{base_genome.agent_id}_seed_{i}")
                # Apply random perturbations
                self._mutation.mutate(variant)
                self._population.append(variant)
        else:
            for i in range(self.population_size):
                genome = AgentGenome(
                    agent_id=f"gen_{self._generation:03d}_{i:04d}",
                    generation=0,
                )
                self._population.append(genome)

        self._fitness_cache.clear()
        logger.info(
            "Initialized population of %d genomes (generation %d)",
            len(self._population), self._generation,
        )

    async def evaluate_population(
        self,
        fitness_fn: FitnessFunction,
    ) -> dict[str, float]:
        """Evaluate fitness for all genomes in the population."""
        scores: dict[str, float] = {}

        # Evaluate in parallel batches
        batch_size = 10
        for i in range(0, len(self._population), batch_size):
            batch = self._population[i:i + batch_size]
            tasks = [fitness_fn.evaluate(genome) for genome in batch]
            batch_scores = await asyncio.gather(*tasks, return_exceptions=True)

            for genome, score in zip(batch, batch_scores):
                if isinstance(score, Exception):
                    logger.warning(
                        "Fitness evaluation failed for %s: %s", genome.agent_id, score,
                    )
                    scores[genome.agent_id] = 0.0
                else:
                    scores[genome.agent_id] = score
                    genome.fitness_history.append(score)

        self._fitness_cache = scores
        return scores

    async def evolve_generation(
        self,
        fitness_fn: FitnessFunction,
    ) -> GeneticOptimizationResult:
        """Execute one full generation of evolution: evaluate, select, crossover, mutate."""
        start = time.perf_counter()

        if not self._population:
            raise PopulationEmptyError("Cannot evolve empty population")

        pop_before = len(self._population)
        avg_before, best_before, div_before = self._compute_stats()

        # 1. Evaluate
        fitness = await self.evaluate_population(fitness_fn)

        # 2. Select
        selected = self.selection.select(
            self._population,
            fitness,
            min(self.population_size, len(self._population)),
        )

        selection_result = SelectionResult(
            selected=selected,
            rejected=[g for g in self._population if g not in selected],
            selection_pressure=len(selected) / max(len(self._population), 1),
            diversity_score=self._compute_diversity(selected),
        )

        # 3. Crossover
        crossover_count = 0
        offspring: list[AgentGenome] = []
        selected_pool = list(selected)

        while len(offspring) + len(selected) < self.population_size:
            if len(selected_pool) < 2:
                break

            if random.random() < self.crossover_rate:
                p1, p2 = random.sample(selected_pool, 2)
                child = self._crossover.uniform_crossover(p1, p2)
                offspring.append(child)
                crossover_count += 1
            else:
                if selected_pool:
                    offspring.append(random.choice(selected_pool).clone())

        # 4. Mutate offspring
        mutation_count = 0
        for child in offspring:
            _, changes = self._mutation.mutate(child)
            if changes:
                mutation_count += 1

        # 5. Build new population: elites + offspring
        elites = selected[:self.elite_count]
        new_population = elites + offspring
        self._population = new_population[:self.population_size]

        # 6. Evaluate new population
        fitness_after = await self.evaluate_population(fitness_fn)

        self._generation += 1

        avg_after, best_after, div_after = self._compute_stats()

        result = GeneticOptimizationResult(
            generation=self._generation,
            population_size_before=pop_before,
            population_size_after=len(self._population),
            avg_fitness_before=avg_before,
            avg_fitness_after=avg_after,
            best_fitness_before=best_before,
            best_fitness_after=best_after,
            diversity_before=div_before,
            diversity_after=div_after,
            selection_result=selection_result,
            mutation_count=mutation_count,
            crossover_count=crossover_count,
            duration_ms=(time.perf_counter() - start) * 1000,
            metadata={
                "elites_preserved": self.elite_count,
                "offspring_created": len(offspring),
            },
        )

        self._history.append(result)

        logger.info(
            "Generation %d: avg_fit %.4f -> %.4f, best %.4f -> %.4f, div %.3f [%d cross, %d mut]",
            self._generation, avg_before, avg_after, best_before, best_after,
            div_after, crossover_count, mutation_count,
        )

        return result

    async def optimize(
        self,
        fitness_fn: FitnessFunction,
        max_generations: int = 100,
        convergence_threshold: float = 0.001,
        stagnation_patience: int = 10,
    ) -> tuple[AgentGenome, list[GeneticOptimizationResult]]:
        """Run the full genetic optimization loop.

        Returns the best genome found and the full history.
        """
        if not self._population:
            self.initialize_population()

        best_fitness = -float("inf")
        stagnation_count = 0

        for _ in range(max_generations):
            result = await self.evolve_generation(fitness_fn)

            improvement = result.best_fitness_after - best_fitness
            if improvement > convergence_threshold:
                best_fitness = result.best_fitness_after
                stagnation_count = 0
            else:
                stagnation_count += 1

            if stagnation_count >= stagnation_patience:
                logger.info(
                    "Converged at generation %d (best=%.4f, patience=%d)",
                    self._generation, best_fitness, stagnation_patience,
                )
                break

        # Find best genome
        best = max(self._population, key=lambda g: self._fitness_cache.get(g.agent_id, 0.0))
        return best, list(self._history)

    # ── Internal Helpers ─────────────────────────────────────────────────────

    def _compute_stats(self) -> tuple[float, float, float]:
        """Compute (avg_fitness, best_fitness, diversity) for current population."""
        if not self._population:
            return 0.0, 0.0, 0.0

        scores = [
            self._fitness_cache.get(g.agent_id, 0.0)
            for g in self._population
        ]

        avg = sum(scores) / len(scores)
        best = max(scores)
        diversity = self._compute_diversity(self._population)

        return avg, best, diversity

    @staticmethod
    def _compute_diversity(population: list[AgentGenome]) -> float:
        """Measure population diversity as average pairwise distance."""
        if len(population) < 2:
            return 1.0

        # Simple diversity: variance in hyperparameter means
        all_hps: dict[str, list[float]] = defaultdict(list)
        for genome in population:
            for key, value in genome.hyperparameters.items():
                all_hps[key].append(value)

        if not all_hps:
            return 0.0

        variances = []
        for values in all_hps.values():
            if len(values) > 1:
                mean = sum(values) / len(values)
                var = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
                variances.append(var)

        avg_var = sum(variances) / max(len(variances), 1)
        return min(avg_var * 10, 1.0)  # Scale up for readability

    # ── Properties ───────────────────────────────────────────────────────────

    @property
    def population(self) -> list[AgentGenome]:
        return list(self._population)

    @property
    def generation(self) -> int:
        return self._generation

    @property
    def best_genome(self) -> Optional[AgentGenome]:
        if not self._population or not self._fitness_cache:
            return None
        return max(self._population, key=lambda g: self._fitness_cache.get(g.agent_id, 0.0))

    @property
    def history(self) -> list[GeneticOptimizationResult]:
        return list(self._history)

    @property
    def fitness_scores(self) -> dict[str, float]:
        return dict(self._fitness_cache)
