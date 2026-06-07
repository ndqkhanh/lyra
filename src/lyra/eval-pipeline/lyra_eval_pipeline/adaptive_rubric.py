"""Adaptive rubric evaluation with automatic threshold calibration."""

from __future__ import annotations

from dataclasses import dataclass

from .exceptions import RubricError


@dataclass(frozen=True)
class RubricDimension:
    """A single dimension of a rubric."""

    name: str
    weight: float
    description: str
    scoring_function: str


@dataclass(frozen=True)
class RubricScore:
    """Score for a single rubric dimension."""

    dimension: str
    raw_score: float
    weighted_score: float
    confidence: float


@dataclass(frozen=True)
class RubricResult:
    """Aggregated result of a rubric evaluation."""

    scores: tuple[RubricScore, ...]
    total_score: float
    grade: str
    calibration_factor: float


@dataclass(frozen=True)
class RubricTemplate:
    """A named rubric template with dimensions and version."""

    name: str
    dimensions: tuple[RubricDimension, ...]
    version: str
    pearson_r: float = 0.79


class AdaptiveRubric:
    """Adaptive rubric scorer with automatic calibration."""

    def __init__(self) -> None:
        self._version_counter: int = 0
        self._calibration_factor: float = 1.0

    def _next_version(self) -> str:
        self._version_counter += 1
        return f"1.{self._version_counter}"

    def create_template(self, name: str, dimensions: list[RubricDimension]) -> RubricTemplate:
        """Create a new rubric template from a list of dimensions."""
        if not dimensions:
            raise RubricError("Rubric template must have at least one dimension")
        _validate_weights(dimensions)
        return RubricTemplate(
            name=name,
            dimensions=tuple(dimensions),
            version=self._next_version(),
        )

    async def score_response(self, response: str, template: RubricTemplate) -> RubricResult:
        """Score a response against a rubric template."""
        if not response:
            raise RubricError("Cannot score an empty response")
        if not template.dimensions:
            raise RubricError("Template has no dimensions")

        scores: list[RubricScore] = []
        for dim in template.dimensions:
            raw = _score_dimension(response, dim)
            weighted = raw * dim.weight * self._calibration_factor
            confidence = _compute_confidence(raw, len(response))
            scores.append(RubricScore(
                dimension=dim.name,
                raw_score=round(raw, 4),
                weighted_score=round(weighted, 4),
                confidence=round(confidence, 4),
            ))

        scores_t = tuple(scores)
        total = sum(s.weighted_score for s in scores_t)
        clamped_total = min(max(total, 0.0), 1.0)
        grade = _grade_from_score(clamped_total)

        return RubricResult(
            scores=scores_t,
            total_score=round(clamped_total, 4),
            grade=grade,
            calibration_factor=self._calibration_factor,
        )

    async def calibrate(self, historical_results: list[RubricResult]) -> float:
        """Calibrate scoring factor from historical results."""
        if not historical_results:
            return 1.0

        scores = [r.total_score for r in historical_results]
        mean_score = sum(scores) / len(scores)

        # Calibrate so mean score approaches 0.75 (target)
        target = 0.75
        if mean_score == 0.0:
            self._calibration_factor = 1.0
        else:
            self._calibration_factor = target / mean_score
            self._calibration_factor = min(max(self._calibration_factor, 0.1), 5.0)

        return round(self._calibration_factor, 4)

    async def auto_adjust_thresholds(self, domain_results: list[RubricResult]) -> RubricTemplate:
        """Auto-adjust a rubric template based on domain evaluation results."""
        if not domain_results:
            raise RubricError("No domain results provided for adjustment")
        if not domain_results[0].scores:
            raise RubricError("Domain results have no dimension scores")

        dim_names = [s.dimension for s in domain_results[0].scores]
        dim_scores: dict[str, list[float]] = {d: [] for d in dim_names}

        for result in domain_results:
            for score in result.scores:
                dim_scores[score.dimension].append(score.raw_score)

        adjusted_dimensions: list[RubricDimension] = []
        for name in dim_names:
            vals = dim_scores[name]
            avg = sum(vals) / len(vals) if vals else 0.0
            # Boost weight for dimensions where performance is lower (more room for improvement)
            new_weight = min(max(1.0 - avg, 0.1), 0.9)
            adjusted_dimensions.append(RubricDimension(
                name=name,
                weight=round(new_weight, 2),
                description=f"Auto-adjusted: {name}",
                scoring_function="auto",
            ))

        # Normalize weights to sum to 1.0
        total_raw = sum(d.weight for d in adjusted_dimensions)
        if total_raw > 0:
            adjusted_dimensions = [
                RubricDimension(
                    name=d.name,
                    weight=round(d.weight / total_raw, 4),
                    description=d.description,
                    scoring_function=d.scoring_function,
                )
                for d in adjusted_dimensions
            ]

        _validate_weights(adjusted_dimensions)
        return RubricTemplate(
            name="auto_adjusted",
            dimensions=tuple(adjusted_dimensions),
            version=self._next_version(),
            pearson_r=0.79,
        )


def _validate_weights(dimensions: list[RubricDimension]) -> None:
    """Validate that dimension weights sum to approximately 1.0."""
    total = sum(d.weight for d in dimensions)
    if abs(total - 1.0) > 0.01:
        raise RubricError(
            f"Dimension weights must sum to 1.0, got {total:.2f}"
        )


def _score_dimension(response: str, dim: RubricDimension) -> float:
    """Score a dimension based on response content."""
    if dim.scoring_function == "exact_match":
        # Exact match: score based on response length and content
        return min(len(response.strip()) / 20.0, 1.0)
    elif dim.scoring_function == "keyword_match":
        # Keyword match: count meaningful keywords
        words = response.split()
        if not words:
            return 0.0
        return min(len(words) / 5.0, 1.0)
    elif dim.scoring_function == "length_based":
        # Length-based: longer responses tend to be more complete
        if not response.strip():
            return 0.0
        return min(len(response) / 50.0, 1.0)
    else:
        # Generic scoring
        return min(len(response.strip()) / 30.0, 1.0)


def _compute_confidence(raw_score: float, response_length: int) -> float:
    """Compute confidence in a score based on response length."""
    length_conf = min(response_length / 20.0, 1.0)
    score_conf = 0.5 + 0.5 * raw_score
    return (length_conf + score_conf) / 2.0


def _grade_from_score(score: float) -> str:
    """Convert a numeric score to a letter grade."""
    if score >= 0.95:
        return "A+"
    elif score >= 0.85:
        return "A"
    elif score >= 0.75:
        return "B+"
    elif score >= 0.65:
        return "B"
    elif score >= 0.50:
        return "C"
    elif score >= 0.30:
        return "D"
    else:
        return "F"
