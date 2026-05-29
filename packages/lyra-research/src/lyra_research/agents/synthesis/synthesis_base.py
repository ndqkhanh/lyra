"""
Base class for synthesis agents.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from lyra_research.agents.analysis.analysis_base import Analysis


@dataclass
class SynthesisResult:
    """Result of synthesis operation."""

    synthesis_type: str  # "cross_source", "contradiction", "evidence", "falsification"
    findings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    issues_found: int = 0
    issues_resolved: int = 0


class SynthesisAgent(ABC):
    """
    Base class for synthesis agents.

    Each agent performs a specific synthesis operation:
    - CrossSourceSynthesizer: Synthesize findings across sources
    - ContradictionDetector: Detect contradictions between sources
    - EvidenceAuditor: Audit evidence quality and citation accuracy
    - FalsificationChecker: Check for falsification attempts
    """

    def __init__(self, synthesis_type: str, model: str = "claude-opus-4-7") -> None:
        """
        Initialize synthesis agent.

        Args:
            synthesis_type: Type of synthesis operation
            model: Model to use (default: Opus for deep reasoning)
        """
        self.synthesis_type = synthesis_type
        self.model = model

    @abstractmethod
    async def synthesize(self, analyses: list[Analysis]) -> SynthesisResult:
        """
        Perform synthesis on the given analyses.

        Args:
            analyses: List of analysis results from analysis agents

        Returns:
            Synthesis result
        """
        pass
