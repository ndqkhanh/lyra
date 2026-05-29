"""Adversarial Review & Convergence — Multi-agent verification system.

Inspired by AutoScientists adversarial review and Claude Code Dynamic Workflows:
  - Adversarial reviewer role: actively tries to find flaws
  - Validator role: confirms correctness independently
  - Convergence check: N independent agents must agree before proceeding
  - Resumable workflows: checkpoint-based state persistence for long-running tasks

The adversarial review process:
  1. Producer agent creates output
  2. Reviewer agents critique the output (seeking flaws)
  3. Validator agents independently verify correctness
  4. Arbitrator resolves disagreements
  5. Convergence gate: N agents must reach consensus before proceeding
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from lyra_core.events import EventBus, EventCategory

logger = logging.getLogger(__name__)


# ── Review Roles ─────────────────────────────────────────────────────────────


class ReviewRole(str, Enum):
    """Roles in the adversarial review process."""
    PRODUCER = "producer"      # Created the work being reviewed
    REVIEWER = "reviewer"      # Seeks flaws and weaknesses
    VALIDATOR = "validator"    # Independently verifies correctness
    ARBITRATOR = "arbitrator"  # Resolves disagreements between reviewers
    CONVERGENCE = "convergence"  # Checks if N agents agree


class ReviewVerdict(str, Enum):
    """Possible review outcomes."""
    APPROVED = "approved"        # No issues found
    APPROVED_WITH_SUGGESTIONS = "approved_with_suggestions"  # Minor improvements
    REVISE = "revise"            # Changes needed before approval
    REJECTED = "rejected"        # Fundamentally flawed
    ESCALATED = "escalated"      # Requires arbitrator intervention
    DEADLOCKED = "deadlocked"    # Can't reach consensus


class Severity(str, Enum):
    """Issue severity in reviews."""
    CRITICAL = "critical"  # Must fix — security, correctness, safety
    HIGH = "high"          # Should fix — significant quality issues
    MEDIUM = "medium"      # Consider fixing — maintainability
    LOW = "low"            # Minor — style, preference
    INFO = "info"          # Informational only


# ── Review ───────────────────────────────────────────────────────────────────


@dataclass
class ReviewFinding:
    """A single finding from a review."""

    id: str
    reviewer_id: str
    severity: Severity
    category: str  # security, correctness, performance, style, etc.
    description: str
    location: str = ""  # file:line or logical location
    suggestion: str = ""
    created_at: float = field(default_factory=time.time)


@dataclass
class AdversarialReview:
    """Complete review from a single reviewer."""

    id: str
    reviewer_id: str
    role: ReviewRole
    subject_id: str  # What's being reviewed (task_id, hypothesis_id, etc.)
    subject_type: str = "task"  # task, hypothesis, code, design, etc.
    verdict: ReviewVerdict = ReviewVerdict.APPROVED
    findings: list[ReviewFinding] = field(default_factory=list)
    summary: str = ""
    confidence: float = 1.0  # Reviewer's confidence in their verdict (0.0–1.0)
    created_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.CRITICAL)

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings
                   if f.severity in (Severity.CRITICAL, Severity.HIGH))

    @property
    def is_clean(self) -> bool:
        return len(self.findings) == 0

    @property
    def has_critical(self) -> bool:
        return self.critical_count > 0

    def add_finding(self, finding: ReviewFinding) -> None:
        self.findings.append(finding)

    def update_verdict(self) -> ReviewVerdict:
        """Auto-compute verdict from findings."""
        if self.has_critical:
            self.verdict = ReviewVerdict.REJECTED
        elif self.high_count > 0:
            self.verdict = ReviewVerdict.REVISE
        elif any(f.severity == Severity.MEDIUM for f in self.findings):
            self.verdict = ReviewVerdict.APPROVED_WITH_SUGGESTIONS
        else:
            self.verdict = ReviewVerdict.APPROVED
        return self.verdict


# ── Convergence ──────────────────────────────────────────────────────────────


class ConvergenceStatus(str, Enum):
    """Status of a convergence check."""
    PENDING = "pending"        # Not enough reviews yet
    CONVERGED = "converged"    # N agents agree
    DIVERGED = "diverged"      # Agents disagree
    DEADLOCKED = "deadlocked"  # Can't resolve disagreement
    ESCALATED = "escalated"    # Sent to arbitrator


@dataclass
class ConvergenceResult:
    """Result of a convergence check across multiple reviews."""

    subject_id: str
    status: ConvergenceStatus = ConvergenceStatus.PENDING
    reviews: list[AdversarialReview] = field(default_factory=list)
    consensus_verdict: ReviewVerdict | None = None
    agreement_ratio: float = 0.0
    dissenting_reviewers: list[str] = field(default_factory=list)
    arbitrator_verdict: ReviewVerdict | None = None
    arbitrator_rationale: str = ""
    resolved_at: float | None = None


class ConvergenceCheck:
    """Checks if N independent reviewers agree before proceeding.

    Like Claude Code Dynamic Workflows convergence pattern:
      "N independent agents must agree before the result is accepted."

    If convergence fails:
      1. Auto-escalate: if disagreement rate > threshold → arbitrator
      2. Majority vote: if N/2 < agree ≤ N → majority prevails
      3. Deadlock: if exactly tied → escalate
    """

    def __init__(self, required_reviewers: int = 2,
                 agreement_threshold: float = 0.6,
                 bus: EventBus | None = None) -> None:
        self.required = required_reviewers
        self.agreement_threshold = agreement_threshold
        self._bus = bus or EventBus.get()
        self._active_checks: dict[str, ConvergenceResult] = {}

    def submit_review(self, review: AdversarialReview) -> ConvergenceResult:
        """Submit a review for convergence checking."""
        subject_id = review.subject_id

        if subject_id not in self._active_checks:
            self._active_checks[subject_id] = ConvergenceResult(
                subject_id=subject_id,
            )

        result = self._active_checks[subject_id]
        result.reviews.append(review)

        # Check convergence
        if len(result.reviews) >= self.required:
            result = self._evaluate_convergence(result)

        return result

    def _evaluate_convergence(self, result: ConvergenceResult) -> ConvergenceResult:
        """Evaluate whether N reviewers have converged."""
        reviews = result.reviews

        if len(reviews) < self.required:
            return result

        # Count verdicts
        verdicts = [r.verdict for r in reviews]
        from collections import Counter
        verdict_counts = Counter(verdicts)
        most_common_verdict, most_common_count = verdict_counts.most_common(1)[0]

        agreement = most_common_count / len(reviews)

        result.agreement_ratio = agreement

        if agreement >= self.agreement_threshold:
            result.status = ConvergenceStatus.CONVERGED
            result.consensus_verdict = most_common_verdict
            result.dissenting_reviewers = [
                r.reviewer_id for r in reviews
                if r.verdict != most_common_verdict
            ]
        elif agreement > 0.5:
            # Majority but below threshold — weak convergence
            result.status = ConvergenceStatus.DIVERGED
            result.consensus_verdict = most_common_verdict
            result.dissenting_reviewers = [
                r.reviewer_id for r in reviews
                if r.verdict != most_common_verdict
            ]
        elif agreement == 0.5:
            # Exact tie — deadlock
            result.status = ConvergenceStatus.DEADLOCKED
        else:
            result.status = ConvergenceStatus.DIVERGED

        result.resolved_at = time.time()

        self._bus.publish(
            category=EventCategory.LIFECYCLE,
            name="convergence.evaluated",
            origin=__name__,
            payload={
                "subject_id": result.subject_id,
                "status": result.status.value,
                "agreement_ratio": agreement,
                "review_count": len(reviews),
                "consensus": result.consensus_verdict.value if result.consensus_verdict else None,
            },
        )

        return result

    def get_result(self, subject_id: str) -> ConvergenceResult | None:
        return self._active_checks.get(subject_id)

    def clear(self, subject_id: str) -> None:
        self._active_checks.pop(subject_id, None)

    @property
    def active_count(self) -> int:
        return len(self._active_checks)


# ── Resumable Workflows ──────────────────────────────────────────────────────


class WorkflowStatus(str, Enum):
    """Status of a resumable workflow."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    WAITING_REVIEW = "waiting_review"
    WAITING_CONVERGENCE = "waiting_convergence"
    REVISING = "revising"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class WorkflowStep:
    """A single step in a resumable workflow."""

    id: str
    name: str
    status: WorkflowStatus = WorkflowStatus.NOT_STARTED
    assigned_agent: str = ""
    input_snapshot: dict[str, Any] = field(default_factory=dict)
    output_snapshot: dict[str, Any] = field(default_factory=dict)
    reviews: list[AdversarialReview] = field(default_factory=list)
    started_at: float | None = None
    completed_at: float | None = None
    retry_count: int = 0
    max_retries: int = 3

    @property
    def can_retry(self) -> bool:
        return self.retry_count < self.max_retries


