"""Workflow orchestrator for SDLC workflow execution.

Coordinates agent teams through SDLC phases, manages phase transitions,
handles user review checkpoints, and tracks workflow progress.
"""

from __future__ import annotations

import asyncio
from typing import Any

from lyra_core.orchestration.orchestrator import TeamOrchestrator, TeamStatus
from lyra_core.orchestration.state_store import StateStore
from lyra_core.orchestration.workflow.models import (
    Artifact,
    PhaseResult,
    SDLCPhase,
    Workflow,
    WorkflowStatus,
)
from lyra_core.orchestration.workflow.phase_executors.base_executor import (
    BasePhaseExecutor,
)
from lyra_core.orchestration.workflow.phase_executors.design_executor import (
    DesignExecutor,
)
from lyra_core.orchestration.workflow.phase_executors.discovery_executor import (
    DiscoveryExecutor,
)
from lyra_core.orchestration.workflow.phase_executors.implementation_executor import (
    ImplementationExecutor,
)
from lyra_core.orchestration.workflow.phase_executors.review_executor import (
    ReviewExecutor,
)
from lyra_core.orchestration.workflow.phase_executors.testing_executor import (
    TestingExecutor,
)
from lyra_core.orchestration.workflow.state_machine import WorkflowStateMachine
from lyra_core.orchestration.workflow.user_review import (
    ReviewRequest,
    UserFeedback,
    UserReviewHandler,
)


