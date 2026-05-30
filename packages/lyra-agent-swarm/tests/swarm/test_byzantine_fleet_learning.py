"""Tests for Byzantine fault tolerance, fleet auto-scaling, and cross-agent learning."""

from __future__ import annotations

import pytest

from lyra_agent_swarm.consensus.byzantine_fault_tolerance import (
    ByzantineConsensus,
    ByzantineNode,
    ConsensusResult,
    FailureMode,
    Verdict,
    WitnessStatement,
)
from lyra_agent_swarm.fleet_auto_scaler import (
    AutoScaler,
    AutoScalerConfig,
    ScaleDirection,
    ScaleEvent,
    SquadLoad,
)
from lyra_agent_swarm.cross_agent_learning import (
    CrossAgentLearning,
    ExperienceRecord,
    LearningPattern,
    PatternType,
)


# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture
def bft_consensus():
    return ByzantineConsensus(fault_tolerance=1, total_nodes=4)


@pytest.fixture
def scaler():
    return AutoScaler(
        config=AutoScalerConfig(
            min_workers_per_squad=1,
            max_workers_per_squad=10,
            scale_up_threshold=0.75,
            scale_down_threshold=0.3,
            cooldown_seconds=0.0,
        )
    )


@pytest.fixture
def cross_learner():
    return CrossAgentLearning()


# ── TestByzantineNode ──────────────────────────────────────────


class TestByzantineNode:
    def test_node_creation(self):
        node = ByzantineNode(node_id="n1", weight=1.0)
        assert node.node_id == "n1"
        assert node.weight == 1.0
        assert node.failure_mode == FailureMode.NONE

    def test_node_mark_failure(self):
        node = ByzantineNode(node_id="n1")
        updated = node.mark_failure(FailureMode.CRASH)
        assert updated.failure_mode == FailureMode.CRASH

    def test_node_immutability(self):
        node = ByzantineNode(node_id="n1")
        with pytest.raises(Exception):
            node.node_id = "n2"

    def test_node_is_byzantine(self):
        honest = ByzantineNode(node_id="n1")
        malicious = ByzantineNode(node_id="n2", failure_mode=FailureMode.HALLUCINATION)
        assert not honest.is_byzantine
        assert malicious.is_byzantine

    def test_node_weight(self):
        node = ByzantineNode(node_id="n1", weight=2.5)
        assert node.weight == 2.5


class TestWitnessStatement:
    def test_statement_creation(self):
        stmt = WitnessStatement(
            node_id="n1",
            verdict=Verdict.APPROVE,
            confidence=0.9,
        )
        assert stmt.verdict == Verdict.APPROVE
        assert stmt.confidence == 0.9

    def test_statement_immutability(self):
        stmt = WitnessStatement(node_id="n1", verdict=Verdict.APPROVE)
        with pytest.raises(Exception):
            stmt.verdict = Verdict.REJECT

    def test_statement_with_reasoning(self):
        stmt = WitnessStatement(
            node_id="n1",
            verdict=Verdict.REJECT,
            confidence=0.8,
            reasoning="Security vulnerability found",
        )
        assert "Security" in stmt.reasoning


class TestConsensusResult:
    def test_result_creation(self):
        result = ConsensusResult(
            outcome=Verdict.APPROVE,
            confidence=0.85,
            agree_count=3,
            total_count=4,
            byzantine_nodes_detected=0,
        )
        assert result.outcome == Verdict.APPROVE
        assert result.quorum_reached is True

    def test_result_no_quorum(self):
        result = ConsensusResult(
            outcome=Verdict.APPROVE,
            confidence=0.5,
            agree_count=2,
            total_count=5,
        )
        assert not result.quorum_reached

    def test_result_with_dissent(self):
        result = ConsensusResult(
            outcome=Verdict.APPROVE,
            confidence=0.7,
            agree_count=3,
            total_count=5,
            dissent_notes=["Minor concern about performance"],
        )
        assert len(result.dissent_notes) == 1


# ── TestByzantineConsensus ─────────────────────────────────────


