"""Base phase executor for SDLC workflow phases."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from lyra_core.orchestration.agent_base import AgentRole
from lyra_core.orchestration.orchestrator import TeamOrchestrator
from lyra_core.orchestration.workflow.models import Artifact, PhaseResult, SDLCPhase
from lyra_core.orchestration.workflow.user_review import UserReviewHandler


class BasePhaseExecutor(ABC):
    """Abstract base class for phase executors.

    Each phase executor is responsible for:
    - Spawning required agents
    - Coordinating agent work
    - Producing phase artifacts
    - Requesting user review (if needed)
    """

    def __init__(
        self,
        orchestrator: TeamOrchestrator,
        review_handler: UserReviewHandler,
    ) -> None:
        """Initialize phase executor.

        Args:
            orchestrator: Team orchestrator for spawning agents
            review_handler: User review handler
        """
        self._orchestrator = orchestrator
        self._review_handler = review_handler

    @property
    @abstractmethod
    def phase(self) -> SDLCPhase:
        """Get the phase this executor handles."""
        pass

    @property
    @abstractmethod
    def required_roles(self) -> list[AgentRole]:
        """Get list of required agent roles for this phase."""
        pass

    @property
    @abstractmethod
    def requires_user_review(self) -> bool:
        """Whether this phase requires user review."""
        pass

    @abstractmethod
    async def execute(
        self,
        workflow_id: str,
        team_id: str,
        input_data: dict[str, Any],
    ) -> PhaseResult:
        """Execute the phase.

        Args:
            workflow_id: Workflow ID
            team_id: Team ID
            input_data: Input data from previous phases

        Returns:
            Phase execution result
        """
        pass

    async def _spawn_agents(
        self,
        team_id: str,
        roles: list[tuple[AgentRole, type, list[str]]],
    ) -> dict[AgentRole, str]:
        """Spawn required agents for the phase.

        Args:
            team_id: Team ID
            roles: List of (role, agent_class, capabilities) tuples

        Returns:
            Dictionary mapping role to agent ID
        """
        agent_ids: dict[AgentRole, str] = {}

        for role, agent_class, capabilities in roles:
            agent_id = await self._orchestrator.spawn_agent(
                team_id=team_id,
                role=role,
                agent_class=agent_class,
                capabilities=capabilities,
            )
            agent_ids[role] = agent_id

        return agent_ids

    async def _request_user_review(
        self,
        workflow_id: str,
        artifacts: list[Artifact],
        questions: list[str] | None = None,
    ) -> str:
        """Request user review for phase artifacts.

        Args:
            workflow_id: Workflow ID
            artifacts: Artifacts to review
            questions: Optional questions for user

        Returns:
            Review request ID
        """
        request = await self._review_handler.create_review_request(
            workflow_id=workflow_id,
            phase=self.phase,
            artifacts=artifacts,
            questions=questions,
        )
        return request.id


__all__ = ["BasePhaseExecutor"]
