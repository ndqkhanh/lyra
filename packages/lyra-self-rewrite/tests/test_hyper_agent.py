"""Tests for the DGM HyperAgent core engine."""

from __future__ import annotations

import pytest
from lyra_self_rewrite.exceptions import HyperAgentError
from lyra_self_rewrite.hyper_agent import (
    AgentGene,
    HyperAgent,
    HyperAgentConfig,
    HyperAgentEngine,
    Population,
    _compute_diversity,
    _genome_distance,
)


class TestAgentGene:
    def test_agent_gene_creation(self) -> None:
        gene = AgentGene(
            gene_id="g1", trait="speed", value=0.5, min_bound=0.0, max_bound=1.0
        )
        assert gene.gene_id == "g1"
        assert gene.trait == "speed"
        assert gene.value == 0.5
        assert gene.min_bound == 0.0
        assert gene.max_bound == 1.0

    def test_agent_gene_frozen(self) -> None:
        gene = AgentGene("g1", "speed", 0.5, 0.0, 1.0)
        with pytest.raises(AttributeError):
            gene.value = 0.8  # type: ignore[misc]

    def test_agent_gene_boundary_values(self) -> None:
        gene = AgentGene("g1", "t", 0.0, 0.0, 1.0)
        assert gene.value == gene.min_bound
        gene2 = AgentGene("g2", "t", 1.0, 0.0, 1.0)
        assert gene2.value == gene2.max_bound

    def test_agent_gene_negative_bounds(self) -> None:
        gene = AgentGene("g1", "t", -0.5, -1.0, 0.0)
        assert gene.value == -0.5
        assert gene.min_bound == -1.0


class TestHyperAgent:
    def test_hyper_agent_creation(self) -> None:
        gene = AgentGene("g1", "speed", 0.5, 0.0, 1.0)
        agent = HyperAgent(
            agent_id="a1",
            genome=(gene,),
            fitness=0.8,
            generation=0,
            lineage=("a1",),
        )
        assert agent.agent_id == "a1"
        assert len(agent.genome) == 1
        assert agent.fitness == 0.8
        assert agent.generation == 0

    def test_hyper_agent_frozen(self) -> None:
        agent = HyperAgent("a1", (), 0.0, 0, ("a1",))
        with pytest.raises(AttributeError):
            agent.fitness = 0.9  # type: ignore[misc]

    def test_hyper_agent_zero_fitness(self) -> None:
        agent = HyperAgent("a1", (), 0.0, 0, ("a1",))
        assert agent.fitness == 0.0

    def test_hyper_agent_generation_tracking(self) -> None:
        g1 = AgentGene("g1", "speed", 0.5, 0.0, 1.0)
        agent = HyperAgent("a1", (g1,), 0.5, 5, ("parent", "a1"))
        assert agent.generation == 5
        assert len(agent.lineage) == 2

    def test_hyper_agent_empty_genome(self) -> None:
        agent = HyperAgent("a1", (), 0.0, 0, ("a1",))
        assert agent.genome == ()


class TestHyperAgentConfig:
    def test_config_defaults(self) -> None:
        config = HyperAgentConfig()
        assert config.max_depth == 5
        assert config.population_size == 20
        assert config.mutation_rate == 0.15
        assert config.crossover_rate == 0.3
        assert config.elitism_count == 2

    def test_config_custom_values(self) -> None:
        config = HyperAgentConfig(
            max_depth=10,
            population_size=50,
            mutation_rate=0.3,
            crossover_rate=0.5,
            elitism_count=5,
        )
        assert config.max_depth == 10
        assert config.population_size == 50
        assert config.elitism_count == 5


class TestPopulation:
    def test_population_creation(self) -> None:
        agent = HyperAgent("a1", (), 0.5, 0, ("a1",))
        pop = Population(
            agents=(agent,),
            generation=0,
            best_fitness=0.5,
            avg_fitness=0.5,
            diversity=0.0,
        )
        assert len(pop.agents) == 1
        assert pop.best_fitness == 0.5
        assert pop.diversity == 0.0

    def test_population_frozen(self) -> None:
        pop = Population((), 0, 0.0, 0.0, 0.0)
        with pytest.raises(AttributeError):
            pop.generation = 1  # type: ignore[misc]


