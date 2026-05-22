"""Design phase executor for architecture and tech stack selection."""

from __future__ import annotations

import time
from typing import Any

from lyra_core.orchestration.agent_base import AgentRole
from lyra_core.orchestration.agents.principal_agent import PrincipalEngineerAgent
from lyra_core.orchestration.workflow.models import Artifact, PhaseResult, SDLCPhase
from lyra_core.orchestration.workflow.phase_executors.base_executor import (
    BasePhaseExecutor,
)


class DesignExecutor(BasePhaseExecutor):
    """Executor for the Design phase.

    Responsibilities:
    - Spawn Principal Engineer agent
    - Design system architecture
    - Select tech stack
    - Create technical specifications
    - Request user review and approval
    """

    @property
    def phase(self) -> SDLCPhase:
        """Get the phase this executor handles."""
        return SDLCPhase.DESIGN

    @property
    def required_roles(self) -> list[AgentRole]:
        """Get list of required agent roles for this phase."""
        return [AgentRole.PRINCIPAL]

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
        """Execute the Design phase.

        Args:
            workflow_id: Workflow ID
            team_id: Team ID
            input_data: Input data containing PRD from Discovery phase

        Returns:
            Phase execution result with architecture artifacts
        """
        start_time = time.time()
        artifacts: list[Artifact] = []
        errors: list[str] = []

        try:
            # Spawn Principal Engineer agent
            agent_ids = await self._spawn_agents(
                team_id=team_id,
                roles=[
                    (
                        AgentRole.PRINCIPAL,
                        PrincipalEngineerAgent,
                        [
                            "architecture_design",
                            "tech_stack_selection",
                            "scalability_planning",
                        ],
                    )
                ],
            )

            principal_agent_id = agent_ids[AgentRole.PRINCIPAL]

            # Extract PRD from input
            prd = input_data.get("prd")
            if not prd:
                raise ValueError("No PRD provided in input_data")

            # Design architecture (simulated)
            architecture = self._design_architecture(prd)
            arch_artifact = Artifact.create(
                type="architecture",
                name="System Architecture",
                content=architecture,
                phase=self.phase,
            )
            artifacts.append(arch_artifact)

            # Select tech stack (simulated)
            tech_stack = self._select_tech_stack(architecture)
            tech_artifact = Artifact.create(
                type="tech_stack",
                name="Technology Stack",
                content=tech_stack,
                phase=self.phase,
            )
            artifacts.append(tech_artifact)

            # Create technical specifications (simulated)
            tech_spec = self._create_tech_spec(architecture, tech_stack)
            spec_artifact = Artifact.create(
                type="tech_spec",
                name="Technical Specification",
                content=tech_spec,
                phase=self.phase,
            )
            artifacts.append(spec_artifact)

            # Request user review
            review_id = await self._request_user_review(
                workflow_id=workflow_id,
                artifacts=artifacts,
                questions=[
                    "Does the architecture meet your scalability requirements?",
                    "Is the tech stack appropriate for your team and constraints?",
                    "Are there any architectural concerns or missing components?",
                ],
            )

            duration = time.time() - start_time

            return PhaseResult.create(
                phase=self.phase,
                success=True,
                artifacts=artifacts,
                duration=duration,
                metadata={
                    "principal_agent_id": principal_agent_id,
                    "review_request_id": review_id,
                    "architecture_pattern": architecture.get("pattern"),
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

    def _design_architecture(self, prd: dict[str, Any]) -> dict[str, Any]:
        """Design system architecture based on PRD.

        Args:
            prd: Product Requirements Document

        Returns:
            Architecture design dictionary
        """
        # Simplified implementation - real version would use Principal agent
        return {
            "pattern": "layered",
            "components": [
                "API Gateway",
                "Application Layer",
                "Data Layer",
                "Cache Layer",
            ],
            "data_flow": "Client -> API Gateway -> Application -> Data Layer",
            "scalability_notes": "Horizontal scaling with load balancer",
            "security_notes": "JWT authentication, HTTPS, input validation",
        }

    def _select_tech_stack(self, architecture: dict[str, Any]) -> dict[str, Any]:
        """Select technology stack based on architecture.

        Args:
            architecture: Architecture design

        Returns:
            Tech stack dictionary
        """
        # Simplified implementation - real version would use Principal agent
        return {
            "languages": ["Python", "TypeScript"],
            "frameworks": ["FastAPI", "React"],
            "databases": ["PostgreSQL", "Redis"],
            "infrastructure": ["Docker", "Kubernetes"],
            "tools": ["pytest", "Jest", "GitHub Actions"],
        }

    def _create_tech_spec(
        self,
        architecture: dict[str, Any],
        tech_stack: dict[str, Any],
    ) -> dict[str, Any]:
        """Create technical specification.

        Args:
            architecture: Architecture design
            tech_stack: Technology stack

        Returns:
            Technical specification dictionary
        """
        # Simplified implementation - real version would use Principal agent
        return {
            "title": "Technical Specification",
            "overview": "System design and implementation details",
            "api_contracts": ["REST API with OpenAPI 3.0 spec"],
            "data_models": ["User", "Session", "Transaction"],
            "interfaces": ["HTTP REST", "WebSocket"],
            "dependencies": ["PostgreSQL 15+", "Redis 7+", "Python 3.11+"],
        }


__all__ = ["DesignExecutor"]
