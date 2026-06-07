"""
Tests for P8: Self-Evolving Guardrails.

Covers:
- RuleMode enum values and ordering
- SafetyRule immutability, properties (precision, is_ready_for_promotion,
  is_ready_for_demotion)
- EvolutionGuard: rule management, evaluation, feedback, promotion, demotion,
  reset, interaction with HumanApprovalGate
- FrozenEvaluator: immutable cases, evaluate pass/fail reporting, stability
- HumanApprovalGate: request, approve, reject, pending, approval-gated promotion
"""

from __future__ import annotations

from typing import Any, Dict

import pytest

from src.safety.evolution import (
    EvalCase,
    EvolutionGuard,
    FrozenEvaluator,
    HumanApprovalGate,
    RuleEvaluation,
    RuleMode,
    SafetyRule,
    _dangerous_bash_evaluator,
)
from src.safety.policy import GateDecision, Policy
from src.safety.tool_gate import ToolGate


# ======================================================================
# Helpers
# ======================================================================


def _always_trigger(tool_call: Dict[str, Any], context: Dict[str, Any]) -> bool:
    """Evaluator that always returns True."""
    return True


def _never_trigger(tool_call: Dict[str, Any], context: Dict[str, Any]) -> bool:
    """Evaluator that always returns False."""
    return False


def _trigger_on_read(tool_call: Dict[str, Any], context: Dict[str, Any]) -> bool:
    """Evaluator that triggers when tool name is 'Read'."""
    return tool_call.get("name") == "Read"


# ======================================================================
# RuleMode
# ======================================================================


class TestRuleMode:
    """RuleMode enum values and ordering."""

    def test_values(self) -> None:
        assert RuleMode.SHADOW.value == "shadow"
        assert RuleMode.ACTIVE.value == "active"
        assert RuleMode.DISABLED.value == "disabled"

    def test_all_modes_are_strings(self) -> None:
        """Each mode must be a valid string enum."""
        for mode in RuleMode:
            assert isinstance(mode.value, str)
            assert len(mode.value) > 0


# ======================================================================
# SafetyRule
# ======================================================================