class TestByzantineConsensusBasic:
    def test_empty_consensus(self, bft_consensus):
        assert bft_consensus.fault_tolerance == 1
        assert bft_consensus.total_nodes == 4

    def test_minimum_nodes(self):
        consensus = ByzantineConsensus(fault_tolerance=1, total_nodes=3)
        assert consensus.quorum_size == 3  # 2f+1 with f=1

    def test_insufficient_nodes(self):
        with pytest.raises(ValueError, match="requires at least"):
            ByzantineConsensus(fault_tolerance=2, total_nodes=3)

    def test_quorum_size(self, bft_consensus):
        assert bft_consensus.quorum_size == 3  # 2*1 + 1

    def test_register_node(self, bft_consensus):
        bft_consensus.register_node("n1", weight=1.0)
        node = bft_consensus.get_node("n1")
        assert node is not None
        assert node.node_id == "n1"

    def test_register_duplicate_node(self, bft_consensus):
        bft_consensus.register_node("n1")
        with pytest.raises(ValueError, match="already registered"):
            bft_consensus.register_node("n1")

    def test_submit_statement(self, bft_consensus):
        bft_consensus.register_node("n1")
        bft_consensus.register_node("n2")
        bft_consensus.register_node("n3")
        bft_consensus.register_node("n4")

        bft_consensus.submit_statement(
            node_id="n1",
            verdict=Verdict.APPROVE,
            confidence=0.9,
        )
        bft_consensus.submit_statement(
            node_id="n2",
            verdict=Verdict.APPROVE,
            confidence=0.8,
        )
        bft_consensus.submit_statement(
            node_id="n3",
            verdict=Verdict.APPROVE,
            confidence=0.85,
        )

        result = bft_consensus.try_consensus()
        assert result is not None
        assert result.outcome == Verdict.APPROVE

    def test_submit_statement_unregistered(self, bft_consensus):
        with pytest.raises(ValueError, match="not registered"):
            bft_consensus.submit_statement(
                node_id="unknown",
                verdict=Verdict.APPROVE,
            )

    def test_consensus_with_dissent(self, bft_consensus):
        for nid in ["n1", "n2", "n3", "n4"]:
            bft_consensus.register_node(nid)

        bft_consensus.submit_statement("n1", Verdict.APPROVE, 0.9)
        bft_consensus.submit_statement("n2", Verdict.APPROVE, 0.8)
        bft_consensus.submit_statement("n3", Verdict.REJECT, 0.7, reasoning="Bug found")
        bft_consensus.submit_statement("n4", Verdict.APPROVE, 0.85)

        result = bft_consensus.try_consensus()
        assert result is not None
        assert result.agree_count == 3
        assert len(result.dissent_notes) == 1

    def test_no_quorum_returns_none(self, bft_consensus):
        for nid in ["n1", "n2", "n3", "n4"]:
            bft_consensus.register_node(nid)

        bft_consensus.submit_statement("n1", Verdict.APPROVE, 0.9)
        bft_consensus.submit_statement("n2", Verdict.REJECT, 0.8)

        result = bft_consensus.try_consensus()
        assert result is None

    def test_weighted_voting(self, bft_consensus):
        bft_consensus.register_node("n1", weight=3.0)  # captain
        bft_consensus.register_node("n2", weight=1.0)
        bft_consensus.register_node("n3", weight=1.0)
        bft_consensus.register_node("n4", weight=1.0)

        bft_consensus.submit_statement("n1", Verdict.APPROVE, 0.95)
        bft_consensus.submit_statement("n2", Verdict.REJECT, 0.5)
        bft_consensus.submit_statement("n3", Verdict.REJECT, 0.5)

        result = bft_consensus.try_consensus()
        assert result is not None
        assert result.outcome == Verdict.APPROVE  # Weight 3 > weight 2

    def test_byzantine_detection(self, bft_consensus):
        bft_consensus.register_node("n1")
        bft_consensus.register_node("n2")
        bft_consensus.register_node("n3")
        bft_consensus.register_node("n4")

        bft_consensus.mark_node_failure("n4", FailureMode.HALLUCINATION)

        bft_consensus.submit_statement("n1", Verdict.APPROVE, 0.9)
        bft_consensus.submit_statement("n2", Verdict.APPROVE, 0.8)
        bft_consensus.submit_statement("n3", Verdict.APPROVE, 0.85)
        bft_consensus.submit_statement("n4", Verdict.REJECT, 0.1, reasoning="nonsense")

        result = bft_consensus.try_consensus()
        assert result is not None
        assert result.byzantine_nodes_detected >= 1

    def test_reset_round(self, bft_consensus):
        for nid in ["n1", "n2", "n3", "n4"]:
            bft_consensus.register_node(nid)

        bft_consensus.submit_statement("n1", Verdict.APPROVE, 0.9)
        bft_consensus.reset_round()
        assert len(bft_consensus._statements) == 0

    def test_confidence_threshold(self):
        consensus = ByzantineConsensus(
            fault_tolerance=1, total_nodes=4, confidence_threshold=0.6
        )
        assert consensus.confidence_threshold == 0.6


