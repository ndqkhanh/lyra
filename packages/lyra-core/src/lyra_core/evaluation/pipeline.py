"""Continuous evaluation pipeline — scheduling, regression detection, improvement tracking.

Wraps the existing ``BenchmarkHarness`` with trigger-based scheduling,
persistence, and automated regression/improvement detection.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum

from lyra_core.auto.benchmark_harness import BenchmarkHarness, BenchmarkRun


class EvalTrigger(str, Enum):
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    ON_COMMIT = "on_commit"
    ON_PR = "on_pr"
    ON_DEPLOY = "on_deploy"
    ON_DRIFT = "on_drift"
    ON_LEARNING_CYCLE = "on_learning_cycle"


@dataclass(frozen=True)
class PipelineConfig:
    """Configuration for the evaluation pipeline."""

    schedule_interval_seconds: float = 3600.0
    regression_threshold: float = 0.05
    improvement_threshold: float = 0.05
    max_runs_history: int = 100
    auto_baseline_after_runs: int = 10
    triggers: tuple[EvalTrigger, ...] = (
        EvalTrigger.MANUAL,
        EvalTrigger.SCHEDULED,
        EvalTrigger.ON_PR,
    )


@dataclass(frozen=True)
class PipelineRun:
    """A single pipeline evaluation run wrapping a BenchmarkRun."""

    id: str
    trigger: EvalTrigger
    benchmark_run: BenchmarkRun
    triggered_by: str = ""
    commit_sha: str = ""
    pr_number: int = 0
    created_at: float = field(default_factory=time.time)
    regressions: tuple[str, ...] = ()
    improvements: tuple[str, ...] = ()

    @property
    def overall_score(self) -> float:
        return self.benchmark_run.overall_score

    @property
    def passed(self) -> bool:
        return self.benchmark_run.passed

    @property
    def has_regressions(self) -> bool:
        return len(self.regressions) > 0

    @property
    def has_improvements(self) -> bool:
        return len(self.improvements) > 0


@dataclass
class EvalPipeline:
    """Continuous evaluation pipeline wrapping BenchmarkHarness.

    Usage::

        pipeline = EvalPipeline()
        pipeline.harness.register("safety", "block_rate", lambda: 0.989, threshold=0.95)
        run = pipeline.run(EvalTrigger.ON_PR, commit_sha="abc123")
        print(f"Regressions: {run.regressions}")
    """

    config: PipelineConfig = field(default_factory=PipelineConfig)
    harness: BenchmarkHarness = field(default_factory=BenchmarkHarness)
    _runs: list[PipelineRun] = field(default_factory=list)
    _run_count: int = 0

    def run(
        self,
        trigger: EvalTrigger,
        *,
        triggered_by: str = "",
        commit_sha: str = "",
        pr_number: int = 0,
    ) -> PipelineRun:
        """Execute a full benchmark run and detect regressions/improvements."""
        benchmark_run = self.harness.run_all()
        self._run_count += 1

        regressions, improvements = self._detect_changes(benchmark_run)

        pipeline_run = PipelineRun(
            id=f"pr-{uuid.uuid4().hex[:12]}",
            trigger=trigger,
            benchmark_run=benchmark_run,
            triggered_by=triggered_by,
            commit_sha=commit_sha,
            pr_number=pr_number,
            regressions=regressions,
            improvements=improvements,
        )

        self._runs.append(pipeline_run)
        if len(self._runs) > self.config.max_runs_history:
            self._runs = self._runs[-self.config.max_runs_history:]

        if self._run_count == self.config.auto_baseline_after_runs:
            self.harness.set_baseline()

        return pipeline_run

    def _detect_changes(self, current: BenchmarkRun) -> tuple[tuple[str, ...], tuple[str, ...]]:
        """Compare current run against history to detect regressions/improvements."""
        if not self._runs:
            return (), ()

        last = self._runs[-1].benchmark_run
        regressions: list[str] = []
        improvements: list[str] = []

        current_scores = {f"{r.domain.value}:{r.metric_name}": r.score for r in current.results}
        last_scores = {f"{r.domain.value}:{r.metric_name}": r.score for r in last.results}

        for key, current_score in current_scores.items():
            last_score = last_scores.get(key)
            if last_score is None:
                continue
            delta = current_score - last_score
            if delta < -self.config.regression_threshold:
                regressions.append(f"{key}: {delta:+.4f}")
            elif delta > self.config.improvement_threshold:
                improvements.append(f"{key}: {delta:+.4f}")

        return tuple(regressions), tuple(improvements)

    def check_regressions(self) -> tuple[str, ...]:
        """Return all regression keys from the most recent run."""
        if not self._runs:
            return ()
        return self._runs[-1].regressions

    def check_improvements(self) -> tuple[str, ...]:
        """Return all improvement keys from the most recent run."""
        if not self._runs:
            return ()
        return self._runs[-1].improvements

    def get_latest_run(self) -> PipelineRun | None:
        return self._runs[-1] if self._runs else None

    def get_runs_by_trigger(self, trigger: EvalTrigger) -> tuple[PipelineRun, ...]:
        return tuple(r for r in self._runs if r.trigger == trigger)

    def get_trend(self, metric_key: str) -> tuple[float, ...]:
        """Get the score trend for a specific metric across all runs."""
        scores: list[float] = []
        for run in self._runs:
            for result in run.benchmark_run.results:
                key = f"{result.domain.value}:{result.metric_name}"
                if key == metric_key:
                    scores.append(result.score)
        return tuple(scores)

    @property
    def run_count(self) -> int:
        return len(self._runs)

    @property
    def last_overall_score(self) -> float | None:
        latest = self.get_latest_run()
        return latest.overall_score if latest else None

    def clear_history(self) -> None:
        self._runs.clear()
        self._run_count = 0
        self.harness.clear_history()
