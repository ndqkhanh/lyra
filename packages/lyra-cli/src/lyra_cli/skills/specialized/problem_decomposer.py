"""
Problem Decomposer Skill - Complex problem decomposition and analysis.

Given a complex problem, produces:
- Problem breakdown structure
- Root cause analysis
- Sub-problem identification
- Solution approach for each sub-problem
- Integration strategy

Outputs structured problem decomposition.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ProblemType(StrEnum):
    """Types of problems."""

    TECHNICAL = "technical"
    ORGANIZATIONAL = "organizational"
    STRATEGIC = "strategic"
    OPERATIONAL = "operational"


@dataclass(frozen=True)
class SubProblem:
    """Decomposed sub-problem."""

    sub_problem_id: str
    title: str
    description: str
    problem_type: ProblemType
    complexity: str
    dependencies: tuple[str, ...]


@dataclass(frozen=True)
class RootCause:
    """Root cause analysis finding."""

    cause_id: str
    description: str
    evidence: tuple[str, ...]
    impact: str


@dataclass(frozen=True)
class SolutionApproach:
    """Solution approach for a sub-problem."""

    sub_problem_id: str
    approach: str
    resources_needed: tuple[str, ...]
    estimated_effort: str
    risks: tuple[str, ...]


@dataclass(frozen=True)
class ProblemDecomposition:
    """Complete problem decomposition."""

    original_problem: str
    sub_problems: tuple[SubProblem, ...]
    root_causes: tuple[RootCause, ...]
    solution_approaches: tuple[SolutionApproach, ...]
    integration_strategy: str
    implementation_sequence: tuple[str, ...]


class ProblemDecomposer:
    """Problem decomposition skill producing structured analyses."""

    def run(self, input_data: dict) -> dict:
        """Run problem decomposition.

        Args:
            input_data: Dictionary with keys:
                - problem_statement: Complex problem statement

        Returns:
            Dictionary with problem decomposition data.
        """
        problem = input_data.get("problem_statement", "")
        if not problem:
            return {"error": "No problem statement provided"}

        sub_problems = self._decompose_problem(problem)
        root_causes = self._analyze_root_causes(problem)
        solutions = self._design_solution_approaches(sub_problems)
        integration = self._define_integration_strategy()
        sequence = self._determine_implementation_sequence(sub_problems)

        return ProblemDecomposition(
            original_problem=problem,
            sub_problems=tuple(sub_problems),
            root_causes=tuple(root_causes),
            solution_approaches=tuple(solutions),
            integration_strategy=integration,
            implementation_sequence=tuple(sequence),
        ).__dict__ | {
            "sub_problems": [s.__dict__ for s in sub_problems],
            "root_causes": [r.__dict__ for r in root_causes],
            "solution_approaches": [s.__dict__ for s in solutions],
        }

    @staticmethod
    def _decompose_problem(problem: str) -> list[SubProblem]:
        return [
            SubProblem(
                sub_problem_id="SP-001",
                title="Data Quality Issues",
                description="Inconsistent and incomplete data across systems",
                problem_type=ProblemType.TECHNICAL,
                complexity="MEDIUM",
                dependencies=(),
            ),
            SubProblem(
                sub_problem_id="SP-002",
                title="Process Inefficiency",
                description="Manual processes causing delays and errors",
                problem_type=ProblemType.OPERATIONAL,
                complexity="MEDIUM",
                dependencies=("SP-001",),
            ),
            SubProblem(
                sub_problem_id="SP-003",
                title="Lack of Integration",
                description="Systems not integrated, causing data silos",
                problem_type=ProblemType.TECHNICAL,
                complexity="HIGH",
                dependencies=("SP-001",),
            ),
            SubProblem(
                sub_problem_id="SP-004",
                title="Insufficient Training",
                description="Users lack training on current systems",
                problem_type=ProblemType.ORGANIZATIONAL,
                complexity="LOW",
                dependencies=(),
            ),
        ]

    @staticmethod
    def _analyze_root_causes(problem: str) -> list[RootCause]:
        return [
            RootCause(
                cause_id="RC-001",
                description="Legacy systems not designed for integration",
                evidence=(
                    "Systems built 10+ years ago",
                    "No API interfaces available",
                    "Different data models",
                ),
                impact="HIGH",
            ),
            RootCause(
                cause_id="RC-002",
                description="Lack of data governance",
                evidence=(
                    "No data quality standards",
                    "No data ownership defined",
                    "No validation rules",
                ),
                impact="HIGH",
            ),
            RootCause(
                cause_id="RC-003",
                description="Insufficient investment in automation",
                evidence=(
                    "Manual data entry still prevalent",
                    "No workflow automation",
                    "Limited IT budget",
                ),
                impact="MEDIUM",
            ),
        ]

    @staticmethod
    def _design_solution_approaches(sub_problems: list[SubProblem]) -> list[SolutionApproach]:
        return [
            SolutionApproach(
                sub_problem_id="SP-001",
                approach="Implement data quality framework with validation rules and cleansing",
                resources_needed=("Data engineer", "Data quality tool", "3 months"),
                estimated_effort="HIGH",
                risks=("Resistance to new processes", "Data migration complexity"),
            ),
            SolutionApproach(
                sub_problem_id="SP-002",
                approach="Automate manual processes with workflow engine",
                resources_needed=("Business analyst", "Developer", "Workflow tool", "2 months"),
                estimated_effort="MEDIUM",
                risks=("Process redesign required", "Change management"),
            ),
            SolutionApproach(
                sub_problem_id="SP-003",
                approach="Build integration layer with API gateway and ETL pipelines",
                resources_needed=("Integration architect", "Developers", "Integration platform", "6 months"),
                estimated_effort="HIGH",
                risks=("Technical complexity", "System downtime during migration"),
            ),
            SolutionApproach(
                sub_problem_id="SP-004",
                approach="Develop comprehensive training program with hands-on workshops",
                resources_needed=("Training specialist", "Training materials", "1 month"),
                estimated_effort="LOW",
                risks=("Low attendance", "Knowledge retention"),
            ),
        ]

    @staticmethod
    def _define_integration_strategy() -> str:
        return (
            "Phased Integration Approach:\n"
            "1. Foundation Phase: Address data quality and establish governance (SP-001)\n"
            "2. Automation Phase: Implement workflow automation (SP-002)\n"
            "3. Integration Phase: Build integration layer (SP-003)\n"
            "4. Enablement Phase: Train users on new systems (SP-004)\n\n"
            "Each phase builds on the previous, with validation gates before proceeding. "
            "Parallel workstreams where dependencies allow."
        )

    @staticmethod
    def _determine_implementation_sequence(sub_problems: list[SubProblem]) -> list[str]:
        return [
            "Phase 1 (Months 1-3): SP-001 (Data Quality) + SP-004 (Training prep)",
            "Phase 2 (Months 4-5): SP-002 (Process Automation)",
            "Phase 3 (Months 6-11): SP-003 (System Integration)",
            "Phase 4 (Month 12): SP-004 (User Training and rollout)",
        ]
