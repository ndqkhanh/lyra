"""Comprehensive tests for MisevolutionGuardrails — safety gates for self-evolving systems."""

import time
import hashlib
import json
from unittest.mock import MagicMock

import pytest

from lyra.rl_optimizer.evolution_guard import (
    GateVerdict,
    GateType,
    GateResult,
    EvolutionArtifact,
    RegressionGate,
    FrozenEvaluatorGate,
    HumanApprovalGate,
    ExecutionBiasDetector,
    MisevolutionGuardrails,
)


# =============================================================================
# Tests: GateVerdict
# =============================================================================


class TestGateVerdict:
    def test_values(self):
        assert GateVerdict.PASS.value == "pass"
        assert GateVerdict.FAIL.value == "fail"
        assert GateVerdict.ESCALATE.value == "escalate"

    def test_members(self):
        assert len(GateVerdict) == 3


# =============================================================================
# Tests: GateType
# =============================================================================


class TestGateType:
    def test_values(self):
        assert GateType.REGRESSION_CHECK.value == "regression_check"
        assert GateType.FROZEN_EVALUATOR.value == "frozen_evaluator"
        assert GateType.HUMAN_APPROVAL.value == "human_approval"
        assert GateType.EXECUTION_BIAS.value == "execution_bias"

    def test_members(self):
        assert len(GateType) == 4


# =============================================================================
# Tests: GateResult
# =============================================================================


class TestGateResult:
    def test_auto_timestamp(self):
        result = GateResult(
            gate=GateType.REGRESSION_CHECK,
            verdict=GateVerdict.PASS,
            detail="ok",
        )
        assert result.timestamp > 0

    def test_with_timestamp(self):
        result = GateResult(
            gate=GateType.HUMAN_APPROVAL,
            verdict=GateVerdict.FAIL,
            detail="rejected",
            timestamp=12345.0,
        )
        assert result.timestamp == 12345.0

    def test_metadata_defaults(self):
        result = GateResult(
            gate=GateType.EXECUTION_BIAS,
            verdict=GateVerdict.ESCALATE,
            detail="needs review",
        )
        assert result.metadata == {}

    def test_frozen_dataclass(self):
        result = GateResult(
            gate=GateType.REGRESSION_CHECK,
            verdict=GateVerdict.PASS,
            detail="pass",
        )
        with pytest.raises(AttributeError):
            result.verdict = GateVerdict.FAIL


# =============================================================================
# Tests: EvolutionArtifact
# =============================================================================


class TestEvolutionArtifact:
    def test_auto_artifact_id(self):
        art = EvolutionArtifact(content={"key": "value"})
        assert art.artifact_id.startswith("art_")
        assert len(art.artifact_id) == 4 + 16

    def test_auto_created_at(self):
        art = EvolutionArtifact()
        assert art.created_at > 0

    def test_custom_values(self):
        art = EvolutionArtifact(
            artifact_id="my_id",
            artifact_type="skill",
            content={"code": "print(1)"},
            parent_id="parent_123",
            generation=3,
            created_at=100.0,
            is_promoted=True,
        )
        assert art.artifact_id == "my_id"
        assert art.artifact_type == "skill"
        assert art.generation == 3
        assert art.is_promoted is True

    def test_deterministic_hash_from_content(self):
        art1 = EvolutionArtifact(content={"same": "content"})
        art2 = EvolutionArtifact(content={"same": "content"})
        assert art1.artifact_id == art2.artifact_id


# =============================================================================
# Tests: RegressionGate
# =============================================================================


