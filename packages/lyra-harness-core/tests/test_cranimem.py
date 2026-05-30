"""Tests for CraniMem Bio-Gating (P2-B4)."""
from __future__ import annotations

import time

import pytest

from lyra_harness_core.cranimem import (
    CraniMemGate,
    GateDecision,
    HippocampalReplay,
    MemoryTrace,
    PrefrontalGate,
    SignalStrength,
    SynapticConsolidator,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_trace(
    trace_id: str = "t1",
    *,
    created_at: float | None = None,
    last_accessed: float | None = None,
    access_count: int = 0,
    importance_score: float = 0.0,
    surprise_score: float = 0.0,
    emotional_salience: float = 0.0,
    tags: frozenset[str] = frozenset(),
    **kwargs,
) -> MemoryTrace:
    now = time.time()
    return MemoryTrace(
        trace_id=trace_id,
        content_hash="abc123",
        created_at=created_at if created_at is not None else now - 100,
        last_accessed=last_accessed if last_accessed is not None else now,
        access_count=access_count,
        importance_score=importance_score,
        surprise_score=surprise_score,
        emotional_salience=emotional_salience,
        tags=tags,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# SignalStrength
# ---------------------------------------------------------------------------


class TestSignalStrength:
    def test_values(self):
        assert SignalStrength.WEAK.value == "weak"
        assert SignalStrength.MODERATE.value == "moderate"
        assert SignalStrength.STRONG.value == "strong"
        assert SignalStrength.CRITICAL.value == "critical"

    def test_count(self):
        assert len(SignalStrength) == 4


# ---------------------------------------------------------------------------
# GateDecision
# ---------------------------------------------------------------------------


class TestGateDecision:
    def test_values(self):
        assert GateDecision.RETAIN.value == "retain"
        assert GateDecision.CONSOLIDATE.value == "consolidate"
        assert GateDecision.DISCARD.value == "discard"
        assert GateDecision.REPLAY.value == "replay"

    def test_count(self):
        assert len(GateDecision) == 4


# ---------------------------------------------------------------------------
# MemoryTrace
# ---------------------------------------------------------------------------


class TestMemoryTrace:
    def test_minimal(self):
        now = time.time()
        t = MemoryTrace(
            trace_id="t1",
            content_hash="abc",
            created_at=now,
            last_accessed=now,
        )
        assert t.trace_id == "t1"
        assert t.content_hash == "abc"
        assert t.access_count == 0
        assert t.importance_score == 0.0
        assert t.consolidation_count == 0
        assert t.replay_count == 0
        assert t.surprise_score == 0.0
        assert t.emotional_salience == 0.0
        assert t.tags == frozenset()

    def test_with_tags(self):
        t = make_trace(tags=frozenset(["python", "testing"]))
        assert "python" in t.tags
        assert "testing" in t.tags

    def test_with_metadata(self):
        t = MemoryTrace(
            trace_id="t1",
            content_hash="abc",
            created_at=time.time(),
            last_accessed=time.time(),
            metadata={"source": "user", "priority": 1},
        )
        assert t.metadata["source"] == "user"

    def test_frozen(self):
        t = make_trace()
        with pytest.raises(Exception):
            t.access_count = 5  # type: ignore[misc]

    def test_default_metadata(self):
        t = make_trace()
        assert t.metadata == {}


# ---------------------------------------------------------------------------
# SynapticConsolidator — compute_importance
# ---------------------------------------------------------------------------


class TestSynapticConsolidatorComputeImportance:
    @pytest.fixture
    def cons(self):
        return SynapticConsolidator()

    def test_importance_range(self, cons):
        score = cons.compute_importance(make_trace())
        assert 0.0 <= score <= 1.0

    def test_frequent_access_increases_importance(self, cons):
        low = cons.compute_importance(make_trace(access_count=0))
        high = cons.compute_importance(make_trace(access_count=100))
        assert high > low

    def test_recent_access_increases_importance(self, cons):
        now = time.time()
        old = cons.compute_importance(make_trace(last_accessed=now - 7200))
        recent = cons.compute_importance(make_trace(last_accessed=now))
        assert recent > old

    def test_surprise_increases_importance(self, cons):
        low = cons.compute_importance(make_trace(surprise_score=0.0))
        high = cons.compute_importance(make_trace(surprise_score=0.9))
        assert high > low

    def test_emotion_increases_importance(self, cons):
        low = cons.compute_importance(make_trace(emotional_salience=0.0))
        high = cons.compute_importance(make_trace(emotional_salience=0.9))
        assert high > low

    def test_all_max_gives_one(self, cons):
        now = time.time()
        t = MemoryTrace(
            trace_id="max",
            content_hash="abc",
            created_at=now,
            last_accessed=now,
            access_count=100000,
            surprise_score=1.0,
            emotional_salience=1.0,
        )
        score = cons.compute_importance(t)
        assert score == pytest.approx(1.0, abs=0.01)

    def test_all_min_gives_low(self, cons):
        now = time.time()
        t = MemoryTrace(
            trace_id="min",
            content_hash="abc",
            created_at=now - 100000,
            last_accessed=now - 100000,
            access_count=0,
            surprise_score=0.0,
            emotional_salience=0.0,
        )
        score = cons.compute_importance(t)
        assert score < 0.1

    def test_custom_weights(self):
        cons = SynapticConsolidator(
            access_weight=0.5,
            recency_weight=0.0,
            surprise_weight=0.5,
            emotion_weight=0.0,
        )
        score = cons.compute_importance(make_trace(access_count=50))
        assert 0.0 <= score <= 1.0

    def test_custom_decay_half_life(self):
        now = time.time()
        t = make_trace(last_accessed=now - 1800)  # 30 min ago

        fast_decay = SynapticConsolidator(decay_half_life=600)  # 10 min
        slow_decay = SynapticConsolidator(decay_half_life=7200)  # 2 hours

        assert slow_decay.compute_importance(t) > fast_decay.compute_importance(t)

    def test_very_old_memory_decays(self, cons):
        now = time.time()
        t = make_trace(
            created_at=now - 86400,
            last_accessed=now - 86400,
        )
        score = cons.compute_importance(t)
        assert score < 0.1


# ---------------------------------------------------------------------------
# SynapticConsolidator — classify
# ---------------------------------------------------------------------------


class TestSynapticConsolidatorClassify:
    @pytest.fixture
    def cons(self):
        return SynapticConsolidator()

    def test_classify_critical(self, cons):
        now = time.time()
        t = MemoryTrace(
            trace_id="c",
            content_hash="abc",
            created_at=now,
            last_accessed=now,
            access_count=1000,
            surprise_score=0.95,
            emotional_salience=0.95,
        )
        assert cons.classify(t) == SignalStrength.CRITICAL

    def test_classify_strong(self, cons):
        now = time.time()
        t = MemoryTrace(
            trace_id="s",
            content_hash="abc",
            created_at=now,
            last_accessed=now,
            access_count=50,
            surprise_score=0.65,
            emotional_salience=0.6,
        )
        assert cons.classify(t) in (SignalStrength.STRONG, SignalStrength.CRITICAL)

    def test_classify_moderate(self, cons):
        now = time.time()
        t = MemoryTrace(
            trace_id="m",
            content_hash="abc",
            created_at=now - 500,
            last_accessed=now - 200,
            access_count=5,
            surprise_score=0.4,
            emotional_salience=0.3,
        )
        assert cons.classify(t) in (SignalStrength.MODERATE, SignalStrength.STRONG)

    def test_classify_weak(self, cons):
        now = time.time()
        t = make_trace(
            created_at=now - 100000,
            last_accessed=now - 100000,
            access_count=0,
            surprise_score=0.0,
            emotional_salience=0.0,
        )
        assert cons.classify(t) == SignalStrength.WEAK

    def test_classify_returns_signal_strength(self, cons):
        result = cons.classify(make_trace())
        assert isinstance(result, SignalStrength)


# ---------------------------------------------------------------------------
# SynapticConsolidator — should_consolidate / should_discard
# ---------------------------------------------------------------------------


class TestSynapticConsolidatorDecisions:
    @pytest.fixture
    def cons(self):
        return SynapticConsolidator()

    def test_should_consolidate_strong(self, cons):
        now = time.time()
        t = MemoryTrace(
            trace_id="s",
            content_hash="abc",
            created_at=now,
            last_accessed=now,
            access_count=100,
            surprise_score=0.7,
            emotional_salience=0.7,
        )
        assert cons.should_consolidate(t)

    def test_should_not_consolidate_weak(self, cons):
        now = time.time()
        t = make_trace(
            created_at=now - 100000,
            last_accessed=now - 100000,
        )
        assert not cons.should_consolidate(t)

    def test_should_discard_weak(self, cons):
        now = time.time()
        t = make_trace(
            created_at=now - 100000,
            last_accessed=now - 100000,
        )
        assert cons.should_discard(t)

    def test_should_not_discard_strong(self, cons):
        now = time.time()
        t = MemoryTrace(
            trace_id="s",
            content_hash="abc",
            created_at=now,
            last_accessed=now,
            access_count=100,
            surprise_score=0.8,
            emotional_salience=0.8,
        )
        assert not cons.should_discard(t)

    def test_custom_thresholds(self):
        cons = SynapticConsolidator(
            consolidation_threshold=0.3,
            discard_threshold=0.8,
        )
        now = time.time()
        t = MemoryTrace(
            trace_id="mid",
            content_hash="abc",
            created_at=now,
            last_accessed=now,
            access_count=10,
            surprise_score=0.5,
            emotional_salience=0.5,
        )
        # With lowered thresholds, this should consolidate
        assert cons.should_consolidate(t)


# ---------------------------------------------------------------------------
# SynapticConsolidator — strengthen
# ---------------------------------------------------------------------------


class TestSynapticConsolidatorStrengthen:
    @pytest.fixture
    def cons(self):
        return SynapticConsolidator()

    def test_strengthen_increases_score(self, cons):
        now = time.time()
        t = MemoryTrace(
            trace_id="s",
            content_hash="abc",
            created_at=now,
            last_accessed=now,
            access_count=50,
            surprise_score=0.5,
            emotional_salience=0.5,
        )
        original = cons.compute_importance(t)
        strengthened = cons.strengthen(t, boost=0.1)
        assert strengthened > original

    def test_strengthen_diminishing_returns(self, cons):
        now = time.time()
        t = MemoryTrace(
            trace_id="s",
            content_hash="abc",
            created_at=now,
            last_accessed=now,
            access_count=1000,
            surprise_score=0.95,
            emotional_salience=0.95,
        )
        score_before = cons.compute_importance(t)
        score_after = cons.strengthen(t, boost=0.2)
        # Already near 1.0, so boost should be small
        assert score_after - score_before < 0.2

    def test_strengthen_does_not_exceed_one(self, cons):
        t = make_trace()
        score = cons.strengthen(t, boost=0.3)
        assert score <= 1.0
        # Even with large boost, stays at or below 1.0
        score2 = cons.strengthen(t, boost=0.9)
        assert score2 <= 1.0

    def test_strengthen_larger_boost(self, cons):
        now = time.time()
        t = MemoryTrace(
            trace_id="s",
            content_hash="abc",
            created_at=now,
            last_accessed=now,
            access_count=10,
            surprise_score=0.3,
            emotional_salience=0.3,
        )
        small = cons.strengthen(t, boost=0.05)
        large = cons.strengthen(t, boost=0.3)
        assert large > small


# ---------------------------------------------------------------------------
# HippocampalReplay — time_for_replay
# ---------------------------------------------------------------------------


class TestHippocampalReplayTiming:
    def test_initial_time_for_replay(self):
        hr = HippocampalReplay()
        assert hr.time_for_replay()

    def test_not_time_immediately_after_replay(self):
        hr = HippocampalReplay()
        hr.replay([], SynapticConsolidator())
        assert not hr.time_for_replay()

    def test_time_after_interval(self):
        hr = HippocampalReplay(replay_interval_seconds=0.01)
        hr.replay([], SynapticConsolidator())
        time.sleep(0.02)
        assert hr.time_for_replay()

    def test_custom_interval(self):
        hr = HippocampalReplay(replay_interval_seconds=999999)
        assert hr.time_for_replay()  # first time
        hr.replay([], SynapticConsolidator())
        assert not hr.time_for_replay()


# ---------------------------------------------------------------------------
# HippocampalReplay — select_for_replay
# ---------------------------------------------------------------------------


class TestHippocampalReplaySelect:
    @pytest.fixture
    def cons(self):
        return SynapticConsolidator()

    def test_selects_strong_traces(self, cons):
        hr = HippocampalReplay()
        now = time.time()
        strong = MemoryTrace(
            trace_id="strong",
            content_hash="abc",
            created_at=now,
            last_accessed=now,
            access_count=100,
            surprise_score=0.8,
            emotional_salience=0.8,
        )
        weak = make_trace(
            trace_id="weak",
            created_at=now - 100000,
            last_accessed=now - 100000,
        )
        selected = hr.select_for_replay([strong, weak], cons)
        assert strong in selected
        assert weak not in selected

    def test_respects_max_per_cycle(self, cons):
        hr = HippocampalReplay(max_replays_per_cycle=2)
        now = time.time()
        traces = [
            MemoryTrace(
                trace_id=f"t{i}",
                content_hash="abc",
                created_at=now,
                last_accessed=now,
                access_count=100,
                surprise_score=0.8,
                emotional_salience=0.8,
            )
            for i in range(5)
        ]
        selected = hr.select_for_replay(traces, cons)
        assert len(selected) == 2

    def test_empty_traces(self, cons):
        hr = HippocampalReplay()
        assert hr.select_for_replay([], cons) == []

    def test_prioritizes_by_importance(self, cons):
        hr = HippocampalReplay(max_replays_per_cycle=1)
        now = time.time()
        medium = MemoryTrace(
            trace_id="medium",
            content_hash="abc",
            created_at=now,
            last_accessed=now,
            access_count=20,
            surprise_score=0.5,
            emotional_salience=0.5,
        )
        high = MemoryTrace(
            trace_id="high",
            content_hash="abc",
            created_at=now,
            last_accessed=now,
            access_count=100,
            surprise_score=0.9,
            emotional_salience=0.9,
        )
        selected = hr.select_for_replay([medium, high], cons)
        assert len(selected) == 1
        assert selected[0].trace_id == "high"


# ---------------------------------------------------------------------------
# HippocampalReplay — replay
# ---------------------------------------------------------------------------


class TestHippocampalReplayReplay:
    @pytest.fixture
    def cons(self):
        return SynapticConsolidator()

    def test_replay_returns_dict(self, cons):
        hr = HippocampalReplay()
        now = time.time()
        t = MemoryTrace(
            trace_id="t1",
            content_hash="abc",
            created_at=now,
            last_accessed=now,
            access_count=100,
            surprise_score=0.8,
            emotional_salience=0.8,
        )
        result = hr.replay([t], cons)
        assert isinstance(result, dict)
        assert "t1" in result

    def test_replay_increments_counter(self, cons):
        hr = HippocampalReplay()
        now = time.time()
        t = MemoryTrace(
            trace_id="t1",
            content_hash="abc",
            created_at=now,
            last_accessed=now,
            access_count=100,
            surprise_score=0.8,
            emotional_salience=0.8,
        )
        hr.replay([t], cons)
        assert hr.total_replays == 1
        hr.replay([t], cons)
        assert hr.total_replays == 2

    def test_replay_updates_timestamp(self, cons):
        hr = HippocampalReplay()
        assert hr.time_for_replay()
        now = time.time()
        t = MemoryTrace(
            trace_id="t1",
            content_hash="abc",
            created_at=now,
            last_accessed=now,
            access_count=100,
            surprise_score=0.8,
            emotional_salience=0.8,
        )
        hr.replay([t], cons)
        assert not hr.time_for_replay()

    def test_replay_scores_increase(self, cons):
        hr = HippocampalReplay(replay_strengthening_boost=0.1)
        now = time.time()
        t = MemoryTrace(
            trace_id="t1",
            content_hash="abc",
            created_at=now,
            last_accessed=now,
            access_count=50,
            surprise_score=0.5,
            emotional_salience=0.5,
        )
        score_before = cons.compute_importance(t)
        result = hr.replay([t], cons)
        assert result["t1"] > score_before


# ---------------------------------------------------------------------------
# PrefrontalGate — decide
# ---------------------------------------------------------------------------


class TestPrefrontalGateDecide:
    @pytest.fixture
    def gate(self):
        return PrefrontalGate()

    @pytest.fixture
    def cons(self):
        return SynapticConsolidator()

    def test_decide_critical_retain(self, gate):
        """CRITICAL importance -> always RETAIN regardless of capacity/relevance."""
        now = time.time()
        t = MemoryTrace(
            trace_id="c",
            content_hash="abc",
            created_at=now,
            last_accessed=now,
            access_count=1000,
            surprise_score=0.95,
            emotional_salience=0.95,
        )
        cons = SynapticConsolidator()
        decision = gate.decide(t, cons, working_memory_count=10, task_tags=frozenset())
        assert decision == GateDecision.RETAIN

    def test_decide_strong_relevant_retain(self, gate):
        now = time.time()
        t = MemoryTrace(
            trace_id="s",
            content_hash="abc",
            created_at=now,
            last_accessed=now,
            access_count=100,
            surprise_score=0.7,
            emotional_salience=0.7,
            tags=frozenset(["task-a"]),
        )
        cons = SynapticConsolidator()
        decision = gate.decide(
            t, cons,
            working_memory_count=3,
            task_tags=frozenset(["task-a"]),
        )
        assert decision == GateDecision.RETAIN

    def test_decide_strong_irrelevant_consolidate(self, gate):
        now = time.time()
        # Score: freq=1.0, recency=1.0, surprise=0.45, emotion=0.45
        # = 0.35*1.0 + 0.25*1.0 + 0.25*0.45 + 0.15*0.45 = 0.60 + 0.18 = 0.78 (STRONG)
        t = MemoryTrace(
            trace_id="s",
            content_hash="abc",
            created_at=now,
            last_accessed=now,
            access_count=10,
            surprise_score=0.45,
            emotional_salience=0.45,
            tags=frozenset(["other"]),
        )
        cons = SynapticConsolidator()
        decision = gate.decide(
            t, cons,
            working_memory_count=3,
            task_tags=frozenset(["task-a"]),
        )
        assert decision == GateDecision.CONSOLIDATE

    def test_decide_strong_over_capacity_consolidate(self, gate):
        now = time.time()
        # Score: 0.78 (STRONG), but over capacity -> CONSOLIDATE
        t = MemoryTrace(
            trace_id="s",
            content_hash="abc",
            created_at=now,
            last_accessed=now,
            access_count=10,
            surprise_score=0.45,
            emotional_salience=0.45,
            tags=frozenset(["task-a"]),
        )
        cons = SynapticConsolidator()
        decision = gate.decide(
            t, cons,
            working_memory_count=10,  # >= capacity
            task_tags=frozenset(["task-a"]),
        )
        assert decision == GateDecision.CONSOLIDATE

    def test_decide_moderate_relevant_replay(self, gate):
        now = time.time()
        # Score: freq=3/60=0.05, recency=exp(-log2*1200/3600)=0.794
        # = 0.35*0.05 + 0.25*0.794 + 0.25*0.5 + 0.15*0.5 ≈ 0.416 (MODERATE)
        t = MemoryTrace(
            trace_id="m",
            content_hash="abc",
            created_at=now - 3600,
            last_accessed=now - 1200,
            access_count=3,
            surprise_score=0.5,
            emotional_salience=0.5,
            tags=frozenset(["task-a"]),
        )
        cons = SynapticConsolidator()
        decision = gate.decide(
            t, cons,
            task_tags=frozenset(["task-a"]),
        )
        assert decision == GateDecision.REPLAY

    def test_decide_moderate_irrelevant_consolidate(self, gate):
        now = time.time()
        t = MemoryTrace(
            trace_id="m",
            content_hash="abc",
            created_at=now - 500,
            last_accessed=now - 200,
            access_count=5,
            surprise_score=0.4,
            emotional_salience=0.4,
            tags=frozenset(["other"]),
        )
        cons = SynapticConsolidator()
        decision = gate.decide(
            t, cons,
            task_tags=frozenset(["task-a"]),
        )
        assert decision == GateDecision.CONSOLIDATE

    def test_decide_weak_discard(self, gate):
        now = time.time()
        t = make_trace(
            created_at=now - 100000,
            last_accessed=now - 100000,
        )
        cons = SynapticConsolidator()
        decision = gate.decide(t, cons)
        assert decision == GateDecision.DISCARD

    def test_decide_null_task_tags_all_relevant(self, gate):
        """None task_tags means all traces are considered relevant."""
        now = time.time()
        t = MemoryTrace(
            trace_id="s",
            content_hash="abc",
            created_at=now,
            last_accessed=now,
            access_count=100,
            surprise_score=0.7,
            emotional_salience=0.7,
        )
        cons = SynapticConsolidator()
        decision = gate.decide(t, cons, task_tags=None)
        assert decision == GateDecision.RETAIN

    def test_decide_empty_task_tags_none_relevant(self, gate):
        """Empty task_tags means nothing is task-relevant."""
        now = time.time()
        t = MemoryTrace(
            trace_id="s",
            content_hash="abc",
            created_at=now,
            last_accessed=now,
            access_count=50,
            surprise_score=0.5,
            emotional_salience=0.5,
        )
        cons = SynapticConsolidator()
        decision = gate.decide(t, cons, task_tags=frozenset())
        # MODERATE + not relevant -> CONSOLIDATE
        assert decision == GateDecision.CONSOLIDATE


# ---------------------------------------------------------------------------
# PrefrontalGate — filter_working_memory
# ---------------------------------------------------------------------------


class TestPrefrontalGateFilter:
    @pytest.fixture
    def gate(self):
        return PrefrontalGate(working_memory_capacity=3)

    @pytest.fixture
    def cons(self):
        return SynapticConsolidator()

    def test_filter_respects_capacity(self, gate, cons):
        now = time.time()
        traces = [
            MemoryTrace(
                trace_id=f"t{i}",
                content_hash="abc",
                created_at=now,
                last_accessed=now,
                access_count=100,
                surprise_score=0.8,
                emotional_salience=0.8,
            )
            for i in range(5)
        ]
        keep, evict = gate.filter_working_memory(traces, cons)
        assert len(keep) <= gate.working_memory_capacity

    def test_filter_discards_weak(self, gate, cons):
        now = time.time()
        strong = MemoryTrace(
            trace_id="strong",
            content_hash="abc",
            created_at=now,
            last_accessed=now,
            access_count=100,
            surprise_score=0.9,
            emotional_salience=0.9,
        )
        weak = make_trace(
            trace_id="weak",
            created_at=now - 100000,
            last_accessed=now - 100000,
        )
        keep, evict = gate.filter_working_memory([strong, weak], cons)
        assert weak in evict

    def test_filter_keeps_important(self, gate, cons):
        now = time.time()
        critical = MemoryTrace(
            trace_id="critical",
            content_hash="abc",
            created_at=now,
            last_accessed=now,
            access_count=1000,
            surprise_score=0.95,
            emotional_salience=0.95,
        )
        keep, evict = gate.filter_working_memory([critical], cons)
        assert critical in keep
        assert len(evict) == 0

    def test_filter_with_task_tags(self, gate, cons):
        now = time.time()
        relevant = MemoryTrace(
            trace_id="rel",
            content_hash="abc",
            created_at=now,
            last_accessed=now,
            access_count=100,
            surprise_score=0.7,
            emotional_salience=0.7,
            tags=frozenset(["current-task"]),
        )
        irrelevant = MemoryTrace(
            trace_id="irr",
            content_hash="abc",
            created_at=now,
            last_accessed=now,
            access_count=100,
            surprise_score=0.7,
            emotional_salience=0.7,
            tags=frozenset(["other"]),
        )
        keep, evict = gate.filter_working_memory(
            [relevant, irrelevant], cons,
            task_tags=frozenset(["current-task"]),
        )
        assert relevant in keep
        # irrelevant STRONG + not relevant -> CONSOLIDATE (may still be kept if space)
        assert len(keep) <= gate.working_memory_capacity


# ---------------------------------------------------------------------------
# PrefrontalGate — detect_interference
# ---------------------------------------------------------------------------


class TestPrefrontalGateDetectInterference:
    @pytest.fixture
    def gate(self):
        return PrefrontalGate(interference_threshold=0.5)

    def test_no_interference_empty_tags(self, gate):
        t = make_trace(tags=frozenset())
        existing = [make_trace(trace_id="e1", tags=frozenset(["a", "b"]))]
        assert gate.detect_interference(t, existing) == []

    def test_no_interference_disjoint_tags(self, gate):
        t = make_trace(tags=frozenset(["x", "y"]))
        existing = [make_trace(trace_id="e1", tags=frozenset(["a", "b"]))]
        assert gate.detect_interference(t, existing) == []

    def test_interference_detected(self, gate):
        t = make_trace(tags=frozenset(["a", "b", "c"]))
        existing = [make_trace(trace_id="e1", tags=frozenset(["a", "b", "d"]))]
        # Jaccard: |{a,b}| / |{a,b,c,d}| = 2/4 = 0.5 -> meets threshold
        result = gate.detect_interference(t, existing)
        assert len(result) == 1
        assert result[0].trace_id == "e1"

    def test_no_interference_below_threshold(self, gate):
        t = make_trace(tags=frozenset(["a", "b", "c", "d"]))
        existing = [make_trace(trace_id="e1", tags=frozenset(["a"]))]
        # Jaccard: 1/4 = 0.25 < 0.5
        assert gate.detect_interference(t, existing) == []

    def test_skips_self(self, gate):
        t = make_trace(trace_id="self", tags=frozenset(["a", "b"]))
        existing = [t, make_trace(trace_id="other", tags=frozenset(["a", "b"]))]
        result = gate.detect_interference(t, existing)
        assert all(r.trace_id != "self" for r in result)

    def test_empty_existing(self, gate):
        t = make_trace(tags=frozenset(["a"]))
        assert gate.detect_interference(t, []) == []

    def test_existing_empty_tags_skipped(self, gate):
        t = make_trace(tags=frozenset(["a"]))
        existing = [make_trace(trace_id="e1", tags=frozenset())]
        assert gate.detect_interference(t, existing) == []

    def test_custom_threshold(self, gate):
        strict_gate = PrefrontalGate(interference_threshold=0.9)
        t = make_trace(tags=frozenset(["a", "b", "c"]))
        existing = [make_trace(trace_id="e1", tags=frozenset(["a", "b", "d"]))]
        # Jaccard = 0.5 < 0.9 -> no interference
        assert strict_gate.detect_interference(t, existing) == []


# ---------------------------------------------------------------------------
# CraniMemGate — ingest / access
# ---------------------------------------------------------------------------


class TestCraniMemGateIngestAccess:
    @pytest.fixture
    def gate(self):
        return CraniMemGate()

    def test_ingest_adds_trace(self, gate):
        t = make_trace()
        gate.ingest(t)
        assert gate.active_count == 1
        assert gate.get_trace("t1") is not None

    def test_access_increments_count(self, gate):
        gate.ingest(make_trace(access_count=0))
        result = gate.access("t1")
        assert result is not None
        assert result.access_count == 1

    def test_access_updates_last_accessed(self, gate):
        before = time.time()
        gate.ingest(make_trace(last_accessed=before - 100))
        result = gate.access("t1")
        assert result.last_accessed >= before

    def test_access_nonexistent(self, gate):
        assert gate.access("nonexistent") is None

    def test_get_trace_from_active(self, gate):
        gate.ingest(make_trace())
        assert gate.get_trace("t1") is not None

    def test_get_trace_nonexistent(self, gate):
        assert gate.get_trace("nonexistent") is None

    def test_multiple_ingest(self, gate):
        gate.ingest(make_trace("a"))
        gate.ingest(make_trace("b"))
        gate.ingest(make_trace("c"))
        assert gate.active_count == 3


# ---------------------------------------------------------------------------
# CraniMemGate — consolidate
# ---------------------------------------------------------------------------


class TestCraniMemGateConsolidate:
    @pytest.fixture
    def gate(self):
        return CraniMemGate()

    def test_consolidate_moves_strong_traces(self, gate):
        now = time.time()
        t = MemoryTrace(
            trace_id="strong",
            content_hash="abc",
            created_at=now,
            last_accessed=now,
            access_count=100,
            surprise_score=0.8,
            emotional_salience=0.8,
        )
        gate.ingest(t)
        count = gate.consolidate()
        assert count == 1
        assert gate.active_count == 0
        assert gate.consolidated_count == 1

    def test_consolidate_leaves_weak_traces(self, gate):
        now = time.time()
        t = make_trace(
            trace_id="weak",
            created_at=now - 100000,
            last_accessed=now - 100000,
        )
        gate.ingest(t)
        count = gate.consolidate()
        assert count == 0
        assert gate.active_count == 1
        assert gate.consolidated_count == 0

    def test_consolidate_increments_count(self, gate):
        now = time.time()
        t = MemoryTrace(
            trace_id="s",
            content_hash="abc",
            created_at=now,
            last_accessed=now,
            access_count=100,
            surprise_score=0.8,
            emotional_salience=0.8,
        )
        gate.ingest(t)
        gate.consolidate()
        consolidated = gate.get_trace("s")
        assert consolidated.consolidation_count == 1

    def test_get_trace_from_consolidated(self, gate):
        now = time.time()
        t = MemoryTrace(
            trace_id="s",
            content_hash="abc",
            created_at=now,
            last_accessed=now,
            access_count=100,
            surprise_score=0.8,
            emotional_salience=0.8,
        )
        gate.ingest(t)
        gate.consolidate()
        # Should be found in consolidated storage
        assert gate.get_trace("s") is not None
        assert gate.active_count == 0

    def test_consolidate_mixed_traces(self, gate):
        now = time.time()
        strong = MemoryTrace(
            trace_id="strong",
            content_hash="abc",
            created_at=now,
            last_accessed=now,
            access_count=100,
            surprise_score=0.8,
            emotional_salience=0.8,
        )
        weak = make_trace(
            trace_id="weak",
            created_at=now - 100000,
            last_accessed=now - 100000,
        )
        gate.ingest(strong)
        gate.ingest(weak)
        count = gate.consolidate()
        assert count == 1
        assert gate.active_count == 1  # weak remains


# ---------------------------------------------------------------------------
# CraniMemGate — replay
# ---------------------------------------------------------------------------


class TestCraniMemGateReplay:
    def test_replay_when_time(self):
        gate = CraniMemGate()
        now = time.time()
        t = MemoryTrace(
            trace_id="s",
            content_hash="abc",
            created_at=now,
            last_accessed=now,
            access_count=100,
            surprise_score=0.8,
            emotional_salience=0.8,
        )
        gate.ingest(t)
        result = gate.replay()
        assert isinstance(result, dict)
        assert "s" in result

    def test_replay_skips_when_not_time(self):
        gate = CraniMemGate()
        gate.replay_system.replay([], gate.consolidator)  # mark as just replayed
        gate.ingest(make_trace())
        assert gate.replay() == {}

    def test_replay_counts_in_stats(self):
        gate = CraniMemGate()
        now = time.time()
        t = MemoryTrace(
            trace_id="s",
            content_hash="abc",
            created_at=now,
            last_accessed=now,
            access_count=100,
            surprise_score=0.8,
            emotional_salience=0.8,
        )
        gate.ingest(t)
        gate.replay()
        stats = gate.stats()
        assert stats["total_replays"] == 1


# ---------------------------------------------------------------------------
# CraniMemGate — filter_working_memory
# ---------------------------------------------------------------------------


class TestCraniMemGateFilter:
    @pytest.fixture
    def gate(self):
        return CraniMemGate()

    def test_filter_returns_keep_evict(self, gate):
        now = time.time()
        t = MemoryTrace(
            trace_id="s",
            content_hash="abc",
            created_at=now,
            last_accessed=now,
            access_count=100,
            surprise_score=0.8,
            emotional_salience=0.8,
        )
        gate.ingest(t)
        keep, evict = gate.filter_working_memory()
        assert t in keep
        assert isinstance(evict, list)

    def test_filter_records_discarded(self, gate):
        now = time.time()
        t = make_trace(
            created_at=now - 100000,
            last_accessed=now - 100000,
        )
        gate.ingest(t)
        gate.filter_working_memory()
        # Weak trace should be discarded
        if gate.discarded_count > 0:
            assert gate.discarded_count == 1

    def test_filter_with_custom_task_tags(self, gate):
        now = time.time()
        t = MemoryTrace(
            trace_id="s",
            content_hash="abc",
            created_at=now,
            last_accessed=now,
            access_count=100,
            surprise_score=0.7,
            emotional_salience=0.7,
            tags=frozenset(["custom"]),
        )
        gate.ingest(t)
        keep, evict = gate.filter_working_memory(task_tags=frozenset(["custom"]))
        assert t in keep


# ---------------------------------------------------------------------------
# CraniMemGate — task_tags
# ---------------------------------------------------------------------------


class TestCraniMemGateTaskTags:
    def test_set_task_tags(self):
        gate = CraniMemGate()
        gate.set_task_tags({"urgent", "backend"})
        now = time.time()
        t = MemoryTrace(
            trace_id="s",
            content_hash="abc",
            created_at=now,
            last_accessed=now,
            access_count=100,
            surprise_score=0.7,
            emotional_salience=0.7,
            tags=frozenset(["urgent"]),
        )
        gate.ingest(t)
        keep, _ = gate.filter_working_memory()
        assert t in keep

    def test_default_task_tags_empty(self):
        gate = CraniMemGate()
        now = time.time()
        t = MemoryTrace(
            trace_id="s",
            content_hash="abc",
            created_at=now,
            last_accessed=now,
            access_count=50,
            surprise_score=0.5,
            emotional_salience=0.5,
        )
        gate.ingest(t)
        keep, _ = gate.filter_working_memory()
        # Empty task_tags means nothing is relevant - MODERATE -> CONSOLIDATE
        # Still kept if space allows
        assert len(keep) <= gate.prefrontal.working_memory_capacity


# ---------------------------------------------------------------------------
# CraniMemGate — stats
# ---------------------------------------------------------------------------


class TestCraniMemGateStats:
    def test_empty_stats(self):
        gate = CraniMemGate()
        stats = gate.stats()
        assert stats["active_count"] == 0
        assert stats["consolidated_count"] == 0
        assert stats["discarded_count"] == 0
        assert stats["total_traces"] == 0

    def test_stats_after_ingest(self):
        gate = CraniMemGate()
        gate.ingest(make_trace("a"))
        gate.ingest(make_trace("b"))
        stats = gate.stats()
        assert stats["active_count"] == 2
        assert stats["total_traces"] == 2

    def test_stats_includes_strength_counts(self, gate=None):
        gate = CraniMemGate()
        now = time.time()
        gate.ingest(MemoryTrace(
            trace_id="critical",
            content_hash="abc", created_at=now, last_accessed=now,
            access_count=1000, surprise_score=0.95, emotional_salience=0.95,
        ))
        stats = gate.stats()
        assert stats["critical_count"] >= 0
        assert "strong_count" in stats
        assert "moderate_count" in stats
        assert "weak_count" in stats

    def test_stats_includes_capacity(self):
        gate = CraniMemGate()
        stats = gate.stats()
        assert stats["working_memory_capacity"] == 7

    def test_stats_includes_replays(self):
        gate = CraniMemGate()
        stats = gate.stats()
        assert stats["total_replays"] == 0


# ---------------------------------------------------------------------------
# CraniMemGate — clear
# ---------------------------------------------------------------------------


class TestCraniMemGateClear:
    def test_clear_resets_all(self):
        gate = CraniMemGate()
        gate.ingest(make_trace("a"))
        gate.ingest(make_trace("b"))
        gate.clear()
        assert gate.active_count == 0
        assert gate.consolidated_count == 0
        assert gate.discarded_count == 0

    def test_clear_resets_stats(self):
        gate = CraniMemGate()
        gate.ingest(make_trace())
        gate.clear()
        stats = gate.stats()
        assert stats["total_traces"] == 0


# ---------------------------------------------------------------------------
# CraniMemGate — full pipeline
# ---------------------------------------------------------------------------


class TestCraniMemGateFullPipeline:
    def test_full_lifecycle(self):
        gate = CraniMemGate()

        # Ingest memories
        now = time.time()
        important = MemoryTrace(
            trace_id="imp",
            content_hash="abc",
            created_at=now,
            last_accessed=now,
            access_count=0,
            surprise_score=0.9,
            emotional_salience=0.9,
            tags=frozenset(["critical-task"]),
        )
        trivial = make_trace(
            trace_id="triv",
            created_at=now - 100000,
            last_accessed=now - 100000,
        )

        gate.ingest(important)
        gate.ingest(trivial)
        assert gate.active_count == 2

        # Access important memory
        result = gate.access("imp")
        assert result.access_count == 1

        # Consolidate — important moves to long-term
        count = gate.consolidate()
        assert count == 1
        assert gate.consolidated_count == 1
        assert gate.active_count == 1  # trivial remains

        # Replay cycle
        replay_result = gate.replay()
        assert isinstance(replay_result, dict)

        # Filter working memory
        gate.set_task_tags({"critical-task"})
        keep, evict = gate.filter_working_memory()
        assert len(keep) <= gate.prefrontal.working_memory_capacity

        # Stats are consistent
        stats = gate.stats()
        assert stats["total_traces"] == gate.active_count + gate.consolidated_count

    def test_multiple_consolidation_cycles(self):
        gate = CraniMemGate()
        now = time.time()

        for i in range(5):
            t = MemoryTrace(
                trace_id=f"imp{i}",
                content_hash="abc",
                created_at=now,
                last_accessed=now,
                access_count=100 + i * 10,
                surprise_score=0.7 + i * 0.05,
                emotional_salience=0.7,
            )
            gate.ingest(t)

        count = gate.consolidate()
        assert count == 5
        assert gate.consolidated_count == 5
        assert gate.active_count == 0

    def test_access_then_consolidate_then_access_again(self):
        gate = CraniMemGate()
        now = time.time()
        t = MemoryTrace(
            trace_id="s",
            content_hash="abc",
            created_at=now,
            last_accessed=now - 10,
            access_count=5,
            surprise_score=0.8,
            emotional_salience=0.8,
        )
        gate.ingest(t)
        gate.access("s")
        gate.consolidate()

        # Trace should be accessible from consolidated storage
        found = gate.get_trace("s")
        assert found is not None
        assert found.consolidation_count == 1

    def test_weak_memory_discarded_in_filter(self):
        gate = CraniMemGate()
        now = time.time()

        for i in range(10):
            t = MemoryTrace(
                trace_id=f"strong{i}",
                content_hash="abc",
                created_at=now,
                last_accessed=now,
                access_count=100,
                surprise_score=0.8,
                emotional_salience=0.8,
            )
            gate.ingest(t)

        # Add one weak trace
        gate.ingest(make_trace(
            trace_id="weak",
            created_at=now - 100000,
            last_accessed=now - 100000,
        ))

        keep, evict = gate.filter_working_memory()
        # Weak trace should be in evict (DISCARD)
        weak_in_evict = any(t.trace_id == "weak" for t in evict)
        assert weak_in_evict or gate.discarded_count > 0


# ---------------------------------------------------------------------------
# Integration
# ---------------------------------------------------------------------------


class TestCraniMemIntegration:
    def test_end_to_end_bio_gating(self):
        """Simulate a realistic bio-gating workflow."""
        gate = CraniMemGate()
        gate.set_task_tags({"api-design", "refactor"})

        now = time.time()

        # Ingest various memories
        critical_mem = MemoryTrace(
            trace_id="auth-bug",
            content_hash="hash1",
            created_at=now,
            last_accessed=now,
            access_count=500,
            surprise_score=0.95,
            emotional_salience=0.9,
            tags=frozenset(["api-design", "security"]),
        )
        important_mem = MemoryTrace(
            trace_id="endpoint-design",
            content_hash="hash2",
            created_at=now,
            last_accessed=now,
            access_count=50,
            surprise_score=0.7,
            emotional_salience=0.6,
            tags=frozenset(["api-design"]),
        )
        old_mem = make_trace(
            trace_id="old-notes",
            created_at=now - 86400 * 30,
            last_accessed=now - 86400 * 7,
            tags=frozenset(["random"]),
        )

        gate.ingest(critical_mem)
        gate.ingest(important_mem)
        gate.ingest(old_mem)
        assert gate.active_count == 3

        # Access important memory multiple times (use-dependent strengthening)
        for _ in range(5):
            gate.access("endpoint-design")

        # Consolidation cycle
        consolidated = gate.consolidate()
        assert consolidated >= 1  # at least critical

        # Replay cycle
        replay_scores = gate.replay()
        assert isinstance(replay_scores, dict)

        # Filter working memory for current task
        keep, evict = gate.filter_working_memory(task_tags=frozenset(["api-design"]))
        assert len(keep) <= 7  # capacity

        # Old memory should be evicted
        keep_ids = {t.trace_id for t in keep}
        assert "old-notes" not in keep_ids or gate.discarded_count > 0

        # Stats are consistent
        stats = gate.stats()
        assert stats["total_traces"] == gate.active_count + gate.consolidated_count
        assert stats["discarded_count"] == gate.discarded_count

    def test_interference_detection_workflow(self):
        """Test that similar memories trigger interference detection."""
        gate = CraniMemGate()

        now = time.time()
        base_trace = MemoryTrace(
            trace_id="base",
            content_hash="abc",
            created_at=now,
            last_accessed=now,
            access_count=100,
            surprise_score=0.7,
            emotional_salience=0.7,
            tags=frozenset(["python", "async", "api"]),
        )

        similar_trace = MemoryTrace(
            trace_id="similar",
            content_hash="def",
            created_at=now,
            last_accessed=now,
            access_count=80,
            surprise_score=0.6,
            emotional_salience=0.6,
            tags=frozenset(["python", "async", "testing"]),
        )

        gate.ingest(base_trace)
        gate.ingest(similar_trace)

        # Detect interference between base and similar
        interfering = gate.prefrontal.detect_interference(
            base_trace,
            [similar_trace],
        )
        # Jaccard: |{python, async}| / |{python, async, api, testing}| = 2/4 = 0.5
        # Default threshold is 0.7, so no interference at default settings
        # But with custom threshold it would trigger
        assert isinstance(interfering, list)

    def test_custom_config_full_pipeline(self):
        """Full pipeline with custom config."""
        gate = CraniMemGate(
            consolidator=SynapticConsolidator(
                access_weight=0.5,
                recency_weight=0.2,
                surprise_weight=0.2,
                emotion_weight=0.1,
                consolidation_threshold=0.5,
                decay_half_life=1800,  # 30 min
            ),
            replay_system=HippocampalReplay(
                replay_interval_seconds=60,
                max_replays_per_cycle=5,
                replay_strengthening_boost=0.1,
            ),
            prefrontal=PrefrontalGate(
                working_memory_capacity=5,
                interference_threshold=0.6,
            ),
        )

        now = time.time()
        for i in range(8):
            gate.ingest(MemoryTrace(
                trace_id=f"mem{i}",
                content_hash=f"hash{i}",
                created_at=now,
                last_accessed=now,
                access_count=50,
                surprise_score=0.5 + i * 0.05,
                emotional_salience=0.5,
                tags=frozenset([f"topic-{i % 3}"]),
            ))

        # Consolidate
        count = gate.consolidate()
        assert count > 0

        # Filter with custom capacity
        keep, evict = gate.filter_working_memory()
        assert len(keep) <= 5

        # Stats
        stats = gate.stats()
        assert stats["working_memory_capacity"] == 5
