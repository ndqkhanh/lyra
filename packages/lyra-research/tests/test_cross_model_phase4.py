"""
Tests for Cross-Model Adversarial Review (Phase 4)

Tests heterogeneous model verification, disagreement resolution,
and selective review.
"""

import pytest
from lyra_research.cross_model.cross_model_reviewer import (
    CrossModelReviewer,
    ExecutionResult,
    ModelType,
    ReviewDecision,
    ReviewResult,
)


class TestCrossModelReviewer:
    """Test cross-model adversarial review"""

    def test_high_confidence_skips_review(self):
        """Test that high confidence execution skips review"""
        reviewer = CrossModelReviewer(review_threshold=0.8)

        task = {
            "description": "Test task",
            "expected_confidence": 0.9
        }

        result = reviewer.execute_and_review(task)
        assert not result["reviewed"]
        assert result["confidence"] >= 0.8

    def test_low_confidence_triggers_review(self):
        """Test that low confidence execution triggers review"""
        reviewer = CrossModelReviewer(review_threshold=0.8)

        task = {
            "description": "Test task",
            "expected_confidence": 0.6
        }

        result = reviewer.execute_and_review(task)
        assert result["reviewed"]
        assert result["confidence"] < 0.8

    def test_execute_task(self):
        """Test task execution"""
        reviewer = CrossModelReviewer()

        task = {"description": "Test task", "id": "task1"}

        execution = reviewer.execute_task(task)
        assert execution.model == ModelType.CLAUDE_OPUS
        assert "Executed" in execution.content
        assert 0.0 <= execution.confidence <= 1.0

    def test_review_execution_approve(self):
        """Test review that approves execution"""
        reviewer = CrossModelReviewer()

        execution = ExecutionResult(
            content="This is a detailed and comprehensive response with sufficient content.",
            confidence=0.7,
            model=ModelType.CLAUDE_OPUS,
            metadata={}
        )

        task = {"description": "Test task"}

        review = reviewer.review_execution(execution, task)
        assert review.model == ModelType.GPT4O
        assert review.decision == ReviewDecision.APPROVE
        assert len(review.issues) == 0

    def test_review_execution_reject(self):
        """Test review that rejects execution"""
        reviewer = CrossModelReviewer()

        execution = ExecutionResult(
            content="Short",
            confidence=0.3,
            model=ModelType.CLAUDE_OPUS,
            metadata={}
        )

        task = {"description": "Test task"}

        review = reviewer.review_execution(execution, task)
        assert review.decision == ReviewDecision.REJECT
        assert len(review.issues) > 0

    def test_has_disagreement_high_conf_rejected(self):
        """Test disagreement detection: high confidence but rejected"""
        reviewer = CrossModelReviewer()

        execution = ExecutionResult(
            content="Good content",
            confidence=0.9,
            model=ModelType.CLAUDE_OPUS,
            metadata={}
        )

        review = ReviewResult(
            decision=ReviewDecision.REJECT,
            confidence=0.8,
            issues=["Issue found"],
            suggestions=[],
            model=ModelType.GPT4O
        )

        assert reviewer.has_disagreement(execution, review)

    def test_has_disagreement_low_conf_approved(self):
        """Test disagreement detection: low confidence but approved"""
        reviewer = CrossModelReviewer()

        execution = ExecutionResult(
            content="Content",
            confidence=0.3,
            model=ModelType.CLAUDE_OPUS,
            metadata={}
        )

        review = ReviewResult(
            decision=ReviewDecision.APPROVE,
            confidence=0.9,
            issues=[],
            suggestions=[],
            model=ModelType.GPT4O
        )

        assert reviewer.has_disagreement(execution, review)

    def test_resolve_disagreement_reviewer_priority(self):
        """Test disagreement resolution: reviewer has higher confidence"""
        reviewer = CrossModelReviewer()

        execution = ExecutionResult(
            content="Content",
            confidence=0.6,
            model=ModelType.CLAUDE_OPUS,
            metadata={}
        )

        review = ReviewResult(
            decision=ReviewDecision.REJECT,
            confidence=0.9,
            issues=["Critical issue"],
            suggestions=[],
            model=ModelType.GPT4O
        )

        task = {"description": "Test"}

        resolution = reviewer.resolve_disagreement(execution, review, task)
        assert resolution.final_decision == ReviewDecision.REJECT
        assert resolution.resolution_method == "reviewer_priority"
        assert resolution.reviewer_confidence > resolution.executor_confidence

    def test_resolve_disagreement_executor_priority(self):
        """Test disagreement resolution: executor has higher confidence"""
        reviewer = CrossModelReviewer()

        execution = ExecutionResult(
            content="Content",
            confidence=0.9,
            model=ModelType.CLAUDE_OPUS,
            metadata={}
        )

        review = ReviewResult(
            decision=ReviewDecision.REJECT,
            confidence=0.6,
            issues=["Minor issue"],
            suggestions=[],
            model=ModelType.GPT4O
        )

        task = {"description": "Test"}

        resolution = reviewer.resolve_disagreement(execution, review, task)
        assert resolution.final_decision == ReviewDecision.APPROVE
        assert resolution.resolution_method == "executor_priority"
        assert resolution.executor_confidence > resolution.reviewer_confidence

    def test_resolve_disagreement_escalate(self):
        """Test disagreement resolution: equal confidence escalates"""
        reviewer = CrossModelReviewer()

        execution = ExecutionResult(
            content="Content",
            confidence=0.7,
            model=ModelType.CLAUDE_OPUS,
            metadata={}
        )

        review = ReviewResult(
            decision=ReviewDecision.REJECT,
            confidence=0.7,
            issues=["Issue"],
            suggestions=[],
            model=ModelType.GPT4O
        )

        task = {"description": "Test"}

        resolution = reviewer.resolve_disagreement(execution, review, task)
        assert resolution.final_decision == ReviewDecision.ESCALATE
        assert resolution.resolution_method == "human_escalation"

    def test_should_review(self):
        """Test review threshold check"""
        reviewer = CrossModelReviewer(review_threshold=0.8)

        assert reviewer.should_review(0.7)  # Below threshold
        assert reviewer.should_review(0.5)  # Below threshold
        assert not reviewer.should_review(0.9)  # Above threshold
        assert not reviewer.should_review(0.8)  # At threshold


