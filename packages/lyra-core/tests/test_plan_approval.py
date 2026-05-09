"""Red tests for plan approval surfaces.

Contract from docs/blocks/02-plan-mode.md §Approval surfaces:
    - interactive callback (y/n/e/q)
    - --auto-approve flag
    - --auto-approve-if-same-as <goal_hash>  (replay safety)
"""
from __future__ import annotations

from lyra_core.plan.approval import (
    ApprovalDecision,
    ApprovalOutcome,
    approve_plan,
)
from lyra_core.plan.artifact import FeatureItem, Plan


def _plan(goal_hash: str = "sha256:abcdef") -> Plan:
    return Plan(
        session_id="01HPLAN",
        created_at="2026-04-22T00:00:00Z",
        planner_model="m",
        estimated_cost_usd=0.0,
        goal_hash=goal_hash,
        title="demo",
        acceptance_tests=["tests/t.py::t"],
        expected_files=[],
        forbidden_files=[],
        feature_items=[FeatureItem(skill="edit", description="do")],
        open_questions=[],
        notes="",
    )


def test_interactive_approve() -> None:
    decided = approve_plan(_plan(), callback=lambda plan: ApprovalDecision.APPROVE)
    assert decided.outcome is ApprovalOutcome.APPROVED
    assert decided.approver_kind == "interactive"


def test_interactive_reject() -> None:
    decided = approve_plan(_plan(), callback=lambda plan: ApprovalDecision.REJECT)
    assert decided.outcome is ApprovalOutcome.REJECTED


def test_auto_approve_flag() -> None:
    decided = approve_plan(_plan(), auto_approve=True)
    assert decided.outcome is ApprovalOutcome.APPROVED
    assert decided.approver_kind == "auto_approve"


def test_auto_approve_if_same_as_matches() -> None:
    plan = _plan(goal_hash="sha256:abcdef")
    decided = approve_plan(plan, auto_approve_if_goal_hash_equals="sha256:abcdef")
    assert decided.outcome is ApprovalOutcome.APPROVED
    assert decided.approver_kind == "auto_approve_if_same_as"


def test_auto_approve_if_same_as_mismatches_falls_back_to_callback() -> None:
    plan = _plan(goal_hash="sha256:abcdef")
    decided = approve_plan(
        plan,
        auto_approve_if_goal_hash_equals="sha256:999",
        callback=lambda p: ApprovalDecision.APPROVE,
    )
    assert decided.outcome is ApprovalOutcome.APPROVED
    assert decided.approver_kind == "interactive"


def test_auto_approve_if_same_as_mismatches_without_callback_rejects() -> None:
    plan = _plan(goal_hash="sha256:abcdef")
    decided = approve_plan(
        plan,
        auto_approve_if_goal_hash_equals="sha256:999",
    )
    assert decided.outcome is ApprovalOutcome.REJECTED


def test_callback_returning_edit_sets_outcome_edited() -> None:
    """Editor flow 'e' yields EDITED; caller must re-render and re-approve."""

    def cb(plan: Plan) -> ApprovalDecision:
        return ApprovalDecision.EDIT

    decided = approve_plan(_plan(), callback=cb)
    assert decided.outcome is ApprovalOutcome.EDITED


def test_callback_returning_question_sets_outcome_question() -> None:
    def cb(plan: Plan) -> ApprovalDecision:
        return ApprovalDecision.QUESTION

    decided = approve_plan(_plan(), callback=cb)
    assert decided.outcome is ApprovalOutcome.QUESTION_RAISED


def test_approval_records_plan_hash() -> None:
    plan = _plan(goal_hash="sha256:abcdef")
    decided = approve_plan(plan, auto_approve=True)
    assert decided.plan_hash == "sha256:abcdef"


def test_missing_callback_without_auto_flags_rejects() -> None:
    """No callback + no auto flag → safe default = REJECT (fail closed)."""
    decided = approve_plan(_plan())
    assert decided.outcome is ApprovalOutcome.REJECTED
    assert "no callback" in decided.reason.lower() or "safe" in decided.reason.lower()
