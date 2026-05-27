"""Tests for lyra-autoresearch HITL (Human-in-the-Loop) module."""
from __future__ import annotations

from unittest.mock import Mock

import pytest

from lyra_autoresearch.hitl import (
    ApprovalGate,
    FeedbackLoop,
    HITLConfig,
    HITLManager,
    GateResult,
    GateStatus,
    ReviewCheckpoint,
)


class TestHITLConfig:
    def test_defaults(self):
        c = HITLConfig()
        assert c.enabled is True
        assert c.require_approval_for_actions is True
        assert c.max_auto_iterations > 0
        assert c.auto_approve_low_risk is True

    def test_custom_config(self):
        c = HITLConfig(
            enabled=False,
            require_approval_for_actions=False,
            max_auto_iterations=5,
            risk_threshold=0.9,
        )
        assert c.enabled is False
        assert c.max_auto_iterations == 5
        assert c.risk_threshold == 0.9

    def test_risk_threshold_default(self):
        c = HITLConfig()
        assert 0.0 <= c.risk_threshold <= 1.0


class TestGateResult:
    def test_approved(self):
        r = GateResult(status=GateStatus.APPROVED, reason="safe", risk_score=0.1)
        assert r.is_approved() is True
        assert r.risk_score == 0.1

    def test_denied(self):
        r = GateResult(status=GateStatus.DENIED, reason="risky", risk_score=0.9)
        assert r.is_approved() is False

    def test_needs_review(self):
        r = GateResult(status=GateStatus.NEEDS_REVIEW, reason="borderline", risk_score=0.6)
        assert r.is_approved() is False
        assert r.status == GateStatus.NEEDS_REVIEW


class TestApprovalGate:
    @pytest.fixture
    def gate(self):
        return ApprovalGate(HITLConfig())

    def test_evaluate_low_risk_auto_approves(self, gate):
        result = gate.evaluate(action="read_file", risk_score=0.1, context={})
        assert result.status in (GateStatus.APPROVED, GateStatus.NEEDS_REVIEW)

    def test_evaluate_high_risk_denies(self, gate):
        result = gate.evaluate(action="delete_files", risk_score=0.95, context={})
        assert result.status in (GateStatus.DENIED, GateStatus.NEEDS_REVIEW)

    def test_evaluate_extreme_risk_always_denies(self, gate):
        gate.config.risk_threshold = 0.5
        result = gate.evaluate(action="rm_rf_root", risk_score=1.0, context={})
        assert result.status != GateStatus.APPROVED

    def test_disabled_gate_auto_approves(self):
        config = HITLConfig(enabled=False)
        gate = ApprovalGate(config)
        result = gate.evaluate(action="anything", risk_score=1.0, context={})
        assert result.status == GateStatus.APPROVED


class TestReviewCheckpoint:
    def test_creation(self):
        ckpt = ReviewCheckpoint(
            checkpoint_id="ck1",
            description="Before code execution",
            action="run_tests",
            risk_score=0.5,
        )
        assert ckpt.checkpoint_id == "ck1"
        assert ckpt.risk_score == 0.5
        assert ckpt.approved is False

    def test_approve_and_deny(self):
        ckpt = ReviewCheckpoint("ck1", "desc", "action", 0.3)
        ckpt.approve(reviewer="human", notes="looks good")
        assert ckpt.approved is True
        assert ckpt.reviewer == "human"

    def test_deny(self):
        ckpt = ReviewCheckpoint("ck1", "desc", "action", 0.3)
        ckpt.deny(reviewer="human", notes="not safe")
        assert ckpt.approved is False


class TestFeedbackLoop:
    def test_record_feedback(self):
        loop = FeedbackLoop()
        loop.record("human", "action_1", "Looks good", is_positive=True)
        assert len(loop.history) == 1
        assert loop.history[0]["feedback"] == "Looks good"

    def test_multiple_feedback_entries(self):
        loop = FeedbackLoop()
        loop.record("user1", "action_1", "ok", True)
        loop.record("user1", "action_2", "bad", False)
        assert len(loop.history) == 2

    def test_get_stats(self):
        loop = FeedbackLoop()
        loop.record("u1", "a1", "good", True)
        loop.record("u1", "a2", "great", True)
        loop.record("u1", "a3", "bad", False)
        stats = loop.get_stats()
        assert stats["total"] == 3
        assert stats["positive"] == 2
        assert stats["positive_rate"] > 0.5

    def test_empty_feedback_stats(self):
        loop = FeedbackLoop()
        stats = loop.get_stats()
        assert stats["total"] == 0


class TestHITLManager:
    @pytest.fixture
    def manager(self):
        return HITLManager(HITLConfig())

    def test_register_checkpoint(self, manager):
        ckpt = manager.register_checkpoint("Before deploy", "deploy", 0.8)
        assert ckpt.checkpoint_id is not None
        assert len(manager.checkpoints) == 1

    def test_multiple_checkpoints(self, manager):
        ids = []
        for i in range(3):
            ckpt = manager.register_checkpoint(f"Check {i}", f"action_{i}", 0.5)
            ids.append(ckpt.checkpoint_id)
        assert len(manager.checkpoints) == 3
        assert len(set(ids)) == 3  # Unique IDs

    def test_iteration_tracking(self, manager):
        assert manager.iteration_count == 0
        manager.increment_iteration()
        assert manager.iteration_count == 1
        manager.increment_iteration()
        assert manager.iteration_count == 2

    def test_max_iterations_limit(self, manager):
        manager.config.max_auto_iterations = 2
        manager.increment_iteration()
        manager.increment_iteration()
        assert manager.is_at_iteration_limit() is True

    def test_not_at_limit(self, manager):
        manager.config.max_auto_iterations = 10
        manager.increment_iteration()
        assert manager.is_at_iteration_limit() is False
