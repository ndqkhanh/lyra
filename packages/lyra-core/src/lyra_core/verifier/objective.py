"""Phase 1 verifier: deterministic objective checks."""
from __future__ import annotations

import enum
from dataclasses import dataclass, field

from ..tdd.coverage import CoverageDelta, CoverageRegressionError, check_coverage_delta


class ObjectiveVerdict(str, enum.Enum):
    PASS = "pass"
    FAIL = "fail"
    NEEDS_MORE = "needs_more"


@dataclass
class ObjectiveEvidence:
    acceptance_tests_run: list[str] = field(default_factory=list)
    acceptance_tests_passed: list[str] = field(default_factory=list)
    expected_files_touched: list[str] = field(default_factory=list)
    forbidden_files_touched: list[str] = field(default_factory=list)
    coverage_before: float = 0.0
    coverage_after: float = 0.0
    coverage_tolerance_pct: float = 1.0


@dataclass
class ObjectiveResult:
    verdict: ObjectiveVerdict
    reason: str = ""


def verify_objective(ev: ObjectiveEvidence) -> ObjectiveResult:
    if not ev.acceptance_tests_run:
        return ObjectiveResult(
            verdict=ObjectiveVerdict.NEEDS_MORE,
            reason="no acceptance tests were run; cannot verify",
        )

    failing = set(ev.acceptance_tests_run) - set(ev.acceptance_tests_passed)
    if failing:
        return ObjectiveResult(
            verdict=ObjectiveVerdict.FAIL,
            reason=f"acceptance tests not green: {sorted(failing)}",
        )

    if ev.forbidden_files_touched:
        return ObjectiveResult(
            verdict=ObjectiveVerdict.FAIL,
            reason=f"forbidden files touched: {ev.forbidden_files_touched}",
        )

    if ev.coverage_before > 0.0:
        try:
            check_coverage_delta(
                CoverageDelta(
                    before=ev.coverage_before,
                    after=ev.coverage_after,
                    tolerance_pct=ev.coverage_tolerance_pct,
                )
            )
        except CoverageRegressionError as e:
            return ObjectiveResult(verdict=ObjectiveVerdict.FAIL, reason=str(e))

    return ObjectiveResult(
        verdict=ObjectiveVerdict.PASS,
        reason="all acceptance tests green; no forbidden files; coverage ok",
    )