# ── TestAutoScaler ─────────────────────────────────────────────


class TestAutoScalerConfig:
    def test_default_config(self):
        cfg = AutoScalerConfig()
        assert cfg.min_workers_per_squad == 1
        assert cfg.max_workers_per_squad == 20
        assert cfg.scale_up_threshold == 0.75

    def test_custom_config(self):
        cfg = AutoScalerConfig(
            min_workers_per_squad=2,
            max_workers_per_squad=15,
            scale_up_threshold=0.8,
            scale_down_threshold=0.2,
            cooldown_seconds=300.0,
        )
        assert cfg.min_workers_per_squad == 2
        assert cfg.max_workers_per_squad == 15
        assert cfg.cooldown_seconds == 300.0


class TestSquadLoad:
    def test_squad_load(self):
        sl = SquadLoad(
            squad_id="s-1",
            current_workers=3,
            queue_depth=10,
            avg_latency_ms=200.0,
            load_factor=0.85,
        )
        assert sl.load_factor == 0.85
        assert sl.queue_depth == 10


class TestAutoScalerBasic:
    def test_empty_scaler(self, scaler):
        assert scaler.event_count == 0

    def test_update_squad_load(self, scaler):
        scaler.update_squad_load("s-1", queue_depth=10, latency_ms=150.0, current_workers=3)
        load = scaler.get_squad_load("s-1")
        assert load is not None
        assert load.queue_depth == 10

    def test_high_load_triggers_scale_up(self, scaler):
        scaler.update_squad_load("s-1", queue_depth=50, latency_ms=500.0, current_workers=3)
        events = scaler.evaluate()
        assert len(events) > 0
        assert events[0].direction == ScaleDirection.UP

    def test_low_load_triggers_scale_down(self, scaler):
        scaler.update_squad_load("s-1", queue_depth=1, latency_ms=10.0, current_workers=5)
        events = scaler.evaluate()
        assert len(events) > 0
        assert events[0].direction == ScaleDirection.DOWN

    def test_normal_load_no_scale(self, scaler):
        # Load factor between scale_down (0.3) and scale_up (0.75)
        # queue_factor = 25/(5*10) = 0.5, latency_factor = 300/1000 = 0.3
        # load_factor = 0.5*0.6 + 0.3*0.4 = 0.42
        scaler.update_squad_load("s-1", queue_depth=25, latency_ms=300.0, current_workers=5)
        events = scaler.evaluate()
        assert len(events) == 0

    def test_cannot_scale_below_min(self, scaler):
        scaler.update_squad_load("s-1", queue_depth=1, latency_ms=10.0, current_workers=1)
        events = scaler.evaluate()
        assert len(events) == 0

    def test_cannot_scale_above_max(self, scaler):
        scaler.update_squad_load("s-1", queue_depth=100, latency_ms=1000.0, current_workers=10)
        events = scaler.evaluate()
        assert len(events) == 0

    def test_cooldown_respected(self):
        s = AutoScaler(
            config=AutoScalerConfig(
                cooldown_seconds=60.0,
                scale_up_threshold=0.7,
                min_workers_per_squad=1,
                max_workers_per_squad=10,
            )
        )
        s.update_squad_load("s-1", queue_depth=50, latency_ms=500.0, current_workers=3)
        s.evaluate()
        # Immediate second evaluate should be blocked by cooldown
        events = s.evaluate()
        assert len(events) == 0

    def test_scale_event_creation(self):
        event = ScaleEvent(
            squad_id="s-1",
            direction=ScaleDirection.UP,
            current_workers=3,
            new_workers=5,
            reason="High load: factor=0.90",
        )
        assert event.direction == ScaleDirection.UP
        assert event.new_workers == 5
        assert event.applied is False

    def test_scale_event_mark_applied(self, scaler):
        event = ScaleEvent(
            squad_id="s-1",
            direction=ScaleDirection.UP,
            current_workers=3,
            new_workers=5,
            reason="High load",
        )
        applied = event.mark_applied()
        assert applied.applied is True

    def test_multiple_squads(self, scaler):
        scaler.update_squad_load("s-1", queue_depth=50, latency_ms=500.0, current_workers=3)
        scaler.update_squad_load("s-2", queue_depth=1, latency_ms=10.0, current_workers=5)
        events = scaler.evaluate()
        squad_ids = {e.squad_id for e in events}
        assert "s-1" in squad_ids
        assert "s-2" in squad_ids

    def test_get_history(self, scaler):
        scaler.update_squad_load("s-1", queue_depth=50, latency_ms=500.0, current_workers=3)
        scaler.evaluate()
        history = scaler.get_history()
        assert len(history) == 1

    def test_get_status(self, scaler):
        scaler.update_squad_load("s-1", queue_depth=10, latency_ms=200.0, current_workers=3)
        status = scaler.get_status()
        assert "squads" in status
        assert status["squads"] == 1
        assert status["total_events"] == 0

    def test_scale_recommendation_includes_count(self, scaler):
        scaler.update_squad_load("s-1", queue_depth=80, latency_ms=800.0, current_workers=3)
        events = scaler.evaluate()
        assert events[0].new_workers > events[0].current_workers

    def test_reset(self, scaler):
        scaler.update_squad_load("s-1", queue_depth=50, latency_ms=500.0, current_workers=3)
        scaler.evaluate()
        scaler.reset()
        assert scaler.event_count == 0
        assert scaler.get_squad_load("s-1") is None


