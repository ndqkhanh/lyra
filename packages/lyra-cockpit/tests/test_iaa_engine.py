"""Tests for the IAA engine module."""

from __future__ import annotations

import time

import pytest

from lyra_cockpit.exceptions import IAAEngineError
from lyra_cockpit.iaa_engine import (
    IAAConfig,
    IAAEngine,
    AuditRecord,
    AutonomousAction,
    IntentPreview,
)


class TestIAAConfig:
    def test_default_values(self) -> None:
        config = IAAConfig()
        assert config.preview_timeout == 5.0
        assert config.auto_execute_threshold == 0.85
        assert config.audit_enabled is True
        assert config.max_preview_tokens == 200

    def test_custom_values(self) -> None:
        config = IAAConfig(
            preview_timeout=10.0,
            auto_execute_threshold=0.9,
            audit_enabled=False,
            max_preview_tokens=500,
        )
        assert config.preview_timeout == 10.0
        assert config.auto_execute_threshold == 0.9
        assert config.audit_enabled is False
        assert config.max_preview_tokens == 500

    def test_frozen(self) -> None:
        config = IAAConfig()
        with pytest.raises(AttributeError):
            config.preview_timeout = 42.0  # type: ignore[misc]


class TestIntentPreview:
    def test_creation(self) -> None:
        preview = IntentPreview(
            intent_id="int-001",
            description="Research the latest AI papers",
            predicted_actions=("Research",),
            risk_score=0.2,
            requires_approval=False,
        )
        assert preview.intent_id == "int-001"
        assert preview.description == "Research the latest AI papers"
        assert preview.predicted_actions == ("Research",)
        assert preview.risk_score == 0.2
        assert not preview.requires_approval

    def test_high_risk(self) -> None:
        preview = IntentPreview(
            intent_id="int-002",
            description="Deploy to production",
            predicted_actions=("Deployment",),
            risk_score=0.8,
            requires_approval=True,
        )
        assert preview.requires_approval
        assert preview.risk_score >= 0.5

    def test_frozen(self) -> None:
        preview = IntentPreview("i1", "test", ("act",), 0.0, False)
        with pytest.raises(AttributeError):
            preview.description = "changed"  # type: ignore[misc]


class TestAutonomousAction:
    def test_creation(self) -> None:
        now = time.time()
        action = AutonomousAction(
            action_id="act-001",
            intent_id="int-001",
            action_type="Research",
            payload="Research completed",
            executed_at=now,
            success=True,
        )
        assert action.action_id == "act-001"
        assert action.intent_id == "int-001"
        assert action.action_type == "Research"
        assert action.payload == "Research completed"
        assert action.success

    def test_failure(self) -> None:
        now = time.time()
        action = AutonomousAction(
            action_id="act-002",
            intent_id="int-002",
            action_type="Deployment",
            payload="Deployment failed",
            executed_at=now,
            success=False,
        )
        assert not action.success

    def test_frozen(self) -> None:
        now = time.time()
        action = AutonomousAction("a", "i", "t", "p", now, True)
        with pytest.raises(AttributeError):
            action.success = False  # type: ignore[misc]


class TestAuditRecord:
    def test_creation_verified(self) -> None:
        now = time.time()
        action = AutonomousAction("act-001", "int-001", "Research", "ok", now, True)
        record = AuditRecord(
            audit_id="aud-001",
            action=action,
            trace=("Step 1 completed", "Step 2 completed"),
            verified=True,
            anomalies=(),
        )
        assert record.audit_id == "aud-001"
        assert record.verified
        assert record.anomalies == ()

    def test_with_anomalies(self) -> None:
        now = time.time()
        action = AutonomousAction("act-002", "int-002", "Deploy", "failed", now, False)
        record = AuditRecord(
            audit_id="aud-002",
            action=action,
            trace=("Action failed",),
            verified=False,
            anomalies=("Action reported failure",),
        )
        assert not record.verified
        assert "Action reported failure" in record.anomalies

    def test_frozen(self) -> None:
        now = time.time()
        action = AutonomousAction("a", "i", "t", "p", now, True)
        record = AuditRecord("aud-001", action, ("trace",), True, ())
        with pytest.raises(AttributeError):
            record.verified = False  # type: ignore[misc]


