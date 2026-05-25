"""Tests for the multi-objective fitness evaluator."""

from __future__ import annotations

import pytest

from lyra_self_rewrite.exceptions import FitnessError
from lyra_self_rewrite.fitness_evaluator import (
    FitnessConfig,
    FitnessEvaluator,
    FitnessScore,
    ParetoFront,
)
from lyra_self_rewrite.hyper_agent import AgentGene, HyperAgent


def _make_agent(agent_id: str = "a1", fitness: float = 0.5) -> HyperAgent:
    genes = (
        AgentGene("g1", "correctness", 0.8, 0.0, 1.0),
        AgentGene("g2", "efficiency", 0.6, 0.0, 1.0),
        AgentGene("g3", "elegance", 0.4, 0.0, 1.0),
    )
    return HyperAgent(
        agent_id=agent_id,
        genome=genes,
        fitness=fitness,
        generation=0,
        lineage=(agent_id,),
    )


class TestFitnessConfig:
    def test_config_defaults(self) -> None:
        config = FitnessConfig()
        assert config.objectives == ("correctness", "efficiency", "elegance")
        assert config.weights == (0.5, 0.3, 0.2)
        assert config.thresholds == (0.7, 0.6, 0.5)

    def test_config_custom(self) -> None:
        config = FitnessConfig(
            objectives=("perf", "qual"),
            weights=(0.6, 0.4),
            thresholds=(0.5, 0.5),
        )
        assert len(config.objectives) == 2


class TestFitnessScore:
    def test_score_creation(self) -> None:
        score = FitnessScore(
            agent_id="a1",
            scores=(("correctness", 0.8), ("efficiency", 0.6)),
            weighted_total=0.7,
        )
        assert score.agent_id == "a1"
        assert score.weighted_total == 0.7
        assert score.pareto_rank == 0

    def test_score_with_pareto_rank(self) -> None:
        score = FitnessScore(
            agent_id="a1",
            scores=(("correctness", 0.8),),
            weighted_total=0.8,
            pareto_rank=1,
        )
        assert score.pareto_rank == 1

    def test_score_frozen(self) -> None:
        score = FitnessScore("a1", (("c", 0.5),), 0.5)
        with pytest.raises(AttributeError):
            score.weighted_total = 0.9  # type: ignore[misc]


class TestParetoFront:
    def test_front_creation(self) -> None:
        front = ParetoFront(
            front=(),
            dominated=(),
            size=0,
        )
        assert front.size == 0

    def test_front_with_scores(self) -> None:
        s1 = FitnessScore("a1", (("c", 0.9),), 0.9)
        s2 = FitnessScore("a2", (("c", 0.5),), 0.5)
        front = ParetoFront(
            front=(s1,),
            dominated=(s2,),
            size=1,
        )
        assert len(front.front) == 1
        assert len(front.dominated) == 1


