"""Lead Engineer Agent implementation."""

from __future__ import annotations

import uuid
from typing import Any

from lyra_core.orchestration.agent_base import AgentStatus, BaseAgent
from lyra_core.orchestration.models.architecture import (
    Architecture,
    ArchitecturePattern,
    ArchitectureReview,
    ReviewStatus,
    TechStack,
)
from lyra_core.orchestration.models.code_review import (
    CodeReview,
    PRStatus,
    PullRequest,
    ReviewComment,
    ReviewSeverity,
)
from lyra_core.orchestration.protocol import Message


class LeadEngineerAgent(BaseAgent):
    """Lead Engineer agent responsible for technical leadership.

    Responsibilities:
    - Review and approve architecture
    - Make technical decisions
    - Conduct code reviews
    - Coordinate implementation work
    - Resolve technical conflicts
    """

    async def on_start(self) -> None:
        """Initialize Lead Engineer agent."""
        self._set_status(AgentStatus.IDLE)

    async def on_stop(self) -> None:
        """Cleanup Lead Engineer agent."""
        pass

    async def on_message(self, message: Message) -> None:
        """Handle incoming messages.

        Args:
            message: Received message
        """
        action = message.payload.get("action")

        if action == "review_architecture":
            await self._handle_review_architecture(message)
        elif action == "review_code":
            await self._handle_review_code(message)
        elif action == "make_tech_decision":
            await self._handle_make_tech_decision(message)
        elif action == "coordinate_work":
            await self._handle_coordinate_work(message)
        else:
            await self.send_response(
                message,
                {
                    "status": "error",
                    "error": f"Unknown action: {action}",
                },
            )

    async def _handle_review_architecture(self, message: Message) -> None:
        """Handle architecture review request.

        Args:
            message: Request message
        """
        self._set_status(AgentStatus.BUSY)

        try:
            architecture_data = message.payload.get("architecture", {})

            # Reconstruct architecture
            tech_stack = TechStack.create(
                languages=architecture_data["tech_stack"]["languages"],
                frameworks=architecture_data["tech_stack"]["frameworks"],
                databases=architecture_data["tech_stack"]["databases"],
                infrastructure=architecture_data["tech_stack"]["infrastructure"],
                tools=architecture_data["tech_stack"]["tools"],
            )

            architecture = Architecture(
                id=architecture_data["id"],
                pattern=ArchitecturePattern(architecture_data["pattern"]),
                components=tuple(architecture_data["components"]),
                tech_stack=tech_stack,
                data_flow=architecture_data["data_flow"],
                scalability_notes=architecture_data["scalability_notes"],
                security_notes=architecture_data["security_notes"],
                created_at=architecture_data["created_at"],
            )

            review = await self.review_architecture(architecture)

            await self.send_response(
                message,
                {
                    "status": "success",
                    "review": {
                        "id": review.id,
                        "architecture_id": review.architecture_id,
                        "status": review.status.value,
                        "feedback": review.feedback,
                        "concerns": list(review.concerns),
                        "recommendations": list(review.recommendations),
                        "reviewer_id": review.reviewer_id,
                        "created_at": review.created_at,
                    },
                },
            )
        finally:
            self._set_status(AgentStatus.IDLE)

    async def _handle_review_code(self, message: Message) -> None:
        """Handle code review request.

        Args:
            message: Request message
        """
        self._set_status(AgentStatus.BUSY)

        try:
            pr_data = message.payload.get("pull_request", {})

            # Reconstruct pull request
            pr = PullRequest(
                id=pr_data["id"],
                title=pr_data["title"],
                description=pr_data["description"],
                author=pr_data["author"],
                files_changed=tuple(pr_data["files_changed"]),
                additions=pr_data["additions"],
                deletions=pr_data["deletions"],
                status=PRStatus(pr_data["status"]),
                created_at=pr_data["created_at"],
            )

            review = await self.review_code(pr)

            await self.send_response(
                message,
                {
                    "status": "success",
                    "review": {
                        "id": review.id,
                        "pr_id": review.pr_id,
                        "reviewer_id": review.reviewer_id,
                        "status": review.status.value,
                        "summary": review.summary,
                        "comments": [
                            {
                                "file_path": c.file_path,
                                "line_number": c.line_number,
                                "severity": c.severity.value,
                                "message": c.message,
                                "suggestion": c.suggestion,
                            }
                            for c in review.comments
                        ],
                        "critical_count": review.critical_count,
                        "high_count": review.high_count,
                        "medium_count": review.medium_count,
                        "low_count": review.low_count,
                        "created_at": review.created_at,
                    },
                },
            )
        finally:
            self._set_status(AgentStatus.IDLE)

    async def _handle_make_tech_decision(self, message: Message) -> None:
        """Handle technical decision request.

        Args:
            message: Request message
        """
        self._set_status(AgentStatus.BUSY)

        try:
            options = message.payload.get("options", [])

            decision = await self.make_tech_decision(options)

            await self.send_response(
                message,
                {
                    "status": "success",
                    "decision": decision,
                },
            )
        finally:
            self._set_status(AgentStatus.IDLE)

    async def _handle_coordinate_work(self, message: Message) -> None:
        """Handle work coordination request.

        Args:
            message: Request message
        """
        self._set_status(AgentStatus.BUSY)

        try:
            tasks = message.payload.get("tasks", [])

            work_plan = await self.coordinate_work(tasks)

            await self.send_response(
                message,
                {
                    "status": "success",
                    "work_plan": work_plan,
                },
            )
        finally:
            self._set_status(AgentStatus.IDLE)

    async def review_architecture(
        self, architecture: Architecture
    ) -> ArchitectureReview:
        """Review and approve architecture.

        Args:
            architecture: Architecture to review

        Returns:
            ArchitectureReview object
        """
        # Analyze architecture for issues
        concerns = []
        recommendations = []

        # Check for common issues
        if len(architecture.components) < 2:
            concerns.append("Architecture has too few components")

        if not architecture.scalability_notes:
            concerns.append("Missing scalability considerations")

        if not architecture.security_notes:
            concerns.append("Missing security considerations")

        # Provide recommendations
        recommendations.append("Consider adding monitoring and observability")
        recommendations.append("Document failure modes and recovery strategies")

        # Determine status
        status = ReviewStatus.APPROVED if len(concerns) == 0 else ReviewStatus.NEEDS_REVISION

        review = ArchitectureReview.create(
            id=str(uuid.uuid4()),
            architecture_id=architecture.id,
            status=status,
            feedback=f"Architecture review complete. Found {len(concerns)} concerns.",
            reviewer_id=self.agent_id,
            concerns=concerns,
            recommendations=recommendations,
        )

        return review

    async def review_code(self, pr: PullRequest) -> CodeReview:
        """Conduct code review.

        Args:
            pr: Pull request to review

        Returns:
            CodeReview object
        """
        # Analyze code for issues
        comments = []

        # Check for common issues
        if pr.additions > 500:
            comments.append(
                ReviewComment(
                    file_path="overall",
                    line_number=0,
                    severity=ReviewSeverity.MEDIUM,
                    message="PR is large (>500 lines). Consider breaking into smaller PRs.",
                )
            )

        if len(pr.files_changed) > 20:
            comments.append(
                ReviewComment(
                    file_path="overall",
                    line_number=0,
                    severity=ReviewSeverity.MEDIUM,
                    message="Many files changed. Ensure changes are cohesive.",
                )
            )

        # Determine status
        has_critical = any(c.severity == ReviewSeverity.CRITICAL for c in comments)
        status = PRStatus.CHANGES_REQUESTED if has_critical else PRStatus.APPROVED

        review = CodeReview.create(
            id=str(uuid.uuid4()),
            pr_id=pr.id,
            reviewer_id=self.agent_id,
            status=status,
            summary=f"Code review complete. Found {len(comments)} issues.",
            comments=comments,
        )

        return review

    async def make_tech_decision(self, options: list[dict[str, Any]]) -> dict[str, Any]:
        """Make technical decision between options.

        Args:
            options: List of technical options

        Returns:
            Decision result
        """
        # Analyze options and make decision
        # In production, this would use more sophisticated analysis
        if not options:
            return {
                "selected": None,
                "rationale": "No options provided",
            }

        selected = options[0]

        return {
            "selected": selected,
            "rationale": "Selected based on technical merit and team expertise",
            "tradeoffs": [
                "May require additional training",
                "Initial setup complexity",
            ],
        }

    async def coordinate_work(self, tasks: list[dict[str, Any]]) -> dict[str, Any]:
        """Coordinate implementation work across tasks.

        Args:
            tasks: List of tasks to coordinate

        Returns:
            Work plan
        """
        # Create work plan with dependencies and assignments
        return {
            "phases": [
                {
                    "name": "Foundation",
                    "tasks": tasks[:len(tasks) // 2],
                    "duration": "1 week",
                },
                {
                    "name": "Implementation",
                    "tasks": tasks[len(tasks) // 2:],
                    "duration": "2 weeks",
                },
            ],
            "dependencies": ["Foundation must complete before Implementation"],
            "risks": ["Resource availability", "Technical complexity"],
        }


__all__ = ["LeadEngineerAgent"]
