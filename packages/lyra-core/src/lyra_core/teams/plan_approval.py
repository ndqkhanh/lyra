"""Plan Approval Workflow (Plan 29.3).

Safety gate for autonomous teammates: plans must be submitted, reviewed,
and approved by the lead before execution. Supports revision cycles with
feedback, approval/rejection decisions, and full audit trail.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class ApprovalDecision(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISION_REQUESTED = "revision_requested"


class PlanState(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTING = "executing"
    COMPLETED = "completed"


@dataclass
class PlanDocument:
    plan_id: str
    title: str
    description: str
    steps: list[str]
    submitted_by: str
    submitted_at: str = ""
    state: PlanState = PlanState.DRAFT
    decisions: list[ApprovalRecord] = field(default_factory=list)
    execution_log: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.submitted_at:
            self.submitted_at = datetime.now(timezone.utc).isoformat()


@dataclass
class ApprovalRecord:
    decision: ApprovalDecision
    decided_by: str
    decided_at: str
    feedback: str = ""
    revision_round: int = 1


class PlanApprovalWorkflow:
    """Submit plans for lead approval before execution.

    Workflow:
    1. Teammate creates Draft plan
    2. Teammate submits → SUBMITTED
    3. Lead reviews → IN_REVIEW
    4. Lead decides: APPROVED / REJECTED / REVISION_REQUESTED
    5. If REVISION_REQUESTED → back to Draft (teammate revises)
    6. If APPROVED → EXECUTING → COMPLETED
    """

    MAX_REVISION_ROUNDS: int = 3

    def __init__(self) -> None:
        self._plans: dict[str, PlanDocument] = {}
        self._audit_log: list[dict[str, object]] = []

    def create_plan(self, plan_id: str, title: str, description: str, steps: list[str], teammate: str) -> PlanDocument:
        if plan_id in self._plans:
            raise ValueError(f"Plan '{plan_id}' already exists")

        plan = PlanDocument(
            plan_id=plan_id,
            title=title,
            description=description,
            steps=steps,
            submitted_by=teammate,
        )
        self._plans[plan_id] = plan
        self._audit(plan_id, "created", teammate)
        logger.info("Plan '%s' created by %s", plan_id, teammate)
        return plan

    def submit(self, plan_id: str) -> PlanDocument:
        plan = self._get_plan(plan_id)
        if plan.state != PlanState.DRAFT:
            raise ValueError(f"Plan '{plan_id}' is not in DRAFT state (current: {plan.state})")
        plan.state = PlanState.SUBMITTED
        self._audit(plan_id, "submitted", plan.submitted_by)
        logger.info("Plan '%s' submitted for review", plan_id)
        return plan

    def review(self, plan_id: str, reviewer: str) -> PlanDocument:
        plan = self._get_plan(plan_id)
        if plan.state != PlanState.SUBMITTED:
            raise ValueError(f"Plan '{plan_id}' is not SUBMITTED (current: {plan.state})")
        plan.state = PlanState.IN_REVIEW
        self._audit(plan_id, "review_started", reviewer)
        logger.info("Plan '%s' review started by %s", plan_id, reviewer)
        return plan

    def decide(
        self,
        plan_id: str,
        decision: str,
        decided_by: str,
        feedback: str = "",
    ) -> PlanDocument:
        plan = self._get_plan(plan_id)
        if plan.state != PlanState.IN_REVIEW:
            raise ValueError(f"Plan '{plan_id}' is not IN_REVIEW (current: {plan.state})")

        revision_round = len([d for d in plan.decisions if d.decision == ApprovalDecision.REVISION_REQUESTED]) + 1
        record = ApprovalRecord(
            decision=ApprovalDecision(decision),
            decided_by=decided_by,
            decided_at=datetime.now(timezone.utc).isoformat(),
            feedback=feedback,
            revision_round=revision_round,
        )
        plan.decisions.append(record)

        if decision == ApprovalDecision.APPROVED:
            plan.state = PlanState.APPROVED
        elif decision == ApprovalDecision.REJECTED:
            plan.state = PlanState.REJECTED
        elif decision == ApprovalDecision.REVISION_REQUESTED:
            if revision_round >= self.MAX_REVISION_ROUNDS:
                plan.state = PlanState.REJECTED
                logger.warning("Plan '%s' exceeded max revision rounds (%d)", plan_id, self.MAX_REVISION_ROUNDS)
            else:
                plan.state = PlanState.DRAFT

        self._audit(plan_id, f"decided:{decision}", decided_by)
        logger.info("Plan '%s' decided: %s by %s", plan_id, decision, decided_by)
        return plan

    def execute(self, plan_id: str) -> PlanDocument:
        plan = self._get_plan(plan_id)
        if plan.state != PlanState.APPROVED:
            raise ValueError(f"Plan '{plan_id}' is not APPROVED (current: {plan.state})")
        plan.state = PlanState.EXECUTING
        self._audit(plan_id, "execution_started", plan.submitted_by)
        return plan

    def complete(self, plan_id: str, log_entry: str = "") -> PlanDocument:
        plan = self._get_plan(plan_id)
        if plan.state != PlanState.EXECUTING:
            raise ValueError(f"Plan '{plan_id}' is not EXECUTING (current: {plan.state})")
        if log_entry:
            plan.execution_log.append(log_entry)
        plan.state = PlanState.COMPLETED
        self._audit(plan_id, "completed", plan.submitted_by)
        return plan

    def get_plan(self, plan_id: str) -> PlanDocument:
        return self._get_plan(plan_id)

    def list_by_state(self, state: PlanState | None = None) -> list[PlanDocument]:
        plans = list(self._plans.values())
        if state:
            plans = [p for p in plans if p.state == state]
        return sorted(plans, key=lambda p: p.submitted_at)

    def get_audit_trail(self, plan_id: str) -> list[dict[str, object]]:
        return [entry for entry in self._audit_log if entry.get("plan_id") == plan_id]

    @property
    def pending_count(self) -> int:
        return len([p for p in self._plans.values() if p.state == PlanState.SUBMITTED])

    @property
    def in_review_count(self) -> int:
        return len([p for p in self._plans.values() if p.state == PlanState.IN_REVIEW])

    def _get_plan(self, plan_id: str) -> PlanDocument:
        plan = self._plans.get(plan_id)
        if plan is None:
            raise KeyError(f"Plan '{plan_id}' not found")
        return plan

    def _audit(self, plan_id: str, action: str, actor: str) -> None:
        self._audit_log.append({
            "plan_id": plan_id,
            "action": action,
            "actor": actor,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