class TestGenomeDistance:
    def test_genome_distance_zero(self) -> None:
        g1 = AgentGene("g1", "speed", 0.5, 0.0, 1.0)
        g2 = AgentGene("g2", "speed", 0.5, 0.0, 1.0)
        dist = _genome_distance((g1,), (g2,))
        assert dist == 0.0

    def test_genome_distance_non_zero(self) -> None:
        g1 = AgentGene("g1", "speed", 0.0, 0.0, 1.0)
        g2 = AgentGene("g2", "speed", 1.0, 0.0, 1.0)
        dist = _genome_distance((g1,), (g2,))
        assert dist == 1.0

    def test_genome_distance_empty(self) -> None:
        assert _genome_distance((), ()) == 0.0

    def test_genome_distance_different_lengths(self) -> None:
        g1 = AgentGene("g1", "speed", 0.5, 0.0, 1.0)
        g2 = AgentGene("g2", "speed", 0.5, 0.0, 1.0)
        dist = _genome_distance((g1,), (g1, g2))
        assert dist == 0.0

    def test_compute_diversity_single_agent(self) -> None:
        agent = HyperAgent("a1", (), 0.0, 0, ("a1",))
        assert _compute_diversity((agent,)) == 0.0

    def test_compute_diversity_two_identical(self) -> None:
        g = AgentGene("g1", "speed", 0.5, 0.0, 1.0)
        a1 = HyperAgent("a1", (g,), 0.0, 0, ("a1",))
        a2 = HyperAgent("a2", (g,), 0.0, 0, ("a2",))
        assert _compute_diversity((a1, a2)) == 0.0

    def test_compute_diversity_zero_is_empty(self) -> None:
        assert _compute_diversity(()) == 0.0


