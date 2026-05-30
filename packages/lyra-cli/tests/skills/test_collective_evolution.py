"""Tests for SkillClaw Collective Evolution system."""

import pytest

from lyra_cli.skills.evolution.collective_evolver import (
    CollectiveEvolver,
    EvolutionResult,
    GenerationSnapshot,
    SelectionMethod,
)
from lyra_cli.skills.evolution.lineage_tracker import LineageTracker, SkillLineage
from lyra_cli.skills.evolution.recursive_propagator import (
    PropagationResult,
    PropagationStrategy,
    RecursivePropagator,
)


def _default_fitness(name: str, traits: list[str]) -> float:
    """Default fitness function for tests."""
    score = len(traits) * 10.0
    # Bonus for specific valuable traits
    for t in traits:
        if "safety" in t.lower():
            score += 25.0
        if "performance" in t.lower():
            score += 15.0
        if "test" in t.lower():
            score += 10.0
    return score


def _default_mutate(traits: list[str]) -> tuple[list[str], str]:
    """Default mutation function for tests."""
    new_traits = list(traits)
    new_trait = f"enhanced_{len(traits)}"
    new_traits.append(new_trait)
    return new_traits, f"added_{new_trait}"


def _default_crossover(traits_a: list[str], traits_b: list[str]) -> list[str]:
    """Default crossover function for tests."""
    combined = list(set(traits_a + traits_b))
    return combined[: max(len(traits_a), len(traits_b))]


# ── LineageTracker Tests ──────────────────────────────────────────


class TestLineageTracker:
    """Test suite for LineageTracker."""

    def test_record_root_skill(self):
        tracker = LineageTracker()
        lineage = tracker.record_birth(
            "root-skill", parent_name=None,
            inherited_traits=[], mutated_traits=["coding", "testing"],
        )
        assert lineage.is_root is True
        assert lineage.parent_name is None
        assert lineage.generation == 0
        assert "coding" in lineage.mutation_log

    def test_record_child_skill(self):
        tracker = LineageTracker()
        tracker.record_birth("root", parent_name=None)
        child = tracker.record_birth(
            "child", parent_name="root",
            inherited_traits=["coding"], mutated_traits=["security"],
        )
        assert child.parent_name == "root"
        assert child.generation == 1
        assert "coding" in child.inheritance_mask
        assert "security" in child.mutation_log

    def test_get_ancestors(self):
        tracker = LineageTracker()
        tracker.record_birth("gen0", parent_name=None)
        tracker.record_birth("gen1", parent_name="gen0")
        tracker.record_birth("gen2", parent_name="gen1")

        ancestors = tracker.get_ancestors("gen2")
        assert len(ancestors) == 2
        assert ancestors[0].skill_name == "gen1"
        assert ancestors[1].skill_name == "gen0"

    def test_get_descendants(self):
        tracker = LineageTracker()
        tracker.record_birth("root", parent_name=None)
        tracker.record_birth("child1", parent_name="root")
        tracker.record_birth("child2", parent_name="root")

        descendants = tracker.get_descendants("root")
        assert len(descendants) == 2

    def test_get_family_tree(self):
        tracker = LineageTracker()
        tracker.record_birth("root", parent_name=None)
        tracker.record_birth("child", parent_name="root")
        tracker.record_birth("grandchild", parent_name="child")

        tree = tracker.get_family_tree("root")
        assert tree["name"] == "root"
        assert len(tree["children"]) == 1
        assert tree["children"][0]["name"] == "child"
        assert len(tree["children"][0]["children"]) == 1

    def test_get_generation(self):
        tracker = LineageTracker()
        tracker.record_birth("a", parent_name=None)
        tracker.record_birth("b", parent_name=None)
        tracker.record_birth("a1", parent_name="a")
        tracker.record_birth("b1", parent_name="b")

        gen0 = tracker.get_generation(0)
        gen1 = tracker.get_generation(1)
        assert len(gen0) == 2
        assert len(gen1) == 2

    def test_lineage_chain(self):
        tracker = LineageTracker()
        tracker.record_birth("r", parent_name=None)
        tracker.record_birth("a", parent_name="r")
        tracker.record_birth("b", parent_name="a")
        tracker.record_birth("c", parent_name="b")

        chain = tracker.get_lineage_chain("c")
        assert chain == ["r", "a", "b", "c"]

    def test_depth(self):
        tracker = LineageTracker()
        tracker.record_birth("root", parent_name=None)
        tracker.record_birth("l1", parent_name="root")
        tracker.record_birth("l2", parent_name="l1")

        assert tracker.depth("root") == 0
        assert tracker.depth("l1") == 1
        assert tracker.depth("l2") == 2
        assert tracker.depth("nonexistent") == 0

    def test_export_graph(self):
        tracker = LineageTracker()
        tracker.record_birth("root", parent_name=None)
        tracker.record_birth("child", parent_name="root")

        graph = tracker.export_graph()
        assert graph.total_generations == 1
        assert len(graph.root_skills) == 1
        assert graph.root_skills[0] == "root"

    def test_find_common_ancestor(self):
        tracker = LineageTracker()
        tracker.record_birth("root", parent_name=None)
        tracker.record_birth("branch_a", parent_name="root")
        tracker.record_birth("branch_b", parent_name="root")
        tracker.record_birth("leaf_a", parent_name="branch_a")
        tracker.record_birth("leaf_b", parent_name="branch_b")

        common = tracker.find_common_ancestor("leaf_a", "leaf_b")
        assert common is not None
        assert common.skill_name == "root"

    def test_count_descendants(self):
        tracker = LineageTracker()
        tracker.record_birth("root", parent_name=None)
        tracker.record_birth("c1", parent_name="root")
        tracker.record_birth("c2", parent_name="root")
        tracker.record_birth("gc1", parent_name="c1")

        assert tracker.count_descendants("root") == 3

    def test_total_skills_and_root_count(self):
        tracker = LineageTracker()
        tracker.record_birth("root1", parent_name=None)
        tracker.record_birth("root2", parent_name=None)
        tracker.record_birth("child1", parent_name="root1")

        assert tracker.total_skills == 3
        assert tracker.root_count == 2


