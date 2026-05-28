"""Spec-Kit Specialist Agent implementation."""

from __future__ import annotations

import uuid
from typing import Any

from lyra_core.orchestration.agent_base import AgentStatus, BaseAgent
from lyra_core.orchestration.models.documentation import (
    APIDocumentation,
    DocsReview,
    DocStatus,
    DocType,
    Specification,
)
from lyra_core.orchestration.protocol import Message


class SpecKitSpecialistAgent(BaseAgent):
    """Spec-Kit Specialist agent responsible for documentation.

    Responsibilities:
    - Write API documentation
    - Create technical specifications
    - Generate code contracts
    - Maintain documentation
    - Review documentation quality
    """

    async def on_start(self) -> None:
        """Initialize Spec-Kit Specialist agent."""
        self._set_status(AgentStatus.IDLE)

    async def on_stop(self) -> None:
        """Cleanup Spec-Kit Specialist agent."""
        pass

    async def on_message(self, message: Message) -> None:
        """Handle incoming messages.

        Args:
            message: Received message
        """
        action = message.payload.get("action")

        if action == "write_api_docs":
            await self._handle_write_api_docs(message)
        elif action == "create_spec":
            await self._handle_create_spec(message)
        elif action == "generate_contracts":
            await self._handle_generate_contracts(message)
        elif action == "review_docs":
            await self._handle_review_docs(message)
        else:
            await self.send_response(
                message,
                {
                    "status": "error",
                    "error": f"Unknown action: {action}",
                },
            )

    async def _handle_write_api_docs(self, message: Message) -> None:
        """Handle API documentation writing request.

        Args:
            message: Request message
        """
        self._set_status(AgentStatus.BUSY)

        try:
            api_data = message.payload.get("api", {})

            docs = await self.write_api_docs(api_data)

            await self.send_response(
                message,
                {
                    "status": "success",
                    "api_documentation": {
                        "id": docs.id,
                        "title": docs.title,
                        "endpoints": list(docs.endpoints),
                        "authentication": docs.authentication,
                        "examples": list(docs.examples),
                        "error_codes": list(docs.error_codes),
                        "changelog": list(docs.changelog),
                        "created_at": docs.created_at,
                    },
                },
            )
        finally:
            self._set_status(AgentStatus.IDLE)

    async def _handle_create_spec(self, message: Message) -> None:
        """Handle specification creation request.

        Args:
            message: Request message
        """
        self._set_status(AgentStatus.BUSY)

        try:
            component_data = message.payload.get("component", {})

            spec = await self.create_spec(component_data)

            await self.send_response(
                message,
                {
                    "status": "success",
                    "specification": {
                        "id": spec.id,
                        "title": spec.title,
                        "type": spec.type.value,
                        "overview": spec.overview,
                        "requirements": spec.requirements,
                        "design": spec.design,
                        "implementation": spec.implementation,
                        "testing": spec.testing,
                        "status": spec.status.value,
                        "created_at": spec.created_at,
                    },
                },
            )
        finally:
            self._set_status(AgentStatus.IDLE)

    async def _handle_generate_contracts(self, message: Message) -> None:
        """Handle contract generation request.

        Args:
            message: Request message
        """
        self._set_status(AgentStatus.BUSY)

        try:
            interfaces_data = message.payload.get("interfaces", [])

            contracts = await self.generate_contracts(interfaces_data)

            await self.send_response(
                message,
                {
                    "status": "success",
                    "contracts": contracts,
                },
            )
        finally:
            self._set_status(AgentStatus.IDLE)

    async def _handle_review_docs(self, message: Message) -> None:
        """Handle documentation review request.

        Args:
            message: Request message
        """
        self._set_status(AgentStatus.BUSY)

        try:
            docs_data = message.payload.get("documentation", {})

            review = await self.review_docs(docs_data)

            await self.send_response(
                message,
                {
                    "status": "success",
                    "review": {
                        "id": review.id,
                        "doc_id": review.doc_id,
                        "reviewer_id": review.reviewer_id,
                        "status": review.status.value,
                        "feedback": review.feedback,
                        "issues": list(review.issues),
                        "suggestions": list(review.suggestions),
                        "approved": review.approved,
                        "created_at": review.created_at,
                    },
                },
            )
        finally:
            self._set_status(AgentStatus.IDLE)

    async def write_api_docs(self, api: dict[str, Any]) -> APIDocumentation:
        """Write API documentation.

        Args:
            api: API specification

        Returns:
            APIDocumentation object
        """
        # Generate comprehensive API documentation
        # In production, this would parse OpenAPI/Swagger specs
        docs = APIDocumentation.create(
            id=str(uuid.uuid4()),
            title=api.get("title", "API Documentation"),
            endpoints=[
                "GET /api/v1/users - List all users",
                "POST /api/v1/users - Create new user",
                "GET /api/v1/users/{id} - Get user by ID",
                "PUT /api/v1/users/{id} - Update user",
                "DELETE /api/v1/users/{id} - Delete user",
            ],
            authentication="Bearer token authentication via Authorization header",
            examples=[
                "curl -H 'Authorization: Bearer TOKEN' https://api.example.com/v1/users",
                "curl -X POST -H 'Content-Type: application/json' -d '{\"name\":\"John\"}' https://api.example.com/v1/users",
            ],
            error_codes=[
                "400 Bad Request - Invalid input",
                "401 Unauthorized - Missing or invalid token",
                "404 Not Found - Resource not found",
                "500 Internal Server Error - Server error",
            ],
            changelog=[
                "v1.0.0 - Initial release",
                "v1.1.0 - Added user endpoints",
            ],
        )

        return docs

    async def create_spec(self, component: dict[str, Any]) -> Specification:
        """Create technical specification.

        Args:
            component: Component to document

        Returns:
            Specification object
        """
        # Generate technical specification
        spec = Specification.create(
            id=str(uuid.uuid4()),
            title=component.get("name", "Component Specification"),
            type=DocType.TECHNICAL,
            overview=f"Technical specification for {component.get('name', 'component')}",
            requirements="Functional and non-functional requirements",
            design="Architecture and design decisions",
            implementation="Implementation details and code structure",
            testing="Testing strategy and test cases",
            status=DocStatus.DRAFT,
        )

        return spec

    async def generate_contracts(
        self, interfaces: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Generate code contracts from interfaces.

        Args:
            interfaces: List of interface definitions

        Returns:
            List of contract definitions
        """
        # Generate contracts for each interface
        contracts = []

        for interface in interfaces:
            contract = {
                "interface": interface.get("name", "IInterface"),
                "methods": [
                    {
                        "name": "method1",
                        "parameters": ["param1: str", "param2: int"],
                        "returns": "bool",
                        "description": "Method description",
                    }
                ],
                "preconditions": ["Input must be valid"],
                "postconditions": ["Output meets specification"],
                "invariants": ["State remains consistent"],
            }
            contracts.append(contract)

        return contracts

    async def review_docs(self, docs: dict[str, Any]) -> DocsReview:
        """Review documentation quality.

        Args:
            docs: Documentation to review

        Returns:
            DocsReview object
        """
        issues = []
        suggestions = []

        # Check for common documentation issues
        if not docs.get("title"):
            issues.append("Missing title")

        if not docs.get("overview"):
            issues.append("Missing overview section")

        # Provide suggestions
        suggestions.append("Add code examples")
        suggestions.append("Include diagrams for complex concepts")
        suggestions.append("Add troubleshooting section")

        # Determine approval
        approved = len(issues) == 0

        review = DocsReview.create(
            id=str(uuid.uuid4()),
            doc_id=docs.get("id", str(uuid.uuid4())),
            reviewer_id=self.agent_id,
            status=DocStatus.APPROVED if approved else DocStatus.REVIEW,
            feedback=f"Documentation review complete. Found {len(issues)} issues.",
            approved=approved,
            issues=issues,
            suggestions=suggestions,
        )

        return review


__all__ = ["SpecKitSpecialistAgent"]