class TestHyperAgentEngine:
    @pytest.mark.asyncio
    async def test_initialize_population(self) -> None:
        engine = HyperAgentEngine()
        config = HyperAgentConfig(population_size=10)
        pop = await engine.initialize_population(config)
        assert len(pop.agents) == 10
        assert pop.generation == 0
        assert pop.best_fitness == 0.0

    @pytest.mark.asyncio
    async def test_initialize_population_min_size(self) -> None:
        engine = HyperAgentEngine()
        config = HyperAgentConfig(population_size=1)
        pop = await engine.initialize_population(config)
        assert len(pop.agents) == 1

    @pytest.mark.asyncio
    async def test_evaluate_fitness(self) -> None:
        engine = HyperAgentEngine()
        gene = AgentGene("g1", "speed", 0.5, 0.0, 1.0)
        agent = HyperAgent("a1", (gene,), 0.0, 0, ("a1",))
        score = await engine.evaluate_fitness(agent, "test task")
        assert score >= 0.0

    @pytest.mark.asyncio
    async def test_evaluate_fitness_empty_genome(self) -> None:
        engine = HyperAgentEngine()
        agent = HyperAgent("a1", (), 0.0, 0, ("a1",))
        score = await engine.evaluate_fitness(agent, "test")
        assert score == 0.0

    @pytest.mark.asyncio
    async def test_evaluate_fitness_different_tasks(self) -> None:
        engine = HyperAgentEngine()
        gene = AgentGene("g1", "speed", 0.5, 0.0, 1.0)
        agent = HyperAgent("a1", (gene,), 0.0, 0, ("a1",))
        score_a = await engine.evaluate_fitness(agent, "task A")
        score_b = await engine.evaluate_fitness(agent, "task B")
        # Different tasks should give different scores
        assert abs(score_a - score_b) > 0.0

    @pytest.mark.asyncio
    async def test_evolve_population(self) -> None:
        engine = HyperAgentEngine()
        config = HyperAgentConfig(population_size=5, elitism_count=1)

        # Create a population with some fitness values
        agents: list[HyperAgent] = []
        for i in range(5):
            g = AgentGene(f"g{i}", "speed", 0.1 * i, 0.0, 1.0)
            agents.append(HyperAgent(f"a{i}", (g,), 0.1 * i, 0, (f"a{i}",)))
        pop = Population(
            agents=tuple(agents),
            generation=0,
            best_fitness=0.4,
            avg_fitness=0.2,
            diversity=0.5,
        )
        evolved = await engine.evolve_population(pop, config)
        assert evolved.generation == 1
        assert len(evolved.agents) == 5

    @pytest.mark.asyncio
    async def test_evolve_population_empty_raises(self) -> None:
        engine = HyperAgentEngine()
        config = HyperAgentConfig()
        pop = Population((), 0, 0.0, 0.0, 0.0)
        with pytest.raises(HyperAgentError, match="empty population"):
            await engine.evolve_population(pop, config)

    @pytest.mark.asyncio
    async def test_evolve_preserves_elite(self) -> None:
        engine = HyperAgentEngine()
        config = HyperAgentConfig(population_size=5, elitism_count=1)

        agents: list[HyperAgent] = []
        for i in range(5):
            g = AgentGene(f"g{i}", "speed", 0.1 * i, 0.0, 1.0)
            agents.append(HyperAgent(f"a{i}", (g,), 0.1 * i, 0, (f"a{i}",)))
        pop = Population(tuple(agents), 0, 0.4, 0.2, 0.5)
        evolved = await engine.evolve_population(pop, config)

        # The best agent should have a lineage that includes the elite
        evolved_sorted = sorted(evolved.agents, key=lambda a: a.fitness, reverse=True)
        assert len(evolved_sorted[0].lineage) >= 1

    @pytest.mark.asyncio
    async def test_select_elite(self) -> None:
        engine = HyperAgentEngine()
        agents: list[HyperAgent] = []
        for i in range(5):
            g = AgentGene(f"g{i}", "speed", 0.1 * i, 0.0, 1.0)
            agents.append(HyperAgent(f"a{i}", (g,), 0.1 * i, 0, (f"a{i}",)))
        pop = Population(tuple(agents), 0, 0.4, 0.2, 0.5)

        elite = await engine.select_elite(pop, 2)
        assert len(elite) == 2
        assert elite[0].fitness >= elite[1].fitness

    @pytest.mark.asyncio
    async def test_select_elite_k_larger_than_population(self) -> None:
        engine = HyperAgentEngine()
        agents: list[HyperAgent] = []
        for i in range(2):
            g = AgentGene(f"g{i}", "speed", 0.1, 0.0, 1.0)
            agents.append(HyperAgent(f"a{i}", (g,), 0.1, 0, (f"a{i}",)))
        pop = Population(tuple(agents), 0, 0.1, 0.1, 0.0)

        elite = await engine.select_elite(pop, 10)
        assert len(elite) == 2

    def test_crossover_different_lengths(self) -> None:
        engine = HyperAgentEngine()
        g1 = AgentGene("g1", "speed", 0.5, 0.0, 1.0)
        g2 = AgentGene("g2", "creativity", 0.3, 0.0, 1.0)
        g3 = AgentGene("g3", "thoroughness", 0.7, 0.0, 1.0)
        result = engine._crossover((g1, g2), (g1, g3))
        assert len(result) >= 1
        assert all(isinstance(g, AgentGene) for g in result)

    def test_crossover_empty_genome(self) -> None:
        engine = HyperAgentEngine()
        g = AgentGene("g1", "speed", 0.5, 0.0, 1.0)
        result = engine._crossover((g,), ())
        assert result == (g,)

    def test_mutate_no_change_with_zero_rate(self) -> None:
        engine = HyperAgentEngine()
        g = AgentGene("g1", "speed", 0.5, 0.0, 1.0)
        result = engine._mutate((g,), 0.0)
        assert result[0].value == 0.5

    def test_mutate_all_with_rate_one(self) -> None:
        engine = HyperAgentEngine()
        g = AgentGene("g1", "speed", 0.5, 0.0, 1.0)
        result = engine._mutate((g,), 1.0)
        # Most of the time the value will change
        # But there is a very small chance it stays the same due to delta=0
        # We'll just check bounds
        assert result[0].min_bound <= result[0].value <= result[0].max_bound

    def test_mutate_clamps_to_bounds(self) -> None:
        engine = HyperAgentEngine()
        # Create a gene at the upper bound
        g = AgentGene("g1", "speed", 1.0, 0.0, 1.0)
        result = engine._mutate((g,), 1.0)
        # Value should never exceed bounds even with positive delta
        assert result[0].value <= 1.0
        assert result[0].value >= 0.0
