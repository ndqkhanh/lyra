"""
Base class for analysis agents.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from lyra_research.discovery import ResearchSource


@dataclass
class Analysis:
    """Result of source analysis."""

    source_id: str
    analysis_type: str  # "paper", "repo", "citation", "quality"
    findings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    quality_score: float = 0.0  # Overall quality score (0.0-1.0)


class AnalysisAgent(ABC):
    """
    Base class for analysis agents.

    Each agent analyzes sources in a specific way (papers, repos, citations, quality).
    """

    def __init__(self, analysis_type: str, model: str = "claude-sonnet-4-6") -> None:
        """
        Initialize analysis agent.

        Args:
            analysis_type: Type of analysis ("paper", "repo", "citation", "quality")
            model: Model to use for analysis (default: Sonnet for quality)
        """
        self.analysis_type = analysis_type
        self.model = model

    @abstractmethod
    async def analyze(self, source: ResearchSource) -> Analysis:
        """
        Analyze a single source.

        Args:
            source: Research source to analyze

        Returns:
            Analysis result
        """
        pass
