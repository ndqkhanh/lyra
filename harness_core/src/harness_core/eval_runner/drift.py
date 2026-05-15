"""DriftMonitor — track suite scores over time; alert on regression."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from .types import EvalRun


@dataclass(frozen=True)
class DriftAlert:
    """Fired when a suite's recent score drops materially below baseline."""

    suite_id: str
    triggered_at: float
    baseline_mean: float  # mean of older runs
    current_score: float  # most recent run's score
    delta: float  # current - baseline (negative for regression)
    threshold: float
    note: str = ""

    @property
    def is_regression(self) -> bool:
        return self.delta < 0


@dataclass
class DriftMonitor:
    """Track an eval suite over time; surface regression alerts.

    Stores a rolling history of :class:`EvalRun`s. Computes a baseline as the
    mean of the older runs (configurable window) vs the most recent run; if
    the delta exceeds the threshold downward, fires a :class:`DriftAlert`.

    >>> monitor = DriftMonitor()
    >>> from harness_core.eval_runner import EvalRun, EvalResult
    >>> r1 = EvalRun.create(suite_id="bench", results=[
    ...     EvalResult.create(case_id="c1", suite_id="bench",
    ...                        score=0.9, passed=True, timestamp=100.0),
    ... ])
    >>> r2 = EvalRun.create(suite_id="bench", results=[
    ...     EvalResult.create(case_id="c1", suite_id="bench",
    ...                        score=0.5, passed=True, timestamp=200.0),
    ... ])
    >>> monitor.add_run(r1)
    >>> monitor.add_run(r2)
    >>> alert = monitor.detect_regression(suite_id="bench", threshold=0.1)
    >>> alert is not None and alert.is_regression
    True
    """

    history: list[EvalRun] = field(default_factory=list)
    baseline_window: int = 5  # how many older runs to average for the baseline

    def __post_init__(self) -> None:
        if self.baseline_window < 1:
            raise ValueError(
                f"baseline_window must be >= 1, got {self.baseline_window}"
            )

    def add_run(self, run: EvalRun) -> None:
        """Append a run to the history."""
        self.history.append(run)

    def runs_for(self, suite_id: str) -> list[EvalRun]:
        """All runs for a given suite, oldest first."""
        runs = [r for r in self.history if r.suite_id == suite_id]
        runs.sort(key=lambda r: r.timestamp)
        return runs

    def trend(self, suite_id: str, *, window: int = 10) -> list[float]:
        """Last ``window`` mean_score values for the suite, oldest first."""
        runs = self.runs_for(suite_id)
        return [r.mean_score for r in runs[-window:]]

    def detect_regression(
        self,
        *,
        suite_id: str,
        threshold: float = 0.05,
    ) -> Optional[DriftAlert]:
        """Compare the most recent run vs the prior ``baseline_window`` mean.

        ``threshold`` is the minimum *downward* delta to flag. A run scoring
        ``baseline_mean - threshold`` or worse fires an alert.
        """
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(f"threshold must be in [0, 1], got {threshold}")

        runs = self.runs_for(suite_id)
        if len(runs) < 2:
            return None  # need at least one baseline run + one current run

        baseline_runs = runs[:-1][-self.baseline_window:]
        current = runs[-1]
        if not baseline_runs:
            return None
        baseline_mean = sum(r.mean_score for r in baseline_runs) / len(baseline_runs)
        delta = current.mean_score - baseline_mean
        if delta >= -threshold:  # not a regression of the required size
            return None
        return DriftAlert(
            suite_id=suite_id,
            triggered_at=time.time(),
            baseline_mean=baseline_mean,
            current_score=current.mean_score,
            delta=delta,
            threshold=threshold,
            note=(
                f"score dropped from baseline {baseline_mean:.3f} "
                f"to {current.mean_score:.3f} (delta={delta:+.3f}, "
                f"exceeds threshold {threshold})"
            ),
        )

    def detect_improvement(
        self,
        *,
        suite_id: str,
        threshold: float = 0.05,
    ) -> Optional[DriftAlert]:
        """Mirror of :meth:`detect_regression` for upward delta — useful for
        celebrating eval gains in CI."""
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(f"threshold must be in [0, 1], got {threshold}")
        runs = self.runs_for(suite_id)
        if len(runs) < 2:
            return None
        baseline_runs = runs[:-1][-self.baseline_window:]
        current = runs[-1]
        if not baseline_runs:
            return None
        baseline_mean = sum(r.mean_score for r in baseline_runs) / len(baseline_runs)
        delta = current.mean_score - baseline_mean
        if delta <= threshold:
            return None
        return DriftAlert(
            suite_id=suite_id,
            triggered_at=time.time(),
            baseline_mean=baseline_mean,
            current_score=current.mean_score,
            delta=delta,
            threshold=threshold,
            note=(
                f"score improved from baseline {baseline_mean:.3f} "
                f"to {current.mean_score:.3f} (delta={delta:+.3f})"
            ),
        )

    def summary(self, suite_id: str) -> dict:
        """Aggregate stats for a suite across all runs."""
        runs = self.runs_for(suite_id)
        if not runs:
            return {"suite_id": suite_id, "n_runs": 0}
        scores = [r.mean_score for r in runs]
        return {
            "suite_id": suite_id,
            "n_runs": len(runs),
            "first_score": scores[0],
            "latest_score": scores[-1],
            "min_score": min(scores),
            "max_score": max(scores),
            "mean_score": sum(scores) / len(scores),
            "total_cost_usd": sum(r.total_cost_usd for r in runs),
        }


__all__ = ["DriftAlert", "DriftMonitor"]
