"""Analysis Gate — Quality gate between Analysis → Synthesis."""
from __future__ import annotations

from lyra_research.agents.analysis import Analysis
from lyra_research.quality.quality_criterion import QualityCriterion
from lyra_research.quality.quality_gate import QualityGate


class AnalysisGate(QualityGate):
    """
    Quality gate between Analysis → Synthesis.

    Criteria:
    - Minimum 5 analyses completed
    - Average quality score >= 0.5
    - At least 80% of analyses have quality scores
    """

    def __init__(self) -> None:
        """Initialize analysis gate with criteria."""

        def check_min_analyses(analyses: list[Analysis]) -> float:
            """Check minimum number of analyses."""
            return float(len(analyses))

        def check_avg_quality(analyses: list[Analysis]) -> float:
            """Check average quality score."""
            if not analyses:
                return 0.0
            quality_scores = [a.quality_score for a in analyses if a.quality_score > 0]
            if not quality_scores:
                return 0.0
            return sum(quality_scores) / len(quality_scores)

        def check_quality_coverage(analyses: list[Analysis]) -> float:
            """Check percentage of analyses with quality scores."""
            if not analyses:
                return 0.0
            with_scores = sum(1 for a in analyses if a.quality_score > 0)
            return with_scores / len(analyses)

        criteria = [
            QualityCriterion(
                name="min_analyses",
                check_fn=check_min_analyses,
                severity="critical",
                threshold=5.0,
            ),
            QualityCriterion(
                name="avg_quality",
                check_fn=check_avg_quality,
                severity="high",
                threshold=0.5,
            ),
            QualityCriterion(
                name="quality_coverage",
                check_fn=check_quality_coverage,
                severity="medium",
                threshold=0.8,
            ),
        ]

        super().__init__("AnalysisGate", criteria)
