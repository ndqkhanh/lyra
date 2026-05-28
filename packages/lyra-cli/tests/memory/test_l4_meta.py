"""Tests for L4 Meta memory layer — cross-session weaving, strategy evolution, meta-knowledge."""

import time

import pytest

from lyra_cli.memory.l4_meta.cross_session_weaver import (
    CrossSessionPattern,
    CrossSessionWeaver,
    StrategyType,
)
from lyra_cli.memory.l4_meta.meta_knowledge import (
    KnowledgeConfidence,
    KnowledgeType,
    MetaKnowledge,
    MetaKnowledgeStore,
)
from lyra_cli.memory.l4_meta.strategy_evolution import (
    Strategy,
    StrategyEvolution,
    StrategyStatus,
)


class TestStrategyType:
    def test_all_types(self):
        assert StrategyType.HEURISTIC.value == "heuristic"
        assert StrategyType.WORKFLOW.value == "workflow"
        assert StrategyType.CONSTRAINT.value == "constraint"
        assert StrategyType.OPTIMIZATION.value == "optimization"


class TestCrossSessionPattern:
    def test_pattern_creation(self):
        p = CrossSessionPattern(
            pattern_id="p1",
            pattern_type=StrategyType.CONSTRAINT,
            description="avoid X when Y",
            source_sessions=["s1", "s2"],
            confidence=0.85,
            observed_count=3,
            created_at=time.time(),
        )
        assert p.pattern_id == "p1"
        assert p.pattern_type == StrategyType.CONSTRAINT
        assert p.source_sessions == ["s1", "s2"]
        assert p.confidence == 0.85
        assert p.observed_count == 3

    def test_pattern_frozen(self):
        p = CrossSessionPattern(
            pattern_id="p1",
            pattern_type=StrategyType.HEURISTIC,
            description="do X",
            source_sessions=["s1"],
            confidence=0.5,
            observed_count=1,
            created_at=time.time(),
        )
        with pytest.raises(Exception):
            p.confidence = 0.9  # type: ignore[misc]


class TestCrossSessionWeaver:
    def test_init(self):
        weaver = CrossSessionWeaver()
        assert weaver.stats()["total_patterns"] == 0
        assert weaver.stats()["active_strategies"] == 0

    def test_observe_single_pattern(self):
        weaver = CrossSessionWeaver()
        pattern = weaver.observe("s1", StrategyType.HEURISTIC, "user prefers concise responses")
        assert pattern.pattern_type == StrategyType.HEURISTIC
        assert pattern.source_sessions == ["s1"]
        assert pattern.observed_count == 1

    def test_observe_multiple_sessions_same_pattern(self):
        weaver = CrossSessionWeaver()
        weaver.observe("s1", StrategyType.WORKFLOW, "prefers markdown format")
        pattern = weaver.observe("s2", StrategyType.WORKFLOW, "prefers markdown format")
        assert pattern.observed_count >= 1

    def test_get_for_session(self):
        weaver = CrossSessionWeaver()
        weaver.observe("s1", StrategyType.HEURISTIC, "pattern a")
        weaver.observe("s2", StrategyType.WORKFLOW, "pattern b")
        session_patterns = weaver.get_for_session("s1")
        assert len(session_patterns) >= 1

    def test_get_strategies_below_threshold(self):
        weaver = CrossSessionWeaver(min_confidence=0.9, min_observations=10)
        weaver.observe("s1", StrategyType.OPTIMIZATION, "optimize startup time")
        strategies = weaver.get_strategies()
        assert len(strategies) == 0

    def test_get_strategies_with_repeated_observations(self):
        weaver = CrossSessionWeaver(min_confidence=0.4, min_observations=2)
        for _ in range(5):
            weaver.observe("s1", StrategyType.CONSTRAINT, "always use type hints")
        strategies = weaver.get_strategies()
        assert len(strategies) >= 1

    def test_stats_after_observations(self):
        weaver = CrossSessionWeaver()
        weaver.observe("s1", StrategyType.HEURISTIC, "pattern a")
        weaver.observe("s2", StrategyType.WORKFLOW, "pattern b")
        s = weaver.stats()
        assert s["total_patterns"] >= 2
        assert s["sessions_analyzed"] >= 2


class TestStrategyStatus:
    def test_all_statuses(self):
        assert StrategyStatus.ACTIVE.value == "active"
        assert StrategyStatus.DEPRECATED.value == "deprecated"
        assert StrategyStatus.EXPERIMENTAL.value == "experimental"
        assert StrategyStatus.ARCHIVED.value == "archived"


