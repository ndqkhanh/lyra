"""
PM Planner Skill - Project management planning and analysis.

Given a project description, produces:
- WBS (work breakdown structure)
- Milestone timeline
- Risk register with mitigation
- Stakeholder analysis
- Sprint planning suggestions

Outputs structured project management plan.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RiskLevel(StrEnum):
    """Risk severity levels."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RiskCategory(StrEnum):
    """Risk category classifications."""

    TECHNICAL = "technical"
    SCHEDULE = "schedule"
    RESOURCE = "resource"
    BUDGET = "budget"
    EXTERNAL = "external"
    OPERATIONAL = "operational"
    SECURITY = "security"
    LEGAL = "legal"


class StakeholderType(StrEnum):
    """Stakeholder classification types."""

    EXECUTIVE_SPONSOR = "executive_sponsor"
    PRODUCT_OWNER = "product_owner"
    TECH_LEAD = "tech_lead"
    END_USER = "end_user"
    REGULATOR = "regulator"
    VENDOR = "vendor"
    SUPPORT = "support"


@dataclass(frozen=True)
class WorkPackage:
    """A single work package in the WBS."""

    id: str
    name: str
    description: str
    estimated_hours: int
    dependencies: tuple[str, ...]
    assigned_role: str
    deliverables: tuple[str, ...]


@dataclass(frozen=True)
class WBS:
    """Work Breakdown Structure."""

    phases: tuple[tuple[str, tuple[WorkPackage, ...]], ...]
    total_estimated_hours: int


@dataclass(frozen=True)
class Milestone:
    """A project milestone."""

    name: str
    week: int
    description: str
    acceptance_criteria: str
    dependencies: tuple[str, ...]
    deliverables: tuple[str, ...]


@dataclass(frozen=True)
class RiskEntry:
    """A single risk entry."""

    id: str
    description: str
    category: RiskCategory
    likelihood: str
    impact: str
    risk_level: RiskLevel
    mitigation: str
    contingency: str
    owner: str


@dataclass(frozen=True)
class Stakeholder:
    """A project stakeholder."""

    name: str
    type: StakeholderType
    interest: str
    influence: str
    engagement_strategy: str
    communication_frequency: str


@dataclass(frozen=True)
class SprintSuggestion:
    """Suggested sprint plan."""

    sprint_number: int
    goal: str
    work_package_ids: tuple[str, ...]
    estimated_velocity: str
    risks: tuple[str, ...]


@dataclass(frozen=True)
class PMPlan:
    """Complete project management plan."""

    project_name: str
    description: str
    wbs: WBS
    milestones: tuple[Milestone, ...]
    risk_register: tuple[RiskEntry, ...]
    stakeholders: tuple[Stakeholder, ...]
    sprint_plan: tuple[SprintSuggestion, ...]
    recommendations: tuple[str, ...]


