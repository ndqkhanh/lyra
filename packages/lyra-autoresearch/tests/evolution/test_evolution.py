"""Tests for lyra-autoresearch evolution module."""
from __future__ import annotations

from unittest.mock import Mock

import pytest

from lyra_autoresearch.evolution import (
    EvolutionConfig,
    EvolutionEngine,
    EvolutionResult,
    Population,
    Strategy,
)


class TestEvolutionConfig:
    def test_defaults(self):
        c = EvolutionConfig()
        assert c.population_size > 0
        assert c.mutation_rate > 0.0
        assert c.crossover_rate > 0.0
        assert c.max_generations > 0

    def test_rates_between_0_and_1(self):
        c = EvolutionConfig()
        assert 0.0 <= c.mutation_rate <= 1.0
        assert 0.0 <= c.crossover_rate <= 1.0

    def test_custom_config(self):
        c = EvolutionConfig(
            population_size=50,
            mutation_rate=0.3,
            crossover_rate=0.8,
            max_generations=10,
            elitism_count=2,
        )
        assert c.population_size == 50
        assert c.mutation_rate == 0.3
        assert c.max_generations == 10


class TestStrategy:
    def test_creation(self):
        s = Strategy(
            name="test_strategy",
            params={"temperature": 0.7, "max_tokens": 1000},
            fitness=0.0,
        )
        assert s.name == "test_strategy"
        assert s.params["temperature"] == 0.7
        assert s.fitness == 0.0

    def test_equality(self):
        s1 = Strategy("s", {"a": 1}, 0.5)
        s2 = Strategy("s", {"a": 1}, 0.5)
        assert s1 == s2

    def test_hash(self):
        s1 = Strategy("s", {"a": 1}, 0.5)
        s2 = Strategy("s", {"a": 1}, 0.5)
        assert hash(s1) == hash(s2)

    def test_different_fitness_not_equal(self):
        s1 = Strategy("s", {"a": 1}, 0.5)
        s2 = Strategy("s", {"a": 1}, 0.9)
        assert s1 != s2


class TestPopulation:
    @pytest.fixture
    def strategies(self):
        return [
            Strategy(f"s{i}", {"value": i}, float(i) / 10.0)
            for i in range(10)
        ]

    @pytest.fixture
    def population(self, strategies):
        return Population(strategies)

    def test_size(self, population):
        assert population.size == 10

    def test_best_strategy(self, population):
        best = population.best
        assert best.fitness == 0.9

    def test_worst_strategy(self, population):
        worst = population.worst
        assert worst.fitness == 0.0

    def test_average_fitness(self, population):
        avg = population.average_fitness
        assert 0.0 <= avg <= 1.0

    def test_top_n(self, population):
        top3 = population.top(3)
        assert len(top3) == 3
        assert all(s.fitness >= 0.7 for s in top3)

    def test_empty_population(self):
        p = Population([])
        assert p.size == 0
        assert p.best is None


class TestEvolutionResult:
    def test_creation(self):
        result = EvolutionResult(
            best_strategy=Strategy("best", {"x": 1}, 0.95),
            final_fitness=0.95,
            generations=5,
            history=[0.3, 0.5, 0.7, 0.85, 0.95],
        )
        assert result.best_strategy.fitness == 0.95
        assert result.generations == 5
        assert len(result.history) == 5

    def test_improvement(self):
        result = EvolutionResult(
            best_strategy=Strategy("b", {}, 0.8),
            final_fitness=0.8,
            generations=3,
            history=[0.2, 0.5, 0.8],
        )
        assert result.improvement() == pytest.approx(0.6)

    def test_converged(self):
        result = EvolutionResult(
            best_strategy=Strategy("b", {}, 0.95),
            final_fitness=0.95,
            generations=3,
            history=[0.2, 0.8, 0.95],
        )
        assert result.is_converged(threshold=0.9)


class TestEvolutionEngine:
    @pytest.fixture
    def mock_evaluator(self):
        evaluator = Mock()
        evaluator.evaluate.side_effect = lambda s: s.params.get("value", 0)
        return evaluator

    @pytest.fixture
    def engine(self, mock_evaluator):
        config = EvolutionConfig(population_size=20, max_generations=3, elitism_count=2)
        return EvolutionEngine(config=config, evaluator=mock_evaluator)

    def test_initialize_population(self, engine):
        pop = engine.initialize_population()
        assert pop.size == engine.config.population_size
        for s in pop.strategies:
            assert s.fitness >= 0.0

    def test_run_evolution(self, engine, mock_evaluator):
        result = engine.run()
        assert isinstance(result, EvolutionResult)
        assert result.generations == engine.config.max_generations
        assert len(result.history) == engine.config.max_generations
        assert result.best_strategy is not None

    def test_elitism_preserves_best(self, engine, mock_evaluator):
        result = engine.run()
        # Best fitness should be monotonically non-decreasing due to elitism
        for i in range(1, len(result.history)):
            assert result.history[i] >= result.history[i - 1]

    def test_mutation_creates_variation(self, engine, mock_evaluator):
        pop1 = engine.initialize_population()
        mutated = engine.mutate(pop1)
        assert mutated.size == pop1.size

    def test_crossover(self, engine, mock_evaluator):
        pop = engine.initialize_population()
        crossed = engine.crossover(pop)
        assert crossed.size == pop.size * 2  # Each pair produces 2 children
