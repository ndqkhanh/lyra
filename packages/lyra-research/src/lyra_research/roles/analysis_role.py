"""Analysis Role — Analyzes discovered sources for quality and relevance.

Parallel analysis across:
- Paper analysis (content, methodology, findings)
- Repository analysis (code quality, activity, documentation)
- Citation analysis (impact, influence)
- Quality scoring (multi-signal ranking)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List

from lyra_core.context.layered_context import LayeredContextManager
from lyra_research.discovery import ResearchSource
from lyra_research.roles.role_base import Role, RoleResult, RoleStatus
from lyra_research.agents.analysis import (
    Analysis,
    PaperAnalysisAgent,
    RepoAnalysisAgent,
    CitationAnalysisAgent,
    QualityScoreAgent,
)


@dataclass
class AnalysisResult(RoleResult):
    """Result from analysis role."""

    analyses: List[Analysis] = field(default_factory=list)
    total_analyzed: int = 0
    average_quality_score: float = 0.0


class AnalysisRole(Role[AnalysisResult]):
    """
    Analysis Role — Analyzes discovered sources for quality and relevance.

    Model: claude-sonnet-4-6 (best coding model, good for analysis)
    """

    def __init__(self, context_manager: LayeredContextManager) -> None:
        """
        Initialize analysis role.

        Args:
            context_manager: Layered context manager
        """
        super().__init__("Analysis", "claude-sonnet-4-6", context_manager)

        # Initialize analysis agents
        self.analysis_agents = [
            PaperAnalysisAgent(),
            RepoAnalysisAgent(),
            CitationAnalysisAgent(),
            QualityScoreAgent(),
        ]

    async def execute(self, sources: List[ResearchSource]) -> AnalysisResult:
        """
        Execute parallel analysis of all sources.

        Args:
            sources: List of discovered sources

        Returns:
            AnalysisResult with analyses and quality scores
        """
        import asyncio

        result = AnalysisResult(
            role_name=self.name,
            status=RoleStatus.RUNNING,
            data=None,
        )

        if not sources:
            result.data = []
            return result

        try:
            # Parallel analysis across all sources
            # Each source is analyzed by all relevant agents
            all_analyses: List[Analysis] = []

            for source in sources:
                # Determine which agents to use based on source type
                relevant_agents = self._select_agents_for_source(source)

                # Analyze with relevant agents in parallel
                tasks = [agent.analyze(source) for agent in relevant_agents]
                source_analyses = await asyncio.gather(*tasks, return_exceptions=True)

                # Collect successful analyses
                for analysis in source_analyses:
                    if isinstance(analysis, Exception):
                        print(f"Analysis error: {analysis}")
                        continue
                    if isinstance(analysis, Analysis):
                        all_analyses.append(analysis)

            # Calculate statistics
            quality_scores = [a.quality_score for a in all_analyses if a.quality_score > 0]
            avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

            result.analyses = all_analyses
            result.total_analyzed = len(all_analyses)
            result.average_quality_score = avg_quality
            result.data = all_analyses
            result.metadata = {
                "total_analyzed": len(all_analyses),
                "average_quality_score": avg_quality,
                "sources_count": len(sources),
            }

            return result

        except Exception as e:
            result.status = RoleStatus.FAILED
            result.error = str(e)
            return result

    def _select_agents_for_source(self, source: ResearchSource) -> List[Any]:
        """
        Select relevant analysis agents based on source type.

        Args:
            source: Research source

        Returns:
            List of relevant analysis agents
        """
        agents = []

        # Paper analysis for academic papers
        if source.source_type.value in ["arxiv", "semantic_scholar", "openreview"]:
            agents.append(self.analysis_agents[0])  # PaperAnalysisAgent

        # Repo analysis for GitHub sources
        if source.source_type.value == "github":
            agents.append(self.analysis_agents[1])  # RepoAnalysisAgent

        # Citation analysis for all sources with citations
        if source.citations and source.citations > 0:
            agents.append(self.analysis_agents[2])  # CitationAnalysisAgent

        # Quality scoring for all sources
        agents.append(self.analysis_agents[3])  # QualityScoreAgent

        return agents

    def validate_input(self, sources: Any) -> bool:
        """
        Validate input sources.

        Args:
            sources: List of research sources

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(sources, list):
            return False

        # Allow empty list (no sources to analyze)
        if len(sources) == 0:
            return True

        # Validate each source
        for source in sources:
            if not isinstance(source, ResearchSource):
                return False

        return True

    def validate_output(self, analyses: Any) -> bool:
        """
        Validate analysis results.

        Args:
            analyses: List of analyses

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(analyses, list):
            return False

        # Allow empty results
        if len(analyses) == 0:
            return True

        # Validate each analysis
        for analysis in analyses:
            if not isinstance(analysis, Analysis):
                return False
            if not analysis.source_id:
                return False
            if analysis.quality_score < 0 or analysis.quality_score > 1:
                return False

        return True
