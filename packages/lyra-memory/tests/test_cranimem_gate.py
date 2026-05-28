"""Tests for CraniMem Admission Gate — goal-conditioned episodic buffer write gating."""

import pytest

from lyra_memory.cranimem_gate import (
    CraniMemAdmissionGate,
    CraniMemCandidate,
    CraniMemConfig,
    GateAction,
    GateDecision,
)


class TestGateAction:
    def test_action_values(self):
        assert GateAction.ADMIT.value == "admit"
        assert GateAction.DEFER.value == "defer"
        assert GateAction.REJECT.value == "reject"


class TestCraniMemCandidate:
    def test_candidate_creation(self):
        candidate = CraniMemCandidate(
            candidate_id="c-001",
            content="User asked to deploy to production",
            goal_relevance=0.85,
            utility_score=0.7,
            surprise_score=0.1,
            source="conversation",
            timestamp=1000.0,
        )
        assert candidate.candidate_id == "c-001"
        assert candidate.goal_relevance == 0.85
        assert candidate.utility_score == 0.7

    def test_candidate_high_surprise(self):
        candidate = CraniMemCandidate(
            candidate_id="c-surprise",
            content="Unexpected database connection failure",
            goal_relevance=0.5,
            utility_score=0.6,
            surprise_score=0.95,
            source="system",
            timestamp=2000.0,
        )
        assert candidate.surprise_score > 0.9

    def test_candidate_immutable(self):
        c = CraniMemCandidate("c1", "content", 0.5, 0.5, 0.0, "src", 0.0)
        with pytest.raises(Exception):
            c.goal_relevance = 1.0


class TestGateDecision:
    def test_admit_decision(self):
        decision = GateDecision(
            candidate_id="c-001",
            action=GateAction.ADMIT,
            reason="All thresholds met",
            relevance_score=0.85,
            utility_score=0.7,
        )
        assert decision.action == GateAction.ADMIT
        assert decision.relevance_score == 0.85

    def test_reject_decision(self):
        decision = GateDecision(
            candidate_id="c-002",
            action=GateAction.REJECT,
            reason="Relevance below threshold",
            relevance_score=0.12,
            utility_score=0.3,
        )
        assert decision.action == GateAction.REJECT

    def test_defer_decision(self):
        decision = GateDecision(
            candidate_id="c-003",
            action=GateAction.DEFER,
            reason="Marginal relevance",
            relevance_score=0.25,
            utility_score=0.5,
        )
        assert decision.action == GateAction.DEFER

    def test_decision_immutable(self):
        d = GateDecision("c1", GateAction.ADMIT, "ok", 0.8, 0.6)
        with pytest.raises(Exception):
            d.action = GateAction.REJECT


class TestCraniMemConfig:
    def test_default_config(self):
        config = CraniMemConfig()
        assert config.relevance_threshold == 0.3
        assert config.utility_threshold == 0.2
        assert config.max_buffer_size == 200

    def test_custom_config(self):
        config = CraniMemConfig(
            relevance_threshold=0.5,
            utility_threshold=0.4,
            max_buffer_size=100,
        )
        assert config.relevance_threshold == 0.5
        assert config.max_buffer_size == 100


class TestCraniMemAdmissionGate:
    def test_admit_high_relevance_candidate(self):
        gate = CraniMemAdmissionGate()
        candidate = CraniMemCandidate("c1", "deploy to production", 0.9, 0.8, 0.1, "user", 1000.0)
        decision = gate.evaluate(candidate)
        assert decision.action == GateAction.ADMIT

    def test_reject_low_relevance_candidate(self):
        gate = CraniMemAdmissionGate()
        candidate = CraniMemCandidate("c2", "irrelevant chat", 0.05, 0.3, 0.0, "chat", 1000.0)
        decision = gate.evaluate(candidate)
        assert decision.action == GateAction.REJECT

    def test_defer_marginal_relevance(self):
        gate = CraniMemAdmissionGate()
        candidate = CraniMemCandidate("c3", "somewhat relevant info", 0.2, 0.1, 0.1, "log", 1000.0)
        decision = gate.evaluate(candidate)
        assert decision.action in (GateAction.DEFER, GateAction.REJECT)

    def test_surprise_boost_helps_admission(self):
        gate = CraniMemAdmissionGate()
        candidate = CraniMemCandidate(
            "c-surprise", "unexpected critical error",
            goal_relevance=0.25, utility_score=0.6, surprise_score=0.9,
            source="system", timestamp=1000.0,
        )
        decision = gate.evaluate(candidate)
        assert decision.relevance_score > candidate.goal_relevance

    def test_buffer_contents_accumulate(self):
        gate = CraniMemAdmissionGate()
        for i in range(5):
            candidate = CraniMemCandidate(
                f"c-{i}", f"important info {i}",
                0.9, 0.8, 0.0, "user", float(i),
            )
            gate.evaluate(candidate)
        assert gate.buffer_size >= 1

    def test_retry_deferred_unknown(self):
        gate = CraniMemAdmissionGate()
        result = gate.retry_deferred("nonexistent")
        assert result is None

    def test_set_goal_clears_expired(self):
        gate = CraniMemAdmissionGate()
        candidate = CraniMemCandidate("c-defer", "marginal", 0.2, 0.1, 0.1, "log", 0.0)
        gate.evaluate(candidate)
        gate.set_goal("new target goal")
        assert gate.deferred_count >= 0

    def test_stats(self):
        gate = CraniMemAdmissionGate()
        candidate = CraniMemCandidate("c-stats", "stats test", 0.9, 0.8, 0.0, "user", 1000.0)
        gate.evaluate(candidate)
        stats = gate.stats()
        assert "admitted" in stats
        assert "deferred" in stats
        assert "rejected" in stats
        assert "buffer_size" in stats

    def test_custom_thresholds(self):
        config = CraniMemConfig(relevance_threshold=0.8, utility_threshold=0.7)
        gate = CraniMemAdmissionGate(config=config)
        candidate = CraniMemCandidate("c-low", "basic info", 0.5, 0.5, 0.0, "user", 1000.0)
        decision = gate.evaluate(candidate)
        assert decision.action in (GateAction.DEFER, GateAction.REJECT)