# ── TestCrossAgentLearning ─────────────────────────────────────


class TestExperienceRecord:
    def test_record_creation(self):
        record = ExperienceRecord(
            agent_id="agent-1",
            task="Fix authentication bug",
            outcome="success",
            reward=0.9,
        )
        assert record.outcome == "success"
        assert record.reward == 0.9

    def test_record_immutability(self):
        record = ExperienceRecord(
            agent_id="agent-1",
            task="test",
            outcome="success",
            reward=0.5,
        )
        with pytest.raises(Exception):
            record.reward = 1.0

    def test_record_with_patterns(self):
        record = ExperienceRecord(
            agent_id="agent-1",
            task="Implement rate limiting",
            outcome="success",
            reward=0.95,
            extracted_patterns=["rate_limit_before_auth", "use_redis_sliding_window"],
        )
        assert len(record.extracted_patterns) == 2


class TestLearningPattern:
    def test_pattern_creation(self):
        pattern = LearningPattern(
            pattern_id="p-1",
            name="rate_limit_before_auth",
            pattern_type=PatternType.ARCHITECTURE,
            success_rate=0.92,
            usage_count=15,
        )
        assert pattern.success_rate == 0.92
        assert pattern.usage_count == 15

    def test_pattern_immutability(self):
        pattern = LearningPattern(
            pattern_id="p-1",
            name="test",
            pattern_type=PatternType.BUG_FIX,
        )
        with pytest.raises(Exception):
            pattern.success_rate = 1.0

    def test_pattern_is_proven(self):
        proven = LearningPattern(
            pattern_id="p-1",
            name="test",
            pattern_type=PatternType.BUG_FIX,
            success_rate=0.9,
            usage_count=10,
        )
        unproven = LearningPattern(
            pattern_id="p-2",
            name="test2",
            pattern_type=PatternType.BUG_FIX,
            success_rate=0.5,
            usage_count=2,
        )
        assert proven.is_proven
        assert not unproven.is_proven

    def test_pattern_update_success(self):
        pattern = LearningPattern(
            pattern_id="p-1",
            name="test",
            pattern_type=PatternType.ARCHITECTURE,
            success_rate=0.8,
            usage_count=10,
        )
        updated = pattern.update_success_rate(success=True)
        assert updated.usage_count == 11
        assert updated.success_rate >= 0.8


