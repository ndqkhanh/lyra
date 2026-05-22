"""Discovery phase executor for requirements gathering."""

from __future__ import annotations

import time
from typing import Any

from lyra_core.orchestration.agent_base import AgentRole
from lyra_core.orchestration.agents.pm_agent import ProductManagerAgent
from lyra_core.orchestration.workflow.models import Artifact, PhaseResult, SDLCPhase
from lyra_core.orchestration.workflow.phase_executors.base_executor import (
    BasePhaseExecutor,
)


class DiscoveryExecutor(BasePhaseExecutor):
    """Executor for the Discovery phase.

    Responsibilities:
    - Spawn PM agent
    - Gather requirements from user input
    - Create user stories and acceptance criteria
    - Generate PRD
    - Request user review and approval
    """

    @property
    def phase(self) -> SDLCPhase:
        """Get the phase this executor handles."""
        return SDLCPhase.DISCOVERY

    @property
    def required_roles(self) -> list[AgentRole]:
        """Get list of required agent roles for this phase."""
        return [AgentRole.PM]

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
        """Execute the Discovery phase.

        Args:
            workflow_id: Workflow ID
            team_id: Team ID
            input_data: Input data containing 'requirements' text

        Returns:
            Phase execution result with PRD artifact
        """
        start_time = time.time()
        artifacts: list[Artifact] = []
        errors: list[str] = []

        try:
            # Spawn PM agent
            agent_ids = await self._spawn_agents(
                team_id=team_id,
                roles=[
                    (
                        AgentRole.PM,
                        ProductManagerAgent,
                        ["requirements_gathering", "prd_creation", "user_stories"],
                    )
                ],
            )

            pm_agent_id = agent_ids[AgentRole.PM]

            # Extract requirements from input
            requirements_text = input_data.get("requirements", "")
            if not requirements_text:
                raise ValueError("No requirements provided in input_data")

            # Create requirements artifact
            requirements_artifact = Artifact.create(
                type="requirements",
                name="Initial Requirements",
                content={"text": requirements_text},
                phase=self.phase,
            )
            artifacts.append(requirements_artifact)

            # Generate user stories (simulated - in real implementation, PM agent would do this)
            user_stories = self._generate_user_stories(requirements_text)
            stories_artifact = Artifact.create(
                type="user_stories",
                name="User Stories",
                content={"stories": user_stories},
                phase=self.phase,
            )
            artifacts.append(stories_artifact)

            # Generate PRD (simulated - in real implementation, PM agent would do this)
            prd = self._generate_prd(requirements_text, user_stories)
            prd_artifact = Artifact.create(
                type="prd",
                name="Product Requirements Document",
                content=prd,
                phase=self.phase,
            )
            artifacts.append(prd_artifact)

            # Request user review
            review_id = await self._request_user_review(
                workflow_id=workflow_id,
                artifacts=artifacts,
                questions=[
                    "Do the user stories accurately capture your requirements?",
                    "Is the PRD complete and clear?",
                    "Are there any missing requirements or concerns?",
                ],
            )

            duration = time.time() - start_time

            return PhaseResult.create(
                phase=self.phase,
                success=True,
                artifacts=artifacts,
                duration=duration,
                metadata={
                    "pm_agent_id": pm_agent_id,
                    "review_request_id": review_id,
                    "user_story_count": len(user_stories),
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

    def _generate_user_stories(self, requirements: str) -> list[dict[str, Any]]:
        """Generate user stories from requirements.

        Args:
            requirements: Requirements text

        Returns:
            List of user story dictionaries
        """
        # Simplified implementation - real version would use PM agent
        return [
            {
                "id": "US-001",
                "title": "Core Functionality",
                "description": f"As a user, I want {requirements[:100]}...",
                "acceptance_criteria": [
                    "Feature is implemented",
                    "Tests pass",
                    "Documentation is complete",
                ],
                "priority": "high",
            }
        ]

    def _generate_prd(
        self,
        requirements: str,
        user_stories: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Generate PRD from requirements and user stories.

        Args:
            requirements: Requirements text
            user_stories: User stories

        Returns:
            PRD dictionary
        """
        # Simplified implementation - real version would use PM agent
        return {
            "title": "Product Requirements Document",
            "overview": requirements,
            "user_stories": user_stories,
            "success_metrics": [
                "Feature completion",
                "User satisfaction",
                "Performance targets met",
            ],
            "timeline": "4 weeks",
            "risks": ["Technical complexity", "Resource availability"],
        }


__all__ = ["DiscoveryExecutor"]