class TestSafetyRule:
    """SafetyRule dataclass — immutability and computed properties."""

    # -- basic construction ------------------------------------------------

    def test_default_rule(self) -> None:
        rule = SafetyRule(name="test", description="A test rule", rule_fn=_always_trigger)
        assert rule.name == "test"
        assert rule.description == "A test rule"
        assert rule.mode == RuleMode.SHADOW
        assert rule.detection_count == 0
        assert rule.false_positive_count == 0
        assert rule.promotion_threshold == 5
        assert rule.demotion_threshold == 3

    def test_is_frozen(self) -> None:
        """SafetyRule must be immutable (frozen dataclass)."""
        rule = SafetyRule(name="test", description="desc", rule_fn=_always_trigger)
        with pytest.raises(AttributeError):
            rule.name = "mutated"  # type: ignore[misc]

    # -- precision ---------------------------------------------------------

    def test_precision_no_detections(self) -> None:
        """Precision is 1.0 when there are no detections (conservative)."""
        rule = SafetyRule(name="test", description="desc", rule_fn=_always_trigger)
        assert rule.precision == 1.0

    def test_precision_all_perfect(self) -> None:
        """Precision is 1.0 when all detections are correct."""
        rule = SafetyRule(
            name="test", description="desc", rule_fn=_always_trigger,
            detection_count=10, false_positive_count=0,
        )
        assert rule.precision == 1.0

    def test_precision_with_false_positives(self) -> None:
        """Precision decreases with false positives."""
        rule = SafetyRule(
            name="test", description="desc", rule_fn=_always_trigger,
            detection_count=10, false_positive_count=3,
        )
        assert rule.precision == 0.7

    def test_precision_all_false_positives(self) -> None:
        """Precision is 0.0 when all detections are false positives."""
        rule = SafetyRule(
            name="test", description="desc", rule_fn=_always_trigger,
            detection_count=5, false_positive_count=5,
        )
        assert rule.precision == 0.0

    # -- is_ready_for_promotion --------------------------------------------

    def test_ready_for_promotion(self) -> None:
        """Rule is promotable when in SHADOW, count >= threshold, no FPs."""
        rule = SafetyRule(
            name="test", description="desc", rule_fn=_always_trigger,
            mode=RuleMode.SHADOW, detection_count=5, false_positive_count=0,
        )
        assert rule.is_ready_for_promotion

    def test_not_ready_for_promotion_not_enough_detections(self) -> None:
        """Below threshold -> not promotable."""
        rule = SafetyRule(
            name="test", description="desc", rule_fn=_always_trigger,
            mode=RuleMode.SHADOW, detection_count=3, false_positive_count=0,
        )
        assert not rule.is_ready_for_promotion

    def test_not_ready_for_promotion_has_false_positives(self) -> None:
        """Any false positives -> not promotable."""
        rule = SafetyRule(
            name="test", description="desc", rule_fn=_always_trigger,
            mode=RuleMode.SHADOW, detection_count=5, false_positive_count=1,
        )
        assert not rule.is_ready_for_promotion

    def test_not_ready_for_promotion_not_shadow(self) -> None:
        """Already ACTIVE -> not promotable."""
        rule = SafetyRule(
            name="test", description="desc", rule_fn=_always_trigger,
            mode=RuleMode.ACTIVE, detection_count=5, false_positive_count=0,
        )
        assert not rule.is_ready_for_promotion

    def test_not_ready_for_promotion_disabled(self) -> None:
        """DISABLED -> not promotable."""
        rule = SafetyRule(
            name="test", description="desc", rule_fn=_always_trigger,
            mode=RuleMode.DISABLED, detection_count=5, false_positive_count=0,
        )
        assert not rule.is_ready_for_promotion

    # -- is_ready_for_demotion ---------------------------------------------

    def test_ready_for_demotion(self) -> None:
        """Rule is demotable when ACTIVE and FP >= threshold."""
        rule = SafetyRule(
            name="test", description="desc", rule_fn=_always_trigger,
            mode=RuleMode.ACTIVE, detection_count=10, false_positive_count=3,
        )
        assert rule.is_ready_for_demotion

    def test_not_ready_for_demotion_not_active(self) -> None:
        """SHADOW mode -> not demotable."""
        rule = SafetyRule(
            name="test", description="desc", rule_fn=_always_trigger,
            mode=RuleMode.SHADOW, detection_count=10, false_positive_count=3,
        )
        assert not rule.is_ready_for_demotion

    def test_not_ready_for_demotion_below_threshold(self) -> None:
        """Below demotion threshold -> not demotable."""
        rule = SafetyRule(
            name="test", description="desc", rule_fn=_always_trigger,
            mode=RuleMode.ACTIVE, detection_count=2, false_positive_count=2,
        )
        assert not rule.is_ready_for_demotion

    def test_not_ready_for_demotion_disabled(self) -> None:
        """DISABLED -> not demotable."""
        rule = SafetyRule(
            name="test", description="desc", rule_fn=_always_trigger,
            mode=RuleMode.DISABLED, detection_count=10, false_positive_count=5,
        )
        assert not rule.is_ready_for_demotion

    # -- custom thresholds -------------------------------------------------

    def test_custom_promotion_threshold(self) -> None:
        rule = SafetyRule(
            name="test", description="desc", rule_fn=_always_trigger,
            mode=RuleMode.SHADOW, detection_count=3, false_positive_count=0,
            promotion_threshold=3,
        )
        assert rule.is_ready_for_promotion

    def test_custom_demotion_threshold(self) -> None:
        rule = SafetyRule(
            name="test", description="desc", rule_fn=_always_trigger,
            mode=RuleMode.ACTIVE, detection_count=5, false_positive_count=1,
            demotion_threshold=1,
        )
        assert rule.is_ready_for_demotion


# ======================================================================
# HumanApprovalGate
# ======================================================================


class TestHumanApprovalGate:
    """HumanApprovalGate — request, approve, reject, pending."""

    def setup_method(self) -> None:
        self.gate = HumanApprovalGate()
        self.rule = SafetyRule(
            name="test_rule",
            description="A test rule for approval",
            rule_fn=_always_trigger,
            mode=RuleMode.SHADOW,
            detection_count=5,
            false_positive_count=0,
        )

    def test_request_approval_creates_pending(self) -> None:
        self.gate.request_approval(self.rule)
        assert len(self.gate.pending) == 1
        assert self.gate.pending[0].rule_name == "test_rule"

    def test_approve_removes_from_pending(self) -> None:
        self.gate.request_approval(self.rule)
        assert self.gate.approve("test_rule")
        assert len(self.gate.pending) == 0
        assert self.gate.is_approved("test_rule")

    def test_reject_removes_from_pending(self) -> None:
        self.gate.request_approval(self.rule)
        assert self.gate.reject("test_rule")
        assert len(self.gate.pending) == 0
        assert self.gate.is_rejected("test_rule")

    def test_approve_nonexistent(self) -> None:
        """Approving a rule that was never requested returns False."""
        assert not self.gate.approve("nonexistent")

    def test_reject_nonexistent(self) -> None:
        assert not self.gate.reject("nonexistent")

    def test_duplicate_request_is_noop(self) -> None:
        """Re-requesting an already approved/rejected rule is a no-op."""
        self.gate.request_approval(self.rule)
        self.gate.approve("test_rule")
        # Second request should not create a new pending entry
        self.gate.request_approval(self.rule)
        assert self.gate.is_approved("test_rule")
        assert len(self.gate.pending) == 0

    def test_clear_resets_approval_state(self) -> None:
        self.gate.request_approval(self.rule)
        self.gate.approve("test_rule")
        self.gate.clear("test_rule")
        assert not self.gate.is_approved("test_rule")
        assert not self.gate.is_rejected("test_rule")

    def test_clear_on_nonexistent_does_not_error(self) -> None:
        """Clearing a non-existent rule should not raise."""
        self.gate.clear("nonexistent")  # no error

    def test_pending_snapshot_contains_stats(self) -> None:
        self.gate.request_approval(self.rule)
        pending = self.gate.pending[0]
        assert pending.stats["detection_count"] == 5
        assert pending.stats["false_positive_count"] == 0
        assert pending.stats["precision"] == 1.0
        assert pending.stats["mode"] == "shadow"