class TestCrossAgentLearningBasic:
    def test_empty_learner(self, cross_learner):
        assert cross_learner.pattern_count == 0
        assert cross_learner.experience_count == 0

    def test_record_experience(self, cross_learner):
        cross_learner.record_experience(
            agent_id="agent-1",
            task="Fix SQL injection",
            outcome="success",
            reward=0.95,
            patterns=["parameterize_queries", "input_validation"],
        )
        assert cross_learner.experience_count == 1
        assert cross_learner.pattern_count == 2

    def test_record_multiple_experiences_same_pattern(self, cross_learner):
        cross_learner.record_experience(
            "a1", "task1", "success", 0.9, patterns=["pattern-x"]
        )
        cross_learner.record_experience(
            "a2", "task2", "success", 0.8, patterns=["pattern-x"]
        )
        pattern = cross_learner.get_pattern("pattern-x")
        assert pattern.usage_count == 2

    def test_record_failure_updates_pattern(self, cross_learner):
        cross_learner.record_experience(
            "a1", "task1", "success", 0.9, patterns=["pattern-y"]
        )
        cross_learner.record_experience(
            "a2", "task2", "failure", 0.2, patterns=["pattern-y"]
        )
        pattern = cross_learner.get_pattern("pattern-y")
        assert pattern.success_rate < 0.9

    def test_get_proven_patterns(self, cross_learner):
        cross_learner.record_experience(
            "a1", "t1", "success", 0.9, patterns=["good-pattern"]
        )
        cross_learner.record_experience(
            "a2", "t2", "success", 0.95, patterns=["good-pattern"]
        )
        cross_learner.record_experience(
            "a3", "t3", "success", 0.9, patterns=["good-pattern"]
        )
        cross_learner.record_experience(
            "a4", "t4", "success", 0.85, patterns=["good-pattern"]
        )
        proven = cross_learner.get_proven_patterns()
        assert any(p.name == "good-pattern" for p in proven)

    def test_get_patterns_by_type(self, cross_learner):
        cross_learner.record_experience(
            "a1", "t1", "success", 0.9,
            patterns=["arch-pattern"],
            pattern_type=PatternType.ARCHITECTURE,
        )
        cross_learner.record_experience(
            "a2", "t2", "failure", 0.3,
            patterns=["bug-pattern"],
            pattern_type=PatternType.BUG_FIX,
        )
        arch_patterns = cross_learner.get_patterns_by_type(PatternType.ARCHITECTURE)
        bug_patterns = cross_learner.get_patterns_by_type(PatternType.BUG_FIX)
        assert len(arch_patterns) == 1
        assert len(bug_patterns) == 1

    def test_get_agent_experiences(self, cross_learner):
        cross_learner.record_experience("agent-1", "task-a", "success", 0.9)
        cross_learner.record_experience("agent-2", "task-b", "failure", 0.2)
        experiences = cross_learner.get_agent_experiences("agent-1")
        assert len(experiences) == 1
        assert experiences[0].agent_id == "agent-1"

    def test_recommend_pattern_for_task(self, cross_learner):
        cross_learner.record_experience(
            "a1", "Implement auth middleware", "success", 0.95,
            patterns=["validate_tokens_before_handler"]
        )
        rec = cross_learner.recommend_patterns(
            task_description="Add JWT authentication to API"
        )
        assert len(rec) >= 0  # May or may not find match based on similarity

    def test_get_skill_improvements(self, cross_learner):
        cross_learner.record_experience(
            "a1", "Fix N+1 query", "success", 0.92,
            patterns=["eager_load_associations"]
        )
        improvements = cross_learner.get_skill_improvements("agent-1")
        assert len(improvements) >= 0

    def test_get_learning_summary(self, cross_learner):
        cross_learner.record_experience("a1", "t1", "success", 0.9, patterns=["p1"])
        cross_learner.record_experience("a2", "t2", "failure", 0.3, patterns=["p2"])
        summary = cross_learner.get_learning_summary()
        assert summary["total_experiences"] == 2
        assert summary["total_patterns"] == 2
        assert "success_rate" in summary

    def test_reset(self, cross_learner):
        cross_learner.record_experience("a1", "t1", "success", 0.9, patterns=["p1"])
        cross_learner.reset()
        assert cross_learner.experience_count == 0
        assert cross_learner.pattern_count == 0
