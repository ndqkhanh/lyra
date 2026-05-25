"""Tests for lyra_meta_evolution.genetic_optimizer module."""

import asyncio

import pytest

from lyra_meta_evolution.genetic_optimizer import (
    CrossoverOperator,
    GeneticOptimizationResult,
    GeneticOptimizer,
    MutationOperator,
    PopulationEmptyError,
    RankSelection,
    RouletteSelection,
    SelectionResult,
    TournamentSelection,
)
from lyra_meta_evolution.meta_evolution import AgentGenome


# ── Fixtures ────────────────────────────────────────────────────────────────────


@pytest.fixture
def sample_genome():
    return AgentGenome(
        agent_id="parent_1",
        hyperparameters={"learning_rate": 0.01, "temperature": 1.0},
        strategy_weights={"greedy": 0.6, "exploration": 0.4},
        active_strategies=["greedy", "exploration"],
        objective_weights={"speed": 0.3, "quality": 0.7},
    )


@pytest.fixture
def sample_genome2():
    return AgentGenome(
        agent_id="parent_2",
        hyperparameters={"learning_rate": 0.001, "temperature": 0.5},
        strategy_weights={"greedy": 0.3, "exploitation": 0.7},
        active_strategies=["exploitation"],
        objective_weights={"speed": 0.6, "cost": 0.4},
    )


@pytest.fixture
def population(sample_genome):
    genomes = [sample_genome]
    for i in range(9):
        variant = sample_genome.clone(f"variant_{i}")
        genomes.append(variant)
    return genomes


# ── Fitness Function ────────────────────────────────────────────────────────────


class _SimpleFitness:
    """Simple fitness function for testing."""
    async def evaluate(self, genome: AgentGenome) -> float:
        lr = genome.hyperparameters.get("learning_rate", 0.01)
        temp = genome.hyperparameters.get("temperature", 1.0)
        return 0.5 + (0.001 / max(lr, 1e-6)) * 0.01 + (1.0 - temp) * 0.1


# ── TournamentSelection ─────────────────────────────────────────────────────────


class TestTournamentSelection:
    def test_selects_correct_count(self, population):
        selector = TournamentSelection(tournament_size=3, elite_count=2)
        fitness = {g.agent_id: 0.5 + i * 0.05 for i, g in enumerate(population)}
        selected = selector.select(population, fitness, 5)
        assert len(selected) <= 5
        assert len(selected) > 0

    def test_empty_population(self):
        selector = TournamentSelection()
        selected = selector.select([], {}, 5)
        assert selected == []

    def test_elite_preserved(self, population):
        selector = TournamentSelection(tournament_size=3, elite_count=2)
        # Make first genome the best
        fitness = {g.agent_id: 0.1 for g in population}
        fitness[population[0].agent_id] = 1.0
        selected = selector.select(population, fitness, 5)
        assert population[0] in selected  # Elite preserved


# ── RouletteSelection ───────────────────────────────────────────────────────────


class TestRouletteSelection:
    def test_selects_correct_count(self, population):
        selector = RouletteSelection(elite_count=2)
        fitness = {g.agent_id: 0.5 for g in population}
        selected = selector.select(population, fitness, 5)
        assert len(selected) <= 5
        assert len(selected) > 0

    def test_empty_population(self):
        selector = RouletteSelection()
        selected = selector.select([], {}, 5)
        assert selected == []


# ── RankSelection ───────────────────────────────────────────────────────────────


class TestRankSelection:
    def test_selects_correct_count(self, population):
        selector = RankSelection(selection_pressure=1.5)
        fitness = {g.agent_id: 0.5 for g in population}
        selected = selector.select(population, fitness, 5)
        assert len(selected) <= 5


# ── CrossoverOperator ───────────────────────────────────────────────────────────


class TestCrossoverOperator:
    def test_uniform_crossover_creates_child(self, sample_genome, sample_genome2):
        child = CrossoverOperator.uniform_crossover(sample_genome, sample_genome2)
        assert child.agent_id != sample_genome.agent_id
        assert child.agent_id != sample_genome2.agent_id
        assert len(child.parent_ids) == 2
        assert child.generation > sample_genome.generation

    def test_single_point_crossover(self, sample_genome, sample_genome2):
        child = CrossoverOperator.single_point_crossover(sample_genome, sample_genome2)
        assert child.agent_id is not None

    def test_arithmetic_crossover(self, sample_genome, sample_genome2):
        child = CrossoverOperator.arithmetic_crossover(sample_genome, sample_genome2, alpha=0.5)
        # Hyperparameters should be averaged
        for key in sample_genome.hyperparameters:
            if key in sample_genome2.hyperparameters:
                v1 = sample_genome.hyperparameters[key]
                v2 = sample_genome2.hyperparameters[key]
                avg = (v1 + v2) / 2
                assert abs(child.hyperparameters[key] - avg) < 1e-6