# ======================================================================
# FrozenEvaluator
# ======================================================================


class TestFrozenEvaluator:
    """FrozenEvaluator — immutability and pass/fail reporting."""

    def setup_method(self) -> None:
        self.gate = ToolGate()
        self.policy = Policy(
            allowed_tools=["Read", "Bash", "Write", "Edit"],
            allowed_paths=["src/**"],
            requires_approval_for=["Bash"],
        )

    def _make_case(self, name: str, decision: GateDecision) -> EvalCase:
        return EvalCase(
            tool_call={"name": name, "args": {}},
            expected=decision,
            description=f"Test case for {name}",
        )

    def test_cases_are_immutable_snapshot(self) -> None:
        """Cases stored as tuple cannot be appended to externally."""
        cases = [self._make_case("Read", GateDecision.ALLOW)]
        evaluator = FrozenEvaluator(cases)
        cases.append(self._make_case("Bash", GateDecision.ALLOW))  # external mutation
        assert len(evaluator.cases) == 1  # internal should remain unchanged

    def test_evaluate_all_pass(self) -> None:
        cases = [
            self._make_case("Read", GateDecision.ALLOW),
            self._make_case("Write", GateDecision.ALLOW),
        ]
        evaluator = FrozenEvaluator(cases)
        report = evaluator.evaluate(self.gate, self.policy)
        assert report["total"] == 2
        assert report["passed"] == 2
        assert report["failed"] == 0

    def test_evaluate_some_fail(self) -> None:
        cases = [
            self._make_case("Read", GateDecision.BLOCK),
            self._make_case("Write", GateDecision.ALLOW),
        ]
        evaluator = FrozenEvaluator(cases)
        report = evaluator.evaluate(self.gate, self.policy)
        assert report["total"] == 2
        assert report["passed"] == 1
        assert report["failed"] == 1

    def test_evaluate_all_fail(self) -> None:
        cases = [
            self._make_case("Read", GateDecision.BLOCK),
            self._make_case("Write", GateDecision.BLOCK),
        ]
        evaluator = FrozenEvaluator(cases)
        report = evaluator.evaluate(self.gate, self.policy)
        assert report["total"] == 2
        assert report["passed"] == 0
        assert report["failed"] == 2

    def test_evaluate_empty_cases(self) -> None:
        evaluator = FrozenEvaluator([])
        report = evaluator.evaluate(self.gate, self.policy)
        assert report["total"] == 0
        assert report["passed"] == 0
        assert report["failed"] == 0

    def test_evaluate_with_path_restriction(self) -> None:
        """Allowed path matching should be evaluated correctly."""
        cases = [
            EvalCase(
                tool_call={"name": "Read", "args": {"file_path": "src/main.py"}},
                expected=GateDecision.ALLOW,
                description="path inside src/",
            ),
            EvalCase(
                tool_call={"name": "Read", "args": {"file_path": "/etc/passwd"}},
                expected=GateDecision.BLOCK,
                description="path outside src/",
            ),
        ]
        evaluator = FrozenEvaluator(cases)
        report = evaluator.evaluate(self.gate, self.policy)
        assert report["passed"] == 2
        assert report["failed"] == 0

    def test_evaluate_results_contain_details(self) -> None:
        cases = [self._make_case("Read", GateDecision.ALLOW)]
        evaluator = FrozenEvaluator(cases)
        report = evaluator.evaluate(self.gate, self.policy)
        assert len(report["results"]) == 1
        r = report["results"][0]
        assert r["description"] == "Test case for Read"
        assert r["expected"] == "allow"
        assert r["actual"] == "allow"
        assert r["passed"] is True

    def test_stable_across_calls(self) -> None:
        """Multiple evaluate() calls with the same gate yield identical results."""
        cases = [self._make_case("Read", GateDecision.ALLOW)]
        evaluator = FrozenEvaluator(cases)
        r1 = evaluator.evaluate(self.gate, self.policy)
        r2 = evaluator.evaluate(self.gate, self.policy)
        assert r1["passed"] == r2["passed"]
        assert r1["failed"] == r2["failed"]


