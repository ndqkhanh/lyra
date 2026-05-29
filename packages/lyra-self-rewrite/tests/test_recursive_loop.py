"""Tests for the recursive self-improvement loop."""

from __future__ import annotations

import pytest
from lyra_self_rewrite.exceptions import ConvergenceError, RecursionError
from lyra_self_rewrite.hyper_agent import (
    AgentGene,
    HyperAgent,
    HyperAgentEngine,
    Population,
)
from lyra_self_rewrite.recursive_loop import (
    LoopConfig,
    LoopIteration,
    LoopResult,
    RecursiveLoop,
)


def _make_population(size: int = 5) -> Population:
    agents: list[HyperAgent] = []
    for i in range(size):
        genes = (
            AgentGene(f"g{i}-1", "speed", 0.1 * i, 0.0, 1.0),
            AgentGene(f"g{i}-2", "creativity", 0.2 * i, 0.0, 1.0),
        )
        agents.append(HyperAgent(
            agent_id=f"a{i}",
            genome=genes,
            fitness=0.1 * i,
            generation=0,
            lineage=(f"a{i}",),
        ))
    return Population(
        agents=tuple(agents),
        generation=0,
        best_fitness=0.4,
        avg_fitness=0.2,
        diversity=0.5,
    )


class TestLoopConfig:
    def test_config_defaults(self) -> None:
        config = LoopConfig()
        assert config.max_iterations == 10
        assert config.convergence_threshold == 0.01
        assert config.improvement_min_delta == 0.001
        assert config.stagnation_limit == 3

    def test_config_custom(self) -> None:
        config = LoopConfig(
            max_iterations=5,
            convergence_threshold=0.05,
            stagnation_limit=2,
        )
        assert config.max_iterations == 5
        assert config.stagnation_limit == 2


class TestLoopIteration:
    def test_iteration_creation(self) -> None:
        pop = _make_population(1)
        iteration = LoopIteration(
            iteration=0,
            population=pop,
            best_fitness=0.5,
            improvement_delta=0.5,
            converged=False,
        )
        assert iteration.iteration == 0
        assert iteration.best_fitness == 0.5
        assert not iteration.converged

    def test_iteration_frozen(self) -> None:
        pop = _make_population(1)
        iteration = LoopIteration(0, pop, 0.5, 0.5, False)
        with pytest.raises(AttributeError):
            iteration.converged = True  # type: ignore[misc]

    def test_iteration_converged_true(self) -> None:
        pop = _make_population(1)
        iteration = LoopIteration(0, pop, 0.5, 0.001, True)
        assert iteration.converged


class TestLoopResult:
    def test_result_creation(self) -> None:
        pop = _make_population(1)
        champion = pop.agents[0]
        iterations = (
            LoopIteration(0, pop, 0.5, 0.5, False),
        )
        result = LoopResult(
            iterations=iterations,
            final_population=pop,
            champion=champion,
            converged=False,
            total_cycles=1,
            final_fitness=0.5,
        )
        assert result.total_cycles == 1
        assert result.final_fitness == 0.5

    def test_result_frozen(self) -> None:
        pop = _make_population(1)
        champion = pop.agents[0]
        result = LoopResult((), pop, champion, False, 0, 0.0)
        with pytest.raises(AttributeError):
            result.converged = True  # type: ignore[misc]

    def test_result_converged_true(self) -> None:
        pop = _make_population(1)
        champion = pop.agents[0]
        result = LoopResult((), pop, champion, True, 5, 0.9)
        assert result.converged
        assert result.total_cycles == 5


