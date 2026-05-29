"""Tests for strategy_evolver, prompt_mutator, fitness_evaluator, and lineage_tracker."""

from __future__ import annotations

from lyra_cli.evolution.fitness_evaluator import (
    FitnessEvaluator,
    FitnessTarget,
)
from lyra_cli.evolution.lineage_tracker import (
    EventType,
    LineageTracker,
)
from lyra_cli.evolution.prompt_mutator import (
    MutationOp,
    PromptMutator,
)
from lyra_cli.evolution.strategy_evolver import (
    GeneType,
    StrategyEvolver,
    StrategyGene,
)


class TestStrategyGene:
    def test_create_gene(self):
        g = StrategyGene(
            gene_type=GeneType.EXPLORATION,
            value=0.5,
            mutation_rate=0.1,
            min_bound=0.0,
            max_bound=1.0,
        )
        assert g.value == 0.5
        assert g.gene_type == GeneType.EXPLORATION

    def test_mutate_changes_value(self):
        g = StrategyGene(
            gene_type=GeneType.EXPLORATION,
            value=0.5,
            mutation_rate=1.0,
            min_bound=0.0,
            max_bound=1.0,
        )
        mutated = g.mutate()
        assert mutated.gene_type == g.gene_type

    def test_mutate_respects_bounds(self):
        g = StrategyGene(
            gene_type=GeneType.CONSERVATISM,
            value=0.0,
            mutation_rate=1.0,
            min_bound=0.0,
            max_bound=1.0,
        )
        for _ in range(50):
            g = g.mutate()
        assert 0.0 <= g.value <= 1.0


class TestStrategyEvolver:
    def test_initialize_population(self):
        evolver = StrategyEvolver(population_size=10, elite_count=2)
        pop = evolver.initialize()
        assert len(pop) == 10
        for s in pop:
            assert len(s.genes) == 4

    def test_evolve_preserves_population_size(self):
        evolver = StrategyEvolver(population_size=10, elite_count=2)
        evolver.initialize()
        fitness = {f"evo-{i:04d}": 0.5 for i in range(1, 11)}
        new_pop = evolver.evolve(fitness)
        assert len(new_pop) == 10

    def test_evolve_empty_initializes(self):
        evolver = StrategyEvolver(population_size=5)
        pop = evolver.evolve({})
        assert len(pop) == 5

    def test_stats(self):
        evolver = StrategyEvolver()
        evolver.initialize()
        s = evolver.stats()
        assert s["population_size"] == 20
        assert s["generation"] == 0


class TestPromptMutator:
    def test_mutate_rephrase(self):
        mutator = PromptMutator()
        results = mutator.mutate("You must always ensure quality.", [MutationOp.REPHRASE])
        assert len(results) == 1
        assert results[0].operation == MutationOp.REPHRASE

    def test_mutate_all_ops_produces_results(self):
        mutator = PromptMutator(similarity_threshold=0.0)
        results = mutator.mutate("First do this. Then do that. Finally do the other thing.")
        assert len(results) > 0

    def test_mutate_reorder_multiple_sentences(self):
        mutator = PromptMutator()
        results = mutator.mutate("First step. Second step. Third step.", [MutationOp.REORDER])
        assert len(results) == 1

    def test_mutate_add_constraint(self):
        mutator = PromptMutator()
        results = mutator.mutate("Analyze the data.", [MutationOp.ADD_CONSTRAINT])
        assert len(results) == 1
        assert "verify your output" in results[0].mutated

    def test_mutate_elaborate(self):
        mutator = PromptMutator()
        results = mutator.mutate("Review the code.", [MutationOp.ELABORATE])
        assert len(results) == 1
        assert "edge cases" in results[0].mutated

    def test_mutate_simplify(self):
        mutator = PromptMutator()
        results = mutator.mutate("First. Second. Third. Fourth. Fifth.", [MutationOp.SIMPLIFY])
        assert len(results) == 1

    def test_mutation_result_fields(self):
        mutator = PromptMutator()
        results = mutator.mutate("Test prompt.", [MutationOp.REPHRASE])
        r = results[0]
        assert r.len_before == len("Test prompt.")
        assert r.similarity_score > 0

    def test_get_history(self):
        mutator = PromptMutator()
        mutator.mutate("Test.", [MutationOp.REPHRASE])
        assert len(mutator.get_history()) == 1

    def test_stats(self):
        mutator = PromptMutator()
        mutator.mutate("Test.", [MutationOp.REPHRASE])
        s = mutator.stats()
        assert s["total_mutations"] == 1