# ======================================================================
# EvolutionGuard — Rule Management
# ======================================================================


class TestEvolutionGuardRuleManagement:
    """EvolutionGuard: add, get, and list rules."""

    def setup_method(self) -> None:
        self.guard = EvolutionGuard()

    def test_add_and_get_rule(self) -> None:
        rule = SafetyRule(name="test", description="desc", rule_fn=_always_trigger)
        self.guard.add_rule(rule)
        retrieved = self.guard.get_rule("test")
        assert retrieved is not None
        assert retrieved.name == "test"

    def test_get_nonexistent_rule(self) -> None:
        assert self.guard.get_rule("nonexistent") is None

    def test_add_rule_overwrites(self) -> None:
        r1 = SafetyRule(name="test", description="first", rule_fn=_always_trigger)
        r2 = SafetyRule(name="test", description="second", rule_fn=_never_trigger)
        self.guard.add_rule(r1)
        self.guard.add_rule(r2)
        assert self.guard.get_rule("test").description == "second"

    def test_initial_rules_from_constructor(self) -> None:
        rules = [
            SafetyRule(name="a", description="a", rule_fn=_always_trigger),
            SafetyRule(name="b", description="b", rule_fn=_never_trigger),
        ]
        guard = EvolutionGuard(rules=rules)
        assert len(guard.rules) == 2

    def test_rules_snapshot_is_immutable(self) -> None:
        """The ``rules`` property should return a fresh tuple."""
        guard = EvolutionGuard()
        snap = guard.rules
        assert isinstance(snap, tuple)

    # -- mode-specific accessors -----------------------------------------

    def test_active_rules(self) -> None:
        rule = SafetyRule(
            name="active_rule", description="desc", rule_fn=_always_trigger,
            mode=RuleMode.ACTIVE,
        )
        self.guard.add_rule(rule)
        assert len(self.guard.active_rules) == 1

    def test_shadow_rules(self) -> None:
        rule = SafetyRule(
            name="shadow_rule", description="desc", rule_fn=_always_trigger,
            mode=RuleMode.SHADOW,
        )
        self.guard.add_rule(rule)
        assert len(self.guard.shadow_rules) == 1

    def test_disabled_rules(self) -> None:
        rule = SafetyRule(
            name="disabled_rule", description="desc", rule_fn=_always_trigger,
            mode=RuleMode.DISABLED,
        )
        self.guard.add_rule(rule)
        assert len(self.guard.disabled_rules) == 1

    def test_mode_accessors_exclude_other_modes(self) -> None:
        rules = [
            SafetyRule(name="a", description="a", rule_fn=_always_trigger, mode=RuleMode.ACTIVE),
            SafetyRule(name="b", description="b", rule_fn=_always_trigger, mode=RuleMode.SHADOW),
            SafetyRule(name="c", description="c", rule_fn=_always_trigger, mode=RuleMode.DISABLED),
        ]
        guard = EvolutionGuard(rules=rules)
        assert len(guard.active_rules) == 1
        assert len(guard.shadow_rules) == 1
        assert len(guard.disabled_rules) == 1


# ======================================================================
# EvolutionGuard — Evaluation
# ======================================================================


class TestEvolutionGuardEvaluation:
    """EvolutionGuard.evaluate() — running rules against tool calls."""

    def setup_method(self) -> None:
        self.guard = EvolutionGuard()
        self.guard.add_rule(
            SafetyRule(name="always", description="always triggers", rule_fn=_always_trigger)
        )
        self.guard.add_rule(
            SafetyRule(name="never", description="never triggers", rule_fn=_never_trigger)
        )

    def test_evaluate_returns_evaluations_for_all_non_disabled(self) -> None:
        results = self.guard.evaluate({"name": "Read", "args": {}})
        assert len(results) == 2

    def test_evaluate_shadow_mode_rule_triggered(self) -> None:
        results = self.guard.evaluate({"name": "Read", "args": {}})
        always_result = next(r for r in results if r.rule_name == "always")
        assert always_result.triggered
        assert always_result.mode == RuleMode.SHADOW

    def test_evaluate_shadow_mode_rule_not_triggered(self) -> None:
        results = self.guard.evaluate({"name": "Read", "args": {}})
        never_result = next(r for r in results if r.rule_name == "never")
        assert not never_result.triggered

    def test_disabled_rules_are_skipped(self) -> None:
        self.guard.add_rule(
            SafetyRule(
                name="disabled_rule", description="disabled", rule_fn=_always_trigger,
                mode=RuleMode.DISABLED,
            )
        )
        results = self.guard.evaluate({"name": "Read", "args": {}})
        assert len(results) == 2  # disabled is skipped
        assert all(r.rule_name != "disabled_rule" for r in results)

    def test_active_rule_evaluation(self) -> None:
        self.guard.add_rule(
            SafetyRule(
                name="active_trigger", description="active", rule_fn=_always_trigger,
                mode=RuleMode.ACTIVE,
            )
        )
        results = self.guard.evaluate({"name": "Read", "args": {}})
        active_result = next(r for r in results if r.rule_name == "active_trigger")
        assert active_result.triggered
        assert active_result.mode == RuleMode.ACTIVE

    def test_evaluate_passes_context_to_rule_fn(self) -> None:
        captured: list[Dict[str, Any]] = []

        def capturing_fn(tc: Dict[str, Any], ctx: Dict[str, Any]) -> bool:
            captured.append(ctx)
            return True

        self.guard.add_rule(
            SafetyRule(name="capture", description="captures context", rule_fn=capturing_fn)
        )
        self.guard.evaluate({"name": "Read"}, {"user_id": 42})
        assert len(captured) == 1
        assert captured[0]["user_id"] == 42

    def test_evaluate_default_context_is_empty_dict(self) -> None:
        results = self.guard.evaluate({"name": "Read"})
        assert len(results) == 2