class WorkflowOrchestrator:
    """Main workflow orchestrator for SDLC execution.

    Manages workflow lifecycle, coordinates agent teams through phases,
    handles user review checkpoints, and tracks progress.
    """

    def __init__(
        self,
        team_orchestrator: TeamOrchestrator,
        state_store: StateStore,
    ) -> None:
        """Initialize workflow orchestrator.

        Args:
            team_orchestrator: Team orchestrator for spawning agents
            state_store: State store for workflow persistence
        """
        self._team_orchestrator = team_orchestrator
        self._state_store = state_store
        self._review_handler = UserReviewHandler()
        self._workflows: dict[str, Workflow] = {}
        self._state_machines: dict[str, WorkflowStateMachine] = {}
        self._phase_results: dict[str, list[PhaseResult]] = {}
        self._artifacts: dict[str, list[Artifact]] = {}
        self._lock = asyncio.Lock()

        # Initialize phase executors
        self._executors: dict[SDLCPhase, BasePhaseExecutor] = {
            SDLCPhase.DISCOVERY: DiscoveryExecutor(
                team_orchestrator, self._review_handler
            ),
            SDLCPhase.DESIGN: DesignExecutor(team_orchestrator, self._review_handler),
            SDLCPhase.IMPLEMENTATION: ImplementationExecutor(
                team_orchestrator, self._review_handler
            ),
            SDLCPhase.TESTING: TestingExecutor(
                team_orchestrator, self._review_handler
            ),
            SDLCPhase.REVIEW: ReviewExecutor(team_orchestrator, self._review_handler),
        }

    async def create_workflow(
        self,
        name: str,
        requirements: str,
        config: dict[str, Any] | None = None,
    ) -> Workflow:
        """Create a new workflow.

        Args:
            name: Workflow name
            requirements: Initial requirements text
            config: Optional workflow configuration

        Returns:
            Created workflow instance
        """
        async with self._lock:
            # Create team for this workflow
            team_id = await self._team_orchestrator.create_team(
                name=f"Team-{name}",
                config=config,
            )

            # Create workflow
            workflow = Workflow.create(
                name=name,
                requirements=requirements,
                team_id=team_id,
                metadata=config or {},
            )

            # Initialize state machine
            state_machine = WorkflowStateMachine(initial_phase=SDLCPhase.DISCOVERY)

            # Store workflow
            self._workflows[workflow.id] = workflow
            self._state_machines[workflow.id] = state_machine
            self._phase_results[workflow.id] = []
            self._artifacts[workflow.id] = []

            # Persist to state store
            await self._persist_workflow(workflow)

            return workflow

    async def start_workflow(self, workflow_id: str) -> None:
        """Start workflow execution.

        Args:
            workflow_id: Workflow ID

        Raises:
            ValueError: If workflow doesn't exist
        """
        async with self._lock:
            if workflow_id not in self._workflows:
                raise ValueError(f"Workflow {workflow_id} does not exist")

            workflow = self._workflows[workflow_id]

            # Set team status to active
            await self._team_orchestrator.set_team_status(
                workflow.team_id, TeamStatus.ACTIVE
            )

            # Execute first phase (Discovery)
            await self._execute_phase_internal(workflow_id, SDLCPhase.DISCOVERY)

    async def execute_phase(
        self,
        workflow_id: str,
        phase: SDLCPhase,
    ) -> PhaseResult:
        """Execute a specific workflow phase.

        Args:
            workflow_id: Workflow ID
            phase: Phase to execute

        Returns:
            Phase execution result

        Raises:
            ValueError: If workflow doesn't exist or phase is invalid
        """
        async with self._lock:
            return await self._execute_phase_internal(workflow_id, phase)

    async def _execute_phase_internal(
        self,
        workflow_id: str,
        phase: SDLCPhase,
    ) -> PhaseResult:
        """Internal phase execution (assumes lock is held).

        Args:
            workflow_id: Workflow ID
            phase: Phase to execute

        Returns:
            Phase execution result

        Raises:
            ValueError: If workflow doesn't exist or phase is invalid
        """
        if workflow_id not in self._workflows:
            raise ValueError(f"Workflow {workflow_id} does not exist")

        workflow = self._workflows[workflow_id]
        state_machine = self._state_machines[workflow_id]

        # Validate phase transition (allow executing current phase)
        if phase != state_machine.current_phase and not state_machine.can_transition(phase):
            raise ValueError(
                f"Invalid phase transition from {state_machine.current_phase.value} "
                f"to {phase.value}"
            )

        # Get phase executor
        if phase not in self._executors:
            raise ValueError(f"No executor for phase {phase.value}")

        executor = self._executors[phase]

        # Prepare input data from previous phases
        input_data = await self._prepare_phase_input(workflow_id, phase)

        # Execute phase
        result = await executor.execute(
            workflow_id=workflow_id,
            team_id=workflow.team_id,
            input_data=input_data,
        )

        # Store result and artifacts
        self._phase_results[workflow_id].append(result)
        self._artifacts[workflow_id].extend(result.artifacts)

        # Persist result
        await self._persist_phase_result(workflow_id, result)

        return result

    async def request_user_review(
        self,
        workflow_id: str,
        phase: SDLCPhase,
    ) -> ReviewRequest:
        """Request user review for a phase.

        Args:
            workflow_id: Workflow ID
            phase: Phase to review

        Returns:
            Review request

        Raises:
            ValueError: If workflow doesn't exist
        """
        async with self._lock:
            if workflow_id not in self._workflows:
                raise ValueError(f"Workflow {workflow_id} does not exist")

            # Get artifacts for this phase
            phase_artifacts = [
                artifact
                for artifact in self._artifacts[workflow_id]
                if artifact.phase == phase
            ]

            # Create review request
            request = await self._review_handler.create_review_request(
                workflow_id=workflow_id,
                phase=phase,
                artifacts=phase_artifacts,
            )

            return request

    async def handle_user_feedback(
        self,
        workflow_id: str,
        feedback: UserFeedback,
    ) -> None:
        """Handle user feedback on a review request.

        Args:
            workflow_id: Workflow ID
            feedback: User feedback

        Raises:
            ValueError: If workflow doesn't exist
        """
        async with self._lock:
            if workflow_id not in self._workflows:
                raise ValueError(f"Workflow {workflow_id} does not exist")

            workflow = self._workflows[workflow_id]
            state_machine = self._state_machines[workflow_id]

            if feedback.approved:
                # Transition to next phase
                next_phase = self._get_next_phase(feedback.phase)
                if next_phase:
                    await self._transition_phase_internal(workflow_id, next_phase)
            else:
                # Handle rejection - stay in current phase or go back
                if feedback.changes_requested:
                    # Store feedback for re-execution
                    await self._state_store.set(
                        f"workflow:{workflow_id}:feedback:{feedback.phase.value}",
                        {
                            "approved": False,
                            "comments": feedback.comments,
                            "changes_requested": list(feedback.changes_requested),
                        },
                    )

    async def transition_phase(
        self,
        workflow_id: str,
        next_phase: SDLCPhase,
    ) -> None:
        """Transition workflow to next phase.

        Args:
            workflow_id: Workflow ID
            next_phase: Next phase to transition to

        Raises:
            ValueError: If workflow doesn't exist or transition is invalid
        """
        async with self._lock:
            await self._transition_phase_internal(workflow_id, next_phase)

    async def _transition_phase_internal(
        self,
        workflow_id: str,
        next_phase: SDLCPhase,
    ) -> None:
        """Internal phase transition (assumes lock is held).

        Args:
            workflow_id: Workflow ID
            next_phase: Next phase

        Raises:
            ValueError: If workflow doesn't exist or transition is invalid
        """
        if workflow_id not in self._workflows:
            raise ValueError(f"Workflow {workflow_id} does not exist")

        workflow = self._workflows[workflow_id]
        state_machine = self._state_machines[workflow_id]

        # Transition state machine
        state_machine.transition_to(next_phase)

        # Update workflow
        updated_workflow = workflow.with_phase(next_phase)
        self._workflows[workflow_id] = updated_workflow

        # Persist
        await self._persist_workflow(updated_workflow)

        # Execute next phase if not terminal
        if next_phase not in [SDLCPhase.COMPLETED, SDLCPhase.FAILED]:
            await self._execute_phase_internal(workflow_id, next_phase)

    async def get_workflow_status(self, workflow_id: str) -> WorkflowStatus:
        """Get current workflow status.

        Args:
            workflow_id: Workflow ID

        Returns:
            Workflow status snapshot

        Raises:
            ValueError: If workflow doesn't exist
        """
        async with self._lock:
            if workflow_id not in self._workflows:
                raise ValueError(f"Workflow {workflow_id} does not exist")

            workflow = self._workflows[workflow_id]
            state_machine = self._state_machines[workflow_id]

            # Get active agents
            team_status = await self._team_orchestrator.get_team_status(workflow.team_id)
            active_agents = [agent["agent_id"] for agent in team_status["agents"]]

            # Get pending reviews
            pending_reviews = await self._review_handler.get_pending_reviews(
                workflow_id
            )
            pending_review_ids = [review.id for review in pending_reviews]

            # Get completed phases
            completed_phases = [
                result.phase
                for result in self._phase_results[workflow_id]
                if result.success
            ]

            # Calculate progress
            progress = WorkflowStateMachine.get_phase_progress(
                state_machine.current_phase
            )

            return WorkflowStatus.create(
                workflow_id=workflow_id,
                current_phase=state_machine.current_phase,
                progress=progress,
                active_agents=active_agents,
                pending_reviews=pending_review_ids,
                completed_phases=completed_phases,
                artifacts=self._artifacts[workflow_id],
            )

    async def stop_workflow(self, workflow_id: str) -> None:
        """Stop workflow execution.

        Args:
            workflow_id: Workflow ID

        Raises:
            ValueError: If workflow doesn't exist
        """
        async with self._lock:
            if workflow_id not in self._workflows:
                raise ValueError(f"Workflow {workflow_id} does not exist")

            workflow = self._workflows[workflow_id]

            # Stop team
            await self._team_orchestrator.stop_team(workflow.team_id)

            # Transition to FAILED state
            state_machine = self._state_machines[workflow_id]
            if state_machine.can_transition(SDLCPhase.FAILED):
                state_machine.transition_to(SDLCPhase.FAILED)

                # Update workflow
                updated_workflow = workflow.with_phase(SDLCPhase.FAILED)
                self._workflows[workflow_id] = updated_workflow
                await self._persist_workflow(updated_workflow)

    async def _prepare_phase_input(
        self,
        workflow_id: str,
        phase: SDLCPhase,
    ) -> dict[str, Any]:
        """Prepare input data for phase execution.

        Args:
            workflow_id: Workflow ID
            phase: Phase to prepare input for

        Returns:
            Input data dictionary
        """
        workflow = self._workflows[workflow_id]
        input_data: dict[str, Any] = {"requirements": workflow.requirements}

        # Add artifacts from previous phases
        for artifact in self._artifacts[workflow_id]:
            if artifact.type == "prd":
                input_data["prd"] = artifact.content
            elif artifact.type == "architecture":
                input_data["architecture"] = artifact.content
            elif artifact.type == "tech_spec":
                input_data["tech_spec"] = artifact.content
            elif artifact.type == "code":
                if "code_artifacts" not in input_data:
                    input_data["code_artifacts"] = []
                input_data["code_artifacts"].append(artifact.content)
            elif artifact.type == "test_results":
                input_data["test_results"] = artifact.content

        return input_data

    def _get_next_phase(self, current_phase: SDLCPhase) -> SDLCPhase | None:
        """Get the next phase in the workflow.

        Args:
            current_phase: Current phase

        Returns:
            Next phase or None if at end
        """
        phase_order = [
            SDLCPhase.DISCOVERY,
            SDLCPhase.DESIGN,
            SDLCPhase.IMPLEMENTATION,
            SDLCPhase.TESTING,
            SDLCPhase.REVIEW,
            SDLCPhase.COMPLETED,
        ]

        try:
            current_index = phase_order.index(current_phase)
            if current_index < len(phase_order) - 1:
                return phase_order[current_index + 1]
        except ValueError:
            pass

        return None

    async def _persist_workflow(self, workflow: Workflow) -> None:
        """Persist workflow to state store.

        Args:
            workflow: Workflow to persist
        """
        await self._state_store.set(
            f"workflow:{workflow.id}",
            {
                "id": workflow.id,
                "name": workflow.name,
                "requirements": workflow.requirements,
                "current_phase": workflow.current_phase.value,
                "team_id": workflow.team_id,
                "created_at": workflow.created_at,
                "updated_at": workflow.updated_at,
                "metadata": workflow.metadata,
            },
        )

    async def _persist_phase_result(
        self,
        workflow_id: str,
        result: PhaseResult,
    ) -> None:
        """Persist phase result to state store.

        Args:
            workflow_id: Workflow ID
            result: Phase result to persist
        """
        await self._state_store.set(
            f"workflow:{workflow_id}:phase:{result.phase.value}",
            {
                "phase": result.phase.value,
                "success": result.success,
                "duration": result.duration,
                "errors": list(result.errors),
                "metadata": result.metadata,
                "artifact_count": len(result.artifacts),
            },
        )


__all__ = ["WorkflowOrchestrator"]
