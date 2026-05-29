"""Role Orchestrator — Coordinates all 5 specialized roles.

Pipeline:
1. Discovery → discovers sources across 7+ platforms
2. Analysis → analyzes sources for quality and relevance
3. Synthesis → synthesizes findings into coherent report
4. Review → adversarial review with heterogeneous model
5. Curator → quality control and knowledge acceptance

Each role:
- Has clear responsibility
- Uses appropriate model (Haiku/Sonnet/Opus/GPT)
- Validates input/output
- Returns typed result
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from lyra_core.context.layered_context import LayeredContextManager

from lyra_research.roles.analysis_role import AnalysisResult, AnalysisRole
from lyra_research.roles.curator_role import CurationResult, CuratorRole
from lyra_research.roles.discovery_role import DiscoveryResult, DiscoveryRole
from lyra_research.roles.review_role import ReviewResult, ReviewRole
from lyra_research.roles.synthesis_role import SynthesisResult, SynthesisRole


@dataclass
class PipelineResult:
    """Result from full pipeline execution."""

    query: str
    discovery: DiscoveryResult
    analysis: AnalysisResult
    synthesis: SynthesisResult
    review: ReviewResult
    curation: CurationResult
    started_at: datetime
    completed_at: datetime
    total_duration_seconds: float
    metadata: dict[str, any] = field(default_factory=dict)


class RoleOrchestrator:
    """
    Role Orchestrator — Coordinates all 5 specialized roles.

    Pipeline: Discovery → Analysis → Synthesis → Review → Curator
    """

    def __init__(self, context_manager: LayeredContextManager) -> None:
        """
        Initialize role orchestrator.

        Args:
            context_manager: Layered context manager for all roles
        """
        self.context_manager = context_manager

        # Initialize all 5 roles
        self.discovery = DiscoveryRole(context_manager)
        self.analysis = AnalysisRole(context_manager)
        self.synthesis = SynthesisRole(context_manager)
        self.review = ReviewRole(context_manager)
        self.curator = CuratorRole(context_manager)

    async def execute_pipeline(self, query: str) -> PipelineResult:
        """
        Execute full pipeline: Discovery → Analysis → Synthesis → Review → Curator.

        Args:
            query: Research query

        Returns:
            PipelineResult with all role results

        Raises:
            ValueError: If any role fails validation
            RuntimeError: If any role execution fails
        """
        started_at = datetime.now(timezone.utc)

        # Step 1: Discovery
        print(f"[RoleOrchestrator] Step 1/5: Discovery (model: {self.discovery.model})")
        discovery_result = await self.discovery.run(query)
        if discovery_result.status.value != "success":
            raise RuntimeError(f"Discovery failed: {discovery_result.error}")
        print(
            f"[RoleOrchestrator] Discovery complete: {discovery_result.total_sources} sources found"
        )

        # Step 2: Analysis
        print(f"[RoleOrchestrator] Step 2/5: Analysis (model: {self.analysis.model})")
        analysis_result = await self.analysis.run(discovery_result.sources)
        if analysis_result.status.value != "success":
            raise RuntimeError(f"Analysis failed: {analysis_result.error}")
        print(
            f"[RoleOrchestrator] Analysis complete: {analysis_result.total_analyzed} analyses, "
            f"avg quality: {analysis_result.average_quality_score:.2f}"
        )

        # Step 3: Synthesis
        print(f"[RoleOrchestrator] Step 3/5: Synthesis (model: {self.synthesis.model})")
        synthesis_result = await self.synthesis.run(analysis_result.analyses)
        if synthesis_result.status.value != "success":
            raise RuntimeError(f"Synthesis failed: {synthesis_result.error}")
        print(
            f"[RoleOrchestrator] Synthesis complete: {synthesis_result.contradictions_found}"
            f" contradictions, "
            f"{synthesis_result.evidence_verified} evidence verified"
        )

        # Step 4: Review
        print(f"[RoleOrchestrator] Step 4/5: Review (model: {self.review.model})")
        review_result = await self.review.run(synthesis_result.report)
        if review_result.status.value != "success":
            raise RuntimeError(f"Review failed: {review_result.error}")
        print(
            f"[RoleOrchestrator] Review complete: approved={review_result.approved}, "
            f"quality={review_result.overall_quality_score:.2f}, "
            f"issues={len(review_result.issues)}"
        )

        # Step 5: Curator
        print(f"[RoleOrchestrator] Step 5/5: Curator (model: {self.curator.model})")
        # Curator needs both report and review
        curation_input = (synthesis_result.report, review_result)
        curation_result = await self.curator.run(curation_input)
        if curation_result.status.value != "success":
            raise RuntimeError(f"Curation failed: {curation_result.error}")
        print(f"[RoleOrchestrator] Curation complete: accepted={curation_result.accepted}")

        completed_at = datetime.now(timezone.utc)
        total_duration = (completed_at - started_at).total_seconds()

        # Build pipeline result
        result = PipelineResult(
            query=query,
            discovery=discovery_result,
            analysis=analysis_result,
            synthesis=synthesis_result,
            review=review_result,
            curation=curation_result,
            started_at=started_at,
            completed_at=completed_at,
            total_duration_seconds=total_duration,
            metadata={
                "total_sources": discovery_result.total_sources,
                "total_analyzed": analysis_result.total_analyzed,
                "contradictions_found": synthesis_result.contradictions_found,
                "review_approved": review_result.approved,
                "curation_accepted": curation_result.accepted,
                "quality_score": review_result.overall_quality_score,
            },
        )

        print(f"[RoleOrchestrator] Pipeline complete in {total_duration:.2f}s")
        return result

    async def execute_partial_pipeline(self, query: str, stop_at: str) -> dict[str, any]:
        """
        Execute partial pipeline for testing/debugging.

        Args:
            query: Research query
            stop_at: Role to stop at ("discovery", "analysis", "synthesis", "review", "curator")

        Returns:
            Dict with results up to stop_at role
        """
        results = {}

        # Discovery
        discovery_result = await self.discovery.run(query)
        results["discovery"] = discovery_result
        if stop_at == "discovery":
            return results

        # Analysis
        analysis_result = await self.analysis.run(discovery_result.sources)
        results["analysis"] = analysis_result
        if stop_at == "analysis":
            return results

        # Synthesis
        synthesis_result = await self.synthesis.run(analysis_result.analyses)
        results["synthesis"] = synthesis_result
        if stop_at == "synthesis":
            return results

        # Review
        review_result = await self.review.run(synthesis_result.report)
        results["review"] = review_result
        if stop_at == "review":
            return results

        # Curator
        curation_input = (synthesis_result.report, review_result)
        curation_result = await self.curator.run(curation_input)
        results["curator"] = curation_result

        return results

    def get_pipeline_stats(self, result: PipelineResult) -> dict[str, any]:
        """
        Get statistics from pipeline execution.

        Args:
            result: Pipeline result

        Returns:
            Dict with pipeline statistics
        """
        return {
            "query": result.query,
            "total_duration_seconds": result.total_duration_seconds,
            "sources_discovered": result.discovery.total_sources,
            "sources_analyzed": result.analysis.total_analyzed,
            "average_quality_score": result.analysis.average_quality_score,
            "contradictions_found": result.synthesis.contradictions_found,
            "evidence_verified": result.synthesis.evidence_verified,
            "review_approved": result.review.approved,
            "review_quality_score": result.review.overall_quality_score,
            "review_issues": len(result.review.issues),
            "curation_accepted": result.curation.accepted,
            "role_durations": {
                "discovery": result.discovery.duration_seconds(),
                "analysis": result.analysis.duration_seconds(),
                "synthesis": result.synthesis.duration_seconds(),
                "review": result.review.duration_seconds(),
                "curator": result.curation.duration_seconds(),
            },
        }
