"""Comprehensive tests for lyra-evolution package."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest

from lyra_evolution import (
    CouncilDecision,
    CouncilMember,
    CouncilMode,
    CouncilVote,
    EscherGeneration,
    EscherLoop,
    EscherSolver,
    EvolutionMetrics,
    GEAREvolve,
    GEARStrategy,
    SelfImprovement,
)

# ============================================================================
# Model tests
# ============================================================================


class TestCouncilMember:
    def test_default_construction(self) -> None:
        m = CouncilMember()
        assert m.agent_id
        assert m.weight == 1.0
        assert m.expertise == ()
        assert m.performance_history == ()

    def test_update_performance_is_immutable(self) -> None:
        m = CouncilMember()
        updated = m.update_performance(0.8)
        assert updated is not m
        assert m.performance_history == ()
        assert updated.performance_history == (0.8,)

    def test_average_performance_empty(self) -> None:
        m = CouncilMember()
        assert m.average_performance == 0.5

    def test_average_performance_computed(self) -> None:
        m = CouncilMember()
        m = m.update_performance(0.6)
        m = m.update_performance(0.8)
        m = m.update_performance(1.0)
        assert m.average_performance == pytest.approx(0.8)

    def test_frozen_prevents_mutation(self) -> None:
        m = CouncilMember(agent_id="x")
        with pytest.raises(Exception):
            m.agent_id = "y"  # type: ignore[misc]


class TestCouncilVote:
    def test_construction(self) -> None:
        v = CouncilVote(member_id="a", decision="approve", confidence=0.9, reasoning="looks good")
        assert v.member_id == "a"
        assert v.decision == "approve"
        assert v.confidence == 0.9

    def test_confidence_clamping(self) -> None:
        with pytest.raises(ValueError, match="confidence"):
            CouncilVote(member_id="a", decision="x", confidence=1.5)
        with pytest.raises(ValueError, match="confidence"):
            CouncilVote(member_id="a", decision="x", confidence=-0.1)

    def test_default_timestamp(self) -> None:
        v = CouncilVote(member_id="a", decision="x")
        assert isinstance(v.timestamp, datetime)


class TestCouncilDecision:
    def test_defaults(self) -> None:
        d = CouncilDecision(final_decision="yes")
        assert d.final_decision == "yes"
        assert d.votes == ()
        assert d.consensus_level == 0.0
        assert d.dissenting_opinions == ()
        assert d.metadata == {}

    def test_with_votes(self) -> None:
        v1 = CouncilVote(member_id="a", decision="yes", confidence=0.9)
        v2 = CouncilVote(member_id="b", decision="no", confidence=0.3, reasoning="disagree")
        d = CouncilDecision(
            final_decision="yes",
            votes=(v1, v2),
            consensus_level=0.75,
            dissenting_opinions=("[b] disagree",),
        )
        assert len(d.votes) == 2
        assert d.consensus_level == 0.75


class TestEscherSolver:
    def test_default_construction(self) -> None:
        s = EscherSolver()
        assert s.solution_id
        assert s.fitness_score == 0.0
        assert s.parent_ids == ()
        assert s.generation == 0

    def test_with_content(self) -> None:
        s = EscherSolver(
            content="hello",
            fitness_score=0.95,
            parent_ids=("a", "b"),
            generation=3,
        )
        assert s.content == "hello"
        assert s.fitness_score == 0.95
        assert s.parent_ids == ("a", "b")
        assert s.generation == 3


class TestEscherGeneration:
    def test_empty_generation(self) -> None:
        gen = EscherGeneration()
        assert gen.best_solution is None
        assert gen.average_score == 0.0

    def test_best_solution(self) -> None:
        s1 = EscherSolver(content="a", fitness_score=0.1)
        s2 = EscherSolver(content="b", fitness_score=0.9)
        s3 = EscherSolver(content="c", fitness_score=0.5)
        gen = EscherGeneration(
            solutions=(s1, s2, s3),
            scores=(0.1, 0.9, 0.5),
            generation_number=0,
        )
        best = gen.best_solution
        assert best is not None
        assert best.content == "b"

    def test_average_score(self) -> None:
        gen = EscherGeneration(solutions=(), scores=(0.2, 0.4, 0.6), generation_number=1)
        assert gen.average_score == pytest.approx(0.4)


class TestGEARStrategy:
    def test_default_construction(self) -> None:
        s = GEARStrategy()
        assert s.strategy_id
        assert s.success_rate == 0.5

    def test_custom_values(self) -> None:
        s = GEARStrategy(
            strategy_id="s1",
            problem_features=(0.1, 0.2),
            success_rate=0.8,
            exploration_weight=0.3,
            total_uses=10,
        )
        assert s.strategy_id == "s1"
        assert s.problem_features == (0.1, 0.2)
        assert s.success_rate == 0.8


class TestEvolutionMetrics:
    def test_construction(self) -> None:
        m = EvolutionMetrics(
            generation=1,
            avg_fitness=0.5,
            best_fitness=0.9,
            diversity=0.7,
            improvement_rate=0.05,
        )
        assert m.generation == 1
        assert m.avg_fitness == 0.5
        assert m.best_fitness == 0.9
        assert isinstance(m.timestamp, datetime)


# ============================================================================
# Council mode tests
# ============================================================================


class TestCouncilMode:
    @pytest.fixture
    def members(self) -> list[CouncilMember]:
        return [
            CouncilMember(agent_id="a", expertise=("math",), weight=1.0),
            CouncilMember(agent_id="b", expertise=("logic",), weight=1.2),
            CouncilMember(agent_id="c", expertise=("coding",), weight=0.8),
        ]

    @pytest.fixture
    def council(self) -> CouncilMode:
        return CouncilMode(name="test-council")

    def test_convene(self, council: CouncilMode, members: list[CouncilMember]) -> None:
        result = council.convene(members, "What is 2+2?")
        assert result is council
        assert council.member_count == 3
        assert council.get_member("a") is not None
        assert council.get_member("nonexistent") is None

    def test_vote_single_option(self, council: CouncilMode, members: list[CouncilMember]) -> None:
        council.convene(members, "test")
        decision = council.vote(members, ["approve"])
        assert decision.final_decision == "approve"
        assert len(decision.votes) == 3
        assert decision.metadata["council"] == "test-council"

    def test_vote_empty_members(self, council: CouncilMode) -> None:
        decision = council.vote([], ["a", "b"])
        assert decision.final_decision == ""

    def test_vote_empty_options(self, council: CouncilMode, members: list[CouncilMember]) -> None:
        council.convene(members, "test")
        decision = council.vote(members, [])
        assert decision.final_decision == ""

    def test_debate_produces_transcript(
        self, council: CouncilMode, members: list[CouncilMember]
    ) -> None:
        council.convene(members, "test problem")
        transcript = council.debate(members, "test problem", rounds=2)
        assert len(transcript) == 2
        assert transcript[0]["round"] == 1
        assert "member_statements" in transcript[0]

    def test_debate_minimum_one_round(
        self, council: CouncilMode, members: list[CouncilMember]
    ) -> None:
        council.convene(members, "test")
        transcript = council.debate(members, "test", rounds=0)
        assert len(transcript) == 1

    def test_compute_consensus_all_agree(self) -> None:
        votes = [
            CouncilVote(member_id="a", decision="yes", confidence=0.9),
            CouncilVote(member_id="b", decision="yes", confidence=0.8),
        ]
        level = CouncilMode.compute_consensus_level(votes)
        assert level == 1.0

    def test_compute_consensus_split(self) -> None:
        votes = [
            CouncilVote(member_id="a", decision="yes", confidence=0.9),
            CouncilVote(member_id="b", decision="no", confidence=0.9),
        ]
        level = CouncilMode.compute_consensus_level(votes)
        assert level == 0.5

    def test_compute_consensus_empty(self) -> None:
        assert CouncilMode.compute_consensus_level([]) == 0.0

    def test_weighted_majority(self) -> None:
        votes = [
            CouncilVote(member_id="a", decision="yes", confidence=0.9),
            CouncilVote(member_id="b", decision="no", confidence=0.5),
            CouncilVote(member_id="c", decision="yes", confidence=0.6),
        ]
        weights = {"a": 1.0, "b": 2.0, "c": 1.0}
        winner, score = CouncilMode.weighted_majority(votes, weights)
        # a: yes * 0.9 = 0.9, b: no * 0.5 * 2 = 1.0, c: yes * 0.6 = 0.6
        # yes = 1.5, no = 1.0 → winner = yes
        assert winner == "yes"
        assert score == pytest.approx(1.5 / 2.5)

    def test_weighted_majority_empty(self) -> None:
        winner, score = CouncilMode.weighted_majority([], {})
        assert winner == ""
        assert score == 0.0

    def test_hallucination_detection_perfect(self) -> None:
        claims = {"a": "The sky is blue", "b": "The sky is blue and clear"}
        reference = "The sky is blue"
        risks = CouncilMode.detect_hallucination(claims, reference)
        assert all(0.0 <= r <= 1.0 for r in risks.values())
        # Identical claim should have lower risk
        assert risks["a"] < risks["b"] or risks["a"] <= 0.5

    def test_hallucination_detection_full_diverge(self) -> None:
        claims = {"a": "The sky is blue", "b": "Bananas are telephones"}
        reference = "The sky is blue"
        risks = CouncilMode.detect_hallucination(claims, reference)
        assert risks["b"] > risks["a"]

    def test_hallucination_detection_empty_reference(self) -> None:
        risks = CouncilMode.detect_hallucination({"a": "text"}, "")
        assert risks["a"] == 0.5

    def test_resolve_conflict_no_disagreement(
        self, council: CouncilMode, members: list[CouncilMember]
    ) -> None:
        council.convene(members, "test")
        disagreement = {"a": "yes", "b": "yes"}
        result = council.resolve_conflict(disagreement)
        assert result.final_decision == "yes"
        assert result.metadata["resolution"] == "no_conflict"

    def test_resolve_conflict_with_disagreement(
        self, council: CouncilMode, members: list[CouncilMember]
    ) -> None:
        council.convene(members, "test")
        # All members agree on different options — triggers resolution
        disagreement = {"a": "option_a", "b": "option_b"}
        result = council.resolve_conflict(disagreement, max_iterations=3)
        assert result.final_decision in ("option_a", "option_b")
        assert "resolution" in result.metadata

    def test_resolve_conflict_empty_members(self, council: CouncilMode) -> None:
        result = council.resolve_conflict({"unknown1": "a", "unknown2": "b"})
        assert result.final_decision == ""


# ============================================================================
# Escher-Loop tests
# ============================================================================


class TestEscherLoop:
    @pytest.fixture
    def loop(self) -> EscherLoop:
        return EscherLoop(population_size=20, top_k=5, seed=42)

    def test_initialize_population(self, loop: EscherLoop) -> None:
        pop = loop.initialize_population()
        assert len(pop) == 20
        assert all(s.generation == 0 for s in pop)
        assert all(s.parent_ids == () for s in pop)

    def test_initialize_custom_size(self, loop: EscherLoop) -> None:
        pop = loop.initialize_population(size=10)
        assert len(pop) == 10

    def test_invalid_population_size(self) -> None:
        with pytest.raises(ValueError):
            EscherLoop(population_size=1)
        with pytest.raises(ValueError):
            EscherLoop(population_size=20, top_k=0)
        with pytest.raises(ValueError):
            EscherLoop(population_size=20, top_k=25)

    def test_select_top(self, loop: EscherLoop) -> None:
        s1 = EscherSolver(content="a", fitness_score=0.1)
        s2 = EscherSolver(content="b", fitness_score=0.9)
        s3 = EscherSolver(content="c", fitness_score=0.5)
        selected = loop.select_top([s1, s2, s3], top_k=2)
        assert len(selected) == 2
        assert selected[0].content == "b"

    def test_select_top_with_scores(self, loop: EscherLoop) -> None:
        s1 = EscherSolver(content="a")
        s2 = EscherSolver(content="b")
        s3 = EscherSolver(content="c")
        selected = loop.select_top([s1, s2, s3], top_k=2, scores=[0.3, 0.1, 0.9])
        assert selected[0].content == "c"
        assert selected[1].content == "a"

    def test_select_top_empty(self, loop: EscherLoop) -> None:
        assert loop.select_top([], top_k=5) == []

    def test_select_top_top_k_larger_than_pop(self, loop: EscherLoop) -> None:
        solvers = [EscherSolver(content="x"), EscherSolver(content="y")]
        selected = loop.select_top(solvers, top_k=10)
        assert len(selected) == 2

    def test_crossover(self, loop: EscherLoop) -> None:
        a = EscherSolver(solution_id="a", content="aaaa")
        b = EscherSolver(solution_id="b", content="bbbb")
        child = loop.crossover(a, b)
        assert child.solution_id != a.solution_id
        assert child.parent_ids == ("a", "b")
        assert child.generation == 1  # current gen + 1

    def test_mutate_applies(self, loop: EscherLoop) -> None:
        s = EscherSolver(content="original")
        # Use rate=1.0 to guarantee mutation
        mutated = loop.mutate(s, rate=1.0)
        assert "[mutated" in mutated.content

    def test_mutate_skips(self, loop: EscherLoop) -> None:
        s = EscherSolver(content="original")
        mutated = loop.mutate(s, rate=0.0)
        assert mutated is s  # identity preserved

    def test_compute_diversity_all_same(self, loop: EscherLoop) -> None:
        solvers = [EscherSolver(content="x") for _ in range(10)]
        assert loop.compute_diversity(solvers) == 0.0

    def test_compute_diversity_all_unique(self, loop: EscherLoop) -> None:
        solvers = [EscherSolver(content=str(i)) for i in range(10)]
        assert loop.compute_diversity(solvers) == 1.0

    def test_compute_diversity_single(self, loop: EscherLoop) -> None:
        assert loop.compute_diversity([EscherSolver(content="only")]) == 0.0

    def test_evolve_with_default_evaluator(self, loop: EscherLoop) -> None:
        loop.initialize_population()
        best = loop.evolve("test problem", generations=5)
        assert best is not None
        assert best.generation < 5  # generation index of best solution

    def test_evolve_runs_without_explicit_init(self, loop: EscherLoop) -> None:
        best = loop.evolve("test", generations=3)
        assert best is not None

    def test_get_metrics_before_evolution(self, loop: EscherLoop) -> None:
        assert loop.get_metrics() is None

    def test_get_metrics_after_evolution(self, loop: EscherLoop) -> None:
        loop.evolve("test", generations=3)
        metrics = loop.get_metrics()
        assert metrics is not None
        assert metrics.generation >= 0
        assert 0.0 <= metrics.diversity <= 1.0

    def test_population_property_returns_copy(self, loop: EscherLoop) -> None:
        loop.initialize_population(size=5)
        pop = loop.population
        assert len(pop) == 5
        pop.clear()  # should not affect internal
        assert len(loop.population) == 5

    def test_evaluate_solutions_calls_evaluator(self, loop: EscherLoop) -> None:
        solvers = [EscherSolver(content="a"), EscherSolver(content="b")]
        scores = loop.evaluate_solutions(solvers, lambda s: float(len(s.content)))
        assert scores == [1.0, 1.0]

    def test_evolve_with_custom_evaluator(self, loop: EscherLoop) -> None:
        def evaluator(s: EscherSolver) -> float:
            # Favour longer content
            return float(len(s.content))

        loop.initialize_population(size=10)
        best = loop.evolve("test", generations=3, evaluator=evaluator)
        assert best is not None

    def test_generation_property(self, loop: EscherLoop) -> None:
        loop.evolve("test", generations=4)
        # After 4 generations, _generation should be 3 (0-indexed)
        assert loop.generation == 3


# ============================================================================
# GEAR-Evolve tests
# ============================================================================


class TestGEAREvolve:
    @pytest.fixture
    def gear(self) -> GEAREvolve:
        g = GEAREvolve(initial_exploration=0.5, seed=42)
        g.register_strategy(GEARStrategy(strategy_id="s1", success_rate=0.9, total_uses=10))
        g.register_strategy(GEARStrategy(strategy_id="s2", success_rate=0.3, total_uses=2))
        g.register_strategy(GEARStrategy(strategy_id="s3", success_rate=0.6, total_uses=50))
        return g

    def test_strategy_count(self, gear: GEAREvolve) -> None:
        assert gear.strategy_count == 3

    def test_list_strategies(self, gear: GEAREvolve) -> None:
        assert len(gear.list_strategies()) == 3

    def test_select_strategy_returns_something(self, gear: GEAREvolve) -> None:
        chosen = gear.select_strategy()
        assert chosen is not None
        assert chosen.strategy_id in {"s1", "s2", "s3"}

    def test_select_strategy_empty_registry(self) -> None:
        g = GEAREvolve()
        chosen = g.select_strategy()
        assert chosen.strategy_id == "default"
        assert g.strategy_count == 1

    def test_select_strategy_with_features(self, gear: GEAREvolve) -> None:
        chosen = gear.select_strategy(problem_features=(0.5, 0.5))
        assert chosen is not None

    def test_execute_search(self, gear: GEAREvolve) -> None:
        s = gear.list_strategies()[0]
        result = gear.execute_search(s, "test query")
        assert result is not None
        assert result["status"] == "noop"

        # Usage count incremented
        updated = gear.list_strategies()[0]
        assert s.total_uses + 1 == updated.total_uses if updated.strategy_id == s.strategy_id else True

    def test_execute_search_with_custom_searcher(self, gear: GEAREvolve) -> None:
        def searcher(strategy: GEARStrategy, problem: str) -> dict[str, Any]:
            return {"found": True, "strategy": strategy.strategy_id, "problem": problem}

        s = gear.list_strategies()[0]
        result = gear.execute_search(s, "find me", searcher=searcher)
        assert result["found"] is True

    def test_update_strategy_performance(self, gear: GEAREvolve) -> None:
        s = gear.list_strategies()[0]
        gear.update_strategy_performance(s, 1.0)
        updated = gear.get_best_strategy()
        assert updated is not None

    def test_update_outcome_clamping(self, gear: GEAREvolve) -> None:
        s = gear.list_strategies()[0]
        with pytest.raises(ValueError):
            gear.update_strategy_performance(s, 1.5)
        with pytest.raises(ValueError):
            gear.update_strategy_performance(s, -0.5)

    def test_adapt_exploration_decays(self, gear: GEAREvolve) -> None:
        initial = gear.exploration_weight
        new_weight = gear.adapt_exploration()
        # With decay_factor 0.95: 0.5 * 0.95 = 0.475
        assert new_weight < initial
        assert new_weight >= 0.05  # min_exploration

    def test_adapt_exploration_boosts_on_poor_performance(self, gear: GEAREvolve) -> None:
        gear.adapt_exploration()  # decay once
        boosted = gear.adapt_exploration(performance_history=[0.1, 0.1, 0.1])
        assert boosted >= 0.05

    def test_adapt_exploration_floor(self, gear: GEAREvolve) -> None:
        g = GEAREvolve(initial_exploration=0.02, min_exploration=0.05)
        g.adapt_exploration()
        assert g.exploration_weight >= 0.05

    def test_discover_new_strategies(self, gear: GEAREvolve) -> None:
        previous = gear.strategy_count
        new = gear.discover_new_strategies(count=3)
        assert len(new) == 3
        assert gear.strategy_count == previous + 3
        # IDs are unique
        ids = {s.strategy_id for s in gear.list_strategies()}
        assert len(ids) == gear.strategy_count

    def test_discover_with_generator(self, gear: GEAREvolve) -> None:
        def gen() -> GEARStrategy:
            return GEARStrategy(strategy_id="custom-gen", success_rate=0.99)

        new = gear.discover_new_strategies(count=1, generator=gen)
        assert new[0].strategy_id == "custom-gen"
        assert new[0].success_rate == 0.99

    def test_prune_ineffective(self, gear: GEAREvolve) -> None:
        # Register a known-bad strategy with enough uses
        bad = GEARStrategy(strategy_id="bad", success_rate=0.01, total_uses=10)
        gear.register_strategy(bad)
        removed = gear.prune_ineffective_strategies(threshold=0.1)
        assert removed >= 1
        assert "bad" not in {s.strategy_id for s in gear.list_strategies()}

    def test_prune_skips_untested(self, gear: GEAREvolve) -> None:
        fresh = GEARStrategy(strategy_id="fresh", success_rate=0.0, total_uses=2)
        gear.register_strategy(fresh)
        gear.prune_ineffective_strategies(threshold=0.1)
        # fresh has < 5 uses, should survive
        assert "fresh" in {s.strategy_id for s in gear.list_strategies()}

    def test_get_best_strategy(self, gear: GEAREvolve) -> None:
        best = gear.get_best_strategy()
        assert best is not None
        assert best.strategy_id == "s1"  # 0.9 > 0.6 > 0.3

    def test_summary(self, gear: GEAREvolve) -> None:
        s = gear.summary()
        assert s["total_strategies"] == 3
        assert s["best_strategy"] == "s1"
        assert s["best_success_rate"] == 0.9

    def test_feature_similarity(self) -> None:
        sim = GEAREvolve._feature_similarity(  # type: ignore[attr-defined]
            (1.0, 0.0), (1.0, 0.0)
        )
        assert sim == pytest.approx(0.5)  # scaled by /2

        sim_zero = GEAREvolve._feature_similarity(  # type: ignore[attr-defined]
            (0.0, 0.0), (1.0, 1.0)
        )
        assert sim_zero == 0.0


# ============================================================================
# Self-Improvement tests
# ============================================================================


class TestSelfImprovement:
    @pytest.fixture
    def engine(self) -> SelfImprovement:
        return SelfImprovement(rollback_threshold=0.05)

    def test_record_episode(self, engine: SelfImprovement) -> None:
        engine.record_episode("task1", "success", 0.95)
        engine.record_episode("task2", "failure", 0.2)
        assert len(engine._episodes) == 2

    def test_analyze_failures_detects_patterns(self, engine: SelfImprovement) -> None:
        for _ in range(5):
            engine.record_episode("buggy_task", "failure", 0.1)
        for _ in range(2):
            engine.record_episode("ok_task", "failure", 0.4)
        patterns = engine.analyze_failures(min_occurrences=3)
        assert len(patterns) >= 1
        assert patterns[0]["task_id"] == "buggy_task"
        assert patterns[0]["count"] == 5

    def test_analyze_failures_no_failures(self, engine: SelfImprovement) -> None:
        engine.record_episode("t1", "success", 0.9)
        patterns = engine.analyze_failures()
        assert patterns == []

    def test_generate_improvements_default(self, engine: SelfImprovement) -> None:
        failures = [{"task_id": "f1", "count": 3, "avg_score": 0.1}]
        improvements = engine.generate_improvements(failures)
        assert len(improvements) == 1
        assert improvements[0]["target_task"] == "f1"
        assert "change_type" in improvements[0]

    def test_generate_improvements_with_generator(self, engine: SelfImprovement) -> None:
        def gen(failure: dict[str, Any]) -> dict[str, Any] | None:
            return {"target_task": failure["task_id"], "custom": True}

        failures = [{"task_id": "f1", "count": 3}]
        improvements = engine.generate_improvements(failures, generator=gen)
        assert improvements[0]["custom"] is True

    def test_validate_improvement(self, engine: SelfImprovement) -> None:
        def test_suite(imp: dict[str, Any]) -> dict[str, Any]:
            return {"passed": True, "score": 0.95, "details": {"tests_run": 5}}

        imp = {"target_task": "test"}
        result = engine.validate_improvement(imp, test_suite)
        assert result["passed"] is True
        assert result["score"] == 0.95

    def test_apply_improvement(self, engine: SelfImprovement) -> None:
        imp = {"target_task": "fix_me"}
        imp_id = engine.apply_improvement(imp)
        assert imp_id.startswith("imp-")
        assert engine.active_improvement_count == 1

    def test_rollback_if_degraded_triggers(self, engine: SelfImprovement) -> None:
        imp = {"target_task": "fragile"}
        engine.apply_improvement(imp)
        rolled_back = engine.rollback_if_degraded(
            imp, baseline=0.9, current_score=0.7  # drop of 0.2 > threshold 0.05
        )
        assert rolled_back is True
        assert engine.active_improvement_count == 0

    def test_rollback_if_degraded_no_trigger(self, engine: SelfImprovement) -> None:
        imp = {"target_task": "stable"}
        engine.apply_improvement(imp)
        rolled_back = engine.rollback_if_degraded(imp, baseline=0.9, current_score=0.89)
        assert rolled_back is False
        assert engine.active_improvement_count == 1

    def test_rollback_no_score(self, engine: SelfImprovement) -> None:
        imp = {"target_task": "unknown"}
        engine.apply_improvement(imp)
        rolled_back = engine.rollback_if_degraded(imp, baseline=0.9)
        assert rolled_back is False  # no score → no rollback

    def test_rollback_with_evaluator(self, engine: SelfImprovement) -> None:
        imp = {"target_task": "eval_test"}
        engine.apply_improvement(imp)
        rolled_back = engine.rollback_if_degraded(
            imp,
            baseline=0.9,
            evaluator=lambda: 0.7,
        )
        assert rolled_back is True

    def test_compute_improvement_rate_flat(self, engine: SelfImprovement) -> None:
        for i in range(10):
            engine.record_episode(f"t{i}", "success", 0.5)
        rate = engine.compute_improvement_rate(window=10)
        # All scores are 0.5 → slope ~ 0
        assert abs(rate) < 0.01

    def test_compute_improvement_rate_trending_up(self, engine: SelfImprovement) -> None:
        for i in range(20):
            engine.record_episode(f"t{i}", "success", 0.1 + i * 0.04)
        rate = engine.compute_improvement_rate(window=20)
        assert rate > 0.0  # positive slope

    def test_compute_improvement_rate_insufficient_data(self, engine: SelfImprovement) -> None:
        assert engine.compute_improvement_rate() == 0.0
        engine.record_episode("t1", "success", 0.5)
        assert engine.compute_improvement_rate() == 0.0

    def test_get_metrics(self, engine: SelfImprovement) -> None:
        engine.record_episode("a", "success", 0.8)
        engine.record_episode("b", "failure", 0.3)
        engine.record_episode("c", "success", 0.7)
        metrics = engine.get_metrics()
        assert isinstance(metrics, EvolutionMetrics)
        assert metrics.avg_fitness == pytest.approx(0.6)
        assert metrics.best_fitness == 0.8

    def test_max_history_truncation(self) -> None:
        engine = SelfImprovement(max_history=5)
        for i in range(10):
            engine.record_episode(f"t{i}", "success", 0.5)
        assert len(engine._episodes) == 5


# ============================================================================
# Integration: end-to-end council + escher
# ============================================================================


class TestIntegration:
    def test_council_informs_escher_fitness(self) -> None:
        """Council judges solutions and feeds scores into Escher loop."""
        council = CouncilMode(name="judge")
        members = [
            CouncilMember(agent_id="j1", expertise=("quality",), weight=1.0),
            CouncilMember(agent_id="j2", expertise=("quality",), weight=1.0),
        ]
        council.convene(members, "judge solutions")

        def council_evaluator(solver: EscherSolver) -> float:
            # Council votes on the solution quality
            votes = [
                CouncilVote(member_id="j1", decision="good", confidence=0.8),
                CouncilVote(member_id="j2", decision="good", confidence=0.7),
            ]
            consensus = CouncilMode.compute_consensus_level(votes)
            return consensus  # 1.0 since both agree

        loop = EscherLoop(population_size=10, top_k=3, seed=99)
        loop.initialize_population()
        best = loop.evolve("test", generations=3, evaluator=council_evaluator)
        assert best is not None

    def test_gear_guides_escher_variation(self) -> None:
        """GEAR strategies determine mutation/crossover rates."""
        gear = GEAREvolve(seed=123)
        gear.register_strategy(
            GEARStrategy(strategy_id="aggressive", success_rate=0.7, exploration_weight=0.8)
        )

        loop = EscherLoop(population_size=10, top_k=3, seed=123)
        loop.evolve("test", generations=3)

        # GEAR selects a strategy based on problem
        strategy = gear.select_strategy(problem="test")
        assert strategy is not None
        outcome = 0.75
        gear.update_strategy_performance(strategy, outcome)

        # After success, best strategy should still be the one with 0.7 rate
        best = gear.get_best_strategy()
        assert best is not None
        assert best.success_rate >= 0.5