class TestFitnessEvaluator:
    def test_evaluate_meets_all_targets(self):
        evaluator = FitnessEvaluator()
        metrics = {
            "success_rate": 0.95,
            "speed_ms": 300.0,
            "cost_tokens": 500.0,
            "quality_score": 0.9,
        }
        report = evaluator.evaluate("strat-1", metrics)
        assert report.meets_all_targets
        assert report.weighted_score > 0

    def test_evaluate_fails_targets(self):
        evaluator = FitnessEvaluator()
        metrics = {
            "success_rate": 0.5,
            "speed_ms": 2000.0,
            "cost_tokens": 2000.0,
            "quality_score": 0.3,
        }
        report = evaluator.evaluate("strat-2", metrics)
        assert not report.meets_all_targets

    def test_evaluate_custom_targets(self):
        targets = [
            FitnessTarget(name="accuracy", weight=1.0, target_value=0.95, higher_is_better=True)
        ]
        evaluator = FitnessEvaluator(targets=targets)
        report = evaluator.evaluate("s1", {"accuracy": 0.97})
        assert report.meets_all_targets

    def test_get_best(self):
        evaluator = FitnessEvaluator()
        evaluator.evaluate(
            "a",
            {"success_rate": 0.9, "speed_ms": 400.0, "cost_tokens": 800.0, "quality_score": 0.9},
        )
        evaluator.evaluate(
            "b",
            {"success_rate": 0.5, "speed_ms": 2000.0, "cost_tokens": 3000.0, "quality_score": 0.3},
        )
        best = evaluator.get_best()
        assert best is not None
        assert best.strategy_id == "a"

    def test_get_history(self):
        evaluator = FitnessEvaluator()
        evaluator.evaluate(
            "s1",
            {"success_rate": 0.8, "speed_ms": 600.0, "cost_tokens": 900.0, "quality_score": 0.8},
        )
        evaluator.evaluate(
            "s1",
            {"success_rate": 0.9, "speed_ms": 400.0, "cost_tokens": 700.0, "quality_score": 0.9},
        )
        history = evaluator.get_history("s1")
        assert len(history) == 2

    def test_normalize_higher_is_better(self):
        evaluator = FitnessEvaluator()
        report = evaluator.evaluate(
            "s1",
            {"success_rate": 0.9, "speed_ms": 500.0, "cost_tokens": 1000.0, "quality_score": 0.85},
        )
        assert report.scores["success_rate"] == 1.0

    def test_stats(self):
        evaluator = FitnessEvaluator()
        evaluator.evaluate(
            "s1",
            {"success_rate": 0.9, "speed_ms": 500.0, "cost_tokens": 1000.0, "quality_score": 0.85},
        )
        s = evaluator.stats()
        assert s["strategies_evaluated"] == 1


class TestLineageTracker:
    def test_record_birth(self):
        tracker = LineageTracker()
        event = tracker.record_birth("strat-1", 0)
        assert event.event_type == EventType.BIRTH
        assert event.strategy_id == "strat-1"

    def test_record_mutation(self):
        tracker = LineageTracker()
        tracker.record_birth("parent", 0)
        event = tracker.record_mutation("child", 1, "parent")
        assert event.event_type == EventType.MUTATION
        assert event.parent_ids == ["parent"]

    def test_record_crossover(self):
        tracker = LineageTracker()
        tracker.record_birth("p1", 0)
        tracker.record_birth("p2", 0)
        event = tracker.record_crossover("child", 1, ["p1", "p2"])
        assert event.parent_ids == ["p1", "p2"]

    def test_record_selection(self):
        tracker = LineageTracker()
        tracker.record_birth("s", 0)
        event = tracker.record_selection("s", 0, 0.95)
        assert event.event_type == EventType.SELECTION
        assert event.fitness == 0.95

    def test_record_extinction(self):
        tracker = LineageTracker()
        tracker.record_birth("s", 0)
        event = tracker.record_extinction("s", 1)
        assert event.event_type == EventType.EXTINCTION

    def test_record_promotion(self):
        tracker = LineageTracker()
        tracker.record_birth("s", 0)
        event = tracker.record_promotion("s", 2, 0.88)
        assert event.event_type == EventType.PROMOTION

    def test_get_ancestry(self):
        tracker = LineageTracker()
        tracker.record_birth("root", 0)
        tracker.record_mutation("gen1", 1, "root")
        tracker.record_mutation("gen2", 2, "gen1")
        ancestry = tracker.get_ancestry("gen2")
        assert "root" in ancestry
        assert "gen1" in ancestry

    def test_get_children(self):
        tracker = LineageTracker()
        tracker.record_birth("parent", 0)
        tracker.record_mutation("child1", 1, "parent")
        tracker.record_mutation("child2", 1, "parent")
        children = tracker.get_children("parent")
        assert len(children) == 2

    def test_get_lineage_tree(self):
        tracker = LineageTracker()
        tracker.record_birth("root", 0)
        tracker.record_mutation("a", 1, "root")
        tracker.record_mutation("b", 1, "root")
        tracker.record_selection("root", 0, 0.9)
        tracker.record_selection("a", 1, 0.8)
        tree = tracker.get_lineage_tree("root")
        assert tree.root_id == "root"
        assert tree.generation_count >= 1
        assert tree.total_strategies >= 1

    def test_lineage_tree_no_extinct(self):
        tracker = LineageTracker()
        tracker.record_birth("root", 0)
        tracker.record_extinction("root", 1)
        tree = tracker.get_lineage_tree("root")
        assert tree.active_strategies == 0

    def test_stats(self):
        tracker = LineageTracker()
        tracker.record_birth("s", 0)
        s = tracker.stats()
        assert s["total_events"] == 1
        assert "by_type" in s