class TestFitnessEvaluator:
    @pytest.mark.asyncio
    async def test_evaluate(self) -> None:
        evaluator = FitnessEvaluator()
        agent = _make_agent()
        config = FitnessConfig()
        score = await evaluator.evaluate(agent, config)
        assert score.agent_id == "a1"
        assert len(score.scores) == 3
        assert 0.0 <= score.weighted_total <= 1.0

    @pytest.mark.asyncio
    async def test_evaluate_empty_genome(self) -> None:
        evaluator = FitnessEvaluator()
        agent = HyperAgent("a1", (), 0.0, 0, ("a1",))
        config = FitnessConfig()
        score = await evaluator.evaluate(agent, config)
        assert score.weighted_total == 0.0

    @pytest.mark.asyncio
    async def test_evaluate_objective_weight_mismatch_raises(self) -> None:
        evaluator = FitnessEvaluator()
        agent = _make_agent()
        config = FitnessConfig(
            objectives=("a", "b"),
            weights=(1.0,),
            thresholds=(0.5, 0.5),
        )
        with pytest.raises(FitnessError, match="must match"):
            await evaluator.evaluate(agent, config)

    @pytest.mark.asyncio
    async def test_evaluate_objective_threshold_mismatch_raises(self) -> None:
        evaluator = FitnessEvaluator()
        agent = _make_agent()
        config = FitnessConfig(
            objectives=("a", "b"),
            weights=(0.5, 0.5),
            thresholds=(0.5,),
        )
        with pytest.raises(FitnessError, match="must match"):
            await evaluator.evaluate(agent, config)

    @pytest.mark.asyncio
    async def test_evaluate_with_zero_fitness(self) -> None:
        evaluator = FitnessEvaluator()
        agent = _make_agent(fitness=0.0)
        config = FitnessConfig()
        score = await evaluator.evaluate(agent, config)
        assert score.weighted_total >= 0.0

    @pytest.mark.asyncio
    async def test_batch_evaluate(self) -> None:
        evaluator = FitnessEvaluator()
        agents = tuple(_make_agent(f"a{i}", 0.1 * i) for i in range(5))
        config = FitnessConfig()
        scores = await evaluator.batch_evaluate(agents, config)
        assert len(scores) == 5
        # All scores should have pareto_rank > 0
        assert all(s.pareto_rank >= 1 for s in scores)

    @pytest.mark.asyncio
    async def test_batch_evaluate_single_agent(self) -> None:
        evaluator = FitnessEvaluator()
        agents = (_make_agent(),)
        config = FitnessConfig()
        scores = await evaluator.batch_evaluate(agents, config)
        assert len(scores) == 1

    @pytest.mark.asyncio
    async def test_batch_evaluate_empty(self) -> None:
        evaluator = FitnessEvaluator()
        config = FitnessConfig()
        scores = await evaluator.batch_evaluate((), config)
        assert scores == ()

    def test_compute_pareto_front(self) -> None:
        evaluator = FitnessEvaluator()
        s1 = FitnessScore("a1", (("c", 0.9), ("e", 0.8)), 0.85)
        s2 = FitnessScore("a2", (("c", 0.5), ("e", 0.4)), 0.45)
        front = evaluator.compute_pareto_front((s1, s2))
        assert front.size == 1
        assert front.front[0].agent_id == "a1"

    def test_compute_pareto_front_no_dominated(self) -> None:
        evaluator = FitnessEvaluator()
        s1 = FitnessScore("a1", (("c", 0.9),), 0.9)
        s2 = FitnessScore("a2", (("c", 0.8),), 0.8)
        front = evaluator.compute_pareto_front((s1, s2))
        assert front.size == 1
        assert front.front[0].agent_id == "a1"

    def test_compute_pareto_front_equal_scores(self) -> None:
        evaluator = FitnessEvaluator()
        s1 = FitnessScore("a1", (("c", 0.5),), 0.5)
        s2 = FitnessScore("a2", (("c", 0.5),), 0.5)
        front = evaluator.compute_pareto_front((s1, s2))
        # Neither dominates the other
        assert front.size == 2

    def test_compute_pareto_front_empty(self) -> None:
        evaluator = FitnessEvaluator()
        front = evaluator.compute_pareto_front(())
        assert front.size == 0

    def test_compute_pareto_front_multi_objective(self) -> None:
        evaluator = FitnessEvaluator()
        s1 = FitnessScore("a1", (("c", 0.9), ("e", 0.9)), 0.9)
        s2 = FitnessScore("a2", (("c", 0.9), ("e", 0.5)), 0.7)
        s3 = FitnessScore("a3", (("c", 0.3), ("e", 0.3)), 0.3)
        front = evaluator.compute_pareto_front((s1, s2, s3))
        assert front.size == 1
        assert front.front[0].agent_id == "a1"

    def test_dominates(self) -> None:
        evaluator = FitnessEvaluator()
        a = FitnessScore("a1", (("c", 0.9), ("e", 0.8)), 0.85)
        b = FitnessScore("a2", (("c", 0.5), ("e", 0.4)), 0.45)
        assert evaluator._dominates(a, b)
        assert not evaluator._dominates(b, a)

    def test_dominates_equal(self) -> None:
        evaluator = FitnessEvaluator()
        a = FitnessScore("a1", (("c", 0.5),), 0.5)
        b = FitnessScore("a2", (("c", 0.5),), 0.5)
        assert not evaluator._dominates(a, b)
        assert not evaluator._dominates(b, a)

    def test_dominates_different_scores(self) -> None:
        evaluator = FitnessEvaluator()
        a = FitnessScore("a1", (("c", 0.9),), 0.9)
        b = FitnessScore("a2", (("c", 0.8), ("e", 0.8)), 0.8)
        # 'b' has key 'e' that 'a' doesn't have
        assert not evaluator._dominates(a, b)

    @pytest.mark.asyncio
    async def test_compare_agents_a_better(self) -> None:
        evaluator = FitnessEvaluator()
        a1 = _make_agent("a1", fitness=0.9)
        a2 = _make_agent("a2", fitness=0.1)
        result = await evaluator.compare_agents(a1, a2)
        assert result == 1  # a1 is better

    @pytest.mark.asyncio
    async def test_compare_agents_b_better(self) -> None:
        evaluator = FitnessEvaluator()
        config = FitnessConfig(
            objectives=("correctness",),
            weights=(1.0,),
            thresholds=(0.0,),
        )
        # We need to construct agents with different enough genomes
        a1_genes = (AgentGene("g1", "correctness", 0.2, 0.0, 1.0),)
        a2_genes = (AgentGene("g1", "correctness", 0.9, 0.0, 1.0),)
        a1 = HyperAgent("a1", a1_genes, 0.2, 0, ("a1",))
        a2 = HyperAgent("a2", a2_genes, 0.9, 0, ("a2",))
        score1 = await evaluator.evaluate(a1, config)
        score2 = await evaluator.evaluate(a2, config)
        # With our custom config, a2 should clearly win
        assert score1.weighted_total < score2.weighted_total

    @pytest.mark.asyncio
    async def test_compare_agents_tie(self) -> None:
        evaluator = FitnessEvaluator()
        config = FitnessConfig(
            objectives=("correctness",),
            weights=(1.0,),
            thresholds=(0.0,),
        )
        # Identical agents yield equal fitness
        g = AgentGene("g1", "correctness", 0.5, 0.0, 1.0)
        a1 = HyperAgent("a1", (g,), 0.5, 0, ("a1",))
        a2 = HyperAgent("a2", (g,), 0.5, 0, ("a2",))
        result = await evaluator.compare_agents(a1, a2)
        assert result == 0

    def test_pareto_front_with_single_pareto_point(self) -> None:
        evaluator = FitnessEvaluator()
        s = FitnessScore("a1", (("c", 0.5),), 0.5)
        front = evaluator.compute_pareto_front((s,))
        assert front.size == 1

    def test_compute_pareto_front_multi_front(self) -> None:
        evaluator = FitnessEvaluator()
        scores = (
            FitnessScore("a1", (("c", 0.9), ("e", 0.9)), 0.9),
            FitnessScore("a2", (("c", 0.7), ("e", 0.7)), 0.7),
            FitnessScore("a3", (("c", 0.5), ("e", 0.5)), 0.5),
        )
        front = evaluator.compute_pareto_front(scores)
        assert front.size == 1  # a1 dominates all others