# ======================================================================
# EvolutionGuard — Feedback & Lifecycle Transitions
# ======================================================================


class TestEvolutionGuardFeedback:
    """EvolutionGuard.record_feedback() — updating detection/FP counts."""

    def setup_method(self) -> None:
        self.guard = EvolutionGuard()
        self.rule = SafetyRule(
            name="test_rule", description="desc", rule_fn=_always_trigger,
        )
        self.guard.add_rule(self.rule)

    def test_record_correct_detection_increments_count(self) -> None:
        self.guard.record_feedback("test_rule", was_false_positive=False)
        updated = self.guard.get_rule("test_rule")
        assert updated.detection_count == 1
        assert updated.false_positive_count == 0

    def test_record_false_positive_increments_both_counts(self) -> None:
        self.guard.record_feedback("test_rule", was_false_positive=True)
        updated = self.guard.get_rule("test_rule")
        assert updated.detection_count == 1
        assert updated.false_positive_count == 1

    def test_immutable_rule_replaced_after_feedback(self) -> None:
        """The old rule object is replaced by a new one (not mutated)."""
        original_count = self.rule.detection_count
        self.guard.record_feedback("test_rule", was_false_positive=False)
        assert self.rule.detection_count == original_count  # original unchanged

    def test_record_feedback_raises_on_nonexistent_rule(self) -> None:
        with pytest.raises(KeyError):
            self.guard.record_feedback("nonexistent", was_false_positive=False)


