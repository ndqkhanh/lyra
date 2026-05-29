"""Synthesis Role — Synthesizes findings into coherent research report.

Sequential synthesis pipeline:
- Cross-source synthesis (find patterns, connections)
- Contradiction detection (identify conflicts)
- Evidence auditing (verify claims)
- Falsification checking (test hypotheses)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lyra_core.context.layered_context import LayeredContextManager

from lyra_research.agents.analysis import Analysis
from lyra_research.agents.synthesis import (
    ContradictionDetectorAgent,
    CrossSourceSynthesizerAgent,
    EvidenceAuditorAgent,
    FalsificationCheckerAgent,
)
from lyra_research.reporter import ResearchReport
from lyra_research.roles.role_base import Role, RoleResult, RoleStatus


@dataclass
class SynthesisResult(RoleResult):
    """Result from synthesis role."""

    report: ResearchReport | None = None
    contradictions_found: int = 0
    evidence_verified: int = 0
    falsification_tests: int = 0


class SynthesisRole(Role[SynthesisResult]):
    """
    Synthesis Role — Synthesizes findings into coherent report.

    Model: claude-opus-4-7 (deepest reasoning for synthesis)
    """

    def __init__(self, context_manager: LayeredContextManager) -> None:
        """
        Initialize synthesis role.

        Args:
            context_manager: Layered context manager
        """
        super().__init__("Synthesis", "claude-opus-4-7", context_manager)

        # Initialize synthesis agents (sequential pipeline)
        self.cross_source_synthesizer = CrossSourceSynthesizerAgent()
        self.contradiction_detector = ContradictionDetectorAgent()
        self.evidence_auditor = EvidenceAuditorAgent()
        self.falsification_checker = FalsificationCheckerAgent()

    async def execute(self, analyses: list[Analysis]) -> SynthesisResult:
        """
        Execute sequential synthesis pipeline.

        Args:
            analyses: List of analyses from analysis role

        Returns:
            SynthesisResult with research report
        """
        result = SynthesisResult(
            role_name=self.name,
            status=RoleStatus.RUNNING,
            data=None,
        )

        if not analyses:
            result.data = None
            return result

        try:
            # Step 1: Cross-source synthesis
            synthesis = await self.cross_source_synthesizer.synthesize(analyses)

            # Step 2: Contradiction detection
            contradictions = await self.contradiction_detector.detect(synthesis)

            # Step 3: Evidence auditing
            evidence_report = await self.evidence_auditor.audit(synthesis)

            # Step 4: Falsification checking
            falsification_report = await self.falsification_checker.check(synthesis)

            # Build final report
            report = ResearchReport(
                topic=synthesis.get("title", "Research Report"),
                executive_summary=synthesis.get("summary", ""),
                taxonomy_section=str(synthesis.get("taxonomy", {})),
                best_papers_section="\n".join(synthesis.get("findings", [])),
                gaps_section="",
                contested_claims_section="\n".join(str(c) for c in contradictions),
                references_section="",
                sources_used=len(analyses),
                quality_score=0.0,
            )

            result.report = report
            result.contradictions_found = len(contradictions)
            result.evidence_verified = len(evidence_report.get("verified", []))
            result.falsification_tests = len(falsification_report.get("tests", []))
            result.data = report
            result.metadata = {
                "contradictions_found": len(contradictions),
                "evidence_verified": len(evidence_report.get("verified", [])),
                "falsification_tests": len(falsification_report.get("tests", [])),
                "sources_analyzed": len(analyses),
            }

            return result

        except Exception as e:
            result.status = RoleStatus.FAILED
            result.error = str(e)
            return result

    def validate_input(self, analyses: Any) -> bool:
        """
        Validate input analyses.

        Args:
            analyses: List of analyses

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(analyses, list):
            return False

        # Require at least one analysis for synthesis
        if len(analyses) == 0:
            return False

        # Validate each analysis
        for analysis in analyses:
            if not isinstance(analysis, Analysis):
                return False

        return True

    def validate_output(self, report: Any) -> bool:
        """
        Validate synthesis report.

        Args:
            report: Research report

        Returns:
            True if valid, False otherwise
        """
        if report is None:
            return False

        if not isinstance(report, ResearchReport):
            return False

        # Validate required fields
        if not report.topic or len(report.topic.strip()) == 0:
            return False

        if not report.executive_summary or len(report.executive_summary.strip()) == 0:
            return False

        return True
