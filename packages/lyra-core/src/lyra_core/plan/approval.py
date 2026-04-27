"""Plan approval surfaces.

Three paths:
    1. ``auto_approve=True``                      — CI flag
    2. ``auto_approve_if_goal_hash_equals=<hash>`` — replay safety
    3. ``callback(plan) -> ApprovalDecision``      — interactive / web

Fail-closed: if none of the three is provided, the plan is rejected with a
"no callback" reason. This enforces a deliberate approval pathway.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Callable

from .artifact import Plan


class ApprovalDecision(str, enum.Enum):
    APPROVE = "approve"
    REJECT = "reject"
    EDIT = "edit"
    QUESTION = "question"


class ApprovalOutcome(str, enum.Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    EDITED = "edited"
    QUESTION_RAISED = "question_raised"


@dataclass
class ApprovalResult:
    outcome: ApprovalOutcome
    approver_kind: str  # "interactive" | "auto_approve" | "auto_approve_if_same_as" | "none"
    reason: str = ""
    plan_hash: str = ""


ApprovalCallback = Callable[[Plan], ApprovalDecision]


def approve_plan(
    plan: Plan,
    *,
    callback: ApprovalCallback | None = None,
    auto_approve: bool = False,
    auto_approve_if_goal_hash_equals: str | None = None,
) -> ApprovalResult:
    """Run the approval pipeline for a produced plan."""
    hash_ = plan.goal_hash

    if auto_approve_if_goal_hash_equals:
        if auto_approve_if_goal_hash_equals == plan.goal_hash:
            return ApprovalResult(
                outcome=ApprovalOutcome.APPROVED,
                approver_kind="auto_approve_if_same_as",
                reason="goal_hash matched presigned value",
                plan_hash=hash_,
            )
        # fall through to callback if provided, else safe reject
        if callback is None and not auto_approve:
            return ApprovalResult(
                outcome=ApprovalOutcome.REJECTED,
                approver_kind="none",
                reason=(
                    "auto_approve_if_same_as mismatch and no interactive callback: "
                    "safe-failing plan approval"
                ),
                plan_hash=hash_,
            )

    if auto_approve:
        return ApprovalResult(
            outcome=ApprovalOutcome.APPROVED,
            approver_kind="auto_approve",
            reason="--auto-approve flag",
            plan_hash=hash_,
        )

    if callback is None:
        return ApprovalResult(
            outcome=ApprovalOutcome.REJECTED,
            approver_kind="none",
            reason=(
                "no callback and no auto flags; safe-failing rather than "
                "auto-approving an unsupervised plan"
            ),
            plan_hash=hash_,
        )

    decision = callback(plan)
    if decision is ApprovalDecision.APPROVE:
        return ApprovalResult(
            outcome=ApprovalOutcome.APPROVED,
            approver_kind="interactive",
            reason="user approved",
            plan_hash=hash_,
        )
    if decision is ApprovalDecision.REJECT:
        return ApprovalResult(
            outcome=ApprovalOutcome.REJECTED,
            approver_kind="interactive",
            reason="user rejected",
            plan_hash=hash_,
        )
    if decision is ApprovalDecision.EDIT:
        return ApprovalResult(
            outcome=ApprovalOutcome.EDITED,
            approver_kind="interactive",
            reason="user requested edit",
            plan_hash=hash_,
        )
    if decision is ApprovalDecision.QUESTION:
        return ApprovalResult(
            outcome=ApprovalOutcome.QUESTION_RAISED,
            approver_kind="interactive",
            reason="user asked a question",
            plan_hash=hash_,
        )
    raise ValueError(f"unknown ApprovalDecision: {decision!r}")
