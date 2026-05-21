"""Data models for workflow orchestration.

Defines workflow state, phase results, and status tracking for the
SDLC workflow engine.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class SDLCPhase(Enum):
    """SDLC workflow phases."""

    DISCOVERY = "discovery"  # Requirements gathering
    DESIGN = "design"  # Architecture & tech stack
    IMPLEMENTATION = "implementation"  # Code development
    TESTING = "testing"  # QA and validation
    REVIEW = "review"  # Final review & approval
    COMPLETED = "completed"  # Done
    FAILED = "failed"  # Failed


@dataclass(frozen=True)
class Artifact:
    """Immutable artifact produced during a workflow phase.

    Attributes:
        id: Unique identifier
        type: Artifact type (prd, architecture, code, tests, etc.)
        name: Human-readable name
        content: Artifact content or reference
        phase: Phase that produced this artifact
        created_at: ISO 8601 timestamp
    """

    id: str
    type: str
    name: str
    content: Any
    phase: SDLCPhase
    created_at: str

    @staticmethod
    def create(
        type: str,
        name: str,
        content: Any,
        phase: SDLCPhase,
    ) -> Artifact:
        """Create artifact with auto-generated ID and timestamp.

        Args:
            type: Artifact type
            name: Artifact name
            content: Artifact content
            phase: Phase that produced this

        Returns:
            New Artifact instance
        """
        return Artifact(
            id=str(uuid.uuid4()),
            type=type,
            name=name,
            content=content,
            phase=phase,
            created_at=datetime.now(timezone.utc).isoformat(),
        )


@dataclass(frozen=True)
class Workflow:
    """Immutable workflow state.

    Attributes:
        id: Unique workflow identifier
        name: Human-readable workflow name
        requirements: Initial requirements text
        current_phase: Current SDLC phase
        team_id: ID of the team executing this workflow
        created_at: ISO 8601 timestamp when created
        updated_at: ISO 8601 timestamp when last updated
        metadata: Additional workflow metadata
    """

    id: str
    name: str
    requirements: str
    current_phase: SDLCPhase
    team_id: str
    created_at: str
    updated_at: str
    metadata: dict[str, Any]

    @staticmethod
    def create(
        name: str,
        requirements: str,
        team_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> Workflow:
        """Create workflow with auto-generated ID and timestamps.

        Args:
            name: Workflow name
            requirements: Initial requirements
            team_id: Team ID
            metadata: Optional metadata

        Returns:
            New Workflow instance
        """
        now = datetime.now(timezone.utc).isoformat()
        return Workflow(
            id=str(uuid.uuid4()),
            name=name,
            requirements=requirements,
            current_phase=SDLCPhase.DISCOVERY,
            team_id=team_id,
            created_at=now,
            updated_at=now,
            metadata=metadata or {},
        )

    def with_phase(self, phase: SDLCPhase) -> Workflow:
        """Create new workflow with updated phase.

        Args:
            phase: New phase

        Returns:
            New Workflow instance with updated phase
        """
        return Workflow(
            id=self.id,
            name=self.name,
            requirements=self.requirements,
            current_phase=phase,
            team_id=self.team_id,
            created_at=self.created_at,
            updated_at=datetime.now(timezone.utc).isoformat(),
            metadata=self.metadata,
        )


@dataclass(frozen=True)
class PhaseResult:
    """Immutable result of a workflow phase execution.

    Attributes:
        phase: Phase that was executed
        success: Whether phase completed successfully
        artifacts: Artifacts produced during phase
        duration: Execution duration in seconds
        errors: List of errors encountered
        metadata: Additional result metadata
    """

    phase: SDLCPhase
    success: bool
    artifacts: tuple[Artifact, ...]
    duration: float
    errors: tuple[str, ...]
    metadata: dict[str, Any]

    @staticmethod
    def create(
        phase: SDLCPhase,
        success: bool,
        artifacts: list[Artifact],
        duration: float,
        errors: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PhaseResult:
        """Create phase result.

        Args:
            phase: Phase that was executed
            success: Success status
            artifacts: Produced artifacts
            duration: Execution duration
            errors: Optional errors
            metadata: Optional metadata

        Returns:
            New PhaseResult instance
        """
        return PhaseResult(
            phase=phase,
            success=success,
            artifacts=tuple(artifacts),
            duration=duration,
            errors=tuple(errors or []),
            metadata=metadata or {},
        )


@dataclass(frozen=True)
class WorkflowStatus:
    """Immutable workflow status snapshot.

    Attributes:
        workflow_id: Workflow identifier
        current_phase: Current SDLC phase
        progress: Progress percentage (0.0 to 1.0)
        active_agents: List of active agent IDs
        pending_reviews: List of pending review request IDs
        completed_phases: List of completed phases
        artifacts: All artifacts produced so far
    """

    workflow_id: str
    current_phase: SDLCPhase
    progress: float
    active_agents: tuple[str, ...]
    pending_reviews: tuple[str, ...]
    completed_phases: tuple[SDLCPhase, ...]
    artifacts: tuple[Artifact, ...]

    @staticmethod
    def create(
        workflow_id: str,
        current_phase: SDLCPhase,
        progress: float,
        active_agents: list[str],
        pending_reviews: list[str] | None = None,
        completed_phases: list[SDLCPhase] | None = None,
        artifacts: list[Artifact] | None = None,
    ) -> WorkflowStatus:
        """Create workflow status.

        Args:
            workflow_id: Workflow ID
            current_phase: Current phase
            progress: Progress (0.0 to 1.0)
            active_agents: Active agent IDs
            pending_reviews: Optional pending reviews
            completed_phases: Optional completed phases
            artifacts: Optional artifacts

        Returns:
            New WorkflowStatus instance
        """
        return WorkflowStatus(
            workflow_id=workflow_id,
            current_phase=current_phase,
            progress=max(0.0, min(1.0, progress)),
            active_agents=tuple(active_agents),
            pending_reviews=tuple(pending_reviews or []),
            completed_phases=tuple(completed_phases or []),
            artifacts=tuple(artifacts or []),
        )


__all__ = [
    "SDLCPhase",
    "Artifact",
    "Workflow",
    "PhaseResult",
    "WorkflowStatus",
]
