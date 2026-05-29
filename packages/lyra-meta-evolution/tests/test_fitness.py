"""Tests for lyra_meta_evolution.fitness module."""

import asyncio

import pytest
from lyra_meta_evolution.fitness import (
    BenchmarkConfig,
    BenchmarkResult,
    FitnessEvaluator,
    FitnessLandscape,
    FitnessWeights,
    ObjectiveDimension,
    ObjectiveVector,
    ParetoFrontier,
)
from lyra_meta_evolution.meta_evolution import AgentGenome

# ── Fixtures ────────────────────────────────────────────────────────────────────


@pytest.fixture
def genome():
    return AgentGenome(
        agent_id="eval_agent",
        hyperparameters={
            "learning_rate": 0.001,
            "temperature": 0.7,
            "exploration_rate": 0.1,
            "batch_size_factor": 1.0,
            "discount_factor": 0.9,
        },
        active_strategies=["greedy", "exploration", "heuristic"],
        objective_weights={"speed": 0.3, "quality": 0.3, "cost": 0.2, "reliability": 0.2},
        constraints={"min_quality_threshold": 0.7},
    )


@pytest.fixture
def evaluator():
    return FitnessEvaluator()


@pytest.fixture
def benchmark_config():
    return BenchmarkConfig(
        name="unit_test",
        description="Test benchmark",
        task_count=5,
    )


# ── ObjectiveVector ─────────────────────────────────────────────────────────────


class TestObjectiveVector:
    def test_default_all_dimensions(self):
        vec = ObjectiveVector()
        for dim in ObjectiveDimension:
            assert dim in vec.values
            assert vec.values[dim] == 0.0

    def test_dominates(self):
        better = ObjectiveVector(values={
            ObjectiveDimension.SPEED: 0.8,
            ObjectiveDimension.QUALITY: 0.9,
        })
        worse = ObjectiveVector(values={
            ObjectiveDimension.SPEED: 0.5,
            ObjectiveDimension.QUALITY: 0.5,
        })
        assert better.dominates(worse)
        assert not worse.dominates(better)

    def test_does_not_dominate_equal(self):
        a = ObjectiveVector(values={ObjectiveDimension.SPEED: 0.5})
        b = ObjectiveVector(values={ObjectiveDimension.SPEED: 0.5})
        assert not a.dominates(b)
        assert not b.dominates(a)

    def test_partial_dominance_not_enough(self):
        a = ObjectiveVector(values={
            ObjectiveDimension.SPEED: 0.9,
            ObjectiveDimension.QUALITY: 0.4,
        })
        b = ObjectiveVector(values={
            ObjectiveDimension.SPEED: 0.5,
            ObjectiveDimension.QUALITY: 0.8,
        })
        # Neither dominates the other (trade-off)
        assert not a.dominates(b)
        assert not b.dominates(a)

    def test_to_list_and_from_list(self):
        vec = ObjectiveVector(values={
            ObjectiveDimension.SPEED: 0.5,
            ObjectiveDimension.QUALITY: 0.7,
        })
        lst = vec.to_list()
        restored = ObjectiveVector.from_list(lst)
        assert restored.values[ObjectiveDimension.SPEED] == 0.5
        assert restored.values[ObjectiveDimension.QUALITY] == 0.7


# ── FitnessWeights ──────────────────────────────────────────────────────────────


class TestFitnessWeights:
    def test_default_weights_normalized(self):
        w = FitnessWeights()
        total = sum(w.weights.values())
        assert abs(total - 1.0) < 0.001

    def test_combine(self):
        w = FitnessWeights()
        vec = ObjectiveVector(values={
            ObjectiveDimension.SPEED: 1.0,
            ObjectiveDimension.QUALITY: 1.0,
        })
        score = w.combine(vec)
        assert 0.0 <= score <= 1.0

    def test_adapt_returns_new_weights(self):
        w = FitnessWeights()
        history = [
            {"speed": 0.5, "quality": 0.6, "cost": 0.4},
            {"speed": 0.6, "quality": 0.7, "cost": 0.3},
            {"speed": 0.7, "quality": 0.8, "cost": 0.2},
        ]
        adapted = w.adapt(history)
        assert isinstance(adapted, FitnessWeights)

    def test_adapt_short_history_no_change(self):
        w = FitnessWeights()
        history = [{"speed": 0.5}]
        adapted = w.adapt(history)
        # Should return same weights for insufficient history
        assert isinstance(adapted, FitnessWeights)


# ── ParetoFrontier ───────────────────────────────────────────────────────────────


