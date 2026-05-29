"""
Business Analyst Skill - Business analysis and requirements engineering.

Given requirements text, produces:
- Use cases with flow descriptions
- User stories (As a / I want / So that)
- Acceptance criteria
- Functional vs non-functional classification
- Gap analysis

Outputs structured business analysis document.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RequirementType(StrEnum):
    """Classification of requirements."""

    FUNCTIONAL = "functional"
    NON_FUNCTIONAL = "non_functional"
    BUSINESS = "business"
    STAKEHOLDER = "stakeholder"
    CONSTRAINT = "constraint"
    DOMAIN = "domain"


class Priority(StrEnum):
    """Requirement priority levels (MoSCoW)."""

    MUST_HAVE = "MUST"
    SHOULD_HAVE = "SHOULD"
    COULD_HAVE = "COULD"
    WONT_HAVE = "WONT"


class UseCaseStatus(StrEnum):
    """Use case maturity status."""

    DRAFT = "draft"
    REVIEWED = "reviewed"
    APPROVED = "approved"


@dataclass(frozen=True)
class UseCase:
    """A structured use case."""

    id: str
    title: str
    actors: tuple[str, ...]
    preconditions: tuple[str, ...]
    postconditions: tuple[str, ...]
    main_flow: tuple[str, ...]
    alternative_flows: tuple[tuple[str, ...], ...]
    priority: Priority
    status: UseCaseStatus


@dataclass(frozen=True)
class UserStory:
    """A user story in standard format."""

    id: str
    as_a: str
    i_want: str
    so_that: str
    acceptance_criteria: tuple[str, ...]
    story_points: int
    priority: Priority
    related_use_case: str | None


@dataclass(frozen=True)
class RequirementStatement:
    """A single requirement statement."""

    id: str
    description: str
    type: RequirementType
    priority: Priority
    source: str
    status: str


@dataclass(frozen=True)
class FunctionalRequirement:
    """A classified functional requirement."""

    id: str
    description: str
    module: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    rules: tuple[str, ...]


@dataclass(frozen=True)
class NonFunctionalRequirement:
    """A classified non-functional requirement."""

    id: str
    category: str
    description: str
    metric: str
    target: str
    measurement_method: str


@dataclass(frozen=True)
class GapItem:
    """A gap identified in the requirements."""

    id: str
    description: str
    impact: str
    recommendation: str
    priority: Priority


@dataclass(frozen=True)
class BAAnalysis:
    """Complete business analysis document."""

    title: str
    executive_summary: str
    use_cases: tuple[UseCase, ...]
    user_stories: tuple[UserStory, ...]
    functional_reqs: tuple[FunctionalRequirement, ...]
    non_functional_reqs: tuple[NonFunctionalRequirement, ...]
    gaps: tuple[GapItem, ...]
    recommendations: tuple[str, ...]


class BAAnalyzer:
    """Business analysis skill producing structured BA documents."""

    def run(self, input_data: dict) -> dict:
        """Run business analysis.

        Args:
            input_data: Dictionary with keys:
                - requirements: Raw requirements text
                - project_name: Optional project name (default "Business Analysis")

        Returns:
            Dictionary with business analysis data.
        """
        requirements = input_data.get("requirements", "")
        if not requirements:
            return {"error": "No requirements provided"}

        project = input_data.get("project_name", "Business Analysis")

        reqs_lower = requirements.lower()

        use_cases = self._build_use_cases(reqs_lower)
        user_stories = self._build_user_stories(reqs_lower, use_cases)
        func_reqs = self._classify_functional(reqs_lower)
        non_func_reqs = self._classify_non_functional(reqs_lower)
        gaps = self._gap_analysis(reqs_lower)
        recommendations = self._build_recommendations(reqs_lower)

        return BAAnalysis(
            title=project,
            executive_summary=self._build_executive_summary(requirements),
            use_cases=tuple(use_cases),
            user_stories=tuple(user_stories),
            functional_reqs=tuple(func_reqs),
            non_functional_reqs=tuple(non_func_reqs),
            gaps=tuple(gaps),
            recommendations=tuple(recommendations),
        ).__dict__ | {
            "use_cases": [uc.__dict__ for uc in use_cases],
            "user_stories": [us.__dict__ for us in user_stories],
            "functional_reqs": [fr.__dict__ for fr in func_reqs],
            "non_functional_reqs": [nfr.__dict__ for nfr in non_func_reqs],
            "gaps": [g.__dict__ for g in gaps],
        }

    @staticmethod
    def _build_executive_summary(requirements: str) -> str:
        max_len = 300
        if len(requirements) <= max_len:
            return requirements
        return requirements[:max_len].rsplit(".", 1)[0] + "."

    @staticmethod
    def _build_use_cases(requirements: str) -> list[UseCase]:
        has_auth = any(kw in requirements for kw in ["auth", "login", "user", "register"])
        has_data = any(kw in requirements for kw in ["data", "report", "search", "crud"])
        has_notify = any(kw in requirements for kw in ["notify", "email", "alert", "push"])

        use_cases: list[UseCase] = []

        if has_auth:
            use_cases.append(
                UseCase(
                    id="UC-001",
                    title="User Authentication",
                    actors=("User", "System"),
                    preconditions=("User is not logged in", "System is operational"),
                    postconditions=("User is authenticated", "Session token is issued"),
                    main_flow=(
                        "1. User enters credentials",
                        "2. System validates credentials",
                        "3. System creates session",
                        "4. System returns authenticated response",
                    ),
                    alternative_flows=(
                        ("2a. Invalid credentials: system returns error",),
                        ("2b. Account locked: system returns lockout message",),
                    ),
                    priority=Priority.MUST_HAVE,
                    status=UseCaseStatus.DRAFT,
                )
            )

        if has_data:
            use_cases.append(
                UseCase(
                    id="UC-002",
                    title="Data Management",
                    actors=("User", "System", "Database"),
                    preconditions=("User is authenticated", "Data store is accessible"),
                    postconditions=("Data is persisted", "User sees confirmation"),
                    main_flow=(
                        "1. User submits data via form/API",
                        "2. System validates input",
                        "3. System processes business rules",
                        "4. System persists data to store",
                        "5. System returns success response",
                    ),
                    alternative_flows=(
                        ("2a. Validation fails: system returns errors",),
                        ("4a. Store unavailable: system queues and retries",),
                    ),
                    priority=Priority.MUST_HAVE,
                    status=UseCaseStatus.DRAFT,
                )
            )

        if has_notify:
            use_cases.append(
                UseCase(
                    id="UC-003",
                    title="Notification Delivery",
                    actors=("System", "Notification Service", "User"),
                    preconditions=("Notification event triggered", "User preferences loaded"),
                    postconditions=("Notification delivered", "Delivery status logged"),
                    main_flow=(
                        "1. System detects trigger event",
                        "2. System resolves user preferences",
                        "3. System formats notification",
                        "4. Notification service delivers message",
                        "5. System logs delivery status",
                    ),
                    alternative_flows=(
                        ("4a. Delivery fails: system retries 3x",),
                        ("4b. Channel unavailable: fallback to email",),
                    ),
                    priority=Priority.SHOULD_HAVE,
                    status=UseCaseStatus.DRAFT,
                )
            )

        return use_cases or [
            UseCase(
                id="UC-001",
                title="Core System Operation",
                actors=("User", "System"),
                preconditions=("System is operational",),
                postconditions=("Operation completed",),
                main_flow=(
                    "1. User initiates action",
                    "2. System processes request",
                    "3. System returns result",
                ),
                alternative_flows=(),
                priority=Priority.MUST_HAVE,
                status=UseCaseStatus.DRAFT,
            )
        ]

    @staticmethod
    def _build_user_stories(requirements: str, use_cases: list[UseCase]) -> list[UserStory]:
        stories: list[UserStory] = [
            UserStory(
                id="US-001",
                as_a="User",
                i_want="to log in with my credentials",
                so_that="I can access the system securely",
                acceptance_criteria=(
                    "Login form accepts username/email and password",
                    "Invalid credentials show clear error message",
                    "Session persists for 24 hours",
                    "Rate limiting prevents brute force attacks",
                ),
                story_points=5,
                priority=Priority.MUST_HAVE,
                related_use_case="UC-001" if any(uc.id == "UC-001" for uc in use_cases) else None,
            ),
            UserStory(
                id="US-002",
                as_a="User",
                i_want="to create and manage data records",
                so_that="I can store and retrieve information",
                acceptance_criteria=(
                    "CRUD operations available for all entities",
                    "Input validated before submission",
                    "Changes reflected immediately after confirmation",
                    "Audit trail maintained for all changes",
                ),
                story_points=8,
                priority=Priority.MUST_HAVE,
                related_use_case="UC-002" if any(uc.id == "UC-002" for uc in use_cases) else None,
            ),
            UserStory(
                id="US-003",
                as_a="System Administrator",
                i_want="to view system logs and metrics",
                so_that="I can monitor system health and troubleshoot issues",
                acceptance_criteria=(
                    "Dashboard shows key metrics (uptime, errors, latency)",
                    "Logs filterable by severity, service, and time range",
                    "Export functionality for log data",
                    "Alert configuration for threshold breaches",
                ),
                story_points=8,
                priority=Priority.SHOULD_HAVE,
                related_use_case=None,
            ),
            UserStory(
                id="US-004",
                as_a="End User",
                i_want="the system to respond within 2 seconds",
                so_that="I can work efficiently without waiting",
                acceptance_criteria=(
                    "P95 response time under 2 seconds for all endpoints",
                    "Page load time under 3 seconds",
                    "Feedback shown for operations taking > 1 second",
                ),
                story_points=5,
                priority=Priority.MUST_HAVE,
                related_use_case=None,
            ),
            UserStory(
                id="US-005",
                as_a="User",
                i_want="to receive notifications about important events",
                so_that="I can stay informed without actively checking",
                acceptance_criteria=(
                    "Notifications delivered within 30 seconds of event",
                    "User can configure notification preferences",
                    "Notifications available via email, in-app, and optionally SMS",
                ),
                story_points=5,
                priority=Priority.COULD_HAVE,
                related_use_case="UC-003" if any(uc.id == "UC-003" for uc in use_cases) else None,
            ),
        ]
        return stories

    @staticmethod
    def _classify_functional(requirements: str) -> list[FunctionalRequirement]:
        return [
            FunctionalRequirement(
                id="FR-001",
                description="User authentication and session management",
                module="Auth",
                inputs=("username", "password", "MFA token"),
                outputs=("JWT/Session token", "User profile"),
                rules=(
                    "Password must meet complexity requirements",
                    "MFA enforced for admin accounts",
                    "Session expires after 24h inactivity",
                ),
            ),
            FunctionalRequirement(
                id="FR-002",
                description="Data CRUD operations with validation",
                module="Data Management",
                inputs=("Entity data", "Query parameters"),
                outputs=("Persisted records", "Query results"),
                rules=(
                    "All inputs validated server-side",
                    "Soft delete for critical entities",
                    "Pagination enforced for list endpoints",
                ),
            ),
            FunctionalRequirement(
                id="FR-003",
                description="Role-based access control (RBAC)",
                module="Authorization",
                inputs=("User role", "Resource identifier", "Action"),
                outputs=("Access grant/deny decision",),
                rules=(
                    "Roles: Admin, Editor, Viewer",
                    "Permissions defined per resource-action pair",
                    "Audit log for all access decisions",
                ),
            ),
            FunctionalRequirement(
                id="FR-004",
                description="Audit logging for all state changes",
                module="Audit",
                inputs=("User identity", "Action", "Before/after state"),
                outputs=("Audit log entry",),
                rules=(
                    "All mutating operations logged",
                    "Logs immutable after creation",
                    "Retention period: 90 days",
                ),
            ),
        ]

    @staticmethod
    def _classify_non_functional(requirements: str) -> list[NonFunctionalRequirement]:
        return [
            NonFunctionalRequirement(
                id="NFR-001",
                category="Performance",
                description="API response time must be under 2 seconds",
                metric="P95 latency",
                target="< 2000ms",
                measurement_method="Distributed tracing (OpenTelemetry)",
            ),
            NonFunctionalRequirement(
                id="NFR-002",
                category="Availability",
                description="System must be highly available",
                metric="Uptime percentage",
                target="99.9% (8.76h downtime/year max)",
                measurement_method="Uptime monitoring (Pingdom / CloudWatch)",
            ),
            NonFunctionalRequirement(
                id="NFR-003",
                category="Scalability",
                description="System must handle traffic spikes",
                metric="Concurrent users",
                target="10x baseline without degradation",
                measurement_method="Load testing (k6 / Locust)",
            ),
            NonFunctionalRequirement(
                id="NFR-004",
                category="Security",
                description="All data encrypted at rest and in transit",
                metric="Encryption coverage",
                target="100%",
                measurement_method="Security scan (bandit / Trivy)",
            ),
            NonFunctionalRequirement(
                id="NFR-005",
                category="Usability",
                description="UI must be responsive and accessible",
                metric="Lighthouse score",
                target="> 90 on performance, accessibility, best practices",
                measurement_method="Automated Lighthouse CI",
            ),
            NonFunctionalRequirement(
                id="NFR-006",
                category="Maintainability",
                description="Codebase must be maintainable",
                metric="Test coverage",
                target="> 80%",
                measurement_method="pytest --cov",
            ),
        ]

    @staticmethod
    def _gap_analysis(requirements: str) -> list[GapItem]:
        gaps: list[GapItem] = []

        if "performance" not in requirements:
            gaps.append(
                GapItem(
                    id="GAP-001",
                    description="No performance requirements specified",
                    impact="Risk of performance issues in production",
                    recommendation="Define P95/P99 latency targets and throughput requirements",
                    priority=Priority.MUST_HAVE,
                )
            )

        if "security" not in requirements:
            gaps.append(
                GapItem(
                    id="GAP-002",
                    description="Security requirements not explicitly defined",
                    impact="Potential security vulnerabilities",
                    recommendation=(
                        "Add authentication, authorization, and data protection requirements"
                    ),
                    priority=Priority.MUST_HAVE,
                )
            )

        if "backup" not in requirements and "disaster" not in requirements:
            gaps.append(
                GapItem(
                    id="GAP-003",
                    description="Disaster recovery and backup requirements missing",
                    impact="Data loss risk in case of system failure",
                    recommendation="Define RPO/RTO targets and backup strategy",
                    priority=Priority.SHOULD_HAVE,
                )
            )

        if "monitoring" not in requirements and "observability" not in requirements:
            gaps.append(
                GapItem(
                    id="GAP-004",
                    description="No monitoring or observability requirements",
                    impact="Blind to production issues",
                    recommendation="Add logging, metrics, and alerting requirements",
                    priority=Priority.SHOULD_HAVE,
                )
            )

        if "compliance" not in requirements and "regulatory" not in requirements:
            gaps.append(
                GapItem(
                    id="GAP-005",
                    description="Compliance requirements not addressed",
                    impact="Legal and regulatory risk",
                    recommendation=(
                        "Identify applicable regulations (GDPR, HIPAA, SOC2) and add requirements"
                    ),
                    priority=Priority.COULD_HAVE,
                )
            )

        return gaps

    @staticmethod
    def _build_recommendations(requirements: str) -> list[str]:
        return [
            "Prioritize MUST requirements for MVP and defer COULD to later releases",
            "Create acceptance criteria for every user story before sprint planning",
            "Involve QA in requirements review to ensure testability",
            "Maintain a requirements traceability matrix for audit purposes",
            "Review requirements with stakeholders bi-weekly to catch drift early",
            "Use BDD (Given/When/Then) to transform use cases into executable scenarios",
        ]
