"""Review Gate — Quality gate between Review → Curator."""
from __future__ import annotations

from typing import Any

from lyra_research.roles.review_role import ReviewResult
from lyra_research.quality.quality_criterion import QualityCriterion
from lyra_research.quality.quality_gate import QualityGate


class ReviewGate(QualityGate):
    """
    Quality gate between Review → Curator.

    Criteria:
    - No critical issues found
    - Quality score >= 0.7
    - At most 2 high-severity issues
    """

    def __init__(self) -> None:
        """Initialize review gate with criteria."""

        def check_no_critical(review: ReviewResult) -> float:
            """Check for critical issues (inverted: 0 critical = 1.0 score)."""
            if not review or not review.issues:
                return 1.0
            critical_count = sum(1 for i in review.issues if i.severity == "critical")
            # Return 1.0 if no critical, 0.0 if any critical
            return 1.0 if critical_count == 0 else 0.0

        def check_quality_score(review: ReviewResult) -> float:
            """Check overall quality score."""
            if not review:
                return 0.0
            return review.overall_quality_score

        def check_high_issues(review: ReviewResult) -> float:
            """Check high-severity issues (inverted: fewer is better)."""
            if not review or not review.issues:
                return 1.0
            high_count = sum(1 for i in review.issues if i.severity == "high")
            # Return score based on high issue count (max 2 allowed)
            if high_count <= 2:
                return 1.0
            else:
                # Penalty for each issue over 2
                return max(0.0, 1.0 - (high_count - 2) * 0.2)

        criteria = [
            QualityCriterion(
                name="no_critical_issues",
                check_fn=check_no_critical,
                severity="critical",
                threshold=1.0,
            ),
            QualityCriterion(
                name="quality_score",
                check_fn=check_quality_score,
                severity="high",
                threshold=0.7,
            ),
            QualityCriterion(
                name="limited_high_issues",
                check_fn=check_high_issues,
                severity="medium",
                threshold=1.0,
            ),
        ]

        super().__init__("ReviewGate", criteria)
