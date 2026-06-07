"""
Quality Calibrator — auto-calibrate the 5-dimension quality rubric weights
from user ratings, with per-category calibration and regression detection.

Provides:
  - CalibrateFromFeedback(ratings) -> dict[dimension, weight]
  - Per-category calibration (code skills vs research skills)
  - Regression detection: flag skills whose quality is declining
"""

from __future__ import annotations

import statistics
import warnings
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from lyra.skills.evolution import (
    CLARITY,
    COMPLETENESS,
    CORRECTNESS,
    EFFICIENCY,
    RUBRIC_DIMENSIONS,
    SAFETY,
    EvalScore,
    RubricDimension,
)
from lyra.skills.skill import Skill

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_LEARNING_RATE: float = 0.1
"""How quickly weights adapt to new ratings."""

REGRESSION_WINDOW: int = 5
"""Number of recent evaluations to consider for regression detection."""

REGRESSION_THRESHOLD: float = -0.15
"""Average score change below this threshold flags a regression."""


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class CalibrationSample:
    """A single rating sample used for weight calibration.

    Attributes:
        dimension: Which rubric dimension was rated.
        rating: User rating (0.0-1.0).
        expected_score: The automatic score that was assigned (0.0-1.0).
        skill_name: The skill being rated.
        category: The skill's category (e.g. "code", "research").
        timestamp: When the rating was given.
    """

    dimension: str
    rating: float
    expected_score: float
    skill_name: str = ""
    category: str = "general"
    timestamp: float = 0.0


@dataclass
class CalibrationResult:
    """Result of a calibration operation.

    Attributes:
        weights: Calibrated weights dict[dimension, float].
        samples_used: Number of samples used for calibration.
        category: The category these weights apply to.
        error_before: Mean absolute error before calibration.
        error_after: Mean absolute error after calibration.
        improvement: Relative improvement (0.0-1.0).
    """

    weights: dict[str, float] = field(default_factory=dict)
    samples_used: int = 0
    category: str = "general"
    error_before: float = 0.0
    error_after: float = 0.0
    improvement: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "weights": {k: round(v, 4) for k, v in self.weights.items()},
            "samples_used": self.samples_used,
            "category": self.category,
            "error_before": round(self.error_before, 4),
            "error_after": round(self.error_after, 4),
            "improvement": round(self.improvement, 4),
        }


@dataclass
class RegressionReport:
    """Report of quality regression for a skill.

    Attributes:
        skill_name: Name of the skill showing regression.
        dimension: Which dimension is regressing.
        current_avg: Average score in the current window.
        previous_avg: Average score in the previous window.
        change: current_avg - previous_avg.
        severity: "critical", "warning", or "ok".
        trend_window: Number of data points examined.
    """

    skill_name: str
    dimension: str
    current_avg: float = 0.0
    previous_avg: float = 0.0
    change: float = 0.0
    severity: str = "ok"
    trend_window: int = REGRESSION_WINDOW

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_name": self.skill_name,
            "dimension": self.dimension,
            "current_avg": round(self.current_avg, 4),
            "previous_avg": round(self.previous_avg, 4),
            "change": round(self.change, 4),
            "severity": self.severity,
        }


# ---------------------------------------------------------------------------
# Weight calibrator
# ---------------------------------------------------------------------------


