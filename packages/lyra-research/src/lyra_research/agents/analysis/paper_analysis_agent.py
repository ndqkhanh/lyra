"""Paper analysis agent for extracting findings from papers."""
from __future__ import annotations

from typing import List

from lyra_research.agents.analysis.analysis_base import Analysis, AnalysisAgent
from lyra_research.discovery import ResearchSource, SourceType


class PaperAnalysisAgent(AnalysisAgent):
    """Specialized agent for analyzing academic papers."""

    def __init__(self, model: str = "claude-sonnet-4-6") -> None:
        """Initialize paper analysis agent."""
        super().__init__(analysis_type="paper", model=model)

    async def analyze(self, sources: List[ResearchSource]) -> List[Analysis]:
        """
        Extract findings from papers.

        Args:
            sources: List of research sources (filters to papers only)

        Returns:
            List of paper analyses
        """
        analyses = []

        for source in sources:
            if source.source_type != SourceType.PAPER:
                continue

            # Extract key findings from abstract and metadata
            findings = self._extract_findings(source)

            analysis = Analysis(
                source_id=source.id,
                analysis_type=self.analysis_type,
                findings=findings,
                metadata={
                    "title": source.title,
                    "authors": source.authors,
                    "venue": source.metadata.get("venue", ""),
                    "year": source.metadata.get("year", ""),
                    "citations": source.citations,
                },
                confidence=0.9 if source.abstract else 0.5,
            )
            analyses.append(analysis)

        return analyses

    def _extract_findings(self, source: ResearchSource) -> List[str]:
        """
        Extract key findings from paper abstract and metadata.

        Args:
            source: Research source (paper)

        Returns:
            List of extracted findings
        """
        findings = []

        # Extract from abstract if available
        if source.abstract:
            # Simple heuristic: split by sentences and take first 3
            sentences = source.abstract.split(". ")
            findings.extend(sentences[:3])

        # Add metadata-based findings
        if source.citations > 100:
            findings.append(f"Highly cited paper ({source.citations} citations)")

        venue = source.metadata.get("venue", "")
        if venue and any(
            top_venue in venue.upper()
            for top_venue in ["NEURIPS", "ICML", "ICLR", "ACL", "CVPR"]
        ):
            findings.append(f"Published at top-tier venue: {venue}")

        return findings
