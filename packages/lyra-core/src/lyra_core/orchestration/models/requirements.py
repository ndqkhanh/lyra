"""Data models for requirements and product management."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class Priority(Enum):
    """Priority level for requirements and user stories."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class StoryStatus(Enum):
    """Status of a user story."""

    DRAFT = "draft"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class Requirements:
    """Immutable requirements gathered from user input.

    Attributes:
        id: Unique identifier
        description: High-level description of what needs to be built
        goals: List of business/user goals
        constraints: Technical or business constraints
        stakeholders: List of stakeholders
        priority: Overall priority
        created_at: ISO 8601 timestamp
    """

    id: str
    description: str
    goals: tuple[str, ...]
    constraints: tuple[str, ...]
    stakeholders: tuple[str, ...]
    priority: Priority
    created_at: str

    @staticmethod
    def create(
        id: str,
        description: str,
        goals: list[str],
        constraints: list[str] | None = None,
        stakeholders: list[str] | None = None,
        priority: Priority = Priority.MEDIUM,
    ) -> Requirements:
        """Create requirements with auto-generated timestamp.

        Args:
            id: Unique identifier
            description: Requirements description
            goals: List of goals
            constraints: Optional constraints
            stakeholders: Optional stakeholders
            priority: Priority level

        Returns:
            New Requirements instance
        """
        return Requirements(
            id=id,
            description=description,
            goals=tuple(goals),
            constraints=tuple(constraints or []),
            stakeholders=tuple(stakeholders or []),
            priority=priority,
            created_at=datetime.now(timezone.utc).isoformat(),
        )


@dataclass(frozen=True)
class UserStory:
    """Immutable user story derived from requirements.

    Attributes:
        id: Unique identifier
        title: Short title
        description: As a [user], I want [goal], so that [benefit]
        acceptance_criteria: List of acceptance criteria
        priority: Story priority
        status: Current status
        requirements_id: ID of parent requirements
        estimated_effort: Estimated effort (story points or hours)
        created_at: ISO 8601 timestamp
    """

    id: str
    title: str
    description: str
    acceptance_criteria: tuple[str, ...]
    priority: Priority
    status: StoryStatus
    requirements_id: str
    estimated_effort: int | None
    created_at: str

    @staticmethod
    def create(
        id: str,
        title: str,
        description: str,
        acceptance_criteria: list[str],
        requirements_id: str,
        priority: Priority = Priority.MEDIUM,
        status: StoryStatus = StoryStatus.DRAFT,
        estimated_effort: int | None = None,
    ) -> UserStory:
        """Create user story with auto-generated timestamp.

        Args:
            id: Unique identifier
            title: Story title
            description: Story description
            acceptance_criteria: List of acceptance criteria
            requirements_id: Parent requirements ID
            priority: Priority level
            status: Story status
            estimated_effort: Optional effort estimate

        Returns:
            New UserStory instance
        """
        return UserStory(
            id=id,
            title=title,
            description=description,
            acceptance_criteria=tuple(acceptance_criteria),
            priority=priority,
            status=status,
            requirements_id=requirements_id,
            estimated_effort=estimated_effort,
            created_at=datetime.now(timezone.utc).isoformat(),
        )


@dataclass(frozen=True)
class PRD:
    """Immutable Product Requirements Document.

    Attributes:
        id: Unique identifier
        title: PRD title
        overview: Executive summary
        requirements: Associated requirements
        user_stories: List of user stories
        success_metrics: Measurable success criteria
        timeline: Estimated timeline
        risks: Identified risks
        created_at: ISO 8601 timestamp
    """

    id: str
    title: str
    overview: str
    requirements: Requirements
    user_stories: tuple[UserStory, ...]
    success_metrics: tuple[str, ...]
    timeline: str
    risks: tuple[str, ...]
    created_at: str

    @staticmethod
    def create(
        id: str,
        title: str,
        overview: str,
        requirements: Requirements,
        user_stories: list[UserStory],
        success_metrics: list[str],
        timeline: str,
        risks: list[str] | None = None,
    ) -> PRD:
        """Create PRD with auto-generated timestamp.

        Args:
            id: Unique identifier
            title: PRD title
            overview: Executive summary
            requirements: Requirements object
            user_stories: List of user stories
            success_metrics: Success metrics
            timeline: Timeline estimate
            risks: Optional risks

        Returns:
            New PRD instance
        """
        return PRD(
            id=id,
            title=title,
            overview=overview,
            requirements=requirements,
            user_stories=tuple(user_stories),
            success_metrics=tuple(success_metrics),
            timeline=timeline,
            risks=tuple(risks or []),
            created_at=datetime.now(timezone.utc).isoformat(),
        )


__all__ = ["Requirements", "UserStory", "PRD", "Priority", "StoryStatus"]
