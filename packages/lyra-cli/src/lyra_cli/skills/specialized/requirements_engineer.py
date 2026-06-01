"""
Requirements Engineer Skill - Requirements elicitation and specification.

Given stakeholder needs, produces:
- Requirements specification document
- Use case diagrams
- Requirements traceability matrix
- Validation criteria
- Change management process

Outputs structured requirements engineering plan.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RequirementCategory(StrEnum):
    """Requirement categories."""

    FUNCTIONAL = "functional"
    PERFORMANCE = "performance"
    SECURITY = "security"
    USABILITY = "usability"
    RELIABILITY = "reliability"
    MAINTAINABILITY = "maintainability"


@dataclass(frozen=True)
class Requirement:
    """Detailed requirement specification."""

    req_id: str
    category: RequirementCategory
    title: str
    description: str
    rationale: str
    priority: str
    source: str
    acceptance_criteria: tuple[str, ...]
    dependencies: tuple[str, ...]


@dataclass(frozen=True)
class UseCase:
    """Use case specification."""

    use_case_id: str
    name: str
    actor: str
    preconditions: tuple[str, ...]
    main_flow: tuple[str, ...]
    alternative_flows: tuple[str, ...]
    postconditions: tuple[str, ...]


@dataclass(frozen=True)
class TraceabilityEntry:
    """Requirements traceability entry."""

    requirement_id: str
    design_element: str
    test_case: str
    status: str


@dataclass(frozen=True)
class RequirementsEngineeringPlan:
    """Complete requirements engineering plan."""

    project_name: str
    requirements: tuple[Requirement, ...]
    use_cases: tuple[UseCase, ...]
    traceability_matrix: tuple[TraceabilityEntry, ...]
    validation_criteria: tuple[str, ...]
    change_process: tuple[str, ...]


class RequirementsEngineer:
    """Requirements engineering skill producing structured plans."""

    def run(self, input_data: dict) -> dict:
        """Run requirements engineering.

        Args:
            input_data: Dictionary with keys:
                - stakeholder_needs: Stakeholder needs description
                - project_name: Optional project name (default "RE Project")

        Returns:
            Dictionary with requirements engineering plan data.
        """
        needs = input_data.get("stakeholder_needs", "")
        if not needs:
            return {"error": "No stakeholder needs provided"}

        project_name = input_data.get("project_name", "RE Project")
        needs_lower = needs.lower()

        requirements = self._elicit_requirements(needs_lower)
        use_cases = self._define_use_cases()
        traceability = self._build_traceability_matrix(requirements)
        validation = self._define_validation_criteria()
        change_process = self._define_change_process()

        return RequirementsEngineeringPlan(
            project_name=project_name,
            requirements=tuple(requirements),
            use_cases=tuple(use_cases),
            traceability_matrix=tuple(traceability),
            validation_criteria=tuple(validation),
            change_process=tuple(change_process),
        ).__dict__ | {
            "requirements": [r.__dict__ for r in requirements],
            "use_cases": [u.__dict__ for u in use_cases],
            "traceability_matrix": [t.__dict__ for t in traceability],
        }

    @staticmethod
    def _elicit_requirements(needs: str) -> list[Requirement]:
        return [
            Requirement(
                req_id="REQ-001",
                category=RequirementCategory.FUNCTIONAL,
                title="User Authentication",
                description="System shall authenticate users via username/password or SSO",
                rationale="Secure access control required for sensitive data",
                priority="P0",
                source="Security Team",
                acceptance_criteria=(
                    "Support username/password authentication",
                    "Support SAML 2.0 SSO",
                    "Enforce password complexity rules",
                    "Lock account after 5 failed attempts",
                ),
                dependencies=(),
            ),
            Requirement(
                req_id="REQ-002",
                category=RequirementCategory.PERFORMANCE,
                title="Response Time",
                description="System shall respond to user requests within 2 seconds (p95)",
                rationale="User experience requirement for interactive application",
                priority="P1",
                source="Product Team",
                acceptance_criteria=(
                    "95% of requests complete within 2 seconds",
                    "Measured under normal load conditions",
                    "Includes database and external API calls",
                ),
                dependencies=("REQ-001",),
            ),
            Requirement(
                req_id="REQ-003",
                category=RequirementCategory.SECURITY,
                title="Data Encryption",
                description="System shall encrypt all sensitive data at rest and in transit",
                rationale="Compliance requirement (GDPR, HIPAA)",
                priority="P0",
                source="Compliance Team",
                acceptance_criteria=(
                    "TLS 1.3 for data in transit",
                    "AES-256 for data at rest",
                    "Key rotation every 90 days",
                ),
                dependencies=(),
            ),
        ]

    @staticmethod
    def _define_use_cases() -> list[UseCase]:
        return [
            UseCase(
                use_case_id="UC-001",
                name="User Login",
                actor="End User",
                preconditions=(
                    "User has valid credentials",
                    "System is available",
                ),
                main_flow=(
                    "1. User navigates to login page",
                    "2. User enters username and password",
                    "3. System validates credentials",
                    "4. System creates session",
                    "5. User is redirected to dashboard",
                ),
                alternative_flows=(
                    "3a. Invalid credentials: Display error message, allow retry",
                    "3b. Account locked: Display message, provide unlock instructions",
                ),
                postconditions=(
                    "User is authenticated",
                    "Session is created",
                    "User has access to authorized features",
                ),
            ),
            UseCase(
                use_case_id="UC-002",
                name="Submit Request",
                actor="End User",
                preconditions=(
                    "User is authenticated",
                    "User has permission to submit requests",
                ),
                main_flow=(
                    "1. User navigates to request form",
                    "2. User fills in required fields",
                    "3. User uploads supporting documents",
                    "4. User submits request",
                    "5. System validates request",
                    "6. System assigns request ID",
                    "7. System sends confirmation email",
                ),
                alternative_flows=(
                    "5a. Validation fails: Display errors, allow correction",
                    "7a. Email fails: Log error, display confirmation on screen",
                ),
                postconditions=(
                    "Request is saved in system",
                    "Request ID is generated",
                    "User receives confirmation",
                ),
            ),
        ]

    @staticmethod
    def _build_traceability_matrix(requirements: list[Requirement]) -> list[TraceabilityEntry]:
        return [
            TraceabilityEntry(
                requirement_id="REQ-001",
                design_element="AuthenticationService, UserRepository",
                test_case="TC-001, TC-002, TC-003",
                status="Implemented",
            ),
            TraceabilityEntry(
                requirement_id="REQ-002",
                design_element="CachingLayer, DatabaseOptimization",
                test_case="TC-010, TC-011",
                status="In Progress",
            ),
            TraceabilityEntry(
                requirement_id="REQ-003",
                design_element="EncryptionService, KeyManagementService",
                test_case="TC-020, TC-021",
                status="Planned",
            ),
        ]

    @staticmethod
    def _define_validation_criteria() -> list[str]:
        return [
            "All requirements have unique IDs and are traceable",
            "All requirements have clear acceptance criteria",
            "All requirements are testable and verifiable",
            "All requirements are approved by stakeholders",
            "All requirements are prioritized (P0/P1/P2)",
            "All dependencies are identified and documented",
            "All requirements are consistent and non-conflicting",
        ]

    @staticmethod
    def _define_change_process() -> list[str]:
        return [
            "1. Change request submitted via change request form",
            "2. Requirements engineer reviews for completeness",
            "3. Impact analysis conducted (scope, schedule, cost)",
            "4. Change control board reviews and approves/rejects",
            "5. If approved, requirements document is updated",
            "6. All stakeholders notified of change",
            "7. Traceability matrix updated",
            "8. Change logged in change register",
        ]