class TestCrossModelIntegration:
    """Test integration of cross-model review"""

    def test_full_review_workflow_with_approval(self):
        """Test complete workflow with approval"""
        reviewer = CrossModelReviewer(review_threshold=0.8)

        task = {
            "description": "Comprehensive research task with detailed requirements",
            "expected_confidence": 0.7,
            "id": "task1"
        }

        result = reviewer.execute_and_review(task)

        # Should be reviewed (confidence < 0.8)
        assert result["reviewed"]
        assert result["executor"] == ModelType.CLAUDE_OPUS.value
        assert result["reviewer"] == ModelType.GPT4O.value

    def test_full_review_workflow_with_rejection(self):
        """Test complete workflow with rejection"""
        reviewer = CrossModelReviewer(review_threshold=0.8)

        task = {
            "description": "Task",
            "expected_confidence": 0.3,
            "id": "task2"
        }

        result = reviewer.execute_and_review(task)

        # Should be reviewed and likely rejected
        assert result["reviewed"]
        assert result["review_decision"] in [
            ReviewDecision.REJECT.value,
            ReviewDecision.REVISE.value
        ]

    def test_selective_review_only_low_confidence(self):
        """Test that only low confidence outputs are reviewed"""
        reviewer = CrossModelReviewer(review_threshold=0.8)

        # High confidence task
        high_conf_task = {
            "description": "High confidence task",
            "expected_confidence": 0.95
        }

        high_result = reviewer.execute_and_review(high_conf_task)
        assert not high_result["reviewed"]

        # Low confidence task
        low_conf_task = {
            "description": "Low confidence task",
            "expected_confidence": 0.6
        }

        low_result = reviewer.execute_and_review(low_conf_task)
        assert low_result["reviewed"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
