"""User review system for workflow checkpoints.

Handles user review requests, feedback collection, and approval workflow.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from lyra_core.orchestration.workflow.models import Artifact, SDLCPhase


@dataclass(frozen=True)
class ReviewRequest:
    """Immutable review request for user approval.

    Attributes:
        id: Unique request identifier
        workflow_id: Associated workflow ID
        phase: Phase requesting review
        artifacts: Artifacts to review
        questions: Questions for the user
        deadline: Review deadline (ISO 8601)
        created_at: ISO 8601 timestamp
        metadata: Additional request metadata
    """

    id: str
    workflow_id: str
    phase: SDLCPhase
    artifacts: tuple[Artifact, ...]
    questions: tuple[str, ...]
    deadline: str
    created_at: str
    metadata: dict[str, Any]

    @staticmethod
    def create(
        workflow_id: str,
        phase: SDLCPhase,
        artifacts: list[Artifact],
        questions: list[str] | None = None,
        deadline_hours: int = 24,
        metadata: dict[str, Any] | None = None,
    ) -> ReviewRequest:
        """Create review request with auto-generated ID and timestamps.

        Args:
            workflow_id: Workflow ID
            phase: Phase requesting review
            artifacts: Artifacts to review
            questions: Optional questions for user
            deadline_hours: Hours until deadline (default: 24)
            metadata: Optional metadata

        Returns:
            New ReviewRequest instance
        """
        now = datetime.now(timezone.utc)
        deadline = now + timedelta(hours=deadline_hours)

        return ReviewRequest(
            id=str(uuid.uuid4()),
            workflow_id=workflow_id,
            phase=phase,
            artifacts=tuple(artifacts),
            questions=tuple(questions or []),
            deadline=deadline.isoformat(),
            created_at=now.isoformat(),
            metadata=metadata or {},
        )


@dataclass(frozen=True)
class UserFeedback:
    """Immutable user feedback on a review request.

    Attributes:
        id: Unique feedback identifier
        request_id: Associated review request ID
        workflow_id: Associated workflow ID
        phase: Phase being reviewed
        approved: Whether user approved
        comments: User comments
        changes_requested: List of requested changes
        created_at: ISO 8601 timestamp
    """

    id: str
    request_id: str
    workflow_id: str
    phase: SDLCPhase
    approved: bool
    comments: str
    changes_requested: tuple[str, ...]
    created_at: str

    @staticmethod
    def create(
        request_id: str,
        workflow_id: str,
        phase: SDLCPhase,
        approved: bool,
        comments: str = "",
        changes_requested: list[str] | None = None,
    ) -> UserFeedback:
        """Create user feedback with auto-generated ID and timestamp.

        Args:
            request_id: Review request ID
            workflow_id: Workflow ID
            phase: Phase being reviewed
            approved: Approval status
            comments: User comments
            changes_requested: Optional change requests

        Returns:
            New UserFeedback instance
        """
        return UserFeedback(
            id=str(uuid.uuid4()),
            request_id=request_id,
            workflow_id=workflow_id,
            phase=phase,
            approved=approved,
            comments=comments,
            changes_requested=tuple(changes_requested or []),
            created_at=datetime.now(timezone.utc).isoformat(),
        )


class UserReviewHandler:
    """Handler for user review workflow.

    Manages review requests, feedback collection, and approval logic.
    """

    def __init__(self) -> None:
        """Initialize review handler."""
        self._pending_reviews: dict[str, ReviewRequest] = {}
        self._feedback_history: dict[str, list[UserFeedback]] = {}

    async def create_review_request(
        self,
        workflow_id: str,
        phase: SDLCPhase,
        artifacts: list[Artifact],
        questions: list[str] | None = None,
        deadline_hours: int = 24,
    ) -> ReviewRequest:
        """Create a new review request.

        Args:
            workflow_id: Workflow ID
            phase: Phase requesting review
            artifacts: Artifacts to review
            questions: Optional questions
            deadline_hours: Hours until deadline

        Returns:
            Created review request
        """
        request = ReviewRequest.create(
            workflow_id=workflow_id,
            phase=phase,
            artifacts=artifacts,
            questions=questions,
            deadline_hours=deadline_hours,
        )

        self._pending_reviews[request.id] = request
        return request

    async def submit_feedback(
        self,
        request_id: str,
        approved: bool,
        comments: str = "",
        changes_requested: list[str] | None = None,
    ) -> UserFeedback:
        """Submit user feedback for a review request.

        Args:
            request_id: Review request ID
            approved: Approval status
            comments: User comments
            changes_requested: Optional change requests

        Returns:
            Created feedback

        Raises:
            ValueError: If request doesn't exist
        """
        if request_id not in self._pending_reviews:
            raise ValueError(f"Review request {request_id} not found")

        request = self._pending_reviews[request_id]

        feedback = UserFeedback.create(
            request_id=request_id,
            workflow_id=request.workflow_id,
            phase=request.phase,
            approved=approved,
            comments=comments,
            changes_requested=changes_requested,
        )

        # Store feedback
        if request.workflow_id not in self._feedback_history:
            self._feedback_history[request.workflow_id] = []
        self._feedback_history[request.workflow_id].append(feedback)

        # Remove from pending if approved
        if approved:
            del self._pending_reviews[request_id]

        return feedback

    async def get_pending_reviews(
        self,
        workflow_id: str | None = None,
    ) -> list[ReviewRequest]:
        """Get pending review requests.

        Args:
            workflow_id: Optional workflow ID to filter by

        Returns:
            List of pending review requests
        """
        reviews = list(self._pending_reviews.values())
        if workflow_id:
            reviews = [r for r in reviews if r.workflow_id == workflow_id]
        return reviews

    async def get_feedback_history(
        self,
        workflow_id: str,
    ) -> list[UserFeedback]:
        """Get feedback history for a workflow.

        Args:
            workflow_id: Workflow ID

        Returns:
            List of feedback entries
        """
        return self._feedback_history.get(workflow_id, []).copy()

    async def cancel_review(self, request_id: str) -> None:
        """Cancel a pending review request.

        Args:
            request_id: Review request ID

        Raises:
            ValueError: If request doesn't exist
        """
        if request_id not in self._pending_reviews:
            raise ValueError(f"Review request {request_id} not found")

        del self._pending_reviews[request_id]


__all__ = ["ReviewRequest", "UserFeedback", "UserReviewHandler"]