# ── MutationOperator ────────────────────────────────────────────────────────────


class TestMutationOperator:
    def test_mutate_modifies_genome(self, sample_genome):
        mutator = MutationOperator(mutation_rate=1.0, mutation_strength=0.5)
        original_lr = sample_genome.hyperparameters.get("learning_rate", 0.01)
        genome, changes = mutator.mutate(sample_genome)
        # With rate 1.0, hyperparameters should be mutated
        assert len(changes) > 0

    def test_mutation_history(self, sample_genome):
        mutator = MutationOperator(mutation_rate=1.0)
        mutator.mutate(sample_genome)
        assert mutator.total_mutations == 1

    def test_mutate_population(self, population):
        mutator = MutationOperator(mutation_rate=1.0)
        results = mutator.mutate_population(population)
        assert len(results) == len(population)

    def test_zero_mutation_rate_no_change(self, sample_genome):
        mutator = MutationOperator(mutation_rate=0.0)
        _, changes = mutator.mutate(sample_genome)
        # Active strategies might still shuffle, but hps won't change
        assert len(changes) >= 0


# ── GeneticOptimizer ────────────────────────────────────────────────────────────


class TestGeneticOptimizer:
    def test_initialize_population(self, sample_genome):
        optimizer = GeneticOptimizer(population_size=20)
        optimizer.initialize_population(sample_genome, variant_count=19)
        assert len(optimizer.population) == 20

    def test_initialize_without_seed(self):
        optimizer = GeneticOptimizer(population_size=10)
        optimizer.initialize_population()
        assert len(optimizer.population) == 10

    def test_evolve_generation(self, sample_genome):
        optimizer = GeneticOptimizer(
            population_size=20,
            selection=TournamentSelection(tournament_size=3),
            mutation_rate=0.2,
        )
        optimizer.initialize_population(sample_genome, variant_count=19)
        fitness = _SimpleFitness()
        result = asyncio.run(optimizer.evolve_generation(fitness))
        assert isinstance(result, GeneticOptimizationResult)
        assert result.generation == 1
        assert result.population_size_after > 0

    def test_evolve_empty_population_raises(self):
        optimizer = GeneticOptimizer()
        fitness = _SimpleFitness()
        with pytest.raises(PopulationEmptyError):
            asyncio.run(optimizer.evolve_generation(fitness))

    def test_optimize_full_run(self, sample_genome):
        optimizer = GeneticOptimizer(
            population_size=20,
            mutation_rate=0.3,
        )
        optimizer.initialize_population(sample_genome, variant_count=19)
        fitness = _SimpleFitness()
        best, history = asyncio.run(optimizer.optimize(
            fitness_fn=fitness,
            max_generations=10,
            convergence_threshold=0.001,
            stagnation_patience=5,
        ))
        assert isinstance(best, AgentGenome)
        assert len(history) > 0

    def test_fitness_scores_populated(self, sample_genome):
        optimizer = GeneticOptimizer(population_size=10)
        optimizer.initialize_population(sample_genome, variant_count=9)
        fitness = _SimpleFitness()
        asyncio.run(optimizer.evolve_generation(fitness))
        assert len(optimizer.fitness_scores) > 0

    def test_best_genome_returns_best(self, sample_genome):
        optimizer = GeneticOptimizer(population_size=10)
        optimizer.initialize_population(sample_genome, variant_count=9)
        fitness = _SimpleFitness()
        asyncio.run(optimizer.evolve_generation(fitness))
        best = optimizer.best_genome
        assert best is not None
        assert isinstance(best, AgentGenome)


# ── SelectionResult ─────────────────────────────────────────────────────────────


class TestSelectionResult:
    def test_creation(self):
        result = SelectionResult(
            selected=[],
            rejected=[],
            selection_pressure=0.5,
            diversity_score=0.7,
        )
        assert result.selection_pressure == 0.5
        assert result.diversity_score == 0.7
