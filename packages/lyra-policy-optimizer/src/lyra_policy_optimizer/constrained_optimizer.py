"""Constrained policy optimization with feasibility checking."""

from __future__ import annotations

from dataclasses import dataclass

from .exceptions import ConstraintOptimizationError

from .policy_search import PolicyCandidate, SearchConfig, SearchResult, PolicySearch


@dataclass(frozen=True)
class ConstraintConfig:
    """Configuration for constrained optimization."""

    constraints: tuple[str, ...]
    constraint_bounds: tuple[tuple[float, float], ...]
    penalty_coef: float = 1.0
    feasibility_tolerance: float = 0.01


@dataclass(frozen=True)
class ConstraintViolation:
    """A single constraint violation record."""

    constraint: str
    required_range: tuple[float, float]
    actual_value: float
    violation_magnitude: float


@dataclass(frozen=True)
class ConstrainedResult:
    """Result of a constraint check on a policy."""

    policy: PolicyCandidate
    violations: tuple[ConstraintViolation, ...]
    feasible: bool
    penalty: float


class ConstrainedOptimizer:
    """Optimizer that enforces constraints during policy search."""

    _tolerance: float = 1e-9

    def __init__(self) -> None:
        self._constraints: dict[str, tuple[float, float]] = {}

    async def add_constraint(
        self, name: str, lower: float, upper: float
    ) -> None:
        """Register a new constraint."""
        if lower >= upper:
            raise ConstraintOptimizationError(
                f"invalid constraint '{name}': lower ({lower}) must be < upper ({upper})"
            )
        self._constraints[name] = (lower, upper)

    async def check_constraints(
        self, policy: PolicyCandidate
    ) -> ConstrainedResult:
        """Check a policy against all registered constraints."""
        if not self._constraints:
            raise ConstraintOptimizationError("no constraints registered")

        violations: list[ConstraintViolation] = []
        total_penalty = 0.0

        param_map = dict(policy.parameters)

        for name, (lower, upper) in self._constraints.items():
            actual = param_map.get(name)
            if actual is None:
                raise ConstraintOptimizationError(
                    f"constraint '{name}' not found in policy parameters"
                )

            violation_mag = 0.0
            if actual < lower - self._tolerance:
                violation_mag = lower - actual
            elif actual > upper + self._tolerance:
                violation_mag = actual - upper

            if violation_mag > 0:
                violations.append(
                    ConstraintViolation(
                        constraint=name,
                        required_range=(lower, upper),
                        actual_value=actual,
                        violation_magnitude=violation_mag,
                    )
                )
                total_penalty += violation_mag

        return ConstrainedResult(
            policy=policy,
            violations=tuple(violations),
            feasible=len(violations) == 0,
            penalty=total_penalty,
        )

    async def project_feasible(
        self, policy: PolicyCandidate
    ) -> PolicyCandidate:
        """Project a policy into the feasible region by clamping parameters."""
        if not self._constraints:
            raise ConstraintOptimizationError("no constraints registered")

        projected_params: list[tuple[str, float]] = []
        for name, value in policy.parameters:
            bounds = self._constraints.get(name)
            if bounds is not None:
                lower, upper = bounds
                value = max(lower, min(upper, value))
            projected_params.append((name, value))

        return PolicyCandidate(
            candidate_id=policy.candidate_id,
            parameters=tuple(projected_params),
            score=policy.score,
            uncertainty=policy.uncertainty,
            iteration_found=policy.iteration_found,
        )

    async def constrained_search(
        self,
        config: SearchConfig,
        constraints: ConstraintConfig,
    ) -> SearchResult:
        """Perform a policy search that respects constraints."""
        if len(constraints.constraints) != len(constraints.constraint_bounds):
            raise ConstraintOptimizationError(
                "constraints and constraint_bounds must have the same length"
            )

        for name, (lower, upper) in zip(
            constraints.constraints, constraints.constraint_bounds
        ):
            self._constraints[name] = (lower, upper)

        searcher = PolicySearch()
        result = await searcher.search_policy(config, "constrained")

        penalty = 0.0
        feasible_candidates: list[PolicyCandidate] = []
        for candidate in result.candidates:
            check = await self.check_constraints(candidate)
            if not check.feasible:
                projected = await self.project_feasible(candidate)
                adjusted_score = projected.score - constraints.penalty_coef * check.penalty
                adjusted = PolicyCandidate(
                    candidate_id=projected.candidate_id,
                    parameters=projected.parameters,
                    score=adjusted_score,
                    uncertainty=projected.uncertainty,
                    iteration_found=projected.iteration_found,
                )
                feasible_candidates.append(adjusted)
                penalty += check.penalty
            else:
                feasible_candidates.append(candidate)

        if feasible_candidates:
            best = max(feasible_candidates, key=lambda c: c.score)
        else:
            raise ConstraintOptimizationError(
                "no feasible candidates found after projection"
            )

        return SearchResult(
            best_policy=best,
            candidates=tuple(feasible_candidates),
            iterations=result.iterations,
            converged=result.converged,
            search_time_ms=result.search_time_ms,
        )
