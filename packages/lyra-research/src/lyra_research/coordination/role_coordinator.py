"""Role coordinator for orchestrating the full pipeline.

Coordinates role execution with state management, handoff validation, and progress tracking.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from lyra_core.context.layered_context import LayeredContextManager
from lyra_research.coordination.handoff_protocol import HandoffData, HandoffProtocol
from lyra_research.coordination.progress_tracker import ProgressTracker
from lyra_research.coordination.role_state_machine import RoleState, RoleStateMachine
from lyra_research.roles.analysis_role import AnalysisRole, AnalysisResult
from lyra_research.roles.curator_role import CuratorRole, CurationResult
from lyra_research.roles.discovery_role import DiscoveryRole, DiscoveryResult
from lyra_research.roles.review_role import ReviewRole, ReviewResult
from lyra_research.roles.role_base import Role, RoleResult, RoleStatus
from lyra_research.roles.synthesis_role import SynthesisRole, SynthesisResult


@dataclass
class CoordinatedPipelineResult:
    """Result from coordinated pipeline execution.

    Attributes:
        query: Research query
        discovery: Discovery result
        analysis: Analysis result
        synthesis: Synthesis result
        review: Review result
        curation: Curation result
        started_at: Pipeline start time
        completed_at: Pipeline completion time
        total_duration_seconds: Total execution time
        handoff_stats: Handoff statistics
        progress_stats: Progress statistics
        metadata: Additional metadata
    """

    query: str
    discovery: DiscoveryResult
    analysis: AnalysisResult
    synthesis: SynthesisResult
    review: ReviewResult
    curation: CurationResult
    started_at: datetime
    completed_at: datetime
    total_duration_seconds: float
    handoff_stats: Dict[str, Any]
    progress_stats: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)


class RoleCoordinator:
    """Coordinator for orchestrating role pipeline with state management.

    Manages:
    - Role state transitions
    - Handoff validation
    - Progress tracking
    - Error handling and recovery
    """

    def __init__(
        self,
        context_manager: LayeredContextManager,
    ) -> None:
        """Initialize role coordinator.

        Args:
            context_manager: Layered context manager for all roles
        """
        self.context_manager = context_manager

        # Initialize roles
        self.discovery = DiscoveryRole(context_manager)
        self.analysis = AnalysisRole(context_manager)
        self.synthesis = SynthesisRole(context_manager)
        self.review = ReviewRole(context_manager)
        self.curator = CuratorRole(context_manager)

        # Role mapping
        self._roles: Dict[str, Role] = {
            "Discovery": self.discovery,
            "Analysis": self.analysis,
            "Synthesis": self.synthesis,
            "Review": self.review,
            "Curator": self.curator,
        }

        # Coordination components
        self.state_machine = RoleStateMachine()
        self.handoff_protocol = HandoffProtocol()
        self.progress_tracker = ProgressTracker(list(self._roles.keys()))

    async def execute_pipeline(self, query: str) -> CoordinatedPipelineResult:
        """Execute full role pipeline with coordination.

        Args:
            query: Research query

        Returns:
            CoordinatedPipelineResult with all results and statistics

        Raises:
            RuntimeError: If any role fails or handoff validation fails
        """
        started_at = datetime.now(timezone.utc)
        self.progress_tracker.start_pipeline()

        try:
            # Step 1: Discovery
            discovery_result = await self._execute_role("Discovery", query)
            await self._handoff("Discovery", "Analysis", discovery_result.sources)

            # Step 2: Analysis
            analysis_result = await self._execute_role("Analysis", discovery_result.sources)
            await self._handoff("Analysis", "Synthesis", analysis_result.analyses)

            # Step 3: Synthesis
            synthesis_result = await self._execute_role("Synthesis", analysis_result.analyses)
            await self._handoff("Synthesis", "Review", synthesis_result.report)

            # Step 4: Review
            review_result = await self._execute_role("Review", synthesis_result.report)
            await self._handoff("Review", "Curator", (synthesis_result.report, review_result))

            # Step 5: Curator
            curation_input = (synthesis_result.report, review_result)
            curation_result = await self._execute_role("Curator", curation_input)

            # Pipeline complete
            completed_at = datetime.now(timezone.utc)
            self.progress_tracker.complete_pipeline()

            # Build result
            result = CoordinatedPipelineResult(
                query=query,
                discovery=discovery_result,
                analysis=analysis_result,
                synthesis=synthesis_result,
                review=review_result,
                curation=curation_result,
                started_at=started_at,
                completed_at=completed_at,
                total_duration_seconds=(completed_at - started_at).total_seconds(),
                handoff_stats=self.handoff_protocol.get_handoff_stats(),
                progress_stats=self.progress_tracker.get_pipeline_status(),
                metadata={
                    "total_sources": discovery_result.total_sources,
                    "total_analyzed": analysis_result.total_analyzed,
                    "contradictions_found": synthesis_result.contradictions_found,
                    "review_approved": review_result.approved,
                    "curation_accepted": curation_result.accepted,
                    "quality_score": review_result.overall_quality_score,
                },
            )

            return result

        except Exception as e:
            self.progress_tracker.complete_pipeline()
            raise RuntimeError(f"Pipeline execution failed: {str(e)}") from e

    async def _execute_role(self, role_name: str, input_data: Any) -> RoleResult:
        """Execute role with state management and error handling.

        Args:
            role_name: Name of the role
            input_data: Input data for the role

        Returns:
            RoleResult from execution

        Raises:
            RuntimeError: If role execution fails
        """
        role = self._roles[role_name]

        # Transition to RUNNING
        success, error = self.state_machine.transition(role_name, "start")
        if not success:
            raise RuntimeError(f"Failed to start {role_name}: {error}")

        # Update progress
        self.progress_tracker.start_role(role_name)
        self.progress_tracker.update_role_state(role_name, RoleState.RUNNING)

        print(f"[RoleCoordinator] Executing {role_name} (model: {role.model})")

        try:
            # Execute role
            result = await role.run(input_data)

            # Check result status
            if result.status != RoleStatus.SUCCESS:
                # Transition to FAILED
                self.state_machine.transition(role_name, "fail")
                self.progress_tracker.complete_role(role_name, error=result.error)
                raise RuntimeError(f"{role_name} failed: {result.error}")

            # Transition to COMPLETED
            self.state_machine.transition(role_name, "complete")
            self.progress_tracker.complete_role(role_name)

            # Add metadata
            self.progress_tracker.add_role_metadata(
                role_name, "duration_seconds", result.duration_seconds()
            )

            print(f"[RoleCoordinator] {role_name} completed in {result.duration_seconds():.2f}s")

            return result

        except Exception as e:
            # Transition to FAILED
            self.state_machine.transition(role_name, "fail")
            self.progress_tracker.complete_role(role_name, error=str(e))
            raise RuntimeError(f"{role_name} execution failed: {str(e)}") from e

    async def _handoff(self, from_role_name: str, to_role_name: str, data: Any) -> None:
        """Execute handoff with gate enforcement.

        Args:
            from_role_name: Source role name
            to_role_name: Target role name
            data: Data to transfer

        Raises:
            RuntimeError: If handoff validation fails
        """
        from_role = self._roles[from_role_name]
        to_role = self._roles[to_role_name]

        # Prepare handoff
        handoff = self.handoff_protocol.prepare_handoff(from_role, to_role, data)

        # Execute handoff with validation
        success, error = self.handoff_protocol.execute_handoff(handoff, from_role, to_role)

        if not success:
            # Rollback handoff
            self.handoff_protocol.rollback_handoff(handoff)
            raise RuntimeError(f"Handoff {from_role_name} → {to_role_name} failed: {error}")

        print(f"[RoleCoordinator] Handoff {from_role_name} → {to_role_name} validated")

    def get_role_state(self, role_name: str) -> RoleState:
        """Get current state of a role.

        Args:
            role_name: Name of the role

        Returns:
            Current role state
        """
        return self.state_machine.get_state(role_name)

    def get_role_progress(self, role_name: str) -> float:
        """Get progress of a role.

        Args:
            role_name: Name of the role

        Returns:
            Progress percentage (0.0 to 1.0)
        """
        return self.progress_tracker.get_role_progress(role_name)

    def get_pipeline_progress(self) -> float:
        """Get overall pipeline progress.

        Returns:
            Progress percentage (0.0 to 1.0)
        """
        return self.progress_tracker.get_pipeline_progress()

    def get_coordination_stats(self) -> Dict[str, Any]:
        """Get coordination statistics.

        Returns:
            Dict with coordination statistics
        """
        return {
            "handoff_stats": self.handoff_protocol.get_handoff_stats(),
            "progress_stats": self.progress_tracker.get_pipeline_status(),
            "role_states": {
                name: self.state_machine.get_state(name).value
                for name in self._roles.keys()
            },
        }

    def reset(self) -> None:
        """Reset coordinator state."""
        self.state_machine.reset_all()
        self.handoff_protocol.clear_history()
        self.progress_tracker.reset()