class PMPlanner:
    """Project management planning skill."""

    def run(self, input_data: dict) -> dict:
        """Run project management planning.

        Args:
            input_data: Dictionary with keys:
                - project_description: Description of the project
                - project_name: Optional project name (default "Project")
                - team_size: Optional team size (default 5)
                - sprint_duration: Optional sprint duration in weeks (default 2)

        Returns:
            Dictionary with project management plan data.
        """
        description = input_data.get("project_description", "")
        if not description:
            return {"error": "No project description provided"}

        project = input_data.get("project_name", "Project")
        team_size = int(input_data.get("team_size", 5))
        sprint_duration = int(input_data.get("sprint_duration", 2))

        reqs_lower = description.lower()

        wbs = self._build_wbs(reqs_lower, project)
        milestones = self._build_milestones(wbs, reqs_lower)
        risks = self._build_risk_register(reqs_lower)
        stakeholders = self._build_stakeholders(reqs_lower)
        sprint_plan = self._build_sprint_plan(
            wbs, milestones, sprint_duration, team_size
        )
        recommendations = self._build_recommendations(reqs_lower, team_size)

        return PMPlan(
            project_name=project,
            description=description,
            wbs=wbs,
            milestones=tuple(milestones),
            risk_register=tuple(risks),
            stakeholders=tuple(stakeholders),
            sprint_plan=tuple(sprint_plan),
            recommendations=tuple(recommendations),
        ).__dict__ | {
            "wbs": self._serialize_wbs(wbs),
            "milestones": [m.__dict__ for m in milestones],
            "risk_register": [r.__dict__ for r in risks],
            "stakeholders": [s.__dict__ for s in stakeholders],
            "sprint_plan": [s.__dict__ for s in sprint_plan],
        }

    @staticmethod
    def _serialize_wbs(wbs: WBS) -> dict:
        return {
            "phases": [
                {
                    "phase_name": phase_name,
                    "packages": [p.__dict__ for p in packages],
                }
                for phase_name, packages in wbs.phases
            ],
            "total_estimated_hours": wbs.total_estimated_hours,
        }

    @staticmethod
    def _build_wbs(requirements: str, project: str) -> WBS:
        phases: list[tuple[str, tuple[WorkPackage, ...]]] = [
            (
                "Discovery & Planning",
                (
                    WorkPackage("WP-001", "Requirements Gathering",
                                "Collect and document functional and non-functional requirements",
                                40, (), "Product Manager",
                                ("PRD document", "User stories", "Acceptance criteria")),
                    WorkPackage("WP-002", "Technical Architecture",
                                "Design system architecture, tech stack, and data model",
                                60, ("WP-001",), "Tech Lead",
                                ("Architecture doc", "ERD", "API specification")),
                    WorkPackage("WP-003", "Project Setup",
                                "Set up repository, CI/CD, development environment",
                                30, ("WP-002",), "DevOps Engineer",
                                ("CI/CD pipeline", "Infrastructure as code", "Dev environment")),
                ),
            ),
            (
                "Core Development",
                (
                    WorkPackage("WP-004", "Data Layer",
                                "Implement database schema, migrations, and data access",
                                80, ("WP-002", "WP-003"), "Backend Engineer",
                                ("Database schema", "Migration scripts", "Repository layer")),
                    WorkPackage("WP-005", "API Development",
                                "Implement REST/gRPC APIs and business logic",
                                120, ("WP-004",), "Backend Engineer",
                                ("API endpoints", "Business logic", "Integration tests")),
                    WorkPackage("WP-006", "Frontend Development",
                                "Implement UI components and pages",
                                120, ("WP-002", "WP-003"), "Frontend Engineer",
                                ("UI components", "Pages", "E2E tests")),
                ),
            ),
            (
                "Integration & Testing",
                (
                    WorkPackage("WP-007", "Integration Testing",
                                "Test end-to-end flows and fix integration issues",
                                60, ("WP-005", "WP-006"), "QA Engineer",
                                ("Integration test suite", "Test report")),
                    WorkPackage("WP-008", "Performance Testing",
                                "Load test, profile, and optimize critical paths",
                                40, ("WP-007",), "Performance Engineer",
                                ("Load test results", "Optimization report")),
                    WorkPackage("WP-009", "Security Audit",
                                "Security review, penetration testing, vulnerability fix",
                                40, ("WP-007",), "Security Engineer",
                                ("Security audit report", "Remediation plan")),
                ),
            ),
            (
                "Deployment & Launch",
                (
                    WorkPackage("WP-010", "Staging Deployment",
                                "Deploy to staging, conduct UAT",
                                30, ("WP-007", "WP-008", "WP-009"), "DevOps Engineer",
                                ("Staging environment", "UAT sign-off")),
                    WorkPackage("WP-011", "Production Deployment",
                                "Deploy to production with rollout plan",
                                40, ("WP-010",), "DevOps Engineer",
                                ("Production deployment", "Rollback plan")),
                    WorkPackage("WP-012", "Documentation & Training",
                                "Write user docs, API docs, conduct team training",
                                40, ("WP-005", "WP-006"), "Tech Writer",
                                ("User guide", "API docs", "Training sessions")),
                ),
            ),
        ]

        total_hours = sum(
            wp.estimated_hours
            for _, packages in phases
            for wp in packages
        )
        return WBS(phases=tuple(phases), total_estimated_hours=total_hours)

    @staticmethod
    def _build_milestones(wbs: WBS, requirements: str) -> list[Milestone]:
        return [
            Milestone("M1: Requirements Signed Off", 2,
                      "All requirements documented and approved",
                      "PRD reviewed and signed by stakeholders",
                      (), ("PRD", "User story map")),
            Milestone("M2: Architecture Approved", 4,
                      "Technical architecture design completed",
                      "Architecture review passed",
                      ("M1",), ("Architecture doc", "Tech stack decision")),
            Milestone("M3: Core Features Complete", 10,
                      "All core features implemented and unit tested",
                      "80% test coverage, all core features passing",
                      ("M2",), ("Feature set", "Test suite")),
            Milestone("M4: Integration Complete", 13,
                      "All integrations tested end-to-end",
                      "Integration tests pass, performance benchmarks met",
                      ("M3",), ("Integration test report", "Performance report")),
            Milestone("M5: Production Launch", 16,
                      "System deployed to production",
                      "Production deployment successful, smoke tests pass",
                      ("M4",), ("Production system", "Monitoring dashboards")),
        ]

    @staticmethod
    def _build_risk_register(requirements: str) -> list[RiskEntry]:
        risks: list[RiskEntry] = [
            RiskEntry(
                id="R-001",
                description="Scope creep due to changing requirements",
                category=RiskCategory.SCHEDULE,
                likelihood="HIGH",
                impact="HIGH",
                risk_level=RiskLevel.HIGH,
                mitigation="Implement formal change control process; prioritize MVP scope",
                contingency="Allocate 20% buffer in timeline for scope changes",
                owner="Product Manager",
            ),
            RiskEntry(
                id="R-002",
                description="Key team member unavailability",
                category=RiskCategory.RESOURCE,
                likelihood="MEDIUM",
                impact="HIGH",
                risk_level=RiskLevel.HIGH,
                mitigation="Cross-train team members; document knowledge",
                contingency="Engage backup contractor; redistribute work",
                owner="Engineering Manager",
            ),
            RiskEntry(
                id="R-003",
                description="Technical debt accumulation under schedule pressure",
                category=RiskCategory.TECHNICAL,
                likelihood="MEDIUM",
                impact="MEDIUM",
                risk_level=RiskLevel.MEDIUM,
                mitigation="Allocate 20% time for refactoring in each sprint",
                contingency="Schedule dedicated hardening sprint before launch",
                owner="Tech Lead",
            ),
            RiskEntry(
                id="R-004",
                description="Integration delays with third-party services",
                category=RiskCategory.EXTERNAL,
                likelihood="MEDIUM",
                impact="MEDIUM",
                risk_level=RiskLevel.MEDIUM,
                mitigation="Engage vendor early; stub interfaces for parallel development",
                contingency="Implement fallback/mock versions of external services",
                owner="Tech Lead",
            ),
            RiskEntry(
                id="R-005",
                description="Performance issues under expected load",
                category=RiskCategory.TECHNICAL,
                likelihood="LOW",
                impact="HIGH",
                risk_level=RiskLevel.MEDIUM,
                mitigation="Design for scale from day one; conduct early load tests",
                contingency="Add horizontal auto-scaling; optimize critical paths",
                owner="Performance Engineer",
            ),
            RiskEntry(
                id="R-006",
                description="Budget overruns due to unforeseen complexity",
                category=RiskCategory.BUDGET,
                likelihood="MEDIUM",
                impact="HIGH",
                risk_level=RiskLevel.HIGH,
                mitigation="Weekly budget reviews; granular task estimation",
                contingency="Maintain 15% contingency budget",
                owner="Project Manager",
            ),
        ]

        if "security" in requirements or "compliance" in requirements:
            risks.append(
                RiskEntry(
                    id="R-007",
                    description="Security/compliance requirements not met",
                    category=RiskCategory.LEGAL,
                    likelihood="MEDIUM",
                    impact="CRITICAL",
                    risk_level=RiskLevel.CRITICAL,
                    mitigation="Engage security team from day one; automated compliance checks",
                    contingency="Dedicated security remediation sprint",
                    owner="Security Lead",
                )
            )

        return risks

    @staticmethod
    def _build_stakeholders(requirements: str) -> list[Stakeholder]:
        return [
            Stakeholder(
                name="Executive Sponsor",
                type=StakeholderType.EXECUTIVE_SPONSOR,
                interest="Strategic alignment, ROI, timeline",
                influence="HIGH",
                engagement_strategy="Monthly steering committee; quarterly business review",
                communication_frequency="Monthly",
            ),
            Stakeholder(
                name="Product Owner",
                type=StakeholderType.PRODUCT_OWNER,
                interest="Feature completeness, quality, user satisfaction",
                influence="HIGH",
                engagement_strategy="Daily standups; sprint review demos",
                communication_frequency="Daily",
            ),
            Stakeholder(
                name="Tech Lead",
                type=StakeholderType.TECH_LEAD,
                interest="Technical quality, architecture, team productivity",
                influence="HIGH",
                engagement_strategy="Technical design reviews; architecture decisions",
                communication_frequency="Daily",
            ),
            Stakeholder(
                name="End Users",
                type=StakeholderType.END_USER,
                interest="Usability, reliability, performance",
                influence="MEDIUM",
                engagement_strategy="User research sessions; beta testing program",
                communication_frequency="Per sprint",
            ),
            Stakeholder(
                name="Support Team",
                type=StakeholderType.SUPPORT,
                interest="Documentation, known issues, deployment timeline",
                influence="LOW",
                engagement_strategy="Pre-launch training; handover documentation",
                communication_frequency="Per milestone",
            ),
            Stakeholder(
                name="QA Team",
                type=StakeholderType.SUPPORT,
                interest="Test coverage, bug tracking, release quality",
                influence="MEDIUM",
                engagement_strategy="Shared test plan; bug triage sessions",
                communication_frequency="Daily",
            ),
        ]

    @staticmethod
    def _build_sprint_plan(
        wbs: WBS, milestones: list[Milestone], sprint_duration: int, team_size: int
    ) -> list[SprintSuggestion]:
        estimated_velocity = team_size * sprint_duration * 5 * 6  # ~6 hrs productive per day
        sprint_suggestions: list[SprintSuggestion] = []

        for i, (phase_name, packages) in enumerate(wbs.phases):
            package_ids = tuple(p.id for p in packages)
            # Divide phase across 1-2 sprints depending on total hours
            phase_hours = sum(p.estimated_hours for p in packages)
            num_sprints = max(1, round(phase_hours / estimated_velocity))

            for j in range(num_sprints):
                sprint_number = i * 2 + j + 1
                sprint_suggestions.append(
                    SprintSuggestion(
                        sprint_number=sprint_number,
                        goal=f"{phase_name} (Sprint {j + 1}/{num_sprints})",
                        work_package_ids=package_ids,
                        estimated_velocity=f"{estimated_velocity} story points",
                        risks=("Scope creep", "Dependencies"),
                    )
                )

        return sprint_suggestions

    @staticmethod
    def _build_recommendations(
        requirements: str, team_size: int
    ) -> list[str]:
        return [
            f"Recommended team size: {team_size} (+1 for buffer)",
            "Use daily standups (15 min) for team sync",
            "Conduct sprint retrospectives every 2 weeks",
            "Maintain a prioritized backlog with MoSCoW prioritization",
            "Implement CI/CD from day one to reduce integration risk",
            "Allocate 20% time for technical debt reduction",
            "Use pair programming for complex features",
            "Document architectural decisions (ADRs) as they are made",
        ]
