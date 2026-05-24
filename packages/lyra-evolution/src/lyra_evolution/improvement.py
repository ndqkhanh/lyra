"""Closed-Loop Self-Improvement.

Analyses failure episodes, proposes targeted fixes, validates them
against a test suite, and applies safe rollback on degradation.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import Any

from .models import EvolutionMetrics

logger = logging.getLogger(__name__)


class SelfImprovement:
    """Closed-loop improvement engine.

    Watches agent performance over time, identifies recurring failure
    patterns, generates candidate improvements, validates them, and
    applies them with automatic rollback on regression.
    """

    def __init__(
        self,
        *,
        rollback_threshold: float = 0.05,
        max_history: int = 1000,
    ) -> None:
        """Initialise the self-improvement engine.

        Args:
            rollback_threshold: Minimum acceptable performance drop before
                                an improvement is rolled back.
            max_history: Maximum number of episodes to retain.
        """
        self.rollback_threshold = rollback_threshold
        self.max_history = max_history

        self._episodes: list[dict[str, Any]] = []
        self._improvements: list[dict[str, Any]] = []
        self._active_improvements: list[str] = []
        self._baselines: dict[str, float] = {}
        self._generation: int = 0

    # ------------------------------------------------------------------
    # Episode recording
    # ------------------------------------------------------------------

    def record_episode(
        self,
        task_id: str,
        outcome: str,
        score: float,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record a single agent episode.

        Args:
            task_id: Identifier for the task.
            outcome: 'success' or 'failure'.
            score: Numeric quality score.
            metadata: Arbitrary extra context.
        """
        episode: dict[str, Any] = {
            "task_id": task_id,
            "outcome": outcome,
            "score": score,
            "timestamp": datetime.now(UTC),
            "metadata": metadata or {},
        }
        self._episodes.append(episode)

        if len(self._episodes) > self.max_history:
            self._episodes = self._episodes[-self.max_history :]

        logger.debug("Recorded episode '%s': %s (score=%.3f)", task_id, outcome, score)

    # ------------------------------------------------------------------
    # Failure analysis
    # ------------------------------------------------------------------

    def analyze_failures(
        self,
        episodes: Sequence[dict[str, Any]] | None = None,
        *,
        min_occurrences: int = 3,
    ) -> list[dict[str, Any]]:
        """Identify failure patterns from recent episodes.

        Groups failures by task_id (or metadata pattern) and returns
        those that appear at least *min_occurrences* times.

        Args:
            episodes: Episode history. Uses internal history when omitted.
            min_occurrences: Minimum count for a pattern to be flagged.

        Returns:
            List of failure-pattern dicts with keys: task_id, count,
            avg_score, example_episodes.
        """
        source = list(episodes) if episodes is not None else self._episodes
        failures = [e for e in source if e["outcome"] == "failure"]

        if not failures:
            logger.debug("No failures to analyse")
            return []

        # Group by task_id
        grouped: dict[str, list[dict[str, Any]]] = {}
        for ep in failures:
            grouped.setdefault(ep["task_id"], []).append(ep)

        patterns: list[dict[str, Any]] = []
        for task_id, group in grouped.items():
            if len(group) >= min_occurrences:
                avg_score = sum(e["score"] for e in group) / len(group)
                patterns.append(
                    {
                        "task_id": task_id,
                        "count": len(group),
                        "avg_score": round(avg_score, 4),
                        "example_episodes": group[:3],
                    }
                )

        patterns.sort(key=lambda p: p["count"], reverse=True)

        if patterns:
            logger.info("Found %d failure pattern(s); top='%s' (%d occurrences)",
                         len(patterns), patterns[0]["task_id"], patterns[0]["count"])

        return patterns

    # ------------------------------------------------------------------
    # Improvement generation
    # ------------------------------------------------------------------

    def generate_improvements(
        self,
        failures: Sequence[dict[str, Any]],
        *,
        generator: Callable[[dict[str, Any]], dict[str, Any] | None] | None = None,
    ) -> list[dict[str, Any]]:
        """Propose fixes for each failure pattern.

        Args:
            failures: Failure-pattern dicts from analyze_failures.
            generator: Optional callable that receives a failure dict
                       and returns an improvement dict or None.

        Returns:
            List of proposed improvements.
        """
        improvements: list[dict[str, Any]] = []
        for pattern in failures:
            if generator is not None:
                proposal = generator(pattern)
                if proposal is not None:
                    improvements.append(proposal)
                continue

            # Default: generate a simple improvement placeholder
            proposal: dict[str, Any] = {
                "target_task": pattern["task_id"],
                "description": f"Auto-generated fix for recurring failure on '{pattern['task_id']}'",
                "change_type": "patch",
                "generation": self._generation,
                "created_at": datetime.now(UTC),
                "failure_count": pattern["count"],
            }
            improvements.append(proposal)

        if improvements:
            logger.info("Generated %d improvement proposal(s)", len(improvements))

        return improvements

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_improvement(
        self,
        improvement: dict[str, Any],
        test_suite: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> dict[str, Any]:
        """Test an improvement against a test suite before applying.

        Args:
            improvement: The proposed improvement.
            test_suite: Callable that runs tests and returns a result dict
                        with at least 'passed' (bool) and 'score' (float).

        Returns:
            Dict with 'passed', 'score', 'details', 'improvement'.
        """
        logger.info("Validating improvement for '%s'", improvement.get("target_task", "unknown"))

        result = test_suite(improvement)

        return {
            "passed": bool(result.get("passed", False)),
            "score": float(result.get("score", 0.0)),
            "details": result.get("details", {}),
            "improvement": improvement,
            "validated_at": datetime.now(UTC),
        }

    # ------------------------------------------------------------------
    # Apply & rollback
    # ------------------------------------------------------------------

    def apply_improvement(self, improvement: dict[str, Any]) -> str:
        """Deploy an improvement and record it for potential rollback.

        Args:
            improvement: The validated improvement.

        Returns:
            An improvement identifier for tracking.
        """
        imp_id = improvement.get(
            "id", f"imp-{self._generation}-{len(self._improvements):04d}"
        )
        improvement["id"] = imp_id
        improvement["applied_at"] = datetime.now(UTC)
        improvement["active"] = True

        self._improvements.append(improvement)
        self._active_improvements.append(imp_id)
        self._generation += 1

        logger.info("Applied improvement '%s'", imp_id)
        return imp_id

    def rollback_if_degraded(
        self,
        improvement: dict[str, Any],
        baseline: float,
        *,
        current_score: float | None = None,
        evaluator: Callable[[], float] | None = None,
    ) -> bool:
        """Roll back an improvement if performance degraded past the threshold.

        Args:
            improvement: The improvement to evaluate.
            baseline: Baseline score before the improvement.
            current_score: Current performance score (if already measured).
            evaluator: Callable that returns the current score.

        Returns:
            True if rollback occurred.
        """
        if current_score is None and evaluator is not None:
            current_score = evaluator()

        if current_score is None:
            logger.warning("Cannot evaluate rollback — no score available")
            return False

        delta = baseline - current_score
        if delta > self.rollback_threshold:
            logger.warning(
                "Rolling back improvement '%s': score dropped from %.4f to %.4f (delta=%.4f)",
                improvement.get("id", "unknown"),
                baseline,
                current_score,
                delta,
            )
            improvement["active"] = False
            improvement["rolled_back_at"] = datetime.now(UTC)
            imp_id = improvement.get("id", "")
            if imp_id in self._active_improvements:
                self._active_improvements.remove(imp_id)
            return True

        logger.debug(
            "Improvement '%s' OK: baseline=%.4f, current=%.4f",
            improvement.get("id", "unknown"),
            baseline,
            current_score,
        )
        return False

    # ------------------------------------------------------------------
    # Improvement rate
    # ------------------------------------------------------------------

    def compute_improvement_rate(self, window: int = 20) -> float:
        """Long-term improvement trend.

        Estimates the per-episode improvement rate using a linear
        regression over the most recent *window* episodes.

        Args:
            window: Number of recent episodes to use.

        Returns:
            Slope of the score trendline (positive = improving).
        """
        recent = self._episodes[-window:] if len(self._episodes) >= window else self._episodes

        if len(recent) < 2:
            return 0.0

        n = len(recent)
        xs = list(range(n))
        ys = [e["score"] for e in recent]

        mean_x = sum(xs) / n
        mean_y = sum(ys) / n

        num = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(n))
        den = sum((x - mean_x) ** 2 for x in xs)

        if den == 0:
            return 0.0

        slope = num / den
        # Normalise by mean score to make it comparable across tasks
        normalised = slope / max(abs(mean_y), 0.001)

        logger.info("Improvement rate (window=%d): %.6f", window, normalised)
        return round(normalised, 6)

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def get_metrics(self) -> EvolutionMetrics:
        """Return aggregate improvement metrics for the current generation."""
        recent = self._episodes[-50:] if len(self._episodes) >= 50 else self._episodes
        scores = [e["score"] for e in recent] if recent else [0.0]

        return EvolutionMetrics(
            generation=self._generation,
            avg_fitness=sum(scores) / len(scores),
            best_fitness=max(scores),
            diversity=self._compute_episode_diversity(recent),
            improvement_rate=self.compute_improvement_rate(),
        )

    @property
    def active_improvement_count(self) -> int:
        """Number of currently active improvements."""
        return len(self._active_improvements)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_episode_diversity(episodes: Sequence[dict[str, Any]]) -> float:
        """Measure task diversity in recent episodes."""
        if not episodes:
            return 0.0
        unique_tasks = len({e["task_id"] for e in episodes})
        return min(1.0, unique_tasks / len(episodes))