# ── RecursivePropagator Tests ─────────────────────────────────────


class TestRecursivePropagator:
    """Test suite for RecursivePropagator."""

    def test_basic_propagation(self):
        propagator = RecursivePropagator(max_generations=5)

        def mutation_fn(name, gen):
            return [(f"{name}_v{gen}", ["new_trait"], "add_trait")]

        def fitness_fn(name):
            return 0.5 + (0.1 * name.count("_v"))

        result = propagator.propagate("root", 0.5, mutation_fn, fitness_fn)

        assert result.total_generations > 0
        assert result.best_fitness >= 0.5
        assert result.original_skill == "root"

    def test_propagation_converges(self):
        propagator = RecursivePropagator(
            max_generations=20, convergence_threshold=0.5
        )

        call_count = [0]

        def mutation_fn(name, gen):
            call_count[0] += 1
            return [(f"{name}_v{gen}", [f"t{gen}"], "add")]

        def fitness_fn(name):
            return 0.9

        result = propagator.propagate("root", 0.9, mutation_fn, fitness_fn)
        # Should stop early due to convergence
        assert result.total_generations < 20

    def test_mutation_history(self):
        propagator = RecursivePropagator(max_generations=3)

        def mutation_fn(name, gen):
            return [(f"{name}_m{gen}", [f"t{gen}"], "mutate")]

        def fitness_fn(name):
            return 1.0

        propagator.propagate("root", 1.0, mutation_fn, fitness_fn)
        history = propagator.get_mutation_history("root")
        assert len(history) > 0
        assert history[0].mutation_type == "mutate"

    def test_improvement_ratio(self):
        propagator = RecursivePropagator(max_generations=3)

        def mutation_fn(name, gen):
            return [(f"{name}_v{gen}", [f"t{gen}"], "improve")]

        def fitness_fn(name):
            return 1.0 + (0.2 * name.count("_v"))

        propagator.propagate("root", 1.0, mutation_fn, fitness_fn)
        ratio = propagator.get_improvement_ratio("root")
        assert ratio > 0

    def test_mutations_by_type(self):
        propagator = RecursivePropagator(max_generations=3)

        def mutation_fn(name, gen):
            return [(f"{name}_v{gen}", [f"t{gen}"], "speed")]

        def fitness_fn(name):
            return 1.0

        propagator.propagate("root", 1.0, mutation_fn, fitness_fn)
        counts = propagator.get_mutations_by_type("root")
        assert "speed" in counts

    def test_diversity_guided_strategy(self):
        propagator = RecursivePropagator(
            max_generations=3,
            strategy=PropagationStrategy.DIVERSITY_GUIDED,
        )

        def mutation_fn(name, gen):
            return [
                (f"{name}_a", ["a"], "add_a"),
                (f"{name}_b", ["b"], "add_b"),
            ]

        def fitness_fn(name):
            return 1.0

        result = propagator.propagate("root", 1.0, mutation_fn, fitness_fn)
        assert result.strategy == "diversity_guided"
        assert result.total_mutations > 0

    def test_propagation_with_exception_in_mutation(self):
        propagator = RecursivePropagator(max_generations=2)

        call_count = [0]

        def mutation_fn(name, gen):
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("Mutation error")
            return [(f"{name}_ok", ["ok"], "ok")]

        def fitness_fn(name):
            return 1.0

        result = propagator.propagate("root", 1.0, mutation_fn, fitness_fn)
        # Should handle the error gracefully without crashing
        assert result.original_skill == "root"
        assert result.total_mutations >= 0


