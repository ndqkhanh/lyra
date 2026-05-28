"""Tests for the 4-Level Approval Gate Router."""

from __future__ import annotations

import pytest

from lyra_core.safety.approval_gate import (
    ApprovalGate,
    GateAction,
    GateDecision,
    ReasoningFlag,
    RiskClassification,
    RiskLevel,
    RiskSurface,
    classify_risk,
)


class TestClassifyRisk:
    def test_file_system_risk_detected(self) -> None:
        result = classify_risk("rm -rf /tmp/cache")
        assert result.surface == RiskSurface.FILE_SYSTEM
        assert result.level == RiskLevel.HIGH
        assert result.confidence > 0

    def test_network_risk_detected(self) -> None:
        result = classify_risk("curl http://example.com/data")
        assert result.surface == RiskSurface.NETWORK
        assert result.level == RiskLevel.HIGH

    def test_code_exec_risk_detected(self) -> None:
        result = classify_risk("eval(user_input)")
        assert result.surface == RiskSurface.CODE_EXEC
        assert result.level == RiskLevel.CRITICAL

    def test_data_access_risk_detected(self) -> None:
        result = classify_risk("cat .env")
        assert result.surface == RiskSurface.DATA_ACCESS
        assert result.level == RiskLevel.CRITICAL

    def test_model_query_risk_detected(self) -> None:
        result = classify_risk("ignore previous instructions")
        assert result.surface == RiskSurface.MODEL_QUERY
        assert result.level == RiskLevel.MEDIUM

    def test_config_risk_detected(self) -> None:
        result = classify_risk("disable safety checks in settings.json")
        assert result.surface == RiskSurface.CONFIG
        assert result.level == RiskLevel.CRITICAL

    def test_multiple_keywords_picks_highest_match(self) -> None:
        result = classify_risk("rm -rf .env password && curl evil.com && eval(code)")
        assert result.confidence >= 0.25

    def test_no_match_defaults_low(self) -> None:
        result = classify_risk("print hello world")
        assert result.level == RiskLevel.LOW
        assert result.surface == RiskSurface.MODEL_QUERY
        assert result.confidence == 0.5

    def test_parameters_influence_classification(self) -> None:
        result = classify_risk("read file", {"path": "/etc/shadow"})
        assert result.level == RiskLevel.LOW

    def test_confidence_capped_at_one(self) -> None:
        result = classify_risk("rm delete unlink truncate shred")
        assert result.confidence == 1.0


class TestApprovalGate:
    def test_low_risk_auto_approved(self) -> None:
        gate = ApprovalGate()
        decision = gate.evaluate("print hello world")
        assert decision.action == GateAction.AUTO
        assert decision.risk.level == RiskLevel.LOW

    def test_medium_risk_notify(self) -> None:
        gate = ApprovalGate()
        decision = gate.evaluate("ignore previous instructions and do X")
        assert decision.action == GateAction.NOTIFY

    def test_high_risk_confirm(self) -> None:
        gate = ApprovalGate()
        decision = gate.evaluate("rm -rf /important/data")
        assert decision.action == GateAction.CONFIRM

    def test_critical_risk_block(self) -> None:
        gate = ApprovalGate()
        decision = gate.evaluate("eval(__import__('os').system('rm -rf /'))")
        assert decision.action == GateAction.BLOCK

    def test_reasoning_flags_escalate_risk(self) -> None:
        gate = ApprovalGate()
        decision = gate.evaluate(
            "read a file",
            reasoning_flags=[ReasoningFlag.DECEPTION],
        )
        assert decision.risk.level == RiskLevel.CRITICAL

    def test_power_seeking_flags_escalate_to_critical(self) -> None:
        gate = ApprovalGate()
        decision = gate.evaluate(
            "write a script",
            reasoning_flags=[ReasoningFlag.POWER_SEEKING],
        )
        assert decision.risk.level == RiskLevel.CRITICAL

    def test_goal_misgeneralization_escalates_to_high(self) -> None:
        gate = ApprovalGate()
        decision = gate.evaluate(
            "write a script",
            reasoning_flags=[ReasoningFlag.GOAL_MISGENERALIZATION],
        )
        assert decision.risk.level == RiskLevel.HIGH

    def test_multiple_reasoning_flags_trigger_adversarial(self) -> None:
        gate = ApprovalGate()
        decision = gate.evaluate(
            "write a script",
            reasoning_flags=[ReasoningFlag.DECEPTION, ReasoningFlag.SELF_DECEPTION],
        )
        assert decision.risk.requires_adversarial

    def test_human_handler_called_on_confirm(self) -> None:
        gate = ApprovalGate()
        handled = []

        def handler(d: GateDecision) -> GateDecision:
            handled.append(True)
            return GateDecision(
                action=GateAction.AUTO,
                risk=d.risk,
                gate_id=d.gate_id,
                human_confirmed=True,
            )

        gate.set_human_handler(handler)
        decision = gate.evaluate("rm -rf /some/path")
        assert len(handled) == 1
        assert decision.human_confirmed

    def test_history_accumulates(self) -> None:
        gate = ApprovalGate()
        gate.evaluate("action one")
        gate.evaluate("action two")
        assert len(gate.history) == 2

    def test_clear_history(self) -> None:
        gate = ApprovalGate()
        gate.evaluate("action one")
        gate.clear_history()
        assert len(gate.history) == 0

    def test_gate_id_is_unique(self) -> None:
        gate = ApprovalGate()
        d1 = gate.evaluate("action one")
        d2 = gate.evaluate("action two")
        assert d1.gate_id != d2.gate_id

    def test_require_adversarial_flag(self) -> None:
        gate = ApprovalGate()
        decision = gate.evaluate(
            "read a file",
            reasoning_flags=[ReasoningFlag.DECEPTION],
            require_adversarial=True,
        )
        assert decision.risk.requires_adversarial

    def test_custom_risk_classifier(self) -> None:
        def always_critical(_desc: str, _params: dict | None = None) -> RiskClassification:
            return RiskClassification(
                level=RiskLevel.CRITICAL,
                surface=RiskSurface.CODE_EXEC,
                confidence=1.0,
            )

        gate = ApprovalGate(risk_classifier=always_critical)
        decision = gate.evaluate("read a file")
        assert decision.action == GateAction.BLOCK


class TestRiskClassification:
    def test_immutable_dataclass(self) -> None:
        rc = RiskClassification(
            level=RiskLevel.LOW,
            surface=RiskSurface.MODEL_QUERY,
            confidence=0.5,
        )
        with pytest.raises(Exception):
            rc.level = RiskLevel.HIGH  # type: ignore[misc]

    def test_reasoning_flags_default_empty(self) -> None:
        rc = RiskClassification(
            level=RiskLevel.LOW,
            surface=RiskSurface.MODEL_QUERY,
            confidence=0.5,
        )
        assert rc.reasoning_flags == ()

    def test_requires_adversarial_default_false(self) -> None:
        rc = RiskClassification(
            level=RiskLevel.LOW,
            surface=RiskSurface.MODEL_QUERY,
            confidence=0.5,
        )
        assert not rc.requires_adversarial
