"""Tests for user review system."""

import pytest

from lyra_core.orchestration.workflow.models import Artifact, SDLCPhase
from lyra_core.orchestration.workflow.user_review import (
    ReviewRequest,
    UserFeedback,
    UserReviewHandler,
)


class TestReviewRequest:
    """Test suite for ReviewRequest."""

    def test_create_review_request(self) -> None:
        """Test creating a review request."""
        artifacts = [
            Artifact.create(
                type="prd",
                name="PRD",
                content={"title": "Test PRD"},
                phase=SDLCPhase.DISCOVERY,
            )
        ]

        request = ReviewRequest.create(
            workflow_id="workflow-123",
            phase=SDLCPhase.DISCOVERY,
            artifacts=artifacts,
            questions=["Is this correct?"],
            deadline_hours=24,
        )

        assert request.workflow_id == "workflow-123"
        assert request.phase == SDLCPhase.DISCOVERY
        assert len(request.artifacts) == 1
        assert len(request.questions) == 1
        assert request.questions[0] == "Is this correct?"
        assert request.id is not None
        assert request.created_at is not None
        assert request.deadline is not None

    def test_review_request_immutable(self) -> None:
        """Test that ReviewRequest is immutable."""
        request = ReviewRequest.create(
            workflow_id="workflow-123",
            phase=SDLCPhase.DISCOVERY,
            artifacts=[],
        )

        with pytest.raises(AttributeError):
            request.workflow_id = "new-id"  # type: ignore


class TestUserFeedback:
    """Test suite for UserFeedback."""

    def test_create_user_feedback(self) -> None:
        """Test creating user feedback."""
        feedback = UserFeedback.create(
            request_id="request-123",
            workflow_id="workflow-123",
            phase=SDLCPhase.DISCOVERY,
            approved=True,
            comments="Looks good!",
            changes_requested=["Add more details"],
        )

        assert feedback.request_id == "request-123"
        assert feedback.workflow_id == "workflow-123"
        assert feedback.phase == SDLCPhase.DISCOVERY
        assert feedback.approved is True
        assert feedback.comments == "Looks good!"
        assert len(feedback.changes_requested) == 1
        assert feedback.id is not None
        assert feedback.created_at is not None

    def test_user_feedback_immutable(self) -> None:
        """Test that UserFeedback is immutable."""
        feedback = UserFeedback.create(
            request_id="request-123",
            workflow_id="workflow-123",
            phase=SDLCPhase.DISCOVERY,
            approved=True,
        )

        with pytest.raises(AttributeError):
            feedback.approved = False  # type: ignore


class TestUserReviewHandler:
    """Test suite for UserReviewHandler."""

    @pytest.mark.asyncio
    async def test_create_review_request(self) -> None:
        """Test creating a review request."""
        handler = UserReviewHandler()

        artifacts = [
            Artifact.create(
                type="prd",
                name="PRD",
                content={"title": "Test"},
                phase=SDLCPhase.DISCOVERY,
            )
        ]

        request = await handler.create_review_request(
            workflow_id="workflow-123",
            phase=SDLCPhase.DISCOVERY,
            artifacts=artifacts,
            questions=["Question 1"],
        )

        assert request.workflow_id == "workflow-123"
        assert request.phase == SDLCPhase.DISCOVERY

        # Check it's in pending reviews
        pending = await handler.get_pending_reviews()
        assert len(pending) == 1
        assert pending[0].id == request.id

    @pytest.mark.asyncio
    async def test_submit_feedback_approved(self) -> None:
        """Test submitting approved feedback."""
        handler = UserReviewHandler()

        # Create review request
        request = await handler.create_review_request(
            workflow_id="workflow-123",
            phase=SDLCPhase.DISCOVERY,
            artifacts=[],
        )

        # Submit approved feedback
        feedback = await handler.submit_feedback(
            request_id=request.id,
            approved=True,
            comments="Approved!",
        )

        assert feedback.approved is True
        assert feedback.request_id == request.id

        # Should be removed from pending
        pending = await handler.get_pending_reviews()
        assert len(pending) == 0

        # Should be in feedback history
        history = await handler.get_feedback_history("workflow-123")
        assert len(history) == 1
        assert history[0].id == feedback.id

    @pytest.mark.asyncio
    async def test_submit_feedback_rejected(self) -> None:
        """Test submitting rejected feedback."""
        handler = UserReviewHandler()

        # Create review request
        request = await handler.create_review_request(
            workflow_id="workflow-123",
            phase=SDLCPhase.DISCOVERY,
            artifacts=[],
        )

        # Submit rejected feedback
        feedback = await handler.submit_feedback(
            request_id=request.id,
            approved=False,
            comments="Needs changes",
            changes_requested=["Fix issue 1", "Fix issue 2"],
        )

        assert feedback.approved is False
        assert len(feedback.changes_requested) == 2

        # Should still be in pending (not removed on rejection)
        pending = await handler.get_pending_reviews()
        assert len(pending) == 1

    @pytest.mark.asyncio
    async def test_submit_feedback_invalid_request(self) -> None:
        """Test submitting feedback for non-existent request."""
        handler = UserReviewHandler()

        with pytest.raises(ValueError, match="not found"):
            await handler.submit_feedback(
                request_id="invalid-id",
                approved=True,
            )

    @pytest.mark.asyncio
    async def test_get_pending_reviews_filtered(self) -> None:
        """Test getting pending reviews filtered by workflow."""
        handler = UserReviewHandler()

        # Create requests for different workflows
        await handler.create_review_request(
            workflow_id="workflow-1",
            phase=SDLCPhase.DISCOVERY,
            artifacts=[],
        )
        await handler.create_review_request(
            workflow_id="workflow-2",
            phase=SDLCPhase.DESIGN,
            artifacts=[],
        )

        # Get all pending
        all_pending = await handler.get_pending_reviews()
        assert len(all_pending) == 2

        # Get filtered by workflow
        workflow1_pending = await handler.get_pending_reviews(workflow_id="workflow-1")
        assert len(workflow1_pending) == 1
        assert workflow1_pending[0].workflow_id == "workflow-1"

    @pytest.mark.asyncio
    async def test_get_feedback_history(self) -> None:
        """Test getting feedback history for a workflow."""
        handler = UserReviewHandler()

        # Create and approve multiple requests
        for i in range(3):
            request = await handler.create_review_request(
                workflow_id="workflow-123",
                phase=SDLCPhase.DISCOVERY,
                artifacts=[],
            )
            await handler.submit_feedback(
                request_id=request.id,
                approved=True,
                comments=f"Feedback {i}",
            )

        # Get history
        history = await handler.get_feedback_history("workflow-123")
        assert len(history) == 3

        # Empty history for non-existent workflow
        empty_history = await handler.get_feedback_history("workflow-999")
        assert len(empty_history) == 0

    @pytest.mark.asyncio
    async def test_cancel_review(self) -> None:
        """Test canceling a review request."""
        handler = UserReviewHandler()

        request = await handler.create_review_request(
            workflow_id="workflow-123",
            phase=SDLCPhase.DISCOVERY,
            artifacts=[],
        )

        # Cancel the review
        await handler.cancel_review(request.id)

        # Should be removed from pending
        pending = await handler.get_pending_reviews()
        assert len(pending) == 0

    @pytest.mark.asyncio
    async def test_cancel_invalid_review(self) -> None:
        """Test canceling non-existent review."""
        handler = UserReviewHandler()

        with pytest.raises(ValueError, match="not found"):
            await handler.cancel_review("invalid-id")