# ── CollectiveEvolver Tests ───────────────────────────────────────


class TestCollectiveEvolver:
    """Test suite for CollectiveEvolver."""

    def test_seed_population(self):
        evolver = CollectiveEvolver(population_size=10)
        skills = [
            ("skill_a", ["coding", "testing"]),
            ("skill_b", ["coding", "security"]),
            ("skill_c", ["design", "testing"]),
        ]
        evolver.seed_population(skills, _default_fitness)
        assert evolver.current_population_size == 3

    def test_evolve_generation(self):
        evolver = CollectiveEvolver(population_size=10, mutation_rate=1.0)
        skills = [
            ("skill_a", ["coding", "testing"]),
            ("skill_b", ["coding", "security"]),
            ("skill_c", ["design", "testing"]),
            ("skill_d", ["architecture"]),
        ]
        evolver.seed_population(skills, _default_fitness)

        snapshot = evolver.evolve_generation(
            _default_fitness, _default_mutate, _default_crossover
        )
        assert snapshot.generation == 1
        assert snapshot.population_size > 0
        assert snapshot.max_fitness > 0

    def test_evolve_multiple_generations(self):
        evolver = CollectiveEvolver(population_size=10, mutation_rate=0.8, crossover_rate=0.5)
        skills = [
            ("skill_a", ["coding", "testing"]),
            ("skill_b", ["security", "performance"]),
            ("skill_c", ["design", "safety"]),
            ("skill_d", ["architecture", "testing"]),
        ]
        evolver.seed_population(skills, _default_fitness)

        result = evolver.evolve(5, _default_fitness, _default_mutate, _default_crossover)
        assert result.generations > 0
        assert result.initial_size == 4
        assert result.final_size > 0
        assert result.total_mutations > 0

    def test_elitism_preserves_best(self):
        evolver = CollectiveEvolver(
            population_size=10, elitism_count=2,
            mutation_rate=0.5, selection_method=SelectionMethod.ELITISM,
        )
        skills = [
            ("elite_a", ["safety", "performance", "testing", "coding"]),
            ("elite_b", ["safety", "security", "performance"]),
            ("normal_c", ["coding"]),
        ]
        evolver.seed_population(skills, _default_fitness)

        best_before = evolver.get_best_skills(1)[0]
        evolver.evolve_generation(_default_fitness, _default_mutate, _default_crossover)
        best_after = evolver.get_best_skills(1)[0]

        # Best skill should survive or be surpassed
        assert best_after[1] >= best_before[1]

    def test_selection_tournament(self):
        evolver = CollectiveEvolver(
            population_size=10, tournament_size=2,
            selection_method=SelectionMethod.TOURNAMENT,
        )
        skills = [
            ("a", ["safety", "performance"]),
            ("b", ["coding"]),
            ("c", ["testing"]),
        ]
        evolver.seed_population(skills, _default_fitness)
        snapshot = evolver.evolve_generation(
            _default_fitness, _default_mutate, _default_crossover
        )
        assert snapshot.population_size > 0

    def test_selection_roulette(self):
        evolver = CollectiveEvolver(
            population_size=10,
            selection_method=SelectionMethod.ROULETTE,
        )
        skills = [
            ("a", ["safety", "performance"]),
            ("b", ["coding"]),
            ("c", ["testing"]),
        ]
        evolver.seed_population(skills, _default_fitness)
        snapshot = evolver.evolve_generation(
            _default_fitness, _default_mutate, _default_crossover
        )
        assert snapshot.population_size > 0

    def test_selection_rank(self):
        evolver = CollectiveEvolver(
            population_size=10, selection_method=SelectionMethod.RANK,
        )
        skills = [("a", ["safety"]), ("b", ["coding"]), ("c", ["testing"])]
        evolver.seed_population(skills, _default_fitness)
        snapshot = evolver.evolve_generation(
            _default_fitness, _default_mutate, _default_crossover
        )
        assert snapshot.population_size > 0

    def test_fitness_improvement(self):
        evolver = CollectiveEvolver(
            population_size=20, mutation_rate=0.8,
            crossover_rate=0.6, elitism_count=3,
        )
        skills = [
            (f"skill_{i}", [f"trait_{i % 3}"])
            for i in range(10)
        ]
        evolver.seed_population(skills, _default_fitness)

        result = evolver.evolve(10, _default_fitness, _default_mutate, _default_crossover)
        # With mutation adding traits, fitness should improve
        assert result.final_avg_fitness >= result.initial_avg_fitness

    def test_diversity_score(self):
        evolver = CollectiveEvolver(population_size=10)
        skills = [
            ("a", ["trait_1", "trait_2"]),
            ("b", ["trait_3", "trait_4"]),
            ("c", ["trait_5"]),
        ]
        evolver.seed_population(skills, _default_fitness)
        diversity = evolver.get_diversity_score()
        assert 0.0 <= diversity <= 1.0

    def test_convergence_early_stop(self):
        evolver = CollectiveEvolver(
            population_size=10, mutation_rate=0.0, crossover_rate=0.0,
        )
        skills = [("static_a", ["trait"]), ("static_b", ["trait"])]
        evolver.seed_population(skills, _default_fitness)

        result = evolver.evolve(
            20, _default_fitness, _default_mutate, _default_crossover,
            convergence_threshold=0.01,
        )
        # Should stop early due to no improvement (no mutation)
        assert result.generations < 20

    def test_get_best_skills(self):
        evolver = CollectiveEvolver(population_size=10)
        skills = [
            ("best", ["safety", "performance", "testing", "coding"]),
            ("mid", ["coding", "testing"]),
            ("low", ["coding"]),
        ]
        evolver.seed_population(skills, _default_fitness)

        best = evolver.get_best_skills(limit=2)
        assert len(best) == 2
        assert best[0][0] == "best"
        assert best[1][0] == "mid"

    def test_get_history(self):
        evolver = CollectiveEvolver(population_size=10, mutation_rate=1.0)
        skills = [("a", ["t1"]), ("b", ["t2"]), ("c", ["t3"])]
        evolver.seed_population(skills, _default_fitness)
        evolver.evolve_generation(_default_fitness, _default_mutate, _default_crossover)
        evolver.evolve_generation(_default_fitness, _default_mutate, _default_crossover)

        history = evolver.get_history()
        assert len(history) == 2
        assert history[0].generation == 1
        assert history[1].generation == 2

    def test_get_fitness_trend(self):
        evolver = CollectiveEvolver(population_size=10, mutation_rate=0.5)
        skills = [("a", ["t1"]), ("b", ["t2"]), ("c", ["t3"])]
        evolver.seed_population(skills, _default_fitness)
        evolver.evolve_generation(_default_fitness, _default_mutate, _default_crossover)

        trend = evolver.get_fitness_trend()
        assert len(trend) == 1
        assert trend[0] > 0

    def test_empty_population_selection(self):
        evolver = CollectiveEvolver()
        parent = evolver._select_parent({})
        assert parent is None

    def test_clear_state(self):
        evolver = CollectiveEvolver()
        skills = [("a", ["t1"]), ("b", ["t2"])]
        evolver.seed_population(skills, _default_fitness)
        evolver.evolve_generation(_default_fitness, _default_mutate, _default_crossover)

        evolver.clear()
        assert evolver.current_population_size == 0
        assert evolver.current_generation == 0
        assert len(evolver.get_history()) == 0
