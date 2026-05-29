"""Repository analysis agent for analyzing GitHub repositories."""
from __future__ import annotations

from lyra_research.agents.analysis.analysis_base import Analysis, AnalysisAgent
from lyra_research.discovery import ResearchSource, SourceType


class RepoAnalysisAgent(AnalysisAgent):
    """Specialized agent for analyzing GitHub repositories."""

    def __init__(self, model: str = "claude-sonnet-4-6") -> None:
        """Initialize repository analysis agent."""
        super().__init__(analysis_type="repo", model=model)

    async def analyze(self, sources: list[ResearchSource]) -> list[Analysis]:
        """
        Analyze GitHub repositories.

        Args:
            sources: List of research sources (filters to repositories only)

        Returns:
            List of repository analyses
        """
        analyses = []

        for source in sources:
            if source.source_type != SourceType.REPOSITORY:
                continue

            # Extract repository insights
            findings = self._extract_repo_insights(source)

            analysis = Analysis(
                source_id=source.id,
                analysis_type=self.analysis_type,
                findings=findings,
                metadata={
                    "title": source.title,
                    "stars": source.stars,
                    "language": source.metadata.get("language", ""),
                    "forks": source.metadata.get("forks", 0),
                    "topics": source.metadata.get("topics", []),
                },
                confidence=0.85,
            )
            analyses.append(analysis)

        return analyses

    def _extract_repo_insights(self, source: ResearchSource) -> list[str]:
        """
        Extract insights from repository metadata.

        Args:
            source: Research source (repository)

        Returns:
            List of extracted insights
        """
        findings = []

        # Add description as primary finding
        if source.abstract:
            findings.append(source.abstract)

        # Star-based insights
        if source.stars > 10000:
            findings.append(f"Highly popular repository ({source.stars:,} stars)")
        elif source.stars > 1000:
            findings.append(f"Popular repository ({source.stars:,} stars)")

        # Language insights
        language = source.metadata.get("language", "")
        if language:
            findings.append(f"Primary language: {language}")

        # Activity insights
        forks = source.metadata.get("forks", 0)
        if forks > 1000:
            findings.append(f"Actively forked ({forks:,} forks)")

        # Topics
        topics = source.metadata.get("topics", [])
        if topics:
            findings.append(f"Topics: {', '.join(topics[:5])}")

        return findings