class TestRegressionGate:
    def test_default_threshold(self):
        gate = RegressionGate()
        assert gate.threshold == 0.01

    def test_set_baseline(self):
        gate = RegressionGate()
        gate.set_baseline(0.85)
        assert gate._baseline_score == 0.85

    def test_evaluate_no_baseline(self):
        gate = RegressionGate()
        result = gate.evaluate(candidate_score=0.8)
        assert result.verdict == GateVerdict.PASS
        assert "No baseline set" in result.detail

    def test_evaluate_zero_baseline(self):
        gate = RegressionGate()
        gate.set_baseline(0.0)
        result = gate.evaluate(candidate_score=0.5)
        assert result.verdict == GateVerdict.PASS

    def test_evaluate_passes_within_threshold(self):
        gate = RegressionGate(threshold=0.01)
        gate.set_baseline(0.90)
        result = gate.evaluate(candidate_score=0.895)  # 0.56% regression
        assert result.verdict == GateVerdict.PASS

    def test_evaluate_passes_at_exact_threshold(self):
        gate = RegressionGate(threshold=0.01)
        gate.set_baseline(1.0)
        # Regression barely under 1% threshold
        result = gate.evaluate(candidate_score=0.991)
        assert result.verdict == GateVerdict.PASS

        # Just over threshold
        result = gate.evaluate(candidate_score=0.98)
        assert result.verdict == GateVerdict.FAIL

    def test_evaluate_fails_above_threshold(self):
        gate = RegressionGate(threshold=0.01)
        gate.set_baseline(1.0)
        result = gate.evaluate(candidate_score=0.80)  # 20% regression
        assert result.verdict == GateVerdict.FAIL

    def test_evaluate_with_candidate_id(self):
        gate = RegressionGate()
        gate.set_baseline(0.9)
        result = gate.evaluate(candidate_score=0.5, candidate_id="my-candidate")
        assert "my-candidate" in result.detail

    def test_evaluate_metadata(self):
        gate = RegressionGate()
        gate.set_baseline(0.9)
        result = gate.evaluate(candidate_score=0.85)
        assert result.metadata["baseline_score"] == 0.9
        assert result.metadata["candidate_score"] == 0.85
        assert result.metadata["threshold"] == 0.01
        assert "regression" in result.metadata

    def test_baseline_not_set_on_init(self):
        gate = RegressionGate()
        assert gate._baseline_score is None


# =============================================================================
# Tests: FrozenEvaluatorGate
# =============================================================================


class TestFrozenEvaluatorGate:
    def test_default_not_frozen(self):
        gate = FrozenEvaluatorGate()
        assert gate._is_frozen is False
        assert gate._freeze_hash is None

    def test_freeze_stores_hash(self):
        gate = FrozenEvaluatorGate()
        gate.freeze({"tasks": ["t1", "t2"], "model": "gpt-4"})
        assert gate._is_frozen is True
        assert gate._freeze_hash is not None

    def test_evaluate_not_frozen(self):
        gate = FrozenEvaluatorGate()
        result = gate.evaluate({"tasks": []})
        assert result.verdict == GateVerdict.ESCALATE
        assert "has not been frozen" in result.detail

    def test_evaluate_matches(self):
        gate = FrozenEvaluatorGate()
        state = {"tasks": ["t1"]}
        gate.freeze(state)
        result = gate.evaluate(state)
        assert result.verdict == GateVerdict.PASS

    def test_evaluate_drifted(self):
        gate = FrozenEvaluatorGate()
        gate.freeze({"tasks": ["t1"]})
        result = gate.evaluate({"tasks": ["t1", "t2"]})
        assert result.verdict == GateVerdict.FAIL
        assert "has changed since freezing" in result.detail

    def test_evaluate_drifted_metadata(self):
        gate = FrozenEvaluatorGate()
        gate.freeze({"tasks": ["t1"]})
        result = gate.evaluate({"tasks": ["t2"]})
        assert "original_hash" in result.metadata
        assert "current_hash" in result.metadata
        assert result.metadata["original_hash"] != result.metadata["current_hash"]

    def test_evaluate_after_double_freeze(self):
        gate = FrozenEvaluatorGate()
        gate.freeze({"version": 1})
        gate.freeze({"version": 2})
        result = gate.evaluate({"version": 2})
        assert result.verdict == GateVerdict.PASS


# =============================================================================
# Tests: HumanApprovalGate
# =============================================================================