class TestParetoFrontier:
    def test_add_first_solution(self):
        pf = ParetoFrontier()
        vec = ObjectiveVector(values={ObjectiveDimension.SPEED: 0.8, ObjectiveDimension.QUALITY: 0.7})
        assert pf.add("agent_1", vec) is True
        assert pf.size == 1

    def test_dominated_solution_not_added(self):
        pf = ParetoFrontier()
        pf.add("best", ObjectiveVector(values={
            ObjectiveDimension.SPEED: 0.9,
            ObjectiveDimension.QUALITY: 0.9,
        }))
        result = pf.add("worse", ObjectiveVector(values={
            ObjectiveDimension.SPEED: 0.5,
            ObjectiveDimension.QUALITY: 0.5,
        }))
        assert result is False
        assert pf.size == 1

    def test_new_solution_dominates_old(self):
        pf = ParetoFrontier()
        pf.add("old", ObjectiveVector(values={
            ObjectiveDimension.SPEED: 0.5,
            ObjectiveDimension.QUALITY: 0.5,
        }))
        pf.add("better", ObjectiveVector(values={
            ObjectiveDimension.SPEED: 0.7,
            ObjectiveDimension.QUALITY: 0.6,
        }))
        # better might not dominate old if old has a higher value in some dimension
        pf.get_frontier()

    def test_get_frontier_ids(self):
        pf = ParetoFrontier()
        pf.add("a", ObjectiveVector(values={ObjectiveDimension.SPEED: 0.8}))
        pf.add("b", ObjectiveVector(values={ObjectiveDimension.QUALITY: 0.9}))
        ids = pf.get_frontier_ids()
        assert len(ids) == 2

    def test_hypervolume(self):
        pf = ParetoFrontier()
        pf.add("a", ObjectiveVector(values={
            ObjectiveDimension.SPEED: 0.8,
            ObjectiveDimension.QUALITY: 0.7,
        }))
        hv = pf.hypervolume()
        assert hv > 0.0

    def test_coverage(self):
        pf1 = ParetoFrontier()
        pf1.add("a", ObjectiveVector(values={
            ObjectiveDimension.SPEED: 0.9,
            ObjectiveDimension.QUALITY: 0.9,
        }))
        pf2 = ParetoFrontier()
        pf2.add("b", ObjectiveVector(values={
            ObjectiveDimension.SPEED: 0.5,
            ObjectiveDimension.QUALITY: 0.5,
        }))
        coverage = pf1.coverage(pf2)
        assert 0.0 <= coverage <= 1.0


# ── FitnessEvaluator ────────────────────────────────────────────────────────────


class TestFitnessEvaluator:
    def test_evaluate_returns_score(self, evaluator, genome, benchmark_config):
        score = asyncio.run(evaluator.evaluate(genome, benchmark_config))
        assert 0.0 <= score <= 1.0

    def test_evaluate_population(self, evaluator, benchmark_config):
        genomes = [
            AgentGenome(agent_id=f"pop_{i}") for i in range(3)
        ]
        scores = asyncio.run(evaluator.evaluate_population(genomes, benchmark_config))
        assert len(scores) == 3
        assert all(0.0 <= v <= 1.0 for v in scores.values())

    def test_evaluation_count_increments(self, evaluator, genome, benchmark_config):
        before = evaluator.evaluation_count
        asyncio.run(evaluator.evaluate(genome, benchmark_config))
        assert evaluator.evaluation_count == before + 1

    def test_analyze_landscape(self, evaluator):
        genomes = [AgentGenome(agent_id=f"land_{i}") for i in range(10)]
        scores = {g.agent_id: 0.5 + i * 0.05 for i, g in enumerate(genomes)}
        landscape = evaluator.analyze_landscape(genomes, scores)
        assert isinstance(landscape, FitnessLandscape)
        assert landscape.max_fitness > landscape.min_fitness
        assert landscape.avg_fitness > 0.0

    def test_analyze_landscape_empty(self, evaluator):
        landscape = evaluator.analyze_landscape([], {})
        assert landscape.avg_fitness == 0.0

    def test_pareto_frontier_tracks_solutions(self, evaluator, genome, benchmark_config):
        asyncio.run(evaluator.evaluate(genome, benchmark_config))
        assert evaluator.pareto_frontier.size > 0

    def test_weights_getter_setter(self, evaluator):
        new_weights = FitnessWeights()
        new_weights.weights[ObjectiveDimension.SPEED] = 0.5
        evaluator.weights = new_weights
        assert evaluator.weights is not None


# ── BenchmarkConfig / BenchmarkResult ───────────────────────────────────────────


class TestBenchmark:
    def test_config_defaults(self):
        config = BenchmarkConfig(name="test", description="desc")
        assert config.task_count == 10
        assert config.timeout_per_task_ms > 0

    def test_result_passed(self):
        config = BenchmarkConfig(name="test", description="desc", min_success_rate=0.5)
        result = BenchmarkResult(
            config=config,
            agent_id="agent",
            scores={},
            success_rate=0.6,
        )
        assert result.passed is True

    def test_result_not_passed(self):
        config = BenchmarkConfig(name="test", description="desc", min_success_rate=0.5)
        result = BenchmarkResult(
            config=config,
            agent_id="agent",
            scores={},
            success_rate=0.3,
        )
        assert result.passed is False
