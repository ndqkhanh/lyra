"""Phase 2.4b — Quality Arbiter.

Score-based quality gate that validates outputs against configurable
thresholds. If output quality falls below threshold, triggers a
revision loop (max revisions configurable).

Target: catch 90%+ of sub-threshold outputs before they reach users.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from enum import Enum


class QualityDimension(Enum):
    CORRECTNESS = "correctness"
    COMPLETENESS = "completeness"
    CONSISTENCY = "consistency"
    SAFETY = "safety"
    READABILITY = "readability"
    EFFICIENCY = "efficiency"
    IDIOMATIC = "idiomatic"          # Follows language conventions
    TESTABILITY = "testability"


class QualityStatus(Enum):
    PASSED = "passed"
    NEEDS_REVISION = "needs_revision"
    REJECTED = "rejected"


@dataclass(frozen=True)
class QualityScore:
    """Score for a single quality dimension."""

    dimension: QualityDimension
    score: float                        # 0.0–1.0
    weight: float                       # Relative importance
    reason: str                         # Why this score was assigned

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"Score must be 0.0–1.0, got {self.score}")


@dataclass(frozen=True)
class QualityReport:
    """Complete quality assessment of an output."""

    report_id: str
    output_preview: str                 # First 200 chars
    scores: tuple[QualityScore, ...]
    composite_score: float              # Weighted average
    status: QualityStatus
    threshold: float                    # The pass/fail threshold used
    revision_suggestions: tuple[str, ...]
    timestamp: float


@dataclass
class QualityArbiter:
    """Validates outputs against quality thresholds and drives revisions.

    Usage::

        arbiter = QualityArbiter()
        report = arbiter.evaluate(
            "def add(a,b): return a+b",
            context="Utility math functions module",
        )
        if report.status == QualityStatus.NEEDS_REVISION:
            # trigger revision loop
            revised = arbiter.revise(output, report, revision_fn)

    The arbiter uses configurable scoring functions for each dimension.
    Default scorers are heuristic-based; custom scorers can be registered
    for domain-specific quality checks.
    """

    threshold: float = 0.70
    max_revisions: int = 3
    _scorers: dict[QualityDimension, Callable[[str, str], float]] = field(
        default_factory=dict
    )
    _history: list[QualityReport] = field(default_factory=list)

    def evaluate(
        self,
        output: str,
        context: str = "",
        *,
        threshold: float | None = None,
        dimensions: Sequence[QualityDimension] | None = None,
    ) -> QualityReport:
        """Evaluate output quality across all dimensions.

        Args:
            output: The output text/code to evaluate.
            context: Optional context about the task.
            threshold: Override the default pass/fail threshold.
            dimensions: Subset of dimensions to check (default: all).

        Returns:
            QualityReport with composite score and status.
        """
        threshold = threshold if threshold is not None else self.threshold
        dims = list(dimensions) if dimensions else list(QualityDimension)

        scores: list[QualityScore] = []
        total_weight = 0.0
        weighted_sum = 0.0

        for dim in dims:
            scorer = self._scorers.get(dim, _DEFAULT_SCORERS.get(dim))
            if scorer is None:
                continue

            raw_score = scorer(output, context)
            weight = _DIMENSION_WEIGHTS.get(dim, 1.0)
            reason = _generate_reason(dim, raw_score)

            score = QualityScore(
                dimension=dim,
                score=round(raw_score, 4),
                weight=weight,
                reason=reason,
            )
            scores.append(score)
            weighted_sum += raw_score * weight
            total_weight += weight

        composite = round(weighted_sum / max(total_weight, 0.001), 4)

        if composite >= threshold:
            status = QualityStatus.PASSED
            suggestions: tuple[str, ...] = ()
        elif composite >= threshold * 0.5:
            status = QualityStatus.NEEDS_REVISION
            suggestions = tuple(
                s.reason for s in scores if s.score < threshold
            )
        else:
            status = QualityStatus.REJECTED
            suggestions = tuple(
                s.reason for s in scores if s.score < 0.5
            )

        report = QualityReport(
            report_id=f"qr-{uuid.uuid4().hex[:12]}",
            output_preview=output[:200],
            scores=tuple(scores),
            composite_score=composite,
            status=status,
            threshold=threshold,
            revision_suggestions=suggestions,
            timestamp=time.time(),
        )
        self._history.append(report)
        return report

    def revise(
        self,
        original: str,
        report: QualityReport,
        revision_fn: Callable[[str, tuple[str, ...]], str],
        context: str = "",
    ) -> tuple[str, QualityReport]:
        """Run the revision loop until quality passes or max revisions hit.

        Args:
            original: The original output.
            report: The initial quality report.
            revision_fn: Function that takes (output, suggestions) → revised.
            context: Task context for evaluation.

        Returns:
            Tuple of (final_output, final_report).
        """
        current = original
        current_report = report

        for _ in range(self.max_revisions):
            if current_report.status == QualityStatus.PASSED:
                break

            current = revision_fn(current, current_report.revision_suggestions)
            current_report = self.evaluate(current, context)

        return current, current_report

    def register_scorer(
        self,
        dimension: QualityDimension,
        scorer: Callable[[str, str], float],
    ) -> None:
        """Register a custom scoring function for a dimension."""
        self._scorers[dimension] = scorer

    def get_dimension_score(
        self,
        report: QualityReport,
        dimension: QualityDimension,
    ) -> float | None:
        """Extract a single dimension's score from a report."""
        for s in report.scores:
            if s.dimension == dimension:
                return s.score
        return None

    @property
    def history(self) -> tuple[QualityReport, ...]:
        return tuple(self._history)

    def clear_history(self) -> None:
        self._history.clear()

    @property
    def pass_rate(self) -> float:
        if not self._history:
            return 0.0
        passed = sum(1 for r in self._history if r.status == QualityStatus.PASSED)
        return passed / len(self._history)


