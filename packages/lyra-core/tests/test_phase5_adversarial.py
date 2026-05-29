"""Comprehensive tests for Phase 5: Adversarial Review & Convergence."""

from __future__ import annotations

import pytest

from lyra_core.adversarial import (
    AdversarialReview,
    ConvergenceCheck,
    ConvergenceStatus,
    ResumableWorkflow,
    ReviewFinding,
    ReviewRole,
    ReviewSession,
    ReviewVerdict,
    Severity,
    WorkflowCheckpoint,
    WorkflowStatus,
    WorkflowStep,
)


# ═══════════════════════════════════════════════════════════════════════════════
# ReviewFinding
# ═══════════════════════════════════════════════════════════════════════════════


class TestReviewFinding:
    def test_create(self):
        f = ReviewFinding(
            id="f1", reviewer_id="r1", severity=Severity.HIGH,
            category="security", description="SQL injection risk",
        )
        assert f.id == "f1"
        assert f.reviewer_id == "r1"
        assert f.severity == Severity.HIGH
        assert f.category == "security"

    def test_defaults(self):
        f = ReviewFinding(
            id="f1", reviewer_id="r1", severity=Severity.LOW,
            category="style", description="Use snake_case",
        )
        assert f.location == ""
        assert f.suggestion == ""

    def test_with_location_and_suggestion(self):
        f = ReviewFinding(
            id="f1", reviewer_id="r1", severity=Severity.CRITICAL,
            category="correctness", description="Null deref",
            location="src/main.py:42",
            suggestion="Add null check before deref",
        )
        assert f.location == "src/main.py:42"
        assert f.suggestion == "Add null check before deref"

    def test_all_severity_values(self):
        for sev in Severity:
            f = ReviewFinding(
                id="f1", reviewer_id="r1", severity=sev,
                category="test", description="test",
            )
            assert f.severity == sev


# ═══════════════════════════════════════════════════════════════════════════════
# AdversarialReview
# ═══════════════════════════════════════════════════════════════════════════════


class TestAdversarialReview:
    def test_create(self):
        review = AdversarialReview(
            id="r1", reviewer_id="a1", role=ReviewRole.REVIEWER,
            subject_id="task_1",
        )
        assert review.id == "r1"
        assert review.verdict == ReviewVerdict.APPROVED
        assert review.is_clean

    def test_add_finding(self):
        review = AdversarialReview(
            id="r1", reviewer_id="a1", role=ReviewRole.REVIEWER,
            subject_id="task_1",
        )
        f = ReviewFinding(
            id="f1", reviewer_id="a1", severity=Severity.HIGH,
            category="performance", description="N+1 query",
        )
        review.add_finding(f)
        assert not review.is_clean
        assert review.high_count == 1

    def test_update_verdict_critical(self):
        review = AdversarialReview(
            id="r1", reviewer_id="a1", role=ReviewRole.REVIEWER,
            subject_id="task_1",
        )
        review.add_finding(ReviewFinding(
            id="f1", reviewer_id="a1", severity=Severity.CRITICAL,
            category="security", description="Hardcoded secret",
        ))
        verdict = review.update_verdict()
        assert verdict == ReviewVerdict.REJECTED
        assert review.has_critical

    def test_update_verdict_high(self):
        review = AdversarialReview(
            id="r1", reviewer_id="a1", role=ReviewRole.REVIEWER,
            subject_id="task_1",
        )
        review.add_finding(ReviewFinding(
            id="f1", reviewer_id="a1", severity=Severity.HIGH,
            category="performance", description="Missing index",
        ))
        verdict = review.update_verdict()
        assert verdict == ReviewVerdict.REVISE

    def test_update_verdict_medium(self):
        review = AdversarialReview(
            id="r1", reviewer_id="a1", role=ReviewRole.REVIEWER,
            subject_id="task_1",
        )
        review.add_finding(ReviewFinding(
            id="f1", reviewer_id="a1", severity=Severity.MEDIUM,
            category="maintainability", description="Long function",
        ))
        verdict = review.update_verdict()
        assert verdict == ReviewVerdict.APPROVED_WITH_SUGGESTIONS

    def test_update_verdict_low(self):
        review = AdversarialReview(
            id="r1", reviewer_id="a1", role=ReviewRole.REVIEWER,
            subject_id="task_1",
        )
        review.add_finding(ReviewFinding(
            id="f1", reviewer_id="a1", severity=Severity.LOW,
            category="style", description="Prefer f-strings",
        ))
        verdict = review.update_verdict()
        assert verdict == ReviewVerdict.APPROVED

    def test_critical_count(self):
        review = AdversarialReview(
            id="r1", reviewer_id="a1", role=ReviewRole.REVIEWER,
            subject_id="task_1",
        )
        review.add_finding(ReviewFinding(
            id="f1", reviewer_id="a1", severity=Severity.CRITICAL,
            category="s1", description="d1",
        ))
        review.add_finding(ReviewFinding(
            id="f2", reviewer_id="a1", severity=Severity.CRITICAL,
            category="s2", description="d2",
        ))
        assert review.critical_count == 2

    def test_metadata(self):
        review = AdversarialReview(
            id="r1", reviewer_id="a1", role=ReviewRole.REVIEWER,
            subject_id="task_1", metadata={"tool": "bandit", "version": "1.7"},
        )
        assert review.metadata["tool"] == "bandit"


