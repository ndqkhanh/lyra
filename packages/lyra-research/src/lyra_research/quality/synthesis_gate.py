"""Synthesis Gate — Quality gate between Synthesis → Review."""
from __future__ import annotations

from typing import Any

from lyra_research.reporter import ResearchReport
from lyra_research.quality.quality_criterion import QualityCriterion
from lyra_research.quality.quality_gate import QualityGate


class SynthesisGate(QualityGate):
    """
    Quality gate between Synthesis → Review.

    Criteria:
    - Report has executive summary (min 100 chars)
    - Report has findings section (min 200 chars)
    - Report used at least 3 sources
    """

    def __init__(self) -> None:
        """Initialize synthesis gate with criteria."""

        def check_executive_summary(report: ResearchReport) -> float:
            """Check executive summary length."""
            if not report or not report.executive_summary:
                return 0.0
            return float(len(report.executive_summary))

        def check_findings_section(report: ResearchReport) -> float:
            """Check findings section length."""
            if not report or not report.best_papers_section:
                return 0.0
            return float(len(report.best_papers_section))

        def check_sources_used(report: ResearchReport) -> float:
            """Check number of sources used."""
            if not report:
                return 0.0
            return float(report.sources_used)

        criteria = [
            QualityCriterion(
                name="executive_summary",
                check_fn=check_executive_summary,
                severity="critical",
                threshold=100.0,
            ),
            QualityCriterion(
                name="findings_section",
                check_fn=check_findings_section,
                severity="high",
                threshold=200.0,
            ),
            QualityCriterion(
                name="sources_used",
                check_fn=check_sources_used,
                severity="medium",
                threshold=3.0,
            ),
        ]

        super().__init__("SynthesisGate", criteria)