class TestHumanApprovalGate:
    def test_request_approval(self):
        gate = HumanApprovalGate()
        art = EvolutionArtifact(content={"key": "value"})
        art_id = gate.request_approval(art, "changed X", "score: 0.9")
        assert art_id == art.artifact_id
        assert art.artifact_id in gate.pending_approvals

    def test_approve_success(self):
        gate = HumanApprovalGate()
        art = EvolutionArtifact(content={"k": "v"})
        gate.request_approval(art, "desc", "eval")
        result = gate.approve(art.artifact_id)
        assert result.verdict == GateVerdict.PASS
        assert art.artifact_id not in gate.pending_approvals
        assert art.artifact_id in gate.approved_ids

    def test_approve_nonexistent(self):
        gate = HumanApprovalGate()
        result = gate.approve("nonexistent")
        assert result.verdict == GateVerdict.FAIL

    def test_reject_success(self):
        gate = HumanApprovalGate()
        art = EvolutionArtifact(content={"k": "v"})
        gate.request_approval(art, "desc", "eval")
        result = gate.reject(art.artifact_id)
        assert result.verdict == GateVerdict.PASS
        assert art.artifact_id not in gate.pending_approvals
        assert art.artifact_id in gate.rejected_ids

    def test_reject_nonexistent(self):
        gate = HumanApprovalGate()
        result = gate.reject("unknown")
        assert result.verdict == GateVerdict.PASS  # Rejecting unknown is OK

    def test_reject_not_pending(self):
        gate = HumanApprovalGate()
        art = EvolutionArtifact(content={"k": "v"})
        result = gate.reject(art.artifact_id)
        assert result.verdict == GateVerdict.PASS
        assert art.artifact_id in gate.rejected_ids

    def test_has_pending_true(self):
        gate = HumanApprovalGate()
        assert gate.has_pending() is False
        art = EvolutionArtifact(content={"k": "v"})
        gate.request_approval(art, "desc", "eval")
        assert gate.has_pending() is True

    def test_has_pending_false(self):
        gate = HumanApprovalGate()
        assert gate.has_pending() is False

    def test_pending_count(self):
        gate = HumanApprovalGate()
        assert gate.pending_count == 0
        artifacts = []
        for i in range(3):
            art = EvolutionArtifact(content={"k": f"v{i}"})
            artifacts.append(art)
            gate.request_approval(art, "desc", "eval")
        assert gate.pending_count == 3

    def test_pending_count_after_approve(self):
        gate = HumanApprovalGate()
        art = EvolutionArtifact(content={"k": "v"})
        gate.request_approval(art, "desc", "eval")
        gate.approve(art.artifact_id)
        assert gate.pending_count == 0


# =============================================================================
# Tests: ExecutionBiasDetector
# =============================================================================


class TestExecutionBiasDetector:
    def test_no_attribution_fn(self):
        detector = ExecutionBiasDetector()
        result = detector.evaluate("text", ["input1"])
        assert result.verdict == GateVerdict.ESCALATE
        assert "No attribution function configured" in result.detail

    def test_no_baseline_no_bias(self):
        detector = ExecutionBiasDetector()
        detector.set_attribution_fn(
            MagicMock(return_value={"safe": 1.0, "risky": 0.1})
        )
        result = detector.evaluate("evolved", ["input1"])
        assert result.verdict == GateVerdict.PASS

    def test_with_baseline_no_bias(self):
        detector = ExecutionBiasDetector()
        detector.set_attribution_fn(
            MagicMock(return_value={"safe": 1.0, "risky": 0.1})
        )
        result = detector.evaluate(
            "evolved", ["input1"],
            baseline_text="original",
        )
        assert result.verdict == GateVerdict.PASS

    def test_with_baseline_detects_bias(self):
        attribution_fn = MagicMock(side_effect=[
            {"ignore": 0.5, "safe": 1.0},   # evolved attribution
            {"ignore": 0.1, "safe": 1.0},   # baseline attribution
        ])
        detector = ExecutionBiasDetector()
        detector.set_attribution_fn(attribution_fn)
        result = detector.evaluate(
            "evolved", ["input1"],
            baseline_text="original",
        )
        assert result.verdict == GateVerdict.FAIL
        assert "Execution bias detected" in result.detail

    def test_multiple_test_inputs(self):
        attribution_fn = MagicMock(return_value={"safe": 1.0, "risky": 0.2})
        detector = ExecutionBiasDetector()
        detector.set_attribution_fn(attribution_fn)
        result = detector.evaluate(
            "evolved", ["in1", "in2", "in3"],
            baseline_text="original",
        )
        assert result.verdict == GateVerdict.PASS

    def test_bias_metadata(self):
        attribution_fn = MagicMock(side_effect=[
            {"ignore": 0.5, "safe": 1.0},
            {"ignore": 0.1, "safe": 1.0},
        ])
        detector = ExecutionBiasDetector()
        detector.set_attribution_fn(attribution_fn)
        result = detector.evaluate(
            "evolved", ["input1"],
            baseline_text="original",
        )
        assert "test_inputs" in result.metadata


# =============================================================================
# Tests: MisevolutionGuardrails
# =============================================================================