# ═══════════════════════════════════════════════════════════════════════════════
# ConvergenceCheck
# ═══════════════════════════════════════════════════════════════════════════════


class TestConvergenceCheck:
    def test_create(self):
        cc = ConvergenceCheck(required_reviewers=2)
        assert cc.required == 2
        assert cc.active_count == 0

    def test_submit_review_not_enough(self):
        cc = ConvergenceCheck(required_reviewers=3)
        review = AdversarialReview(
            id="r1", reviewer_id="a1", role=ReviewRole.REVIEWER,
            subject_id="subj1",
        )
        result = cc.submit_review(review)
        assert result.status == ConvergenceStatus.PENDING

    def test_converged_all_approved(self):
        cc = ConvergenceCheck(required_reviewers=2)
        r1 = AdversarialReview(
            id="r1", reviewer_id="a1", role=ReviewRole.REVIEWER,
            subject_id="subj1", verdict=ReviewVerdict.APPROVED,
        )
        r2 = AdversarialReview(
            id="r2", reviewer_id="a2", role=ReviewRole.REVIEWER,
            subject_id="subj1", verdict=ReviewVerdict.APPROVED,
        )
        cc.submit_review(r1)
        result = cc.submit_review(r2)
        assert result.status == ConvergenceStatus.CONVERGED
        assert result.consensus_verdict == ReviewVerdict.APPROVED
        assert result.agreement_ratio == 1.0

    def test_converged_all_rejected(self):
        cc = ConvergenceCheck(required_reviewers=2)
        r1 = AdversarialReview(
            id="r1", reviewer_id="a1", role=ReviewRole.REVIEWER,
            subject_id="subj1", verdict=ReviewVerdict.REJECTED,
        )
        r2 = AdversarialReview(
            id="r2", reviewer_id="a2", role=ReviewRole.REVIEWER,
            subject_id="subj1", verdict=ReviewVerdict.REJECTED,
        )
        cc.submit_review(r1)
        result = cc.submit_review(r2)
        assert result.status == ConvergenceStatus.CONVERGED
        assert result.consensus_verdict == ReviewVerdict.REJECTED

    def test_diverged_one_dissenter(self):
        cc = ConvergenceCheck(required_reviewers=3, agreement_threshold=0.6)
        r1 = AdversarialReview(
            id="r1", reviewer_id="a1", role=ReviewRole.REVIEWER,
            subject_id="subj1", verdict=ReviewVerdict.APPROVED,
        )
        r2 = AdversarialReview(
            id="r2", reviewer_id="a2", role=ReviewRole.REVIEWER,
            subject_id="subj1", verdict=ReviewVerdict.APPROVED,
        )
        r3 = AdversarialReview(
            id="r3", reviewer_id="a3", role=ReviewRole.REVIEWER,
            subject_id="subj1", verdict=ReviewVerdict.REVISE,
        )
        cc.submit_review(r1)
        cc.submit_review(r2)
        result = cc.submit_review(r3)
        # 2/3 = 0.67 ≥ 0.6 threshold → converged
        assert result.status == ConvergenceStatus.CONVERGED
        assert result.agreement_ratio == pytest.approx(2 / 3)

    def test_deadlocked_equal_split(self):
        cc = ConvergenceCheck(required_reviewers=2, agreement_threshold=0.6)
        r1 = AdversarialReview(
            id="r1", reviewer_id="a1", role=ReviewRole.REVIEWER,
            subject_id="subj1", verdict=ReviewVerdict.APPROVED,
        )
        r2 = AdversarialReview(
            id="r2", reviewer_id="a2", role=ReviewRole.REVIEWER,
            subject_id="subj1", verdict=ReviewVerdict.REJECTED,
        )
        cc.submit_review(r1)
        result = cc.submit_review(r2)
        assert result.status == ConvergenceStatus.DEADLOCKED

    def test_get_result(self):
        cc = ConvergenceCheck(required_reviewers=1)
        review = AdversarialReview(
            id="r1", reviewer_id="a1", role=ReviewRole.REVIEWER,
            subject_id="subj1",
        )
        cc.submit_review(review)
        result = cc.get_result("subj1")
        assert result is not None
        assert result.subject_id == "subj1"

    def test_get_result_nonexistent(self):
        cc = ConvergenceCheck()
        assert cc.get_result("nonexistent") is None

    def test_clear(self):
        cc = ConvergenceCheck(required_reviewers=1)
        review = AdversarialReview(
            id="r1", reviewer_id="a1", role=ReviewRole.REVIEWER,
            subject_id="subj1",
        )
        cc.submit_review(review)
        cc.clear("subj1")
        assert cc.get_result("subj1") is None

    def test_dissenting_reviewers_tracked(self):
        cc = ConvergenceCheck(required_reviewers=3, agreement_threshold=0.6)
        r1 = AdversarialReview(
            id="r1", reviewer_id="a1", role=ReviewRole.REVIEWER,
            subject_id="s1", verdict=ReviewVerdict.APPROVED,
        )
        r2 = AdversarialReview(
            id="r2", reviewer_id="a2", role=ReviewRole.REVIEWER,
            subject_id="s1", verdict=ReviewVerdict.REVISE,
        )
        r3 = AdversarialReview(
            id="r3", reviewer_id="a3", role=ReviewRole.REVIEWER,
            subject_id="s1", verdict=ReviewVerdict.APPROVED,
        )
        cc.submit_review(r1)
        cc.submit_review(r2)
        result = cc.submit_review(r3)
        assert "a2" in result.dissenting_reviewers


