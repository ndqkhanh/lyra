"""Tests for workflow orchestrator."""

import pytest
from lyra_core.orchestration.message_bus import InMemoryMessageBus
from lyra_core.orchestration.orchestrator import TeamOrchestrator
from lyra_core.orchestration.state_store import InMemoryStateStore
from lyra_core.orchestration.workflow.models import SDLCPhase
from lyra_core.orchestration.workflow.orchestrator import WorkflowOrchestrator
from lyra_core.orchestration.workflow.user_review import UserFeedback


class TestWorkflowOrchestrator:
    """Test suite for WorkflowOrchestrator."""

    @pytest.fixture
    def message_bus(self) -> InMemoryMessageBus:
        """Create message bus fixture."""
        return InMemoryMessageBus()

    @pytest.fixture
    def state_store(self) -> InMemoryStateStore:
        """Create state store fixture."""
        return InMemoryStateStore()

    @pytest.fixture
    def team_orchestrator(
        self,
        message_bus: InMemoryMessageBus,
        state_store: InMemoryStateStore,
    ) -> TeamOrchestrator:
        """Create team orchestrator fixture."""
        return TeamOrchestrator(message_bus, state_store)

    @pytest.fixture
    def orchestrator(
        self,
        team_orchestrator: TeamOrchestrator,
        state_store: InMemoryStateStore,
    ) -> WorkflowOrchestrator:
        """Create workflow orchestrator fixture."""
        return WorkflowOrchestrator(team_orchestrator, state_store)

    @pytest.mark.asyncio
    async def test_create_workflow(
        self,
        orchestrator: WorkflowOrchestrator,
    ) -> None:
        """Test creating a new workflow."""
        workflow = await orchestrator.create_workflow(
            name="Test Workflow",
            requirements="Build a test feature",
        )

        assert workflow.name == "Test Workflow"
        assert workflow.requirements == "Build a test feature"
        assert workflow.current_phase == SDLCPhase.DISCOVERY
        assert workflow.id is not None
        assert workflow.team_id is not None

    @pytest.mark.asyncio
    async def test_create_workflow_with_config(
        self,
        orchestrator: WorkflowOrchestrator,
    ) -> None:
        """Test creating workflow with configuration."""
        config = {"priority": "high", "deadline": "2024-12-31"}

        workflow = await orchestrator.create_workflow(
            name="Test Workflow",
            requirements="Build a test feature",
            config=config,
        )

        assert workflow.metadata == config

    @pytest.mark.asyncio
    async def test_start_workflow(
        self,
        orchestrator: WorkflowOrchestrator,
    ) -> None:
        """Test starting workflow execution."""
        workflow = await orchestrator.create_workflow(
            name="Test Workflow",
            requirements="Build a test feature",
        )

        await orchestrator.start_workflow(workflow.id)

        # Check workflow status
        status = await orchestrator.get_workflow_status(workflow.id)
        assert status.workflow_id == workflow.id
        assert status.current_phase == SDLCPhase.DISCOVERY

    @pytest.mark.asyncio
    async def test_start_invalid_workflow(
        self,
        orchestrator: WorkflowOrchestrator,
    ) -> None:
        """Test starting non-existent workflow."""
        with pytest.raises(ValueError, match="does not exist"):
            await orchestrator.start_workflow("invalid-id")

    @pytest.mark.asyncio
    async def test_execute_phase(
        self,
        orchestrator: WorkflowOrchestrator,
    ) -> None:
        """Test executing a workflow phase."""
        workflow = await orchestrator.create_workflow(
            name="Test Workflow",
            requirements="Build a test feature",
        )

        # Execute discovery phase
        result = await orchestrator.execute_phase(workflow.id, SDLCPhase.DISCOVERY)

        assert result.phase == SDLCPhase.DISCOVERY
        assert result.success is True
        assert len(result.artifacts) > 0
        assert result.duration > 0

    @pytest.mark.asyncio
    async def test_execute_invalid_phase_transition(
        self,
        orchestrator: WorkflowOrchestrator,
    ) -> None:
        """Test executing invalid phase transition."""
        workflow = await orchestrator.create_workflow(
            name="Test Workflow",
            requirements="Build a test feature",
        )

        # Cannot skip to implementation from discovery
        with pytest.raises(ValueError, match="Invalid phase transition"):
            await orchestrator.execute_phase(workflow.id, SDLCPhase.IMPLEMENTATION)

    @pytest.mark.asyncio
    async def test_request_user_review(
        self,
        orchestrator: WorkflowOrchestrator,
    ) -> None:
        """Test requesting user review."""
        workflow = await orchestrator.create_workflow(
            name="Test Workflow",
            requirements="Build a test feature",
        )

        # Execute discovery phase to generate artifacts
        await orchestrator.execute_phase(workflow.id, SDLCPhase.DISCOVERY)

        # Request review
        review = await orchestrator.request_user_review(
            workflow.id,
            SDLCPhase.DISCOVERY,
        )

        assert review.workflow_id == workflow.id
        assert review.phase == SDLCPhase.DISCOVERY
        assert len(review.artifacts) > 0

    @pytest.mark.asyncio
    async def test_handle_user_feedback_approved(
        self,
        orchestrator: WorkflowOrchestrator,
    ) -> None:
        """Test handling approved user feedback."""
        workflow = await orchestrator.create_workflow(
            name="Test Workflow",
            requirements="Build a test feature",
        )

        # Execute discovery phase
        await orchestrator.execute_phase(workflow.id, SDLCPhase.DISCOVERY)

        # Create feedback
        feedback = UserFeedback.create(
            request_id="request-123",
            workflow_id=workflow.id,
            phase=SDLCPhase.DISCOVERY,
            approved=True,
            comments="Looks good!",
        )

        # Handle feedback
        await orchestrator.handle_user_feedback(workflow.id, feedback)

        # Should transition to next phase
        status = await orchestrator.get_workflow_status(workflow.id)
        assert status.current_phase == SDLCPhase.DESIGN

    @pytest.mark.asyncio
    async def test_handle_user_feedback_rejected(
        self,
        orchestrator: WorkflowOrchestrator,
        state_store: InMemoryStateStore,
    ) -> None:
        """Test handling rejected user feedback."""
        workflow = await orchestrator.create_workflow(
            name="Test Workflow",
            requirements="Build a test feature",
        )

        # Execute discovery phase
        await orchestrator.execute_phase(workflow.id, SDLCPhase.DISCOVERY)

        # Create rejected feedback
        feedback = UserFeedback.create(
            request_id="request-123",
            workflow_id=workflow.id,
            phase=SDLCPhase.DISCOVERY,
            approved=False,
            comments="Needs changes",
            changes_requested=["Add more details"],
        )

        # Handle feedback
        await orchestrator.handle_user_feedback(workflow.id, feedback)

        # Should stay in current phase
        status = await orchestrator.get_workflow_status(workflow.id)
        assert status.current_phase == SDLCPhase.DISCOVERY

        # Feedback should be stored
        stored_feedback = await state_store.get(
            f"workflow:{workflow.id}:feedback:discovery"
        )
        assert stored_feedback is not None
        assert stored_feedback["approved"] is False

    @pytest.mark.asyncio
    async def test_transition_phase(
        self,
        orchestrator: WorkflowOrchestrator,
    ) -> None:
        """Test manual phase transition."""
        workflow = await orchestrator.create_workflow(
            name="Test Workflow",
            requirements="Build a test feature",
        )

        # Execute discovery
        await orchestrator.execute_phase(workflow.id, SDLCPhase.DISCOVERY)

        # Transition to design
        await orchestrator.transition_phase(workflow.id, SDLCPhase.DESIGN)

        status = await orchestrator.get_workflow_status(workflow.id)
        assert status.current_phase == SDLCPhase.DESIGN

    @pytest.mark.asyncio
    async def test_get_workflow_status(
        self,
        orchestrator: WorkflowOrchestrator,
    ) -> None:
        """Test getting workflow status."""
        workflow = await orchestrator.create_workflow(
            name="Test Workflow",
            requirements="Build a test feature",
        )

        # Execute discovery phase
        await orchestrator.execute_phase(workflow.id, SDLCPhase.DISCOVERY)

        status = await orchestrator.get_workflow_status(workflow.id)

        assert status.workflow_id == workflow.id
        assert status.current_phase == SDLCPhase.DISCOVERY
        assert status.progress == 0.0
        assert len(status.completed_phases) >= 1  # Phase executed successfully
        assert len(status.artifacts) > 0

    @pytest.mark.asyncio
    async def test_get_workflow_status_invalid(
        self,
        orchestrator: WorkflowOrchestrator,
    ) -> None:
        """Test getting status for non-existent workflow."""
        with pytest.raises(ValueError, match="does not exist"):
            await orchestrator.get_workflow_status("invalid-id")

    @pytest.mark.asyncio
    async def test_stop_workflow(
        self,
        orchestrator: WorkflowOrchestrator,
    ) -> None:
        """Test stopping workflow execution."""
        workflow = await orchestrator.create_workflow(
            name="Test Workflow",
            requirements="Build a test feature",
        )

        await orchestrator.start_workflow(workflow.id)
        await orchestrator.stop_workflow(workflow.id)

        status = await orchestrator.get_workflow_status(workflow.id)
        assert status.current_phase == SDLCPhase.FAILED

    @pytest.mark.asyncio
    async def test_stop_invalid_workflow(
        self,
        orchestrator: WorkflowOrchestrator,
    ) -> None:
        """Test stopping non-existent workflow."""
        with pytest.raises(ValueError, match="does not exist"):
            await orchestrator.stop_workflow("invalid-id")

    @pytest.mark.asyncio
    async def test_workflow_persistence(
        self,
        orchestrator: WorkflowOrchestrator,
        state_store: InMemoryStateStore,
    ) -> None:
        """Test workflow state persistence."""
        workflow = await orchestrator.create_workflow(
            name="Test Workflow",
            requirements="Build a test feature",
        )

        # Check workflow is persisted
        stored = await state_store.get(f"workflow:{workflow.id}")
        assert stored is not None
        assert stored["id"] == workflow.id
        assert stored["name"] == "Test Workflow"

    @pytest.mark.asyncio
    async def test_phase_result_persistence(
        self,
        orchestrator: WorkflowOrchestrator,
        state_store: InMemoryStateStore,
    ) -> None:
        """Test phase result persistence."""
        workflow = await orchestrator.create_workflow(
            name="Test Workflow",
            requirements="Build a test feature",
        )

        await orchestrator.execute_phase(workflow.id, SDLCPhase.DISCOVERY)

        # Check phase result is persisted
        stored = await state_store.get(
            f"workflow:{workflow.id}:phase:discovery"
        )
        assert stored is not None
        assert stored["phase"] == "discovery"
        assert stored["success"] is True

    @pytest.mark.asyncio
    async def test_full_workflow_execution(
        self,
        orchestrator: WorkflowOrchestrator,
    ) -> None:
        """Test executing full workflow through all phases."""
        workflow = await orchestrator.create_workflow(
            name="Test Workflow",
            requirements="Build a test feature",
        )

        # Execute all phases
        phases = [
            SDLCPhase.DISCOVERY,
            SDLCPhase.DESIGN,
            SDLCPhase.IMPLEMENTATION,
            SDLCPhase.TESTING,
            SDLCPhase.REVIEW,
        ]

        for phase in phases:
            result = await orchestrator.execute_phase(workflow.id, phase)
            assert result.success is True
            assert result.phase == phase

            # Transition to next phase
            if phase != SDLCPhase.REVIEW:
                next_phase = phases[phases.index(phase) + 1]
                await orchestrator.transition_phase(workflow.id, next_phase)

        # Final status
        status = await orchestrator.get_workflow_status(workflow.id)
        assert status.current_phase == SDLCPhase.REVIEW
        assert len(status.artifacts) > 0

    @pytest.mark.asyncio
    async def test_workflow_error_handling(
        self,
        orchestrator: WorkflowOrchestrator,
    ) -> None:
        """Test workflow error handling."""
        workflow = await orchestrator.create_workflow(
            name="Test Workflow",
            requirements="",  # Empty requirements should cause error
        )

        result = await orchestrator.execute_phase(workflow.id, SDLCPhase.DISCOVERY)

        # Should fail gracefully
        assert result.success is False
        assert len(result.errors) > 0