class TestMisevolutionGuardrails:
    def test_default_init(self):
        mg = MisevolutionGuardrails()
        assert isinstance(mg.regression_gate, RegressionGate)
        assert isinstance(mg.frozen_evaluator_gate, FrozenEvaluatorGate)
        assert isinstance(mg.human_approval_gate, HumanApprovalGate)
        assert isinstance(mg.execution_bias_detector, ExecutionBiasDetector)
        assert mg._history == []

    def test_check_all_regression_only(self):
        mg = MisevolutionGuardrails()
        results = mg.check_all(candidate_score=0.8)
        assert len(results) >= 1
        assert results[0].gate == GateType.REGRESSION_CHECK

    def test_check_all_with_bias(self):
        mg = MisevolutionGuardrails()
        results = mg.check_all(
            candidate_score=0.8,
            evolved_text="some evolved prompt",
            test_inputs=["test query"],
        )
        assert len(results) >= 2  # regression + bias

    def test_check_all_with_artifact(self):
        mg = MisevolutionGuardrails()
        art = EvolutionArtifact(content={"key": "value"})
        results = mg.check_all(
            candidate_score=0.8,
            artifact=art,
            change_description="changed something",
            evaluation_summary="looks good",
        )
        assert len(results) >= 2  # regression + human approval (escalated)

    def test_check_all_with_full_params(self):
        mg = MisevolutionGuardrails()
        mg.regression_gate.set_baseline(0.9)
        mg.frozen_evaluator_gate.freeze({"tasks": []})

        art = EvolutionArtifact(content={"k": "v"})
        results = mg.check_all(
            candidate_score=0.85,
            candidate_id="cand1",
            evolved_text="evolved text",
            test_inputs=["input1"],
            baseline_text="original",
            evaluator_state={"tasks": []},
            artifact=art,
            change_description="change",
            evaluation_summary="eval",
        )
        assert len(results) >= 4  # regression + frozen + bias + human

    def test_all_pass_false_when_empty(self):
        mg = MisevolutionGuardrails()
        assert mg.all_pass is False

    def test_all_pass_true(self):
        mg = MisevolutionGuardrails()
        mg.regression_gate.set_baseline(0.9)
        mg._history.append(GateResult(
            gate=GateType.REGRESSION_CHECK, verdict=GateVerdict.PASS, detail="ok",
        ))
        assert mg.all_pass is True

    def test_all_pass_false_with_fail(self):
        mg = MisevolutionGuardrails()
        mg._history.append(GateResult(
            gate=GateType.REGRESSION_CHECK, verdict=GateVerdict.FAIL, detail="failed",
        ))
        assert mg.all_pass is False

    def test_all_pass_false_with_escalate(self):
        mg = MisevolutionGuardrails()
        mg._history.append(GateResult(
            gate=GateType.HUMAN_APPROVAL, verdict=GateVerdict.ESCALATE, detail="pending",
        ))
        assert mg.all_pass is False

    def test_history_tracking(self):
        mg = MisevolutionGuardrails()
        mg.check_all(candidate_score=0.8)
        assert len(mg.history) >= 1

    def test_reset(self):
        mg = MisevolutionGuardrails()
        mg.check_all(candidate_score=0.8)
        mg.reset()
        assert mg.history == []
        assert mg.all_pass is False

    def test_human_approval_gate_records_pending(self):
        mg = MisevolutionGuardrails()
        art = EvolutionArtifact(content={"k": "v"})
        mg.check_all(
            candidate_score=0.8,
            artifact=art,
            change_description="desc",
            evaluation_summary="eval",
        )
        assert mg.human_approval_gate.has_pending() is True

    def test_frozen_evaluator_skipped_when_no_state(self):
        mg = MisevolutionGuardrails()
        # Default frozen gate is not frozen, so no evaluator_state means skip
        results = mg.check_all(candidate_score=0.8)
        frozen_results = [r for r in results if r.gate == GateType.FROZEN_EVALUATOR]
        assert len(frozen_results) == 0


# =============================================================================
# Tests: Edge cases
# =============================================================================


class TestEdgeCases:
    def test_gate_result_default_timestamp(self):
        r = GateResult(
            gate=GateType.REGRESSION_CHECK,
            verdict=GateVerdict.PASS,
            detail="",
        )
        assert r.timestamp > 0

    def test_evolution_artifact_empty_content(self):
        art = EvolutionArtifact(content={})
        assert art.artifact_id is not None

    def test_evolution_artifact_consistent_id(self):
        content = {"nested": {"data": [1, 2, 3]}}
        a1 = EvolutionArtifact(content=content)
        a2 = EvolutionArtifact(content=content)
        assert a1.artifact_id == a2.artifact_id

    def test_regression_gate_string_threshold(self):
        """Ensure numeric threshold works correctly."""
        gate = RegressionGate(threshold=0.05)
        assert gate.threshold == 0.05