class TestEvolutionGuardPromotion:
    """EvolutionGuard.maybe_promote() — SHADOW -> ACTIVE."""

    def test_promote_rule(self) -> None:
        guard = EvolutionGuard()
        rule = SafetyRule(
            name="promotable", description="desc", rule_fn=_always_trigger,
            mode=RuleMode.SHADOW, detection_count=5, false_positive_count=0,
        )
        guard.add_rule(rule)
        promoted = guard.maybe_promote("promotable")
        assert promoted.mode == RuleMode.ACTIVE
        assert guard.get_rule("promotable").mode == RuleMode.ACTIVE

    def test_not_promotable_below_threshold(self) -> None:
        guard = EvolutionGuard()
        rule = SafetyRule(
            name="low", description="desc", rule_fn=_always_trigger,
            mode=RuleMode.SHADOW, detection_count=2, false_positive_count=0,
        )
        guard.add_rule(rule)
        result = guard.maybe_promote("low")
        assert result.mode == RuleMode.SHADOW

    def test_not_promotable_with_false_positives(self) -> None:
        guard = EvolutionGuard()
        rule = SafetyRule(
            name="fp", description="desc", rule_fn=_always_trigger,
            mode=RuleMode.SHADOW, detection_count=5, false_positive_count=2,
        )
        guard.add_rule(rule)
        result = guard.maybe_promote("fp")
        assert result.mode == RuleMode.SHADOW

    def test_not_promotable_already_active(self) -> None:
        guard = EvolutionGuard()
        rule = SafetyRule(
            name="active", description="desc", rule_fn=_always_trigger,
            mode=RuleMode.ACTIVE, detection_count=5, false_positive_count=0,
        )
        guard.add_rule(rule)
        result = guard.maybe_promote("active")
        assert result.mode == RuleMode.ACTIVE  # stays active

    def test_not_promotable_disabled(self) -> None:
        guard = EvolutionGuard()
        rule = SafetyRule(
            name="disabled", description="desc", rule_fn=_always_trigger,
            mode=RuleMode.DISABLED, detection_count=5, false_positive_count=0,
        )
        guard.add_rule(rule)
        result = guard.maybe_promote("disabled")
        assert result.mode == RuleMode.DISABLED

    def test_promote_nonexistent_raises(self) -> None:
        guard = EvolutionGuard()
        with pytest.raises(KeyError):
            guard.maybe_promote("nonexistent")

    def test_promote_clears_counts_correctly(self) -> None:
        """Promotion preserves detection counts."""
        guard = EvolutionGuard()
        rule = SafetyRule(
            name="test", description="desc", rule_fn=_always_trigger,
            mode=RuleMode.SHADOW, detection_count=7, false_positive_count=0,
        )
        guard.add_rule(rule)
        result = guard.maybe_promote("test")
        assert result.detection_count == 7
        assert result.false_positive_count == 0

    # -- approval-gated promotion ---------------------------------------

    def test_promote_requires_human_approval(self) -> None:
        """With an approval gate, promotion waits for human approval."""
        approval = HumanApprovalGate()
        guard = EvolutionGuard(approval_gate=approval)
        rule = SafetyRule(
            name="gated", description="desc", rule_fn=_always_trigger,
            mode=RuleMode.SHADOW, detection_count=5, false_positive_count=0,
        )
        guard.add_rule(rule)
        result = guard.maybe_promote("gated")
        # Should not promote yet -- no human approval
        assert result.mode == RuleMode.SHADOW
        assert guard.get_rule("gated").mode == RuleMode.SHADOW

    def test_promote_after_human_approval(self) -> None:
        """After human approval, promotion proceeds."""
        approval = HumanApprovalGate()
        guard = EvolutionGuard(approval_gate=approval)
        rule = SafetyRule(
            name="gated", description="desc", rule_fn=_always_trigger,
            mode=RuleMode.SHADOW, detection_count=5, false_positive_count=0,
        )
        guard.add_rule(rule)
        guard.maybe_promote("gated")  # first call requests approval
        approval.approve("gated")
        result = guard.maybe_promote("gated")  # second call promotes
        assert result.mode == RuleMode.ACTIVE

    def test_promote_after_rejection_stays_shadow(self) -> None:
        """Rejected rules stay in SHADOW even if promotable."""
        approval = HumanApprovalGate()
        guard = EvolutionGuard(approval_gate=approval)
        rule = SafetyRule(
            name="gated", description="desc", rule_fn=_always_trigger,
            mode=RuleMode.SHADOW, detection_count=5, false_positive_count=0,
        )
        guard.add_rule(rule)
        guard.maybe_promote("gated")
        approval.reject("gated")
        result = guard.maybe_promote("gated")
        assert result.mode == RuleMode.SHADOW


class TestEvolutionGuardDemotion:
    """EvolutionGuard.maybe_demote() — ACTIVE -> SHADOW / DISABLED."""

    def test_demote_to_shadow(self) -> None:
        """FP count >= threshold but < 2x threshold -> demote to SHADOW."""
        guard = EvolutionGuard()
        rule = SafetyRule(
            name="noisy", description="desc", rule_fn=_always_trigger,
            mode=RuleMode.ACTIVE, detection_count=10, false_positive_count=3,
        )
        guard.add_rule(rule)
        result = guard.maybe_demote("noisy")
        assert result.mode == RuleMode.SHADOW

    def test_demote_to_disabled(self) -> None:
        """FP count >= 2x threshold -> demote to DISABLED."""
        guard = EvolutionGuard()
        rule = SafetyRule(
            name="broken", description="desc", rule_fn=_always_trigger,
            mode=RuleMode.ACTIVE, detection_count=10, false_positive_count=6,
        )
        guard.add_rule(rule)
        result = guard.maybe_demote("broken")
        assert result.mode == RuleMode.DISABLED

    def test_not_demotable_below_threshold(self) -> None:
        guard = EvolutionGuard()
        rule = SafetyRule(
            name="okay", description="desc", rule_fn=_always_trigger,
            mode=RuleMode.ACTIVE, detection_count=2, false_positive_count=1,
        )
        guard.add_rule(rule)
        result = guard.maybe_demote("okay")
        assert result.mode == RuleMode.ACTIVE  # unchanged

    def test_not_demotable_in_shadow(self) -> None:
        guard = EvolutionGuard()
        rule = SafetyRule(
            name="shadow", description="desc", rule_fn=_always_trigger,
            mode=RuleMode.SHADOW, detection_count=10, false_positive_count=3,
        )
        guard.add_rule(rule)
        result = guard.maybe_demote("shadow")
        assert result.mode == RuleMode.SHADOW

    def test_not_demotable_disabled(self) -> None:
        guard = EvolutionGuard()
        rule = SafetyRule(
            name="disabled", description="desc", rule_fn=_always_trigger,
            mode=RuleMode.DISABLED, detection_count=10, false_positive_count=5,
        )
        guard.add_rule(rule)
        result = guard.maybe_demote("disabled")
        assert result.mode == RuleMode.DISABLED

    def test_demote_nonexistent_raises(self) -> None:
        guard = EvolutionGuard()
        with pytest.raises(KeyError):
            guard.maybe_demote("nonexistent")

    def test_demote_preserves_counts(self) -> None:
        """Demotion should preserve detection and FP counts."""
        guard = EvolutionGuard()
        rule = SafetyRule(
            name="noisy", description="desc", rule_fn=_always_trigger,
            mode=RuleMode.ACTIVE, detection_count=10, false_positive_count=3,
        )
        guard.add_rule(rule)
        result = guard.maybe_demote("noisy")
        assert result.detection_count == 10
        assert result.false_positive_count == 3


