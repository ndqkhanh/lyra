"""
Program Manager Skill - Multi-project program management.

Given program scope, produces:
- Program charter
- Project portfolio
- Resource allocation
- Risk management
- Stakeholder communication plan

Outputs structured program management plan.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ProjectStatus(StrEnum):
    """Project status."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    AT_RISK = "at_risk"
    COMPLETED = "completed"


@dataclass(frozen=True)
class Project:
    """Individual project in the program."""

    project_name: str
    objective: str
    status: ProjectStatus
    start_date: str
    end_date: str
    budget: str
    team_size: int
    dependencies: tuple[str, ...]


@dataclass(frozen=True)
class ResourceAllocation:
    """Resource allocation across projects."""

    resource_type: str
    total_available: int
    allocated: int
    utilization_percentage: str


@dataclass(frozen=True)
class ProgramRisk:
    """Program-level risk."""

    risk_id: str
    description: str
    impact: str
    probability: str
    mitigation: str
    owner: str


@dataclass(frozen=True)
class StakeholderComm:
    """Stakeholder communication plan."""

    stakeholder_group: str
    communication_frequency: str
    communication_method: str
    key_messages: tuple[str, ...]


@dataclass(frozen=True)
class ProgramPlan:
    """Complete program management plan."""

    program_name: str
    program_charter: str
    projects: tuple[Project, ...]
    resource_allocation: tuple[ResourceAllocation, ...]
    program_risks: tuple[ProgramRisk, ...]
    stakeholder_communication: tuple[StakeholderComm, ...]
    program_milestones: tuple[tuple[str, str], ...]


class ProgramManager:
    """Program management skill producing structured plans."""

    def run(self, input_data: dict) -> dict:
        """Run program planning.

        Args:
            input_data: Dictionary with keys:
                - program_description: Program description
                - program_name: Optional program name (default "Program")

        Returns:
            Dictionary with program plan data.
        """
        description = input_data.get("program_description", "")
        if not description:
            return {"error": "No program description provided"}

        program_name = input_data.get("program_name", "Program")

        charter = self._create_charter(description)
        projects = self._define_projects()
        resources = self._allocate_resources(projects)
        risks = self._identify_program_risks()
        stakeholder_comm = self._plan_stakeholder_communication()
        milestones = self._define_program_milestones()

        return ProgramPlan(
            program_name=program_name,
            program_charter=charter,
            projects=tuple(projects),
            resource_allocation=tuple(resources),
            program_risks=tuple(risks),
            stakeholder_communication=tuple(stakeholder_comm),
            program_milestones=tuple(milestones),
        ).__dict__ | {
            "projects": [p.__dict__ for p in projects],
            "resource_allocation": [r.__dict__ for r in resources],
            "program_risks": [r.__dict__ for r in risks],
            "stakeholder_communication": [s.__dict__ for s in stakeholder_comm],
        }

    @staticmethod
    def _create_charter(description: str) -> str:
        return (
            f"Program Charter: {description[:100]}... "
            f"This program aims to deliver strategic value through coordinated execution "
            f"of multiple interdependent projects. Success criteria include on-time delivery, "
            f"budget adherence, and stakeholder satisfaction."
        )

    @staticmethod
    def _define_projects() -> list[Project]:
        return [
            Project(
                project_name="Foundation Project",
                objective="Establish core infrastructure and architecture",
                status=ProjectStatus.IN_PROGRESS,
                start_date="2026-01-01",
                end_date="2026-03-31",
                budget="$500K",
                team_size=8,
                dependencies=(),
            ),
            Project(
                project_name="Feature Development Project",
                objective="Build core product features",
                status=ProjectStatus.NOT_STARTED,
                start_date="2026-04-01",
                end_date="2026-06-30",
                budget="$750K",
                team_size=12,
                dependencies=("Foundation Project",),
            ),
            Project(
                project_name="Integration Project",
                objective="Integrate with external systems",
                status=ProjectStatus.NOT_STARTED,
                start_date="2026-05-01",
                end_date="2026-08-31",
                budget="$400K",
                team_size=6,
                dependencies=("Foundation Project",),
            ),
            Project(
                project_name="Launch Project",
                objective="Production deployment and go-live",
                status=ProjectStatus.NOT_STARTED,
                start_date="2026-09-01",
                end_date="2026-10-31",
                budget="$300K",
                team_size=10,
                dependencies=("Feature Development Project", "Integration Project"),
            ),
        ]

    @staticmethod
    def _allocate_resources(projects: list[Project]) -> list[ResourceAllocation]:
        total_team = sum(p.team_size for p in projects)
        return [
            ResourceAllocation(
                resource_type="Software Engineers",
                total_available=20,
                allocated=18,
                utilization_percentage="90%",
            ),
            ResourceAllocation(
                resource_type="QA Engineers",
                total_available=5,
                allocated=4,
                utilization_percentage="80%",
            ),
            ResourceAllocation(
                resource_type="DevOps Engineers",
                total_available=3,
                allocated=3,
                utilization_percentage="100%",
            ),
            ResourceAllocation(
                resource_type="Product Managers",
                total_available=2,
                allocated=2,
                utilization_percentage="100%",
            ),
        ]

    @staticmethod
    def _identify_program_risks() -> list[ProgramRisk]:
        return [
            ProgramRisk(
                risk_id="PR-001",
                description="Resource contention across projects",
                impact="HIGH",
                probability="MEDIUM",
                mitigation="Implement resource allocation matrix and weekly sync meetings",
                owner="Program Manager",
            ),
            ProgramRisk(
                risk_id="PR-002",
                description="Dependency delays cascading across projects",
                impact="HIGH",
                probability="HIGH",
                mitigation="Build buffer time into schedules, identify critical path",
                owner="Program Manager",
            ),
            ProgramRisk(
                risk_id="PR-003",
                description="Budget overruns due to scope creep",
                impact="MEDIUM",
                probability="MEDIUM",
                mitigation="Strict change control process, monthly budget reviews",
                owner="Finance Lead",
            ),
        ]

    @staticmethod
    def _plan_stakeholder_communication() -> list[StakeholderComm]:
        return [
            StakeholderComm(
                stakeholder_group="Executive Sponsors",
                communication_frequency="Monthly",
                communication_method="Executive dashboard + steering committee meeting",
                key_messages=("Program status", "Budget vs actuals", "Key risks and mitigations"),
            ),
            StakeholderComm(
                stakeholder_group="Project Managers",
                communication_frequency="Weekly",
                communication_method="Program sync meeting",
                key_messages=("Cross-project dependencies", "Resource allocation", "Blockers"),
            ),
            StakeholderComm(
                stakeholder_group="Engineering Teams",
                communication_frequency="Bi-weekly",
                communication_method="All-hands meeting",
                key_messages=("Program vision", "Technical decisions", "Upcoming milestones"),
            ),
        ]

    @staticmethod
    def _define_program_milestones() -> list[tuple[str, str]]:
        return [
            ("2026-03-31", "Foundation complete, architecture approved"),
            ("2026-06-30", "Core features complete, integration testing started"),
            ("2026-08-31", "All integrations complete, UAT started"),
            ("2026-10-31", "Production launch, program closure"),
        ]