class TestRecursiveLoop:
    @pytest.mark.asyncio
    async def test_run_loop_basic(self) -> None:
        loop = RecursiveLoop()
        pop = _make_population(size=5)
        config = LoopConfig(max_iterations=3)
        result = await loop.run_loop(pop, config)
        assert result.total_cycles > 0
        assert result.final_fitness >= 0.0

    @pytest.mark.asyncio
    async def test_run_loop_empty_population_raises(self) -> None:
        loop = RecursiveLoop()
        empty_pop = Population((), 0, 0.0, 0.0, 0.0)
        config = LoopConfig()
        with pytest.raises(RecursionError, match="empty population"):
            await loop.run_loop(empty_pop, config)

    @pytest.mark.asyncio
    async def test_run_loop_single_agent(self) -> None:
        loop = RecursiveLoop()
        pop = _make_population(size=1)
        config = LoopConfig(max_iterations=2)
        result = await loop.run_loop(pop, config)
        assert result.total_cycles >= 1

    @pytest.mark.asyncio
    async def test_run_loop_convergence(self) -> None:
        """Test loop with very low convergence threshold so it converges quickly."""
        loop = RecursiveLoop()
        pop = _make_population(size=3)
        # Very large threshold to trigger convergence quickly
        config = LoopConfig(
            max_iterations=10,
            convergence_threshold=100.0,
        )
        result = await loop.run_loop(pop, config)
        # Should converge after at most a few iterations (need minimum 2-3)
        assert result.total_cycles <= 4
        assert result.converged

    @pytest.mark.asyncio
    async def test_run_loop_max_iterations(self) -> None:
        loop = RecursiveLoop()
        pop = _make_population(size=3)
        config = LoopConfig(
            max_iterations=2,
            convergence_threshold=0.001,
            improvement_min_delta=0.0,
        )
        result = await loop.run_loop(pop, config)
        assert result.total_cycles == 2

    @pytest.mark.asyncio
    async def test_run_loop_returns_champion(self) -> None:
        loop = RecursiveLoop()
        pop = _make_population(size=5)
        config = LoopConfig(max_iterations=2)
        result = await loop.run_loop(pop, config)
        assert result.champion.agent_id is not None
        assert result.final_fitness >= 0.0

    @pytest.mark.asyncio
    async def test_run_loop_stagnation_limit(self) -> None:
        loop = RecursiveLoop()
        pop = _make_population(size=3)
        config = LoopConfig(
            max_iterations=10,
            convergence_threshold=0.001,
            improvement_min_delta=100.0,  # Always below this
            stagnation_limit=2,  # Stagnate after 2 iterations
        )
        result = await loop.run_loop(pop, config)
        # Should stop early due to stagnation
        assert result.total_cycles < 10

    @pytest.mark.asyncio
    async def test_run_loop_first_iteration_stagnation_raises(self) -> None:
        """Stagnation at first iteration should raise."""
        loop = RecursiveLoop()
        pop = _make_population(size=3)
        config = LoopConfig(
            max_iterations=10,
            convergence_threshold=0.001,
            improvement_min_delta=1.0,
            stagnation_limit=1,
        )
        # This will try to raise ConvergenceError because stagnation at iteration 0
        with pytest.raises(ConvergenceError):
            await loop.run_loop(pop, config)

    @pytest.mark.asyncio
    async def test_check_convergence_insufficient_history(self) -> None:
        loop = RecursiveLoop()
        assert not await loop.check_convergence((), 0.01)

    @pytest.mark.asyncio
    async def test_check_convergence_single_entry(self) -> None:
        loop = RecursiveLoop()
        pop = _make_population(1)
        iteration = LoopIteration(0, pop, 0.5, 0.5, False)
        assert not await loop.check_convergence((iteration,), 0.01)

    @pytest.mark.asyncio
    async def test_check_convergence_achieved(self) -> None:
        loop = RecursiveLoop()
        pop = _make_population(1)
        # All 3 iterations have small improvement deltas below threshold 0.05
        iterations = (
            LoopIteration(0, pop, 0.5, 0.001, False),
            LoopIteration(1, pop, 0.51, 0.002, False),
            LoopIteration(2, pop, 0.511, 0.001, False),
        )
        # With threshold 0.05, all recent deltas < 0.05 -> converged
        assert await loop.check_convergence(iterations, 0.05)

    @pytest.mark.asyncio
    async def test_check_convergence_not_achieved(self) -> None:
        loop = RecursiveLoop()
        pop = _make_population(1)
        iterations = (
            LoopIteration(0, pop, 0.5, 0.5, False),
            LoopIteration(1, pop, 0.6, 0.1, False),
            LoopIteration(2, pop, 0.9, 0.3, False),
        )
        assert not await loop.check_convergence(iterations, 0.01)

    @pytest.mark.asyncio
    async def test_detect_stagnation(self) -> None:
        loop = RecursiveLoop()
        pop = _make_population(1)
        iterations = (
            LoopIteration(0, pop, 0.5, 0.5, False),
            LoopIteration(1, pop, 0.5, 0.0, False),
            LoopIteration(2, pop, 0.5, 0.0, False),
        )
        assert await loop.detect_stagnation(iterations, limit=1)

    @pytest.mark.asyncio
    async def test_detect_stagnation_not_stagnated(self) -> None:
        loop = RecursiveLoop()
        pop = _make_population(1)
        iterations = (
            LoopIteration(0, pop, 0.5, 0.5, False),
            LoopIteration(1, pop, 0.6, 0.1, False),
        )
        assert not await loop.detect_stagnation(iterations, limit=2)

    @pytest.mark.asyncio
    async def test_detect_stagnation_insufficient_history(self) -> None:
        loop = RecursiveLoop()
        pop = _make_population(1)
        iteration = LoopIteration(0, pop, 0.5, 0.5, False)
        assert not await loop.detect_stagnation((iteration,), limit=2)

    @pytest.mark.asyncio
    async def test_run_loop_with_custom_engine(self) -> None:
        engine = HyperAgentEngine()
        loop = RecursiveLoop(engine=engine)
        pop = _make_population(size=3)
        config = LoopConfig(max_iterations=2)
        result = await loop.run_loop(pop, config)
        assert result.total_cycles > 0

    @pytest.mark.asyncio
    async def test_run_loop_champion_is_best(self) -> None:
        loop = RecursiveLoop()
        pop = _make_population(size=5)
        config = LoopConfig(max_iterations=2)
        result = await loop.run_loop(pop, config)
        # Champion should be one of the agents
        assert result.champion in result.final_population.agents

    @pytest.mark.asyncio
    async def test_run_loop_multiple_evolutions(self) -> None:
        loop = RecursiveLoop()
        pop = _make_population(size=4)
        config = LoopConfig(max_iterations=5)
        result = await loop.run_loop(pop, config)
        # Should have evolved to at least generation 1
        final_generation = result.final_population.generation
        assert final_generation >= 1

    @pytest.mark.asyncio
    async def test_run_loop_improvement_tracking(self) -> None:
        loop = RecursiveLoop()
        pop = _make_population(size=3)
        config = LoopConfig(max_iterations=3)
        result = await loop.run_loop(pop, config)
        # Verify we have iteration data
        assert len(result.iterations) > 0
        for iteration in result.iterations:
            assert iteration.population is not None