# ═══════════════════════════════════════════════════════════════════════════════
# ResumableWorkflow
# ═══════════════════════════════════════════════════════════════════════════════


class TestWorkflowStep:
    def test_create(self):
        step = WorkflowStep(id="s1", name="Review code")
        assert step.id == "s1"
        assert step.status == WorkflowStatus.NOT_STARTED
        assert step.retry_count == 0

    def test_can_retry(self):
        step = WorkflowStep(id="s1", name="Test", max_retries=3)
        assert step.can_retry

    def test_cannot_retry_after_max(self):
        step = WorkflowStep(id="s1", name="Test", max_retries=1,
                           retry_count=1)
        assert not step.can_retry


class TestWorkflowCheckpoint:
    def test_create(self):
        ckpt = WorkflowCheckpoint(
            id="c1", workflow_id="w1", step_id="s1",
            state={"progress": 0.5},
        )
        assert ckpt.id == "c1"
        assert ckpt.workflow_id == "w1"
        assert ckpt.state["progress"] == 0.5


class TestResumableWorkflow:
    def test_create(self):
        wf = ResumableWorkflow(id="w1", name="Code review workflow")
        assert wf.id == "w1"
        assert wf.status == WorkflowStatus.NOT_STARTED
        assert wf.progress == 0.0

    def test_add_step(self):
        wf = ResumableWorkflow(id="w1", name="Test")
        step = WorkflowStep(id="s1", name="Step 1")
        wf.add_step(step)
        assert len(wf.steps) == 1

    def test_current_step(self):
        wf = ResumableWorkflow(id="w1", name="Test")
        wf.add_step(WorkflowStep(id="s1", name="First"))
        wf.add_step(WorkflowStep(id="s2", name="Second"))
        assert wf.current_step.id == "s1"

    def test_current_step_none_when_empty(self):
        wf = ResumableWorkflow(id="w1", name="Test")
        assert wf.current_step is None

    def test_create_checkpoint(self):
        wf = ResumableWorkflow(id="w1", name="Test")
        wf.add_step(WorkflowStep(id="s1", name="First"))
        ckpt = wf.create_checkpoint("s1", {"data": "important"})
        assert len(wf.checkpoints) == 1
        assert ckpt.workflow_id == "w1"

    def test_restore_from_checkpoint(self):
        wf = ResumableWorkflow(id="w1", name="Test")
        wf.add_step(WorkflowStep(id="s1", name="First"))
        wf.add_step(WorkflowStep(id="s2", name="Second"))
        wf.current_step_index = 1  # on step 2

        ckpt = wf.create_checkpoint("s1", {})
        step = wf.restore_from_checkpoint(ckpt)
        assert step is not None
        assert step.id == "s1"
        assert wf.current_step_index == 0  # back to s1

    def test_restore_invalid_checkpoint(self):
        wf = ResumableWorkflow(id="w1", name="Test")
        wf.add_step(WorkflowStep(id="s1", name="First"))
        ckpt = WorkflowCheckpoint(
            id="c1", workflow_id="w1", step_id="nonexistent",
        )
        assert wf.restore_from_checkpoint(ckpt) is None

    def test_advance(self):
        wf = ResumableWorkflow(id="w1", name="Test")
        wf.add_step(WorkflowStep(id="s1", name="First",
                                status=WorkflowStatus.COMPLETED))
        wf.add_step(WorkflowStep(id="s2", name="Second"))
        step = wf.advance()
        assert step is not None
        assert step.id == "s2"

    def test_advance_all_complete(self):
        wf = ResumableWorkflow(id="w1", name="Test")
        wf.add_step(WorkflowStep(id="s1", name="First",
                                status=WorkflowStatus.COMPLETED))
        wf.add_step(WorkflowStep(id="s2", name="Second",
                                status=WorkflowStatus.COMPLETED))
        step = wf.advance()
        assert step is None
        assert wf.is_complete

    def test_retry_current(self):
        wf = ResumableWorkflow(id="w1", name="Test")
        wf.add_step(WorkflowStep(id="s1", name="First",
                                status=WorkflowStatus.FAILED))
        assert wf.retry_current()
        assert wf.current_step.retry_count == 1

    def test_retry_current_exceeded(self):
        wf = ResumableWorkflow(id="w1", name="Test")
        wf.add_step(WorkflowStep(id="s1", name="First",
                                status=WorkflowStatus.FAILED,
                                retry_count=3, max_retries=3))
        assert not wf.retry_current()

    def test_progress_calculation(self):
        wf = ResumableWorkflow(id="w1", name="Test")
        wf.add_step(WorkflowStep(id="s1", name="First",
                                status=WorkflowStatus.COMPLETED))
        wf.add_step(WorkflowStep(id="s2", name="Second"))
        wf.add_step(WorkflowStep(id="s3", name="Third"))
        assert wf.progress == 1 / 3

    def test_progress_empty(self):
        wf = ResumableWorkflow(id="w1", name="Test")
        assert wf.progress == 0.0

    def test_is_complete_and_is_failed(self):
        wf = ResumableWorkflow(id="w1", name="Test")
        assert not wf.is_complete
        wf.status = WorkflowStatus.COMPLETED
        assert wf.is_complete
        wf.status = WorkflowStatus.FAILED
        assert wf.is_failed