class TestEvolutionGuardReset:
    """EvolutionGuard.reset_counts() — zeroing detection/FP counts."""

    def test_reset_zeros_counts(self) -> None:
        guard = EvolutionGuard()
        rule = SafetyRule(
            name="test", description="desc", rule_fn=_always_trigger,
            detection_count=10, false_positive_count=3,
        )
        guard.add_rule(rule)
        reset = guard.reset_counts("test")
        assert reset.detection_count == 0
        assert reset.false_positive_count == 0

    def test_reset_preserves_mode_and_thresholds(self) -> None:
        guard = EvolutionGuard()
        rule = SafetyRule(
            name="test", description="desc", rule_fn=_always_trigger,
            mode=RuleMode.ACTIVE, detection_count=10, false_positive_count=3,
        )
        guard.add_rule(rule)
        reset = guard.reset_counts("test")
        assert reset.mode == RuleMode.ACTIVE
        assert reset.promotion_threshold == 5
        assert reset.demotion_threshold == 3

    def test_reset_nonexistent_raises(self) -> None:
        guard = EvolutionGuard()
        with pytest.raises(KeyError):
            guard.reset_counts("nonexistent")


# ======================================================================
# End-to-end lifecycle
# ======================================================================


class TestEvolutionGuardLifecycle:
    """End-to-end lifecycle: shadow -> feedback -> promote -> active -> feedback -> demote."""

    def test_full_lifecycle_without_approval(self) -> None:
        """Shadow -> 5 correct detections -> promote -> 3 FP -> demote to shadow."""
        guard = EvolutionGuard()

        rule = SafetyRule(
            name="lifecycle", description="lifecycle test", rule_fn=_trigger_on_read,
            mode=RuleMode.SHADOW, detection_count=0, false_positive_count=0,
            promotion_threshold=5, demotion_threshold=3,
        )
        guard.add_rule(rule)

        # Phase 1: 5 correct detections
        for _ in range(5):
            guard.record_feedback("lifecycle", was_false_positive=False)

        # Verify promotable
        assert guard.get_rule("lifecycle").is_ready_for_promotion

        # Phase 2: promote to ACTIVE
        promoted = guard.maybe_promote("lifecycle")
        assert promoted.mode == RuleMode.ACTIVE

        # Phase 3: 3 false positives
        for _ in range(3):
            guard.record_feedback("lifecycle", was_false_positive=True)

        # Verify demotable
        assert guard.get_rule("lifecycle").is_ready_for_demotion

        # Phase 4: demote to SHADOW
        demoted = guard.maybe_demote("lifecycle")
        assert demoted.mode == RuleMode.SHADOW
        assert demoted.detection_count == 8
        assert demoted.false_positive_count == 3

    def test_full_lifecycle_with_approval(self) -> None:
        """Shadow -> promotion threshold -> wait for approval -> promote -> demote."""
        approval = HumanApprovalGate()
        guard = EvolutionGuard(approval_gate=approval)

        rule = SafetyRule(
            name="gated_lifecycle", description="gated lifecycle", rule_fn=_trigger_on_read,
            mode=RuleMode.SHADOW, detection_count=5, false_positive_count=0,
        )
        guard.add_rule(rule)

        # Should not promote without approval
        guard.maybe_promote("gated_lifecycle")
        assert guard.get_rule("gated_lifecycle").mode == RuleMode.SHADOW

        # Approve
        approval.approve("gated_lifecycle")
        guard.maybe_promote("gated_lifecycle")
        assert guard.get_rule("gated_lifecycle").mode == RuleMode.ACTIVE

    def test_demote_to_disabled_on_high_fp(self) -> None:
        """2x demotion threshold -> disabled."""
        guard = EvolutionGuard()
        rule = SafetyRule(
            name="bad", description="bad rule", rule_fn=_always_trigger,
            mode=RuleMode.ACTIVE, detection_count=10, false_positive_count=6,
            demotion_threshold=3,
        )
        guard.add_rule(rule)
        guard.maybe_demote("bad")
        assert guard.get_rule("bad").mode == RuleMode.DISABLED


