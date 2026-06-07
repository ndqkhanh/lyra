"""Constraint-based safe generation — validate agents against hard and soft constraints."""

from __future__ import annotations

from dataclasses import dataclass

from .hyper_agent import HyperAgent


@dataclass(frozen=True)
class ConstraintSpec:
    """A single constraint specification for agent validation."""

    constraint_id: str
    description: str
    check_function: str
    severity: str = "hard"
    enabled: bool = True


@dataclass(frozen=True)
class ConstraintCheck:
    """Result of checking a single constraint against an agent."""

    constraint: ConstraintSpec
    passed: bool
    violations: tuple[str, ...]
    score_deduction: float = 0.0


@dataclass(frozen=True)
class ConstraintReport:
    """Aggregate report from validating an agent against constraints."""

    checks: tuple[ConstraintCheck, ...]
    all_passed: bool
    score_penalty: float
    recommendations: tuple[str, ...]


class ConstraintGenerator:
    """Generates and validates constraints against HyperAgent genomes."""

    def __init__(self) -> None:
        self._constraints: dict[str, ConstraintSpec] = {}

    async def add_constraint(
        self, description: str, severity: str = "hard"
    ) -> ConstraintSpec:
        """Add a new constraint and return its spec."""
        constraint_id = f"c-{len(self._constraints) + 1}"
        check_function = _description_to_check(description)
        spec = ConstraintSpec(
            constraint_id=constraint_id,
            description=description,
            check_function=check_function,
            severity=severity,
        )
        self._constraints[constraint_id] = spec
        return spec

    async def validate_agent(
        self,
        agent: HyperAgent,
        constraints: tuple[ConstraintSpec, ...],
    ) -> ConstraintReport:
        """Validate a single agent against given constraints."""
        checks: list[ConstraintCheck] = []
        total_penalty = 0.0
        recommendations: list[str] = []

        for constraint in constraints:
            if not constraint.enabled:
                checks.append(ConstraintCheck(
                    constraint=constraint,
                    passed=True,
                    violations=(),
                    score_deduction=0.0,
                ))
                continue

            passed, violations = _check_agent(agent, constraint)

            deduction = 0.0
            if not passed:
                if constraint.severity == "hard":
                    deduction = 0.5
                    recommendations.append(
                        f"Hard constraint '{constraint.description}' violated"
                    )
                elif constraint.severity == "soft":
                    deduction = 0.1
                    recommendations.append(
                        f"Soft constraint '{constraint.description}' should be addressed"
                    )
                total_penalty += deduction

            checks.append(ConstraintCheck(
                constraint=constraint,
                passed=passed,
                violations=tuple(violations),
                score_deduction=deduction,
            ))

        all_passed = all(c.passed for c in checks)
        return ConstraintReport(
            checks=tuple(checks),
            all_passed=all_passed,
            score_penalty=total_penalty,
            recommendations=tuple(recommendations),
        )

    async def generate_default_constraints(
        self,
    ) -> tuple[ConstraintSpec, ...]:
        """Generate a set of default constraints for agent validation."""
        defaults: list[tuple[str, str, str]] = [
            ("Agent must have at least one gene in genome", "hard", "min_genes"),
            ("Gene values must be within [0.0, 1.0] bounds", "hard", "gene_bounds"),
            ("Fitness should be non-negative", "hard", "non_negative_fitness"),
            ("Lineage should contain at least the agent ID", "soft", "lineage_minimal"),
            ("Agent should have a reasonable number of genes (<= 50)", "soft", "max_genes"),
        ]
        constraints: list[ConstraintSpec] = []
        for i, (desc, severity, check_fn) in enumerate(defaults):
            constraints.append(ConstraintSpec(
                constraint_id=f"default-c-{i + 1}",
                description=desc,
                check_function=check_fn,
                severity=severity,
            ))
        return tuple(constraints)

    async def filter_by_constraints(
        self,
        agents: tuple[HyperAgent, ...],
        constraints: tuple[ConstraintSpec, ...],
    ) -> tuple[HyperAgent, ...]:
        """Filter agents, returning only those passing all hard constraints."""
        if not agents:
            return ()

        filtered: list[HyperAgent] = []
        for agent in agents:
            report = await self.validate_agent(agent, constraints)
            hard_passed = all(
                c.passed
                for c in report.checks
                if c.constraint.severity == "hard"
            )
            if hard_passed:
                filtered.append(agent)

        return tuple(filtered)


def _description_to_check(description: str) -> str:
    """Convert a constraint description to a canonical check function name."""
    return description.lower().replace(" ", "_").replace("-", "_")[:64]


def _check_agent(
    agent: HyperAgent, constraint: ConstraintSpec
) -> tuple[bool, list[str]]:
    """Check an agent against a constraint spec, returning (passed, violations)."""
    violations: list[str] = []
    check_name = constraint.check_function

    if check_name == "min_genes":
        if len(agent.genome) < 1:
            violations.append("Genome is empty")

    elif check_name == "gene_bounds":
        for gene in agent.genome:
            if gene.value < gene.min_bound or gene.value > gene.max_bound:
                violations.append(
                    f"Gene '{gene.gene_id}' value {gene.value} out of bounds"
                )

    elif check_name == "non_negative_fitness":
        if agent.fitness < 0:
            violations.append(f"Fitness {agent.fitness} is negative")

    elif check_name == "lineage_minimal":
        if len(agent.lineage) < 1:
            violations.append("Lineage is empty")

    elif check_name == "max_genes":
        if len(agent.genome) > 50:
            violations.append(f"Genome size {len(agent.genome)} exceeds 50")

    return len(violations) == 0, violations