# ═══════════════════════════════════════════════════════════════════════════════
# ReviewSession
# ═══════════════════════════════════════════════════════════════════════════════


class TestReviewSession:
    def test_create(self):
        session = ReviewSession(id="s1", subject_id="task_1")
        assert session.id == "s1"
        assert session.subject_id == "task_1"
        assert session.review_count == 0
        assert session.status == "collecting_reviews"

    def test_submit_review_converges(self):
        session = ReviewSession(
            id="s1", subject_id="task_1", required_reviewers=2,
        )
        r1 = AdversarialReview(
            id="r1", reviewer_id="a1", role=ReviewRole.REVIEWER,
            subject_id="task_1", verdict=ReviewVerdict.APPROVED,
        )
        r2 = AdversarialReview(
            id="r2", reviewer_id="a2", role=ReviewRole.REVIEWER,
            subject_id="task_1", verdict=ReviewVerdict.APPROVED,
        )
        session.submit_review(r1)
        result = session.submit_review(r2)
        assert result.status == ConvergenceStatus.CONVERGED
        assert session.has_consensus

    def test_submit_review_deadlocks(self):
        session = ReviewSession(
            id="s1", subject_id="task_1", required_reviewers=2,
        )
        r1 = AdversarialReview(
            id="r1", reviewer_id="a1", role=ReviewRole.REVIEWER,
            subject_id="task_1", verdict=ReviewVerdict.APPROVED,
        )
        r2 = AdversarialReview(
            id="r2", reviewer_id="a2", role=ReviewRole.REVIEWER,
            subject_id="task_1", verdict=ReviewVerdict.REJECTED,
        )
        session.submit_review(r1)
        session.submit_review(r2)
        assert session.needs_arbitration

    def test_arbitrate_resolves(self):
        session = ReviewSession(id="s1", subject_id="task_1")
        # Manually set deadlocked state
        r1 = AdversarialReview(
            id="r1", reviewer_id="a1", role=ReviewRole.REVIEWER,
            subject_id="task_1", verdict=ReviewVerdict.APPROVED,
        )
        r2 = AdversarialReview(
            id="r2", reviewer_id="a2", role=ReviewRole.REVIEWER,
            subject_id="task_1", verdict=ReviewVerdict.REJECTED,
        )
        session.submit_review(r1)
        session.submit_review(r2)

        session.arbitrate("arbiter_1", ReviewVerdict.APPROVED,
                         "Majority rule applies")
        assert session.status == "resolved"
        assert session.final_verdict == ReviewVerdict.APPROVED

    def test_get_critical_findings(self):
        session = ReviewSession(id="s1", subject_id="task_1")
        review = AdversarialReview(
            id="r1", reviewer_id="a1", role=ReviewRole.REVIEWER,
            subject_id="task_1",
        )
        review.add_finding(ReviewFinding(
            id="f1", reviewer_id="a1", severity=Severity.CRITICAL,
            category="security", description="Secret leak",
        ))
        review.add_finding(ReviewFinding(
            id="f2", reviewer_id="a1", severity=Severity.LOW,
            category="style", description="Formatting",
        ))
        session.submit_review(review)
        critical = session.get_critical_findings()
        assert len(critical) == 1
        assert critical[0].id == "f1"

    def test_get_findings_by_severity(self):
        session = ReviewSession(id="s1", subject_id="task_1")
        review = AdversarialReview(
            id="r1", reviewer_id="a1", role=ReviewRole.REVIEWER,
            subject_id="task_1",
        )
        review.add_finding(ReviewFinding(
            id="f1", reviewer_id="a1", severity=Severity.HIGH,
            category="perf", description="slow",
        ))
        review.add_finding(ReviewFinding(
            id="f2", reviewer_id="a1", severity=Severity.HIGH,
            category="security", description="xss",
        ))
        session.submit_review(review)
        high_findings = session.get_findings_by_severity(Severity.HIGH)
        assert len(high_findings) == 2

    def test_review_count(self):
        session = ReviewSession(id="s1", subject_id="task_1")
        assert session.review_count == 0
        review = AdversarialReview(
            id="r1", reviewer_id="a1", role=ReviewRole.REVIEWER,
            subject_id="task_1",
        )
        session.submit_review(review)
        assert session.review_count == 1

    def test_has_consensus_initially_false(self):
        session = ReviewSession(id="s1", subject_id="task_1")
        assert not session.has_consensus

    def test_needs_arbitration_initially_false(self):
        session = ReviewSession(id="s1", subject_id="task_1")
        assert not session.needs_arbitration


# ═══════════════════════════════════════════════════════════════════════════════
# Enum completeness
# ═══════════════════════════════════════════════════════════════════════════════


class TestEnums:
    def test_review_role_values(self):
        for role in ReviewRole:
            assert isinstance(role.value, str)

    def test_review_verdict_values(self):
        for v in ReviewVerdict:
            assert isinstance(v.value, str)

    def test_severity_values(self):
        for s in Severity:
            assert isinstance(s.value, str)

    def test_convergence_status_values(self):
        for s in ConvergenceStatus:
            assert isinstance(s.value, str)

    def test_workflow_status_values(self):
        for s in WorkflowStatus:
            assert isinstance(s.value, str)

