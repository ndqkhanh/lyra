"""UX Researcher Skill — user research methodology and insights validation.

Analyzes UX research for:
- Research methodology rigor
- Sample size and participant diversity
- Data collection methods
- Analysis framework
- Actionable insights quality
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ResearchSeverity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ResearchCategory(StrEnum):
    METHODOLOGY = "methodology"
    SAMPLE = "sample"
    DATA_QUALITY = "data_quality"
    ANALYSIS = "analysis"
    INSIGHTS = "insights"


@dataclass(frozen=True)
class ResearchIssue:
    category: ResearchCategory
    severity: ResearchSeverity
    message: str
    suggestion: str


class UXResearcherSkill:
    """Validates UX research methodology and insights quality."""

    def __init__(self) -> None:
        self._issues: list[ResearchIssue] = []

    def run(self, input_data: dict) -> dict:
        """Run UX research validation.

        Args:
            input_data: Dictionary with keys:
                - research_type: Type of research (usability, interview, survey, etc.)
                - sample_size: Number of participants
                - methodology: Research methodology description
                - findings: List of research findings
                - demographics: Participant demographics

        Returns:
            Dictionary with validation report data.
        """
        research_type = input_data.get("research_type", "unknown")
        sample_size = input_data.get("sample_size", 0)
        methodology = input_data.get("methodology", "")
        findings = input_data.get("findings", [])
        demographics = input_data.get("demographics", {})

        self._issues.clear()

        self._check_sample_size(research_type, sample_size)
        self._check_methodology(research_type, methodology)
        self._check_participant_diversity(demographics, sample_size)
        self._check_data_quality(input_data)
        self._check_findings_quality(findings)
        self._check_bias_mitigation(input_data)

        score = self._compute_score()

        return {
            "research_type": research_type,
            "sample_size": sample_size,
            "issues": [i.__dict__ for i in self._issues],
            "score": score,
            "total_issues": len(self._issues),
            "validity": self._compute_validity(score),
        }

    def _check_sample_size(self, research_type: str, sample_size: int) -> None:
        """Check if sample size is appropriate for research type."""
        min_samples = {
            "usability": 5,
            "interview": 8,
            "survey": 100,
            "card_sorting": 15,
            "tree_testing": 30,
            "a_b_test": 100,
        }

        min_required = min_samples.get(research_type, 5)

        if sample_size < min_required:
            self._issues.append(
                ResearchIssue(
                    category=ResearchCategory.SAMPLE,
                    severity=ResearchSeverity.CRITICAL,
                    message=f"Sample size ({sample_size}) below minimum for {research_type} (need {min_required})",
                    suggestion=f"Recruit at least {min_required} participants for valid results",
                )
            )
        elif sample_size < min_required * 1.5:
            self._issues.append(
                ResearchIssue(
                    category=ResearchCategory.SAMPLE,
                    severity=ResearchSeverity.MEDIUM,
                    message=f"Sample size ({sample_size}) is minimal for {research_type}",
                    suggestion=f"Consider recruiting {int(min_required * 2)} participants for stronger insights",
                )
            )

    def _check_methodology(self, research_type: str, methodology: str) -> None:
        """Check research methodology completeness."""
        if not methodology:
            self._issues.append(
                ResearchIssue(
                    category=ResearchCategory.METHODOLOGY,
                    severity=ResearchSeverity.CRITICAL,
                    message="No research methodology documented",
                    suggestion="Document research protocol, tasks, and procedures",
                )
            )
            return

        # Check for key methodology components
        required_components = {
            "usability": ["tasks", "success criteria", "metrics"],
            "interview": ["script", "questions", "duration"],
            "survey": ["questions", "scale", "validation"],
        }

        components = required_components.get(research_type, [])
        missing = [c for c in components if c.lower() not in methodology.lower()]

        if missing:
            self._issues.append(
                ResearchIssue(
                    category=ResearchCategory.METHODOLOGY,
                    severity=ResearchSeverity.HIGH,
                    message=f"Methodology missing key components: {', '.join(missing)}",
                    suggestion=f"Document {', '.join(missing)} in research protocol",
                )
            )

        # Check for pilot testing
        if "pilot" not in methodology.lower() and research_type in ("usability", "survey"):
            self._issues.append(
                ResearchIssue(
                    category=ResearchCategory.METHODOLOGY,
                    severity=ResearchSeverity.MEDIUM,
                    message="No pilot testing mentioned",
                    suggestion="Conduct pilot test to validate research protocol",
                )
            )

    def _check_participant_diversity(self, demographics: dict, sample_size: int) -> None:
        """Check participant diversity and representation."""
        if not demographics:
            self._issues.append(
                ResearchIssue(
                    category=ResearchCategory.SAMPLE,
                    severity=ResearchSeverity.HIGH,
                    message="No demographic data collected",
                    suggestion="Collect demographics to ensure representative sample",
                )
            )
            return

        # Check age diversity
        age_groups = demographics.get("age_groups", {})
        if age_groups and len(age_groups) < 3:
            self._issues.append(
                ResearchIssue(
                    category=ResearchCategory.SAMPLE,
                    severity=ResearchSeverity.MEDIUM,
                    message=f"Limited age diversity ({len(age_groups)} groups)",
                    suggestion="Include participants from at least 3 age groups",
                )
            )

        # Check gender balance
        gender_dist = demographics.get("gender_distribution", {})
        if gender_dist:
            max_ratio = max(gender_dist.values()) / sample_size if sample_size > 0 else 0
            if max_ratio > 0.8:
                self._issues.append(
                    ResearchIssue(
                        category=ResearchCategory.SAMPLE,
                        severity=ResearchSeverity.MEDIUM,
                        message=f"Gender imbalance ({max_ratio:.0%} of one gender)",
                        suggestion="Aim for more balanced gender representation",
                    )
                )

        # Check experience level diversity
        experience = demographics.get("experience_levels", {})
        if experience and len(experience) < 2:
            self._issues.append(
                ResearchIssue(
                    category=ResearchCategory.SAMPLE,
                    severity=ResearchSeverity.LOW,
                    message="Limited experience level diversity",
                    suggestion="Include both novice and expert users",
                )
            )

    def _check_data_quality(self, input_data: dict) -> None:
        """Check data collection quality."""
        # Check for recording
        has_recording = input_data.get("has_recording", False)
        research_type = input_data.get("research_type", "")

        if not has_recording and research_type in ("usability", "interview"):
            self._issues.append(
                ResearchIssue(
                    category=ResearchCategory.DATA_QUALITY,
                    severity=ResearchSeverity.HIGH,
                    message="No session recording mentioned",
                    suggestion="Record sessions for accurate analysis and quotes",
                )
            )

        # Check for consent
        has_consent = input_data.get("has_consent", False)
        if not has_consent:
            self._issues.append(
                ResearchIssue(
                    category=ResearchCategory.METHODOLOGY,
                    severity=ResearchSeverity.CRITICAL,
                    message="No informed consent documented",
                    suggestion="Obtain informed consent from all participants",
                )
            )

        # Check for compensation
        has_compensation = input_data.get("has_compensation", False)
        if not has_compensation and input_data.get("sample_size", 0) > 5:
            self._issues.append(
                ResearchIssue(
                    category=ResearchCategory.METHODOLOGY,
                    severity=ResearchSeverity.LOW,
                    message="No participant compensation mentioned",
                    suggestion="Consider compensating participants for their time",
                )
            )

    def _check_findings_quality(self, findings: list) -> None:
        """Check quality and actionability of findings."""
        if not findings:
            self._issues.append(
                ResearchIssue(
                    category=ResearchCategory.INSIGHTS,
                    severity=ResearchSeverity.CRITICAL,
                    message="No findings documented",
                    suggestion="Document key findings from research",
                )
            )
            return

        # Check for evidence backing
        findings_with_evidence = sum(1 for f in findings if f.get("has_evidence"))
        if findings_with_evidence < len(findings) * 0.8:
            self._issues.append(
                ResearchIssue(
                    category=ResearchCategory.INSIGHTS,
                    severity=ResearchSeverity.HIGH,
                    message=f"Only {findings_with_evidence}/{len(findings)} findings have evidence",
                    suggestion="Support all findings with quotes, metrics, or observations",
                )
            )

        # Check for actionable recommendations
        findings_with_recommendations = sum(1 for f in findings if f.get("has_recommendation"))
        if findings_with_recommendations < len(findings) * 0.5:
            self._issues.append(
                ResearchIssue(
                    category=ResearchCategory.INSIGHTS,
                    severity=ResearchSeverity.MEDIUM,
                    message=f"Only {findings_with_recommendations}/{len(findings)} findings have recommendations",
                    suggestion="Provide actionable recommendations for each finding",
                )
            )

        # Check for severity/priority
        findings_with_priority = sum(1 for f in findings if f.get("priority"))
        if findings_with_priority < len(findings) * 0.7:
            self._issues.append(
                ResearchIssue(
                    category=ResearchCategory.INSIGHTS,
                    severity=ResearchSeverity.LOW,
                    message="Not all findings prioritized",
                    suggestion="Assign priority levels to help teams focus on critical issues",
                )
            )

    def _check_bias_mitigation(self, input_data: dict) -> None:
        """Check for bias mitigation strategies."""
        methodology = input_data.get("methodology", "")

        # Check for leading questions
        if "leading" not in methodology.lower() and "neutral" not in methodology.lower():
            self._issues.append(
                ResearchIssue(
                    category=ResearchCategory.METHODOLOGY,
                    severity=ResearchSeverity.MEDIUM,
                    message="No mention of avoiding leading questions",
                    suggestion="Use neutral, non-leading questions to reduce bias",
                )
            )

        # Check for randomization
        research_type = input_data.get("research_type", "")
        if research_type in ("usability", "a_b_test") and "random" not in methodology.lower():
            self._issues.append(
                ResearchIssue(
                    category=ResearchCategory.METHODOLOGY,
                    severity=ResearchSeverity.MEDIUM,
                    message="No task/condition randomization mentioned",
                    suggestion="Randomize task order to reduce learning effects",
                )
            )

        # Check for observer bias
        has_multiple_observers = input_data.get("has_multiple_observers", False)
        if not has_multiple_observers and research_type in ("usability", "interview"):
            self._issues.append(
                ResearchIssue(
                    category=ResearchCategory.METHODOLOGY,
                    severity=ResearchSeverity.LOW,
                    message="Single observer may introduce bias",
                    suggestion="Use multiple observers or inter-rater reliability checks",
                )
            )

    def _compute_score(self) -> int:
        """Compute overall research quality score (0-100)."""
        return max(
            0,
            100
            - len([i for i in self._issues if i.severity == ResearchSeverity.CRITICAL]) * 25
            - len([i for i in self._issues if i.severity == ResearchSeverity.HIGH]) * 15
            - len([i for i in self._issues if i.severity == ResearchSeverity.MEDIUM]) * 8
            - len([i for i in self._issues if i.severity == ResearchSeverity.LOW]) * 3,
        )

    def _compute_validity(self, score: int) -> str:
        """Compute research validity level."""
        if score >= 90:
            return "high"
        if score >= 75:
            return "moderate"
        if score >= 60:
            return "low"
        return "questionable"
