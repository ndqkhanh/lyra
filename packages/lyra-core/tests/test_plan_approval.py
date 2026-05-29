"""Tests for Plan Approval Workflow (Plan 29.3)."""

import pytest
from lyra_core.teams.plan_approval import (
    PlanApprovalWorkflow,
    PlanState,
)


class TestPlanApprovalWorkflow:
    def test_create_plan(self):
        wf = PlanApprovalWorkflow()
        plan = wf.create_plan(
            "p1", "Add auth", "Implement OAuth2", ["Step 1", "Step 2"], "engineer"
        )
        assert plan.plan_id == "p1"
        assert plan.state == PlanState.DRAFT
        assert plan.submitted_by == "engineer"

    def test_create_duplicate_raises(self):
        wf = PlanApprovalWorkflow()
        wf.create_plan("p1", "Title", "Desc", ["Step"], "alice")
        with pytest.raises(ValueError, match="already exists"):
            wf.create_plan("p1", "Title", "Desc", ["Step"], "alice")

    def test_submit_draft(self):
        wf = PlanApprovalWorkflow()
        plan = wf.create_plan("p1", "Title", "Desc", ["Step"], "alice")
        wf.submit("p1")
        assert plan.state == PlanState.SUBMITTED

    def test_submit_non_draft_raises(self):
        wf = PlanApprovalWorkflow()
        wf.create_plan("p1", "Title", "Desc", ["Step"], "alice")
        wf.submit("p1")
        with pytest.raises(ValueError, match="not in DRAFT"):
            wf.submit("p1")

    def test_review(self):
        wf = PlanApprovalWorkflow()
        wf.create_plan("p1", "Title", "Desc", ["Step"], "alice")
        wf.submit("p1")
        plan = wf.review("p1", "lead")
        assert plan.state == PlanState.IN_REVIEW

    def test_approve_plan(self):
        wf = PlanApprovalWorkflow()
        wf.create_plan("p1", "Title", "Desc", ["Step"], "alice")
        wf.submit("p1")
        wf.review("p1", "lead")
        plan = wf.decide("p1", "approved", "lead")
        assert plan.state == PlanState.APPROVED

    def test_reject_plan(self):
        wf = PlanApprovalWorkflow()
        wf.create_plan("p1", "Title", "Desc", ["Step"], "alice")
        wf.submit("p1")
        wf.review("p1", "lead")
        plan = wf.decide("p1", "rejected", "lead", "Needs more detail")
        assert plan.state == PlanState.REJECTED
        assert plan.decisions[-1].feedback == "Needs more detail"

    def test_revision_requested(self):
        wf = PlanApprovalWorkflow()
        wf.create_plan("p1", "Title", "Desc", ["Step"], "alice")
        wf.submit("p1")
        wf.review("p1", "lead")
        plan = wf.decide("p1", "revision_requested", "lead", "Fix step 2")
        assert plan.state == PlanState.DRAFT

    def test_revision_then_approve(self):
        wf = PlanApprovalWorkflow()
        wf.create_plan("p1", "Title", "Desc", ["Step"], "alice")
        wf.submit("p1")
        wf.review("p1", "lead")
        wf.decide("p1", "revision_requested", "lead", "Fix it")
        wf.submit("p1")
        wf.review("p1", "lead")
        plan = wf.decide("p1", "approved", "lead")
        assert plan.state == PlanState.APPROVED
        assert len(plan.decisions) == 2

    def test_max_revision_rounds_exceeded(self):
        wf = PlanApprovalWorkflow()
        wf.create_plan("p1", "Title", "Desc", ["Step"], "alice")
        for _ in range(wf.MAX_REVISION_ROUNDS):
            wf.submit("p1")
            wf.review("p1", "lead")
            wf.decide("p1", "revision_requested", "lead")
        assert wf.get_plan("p1").state == PlanState.REJECTED

    def test_execute_approved(self):
        wf = PlanApprovalWorkflow()
        wf.create_plan("p1", "Title", "Desc", ["Step"], "alice")
        wf.submit("p1")
        wf.review("p1", "lead")
        wf.decide("p1", "approved", "lead")
        plan = wf.execute("p1")
        assert plan.state == PlanState.EXECUTING

    def test_complete_with_log(self):
        wf = PlanApprovalWorkflow()
        wf.create_plan("p1", "Title", "Desc", ["Step"], "alice")
        wf.submit("p1")
        wf.review("p1", "lead")
        wf.decide("p1", "approved", "lead")
        wf.execute("p1")
        plan = wf.complete("p1", "All steps done successfully")
        assert plan.state == PlanState.COMPLETED
        assert "All steps done successfully" in plan.execution_log

    def test_audit_trail(self):
        wf = PlanApprovalWorkflow()
        wf.create_plan("p1", "Title", "Desc", ["Step"], "alice")
        wf.submit("p1")
        wf.review("p1", "lead")
        wf.decide("p1", "approved", "lead")
        trail = wf.get_audit_trail("p1")
        assert len(trail) == 4

    def test_list_by_state(self):
        wf = PlanApprovalWorkflow()
        wf.create_plan("p1", "Title", "Desc", ["Step"], "alice")
        wf.create_plan("p2", "Title", "Desc", ["Step"], "bob")
        wf.submit("p1")
        drafts = wf.list_by_state(PlanState.DRAFT)
        submitted = wf.list_by_state(PlanState.SUBMITTED)
        assert len(drafts) == 1
        assert len(submitted) == 1

    def test_pending_and_review_counts(self):
        wf = PlanApprovalWorkflow()
        wf.create_plan("p1", "Title", "Desc", ["Step"], "alice")
        wf.create_plan("p2", "Title", "Desc", ["Step"], "bob")
        assert wf.pending_count == 0
        wf.submit("p1")
        wf.submit("p2")
        wf.review("p1", "lead")
        assert wf.pending_count == 1
        assert wf.in_review_count == 1

    def test_state_transition_errors(self):
        wf = PlanApprovalWorkflow()
        wf.create_plan("p1", "Title", "Desc", ["Step"], "alice")
        with pytest.raises(ValueError, match="not SUBMITTED"):
            wf.review("p1", "lead")
