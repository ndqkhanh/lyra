"""Collective Evolver - Population-level skill evolution with fitness-driven selection.

Implements SkillClaw-style collective evolution where skills compete,
mate (crossover), and mutate across generations with fitness-driven
selection pressure.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class SelectionMethod(StrEnum):
    """Selection strategy for parent skills."""

    TOURNAMENT = "tournament"
    ROULETTE = "roulette"
    RANK = "rank"
    ELITISM = "elitism"


@dataclass(frozen=True)
class EvolutionResult:
    """Result of a collective evolution run."""

    population_name: str
    initial_size: int
    final_size: int
    generations: int
    initial_avg_fitness: float
    final_avg_fitness: float
    best_initial_fitness: float
    best_final_fitness: float
    improvement_pct: float
    total_mutations: int
    total_crossovers: int
    extinct_lineages: int
    survival_rate: float


@dataclass(frozen=True)
class GenerationSnapshot:
    """Snapshot of a single generation in the evolution."""

    generation: int
    population_size: int
    avg_fitness: float
    max_fitness: float
    min_fitness: float
    new_skills: tuple[str, ...]
    extinct_skills: tuple[str, ...]


class CollectiveEvolver:
    """Collective evolution engine for skill populations.

    Features:
    - Tournament, roulette, rank, and elitism selection
    - Crossover between parent skills
    - Mutation with configurable rate and types
    - Fitness-driven generational advancement
    - Extinction and survival tracking
    - Convergence detection
    """

    def __init__(
        self,
        population_size: int = 50,
        mutation_rate: float = 0.1,
        crossover_rate: float = 0.7,
        elitism_count: int = 2,
        selection_method: SelectionMethod = SelectionMethod.TOURNAMENT,
        tournament_size: int = 3,
    ):
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.elitism_count = elitism_count
        self.selection_method = selection_method
        self.tournament_size = tournament_size

        self._population: dict[str, dict] = {}  # {name: {fitness, traits, parent, gen}}
        self._history: list[GenerationSnapshot] = []
        self._generation = 0

    def seed_population(
        self,
        skills: list[tuple[str, list[str]]],  # [(name, [trait, ...]), ...]
        fitness_fn,
    ) -> None:
        """Seed the initial population.

        Args:
            skills: List of (skill_name, traits) tuples
            fitness_fn: Callable(skill_name, traits) -> float
        """
        self._population.clear()
        self._history.clear()
        self._generation = 0

        for name, traits in skills:
            fitness = fitness_fn(name, traits)
            self._population[name] = {
                "traits": list(traits),
                "fitness": fitness,
                "parent": None,
                "generation": 0,
            }

    def evolve_generation(
        self,
        fitness_fn,
        mutate_fn,
        crossover_fn,
    ) -> GenerationSnapshot:
        """Evolve one generation.

        Args:
            fitness_fn: Callable(skill_name, traits) -> float
            mutate_fn: Callable(traits) -> (list[str], str) — (new_traits, mutation_desc)
            crossover_fn: Callable(traits_a, traits_b) -> list[str]

        Returns:
            GenerationSnapshot for the new generation
        """
        self._generation += 1
        current_pop = dict(self._population)
        new_pop: dict[str, dict] = {}

        # Sort by fitness
        sorted_skills = sorted(
            current_pop.items(), key=lambda x: x[1]["fitness"], reverse=True
        )

        # Elitism — keep top performers
        for _, (name, data) in zip(range(self.elitism_count), sorted_skills[: self.elitism_count]):
            new_pop[name] = {
                "traits": list(data["traits"]),
                "fitness": data["fitness"],
                "parent": name,
                "generation": self._generation,
            }

        extinct = []

        # Fill population
        attempts = 0
        max_attempts = self.population_size * 3
        mutations_count = 0
        crossovers_count = 0

        while len(new_pop) < self.population_size and attempts < max_attempts:
            attempts += 1

            # Select parents
            parent_a = self._select_parent(current_pop)
            parent_b = self._select_parent(current_pop)

            if not parent_a or not parent_b:
                continue

            parent_a_traits = current_pop[parent_a]["traits"]
            parent_b_traits = current_pop[parent_b]["traits"]

            # Crossover
            if random.random() < self.crossover_rate:
                child_traits = crossover_fn(parent_a_traits, parent_b_traits)
                crossovers_count += 1
            else:
                child_traits = list(parent_a_traits)

            # Mutation
            if random.random() < self.mutation_rate:
                child_traits, _ = mutate_fn(child_traits)
                mutations_count += 1

            child_name = f"{parent_a}_x_{parent_b}_gen{self._generation}_{len(new_pop)}"
            child_fitness = fitness_fn(child_name, child_traits)

            new_pop[child_name] = {
                "traits": child_traits,
                "fitness": child_fitness,
                "parent": f"{parent_a}+{parent_b}",
                "generation": self._generation,
            }

        # Identify extinct skills
        for name in current_pop:
            if name not in new_pop and not any(
                data["parent"] and name in data["parent"]
                for data in new_pop.values()
            ):
                extinct.append(name)

        # Update population
        self._population = new_pop

        # Record snapshot
        fitnesses = [d["fitness"] for d in new_pop.values()]
        new_skills = [n for n in new_pop if n not in current_pop]
        snapshot = GenerationSnapshot(
            generation=self._generation,
            population_size=len(new_pop),
            avg_fitness=sum(fitnesses) / len(fitnesses) if fitnesses else 0.0,
            max_fitness=max(fitnesses) if fitnesses else 0.0,
            min_fitness=min(fitnesses) if fitnesses else 0.0,
            new_skills=tuple(new_skills),
            extinct_skills=tuple(extinct),
        )
        self._history.append(snapshot)

        return snapshot

    def evolve(
        self,
        generations: int,
        fitness_fn,
        mutate_fn,
        crossover_fn,
        convergence_threshold: float = 0.0001,
    ) -> EvolutionResult:
        """Run evolution for multiple generations.

        Args:
            generations: Maximum number of generations
            fitness_fn: Callable(skill_name, traits) -> float
            mutate_fn: Callable(traits) -> (list[str], str)
            crossover_fn: Callable(traits_a, traits_b) -> list[str]
            convergence_threshold: Stop if improvement < threshold

        Returns:
            EvolutionResult
        """
        initial_fitnesses = [d["fitness"] for d in self._population.values()]
        initial_avg = sum(initial_fitnesses) / len(initial_fitnesses) if initial_fitnesses else 0.0
        initial_best = max(initial_fitnesses) if initial_fitnesses else 0.0
        initial_size = len(self._population)

        total_mutations = 0
        total_crossovers = 0
        prev_best = initial_best

        for _ in range(generations):
            snapshot = self.evolve_generation(fitness_fn, mutate_fn, crossover_fn)
            total_mutations += len(snapshot.new_skills)
            total_crossovers += len(snapshot.new_skills)

            # Check convergence
            if abs(snapshot.max_fitness - prev_best) < convergence_threshold:
                break
            prev_best = snapshot.max_fitness

        final_fitnesses = [d["fitness"] for d in self._population.values()]
        final_avg = sum(final_fitnesses) / len(final_fitnesses) if final_fitnesses else 0.0
        final_best = max(final_fitnesses) if final_fitnesses else 0.0

        if initial_avg > 0:
            improvement_pct = ((final_avg - initial_avg) / initial_avg) * 100
        else:
            improvement_pct = 0.0

        extinct_count = sum(len(s.extinct_skills) for s in self._history)

        return EvolutionResult(
            population_name=f"evolution_run_{datetime.now().isoformat()}",
            initial_size=initial_size,
            final_size=len(self._population),
            generations=self._generation,
            initial_avg_fitness=initial_avg,
            final_avg_fitness=final_avg,
            best_initial_fitness=initial_best,
            best_final_fitness=final_best,
            improvement_pct=improvement_pct,
            total_mutations=total_mutations,
            total_crossovers=total_crossovers,
            extinct_lineages=extinct_count,
            survival_rate=len(self._population) / initial_size if initial_size > 0 else 0.0,
        )

    def _select_parent(self, population: dict[str, dict]) -> str | None:
        """Select a parent from the population."""
        if not population:
            return None

        if self.selection_method == SelectionMethod.ELITISM:
            return max(population.items(), key=lambda x: x[1]["fitness"])[0]

        elif self.selection_method == SelectionMethod.TOURNAMENT:
            if len(population) < self.tournament_size:
                candidates = list(population.keys())
            else:
                candidates = random.sample(
                    list(population.keys()), self.tournament_size
                )
            return max(candidates, key=lambda n: population[n]["fitness"])

        elif self.selection_method == SelectionMethod.ROULETTE:
            total_fitness = sum(d["fitness"] for d in population.values())
            if total_fitness <= 0:
                return random.choice(list(population.keys()))

            pick = random.uniform(0, total_fitness)
            current = 0.0
            for name, data in population.items():
                current += data["fitness"]
                if current >= pick:
                    return name
            return list(population.keys())[-1]

        elif self.selection_method == SelectionMethod.RANK:
            ranked = sorted(
                population.items(), key=lambda x: x[1]["fitness"]
            )
            n = len(ranked)
            weights = [(i + 1) / (n * (n + 1) / 2) for i in range(n)]
            chosen = random.choices(
                [r[0] for r in ranked], weights=weights, k=1
            )
            return chosen[0]

        return None

    def get_best_skills(self, limit: int = 10) -> list[tuple[str, float, int]]:
        """Get the best skills by fitness.

        Returns:
            List of (name, fitness, generation) tuples
        """
        sorted_skills = sorted(
            self._population.items(),
            key=lambda x: x[1]["fitness"],
            reverse=True,
        )
        return [
            (name, data["fitness"], data["generation"])
            for name, data in sorted_skills[:limit]
        ]

    def get_history(self) -> list[GenerationSnapshot]:
        """Get generation snapshots."""
        return list(self._history)

    def get_fitness_trend(self) -> list[float]:
        """Get average fitness trend across generations."""
        return [s.avg_fitness for s in self._history]

    def get_diversity_score(self) -> float:
        """Calculate trait diversity in the current population."""
        all_traits: set[str] = set()
        total_traits = 0
        for data in self._population.values():
            traits = data["traits"]
            all_traits.update(traits)
            total_traits += len(traits)

        if total_traits == 0:
            return 0.0

        return len(all_traits) / total_traits

    @property
    def current_population_size(self) -> int:
        return len(self._population)

    @property
    def current_generation(self) -> int:
        return self._generation

    def clear(self) -> None:
        """Clear all evolution state."""
        self._population.clear()
        self._history.clear()
        self._generation = 0
