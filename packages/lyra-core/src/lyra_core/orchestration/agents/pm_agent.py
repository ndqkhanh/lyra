"""Product Manager Agent implementation."""

from __future__ import annotations

import uuid
from typing import Any

from lyra_core.orchestration.agent_base import AgentStatus, BaseAgent
from lyra_core.orchestration.models.requirements import (
    PRD,
    Priority,
    Requirements,
    StoryStatus,
    UserStory,
)
from lyra_core.orchestration.protocol import Message


class ProductManagerAgent(BaseAgent):
    """Product Manager agent responsible for requirements and product vision.

    Responsibilities:
    - Gather requirements from user input
    - Create user stories and acceptance criteria
    - Define project scope and priorities
    - Generate PRD (Product Requirements Document)
    - Approve/reject design proposals
    """

    async def on_start(self) -> None:
        """Initialize PM agent."""
        self._set_status(AgentStatus.IDLE)

    async def on_stop(self) -> None:
        """Cleanup PM agent."""
        pass

    async def on_message(self, message: Message) -> None:
        """Handle incoming messages.

        Args:
            message: Received message
        """
        action = message.payload.get("action")

        if action == "gather_requirements":
            await self._handle_gather_requirements(message)
        elif action == "create_user_stories":
            await self._handle_create_user_stories(message)
        elif action == "generate_prd":
            await self._handle_generate_prd(message)
        elif action == "review_design":
            await self._handle_review_design(message)
        else:
            # Unknown action, send error response
            await self.send_response(
                message,
                {
                    "status": "error",
                    "error": f"Unknown action: {action}",
                },
            )

    async def _handle_gather_requirements(self, message: Message) -> None:
        """Handle requirements gathering request.

        Args:
            message: Request message
        """
        self._set_status(AgentStatus.BUSY)

        try:
            user_input = message.payload.get("user_input", "")
            priority = message.payload.get("priority", "medium")

            # Parse user input and extract requirements
            requirements = await self.gather_requirements(user_input, priority)

            await self.send_response(
                message,
                {
                    "status": "success",
                    "requirements": {
                        "id": requirements.id,
                        "description": requirements.description,
                        "goals": list(requirements.goals),
                        "constraints": list(requirements.constraints),
                        "stakeholders": list(requirements.stakeholders),
                        "priority": requirements.priority.value,
                        "created_at": requirements.created_at,
                    },
                },
            )
        finally:
            self._set_status(AgentStatus.IDLE)

    async def _handle_create_user_stories(self, message: Message) -> None:
        """Handle user story creation request.

        Args:
            message: Request message
        """
        self._set_status(AgentStatus.BUSY)

        try:
            requirements_data = message.payload.get("requirements", {})

            # Reconstruct requirements object
            requirements = Requirements(
                id=requirements_data["id"],
                description=requirements_data["description"],
                goals=tuple(requirements_data["goals"]),
                constraints=tuple(requirements_data.get("constraints", [])),
                stakeholders=tuple(requirements_data.get("stakeholders", [])),
                priority=Priority(requirements_data["priority"]),
                created_at=requirements_data["created_at"],
            )

            # Create user stories
            stories = await self.create_user_stories(requirements)

            await self.send_response(
                message,
                {
                    "status": "success",
                    "user_stories": [
                        {
                            "id": story.id,
                            "title": story.title,
                            "description": story.description,
                            "acceptance_criteria": list(story.acceptance_criteria),
                            "priority": story.priority.value,
                            "status": story.status.value,
                            "requirements_id": story.requirements_id,
                            "estimated_effort": story.estimated_effort,
                            "created_at": story.created_at,
                        }
                        for story in stories
                    ],
                },
            )
        finally:
            self._set_status(AgentStatus.IDLE)

    async def _handle_generate_prd(self, message: Message) -> None:
        """Handle PRD generation request.

        Args:
            message: Request message
        """
        self._set_status(AgentStatus.BUSY)

        try:
            requirements_data = message.payload.get("requirements", {})
            stories_data = message.payload.get("user_stories", [])

            # Reconstruct objects
            requirements = Requirements(
                id=requirements_data["id"],
                description=requirements_data["description"],
                goals=tuple(requirements_data["goals"]),
                constraints=tuple(requirements_data.get("constraints", [])),
                stakeholders=tuple(requirements_data.get("stakeholders", [])),
                priority=Priority(requirements_data["priority"]),
                created_at=requirements_data["created_at"],
            )

            stories = [
                UserStory(
                    id=s["id"],
                    title=s["title"],
                    description=s["description"],
                    acceptance_criteria=tuple(s["acceptance_criteria"]),
                    priority=Priority(s["priority"]),
                    status=StoryStatus(s["status"]),
                    requirements_id=s["requirements_id"],
                    estimated_effort=s.get("estimated_effort"),
                    created_at=s["created_at"],
                )
                for s in stories_data
            ]

            # Generate PRD
            prd = await self.generate_prd(requirements, stories)

            await self.send_response(
                message,
                {
                    "status": "success",
                    "prd": {
                        "id": prd.id,
                        "title": prd.title,
                        "overview": prd.overview,
                        "success_metrics": list(prd.success_metrics),
                        "timeline": prd.timeline,
                        "risks": list(prd.risks),
                        "created_at": prd.created_at,
                    },
                },
            )
        finally:
            self._set_status(AgentStatus.IDLE)

    async def _handle_review_design(self, message: Message) -> None:
        """Handle design review request.

        Args:
            message: Request message
        """
        self._set_status(AgentStatus.BUSY)

        try:
            design_data = message.payload.get("design", {})

            # Review design
            review = await self.review_design(design_data)

            await self.send_response(
                message,
                {
                    "status": "success",
                    "review": review,
                },
            )
        finally:
            self._set_status(AgentStatus.IDLE)

    async def gather_requirements(
        self, user_input: str, priority: str = "medium"
    ) -> Requirements:
        """Gather requirements from user input.

        Args:
            user_input: User input describing what needs to be built
            priority: Priority level

        Returns:
            Requirements object
        """
        # Parse user input and extract structured requirements
        # In production, this would use NLP/LLM to extract goals, constraints, etc.
        req_id = str(uuid.uuid4())

        return Requirements.create(
            id=req_id,
            description=user_input,
            goals=["Deliver working solution", "Meet user needs"],
            constraints=["Time constraints", "Resource constraints"],
            stakeholders=["Product Team", "Engineering Team"],
            priority=Priority(priority),
        )

    async def create_user_stories(
        self, requirements: Requirements
    ) -> list[UserStory]:
        """Create user stories from requirements.

        Args:
            requirements: Requirements object

        Returns:
            List of user stories
        """
        # In production, this would use LLM to generate stories from requirements
        stories = []

        for i, goal in enumerate(requirements.goals):
            story = UserStory.create(
                id=str(uuid.uuid4()),
                title=f"Story {i + 1}: {goal}",
                description=f"As a user, I want {goal}, so that I can achieve my objectives",
                acceptance_criteria=[
                    "Feature is implemented",
                    "Tests pass",
                    "Documentation is complete",
                ],
                requirements_id=requirements.id,
                priority=requirements.priority,
                status=StoryStatus.DRAFT,
                estimated_effort=5,
            )
            stories.append(story)

        return stories

    async def generate_prd(
        self, requirements: Requirements, stories: list[UserStory]
    ) -> PRD:
        """Generate Product Requirements Document.

        Args:
            requirements: Requirements object
            stories: List of user stories

        Returns:
            PRD object
        """
        prd = PRD.create(
            id=str(uuid.uuid4()),
            title=f"PRD: {requirements.description[:50]}",
            overview=f"This PRD outlines the requirements for: {requirements.description}",
            requirements=requirements,
            user_stories=stories,
            success_metrics=[
                "User satisfaction > 80%",
                "Performance meets SLA",
                "Zero critical bugs",
            ],
            timeline="4 weeks",
            risks=[
                "Technical complexity",
                "Resource availability",
                "Scope creep",
            ],
        )

        return prd

    async def review_design(self, design: dict[str, Any]) -> dict[str, Any]:
        """Review and approve/reject design proposals.

        Args:
            design: Design proposal data

        Returns:
            Review result
        """
        # In production, this would analyze design against requirements
        return {
            "approved": True,
            "feedback": "Design looks good and aligns with requirements",
            "concerns": [],
            "recommendations": ["Consider scalability", "Add monitoring"],
        }


__all__ = ["ProductManagerAgent"]