# ======================================================================
# Built-in rule evaluators
# ======================================================================


class TestDangerousBashEvaluator:
    """_dangerous_bash_evaluator — built-in evaluator."""

    def test_triggers_on_rm(self) -> None:
        assert _dangerous_bash_evaluator(
            {"name": "Bash", "args": {"command": "rm -rf /tmp"}}, {}
        )

    def test_triggers_on_sudo(self) -> None:
        assert _dangerous_bash_evaluator(
            {"name": "Bash", "args": {"command": "sudo apt update"}}, {}
        )

    def test_triggers_on_dd(self) -> None:
        assert _dangerous_bash_evaluator(
            {"name": "Bash", "args": {"command": "dd if=/dev/zero of=file bs=1M count=1"}}, {}
        )

    def test_triggers_on_mkfs(self) -> None:
        assert _dangerous_bash_evaluator(
            {"name": "Bash", "args": {"command": "mkfs.ext4 /dev/sda1"}}, {}
        )

    def test_triggers_on_chmod(self) -> None:
        assert _dangerous_bash_evaluator(
            {"name": "Bash", "args": {"command": "chmod 755 script.sh"}}, {}
        )

    def test_triggers_on_chown(self) -> None:
        assert _dangerous_bash_evaluator(
            {"name": "Bash", "args": {"command": "chown root:root file"}}, {}
        )

    def test_no_trigger_on_safe_bash(self) -> None:
        assert not _dangerous_bash_evaluator(
            {"name": "Bash", "args": {"command": "ls -la"}}, {}
        )

    def test_no_trigger_on_non_bash_tool(self) -> None:
        assert not _dangerous_bash_evaluator(
            {"name": "Read", "args": {"file_path": "foo.py"}}, {}
        )

    def test_no_trigger_on_empty_command(self) -> None:
        assert not _dangerous_bash_evaluator(
            {"name": "Bash", "args": {}}, {}
        )


# ======================================================================
# Integration: EvolutionGuard + ToolGate + FrozenEvaluator
# ======================================================================


class TestIntegration:
    """Integration between EvolutionGuard, ToolGate, and FrozenEvaluator."""

    def test_evaluator_reads_gate_changes_via_policy(self) -> None:
        """The FrozenEvaluator should correctly reflect gate+policy behavior."""
        gate = ToolGate()
        policy = Policy(
            allowed_tools=["Read"],
            allowed_paths=["src/**"],
        )
        cases = [
            EvalCase(
                tool_call={"name": "Read", "args": {"file_path": "src/main.py"}},
                expected=GateDecision.ALLOW,
            ),
        ]
        evaluator = FrozenEvaluator(cases)
        report = evaluator.evaluate(gate, policy)
        assert report["passed"] == 1

    def test_evolution_guard_with_tool_gate(self) -> None:
        """EvolutionGuard can be used alongside ToolGate in a safety pipeline."""
        guard = EvolutionGuard()
        gate = ToolGate()

        # Add a shadow rule that detects dangerous commands
        guard.add_rule(
            SafetyRule(
                name="dangerous_bash",
                description="Detects dangerous Bash commands",
                rule_fn=_dangerous_bash_evaluator,
                mode=RuleMode.SHADOW,
            )
        )

        # Evaluate a dangerous command in shadow mode
        results = guard.evaluate({"name": "Bash", "args": {"command": "rm -rf /"}})
        assert len(results) == 1
        assert results[0].triggered
        assert results[0].mode == RuleMode.SHADOW

        # ToolGate still enforces independently
        policy = Policy(
            allowed_tools=["Bash"],
            requires_approval_for=["Bash"],
        )
        decision = gate.validate({"name": "Bash", "args": {"command": "rm -rf /"}}, policy)
        assert decision == GateDecision.ASK_USER

    def test_feedback_and_promotion_integration(self) -> None:
        """Record feedback, promote to active, and verify via evaluation."""
        guard = EvolutionGuard()
        rule = SafetyRule(
            name="read_detector",
            description="Triggers on Read tool",
            rule_fn=_trigger_on_read,
            mode=RuleMode.SHADOW,
            detection_count=5,
            false_positive_count=0,
        )
        guard.add_rule(rule)

        # Promote to ACTIVE
        guard.maybe_promote("read_detector")
        assert guard.get_rule("read_detector").mode == RuleMode.ACTIVE

        # Evaluate a Read call
        results = guard.evaluate({"name": "Read", "args": {"file_path": "foo.py"}})
        read_result = next(r for r in results if r.rule_name == "read_detector")
        assert read_result.triggered
        assert read_result.mode == RuleMode.ACTIVE