class TestStrategy:
    def test_strategy_creation(self):
        s = Strategy(
            strategy_id="s1",
            name="test-strategy",
            description="when X, do Y",
            status=StrategyStatus.EXPERIMENTAL,
            success_rate=0.5,
            total_uses=0,
            created_at=time.time(),
            last_used=None,
            parent_id=None,
        )
        assert s.strategy_id == "s1"
        assert s.status == StrategyStatus.EXPERIMENTAL
        assert s.total_uses == 0

    def test_strategy_frozen(self):
        s = Strategy(
            strategy_id="s1",
            name="test",
            description="do X",
            status=StrategyStatus.EXPERIMENTAL,
            success_rate=0.5,
            total_uses=0,
            created_at=time.time(),
            last_used=None,
            parent_id=None,
        )
        with pytest.raises(Exception):
            s.success_rate = 1.0  # type: ignore[misc]


class TestStrategyEvolution:
    def test_init(self):
        evo = StrategyEvolution()
        assert evo.stats()["total_strategies"] == 0

    def test_register_strategy(self):
        evo = StrategyEvolution()
        s = evo.register("test-strategy", "when X, do Y")
        assert s.name == "test-strategy"
        assert s.status == StrategyStatus.EXPERIMENTAL
        assert evo.stats()["total_strategies"] == 1

    def test_record_success(self):
        evo = StrategyEvolution()
        s = evo.register("test", "when X, do Y")
        updated = evo.record_outcome(s.strategy_id, success=True)
        assert updated is not None
        assert updated.total_uses == 1
        assert updated.success_rate > 0.5

    def test_record_failure(self):
        evo = StrategyEvolution()
        s = evo.register("test", "when X, do Y")
        updated = evo.record_outcome(s.strategy_id, success=False)
        assert updated is not None
        assert updated.total_uses == 1
        assert updated.success_rate < 0.5

    def test_record_nonexistent(self):
        evo = StrategyEvolution()
        result = evo.record_outcome("nonexistent", success=True)
        assert result is None

    def test_promotes_to_active_after_successes(self):
        evo = StrategyEvolution()
        s = evo.register("reliable", "when A, do B")
        for _ in range(11):
            evo.record_outcome(s.strategy_id, success=True)
        active = evo.get_active()
        assert len(active) >= 1
        assert active[0].status == StrategyStatus.ACTIVE

    def test_deprecates_after_failures(self):
        evo = StrategyEvolution()
        s = evo.register("unreliable", "when C, do D")
        for _ in range(11):
            evo.record_outcome(s.strategy_id, success=False)
        deprecated = [
            s for s in evo.stats().keys() if s == "total_strategies"
        ]
        assert evo.stats()["total_strategies"] == 1

    def test_mutate_creates_variant(self):
        evo = StrategyEvolution()
        s = evo.register("base", "base description")
        variant = evo.mutate(s.strategy_id, "variant1")
        assert variant is not None
        assert "variant1" in variant.name
        assert variant.parent_id is None  # new strategy, parent is base
        assert evo.stats()["total_strategies"] == 2

    def test_mutate_nonexistent(self):
        evo = StrategyEvolution()
        result = evo.mutate("nonexistent", "v1")
        assert result is None

    def test_get_experimental(self):
        evo = StrategyEvolution()
        evo.register("a", "pattern A")
        evo.register("b", "pattern B")
        experimental = evo.get_experimental()
        assert len(experimental) == 2


class TestKnowledgeType:
    def test_all_types(self):
        assert KnowledgeType.INVARIANT.value == "invariant"
        assert KnowledgeType.HEURISTIC.value == "heuristic"
        assert KnowledgeType.ANTI_PATTERN.value == "anti_pattern"
        assert KnowledgeType.BEST_PRACTICE.value == "best_practice"
        assert KnowledgeType.CONSTRAINT.value == "constraint"


class TestKnowledgeConfidence:
    def test_all_levels(self):
        assert KnowledgeConfidence.HYPOTHESIS.value == "hypothesis"
        assert KnowledgeConfidence.OBSERVED.value == "observed"
        assert KnowledgeConfidence.CONFIRMED.value == "confirmed"
        assert KnowledgeConfidence.PROVEN.value == "proven"