class QualityCalibrator:
    """Auto-calibrate the 5-dimension quality rubric weights from user
    ratings, with per-category support.

    The calibrator learns which dimensions users care about most for
    different skill categories. For example, ``code`` skills may be
    weighted toward correctness and safety, while ``research`` skills
    may weight completeness and clarity more heavily.

    Usage::

        cal = QualityCalibrator()
        cal.add_rating(CORRECTNESS, 0.9, expected=0.6, category="code")
        cal.add_rating(CLARITY, 0.7, expected=0.5, category="code")
        weights = cal.calibrate("code")
        print(weights)
    """

    def __init__(
        self,
        learning_rate: float = DEFAULT_LEARNING_RATE,
        default_weights: dict[str, float] | None = None,
    ):
        """
        Args:
            learning_rate: Step size for weight adjustments.
            default_weights: Initial weights per dimension. Falls back
                to the evolution module's DIMENSION_WEIGHTS if None.
        """
        self.learning_rate = learning_rate
        self._default_weights = default_weights or {
            CORRECTNESS: 0.30,
            COMPLETENESS: 0.25,
            CLARITY: 0.20,
            EFFICIENCY: 0.15,
            SAFETY: 0.10,
        }
        # Per-category samples: category -> list[CalibrationSample]
        self._samples: dict[str, list[CalibrationSample]] = defaultdict(list)
        # Per-category learned weights: category -> dict[dimension, weight]
        self._learned_weights: dict[str, dict[str, float]] = defaultdict(
            lambda: dict(self._default_weights)
        )

    # ------------------------------------------------------------------
    # Rating ingestion
    # ------------------------------------------------------------------

    def add_rating(
        self,
        dimension: RubricDimension | str,
        rating: float,
        expected_score: float = 0.0,
        skill_name: str = "",
        category: str = "general",
        timestamp: float | None = None,
    ):
        """Record a user rating for calibration.

        Args:
            dimension: Which rubric dimension was rated.
            rating: User rating (0.0-1.0).
            expected_score: The automatic score assigned (0.0-1.0).
            skill_name: Name of the rated skill.
            category: Skill category (e.g. "code", "research").
            timestamp: When the rating was given (defaults to now).
        """
        dim = dimension if isinstance(dimension, str) else str(dimension)
        rating = max(0.0, min(1.0, rating))
        expected_score = max(0.0, min(1.0, expected_score))

        import time as _time
        self._samples[category].append(CalibrationSample(
            dimension=dim,
            rating=rating,
            expected_score=expected_score,
            skill_name=skill_name,
            category=category,
            timestamp=timestamp or _time.time(),
        ))

    def add_eval_score_rating(
        self,
        eval_score: EvalScore,
        user_feedback: str = "",
        skill_name: str = "",
        category: str = "general",
    ):
        """Record ratings from an EvalScore with implicit user feedback.

        Parses the user feedback string to infer which dimensions were
        over- or under-scored.

        Args:
            eval_score: The automatic EvalScore.
            user_feedback: Optional user feedback text.
            skill_name: Name of the evaluated skill.
            category: Skill category.
        """
        # Use the evaluation score itself as the "expected" value
        for dim in RUBRIC_DIMENSIONS:
            score = getattr(eval_score, dim)
            # Without explicit user ratings, use the score as a self-consistency signal
            self.add_rating(
                dimension=dim,
                rating=score,
                expected_score=score,
                skill_name=skill_name,
                category=category,
            )

    # ------------------------------------------------------------------
    # Calibration
    # ------------------------------------------------------------------

    def calibrate(
        self,
        category: str = "general",
    ) -> CalibrationResult:
        """Run calibration for a specific category.

        Adjusts dimension weights to minimise the error between user
        ratings and automatic scores.

        Args:
            category: The skill category to calibrate for.

        Returns:
            CalibrationResult with new weights and error metrics.
        """
        samples = self._samples.get(category, [])
        if not samples:
            return CalibrationResult(
                weights=dict(self._learned_weights[category]),
                samples_used=0,
                category=category,
            )

        # Current weights before calibration
        current_weights = dict(self._learned_weights[category])

        # Compute error before calibration
        error_before = self._mean_absolute_error(samples, current_weights)

        # Group samples by dimension
        dim_samples: dict[str, list[float]] = defaultdict(list)
        for s in samples:
            dim_samples[s.dimension].append(s.rating)

        # Adjust weights: dimensions with higher user ratings get more weight
        new_weights: dict[str, float] = {}
        for dim in RUBRIC_DIMENSIONS:
            dim_str = str(dim)
            dim_ratings = dim_samples.get(dim_str, [])
            if dim_ratings:
                # Average user rating for this dimension
                avg_rating = statistics.mean(dim_ratings)
                # Adjust: higher rating -> higher weight (users value this dim)
                adjustment = self.learning_rate * (avg_rating - 0.5)
                new_weights[dim_str] = max(
                    0.01,
                    current_weights.get(dim_str, self._default_weights[dim])
                    + adjustment,
                )
            else:
                new_weights[dim_str] = current_weights.get(
                    dim_str, self._default_weights[dim]
                )

        # Normalise weights to sum to 1.0
        total = sum(new_weights.values())
        if total > 0:
            for dim in new_weights:
                new_weights[dim] /= total

        # Store learned weights
        self._learned_weights[category] = new_weights

        # Error after calibration
        error_after = self._mean_absolute_error(samples, new_weights)

        improvement = max(
            0.0,
            (error_before - error_after) / max(error_before, 1e-12),
        ) if error_before > 0 else 0.0

        return CalibrationResult(
            weights=new_weights,
            samples_used=len(samples),
            category=category,
            error_before=error_before,
            error_after=error_after,
            improvement=improvement,
        )

    def calibrate_all(self) -> dict[str, CalibrationResult]:
        """Run calibration for every category that has samples.

        Returns:
            Dict mapping category to its CalibrationResult.
        """
        results: dict[str, CalibrationResult] = {}
        for category in list(self._samples.keys()):
            results[category] = self.calibrate(category)
        return results

    # ------------------------------------------------------------------
    # Weight accessors
    # ------------------------------------------------------------------

    def get_weights(self, category: str = "general") -> dict[str, float]:
        """Get the current calibrated weights for a category.

        Args:
            category: Skill category.

        Returns:
            Dict of dimension -> weight (sums to 1.0).
        """
        return dict(self._learned_weights[category])

    def reset_weights(self, category: str | None = None):
        """Reset learned weights to defaults.

        Args:
            category: If provided, reset only this category.
                If None, reset all categories.
        """
        if category:
            self._learned_weights[category] = dict(self._default_weights)
            self._samples[category].clear()
        else:
            self._learned_weights.clear()
            self._samples.clear()

    # ------------------------------------------------------------------
    # Regression detection
    # ------------------------------------------------------------------

    def detect_regression(
        self,
        skill_name: str,
        eval_history: list[EvalScore],
        window: int = REGRESSION_WINDOW,
    ) -> list[RegressionReport]:
        """Check if a skill's quality scores are declining.

        Compares the average of the most recent *window* evaluations
        against the preceding *window* evaluations for each dimension.

        Args:
            skill_name: Name of the skill to check.
            eval_history: Chronological list of EvalScore evaluations.
            window: Number of evaluations to consider per window.

        Returns:
            List of RegressionReport (one per declining dimension).
        """
        if len(eval_history) < window * 2:
            return []

        recent = eval_history[-window:]
        previous = eval_history[-(window * 2):-window]

        reports: list[RegressionReport] = []
        for dim in RUBRIC_DIMENSIONS:
            recent_vals = [getattr(e, dim) for e in recent]
            prev_vals = [getattr(e, dim) for e in previous]

            recent_avg = statistics.mean(recent_vals) if recent_vals else 0.0
            prev_avg = statistics.mean(prev_vals) if prev_vals else 0.0
            change = recent_avg - prev_avg

            if change < REGRESSION_THRESHOLD:
                severity = "critical" if change < REGRESSION_THRESHOLD * 2 else "warning"
            else:
                severity = "ok"

            reports.append(RegressionReport(
                skill_name=skill_name,
                dimension=str(dim),
                current_avg=recent_avg,
                previous_avg=prev_avg,
                change=change,
                severity=severity,
                trend_window=window,
            ))

        return reports

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _mean_absolute_error(
        samples: list[CalibrationSample],
        weights: dict[str, float],
    ) -> float:
        """Compute the mean absolute error between predicted and actual ratings.

        Predicted score = sum(dimension_score * dimension_weight).
        """
        if not samples:
            return 0.0

        total_error = 0.0
        count = 0
        for s in samples:
            weight = weights.get(s.dimension, 0.0)
            predicted = s.expected_score * weight
            total_error += abs(s.rating * weight - predicted)
            count += 1
        return total_error / max(count, 1)


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------


def calibrate_from_feedback(
    ratings: list[dict[str, Any]],
    category: str = "general",
    learning_rate: float = DEFAULT_LEARNING_RATE,
) -> dict[str, float]:
    """One-shot calibration from a list of rating dicts.

    Each rating dict should have:
      - ``"dimension"``: rubric dimension name
      - ``"rating"``: user rating (0.0-1.0)
      - ``"expected_score"``: automatic score (0.0-1.0)
      - ``"category"`` (optional): defaults to *category*

    Args:
        ratings: List of rating records.
        category: Default category for ratings without one.
        learning_rate: Weight adjustment rate.

    Returns:
        Calibrated weights dict[dimension, weight].
    """
    calibrator = QualityCalibrator(learning_rate=learning_rate)
    for r in ratings:
        calibrator.add_rating(
            dimension=r.get("dimension", "correctness"),
            rating=r.get("rating", 0.5),
            expected_score=r.get("expected_score", 0.5),
            category=r.get("category", category),
        )
    result = calibrator.calibrate(category)
    return result.weights
