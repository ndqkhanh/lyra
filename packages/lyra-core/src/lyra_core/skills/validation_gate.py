"""Phase 3.1 — Skill Validation Gates.

4-gate validation pipeline for skill candidates before they are
admitted to the registry:

  Gate 1: Syntax & Structure  (threshold: 1.0, auto-fix)
  Gate 2: Semantic Correctness (threshold: 0.95, auto-fix)
  Gate 3: Performance Benchmark (threshold: 0.80)
  Gate 4: Safety Screener       (threshold: 0.98)

A skill must pass all 4 gates to be production-ready.
Skills that fail Gates 3 or 4 are flagged for human review.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum

from .gates.benchmark_runner import BenchmarkRunner
from .gates.safety_screener import SafetyScreener
from .gates.semantic_checker import SemanticChecker
from .gates.syntax_validator import SyntaxValidator


class GateNumber(Enum):
    GATE_1 = 1  # Syntax & Structure
    GATE_2 = 2  # Semantic Correctness
    GATE_3 = 3  # Performance Benchmark
    GATE_4 = 4  # Safety Screener


class GateStatus(Enum):
    PASSED = "passed"
    AUTO_FIXED = "auto_fixed"
    NEEDS_REVIEW = "needs_review"
    REJECTED = "rejected"


@dataclass(frozen=True)
class GateResult:
    """Result from a single validation gate."""

    gate: GateNumber
    status: GateStatus
    score: float  # 0.0–1.0
    threshold: float
    issues: tuple[str, ...]  # Issues found
    auto_fixes_applied: tuple[str, ...]  # Fixes auto-applied
    recommendation: str
    timestamp: float


@dataclass(frozen=True)
class ValidationReport:
    """Complete 4-gate validation result for a skill candidate."""

    report_id: str
    skill_name: str
    skill_triggers: tuple[str, ...]
    skill_body: str  # The skill implementation
    gate_results: tuple[GateResult, ...]
    passed: bool
    needs_human_review: bool
    composite_score: float
    summary: str


# ── Gate Adapters (backward compatibility) ───────────────────────────


def _gate1_syntax(skill_name: str, skill_triggers: tuple[str, ...], skill_body: str) -> GateResult:
    """Gate 1: Validate syntax, structure, and metadata."""
    validator = SyntaxValidator()
    result = validator.validate(skill_name, skill_triggers, skill_body)

    status = GateStatus.PASSED if result.passed else GateStatus.REJECTED
    if not result.passed and result.score >= 0.75:
        status = GateStatus.AUTO_FIXED
    elif not result.passed and result.score >= 0.5:
        status = GateStatus.NEEDS_REVIEW

    return GateResult(
        gate=GateNumber.GATE_1,
        status=status,
        score=result.score,
        threshold=validator.THRESHOLD,
        issues=result.issues,
        auto_fixes_applied=result.auto_fixes_applied,
        recommendation=result.recommendation,
        timestamp=time.time(),
    )


def _gate2_semantic(skill_body: str) -> GateResult:
    """Gate 2: Validate semantic correctness of the skill."""
    checker = SemanticChecker()
    result = checker.validate("", (), skill_body)

    status = GateStatus.PASSED if result.passed else GateStatus.REJECTED
    if not result.passed and result.score >= 0.8:
        status = GateStatus.AUTO_FIXED
    elif not result.passed and result.score >= 0.6:
        status = GateStatus.NEEDS_REVIEW

    return GateResult(
        gate=GateNumber.GATE_2,
        status=status,
        score=result.score,
        threshold=checker.THRESHOLD,
        issues=result.issues,
        auto_fixes_applied=result.auto_fixes_applied,
        recommendation=result.recommendation,
        timestamp=time.time(),
    )


def _gate3_performance(skill_body: str, skill_triggers: tuple[str, ...]) -> GateResult:
    """Gate 3: Run performance benchmarks on the skill."""
    runner = BenchmarkRunner()
    result = runner.validate("", skill_triggers, skill_body)

    status = GateStatus.PASSED if result.passed else GateStatus.REJECTED
    if not result.passed and result.score >= 0.6:
        status = GateStatus.NEEDS_REVIEW

    return GateResult(
        gate=GateNumber.GATE_3,
        status=status,
        score=result.score,
        threshold=runner.THRESHOLD,
        issues=result.issues,
        auto_fixes_applied=(),
        recommendation=result.recommendation,
        timestamp=time.time(),
    )


def _gate4_safety(skill_body: str) -> GateResult:
    """Gate 4: Screen skill for safety violations."""
    screener = SafetyScreener()
    result = screener.validate("", (), skill_body)

    status = GateStatus.PASSED if result.passed else GateStatus.REJECTED
    if not result.passed and result.score >= 0.9:
        status = GateStatus.NEEDS_REVIEW

    return GateResult(
        gate=GateNumber.GATE_4,
        status=status,
        score=result.score,
        threshold=screener.THRESHOLD,
        issues=result.issues,
        auto_fixes_applied=(),
        recommendation=result.recommendation,
        timestamp=time.time(),
    )


# ── Pipeline ──────────────────────────────────────────────────────────


@dataclass
class SkillValidationPipeline:
    """4-gate validation pipeline for skill candidates.

    Usage::

        pipeline = SkillValidationPipeline()
        report = pipeline.validate(
            skill_name="my-skill",
            skill_triggers=("trigger1",),
            skill_body='''#!/bin/bash
            echo "hello"
            ''',
        )
        if report.passed:
            registry.register(skill)
    """

    gate1_threshold: float = 1.0
    gate2_threshold: float = 0.95
    gate3_threshold: float = 0.80
    gate4_threshold: float = 0.98
    _history: list[ValidationReport] = field(default_factory=list)
    _syntax_validator: SyntaxValidator = field(default_factory=SyntaxValidator, init=False)
    _semantic_checker: SemanticChecker = field(default_factory=SemanticChecker, init=False)
    _benchmark_runner: BenchmarkRunner = field(default_factory=BenchmarkRunner, init=False)
    _safety_screener: SafetyScreener = field(default_factory=SafetyScreener, init=False)

    def validate(
        self,
        skill_name: str,
        skill_triggers: tuple[str, ...],
        skill_body: str,
        *,
        skip_performance: bool = False,
        skip_safety: bool = False,
    ) -> ValidationReport:
        """Run a skill candidate through all 4 validation gates.

        Args:
            skill_name: Name of the skill.
            skill_triggers: Trigger phrases for the skill.
            skill_body: The skill implementation (Python or shell).
            skip_performance: Skip Gate 3 (for quick dev iterations).
            skip_safety: Skip Gate 4 (NOT recommended for production).

        Returns:
            ValidationReport with per-gate results and overall status.
        """
        results: list[GateResult] = []

        r1 = _gate1_syntax(skill_name, skill_triggers, skill_body)
        results.append(r1)

        if r1.status == GateStatus.REJECTED:
            report = self._build_report(skill_name, skill_triggers, skill_body, tuple(results))
            self._history.append(report)
            return report

        r2 = _gate2_semantic(skill_body)
        results.append(r2)

        if not skip_performance:
            r3 = _gate3_performance(skill_body, skill_triggers)
            results.append(r3)

        if not skip_safety:
            r4 = _gate4_safety(skill_body)
            results.append(r4)

        report = self._build_report(skill_name, skill_triggers, skill_body, tuple(results))
        self._history.append(report)
        return report

    def _build_report(
        self,
        skill_name: str,
        skill_triggers: tuple[str, ...],
        skill_body: str,
        results: tuple[GateResult, ...],
    ) -> ValidationReport:
        passed = all(r.status in (GateStatus.PASSED, GateStatus.AUTO_FIXED) for r in results)
        needs_review = any(r.status == GateStatus.NEEDS_REVIEW for r in results)
        composite = sum(r.score for r in results) / len(results) if results else 0.0

        if passed and not needs_review:
            summary = (
                f"Skill '{skill_name}' passed all {len(results)} gates (score={composite:.3f})."
            )
        elif needs_review:
            summary =(
                f"Skill '{skill_name}' needs human review ({len(results)} gates, score="
                f"{composite:.3f})."
            )
        else:
            summary = (
                f"Skill '{skill_name}' rejected ({len(results)} gates, score={composite:.3f})."
            )

        return ValidationReport(
            report_id=f"vr-{uuid.uuid4().hex[:12]}",
            skill_name=skill_name,
            skill_triggers=skill_triggers,
            skill_body=skill_body,
            gate_results=results,
            passed=passed,
            needs_human_review=needs_review,
            composite_score=round(composite, 4),
            summary=summary,
        )

    @property
    def history(self) -> tuple[ValidationReport, ...]:
        return tuple(self._history)

    def clear_history(self) -> None:
        self._history.clear()

    @property
    def pass_rate(self) -> float:
        if not self._history:
            return 0.0
        return sum(1 for r in self._history if r.passed) / len(self._history)


__all__ = [
    "GateNumber",
    "GateResult",
    "GateStatus",
    "SkillValidationPipeline",
    "ValidationReport",
]
