"""Tests for review phase executor."""

import pytest
from lyra_core.orchestration.message_bus import InMemoryMessageBus
from lyra_core.orchestration.orchestrator import TeamOrchestrator
from lyra_core.orchestration.state_store import InMemoryStateStore
from lyra_core.orchestration.workflow.models import SDLCPhase
from lyra_core.orchestration.workflow.phase_executors.review_executor import (
    ReviewExecutor,
)
from lyra_core.orchestration.workflow.user_review import UserReviewHandler


class TestReviewExecutor:
    """Test suite for ReviewExecutor."""

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
    def review_handler(self) -> UserReviewHandler:
        """Create review handler fixture."""
        return UserReviewHandler()

    @pytest.fixture
    def executor(
        self,
        team_orchestrator: TeamOrchestrator,
        review_handler: UserReviewHandler,
    ) -> ReviewExecutor:
        """Create review executor fixture."""
        return ReviewExecutor(team_orchestrator, review_handler)

    def test_phase_property(self, executor: ReviewExecutor) -> None:
        """Test phase property returns REVIEW."""
        assert executor.phase == SDLCPhase.REVIEW

    def test_required_roles(self, executor: ReviewExecutor) -> None:
        """Test required roles includes all review agents."""
        from lyra_core.orchestration.agent_base import AgentRole

        roles = executor.required_roles
        assert AgentRole.PM in roles
        assert AgentRole.LEAD in roles
        assert AgentRole.PRINCIPAL in roles
        assert AgentRole.QA in roles
        assert AgentRole.SPEC in roles
        assert len(roles) == 5

    def test_requires_user_review(self, executor: ReviewExecutor) -> None:
        """Test that review phase requires user review."""
        assert executor.requires_user_review is True

    @pytest.mark.asyncio
    async def test_execute_success(
        self,
        executor: ReviewExecutor,
        team_orchestrator: TeamOrchestrator,
    ) -> None:
        """Test successful review phase execution."""
        team_id = await team_orchestrator.create_team("Test Team")

        # Prepare input data with all required artifacts
        input_data = {
            "prd": {"title": "Test PRD", "user_stories": [{"id": "US-001"}]},
            "architecture": {"components": ["api", "database"]},
            "code_artifacts": [
                {"path": "main.py", "content": "# code"},
                {"path": "api.py", "content": "# api"},
            ],
            "test_results": {
                "tests_passed": 10,
                "tests_failed": 0,
                "coverage_percentage": 85,
            },
        }

        result = await executor.execute(
            workflow_id="workflow-123",
            team_id=team_id,
            input_data=input_data,
        )

        assert result.phase == SDLCPhase.REVIEW
        assert result.success is True
        assert len(result.artifacts) >= 2  # feedback + final report
        assert result.duration > 0

        # Check metadata
        assert "agent_ids" in result.metadata
        assert "review_request_id" in result.metadata
        assert "overall_approval" in result.metadata
        assert "critical_issues" in result.metadata

    @pytest.mark.asyncio
    async def test_execute_missing_artifacts(
        self,
        executor: ReviewExecutor,
        team_orchestrator: TeamOrchestrator,
    ) -> None:
        """Test execution with missing required artifacts."""
        team_id = await team_orchestrator.create_team("Test Team")

        # Missing test_results
        input_data = {
            "prd": {"title": "Test PRD"},
            "architecture": {"components": []},
            "code_artifacts": [],
        }

        result = await executor.execute(
            workflow_id="workflow-123",
            team_id=team_id,
            input_data=input_data,
        )

        assert result.success is False
        assert len(result.errors) > 0
        assert "Missing required artifacts" in result.errors[0]

    @pytest.mark.asyncio
    async def test_agent_feedback_collection(
        self,
        executor: ReviewExecutor,
        team_orchestrator: TeamOrchestrator,
    ) -> None:
        """Test that all agent feedback is collected."""
        team_id = await team_orchestrator.create_team("Test Team")

        input_data = {
            "prd": {"title": "Test PRD", "user_stories": []},
            "architecture": {"components": []},
            "code_artifacts": [{"path": "test.py"}],
            "test_results": {"tests_passed": 5, "coverage_percentage": 80},
        }

        result = await executor.execute(
            workflow_id="workflow-123",
            team_id=team_id,
            input_data=input_data,
        )

        # Find feedback artifact
        feedback_artifact = next(
            (a for a in result.artifacts if a.type == "agent_feedback"),
            None,
        )
        assert feedback_artifact is not None

        feedback_content = feedback_artifact.content
        assert "pm" in feedback_content
        assert "lead" in feedback_content
        assert "principal" in feedback_content
        assert "qa" in feedback_content
        assert "spec" in feedback_content

    @pytest.mark.asyncio
    async def test_final_report_generation(
        self,
        executor: ReviewExecutor,
        team_orchestrator: TeamOrchestrator,
    ) -> None:
        """Test final review report generation."""
        team_id = await team_orchestrator.create_team("Test Team")

        input_data = {
            "prd": {"title": "Test PRD", "user_stories": []},
            "architecture": {"components": []},
            "code_artifacts": [],
            "test_results": {"tests_passed": 10, "coverage_percentage": 90},
        }

        result = await executor.execute(
            workflow_id="workflow-123",
            team_id=team_id,
            input_data=input_data,
        )

        # Check execution succeeded
        assert result.success is True, f"Execution failed: {result.errors}"

        # Find final report artifact
        report_artifact = next(
            (a for a in result.artifacts if a.type == "final_review_report"),
            None,
        )
        assert report_artifact is not None

        report = report_artifact.content
        assert "overall_approval" in report
        assert "approval_count" in report
        assert "total_reviewers" in report
        assert "critical_issues_count" in report
        assert "concerns" in report
        assert "recommendations" in report
        assert "summary" in report
        assert "agent_feedback" in report

    @pytest.mark.asyncio
    async def test_user_review_request(
        self,
        executor: ReviewExecutor,
        team_orchestrator: TeamOrchestrator,
        review_handler: UserReviewHandler,
    ) -> None:
        """Test that user review is requested."""
        team_id = await team_orchestrator.create_team("Test Team")

        input_data = {
            "prd": {"title": "Test PRD", "user_stories": []},
            "architecture": {"components": []},
            "code_artifacts": [],
            "test_results": {"tests_passed": 10},
        }

        result = await executor.execute(
            workflow_id="workflow-123",
            team_id=team_id,
            input_data=input_data,
        )

        # Check review was requested
        review_id = result.metadata.get("review_request_id")
        assert review_id is not None

        # Check review exists in handler
        pending = await review_handler.get_pending_reviews("workflow-123")
        assert len(pending) == 1
        assert pending[0].id == review_id
        assert len(pending[0].questions) == 4  # 4 review questions

    @pytest.mark.asyncio
    async def test_pm_feedback_collection(
        self,
        executor: ReviewExecutor,
    ) -> None:
        """Test PM feedback collection."""
        prd = {"user_stories": [{"id": "US-001"}, {"id": "US-002"}]}
        test_results = {"tests_passed": 10}

        feedback = await executor._collect_pm_feedback(prd, test_results)

        assert "requirements_met" in feedback
        assert "acceptance_criteria_satisfied" in feedback
        assert "user_stories_completed" in feedback
        assert "approval" in feedback
        assert feedback["user_stories_completed"] == 2

    @pytest.mark.asyncio
    async def test_lead_feedback_collection(
        self,
        executor: ReviewExecutor,
    ) -> None:
        """Test Lead Engineer feedback collection."""
        code_artifacts = [{"path": "file1.py"}, {"path": "file2.py"}]
        architecture = {"components": ["api"]}

        feedback = await executor._collect_lead_feedback(code_artifacts, architecture)

        assert "code_quality" in feedback
        assert "architecture_alignment" in feedback
        assert "code_review_passed" in feedback
        assert "files_reviewed" in feedback
        assert "approval" in feedback
        assert feedback["files_reviewed"] == 2

    @pytest.mark.asyncio
    async def test_principal_feedback_collection(
        self,
        executor: ReviewExecutor,
    ) -> None:
        """Test Principal Engineer feedback collection."""
        architecture = {"components": ["api", "database"]}
        code_artifacts = [{"path": "main.py"}]

        feedback = await executor._collect_principal_feedback(architecture, code_artifacts)

        assert "architecture_quality" in feedback
        assert "scalability_assessment" in feedback
        assert "security_review" in feedback
        assert "approval" in feedback

    @pytest.mark.asyncio
    async def test_qa_feedback_collection(
        self,
        executor: ReviewExecutor,
    ) -> None:
        """Test QA Engineer feedback collection."""
        test_results = {
            "coverage_percentage": 85,
            "tests_passed": 20,
            "tests_failed": 1,
        }
        code_artifacts = []

        feedback = await executor._collect_qa_feedback(test_results, code_artifacts)

        assert "test_coverage" in feedback
        assert "tests_passed" in feedback
        assert "tests_failed" in feedback
        assert "quality_gates_passed" in feedback
        assert "approval" in feedback
        assert feedback["test_coverage"] == 85
        assert feedback["tests_passed"] == 20

    @pytest.mark.asyncio
    async def test_spec_feedback_collection(
        self,
        executor: ReviewExecutor,
    ) -> None:
        """Test Spec-Kit Specialist feedback collection."""
        prd = {"title": "Test PRD"}
        architecture = {"components": []}
        code_artifacts = []

        feedback = await executor._collect_spec_feedback(prd, architecture, code_artifacts)

        assert "spec_compliance" in feedback
        assert "documentation_complete" in feedback
        assert "api_spec_valid" in feedback
        assert "approval" in feedback

    def test_generate_final_report_all_approved(
        self,
        executor: ReviewExecutor,
    ) -> None:
        """Test final report generation with all approvals."""
        pm_feedback = {"approval": "approved", "concerns": [], "recommendations": ["R1"]}
        lead_feedback = {
            "approval": "approved",
            "concerns": [],
            "recommendations": ["R2"],
            "code_quality": "excellent",
        }
        principal_feedback = {
            "approval": "approved",
            "concerns": [],
            "recommendations": [],
            "architecture_quality": "good",
        }
        qa_feedback = {
            "approval": "approved",
            "concerns": [],
            "recommendations": [],
            "test_coverage": 85,
        }
        spec_feedback = {
            "approval": "approved",
            "concerns": [],
            "recommendations": [],
            "documentation_complete": True,
        }

        report = executor._generate_final_report(
            pm_feedback=pm_feedback,
            lead_feedback=lead_feedback,
            principal_feedback=principal_feedback,
            qa_feedback=qa_feedback,
            spec_feedback=spec_feedback,
        )

        assert report["overall_approval"] is True
        assert report["approval_count"] == 5
        assert report["total_reviewers"] == 5
        assert report["critical_issues_count"] == 0
        assert len(report["recommendations"]) == 2

    def test_generate_final_report_with_concerns(
        self,
        executor: ReviewExecutor,
    ) -> None:
        """Test final report generation with concerns."""
        pm_feedback = {
            "approval": "approved",
            "concerns": ["Concern 1"],
            "recommendations": [],
            "requirements_met": True,
        }
        lead_feedback = {
            "approval": "rejected",
            "concerns": ["Concern 2"],
            "recommendations": [],
            "code_quality": "poor",
        }
        principal_feedback = {
            "approval": "approved",
            "concerns": [],
            "recommendations": [],
            "architecture_quality": "good",
        }
        qa_feedback = {
            "approval": "approved",
            "concerns": [],
            "recommendations": [],
            "test_coverage": 70,
        }
        spec_feedback = {
            "approval": "approved",
            "concerns": [],
            "recommendations": [],
            "documentation_complete": False,
        }

        report = executor._generate_final_report(
            pm_feedback=pm_feedback,
            lead_feedback=lead_feedback,
            principal_feedback=principal_feedback,
            qa_feedback=qa_feedback,
            spec_feedback=spec_feedback,
        )

        assert report["overall_approval"] is False
        assert report["approval_count"] == 4
        assert report["critical_issues_count"] == 2
        assert "Concern 1" in report["concerns"]
        assert "Concern 2" in report["concerns"]
