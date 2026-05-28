"""Strategy evolver — evolves agent strategies through mutation, crossover, and selection.

Manages a population of evolution strategies, applies genetic operators,
and selects the fittest strategies for the next generation.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from enum import StrEnum


class GeneType(StrEnum):
    EXPLORATION = "exploration"
    EXPLOITATION = "exploitation"
    CONSERVATISM = "conservatism"
    RISK_TAKING = "risk_taking"


@dataclass(frozen=True)
class StrategyGene:
    gene_type: GeneType
    value: float
    mutation_rate: float
    min_bound: float
    max_bound: float

    def mutate(self) -> StrategyGene:
        if random.random() < self.mutation_rate:
            delta = random.uniform(-0.1, 0.1) * (self.max_bound - self.min_bound)
            new_value = max(self.min_bound, min(self.max_bound, self.value + delta))
            return StrategyGene(
                gene_type=self.gene_type,
                value=round(new_value, 4),
                mutation_rate=self.mutation_rate,
                min_bound=self.min_bound,
                max_bound=self.max_bound,
            )
        return self


@dataclass(frozen=True)
class EvolutionStrategy:
    strategy_id: str
    genes: list[StrategyGene]
    generation: int
    fitness: float
    parent_ids: list[str]
    created_at: float


class StrategyEvolver:
    """Evolves agent strategies through genetic algorithms.

    Maintains a population of strategies, applies tournament selection,
    single-point crossover, and per-gene mutation to evolve strategies
    that maximize task success rates.
    """

    def __init__(
        self, population_size: int = 20, elite_count: int = 3
    ) -> None:
        self.population_size = population_size
        self.elite_count = elite_count
        self._population: list[EvolutionStrategy] = []
        self._generation = 0
        self._counter = 0

    def initialize(self) -> list[EvolutionStrategy]:
        self._population = [self._random_strategy(0) for _ in range(self.population_size)]
        self._generation = 0
        return list(self._population)

    def evolve(self, fitness_scores: dict[str, float]) -> list[EvolutionStrategy]:
        if not self._population:
            return self.initialize()

        scored = sorted(
            self._population,
            key=lambda s: fitness_scores.get(s.strategy_id, 0.0),
            reverse=True,
        )
        elites = scored[: self.elite_count]
        new_population = list(elites)

        while len(new_population) < self.population_size:
            parent1 = self._tournament_select(scored)
            parent2 = self._tournament_select(scored)
            child = self._crossover(parent1, parent2)
            child = self._mutate(child)
            new_population.append(child)

        self._generation += 1
        self._population = new_population[: self.population_size]
        return list(self._population)

    def _random_strategy(self, generation: int) -> EvolutionStrategy:
        self._counter += 1
        genes = [
            StrategyGene(
                gene_type=GeneType.EXPLORATION,
                value=round(random.uniform(0.0, 1.0), 4),
                mutation_rate=0.1,
                min_bound=0.0,
                max_bound=1.0,
            ),
            StrategyGene(
                gene_type=GeneType.EXPLOITATION,
                value=round(random.uniform(0.0, 1.0), 4),
                mutation_rate=0.1,
                min_bound=0.0,
                max_bound=1.0,
            ),
            StrategyGene(
                gene_type=GeneType.CONSERVATISM,
                value=round(random.uniform(0.0, 1.0), 4),
                mutation_rate=0.1,
                min_bound=0.0,
                max_bound=1.0,
            ),
            StrategyGene(
                gene_type=GeneType.RISK_TAKING,
                value=round(random.uniform(0.0, 1.0), 4),
                mutation_rate=0.1,
                min_bound=0.0,
                max_bound=1.0,
            ),
        ]
        return EvolutionStrategy(
            strategy_id=f"evo-{self._counter:04d}",
            genes=genes,
            generation=generation,
            fitness=0.0,
            parent_ids=[],
            created_at=time.time(),
        )

    def _tournament_select(
        self, population: list[EvolutionStrategy], k: int = 3
    ) -> EvolutionStrategy:
        candidates = random.sample(population, min(k, len(population)))
        return max(candidates, key=lambda s: s.fitness)

    def _crossover(
        self, parent1: EvolutionStrategy, parent2: EvolutionStrategy
    ) -> EvolutionStrategy:
        self._counter += 1
        crossover_point = random.randint(1, len(parent1.genes) - 1)
        child_genes = [
            parent1.genes[i] if i < crossover_point else parent2.genes[i]
            for i in range(len(parent1.genes))
        ]
        return EvolutionStrategy(
            strategy_id=f"evo-{self._counter:04d}",
            genes=child_genes,
            generation=self._generation + 1,
            fitness=0.0,
            parent_ids=[parent1.strategy_id, parent2.strategy_id],
            created_at=time.time(),
        )

    def _mutate(self, strategy: EvolutionStrategy) -> EvolutionStrategy:
        return EvolutionStrategy(
            strategy_id=strategy.strategy_id,
            genes=[g.mutate() for g in strategy.genes],
            generation=strategy.generation,
            fitness=strategy.fitness,
            parent_ids=strategy.parent_ids,
            created_at=strategy.created_at,
        )

    def stats(self) -> dict:
        return {
            "population_size": len(self._population),
            "generation": self._generation,
            "avg_fitness": round(
                sum(s.fitness for s in self._population) / max(len(self._population), 1), 4
            ),
        }
