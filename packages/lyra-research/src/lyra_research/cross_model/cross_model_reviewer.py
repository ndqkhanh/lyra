"""
Cross-Model Adversarial Review

Implements heterogeneous model verification:
- Claude Opus as executor
- GPT-4o as reviewer
- Disagreement resolution protocol
- Selective review (confidence <0.8)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ModelType(Enum):
    """Model types"""

    CLAUDE_OPUS = "claude_opus"
    GPT4O = "gpt4o"


class ReviewDecision(Enum):
    """Review decisions"""

    APPROVE = "approve"
    REJECT = "reject"
    REVISE = "revise"
    ESCALATE = "escalate"


@dataclass
class ExecutionResult:
    """Result from executor model"""

    content: str
    confidence: float  # 0.0 to 1.0
    model: ModelType
    metadata: dict[str, Any]


@dataclass
class ReviewResult:
    """Result from reviewer model"""

    decision: ReviewDecision
    confidence: float
    issues: list[str]
    suggestions: list[str]
    model: ModelType


@dataclass
class DisagreementResolution:
    """Resolution of disagreement between models"""

    final_decision: ReviewDecision
    reasoning: str
    executor_confidence: float
    reviewer_confidence: float
    resolution_method: str


class CrossModelReviewer:
    """
    Heterogeneous model verification with disagreement resolution

    Claude Opus executes, GPT-4o reviews, disagreements are resolved.
    """

    def __init__(self, review_threshold: float = 0.8):
        """
        Initialize cross-model reviewer

        Args:
            review_threshold: Confidence threshold below which review is triggered
        """
        self.review_threshold = review_threshold
        self.executor_model = ModelType.CLAUDE_OPUS
        self.reviewer_model = ModelType.GPT4O

    def execute_and_review(self, task: dict[str, Any]) -> dict[str, Any]:
        """
        Execute task with Claude Opus and review with GPT-4o

        Args:
            task: Research task to execute

        Returns:
            Final result with review
        """
        # Step 1: Execute with Claude Opus
        execution = self.execute_task(task)

        # Step 2: Check if review is needed
        if execution.confidence >= self.review_threshold:
            # High confidence - skip review
            return {
                "content": execution.content,
                "confidence": execution.confidence,
                "reviewed": False,
                "executor": execution.model.value,
            }

        # Step 3: Review with GPT-4o
        review = self.review_execution(execution, task)

        # Step 4: Resolve disagreements if any
        if self.has_disagreement(execution, review):
            resolution = self.resolve_disagreement(execution, review, task)
            return {
                "content": execution.content,
                "confidence": execution.confidence,
                "reviewed": True,
                "review_decision": resolution.final_decision.value,
                "resolution": resolution.reasoning,
                "executor": execution.model.value,
                "reviewer": review.model.value,
            }

        # No disagreement - apply review decision
        return {
            "content": execution.content,
            "confidence": execution.confidence,
            "reviewed": True,
            "review_decision": review.decision.value,
            "issues": review.issues,
            "suggestions": review.suggestions,
            "executor": execution.model.value,
            "reviewer": review.model.value,
        }

    def execute_task(self, task: dict[str, Any]) -> ExecutionResult:
        """
        Execute task with Claude Opus

        Args:
            task: Task to execute

        Returns:
            ExecutionResult
        """
        # In production, would call actual Claude Opus API
        # For now, simulate execution
        content = f"Executed: {task.get('description', 'task')}"
        confidence = task.get("expected_confidence", 0.7)

        return ExecutionResult(
            content=content,
            confidence=confidence,
            model=ModelType.CLAUDE_OPUS,
            metadata={"task_id": task.get("id", "unknown")},
        )

    def review_execution(self, execution: ExecutionResult, task: dict[str, Any]) -> ReviewResult:
        """
        Review execution with GPT-4o

        Args:
            execution: Execution result to review
            task: Original task

        Returns:
            ReviewResult
        """
        # In production, would call actual GPT-4o API
        # For now, simulate review
        issues = []
        suggestions = []

        # Check for common issues
        if len(execution.content) < 50:
            issues.append("Content too short")
            suggestions.append("Provide more detail")

        if execution.confidence < 0.5:
            issues.append("Low confidence execution")
            suggestions.append("Revise with more evidence")

        # Determine decision
        if len(issues) == 0:
            decision = ReviewDecision.APPROVE
            confidence = 0.9
        elif len(issues) == 1:
            decision = ReviewDecision.REVISE
            confidence = 0.7
        else:
            decision = ReviewDecision.REJECT
            confidence = 0.8

        return ReviewResult(
            decision=decision,
            confidence=confidence,
            issues=issues,
            suggestions=suggestions,
            model=ModelType.GPT4O,
        )

    def has_disagreement(self, execution: ExecutionResult, review: ReviewResult) -> bool:
        """
        Check if there's disagreement between executor and reviewer

        Args:
            execution: Execution result
            review: Review result

        Returns:
            True if disagreement exists
        """
        # Disagreement if:
        # 1. Executor has high confidence but reviewer rejects
        # 2. Executor has low confidence but reviewer approves
        # 3. Both have medium confidence but different decisions

        if execution.confidence > 0.7 and review.decision == ReviewDecision.REJECT:
            return True

        if execution.confidence < 0.5 and review.decision == ReviewDecision.APPROVE:
            return True

        return False

    def resolve_disagreement(
        self, execution: ExecutionResult, review: ReviewResult, task: dict[str, Any]
    ) -> DisagreementResolution:
        """
        Resolve disagreement between models

        Args:
            execution: Execution result
            review: Review result
            task: Original task

        Returns:
            DisagreementResolution
        """
        # Resolution strategy:
        # 1. If reviewer confidence > executor confidence: follow reviewer
        # 2. If executor confidence > reviewer confidence: follow executor
        # 3. If equal: escalate for human review

        if review.confidence > execution.confidence:
            return DisagreementResolution(
                final_decision=review.decision,
                reasoning=(
                    f"Reviewer confidence ({review.confidence:.2f}) exceeds executor confidence ("
                    f"{execution.confidence:.2f})"
                ),
                executor_confidence=execution.confidence,
                reviewer_confidence=review.confidence,
                resolution_method="reviewer_priority",
            )
        elif execution.confidence > review.confidence:
            return DisagreementResolution(
                final_decision=ReviewDecision.APPROVE,
                reasoning=(
                    f"Executor confidence ({execution.confidence:.2f}"
                    f") exceeds reviewer confidence ({review.confidence:.2f})"
                ),
                executor_confidence=execution.confidence,
                reviewer_confidence=review.confidence,
                resolution_method="executor_priority",
            )
        else:
            return DisagreementResolution(
                final_decision=ReviewDecision.ESCALATE,
                reasoning="Equal confidence - escalating to human review",
                executor_confidence=execution.confidence,
                reviewer_confidence=review.confidence,
                resolution_method="human_escalation",
            )

    def should_review(self, confidence: float) -> bool:
        """
        Check if execution should be reviewed

        Args:
            confidence: Execution confidence

        Returns:
            True if review is needed
        """
        return confidence < self.review_threshold
