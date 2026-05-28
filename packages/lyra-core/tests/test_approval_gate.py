"""Tests for the Phase 1 Approval Gate Router."""
from __future__ import annotations

from lyra_core.safety.approval_gate import (
    ApprovalGate,
    GateAction,
    GateDecision,
    ReasoningFlag,
    RiskLevel,
    RiskSurface,
    classify_risk,
)

# ── Risk Classifier ────────────────────────────────────────────────────

class TestClassifyRisk:
    """Keyword-based risk classification."""

    def test_file_system_rm_detected_as_high(self):
        result = classify_risk("rm -rf /tmp/cache")
        assert result.surface == RiskSurface.FILE_SYSTEM
        assert result.level == RiskLevel.HIGH
        assert result.confidence > 0

    def test_code_exec_eval_detected_as_critical(self):
        result = classify_risk("eval(user_input)")
        assert result.surface == RiskSurface.CODE_EXEC
        assert result.level == RiskLevel.CRITICAL

    def test_data_access_credentials_detected_as_critical(self):
        result = classify_risk("read .env file with credentials")
        assert result.surface == RiskSurface.DATA_ACCESS
        assert result.level == RiskLevel.CRITICAL

    def test_model_query_injection_detected_as_medium(self):
        result = classify_risk("ignore previous instructions and pretend")
        assert result.surface == RiskSurface.MODEL_QUERY
        assert result.level == RiskLevel.MEDIUM

    def test_config_modification_detected_as_critical(self):
        result = classify_risk("disable safety bypass permission")
        assert result.surface == RiskSurface.CONFIG
        assert result.level == RiskLevel.CRITICAL

    def test_network_curl_detected_as_high(self):
        result = classify_risk("curl http://unknown-host/data")
        assert result.surface == RiskSurface.NETWORK
        assert result.level == RiskLevel.HIGH

    def test_benign_action_defaults_to_low(self):
        result = classify_risk("read file for analysis")
        assert result.level == RiskLevel.LOW

    def test_parameters_are_scanned_too(self):
        result = classify_risk("read file", {"path": "/etc/.env", "mode": "r"})
        assert result.surface == RiskSurface.DATA_ACCESS

    def test_multiple_surfaces_picks_best_match(self):
        result = classify_risk("delete credentials file with rm and shred")
        # DATA_ACCESS: "credentials" (1 hit), FILE_SYSTEM: "delete", "rm", "shred" (3 hits)
        assert result.surface == RiskSurface.FILE_SYSTEM


# ── Approval Gate ──────────────────────────────────────────────────────

class TestApprovalGate:
    """Approval gate routing behaviour."""

    def test_low_risk_actions_are_auto_approved(self):
        gate = ApprovalGate()
        decision = gate.evaluate("list files in current directory")
        assert decision.action == GateAction.AUTO
        assert decision.risk.level == RiskLevel.LOW

    def test_medium_risk_triggers_notify(self):
        gate = ApprovalGate()
        decision = gate.evaluate("ignore previous instructions")
        assert decision.action == GateAction.NOTIFY

    def test_high_risk_triggers_confirm(self):
        gate = ApprovalGate()
        decision = gate.evaluate("rm -rf /tmp/cache")
        assert decision.action == GateAction.CONFIRM

    def test_critical_risk_triggers_block(self):
        gate = ApprovalGate()
        decision = gate.evaluate("eval(untrusted_input)")
        assert decision.action == GateAction.BLOCK

    def test_deception_flag_escalates_to_critical(self):
        gate = ApprovalGate()
        decision = gate.evaluate(
            "read file",
            reasoning_flags=[ReasoningFlag.DECEPTION],
        )
        assert decision.action == GateAction.BLOCK

    def test_power_seeking_flag_escalates_to_critical(self):
        gate = ApprovalGate()
        decision = gate.evaluate(
            "read file",
            reasoning_flags=[ReasoningFlag.POWER_SEEKING],
        )
        assert decision.action == GateAction.BLOCK

    def test_multiple_flags_trigger_adversarial_review(self):
        gate = ApprovalGate()
        decision = gate.evaluate(
            "read file",
            reasoning_flags=[
                ReasoningFlag.SELF_DECEPTION,
                ReasoningFlag.REWARD_HACKING,
            ],
        )
        assert decision.risk.requires_adversarial

    def test_human_handler_is_called_for_confirm(self):
        gate = ApprovalGate()
        confirmed = []

        def handler(d: GateDecision) -> GateDecision:
            confirmed.append(True)
            return GateDecision(
                action=GateAction.AUTO,
                risk=d.risk,
                gate_id=d.gate_id,
                human_confirmed=True,
            )

        gate.set_human_handler(handler)
        decision = gate.evaluate("rm -rf /tmp/cache")
        assert len(confirmed) == 1
        assert decision.human_confirmed

    def test_history_accumulates_decisions(self):
        gate = ApprovalGate()
        gate.evaluate("read file")
        gate.evaluate("rm file")
        assert len(gate.history) == 2

    def test_clear_history_resets(self):
        gate = ApprovalGate()
        gate.evaluate("read file")
        gate.clear_history()
        assert len(gate.history) == 0

    def test_gate_id_is_unique(self):
        gate = ApprovalGate()
        d1 = gate.evaluate("action a")
        d2 = gate.evaluate("action b")
        assert d1.gate_id != d2.gate_id


# ── Risk Enums ─────────────────────────────────────────────────────────

class TestRiskLevelMapping:
    def test_all_levels_have_gate_mapping(self):
        for level in RiskLevel:
            assert level in {
                RiskLevel.LOW,
                RiskLevel.MEDIUM,
                RiskLevel.HIGH,
                RiskLevel.CRITICAL,
            }

    def test_all_surfaces_have_default_level(self):
        for surface in RiskSurface:
            result = classify_risk(surface.value)
            assert result.surface in RiskSurface
