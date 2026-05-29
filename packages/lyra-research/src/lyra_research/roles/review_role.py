"""Review Role — Adversarial review with heterogeneous model.

Uses a different model (GPT-4o-mini) for adversarial review to:
- Catch blind spots from Claude models
- Provide diverse perspective
- Identify issues, gaps, and suggestions
- Approve or reject report
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from lyra_core.context.layered_context import LayeredContextManager

from lyra_research.reporter import ResearchReport
from lyra_research.roles.role_base import Role, RoleResult, RoleStatus


@dataclass
class ReviewIssue:
    """Single issue found during review."""

    severity: str  # "critical", "high", "medium", "low"
    category: str  # "accuracy", "completeness", "clarity", "methodology"
    description: str
    suggestion: str


@dataclass
class ReviewResult(RoleResult):
    """Result from review role."""

    approved: bool = False
    issues: list[ReviewIssue] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    overall_quality_score: float = 0.0


class ReviewRole(Role[ReviewResult]):
    """
    Review Role — Adversarial review with heterogeneous model.

    Model: gpt-4o-mini (different model family for diverse perspective)
    """

    def __init__(self, context_manager: LayeredContextManager) -> None:
        """
        Initialize review role.

        Args:
            context_manager: Layered context manager
        """
        super().__init__("Review", "gpt-4o-mini", context_manager)

    async def execute(self, report: ResearchReport) -> ReviewResult:
        """
        Execute adversarial review of research report.

        Args:
            report: Research report to review

        Returns:
            ReviewResult with issues, suggestions, and approval status
        """
        result = ReviewResult(
            role_name=self.name,
            status=RoleStatus.RUNNING,
            data=None,
        )

        try:
            # Perform multi-dimensional review
            issues: list[ReviewIssue] = []

            # 1. Accuracy review
            accuracy_issues = await self._review_accuracy(report)
            issues.extend(accuracy_issues)

            # 2. Completeness review
            completeness_issues = await self._review_completeness(report)
            issues.extend(completeness_issues)

            # 3. Clarity review
            clarity_issues = await self._review_clarity(report)
            issues.extend(clarity_issues)

            # 4. Methodology review
            methodology_issues = await self._review_methodology(report)
            issues.extend(methodology_issues)

            # Calculate quality score
            critical_count = sum(1 for i in issues if i.severity == "critical")
            high_count = sum(1 for i in issues if i.severity == "high")
            medium_count = sum(1 for i in issues if i.severity == "medium")
            low_count = sum(1 for i in issues if i.severity == "low")

            # Quality score: 1.0 - weighted penalty
            quality_score = 1.0 - (
                critical_count * 0.25 + high_count * 0.15 + medium_count * 0.05 + low_count * 0.01
            )
            quality_score = max(0.0, min(1.0, quality_score))

            # Approval criteria: no critical issues, quality score >= 0.7
            approved = critical_count == 0 and quality_score >= 0.7

            # Generate suggestions
            suggestions = self._generate_suggestions(issues)

            result.approved = approved
            result.issues = issues
            result.suggestions = suggestions
            result.overall_quality_score = quality_score
            result.data = {
                "approved": approved,
                "issues": issues,
                "suggestions": suggestions,
                "quality_score": quality_score,
            }
            result.metadata = {
                "approved": approved,
                "total_issues": len(issues),
                "critical_issues": critical_count,
                "high_issues": high_count,
                "medium_issues": medium_count,
                "low_issues": low_count,
                "quality_score": quality_score,
            }

            return result

        except Exception as e:
            result.status = RoleStatus.FAILED
            result.error = str(e)
            return result

    async def _review_accuracy(self, report: ResearchReport) -> list[ReviewIssue]:
        """Review report accuracy."""
        issues: list[ReviewIssue] = []

        # Check for unsupported claims
        if not report.references_section or len(report.references_section.strip()) == 0:
            issues.append(
                ReviewIssue(
                    severity="high",
                    category="accuracy",
                    description="No references provided",
                    suggestion="Add references for key claims",
                )
            )

        # Check for contradictions
        if report.contested_claims_section and len(report.contested_claims_section) > 500:
            issues.append(
                ReviewIssue(
                    severity="medium",
                    category="accuracy",
                    description="High number of contested claims",
                    suggestion="Resolve or explain contradictions",
                )
            )

        return issues

    async def _review_completeness(self, report: ResearchReport) -> list[ReviewIssue]:
        """Review report completeness."""
        issues: list[ReviewIssue] = []

        # Check for missing sections
        if not report.best_papers_section or len(report.best_papers_section.strip()) == 0:
            issues.append(
                ReviewIssue(
                    severity="critical",
                    category="completeness",
                    description="No papers section in report",
                    suggestion="Add key papers from analysis",
                )
            )

        if not report.taxonomy_section or len(report.taxonomy_section.strip()) == 0:
            issues.append(
                ReviewIssue(
                    severity="medium",
                    category="completeness",
                    description="No taxonomy provided",
                    suggestion="Add taxonomy to organize findings",
                )
            )

        # Check source coverage
        if report.sources_used < 5:
            issues.append(
                ReviewIssue(
                    severity="high",
                    category="completeness",
                    description=f"Low source coverage ({report.sources_used} sources)",
                    suggestion="Analyze more sources for comprehensive coverage",
                )
            )

        return issues

    async def _review_clarity(self, report: ResearchReport) -> list[ReviewIssue]:
        """Review report clarity."""
        issues: list[ReviewIssue] = []

        # Check summary length
        if len(report.executive_summary) < 100:
            issues.append(
                ReviewIssue(
                    severity="medium",
                    category="clarity",
                    description="Executive summary too brief",
                    suggestion="Expand summary to provide better overview",
                )
            )

        if len(report.executive_summary) > 2000:
            issues.append(
                ReviewIssue(
                    severity="low",
                    category="clarity",
                    description="Executive summary too long",
                    suggestion="Condense summary for better readability",
                )
            )

        return issues

    async def _review_methodology(self, report: ResearchReport) -> list[ReviewIssue]:
        """Review research methodology."""
        issues: list[ReviewIssue] = []

        # Check gaps analysis
        if not report.gaps_section or len(report.gaps_section.strip()) == 0:
            issues.append(
                ReviewIssue(
                    severity="medium",
                    category="methodology",
                    description="No gaps analysis performed",
                    suggestion="Add gaps analysis to strengthen findings",
                )
            )

        return issues

    def _generate_suggestions(self, issues: list[ReviewIssue]) -> list[str]:
        """Generate actionable suggestions from issues."""
        suggestions = []

        # Group by severity
        critical = [i for i in issues if i.severity == "critical"]
        high = [i for i in issues if i.severity == "high"]

        if critical:
            suggestions.append(f"CRITICAL: Address {len(critical)} critical issues before approval")

        if high:
            suggestions.append(f"HIGH PRIORITY: Resolve {len(high)} high-priority issues")

        # Add specific suggestions
        for issue in issues:
            if issue.severity in ["critical", "high"]:
                suggestions.append(f"{issue.category.upper()}: {issue.suggestion}")

        return suggestions

    def validate_input(self, report: Any) -> bool:
        """
        Validate input report.

        Args:
            report: Research report

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(report, ResearchReport):
            return False

        if not report.topic or len(report.topic.strip()) == 0:
            return False

        if not report.executive_summary or len(report.executive_summary.strip()) == 0:
            return False

        return True

    def validate_output(self, review_data: Any) -> bool:
        """
        Validate review output.

        Args:
            review_data: Review result data

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(review_data, dict):
            return False

        if "approved" not in review_data:
            return False

        if "issues" not in review_data:
            return False

        if "quality_score" not in review_data:
            return False

        quality_score = review_data["quality_score"]
        if not isinstance(quality_score, (int, float)):
            return False

        if quality_score < 0 or quality_score > 1:
            return False

        return True
