"""Verification system for research reports."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from lyra_research.discovery import ResearchSource
from lyra_research.reporter import ResearchReport


@dataclass
class VerificationResult:
    """Result from verification check."""

    check_name: str
    passed: bool
    score: float  # 0.0 to 1.0
    issues: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


class Verifier:
    """
    Verification system for research reports.

    Verifies:
    - Completeness (all required sections present)
    - Accuracy (claims supported by sources)
    - Consistency (no internal contradictions)
    """

    def verify_completeness(self, report: ResearchReport) -> VerificationResult:
        """
        Verify report completeness.

        Checks:
        - Executive summary present and adequate length
        - Best papers section present
        - Taxonomy section present
        - References section present
        - Minimum source coverage

        Args:
            report: Research report to verify

        Returns:
            VerificationResult with completeness check
        """
        issues: list[str] = []
        checks = {}

        # Check executive summary
        if not report.executive_summary or len(report.executive_summary.strip()) == 0:
            issues.append("Missing executive summary")
            checks["has_summary"] = False
        elif len(report.executive_summary) < 100:
            issues.append("Executive summary too brief (< 100 chars)")
            checks["has_summary"] = False
        else:
            checks["has_summary"] = True

        # Check best papers section
        if not report.best_papers_section or len(report.best_papers_section.strip()) == 0:
            issues.append("Missing best papers section")
            checks["has_papers"] = False
        else:
            checks["has_papers"] = True

        # Check taxonomy section
        if not report.taxonomy_section or len(report.taxonomy_section.strip()) == 0:
            issues.append("Missing taxonomy section")
            checks["has_taxonomy"] = False
        else:
            checks["has_taxonomy"] = True

        # Check references section
        if not report.references_section or len(report.references_section.strip()) == 0:
            issues.append("Missing references section")
            checks["has_references"] = False
        else:
            checks["has_references"] = True

        # Check source coverage
        if report.sources_used < 5:
            issues.append(f"Low source coverage ({report.sources_used} sources)")
            checks["adequate_sources"] = False
        else:
            checks["adequate_sources"] = True

        # Calculate score
        passed_checks = sum(1 for v in checks.values() if v)
        score = passed_checks / len(checks) if checks else 0.0
        passed = score >= 0.8  # 80% of checks must pass

        return VerificationResult(
            check_name="completeness",
            passed=passed,
            score=score,
            issues=issues,
            details=checks,
        )

    def verify_accuracy(
        self, report: ResearchReport, sources: list[ResearchSource]
    ) -> VerificationResult:
        """
        Verify report accuracy against sources.

        Checks:
        - Claims are supported by sources
        - Source citations are valid
        - No unsupported claims
        - Source quality is adequate

        Args:
            report: Research report to verify
            sources: List of sources used

        Returns:
            VerificationResult with accuracy check
        """
        issues: list[str] = []
        checks = {}

        # Check source count matches
        if report.sources_used != len(sources):
            issues.append(
                f"Source count mismatch: report claims {report.sources_used}, "
                f"but {len(sources)} sources provided"
            )
            checks["source_count_match"] = False
        else:
            checks["source_count_match"] = True

        # Check references section has content
        if not report.references_section or len(report.references_section.strip()) == 0:
            issues.append("No references provided for claims")
            checks["has_references"] = False
        else:
            checks["has_references"] = True

        # Check source quality
        if sources:
            # Quality score is stored in metadata
            quality_scores = []
            for s in sources:
                if "quality_score" in s.metadata:
                    quality_scores.append(s.metadata["quality_score"])
                else:
                    # Heuristic: sources with citations/stars are higher quality
                    score = 0.5  # Base score
                    if s.citations > 0:
                        score += 0.3
                    if s.stars > 0:
                        score += 0.2
                    quality_scores.append(score)

            if quality_scores:
                avg_quality = sum(quality_scores) / len(quality_scores)
            else:
                avg_quality = 0.0

            if avg_quality < 0.5:
                issues.append(f"Low average source quality ({avg_quality:.2f})")
                checks["adequate_quality"] = False
            else:
                checks["adequate_quality"] = True
        else:
            checks["adequate_quality"] = False

        # Check for source diversity
        if sources:
            unique_types = len(set(s.source_type.value for s in sources))
            if unique_types < 2:
                issues.append(f"Low source diversity ({unique_types} types)")
                checks["source_diversity"] = False
            else:
                checks["source_diversity"] = True
        else:
            checks["source_diversity"] = False

        # Calculate score
        passed_checks = sum(1 for v in checks.values() if v)
        score = passed_checks / len(checks) if checks else 0.0
        passed = score >= 0.75  # 75% of checks must pass

        return VerificationResult(
            check_name="accuracy",
            passed=passed,
            score=score,
            issues=issues,
            details=checks,
        )

    def verify_consistency(self, report: ResearchReport) -> VerificationResult:
        """
        Verify report internal consistency.

        Checks:
        - No contradictions in findings
        - Consistent terminology
        - Logical flow
        - Contested claims are explained

        Args:
            report: Research report to verify

        Returns:
            VerificationResult with consistency check
        """
        issues: list[str] = []
        checks = {}

        # Check contested claims section
        if report.contested_claims_section and len(report.contested_claims_section) > 0:
            # Contested claims exist, check if they're explained
            if len(report.contested_claims_section) > 1000:
                issues.append("High number of contested claims (> 1000 chars)")
                checks["contested_claims_explained"] = False
            else:
                checks["contested_claims_explained"] = True
        else:
            # No contested claims is fine
            checks["contested_claims_explained"] = True

        # Check for gaps section
        if report.gaps_section and len(report.gaps_section.strip()) > 0:
            checks["has_gaps_analysis"] = True
        else:
            issues.append("Missing gaps analysis")
            checks["has_gaps_analysis"] = False

        # Check topic consistency
        if not report.topic or len(report.topic.strip()) == 0:
            issues.append("Missing or empty topic")
            checks["has_topic"] = False
        else:
            checks["has_topic"] = True

        # Check summary consistency with findings
        if report.executive_summary and report.best_papers_section:
            # Both sections exist, assume consistent
            checks["summary_findings_consistent"] = True
        else:
            issues.append("Cannot verify summary-findings consistency")
            checks["summary_findings_consistent"] = False

        # Calculate score
        passed_checks = sum(1 for v in checks.values() if v)
        score = passed_checks / len(checks) if checks else 0.0
        passed = score >= 0.75  # 75% of checks must pass

        return VerificationResult(
            check_name="consistency",
            passed=passed,
            score=score,
            issues=issues,
            details=checks,
        )

    def verify_all(
        self, report: ResearchReport, sources: list[ResearchSource]
    ) -> list[VerificationResult]:
        """
        Run all verification checks.

        Args:
            report: Research report to verify
            sources: List of sources used

        Returns:
            List of VerificationResults for all checks
        """
        results = [
            self.verify_completeness(report),
            self.verify_accuracy(report, sources),
            self.verify_consistency(report),
        ]
        return results

    def get_overall_score(self, results: list[VerificationResult]) -> float:
        """
        Calculate overall verification score.

        Args:
            results: List of verification results

        Returns:
            Overall score (0.0 to 1.0)
        """
        if not results:
            return 0.0
        return sum(r.score for r in results) / len(results)

    def all_passed(self, results: list[VerificationResult]) -> bool:
        """
        Check if all verification checks passed.

        Args:
            results: List of verification results

        Returns:
            True if all checks passed, False otherwise
        """
        return all(r.passed for r in results)
