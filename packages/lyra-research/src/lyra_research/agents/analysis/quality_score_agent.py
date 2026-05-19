"""Quality scoring agent for ranking source quality."""
from __future__ import annotations

from typing import List

from lyra_research.agents.analysis.analysis_base import Analysis, AnalysisAgent
from lyra_research.discovery import ResearchSource
from lyra_research.sources import SourceQualityScorer


class QualityScoreAgent(AnalysisAgent):
    """Specialized agent for scoring source quality."""

    def __init__(self, model: str = "claude-sonnet-4-6") -> None:
        """Initialize quality scoring agent."""
        super().__init__(analysis_type="quality", model=model)
        self.scorer = SourceQualityScorer()

    async def analyze(self, source: ResearchSource) -> Analysis:
        """
        Score quality of a single source.

        Args:
            source: Research source

        Returns:
            Quality analysis
        """
        # Use a generic query for quality scoring (no specific query context)
        query = "research"

        # Calculate quality score
        quality_score = self.scorer.score(source, query)

        # Generate quality insights
        findings = self._generate_quality_insights(source, quality_score)

        analysis = Analysis(
            source_id=source.id,
            analysis_type=self.analysis_type,
            findings=findings,
            metadata={
                "quality_score": quality_score,
                "citations": source.citations,
                "stars": source.stars,
                "venue": source.metadata.get("venue", ""),
            },
            confidence=quality_score,
            quality_score=quality_score,
        )

        return analysis

    def _generate_quality_insights(
        self, source: ResearchSource, quality_score: float
    ) -> List[str]:
        """
        Generate quality insights based on score.

        Args:
            source: Research source
            quality_score: Calculated quality score (0.0-1.0)

        Returns:
            List of quality insights
        """
        findings = []

        # Overall quality tier
        if quality_score >= 0.8:
            findings.append(f"Excellent quality (score: {quality_score:.2f})")
        elif quality_score >= 0.6:
            findings.append(f"Good quality (score: {quality_score:.2f})")
        elif quality_score >= 0.4:
            findings.append(f"Moderate quality (score: {quality_score:.2f})")
        else:
            findings.append(f"Lower quality (score: {quality_score:.2f})")

        # Component breakdowns
        if source.citations > 100:
            findings.append("Strong citation impact")

        if source.published_date:
            from datetime import datetime
            age_days = (datetime.now() - source.published_date.replace(tzinfo=None)).days
            if age_days < 730:  # 2 years
                findings.append("Recent publication")
            elif age_days > 3650:  # 10 years
                findings.append("Older publication")

        venue = source.metadata.get("venue", "")
        if venue and any(
            top in venue.upper()
            for top in ["NEURIPS", "ICML", "ICLR", "ACL", "CVPR", "SOSP"]
        ):
            findings.append(f"Top-tier venue: {venue}")

        return findings