# ── Default heuristic scorers ─────────────────────────────────────────

_DIMENSION_WEIGHTS: dict[QualityDimension, float] = {
    QualityDimension.CORRECTNESS: 2.0,
    QualityDimension.COMPLETENESS: 1.5,
    QualityDimension.CONSISTENCY: 1.0,
    QualityDimension.SAFETY: 2.0,
    QualityDimension.READABILITY: 1.0,
    QualityDimension.EFFICIENCY: 0.5,
    QualityDimension.IDIOMATIC: 0.5,
    QualityDimension.TESTABILITY: 1.0,
}


def _score_correctness(output: str, _context: str) -> float:
    """Heuristic correctness: checks for common issues."""
    stripped = output.strip()
    if not stripped:
        return 0.1
    score = 0.8
    if "TODO" in output or "FIXME" in output:
        score -= 0.2
    if "pass" in output and len(stripped.split("\n")) <= 2:
        score -= 0.3
    if stripped.endswith(":"):
        score -= 0.1
    if len(stripped) < 20:
        score -= 0.5
    return max(0.0, min(1.0, score))


def _score_completeness(output: str, _context: str) -> float:
    """Heuristic completeness: checks if output seems truncated."""
    stripped = output.strip()
    if not stripped:
        return 0.1
    score = 0.8
    if output.rstrip().endswith("..."):
        score -= 0.3
    if len(stripped) < 50:
        score -= 0.2
    if stripped.endswith(","):
        score -= 0.1
    return max(0.0, min(1.0, score))


def _score_consistency(output: str, _context: str) -> float:
    """Heuristic consistency: basic pattern checks."""
    score = 0.85
    lines = output.split("\n")
    indents = set()
    for line in lines:
        if line and not line.startswith(" "):
            stripped = len(line) - len(line.lstrip(" "))
            indents.add(stripped)
    if len(indents) > 5:
        score -= 0.15
    return max(0.0, min(1.0, score))


def _score_safety(output: str, _context: str) -> float:
    """Heuristic safety: flags dangerous patterns."""
    score = 1.0
    dangerous = [
        "rm -rf", "DROP TABLE", "DELETE FROM", "sudo ",
        "eval(", "exec(", "__import__", "subprocess",
    ]
    for pattern in dangerous:
        if pattern in output:
            score -= 0.3
    return max(0.0, min(1.0, score))


def _score_readability(output: str, _context: str) -> float:
    """Heuristic readability: checks structure and formatting."""
    score = 0.75
    lines = [l for l in output.split("\n") if l.strip()]
    if len(lines) > 5:
        score += 0.1
    avg_len = sum(len(l) for l in lines) / max(1, len(lines))
    if avg_len > 120:
        score -= 0.15
    if avg_len < 80:
        score += 0.05
    return max(0.0, min(1.0, score))


def _score_efficiency(output: str, _context: str) -> float:
    """Heuristic efficiency: basic complexity indicators."""
    score = 0.7
    nested_loops = output.count("for ") + output.count("while ")
    if nested_loops > 3:
        score -= 0.2
    if "O(n^2)" in output or "O(n**2)" in output:
        score -= 0.1
    return max(0.0, min(1.0, score))


def _score_idiomatic(output: str, _context: str) -> float:
    """Heuristic idiomatic check: language conventions."""
    score = 0.7
    if "def " in output and "->" in output:
        score += 0.1
    if "from __future__" in output:
        score += 0.05
    return max(0.0, min(1.0, score))


def _score_testability(output: str, _context: str) -> float:
    """Heuristic testability: checks for test-friendly patterns."""
    score = 0.65
    if "def " in output and "return" in output:
        score += 0.1
    if "print(" in output and "def " in output:
        score -= 0.15
    if "import " in output:
        score += 0.05
    return max(0.0, min(1.0, score))


def _generate_reason(dim: QualityDimension, score: float) -> str:
    if score >= 0.8:
        return f"{dim.value}: good ({score:.2f})"
    if score >= 0.6:
        return f"{dim.value}: adequate ({score:.2f})"
    return f"{dim.value}: needs improvement ({score:.2f})"


_DEFAULT_SCORERS: dict[QualityDimension, Callable[[str, str], float]] = {
    QualityDimension.CORRECTNESS: _score_correctness,
    QualityDimension.COMPLETENESS: _score_completeness,
    QualityDimension.CONSISTENCY: _score_consistency,
    QualityDimension.SAFETY: _score_safety,
    QualityDimension.READABILITY: _score_readability,
    QualityDimension.EFFICIENCY: _score_efficiency,
    QualityDimension.IDIOMATIC: _score_idiomatic,
    QualityDimension.TESTABILITY: _score_testability,
}


__all__ = [
    "QualityArbiter",
    "QualityDimension",
    "QualityReport",
    "QualityScore",
    "QualityStatus",
]
