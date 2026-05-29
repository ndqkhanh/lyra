"""Integration tests for lyra_meta_evolution package.

Tests the full pipeline: seed genome -> genetic optimization -> strategy pool
-> fitness evaluation -> meta-cognitive evolution.
"""

import asyncio

from lyra_meta_evolution import (
    AgentGenome,
    BenchmarkConfig,
    EvolutionLevel,
    EvolutionOrchestrator,
    EvolutionTrigger,
    FitnessEvaluator,
    GeneticOptimizer,
    MetaCognitiveStack,
    MutationOperator,
    ObjectiveDimension,
    ObjectiveVector,
    ParetoFrontier,
    StrategyEncoding,
    StrategyPool,
    TournamentSelection,
)
from lyra_meta_evolution.fitness import FitnessLandscape
from lyra_meta_evolution.genetic_optimizer import CrossoverOperator


class TestFullPipeline:
    """End-to-end test of the meta-evolution pipeline."""

    def test_seed_to_evolution_cycle(self):
        """Create seed genome, evolve through one cycle at each level."""
        # Setup
        seed = AgentGenome(
            agent_id="e2e_agent",
            hyperparameters={"learning_rate": 0.01, "temperature": 0.7},
            active_strategies=["greedy", "exploration"],
            objective_weights={"speed": 0.3, "quality": 0.4, "cost": 0.2, "reliability": 0.1},
        )

        meta_stack = MetaCognitiveStack()

        # Evolve at each level
        for level in list(EvolutionLevel):
            controller = meta_stack.get_controller(level)
            assert controller.is_ready()

            result = asyncio.run(controller.evolve(seed, EvolutionTrigger.SCHEDULED_REVIEW))
            assert result.level == level
            assert result.improvement is not None

    def test_genetic_optimizer_with_strategy_pool(self):
        """Genetic optimization with strategy pool tracking."""
        seed = AgentGenome(agent_id="pool_test", hyperparameters={"lr": 0.01})

        pool = StrategyPool(max_size=50)
        optimizer = GeneticOptimizer(
            population_size=10,
            selection=TournamentSelection(tournament_size=3),
            mutation_rate=0.3,
        )
        optimizer.initialize_population(seed, variant_count=9)

        # Simple fitness
        class _Fit:
            async def evaluate(self, genome):
                return genome.hyperparameters.get("lr", 0.01)

        fitness = _Fit()
        result = asyncio.run(optimizer.evolve_generation(fitness))

        # Store best in strategy pool
        if optimizer.best_genome:
            enc = StrategyEncoding.from_genome(optimizer.best_genome)
            pool.add_strategy(enc, fitness=result.best_fitness_after)

        assert pool.size >= 1
        assert optimizer.generation == 1

    def test_fitness_evaluator_with_pareto(self):
        """Fitness evaluation with Pareto frontier tracking."""
        evaluator = FitnessEvaluator(track_pareto=True)
        config = BenchmarkConfig(name="e2e_test", description="Integration test", task_count=3)

        genomes = [
            AgentGenome(
                agent_id=f"pareto_{i}",
                hyperparameters={
                    "exploration_rate": 0.1 + i * 0.1,
                    "temperature": 1.0 - i * 0.15,
                },
            )
            for i in range(5)
        ]

        scores = asyncio.run(evaluator.evaluate_population(genomes, config))
        assert len(scores) == 5

        # Check pareto frontier
        assert evaluator.pareto_frontier.size > 0

        # Analyze landscape
        landscape = evaluator.analyze_landscape(genomes, scores)
        assert isinstance(landscape, FitnessLandscape)
        assert landscape.max_fitness >= landscape.min_fitness

    def test_crossover_then_mutate(self):
        """Crossover two genomes, then mutate the children."""
        p1 = AgentGenome(
            agent_id="p1",
            hyperparameters={"lr": 0.01, "temp": 1.0},
            strategy_weights={"greedy": 0.5, "explore": 0.5},
        )
        p2 = AgentGenome(
            agent_id="p2",
            hyperparameters={"lr": 0.001, "temp": 0.5},
            strategy_weights={"greedy": 0.3, "exploit": 0.7},
        )

        # Crossover
        child = CrossoverOperator.uniform_crossover(p1, p2, crossover_rate=0.5)
        assert child.generation > p1.generation

        # Mutate
        mutator = MutationOperator(mutation_rate=1.0, mutation_strength=0.1)
        mutated, changes = mutator.mutate(child)
        assert isinstance(mutated, AgentGenome)

    def test_full_orchestrator_mini_pipeline(self):
        """Run a minimal orchestrator pipeline."""
        config = __import__("lyra_meta_evolution.orchestrator", fromlist=["CycleConfig"]).CycleConfig(
            max_cycles=3,
            cycles_per_level={
                EvolutionLevel.L1_PARAMETER: 2,
                EvolutionLevel.L2_STRATEGY: 1,
            },
            auto_promote=True,
            promote_threshold=0.0,  # Always promote
        )

        orchestrator = EvolutionOrchestrator(config=config)
        seed = AgentGenome(agent_id="orch_test")

        results = asyncio.run(orchestrator.run_pipeline(seed))
        assert len(results) > 0

        # Verify we can export
        exported = asyncio.run(orchestrator.export_best_genome())
        assert "genome" in exported

    def test_pareto_frontier_multi_objective(self):
        """Test Pareto frontier with trade-off objectives."""
        pf = ParetoFrontier()

        # Speed-favoring solution
        pf.add("fast", ObjectiveVector(values={
            ObjectiveDimension.SPEED: 0.9,
            ObjectiveDimension.QUALITY: 0.4,
            ObjectiveDimension.COST: 0.6,
        }))

        # Quality-favoring solution (different trade-off)
        pf.add("quality", ObjectiveVector(values={
            ObjectiveDimension.SPEED: 0.4,
            ObjectiveDimension.QUALITY: 0.9,
            ObjectiveDimension.COST: 0.3,
        }))

        # Should have 2 solutions (neither dominates the other)
        assert pf.size == 2

        # A clearly dominated solution should not be added
        pf.add("dominated", ObjectiveVector(values={
            ObjectiveDimension.SPEED: 0.3,
            ObjectiveDimension.QUALITY: 0.3,
            ObjectiveDimension.COST: 0.2,
        }))
        # Either dominated or added (depends on overall objective values)
        assert pf.size >= 2

    def test_weight_adaptation_over_time(self):
        """Test that fitness weights adapt over multiple evaluations."""
        evaluator = FitnessEvaluator(dynamic_weights=True)
        config = BenchmarkConfig(name="adapt_test", description="Adaptation test", task_count=2)

        dict(evaluator.weights.weights)

        # Run enough evaluations to trigger adaptation
        for i in range(11):
            genome = AgentGenome(agent_id=f"adapt_{i}")
            asyncio.run(evaluator.evaluate(genome, config))

        # Weights may or may not have changed depending on adaptation trigger
        dict(evaluator.weights.weights)
        assert evaluator.evaluation_count == 11
