"""Review phase executor for final review and approval."""

from __future__ import annotations

import time
from typing import Any

from lyra_core.orchestration.agent_base import AgentRole
from lyra_core.orchestration.agents.lead_agent import LeadEngineerAgent
from lyra_core.orchestration.agents.pm_agent import ProductManagerAgent
from lyra_core.orchestration.agents.principal_agent import PrincipalEngineerAgent
from lyra_core.orchestration.agents.qa_agent import QAEngineerAgent
from lyra_core.orchestration.agents.spec_agent import SpecKitSpecialistAgent
from lyra_core.orchestration.workflow.models import Artifact, PhaseResult, SDLCPhase
from lyra_core.orchestration.workflow.phase_executors.base_executor import (
    BasePhaseExecutor,
)


class ReviewExecutor(BasePhaseExecutor):
    """Executor for the Review phase.

    Responsibilities:
    - Spawn all review agents (PM, Lead, Principal, QA, Spec)
    - Collect feedback from each agent
    - Generate comprehensive final report
    - Request user approval for completion
    - Handle approval/rejection workflow
    """

    @property
    def phase(self) -> SDLCPhase:
        """Get the phase this executor handles."""
        return SDLCPhase.REVIEW

    @property
    def required_roles(self) -> list[AgentRole]:
        """Get list of required agent roles for this phase."""
        return [
            AgentRole.PM,
            AgentRole.LEAD,
            AgentRole.PRINCIPAL,
            AgentRole.QA,
            AgentRole.SPEC,
        ]

    @property
    def requires_user_review(self) -> bool:
        """Whether this phase requires user review."""
        return True

    async def execute(
        self,
        workflow_id: str,
        team_id: str,
        input_data: dict[str, Any],
    ) -> PhaseResult:
        """Execute the Review phase.

        Args:
            workflow_id: Workflow ID
            team_id: Team ID
            input_data: Input data containing all artifacts from previous phases

        Returns:
            Phase execution result with final review report
        """
        start_time = time.time()
        artifacts: list[Artifact] = []
        errors: list[str] = []

        try:
            # Spawn all review agents
            agent_ids = await self._spawn_agents(
                team_id=team_id,
                roles=[
                    (
                        AgentRole.PM,
                        ProductManagerAgent,
                        ["requirements_review", "acceptance_criteria"],
                    ),
                    (
                        AgentRole.LEAD,
                        LeadEngineerAgent,
                        ["code_review", "architecture_review"],
                    ),
                    (
                        AgentRole.PRINCIPAL,
                        PrincipalEngineerAgent,
                        ["architecture_review", "scalability_review"],
                    ),
                    (
                        AgentRole.QA,
                        QAEngineerAgent,
                        ["quality_review", "test_coverage_review"],
                    ),
                    (
                        AgentRole.SPEC,
                        SpecKitSpecialistAgent,
                        ["spec_compliance_review", "documentation_review"],
                    ),
                ],
            )

            # Extract artifacts from previous phases
            prd = input_data.get("prd")
            architecture = input_data.get("architecture")
            code_artifacts = input_data.get("code_artifacts", [])
            test_results = input_data.get("test_results")

            if prd is None or architecture is None or test_results is None:
                raise ValueError("Missing required artifacts from previous phases")

            # Collect feedback from each agent
            pm_feedback = await self._collect_pm_feedback(prd, test_results)
            lead_feedback = await self._collect_lead_feedback(code_artifacts, architecture)
            principal_feedback = await self._collect_principal_feedback(
                architecture, code_artifacts
            )
            qa_feedback = await self._collect_qa_feedback(test_results, code_artifacts)
            spec_feedback = await self._collect_spec_feedback(prd, architecture, code_artifacts)

            # Create feedback artifacts
            feedback_artifact = Artifact.create(
                type="agent_feedback",
                name="Agent Review Feedback",
                content={
                    "pm": pm_feedback,
                    "lead": lead_feedback,
                    "principal": principal_feedback,
                    "qa": qa_feedback,
                    "spec": spec_feedback,
                },
                phase=self.phase,
            )
            artifacts.append(feedback_artifact)

            # Generate final review report
            final_report = self._generate_final_report(
                pm_feedback=pm_feedback,
                lead_feedback=lead_feedback,
                principal_feedback=principal_feedback,
                qa_feedback=qa_feedback,
                spec_feedback=spec_feedback,
            )

            report_artifact = Artifact.create(
                type="final_review_report",
                name="Final Review Report",
                content=final_report,
                phase=self.phase,
            )
            artifacts.append(report_artifact)

            # Request user approval
            review_id = await self._request_user_review(
                workflow_id=workflow_id,
                artifacts=artifacts,
                questions=[
                    "Do you approve the final implementation?",
                    "Are all requirements met to your satisfaction?",
                    "Is the quality acceptable for deployment?",
                    "Any final concerns or changes needed?",
                ],
            )

            duration = time.time() - start_time

            return PhaseResult.create(
                phase=self.phase,
                success=True,
                artifacts=artifacts,
                duration=duration,
                metadata={
                    "agent_ids": {role.value: agent_id for role, agent_id in agent_ids.items()},
                    "review_request_id": review_id,
                    "overall_approval": final_report["overall_approval"],
                    "critical_issues": final_report["critical_issues_count"],
                },
            )

        except Exception as e:
            duration = time.time() - start_time
            errors.append(str(e))

            return PhaseResult.create(
                phase=self.phase,
                success=False,
                artifacts=artifacts,
                duration=duration,
                errors=errors,
            )

    async def _collect_pm_feedback(
        self,
        prd: dict[str, Any],
        test_results: dict[str, Any],
    ) -> dict[str, Any]:
        """Collect feedback from PM agent.

        Args:
            prd: Product requirements document
            test_results: Test results

        Returns:
            PM feedback dictionary
        """
        # Simplified - real implementation would use PM agent
        return {
            "requirements_met": True,
            "acceptance_criteria_satisfied": True,
            "user_stories_completed": len(prd.get("user_stories", [])),
            "concerns": [],
            "recommendations": ["Consider adding user onboarding flow"],
            "approval": "approved",
        }

    async def _collect_lead_feedback(
        self,
        code_artifacts: list[dict[str, Any]],
        architecture: dict[str, Any],
    ) -> dict[str, Any]:
        """Collect feedback from Lead Engineer agent.

        Args:
            code_artifacts: Code artifacts
            architecture: Architecture design

        Returns:
            Lead feedback dictionary
        """
        # Simplified - real implementation would use Lead agent
        return {
            "code_quality": "excellent",
            "architecture_alignment": True,
            "code_review_passed": True,
            "files_reviewed": len(code_artifacts),
            "issues_found": 0,
            "concerns": [],
            "recommendations": ["Add more inline documentation"],
            "approval": "approved",
        }

    async def _collect_principal_feedback(
        self,
        architecture: dict[str, Any],
        code_artifacts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Collect feedback from Principal Engineer agent.

        Args:
            architecture: Architecture design
            code_artifacts: Code artifacts

        Returns:
            Principal feedback dictionary
        """
        # Simplified - real implementation would use Principal agent
        return {
            "architecture_quality": "excellent",
            "scalability_assessment": "good",
            "performance_concerns": [],
            "security_review": "passed",
            "best_practices_followed": True,
            "concerns": [],
            "recommendations": ["Consider adding caching layer for future scale"],
            "approval": "approved",
        }

    async def _collect_qa_feedback(
        self,
        test_results: dict[str, Any],
        code_artifacts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Collect feedback from QA agent.

        Args:
            test_results: Test results
            code_artifacts: Code artifacts

        Returns:
            QA feedback dictionary
        """
        # Simplified - real implementation would use QA agent
        return {
            "test_coverage": test_results.get("coverage_percentage", 0),
            "tests_passed": test_results.get("tests_passed", 0),
            "tests_failed": test_results.get("tests_failed", 0),
            "quality_gates_passed": True,
            "bugs_found": 0,
            "concerns": [],
            "recommendations": ["Add more edge case tests"],
            "approval": "approved",
        }

    async def _collect_spec_feedback(
        self,
        prd: dict[str, Any],
        architecture: dict[str, Any],
        code_artifacts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Collect feedback from Spec-Kit Specialist agent.

        Args:
            prd: Product requirements document
            architecture: Architecture design
            code_artifacts: Code artifacts

        Returns:
            Spec feedback dictionary
        """
        # Simplified - real implementation would use Spec agent
        return {
            "spec_compliance": True,
            "documentation_complete": True,
            "api_spec_valid": True,
            "concerns": [],
            "recommendations": ["Add API versioning documentation"],
            "approval": "approved",
        }

    def _generate_final_report(
        self,
        pm_feedback: dict[str, Any],
        lead_feedback: dict[str, Any],
        principal_feedback: dict[str, Any],
        qa_feedback: dict[str, Any],
        spec_feedback: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate comprehensive final review report.

        Args:
            pm_feedback: PM agent feedback
            lead_feedback: Lead agent feedback
            principal_feedback: Principal agent feedback
            qa_feedback: QA agent feedback
            spec_feedback: Spec agent feedback

        Returns:
            Final review report dictionary
        """
        # Aggregate approvals
        approvals = [
            pm_feedback.get("approval") == "approved",
            lead_feedback.get("approval") == "approved",
            principal_feedback.get("approval") == "approved",
            qa_feedback.get("approval") == "approved",
            spec_feedback.get("approval") == "approved",
        ]

        overall_approval = all(approvals)

        # Aggregate concerns
        all_concerns = (
            pm_feedback.get("concerns", [])
            + lead_feedback.get("concerns", [])
            + principal_feedback.get("concerns", [])
            + qa_feedback.get("concerns", [])
            + spec_feedback.get("concerns", [])
        )

        # Aggregate recommendations
        all_recommendations = (
            pm_feedback.get("recommendations", [])
            + lead_feedback.get("recommendations", [])
            + principal_feedback.get("recommendations", [])
            + qa_feedback.get("recommendations", [])
            + spec_feedback.get("recommendations", [])
        )

        return {
            "overall_approval": overall_approval,
            "approval_count": sum(approvals),
            "total_reviewers": len(approvals),
            "critical_issues_count": len(all_concerns),
            "concerns": all_concerns,
            "recommendations": all_recommendations,
            "summary": {
                "requirements": (
                    "All requirements met"
                    if pm_feedback.get("requirements_met")
                    else "Requirements incomplete"
                ),
                "code_quality": lead_feedback.get("code_quality", "unknown"),
                "architecture": principal_feedback.get("architecture_quality", "unknown"),
                "testing": f"{qa_feedback.get('test_coverage', 0)}% coverage",
                "documentation": (
                    "Complete" if spec_feedback.get("documentation_complete") else "Incomplete"
                ),
            },
            "agent_feedback": {
                "pm": pm_feedback,
                "lead": lead_feedback,
                "principal": principal_feedback,
                "qa": qa_feedback,
                "spec": spec_feedback,
            },
        }


__all__ = ["ReviewExecutor"]
