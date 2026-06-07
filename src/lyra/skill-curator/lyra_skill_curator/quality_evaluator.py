"""Quality Evaluation — score skills on clarity, completeness, correctness, usefulness, and
testability."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum


class QualityCriteria(Enum):
    """Dimensions along which a skill is evaluated."""

    CLARITY = "clarity"
    COMPLETENESS = "completeness"
    CORRECTNESS = "correctness"
    USEFULNESS = "usefulness"
    TESTABILITY = "testability"


@dataclass(frozen=True)
class QualityScore:
    """Quality scores across all evaluation dimensions."""

    overall: float
    clarity: float
    completeness: float
    correctness: float
    usefulness: float
    testability: float


@dataclass(frozen=True)
class EvaluationConfig:
    """Configuration thresholds for quality evaluation."""

    min_clarity: float = 0.5
    min_correctness: float = 0.5
    pass_threshold: float = 0.6


class QualityEvaluator:
    """Evaluates the quality of skill candidates.

    Analysis is based on heuristic properties of the skill's name, description, trigger patterns,
    and body content.
    """

    def __init__(self, config: EvaluationConfig | None = None) -> None:
        self._config = config or EvaluationConfig()

    @property
    def config(self) -> EvaluationConfig:
        return self._config

    def evaluate(self, skill: object) -> QualityScore:
        """Evaluate a single skill candidate.

        Args:
            skill: the object to evaluate (expected to have name, description,
                   trigger_patterns, and body attributes).

        Returns:
            A QualityScore with dimension scores and overall.
        """
        return evaluate(skill)

    def batch_evaluate(self, skills: Sequence[object]) -> list[QualityScore]:
        """Evaluate multiple skill candidates in batch."""
        return batch_evaluate(skills)

    def rank_by_quality(self, skills: Sequence[object]) -> list[tuple[object, QualityScore]]:
        """Rank skill candidates by their overall quality score."""
        return rank_by_quality(skills)


def _score_clarity(name: str | None, description: str | None) -> float:
    """Score clarity based on name and description length and content."""
    score = 0.5
    if name and len(name) > 3:
        score += 0.2
    if description and len(description) > 20:
        score += 0.2
    if description and " " in (description or ""):
        score += 0.1
    return min(score, 1.0)


def _score_completeness(body: str | None) -> float:
    """Score completeness based on body length and structure."""
    score = 0.3
    if body:
        score += min(len(body) / 200, 0.4)
        if "def " in body or "class " in body:
            score += 0.15
        if "return" in body or "->" in body:
            score += 0.15
    return min(score, 1.0)


def _score_correctness(trigger_patterns: tuple[str, ...]) -> float:
    """Score correctness by evaluating the number of trigger patterns."""
    if not trigger_patterns:
        return 0.3
    score = min(len(trigger_patterns) * 0.2, 0.8)
    return min(score + 0.2, 1.0)


def _score_usefulness(name: str | None, description: str | None) -> float:
    """Score usefulness based on name and description content."""
    score = 0.4
    if name:
        score += min(len(name) * 0.02, 0.2)
    if description:
        score += min(len(description) * 0.005, 0.2)
        if any(
            kw in (description or "").lower()
            for kw in ("extract", "generate", "analyze", "validate", "convert")
        ):
            score += 0.2
    return min(score, 1.0)


def _score_testability(body: str | None) -> float:
    """Score testability based on body content."""
    score = 0.3
    if body:
        score += min(len(body) / 300, 0.3)
        if "def " in body:
            score += 0.2
        if "return" in body:
            score += 0.2
    return min(score, 1.0)


def _safe_getattr(obj: object, name: str, default: str = "") -> str:
    """Safely extract a string attribute from an object."""
    val = getattr(obj, name, default)
    if val is None:
        return ""
    return str(val)


def _safe_getattr_tuple(obj: object, name: str, default: tuple[str, ...] = ()) -> tuple[str, ...]:
    """Safely extract a tuple attribute from an object."""
    val = getattr(obj, name, default)
    if val is None:
        return default
    if isinstance(val, tuple):
        return val
    return default


def evaluate(skill: object) -> QualityScore:
    """Evaluate a single skill candidate against quality criteria.

    Args:
        skill: an object with attributes name, description, trigger_patterns,
               and body.

    Returns:
        A QualityScore with dimension scores between 0 and 1.
    """
    name = _safe_getattr(skill, "name")
    description = _safe_getattr(skill, "description")
    trigger_patterns = _safe_getattr_tuple(skill, "trigger_patterns")
    body = _safe_getattr(skill, "body")

    clarity = _score_clarity(name, description)
    completeness = _score_completeness(body)
    correctness = _score_correctness(trigger_patterns)
    usefulness = _score_usefulness(name, description)
    testability = _score_testability(body)

    overall_raw = (clarity + completeness + correctness + usefulness + testability) / 5.0
    overall = min(overall_raw, 1.0)

    return QualityScore(
        overall=round(overall, 4),
        clarity=round(clarity, 4),
        completeness=round(completeness, 4),
        correctness=round(correctness, 4),
        usefulness=round(usefulness, 4),
        testability=round(testability, 4),
    )


def batch_evaluate(skills: Sequence[object]) -> list[QualityScore]:
    """Evaluate multiple skill candidates in batch.

    Args:
        skills: a sequence of skill objects.

    Returns:
        A list of QualityScore objects, one per skill.
    """
    return [evaluate(s) for s in skills]


def rank_by_quality(
    skills: Sequence[object],
) -> list[tuple[object, QualityScore]]:
    """Rank skill candidates by their overall quality score (descending).

    Args:
        skills: a sequence of skill objects.

    Returns:
        A list of (skill, score) tuples sorted by overall quality.
    """
    scored = [(s, evaluate(s)) for s in skills]
    scored.sort(key=lambda pair: pair[1].overall, reverse=True)
    return scored
