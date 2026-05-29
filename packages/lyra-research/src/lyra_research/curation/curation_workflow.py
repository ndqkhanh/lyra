"""Curation Workflow — Decision-making process for knowledge curation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from lyra_research.curation.knowledge_entry import EntryStatus, KnowledgeEntry


class DecisionType(Enum):
    """Type of curation decision."""

    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_REVISION = "request_revision"


@dataclass
class CurationDecision:
    """
    Decision made during curation workflow.

    Contains the decision type, reasoning, and any feedback for revision.
    """

    decision_type: DecisionType
    entry_id: str
    reason: str
    feedback: str | None = None
    quality_threshold: float = 0.7

    def __post_init__(self) -> None:
        """Validate decision after initialization."""
        if not self.entry_id:
            raise ValueError("Entry ID cannot be empty")
        if not self.reason:
            raise ValueError("Reason cannot be empty")
        if self.decision_type == DecisionType.REQUEST_REVISION and not self.feedback:
            raise ValueError("Feedback required for revision request")


class CurationWorkflow:
    """
    Curation workflow for knowledge entries.

    Implements the decision-making process for accepting, rejecting,
    or requesting revisions for knowledge entries.
    """

    def __init__(self, quality_threshold: float = 0.7) -> None:
        """
        Initialize curation workflow.

        Args:
            quality_threshold: Minimum quality score for approval (default: 0.7)
        """
        if not 0.0 <= quality_threshold <= 1.0:
            raise ValueError("Quality threshold must be between 0.0 and 1.0")
        self.quality_threshold = quality_threshold

    def review(self, entry: KnowledgeEntry) -> CurationDecision:
        """
        Review entry and make curation decision.

        Args:
            entry: Knowledge entry to review

        Returns:
            CurationDecision with recommendation
        """
        # Check quality score
        if entry.quality_score >= self.quality_threshold:
            # High quality - approve
            return CurationDecision(
                decision_type=DecisionType.APPROVE,
                entry_id=entry.id,
                reason=(
                    f"Quality score {entry.quality_score:.2f} meets threshold "
                    f"{self.quality_threshold:.2f}"
                ),
                quality_threshold=self.quality_threshold,
            )
        elif entry.quality_score >= self.quality_threshold - 0.1:
            # Close to threshold - request revision
            return CurationDecision(
                decision_type=DecisionType.REQUEST_REVISION,
                entry_id=entry.id,
                reason=(
                    f"Quality score {entry.quality_score:.2f} slightly below threshold "
                    f"{self.quality_threshold:.2f}"
                ),
                feedback="Please improve content quality to meet acceptance criteria",
                quality_threshold=self.quality_threshold,
            )
        else:
            # Low quality - reject
            return CurationDecision(
                decision_type=DecisionType.REJECT,
                entry_id=entry.id,
                reason=(
                    f"Quality score {entry.quality_score:.2f} significantly below threshold "
                    f"{self.quality_threshold:.2f}"
                ),
                quality_threshold=self.quality_threshold,
            )

    def approve(self, entry: KnowledgeEntry) -> KnowledgeEntry:
        """
        Approve entry for storage.

        Args:
            entry: Knowledge entry to approve

        Returns:
            Approved KnowledgeEntry
        """
        if entry.status == EntryStatus.APPROVED:
            return entry
        return entry.approve()

    def reject(self, entry: KnowledgeEntry, reason: str) -> KnowledgeEntry:
        """
        Reject entry with reason.

        Args:
            entry: Knowledge entry to reject
            reason: Reason for rejection

        Returns:
            Rejected KnowledgeEntry with reason in metadata
        """
        rejected_entry = entry.reject()
        rejected_entry.metadata["rejection_reason"] = reason
        return rejected_entry

    def request_revision(self, entry: KnowledgeEntry, feedback: str) -> KnowledgeEntry:
        """
        Request revision with feedback.

        Args:
            entry: Knowledge entry to revise
            feedback: Feedback for revision

        Returns:
            KnowledgeEntry with revision feedback in metadata
        """
        # Store feedback in metadata
        entry.metadata["revision_feedback"] = feedback
        entry.metadata["revision_requested"] = True

        # Return entry with updated metadata (status remains PENDING)
        return KnowledgeEntry(
            id=entry.id,
            content=entry.content,
            source=entry.source,
            quality_score=entry.quality_score,
            category=entry.category,
            tags=entry.tags,
            version=entry.version,
            created_at=entry.created_at,
            updated_at=entry.updated_at,
            status=EntryStatus.PENDING,
            metadata=entry.metadata,
        )

    def apply_decision(self, entry: KnowledgeEntry, decision: CurationDecision) -> KnowledgeEntry:
        """
        Apply curation decision to entry.

        Args:
            entry: Knowledge entry
            decision: Curation decision to apply

        Returns:
            Updated KnowledgeEntry
        """
        if decision.entry_id != entry.id:
            raise ValueError("Decision entry ID does not match entry ID")

        if decision.decision_type == DecisionType.APPROVE:
            return self.approve(entry)
        elif decision.decision_type == DecisionType.REJECT:
            return self.reject(entry, decision.reason)
        elif decision.decision_type == DecisionType.REQUEST_REVISION:
            return self.request_revision(entry, decision.feedback or "")
        else:
            raise ValueError(f"Unknown decision type: {decision.decision_type}")