@dataclass
class WorkflowCheckpoint:
    """A checkpoint in a resumable workflow. Like tmux's saved layout state."""

    id: str
    workflow_id: str
    step_id: str
    state: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ResumableWorkflow:
    """A workflow that can be paused and resumed from checkpoints.

    Like Claude Code Dynamic Workflows resumable pattern:
      "Workflows are checkpointed so they can resume after interruption."
    """

    id: str
    name: str
    steps: list[WorkflowStep] = field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.NOT_STARTED
    current_step_index: int = 0
    checkpoints: list[WorkflowCheckpoint] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None
    convergence: ConvergenceCheck | None = None

    @property
    def current_step(self) -> WorkflowStep | None:
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None

    @property
    def is_complete(self) -> bool:
        return self.status == WorkflowStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        return self.status == WorkflowStatus.FAILED

    @property
    def progress(self) -> float:
        """Return progress as 0.0–1.0."""
        if not self.steps:
            return 1.0 if self.is_complete else 0.0
        completed = sum(
            1 for s in self.steps
            if s.status in (WorkflowStatus.COMPLETED,)
        )
        return completed / len(self.steps)

    def add_step(self, step: WorkflowStep) -> None:
        self.steps.append(step)

    def create_checkpoint(self, step_id: str,
                         state: dict[str, Any] | None = None) -> WorkflowCheckpoint:
        """Create a checkpoint for the current workflow state."""
        import uuid
        checkpoint = WorkflowCheckpoint(
            id=f"ckpt_{uuid.uuid4().hex[:8]}",
            workflow_id=self.id,
            step_id=step_id,
            state=state or {},
        )
        self.checkpoints.append(checkpoint)
        return checkpoint

    def restore_from_checkpoint(self,
                                checkpoint: WorkflowCheckpoint) -> WorkflowStep | None:
        """Restore workflow to a specific checkpoint."""
        # Find the step in our list
        for i, step in enumerate(self.steps):
            if step.id == checkpoint.step_id:
                self.current_step_index = i
                self.status = WorkflowStatus.IN_PROGRESS
                return step
        return None

    def advance(self) -> WorkflowStep | None:
        """Move to the next incomplete step."""
        for i in range(self.current_step_index + 1, len(self.steps)):
            if self.steps[i].status != WorkflowStatus.COMPLETED:
                self.current_step_index = i
                return self.steps[i]

        # All steps complete
        self.status = WorkflowStatus.COMPLETED
        self.completed_at = time.time()
        return None

    def retry_current(self) -> bool:
        """Retry the current step if possible."""
        step = self.current_step
        if step and step.can_retry:
            step.retry_count += 1
            step.status = WorkflowStatus.IN_PROGRESS
            return True
        return False