class TestIAAEngine:
    @pytest.mark.asyncio
    async def test_preview_intent_simple(self) -> None:
        engine = IAAEngine()
        preview = await engine.preview_intent("Research the latest papers on AI")
        assert preview.intent_id.startswith("int-")
        assert "Research" in preview.predicted_actions
        assert not preview.requires_approval

    @pytest.mark.asyncio
    async def test_preview_intent_empty_raises(self) -> None:
        engine = IAAEngine()
        with pytest.raises(IAAEngineError, match="cannot be empty"):
            await engine.preview_intent("")

    @pytest.mark.asyncio
    async def test_preview_intent_whitespace_raises(self) -> None:
        engine = IAAEngine()
        with pytest.raises(IAAEngineError, match="cannot be empty"):
            await engine.preview_intent("   \n   ")

    @pytest.mark.asyncio
    async def test_preview_intent_multiple_actions(self) -> None:
        engine = IAAEngine()
        preview = await engine.preview_intent("Build and test the new module")
        assert "Build" in preview.predicted_actions
        assert "Testing" in preview.predicted_actions

    @pytest.mark.asyncio
    async def test_preview_intent_high_risk(self) -> None:
        engine = IAAEngine()
        preview = await engine.preview_intent("Deploy to production and modify config")
        assert preview.requires_approval
        assert preview.risk_score >= 0.2

    @pytest.mark.asyncio
    async def test_preview_intent_unknown_action(self) -> None:
        engine = IAAEngine()
        preview = await engine.preview_intent("Sing a song")
        assert "Unknown" in preview.predicted_actions

    @pytest.mark.asyncio
    async def test_execute_action_success(self) -> None:
        engine = IAAEngine()
        preview = await engine.preview_intent("Research AI safety")
        action = await engine.execute_action(preview)
        assert action.action_id.startswith("act-")
        assert action.intent_id == preview.intent_id
        assert action.success

    @pytest.mark.asyncio
    async def test_execute_action_requires_approval_raises(self) -> None:
        engine = IAAEngine()
        preview = await engine.preview_intent("Deploy to production")
        assert preview.requires_approval
        with pytest.raises(IAAEngineError, match="requires approval"):
            await engine.execute_action(preview)

    @pytest.mark.asyncio
    async def test_audit_action_verified(self) -> None:
        engine = IAAEngine()
        preview = await engine.preview_intent("Research AI")
        action = await engine.execute_action(preview)
        record = await engine.audit_action(action)
        assert record.verified
        assert record.anomalies == ()

    @pytest.mark.asyncio
    async def test_audit_action_unverified(self) -> None:
        engine = IAAEngine()
        now = time.time()
        action = AutonomousAction("act-bad", "int-001", "Test", "x" * 300, now, False)
        record = await engine.audit_action(action)
        assert not record.verified
        assert len(record.anomalies) >= 1

    @pytest.mark.asyncio
    async def test_run_iaa_cycle(self) -> None:
        engine = IAAEngine()
        preview, action, audit = await engine.run_iaa_cycle("Research AI papers")
        assert preview.intent_id is not None
        assert action.intent_id == preview.intent_id
        assert audit.verified

    @pytest.mark.asyncio
    async def test_run_iaa_cycle_approval_needed_raises(self) -> None:
        engine = IAAEngine()
        with pytest.raises(IAAEngineError):
            await engine.run_iaa_cycle("Deploy to production")

    def test_config_property(self) -> None:
        config = IAAConfig(preview_timeout=30.0)
        engine = IAAEngine(config)
        assert engine.config.preview_timeout == 30.0

    def test_intent_history_tracked(self) -> None:
        engine = IAAEngine()
        # Access internal state to verify tracking
        assert len(engine._intent_history) == 0
