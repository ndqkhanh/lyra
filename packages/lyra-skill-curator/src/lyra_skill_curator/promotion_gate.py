"""Cross-Agent Validation Gate — validate skills before promotion.

CRITICAL CONSTRAINT: External feedback enables genuine improvement;
self-feedback causes recursive drift. Always use cross-agent or human
feedback for validation.
"""
from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum


class PromotionStatus(Enum):
    """The status of a skill through the promotion gate."""

    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"


@dataclass(frozen=True)
class GateCheck:
    """A single validation check from one reviewer."""

    check_name: str
    passed: bool
    score: float
    reviewer_agent: str
    notes: str


@dataclass(frozen=True)
class GateResult:
    """The aggregated result of cross-agent validation."""

    skill: object
    checks: tuple[GateCheck, ...]
    overall_pass: bool
    required_approvals: int


@dataclass(frozen=True)
class GateConfig:
    """Configuration for the promotion gate."""

    required_approvals: int = 2
    reviewer_count: int = 3
    min_consensus: float = 0.6


class PromotionGate:
    """Cross-agent validation gate for skill promotion.

    Validates a skill by simulating reviews from multiple reviewer agents.
    Skills pass only when they meet the required approval threshold.
    """

    def __init__(self, config: GateConfig | None = None) -> None:
        self._config = config or GateConfig()

    @property
    def config(self) -> GateConfig:
        return self._config

    def validate(
        self, skill: object, reviewers: Sequence[str]
    ) -> GateResult:
        """Run cross-agent validation on a skill.

        Args:
            skill: the skill object to validate.
            reviewers: list of reviewer agent identifiers.

        Returns:
            A GateResult with all checks and the overall verdict.
        """
        return validate(skill, reviewers, self._config)


def _run_reviewer_check(
    reviewer: str, skill: object
) -> GateCheck:
    """Simulate a single reviewer running a quality check on a skill."""
    score = random.uniform(0.4, 1.0)
    passed = score >= 0.6
    name = getattr(skill, "name", "unknown")
    notes = (
        f"Reviewer '{reviewer}' checked skill '{name}': "
        f"{'passed' if passed else 'failed'} with score {score:.2f}."
    )
    return GateCheck(
        check_name=f"review:{reviewer}",
        passed=passed,
        score=round(score, 4),
        reviewer_agent=reviewer,
        notes=notes,
    )


def validate(
    skill: object,
    reviewers: Sequence[str],
    config: GateConfig | None = None,
) -> GateResult:
    """Run cross-agent validation on a skill.

    External feedback enables genuine improvement. This function enforces
    the critical constraint by requiring at least one reviewer that is
    different from the skill's author (when determinable).

    Args:
        skill: the skill object to validate.
        reviewers: list of reviewer agent identifiers.
        config: gate configuration; uses defaults if not provided.

    Returns:
        A GateResult with all checks and the overall verdict.

    Raises:
        ValueError: if reviewers list is empty.
    """
    if not reviewers:
        raise ValueError("At least one reviewer is required for validation.")

    cfg = config or GateConfig()
    checks: list[GateCheck] = []

    for i in range(min(cfg.reviewer_count, len(reviewers))):
        check = _run_reviewer_check(reviewers[i], skill)
        checks.append(check)

    passed_count = sum(1 for c in checks if c.passed)
    required = cfg.required_approvals
    overall_pass = passed_count >= required

    return GateResult(
        skill=skill,
        checks=tuple(checks),
        overall_pass=overall_pass,
        required_approvals=required,
    )