# ── Review Session ───────────────────────────────────────────────────────────


@dataclass
class ReviewSession:
    """Orchestrates adversarial review across multiple reviewers.

    A full review session:
      1. Producer submits work
      2. N reviewers independently review
      3. Convergence check determines if agreement is reached
      4. If divergent → arbitrator resolves
      5. If deadlocked → escalation
    """

    id: str
    subject_id: str
    required_reviewers: int = 2
    convergence: ConvergenceCheck = field(default_factory=ConvergenceCheck)
    reviews: list[AdversarialReview] = field(default_factory=list)
    status: str = "collecting_reviews"  # collecting_reviews, evaluating, converged, deadlocked, resolved
    created_at: float = field(default_factory=time.time)
    resolved_at: float | None = None
    final_verdict: ReviewVerdict | None = None

    def submit_review(self, review: AdversarialReview) -> ConvergenceResult:
        self.reviews.append(review)
        result = self.convergence.submit_review(review)

        if result.status == ConvergenceStatus.CONVERGED:
            self.status = "converged"
            self.final_verdict = result.consensus_verdict
            self.resolved_at = time.time()
        elif result.status == ConvergenceStatus.DEADLOCKED:
            self.status = "deadlocked"
        elif result.status == ConvergenceStatus.DIVERGED:
            self.status = "divergent"

        return result

    def arbitrate(self, _arbitrator_id: str, verdict: ReviewVerdict,
                 rationale: str) -> None:
        """An arbitrator resolves the deadlock/divergence."""
        result = self.convergence.get_result(self.subject_id)
        if result:
            result.status = ConvergenceStatus.ESCALATED
            result.arbitrator_verdict = verdict
            result.arbitrator_rationale = rationale

        self.status = "resolved"
        self.final_verdict = verdict
        self.resolved_at = time.time()

    def get_findings_by_severity(self, severity: Severity) -> list[ReviewFinding]:
        """Collect all findings of a given severity across all reviews."""
        findings: list[ReviewFinding] = []
        for review in self.reviews:
            for finding in review.findings:
                if finding.severity == severity:
                    findings.append(finding)
        return findings

    def get_critical_findings(self) -> list[ReviewFinding]:
        return self.get_findings_by_severity(Severity.CRITICAL)

    @property
    def review_count(self) -> int:
        return len(self.reviews)

    @property
    def has_consensus(self) -> bool:
        return self.status == "converged"

    @property
    def needs_arbitration(self) -> bool:
        return self.status in ("deadlocked", "divergent")