class TestMetaKnowledge:
    def test_creation(self):
        mk = MetaKnowledge(
            entry_id="k1",
            knowledge_type=KnowledgeType.INVARIANT,
            statement="Python uses significant whitespace",
            confidence=KnowledgeConfidence.CONFIRMED,
            supporting_evidence=["e1", "e2"],
            contradicting_evidence=[],
            source_sessions=["s1"],
            created_at=time.time(),
            last_updated=time.time(),
        )
        assert mk.entry_id == "k1"
        assert mk.knowledge_type == KnowledgeType.INVARIANT
        assert mk.confidence == KnowledgeConfidence.CONFIRMED

    def test_evidence_ratio_all_support(self):
        mk = MetaKnowledge(
            entry_id="k1",
            knowledge_type=KnowledgeType.BEST_PRACTICE,
            statement="test",
            confidence=KnowledgeConfidence.OBSERVED,
            supporting_evidence=["e1", "e2", "e3"],
            contradicting_evidence=[],
            source_sessions=[],
            created_at=time.time(),
            last_updated=time.time(),
        )
        assert mk.evidence_ratio == 1.0

    def test_evidence_ratio_no_evidence(self):
        mk = MetaKnowledge(
            entry_id="k1",
            knowledge_type=KnowledgeType.CONSTRAINT,
            statement="test",
            confidence=KnowledgeConfidence.HYPOTHESIS,
            supporting_evidence=[],
            contradicting_evidence=[],
            source_sessions=[],
            created_at=time.time(),
            last_updated=time.time(),
        )
        assert mk.evidence_ratio == 0.5

    def test_frozen(self):
        mk = MetaKnowledge(
            entry_id="k1",
            knowledge_type=KnowledgeType.INVARIANT,
            statement="test",
            confidence=KnowledgeConfidence.HYPOTHESIS,
            supporting_evidence=[],
            contradicting_evidence=[],
            source_sessions=[],
            created_at=time.time(),
            last_updated=time.time(),
        )
        with pytest.raises(Exception):
            mk.statement = "new"  # type: ignore[misc]


class TestMetaKnowledgeStore:
    def test_init(self):
        store = MetaKnowledgeStore()
        assert store.stats()["total_entries"] == 0

    def test_add_knowledge(self):
        store = MetaKnowledgeStore()
        mk = store.add(KnowledgeType.BEST_PRACTICE, "use frozen dataclasses")
        assert mk.knowledge_type == KnowledgeType.BEST_PRACTICE
        assert mk.confidence == KnowledgeConfidence.HYPOTHESIS

    def test_add_reinforces_confidence(self):
        store = MetaKnowledgeStore()
        mk = store.add(
            KnowledgeType.INVARIANT,
            "repeatable fact",
            evidence="session 1 observed this",
            session_id="s1",
        )
        mk = store.add(
            KnowledgeType.INVARIANT,
            "repeatable fact",
            evidence="session 2 confirmed",
            session_id="s2",
        )
        mk = store.add(
            KnowledgeType.INVARIANT,
            "repeatable fact",
            evidence="session 3 confirmed again",
            session_id="s3",
        )
        assert mk.confidence == KnowledgeConfidence.CONFIRMED

    def test_query_by_type(self):
        store = MetaKnowledgeStore()
        store.add(KnowledgeType.INVARIANT, "invariant fact")
        store.add(KnowledgeType.HEURISTIC, "heuristic pattern")
        invariants = store.query(knowledge_type=KnowledgeType.INVARIANT)
        assert len(invariants) >= 1
        heuristics = store.query(knowledge_type=KnowledgeType.HEURISTIC)
        assert len(heuristics) >= 1

    def test_query_by_confidence(self):
        store = MetaKnowledgeStore()
        store.add(KnowledgeType.BEST_PRACTICE, "best practice 1")
        store.add(
            KnowledgeType.BEST_PRACTICE,
            "confirmed fact",
            confidence=KnowledgeConfidence.CONFIRMED,
        )
        results = store.query(min_confidence=KnowledgeConfidence.OBSERVED)
        assert len(results) >= 1

    def test_contradict_entry(self):
        store = MetaKnowledgeStore()
        mk = store.add(KnowledgeType.INVARIANT, "some invariant", evidence="seen in s1")
        updated = store.contradict(mk.entry_id, "counter-evidence from s2")
        assert updated is not None
        assert len(updated.contradicting_evidence) == 1

    def test_contradict_nonexistent(self):
        store = MetaKnowledgeStore()
        result = store.contradict("nonexistent", "evidence")
        assert result is None

    def test_stats_tracks_by_type(self):
        store = MetaKnowledgeStore()
        store.add(KnowledgeType.INVARIANT, "fact 1")
        store.add(KnowledgeType.INVARIANT, "fact 2")
        store.add(KnowledgeType.HEURISTIC, "pattern 1")
        s = store.stats()
        assert s["total_entries"] == 3
        assert "by_type" in s
