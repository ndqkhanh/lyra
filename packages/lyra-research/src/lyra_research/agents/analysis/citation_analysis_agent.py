"""Citation analysis agent for building citation networks."""
from __future__ import annotations

from lyra_research.agents.analysis.analysis_base import Analysis, AnalysisAgent
from lyra_research.discovery import ResearchSource, SourceType


class CitationAnalysisAgent(AnalysisAgent):
    """Specialized agent for analyzing citation networks."""

    def __init__(self, model: str = "claude-sonnet-4-6") -> None:
        """Initialize citation analysis agent."""
        super().__init__(analysis_type="citation", model=model)

    async def analyze(self, sources: list[ResearchSource]) -> list[Analysis]:
        """
        Build citation network from papers.

        Args:
            sources: List of research sources (filters to papers only)

        Returns:
            List of citation analyses
        """
        analyses = []

        # Build citation graph
        citation_counts: dict[str, int] = {}
        for source in sources:
            if source.source_type == SourceType.PAPER:
                citation_counts[source.id] = source.citations

        # Analyze each paper's position in the network
        for source in sources:
            if source.source_type != SourceType.PAPER:
                continue

            findings = self._analyze_citation_position(source, citation_counts)

            analysis = Analysis(
                source_id=source.id,
                analysis_type=self.analysis_type,
                findings=findings,
                metadata={
                    "citations": source.citations,
                    "citation_rank": self._calculate_rank(source.id, citation_counts),
                    "total_papers": len(citation_counts),
                },
                confidence=0.95,
            )
            analyses.append(analysis)

        return analyses

    def _analyze_citation_position(
        self, source: ResearchSource, citation_counts: dict[str, int]
    ) -> list[str]:
        """
        Analyze paper's position in citation network.

        Args:
            source: Research source (paper)
            citation_counts: Citation counts for all papers

        Returns:
            List of citation insights
        """
        findings = []

        citations = source.citations
        rank = self._calculate_rank(source.id, citation_counts)
        total = len(citation_counts)

        # Citation tier
        if citations > 1000:
            findings.append(f"Seminal work with {citations:,} citations")
        elif citations > 500:
            findings.append(f"Highly influential with {citations:,} citations")
        elif citations > 100:
            findings.append(f"Well-cited with {citations:,} citations")
        elif citations > 10:
            findings.append(f"Moderately cited with {citations} citations")
        else:
            findings.append(f"Recently published or niche ({citations} citations)")

        # Relative ranking
        percentile = (1 - rank / total) * 100 if total > 0 else 0
        findings.append(f"Citation rank: {rank}/{total} (top {percentile:.0f}%)")

        return findings

    def _calculate_rank(self, paper_id: str, citation_counts: dict[str, int]) -> int:
        """
        Calculate paper's rank by citation count (1 = most cited).

        Args:
            paper_id: Paper ID
            citation_counts: Citation counts for all papers

        Returns:
            Rank (1-indexed)
        """
        sorted_papers = sorted(
            citation_counts.items(), key=lambda x: x[1], reverse=True
        )
        for rank, (pid, _) in enumerate(sorted_papers, start=1):
            if pid == paper_id:
                return rank
        return len(citation_counts)
