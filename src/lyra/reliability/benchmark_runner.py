"""
Benchmark Runner — Continuous evaluation against standard agent benchmarks.

v8.3 enhancements:
- Scheduled benchmark runs: cron-style scheduling
- Regression detection with configurable thresholds
- Multi-benchmark support: Terminal-Bench, tau-bench, HumanEval, SWE-bench subset
- BenchmarkReport with per-benchmark scores, trends, and regression alerts
- CI integration stubs for pipeline integration
"""

from __future__ import annotations

import asyncio
import json
import math
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from lyra.verification.eval_harness import (
    EvalHarness,
    EvalRunner,
    EvalTask,
    SWEBenchRunner,
    TauBenchRunner,
)


# ---------------------------------------------------------------------------
# Cron-style scheduling
# ---------------------------------------------------------------------------


def parse_cron(expr: str) -> tuple[int, int, int, int, int]:
    """Parse a 5-field cron expression into (minute, hour, dom, month, dow).

    Asterisks are represented as ``-1``. Supports the ``*/N`` step syntax
    for minute and hour fields only.

    Example::

        parse_cron("0 */6 * * *")  -> (0, -1, -1, -1, -1) meaning
                                     "at minute 0, every 6th hour"
    """
    fields = expr.strip().split()
    if len(fields) != 5:
        raise ValueError(f"Expected 5 cron fields, got {len(fields)}: {expr}")

    parsed: list[int] = []
    for pos, f in enumerate(fields):
        if f == "*":
            parsed.append(-1)
        elif f.startswith("*/"):
            step = int(f[2:])
            parsed.append(-step)  # negative => step value
        else:
            parsed.append(int(f))
    return tuple(parsed)  # type: ignore[return-value]


def cron_matches(
    parsed: tuple[int, int, int, int, int], dt: datetime | None = None
) -> bool:
    """Check whether *dt* (default: now) matches the parsed cron expression."""
    now = dt or datetime.now()
    minute, hour, dom, month, dow = parsed

    def _match(field_val: int, cron_val: int) -> bool:
        if cron_val == -1:  # wildcard
            return True
        if cron_val < 0:  # step e.g. */6 = -6
            step = -cron_val
            return field_val % step == 0
        return field_val == cron_val

    return (
        _match(now.minute, minute)
        and _match(now.hour, hour)
        and _match(now.day, dom)
        and _match(now.month, month)
        and _match(now.weekday(), dow)
    )


# ---------------------------------------------------------------------------
# Benchmark types
# ---------------------------------------------------------------------------


@dataclass
class BenchmarkConfig:
    """Configuration for a benchmark run.

    Attributes
    ----------
    which:
        Which benchmarks to run.  "*" means all known.
    frequency:
        How often to run ("daily", "weekly", "manual").
    tasks:
        Number of tasks to evaluate.
    k:
        Number of trials per task for pass@k.
    alert_on_regression:
        If True, generate alerts when scores drop below baseline.
    baseline_path:
        Path to a JSON file storing baseline scores.
    output_dir:
        Where to write result artifacts.
    regression_threshold:
        Minimum score drop (absolute, 0-1) before regression is flagged.
    cron_expr:
        5-field cron expression for scheduled runs (overrides ``frequency``
        when set).
    ci_mode:
        When True, treat failures as CI pipeline failures.
    max_concurrent:
        Maximum number of benchmarks to run concurrently.
    """

    which: list[str] | str = "*"
    frequency: str = "weekly"
    tasks: int = 50
    k: int = 5
    alert_on_regression: bool = True
    baseline_path: str | None = None
    output_dir: str | None = None
    regression_threshold: float = 0.05
    cron_expr: str | None = None
    ci_mode: bool = False
    max_concurrent: int = 2

    def __post_init__(self) -> None:
        valid_freq = {"daily", "weekly", "manual"}
        if self.frequency not in valid_freq:
            raise ValueError(f"frequency must be one of {valid_freq}")
        if not 0.0 <= self.regression_threshold <= 1.0:
            raise ValueError("regression_threshold must be in [0, 1]")
        if self.cron_expr:
            parse_cron(self.cron_expr)


@dataclass
class BenchmarkResult:
    """Result of a single benchmark evaluation."""

    benchmark_name: str
    pass_at_1: float
    pass_at_k: float
    k: int
    n_tasks: int
    avg_cost_per_task: float
    avg_tokens_per_task: int
    total_duration_seconds: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    task_results: list = field(default_factory=list)
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def score(self) -> float:
        """Primary score — use pass@k for multi-shot, pass@1 otherwise."""
        return self.pass_at_k if self.k > 1 else self.pass_at_1


@dataclass
class BenchmarkSuiteResult:
    """Result of a full benchmark suite run."""

    results: list[BenchmarkResult]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    total_duration_seconds: float = 0.0
    regressions: list[RegressionAlert] = field(default_factory=list)
    run_id: str = ""

    def by_name(self, name: str) -> BenchmarkResult | None:
        """Look up a result by benchmark name."""
        for r in self.results:
            if r.benchmark_name == name:
                return r
        return None


# ---------------------------------------------------------------------------
# Trend tracking
# ---------------------------------------------------------------------------


@dataclass
class TrendPoint:
    """A single data point in a benchmark trend."""

    score: float
    timestamp: datetime
    run_id: str = ""


@dataclass
class BenchmarkTrend:
    """Trend data over multiple runs for a single benchmark.

    Supports linear regression to determine if the trend is improving
    or degrading.
    """

    benchmark_name: str
    points: list[TrendPoint] = field(default_factory=list)

    @property
    def slope(self) -> float:
        """Slope of the linear trend (positive = improving)."""
        n = len(self.points)
        if n < 2:
            return 0.0
        # Normalize timestamps to seconds since first point
        t0 = self.points[0].timestamp.timestamp()
        xs = [p.timestamp.timestamp() - t0 for p in self.points]
        ys = [p.score for p in self.points]
        x_mean = sum(xs) / n
        y_mean = sum(ys) / n
        num = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
        den = sum((x - x_mean) ** 2 for x in xs)
        return num / den if den != 0 else 0.0

    @property
    def direction(self) -> str:
        """Return ``"improving"``, ``"degrading"``, or ``"stable"``.

        Slope is measured in score-per-second. A 10 pp change over 1 hour
        yields ≈ 2.8e-5; a 10 pp change over 1 day yields ≈ 1.2e-6.
        The threshold of 1e-7 balances sensitivity against noise.
        """
        s = self.slope
        if s > 1e-7:
            return "improving"
        elif s < -1e-7:
            return "degrading"
        return "stable"


# ---------------------------------------------------------------------------
# Baselines
# ---------------------------------------------------------------------------


@dataclass
class BaselineEntry:
    """A stored baseline score for regression comparison."""

    benchmark_name: str
    score: float
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_regression(self, new_score: float, threshold: float = 0.05) -> bool:
        """Return True if *new_score* regresses more than *threshold*."""
        return new_score < self.score - threshold


@dataclass
class RegressionAlert:
    """Alert raised when a benchmark score regresses."""

    benchmark_name: str
    previous_score: float
    current_score: float
    drop: float
    threshold: float
    message: str


class BaselineManager:
    """Loads and persists benchmark baselines for regression detection."""

    def __init__(self, path: str | None = None) -> None:
        self.path = Path(path) if path else None
        self._entries: dict[str, BaselineEntry] = {}
        self._load()

    def _load(self) -> None:
        if self.path and self.path.exists():
            with open(self.path) as f:
                data = json.load(f)
            for item in data.get("baselines", []):
                entry = BaselineEntry(
                    benchmark_name=item["benchmark_name"],
                    score=item["score"],
                    timestamp=datetime.fromisoformat(item["timestamp"]),
                    metadata=item.get("metadata", {}),
                )
                self._entries[entry.benchmark_name] = entry

    def _save(self) -> None:
        if not self.path:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w") as f:
            json.dump(
                {
                    "baselines": [
                        {
                            "benchmark_name": e.benchmark_name,
                            "score": e.score,
                            "timestamp": e.timestamp.isoformat(),
                            "metadata": e.metadata,
                        }
                        for e in self._entries.values()
                    ]
                },
                f,
                indent=2,
            )

    def get(self, benchmark_name: str) -> BaselineEntry | None:
        """Get the stored baseline for *benchmark_name*."""
        return self._entries.get(benchmark_name)

    def update(self, result: BenchmarkResult) -> None:
        """Set the baseline for a benchmark from a fresh result."""
        self._entries[result.benchmark_name] = BaselineEntry(
            benchmark_name=result.benchmark_name,
            score=result.score,
            timestamp=result.timestamp,
        )
        self._save()

    def check_regression(
        self, result: BenchmarkResult, threshold: float = 0.05
    ) -> RegressionAlert | None:
        """Check if *result* regresses against the stored baseline."""
        entry = self.get(result.benchmark_name)
        if entry is None:
            return None
        if entry.is_regression(result.score, threshold):
            drop = entry.score - result.score
            return RegressionAlert(
                benchmark_name=result.benchmark_name,
                previous_score=entry.score,
                current_score=result.score,
                drop=drop,
                threshold=threshold,
                message=(
                    f"REGRESSION: {result.benchmark_name} dropped from "
                    f"{entry.score:.1%} to {result.score:.1%} "
                    f"(drop={drop:.1%}, threshold={threshold:.1%})"
                ),
            )
        return None

    def clear(self) -> None:
        """Remove all stored baselines."""
        self._entries.clear()
        self._save()


# ---------------------------------------------------------------------------
# Benchmark runners
# ---------------------------------------------------------------------------


class TerminalBenchRunner(EvalRunner):
    """Terminal-Bench evaluation: CLI tool completion tasks."""

    def __init__(self, domain: str = "general", data_path: Path | None = None) -> None:
        self.domain = domain
        self.data_path = data_path or Path.home() / ".lyra" / "eval_data" / "terminal-bench"
        self._tasks: list = []

    def get_tasks(self, n: int = 100) -> list:
        if self._tasks:
            return self._tasks[:n]
        tasks_file = self.data_path / "tasks.json"
        if tasks_file.exists():
            import json
            with open(tasks_file) as f:
                data = json.load(f)
            self._tasks = [
                EvalTask(task_id=t["task_id"], prompt=t["prompt"], metadata=t.get("metadata", {}))
                for t in data.get("tasks", [])
            ]
        else:
            self._tasks = self._generate_synthetic_tasks(n)
        return self._tasks[:n]

    def _generate_synthetic_tasks(self, n: int) -> list:
        return [
            EvalTask(
                task_id=f"terminal-{i:03d}",
                prompt=f"CLI task {i}: {self._cli_descriptions(i)}",
                metadata={"domain": self.domain},
            )
            for i in range(n)
        ]

    @staticmethod
    def _cli_descriptions(i: int) -> str:
        tasks = [
            "find all log files modified in the last 24 hours",
            "extract the third column from a CSV",
            "count unique IPs in an access log",
            "merge two sorted text files",
            "convert markdown to HTML using pandoc",
        ]
        return tasks[i % len(tasks)]

    async def check(self, task, output: str) -> bool:
        import re
        commands = re.findall(r"(?:^|\n)\s*\$?\s*([a-z][a-z0-9_-]+)\s", output)
        return len(commands) >= 1

    def get_name(self) -> str:
        return f"terminal-bench-{self.domain}"


class HumanEvalRunner(EvalRunner):
    """HumanEval evaluation: function synthesis from docstring."""

    def __init__(self, data_path: Path | None = None) -> None:
        self.data_path = data_path or Path.home() / ".lyra" / "eval_data" / "humaneval"
        self._tasks: list = []

    def get_tasks(self, n: int = 100) -> list:
        if self._tasks:
            return self._tasks[:n]
        tasks_file = self.data_path / "tasks.json"
        if tasks_file.exists():
            import json
            with open(tasks_file) as f:
                data = json.load(f)
            self._tasks = [
                EvalTask(
                    task_id=t["task_id"],
                    prompt=t["prompt"],
                    expected_output=t.get("canonical_solution"),
                    metadata={"entry_point": t.get("entry_point")},
                )
                for t in data.get("tasks", [])
            ]
        else:
            self._tasks = self._generate_synthetic_tasks(n)
        return self._tasks[:n]

    def _generate_synthetic_tasks(self, n: int) -> list:
        return [
            EvalTask(
                task_id=f"humaneval-{i:03d}",
                prompt=f"Write a Python function that solves problem {i}",
                metadata={"entry_point": f"solution_{i}"},
            )
            for i in range(n)
        ]

    async def check(self, task, output: str) -> bool:
        import re
        has_function = "def " in output
        has_return = "return " in output
        has_type_hint = bool(re.search(r"\bdef\s+\w+\s*\(.*?\)\s*->", output))
        score = sum([has_function, has_return, has_type_hint])
        return score >= 2

    def get_name(self) -> str:
        return "humaneval"


# ---------------------------------------------------------------------------
# CI Integration
# ---------------------------------------------------------------------------


@dataclass
class CIBreakdown:
    """Result of integrating a benchmark suite run into a CI pipeline.

    Attributes
    ----------
    passed:
        True if no regressions and no errors.
    total_benchmarks:
        Number of benchmarks in the run.
    passed_benchmarks:
        Number of benchmarks that passed without regression.
    failed_benchmarks:
        Number of benchmarks with regressions.
    errored_benchmarks:
        Number of benchmarks that produced errors.
    exit_code:
        Suggested CI exit code (0 = pass, 1 = regression, 2 = error).
    """

    passed: bool
    total_benchmarks: int
    passed_benchmarks: int
    failed_benchmarks: int
    errored_benchmarks: int
    exit_code: int


# ---------------------------------------------------------------------------
# Benchmark Report
# ---------------------------------------------------------------------------


@dataclass
class BenchmarkReport:
    """Comprehensive report across multiple runs with trends.

    Attributes
    ----------
    suite_result:
        The latest suite result.
    history:
        Previous suite results for trend analysis.
    trends:
        Per-benchmark trend data.
    ci:
        Optional CI breakdown.
    """

    suite_result: BenchmarkSuiteResult
    history: list[BenchmarkSuiteResult] = field(default_factory=list)
    trends: dict[str, BenchmarkTrend] = field(default_factory=dict)
    ci: CIBreakdown | None = None

    def to_markdown(self) -> str:
        """Render report as a markdown table."""
        lines = [
            "# Benchmark Report",
            "",
            f"**Run ID**: {self.suite_result.run_id}",
            f"**Timestamp**: {self.suite_result.timestamp.isoformat()}",
            f"**Duration**: {self.suite_result.total_duration_seconds:.1f}s",
            "",
            "## Scores",
            "",
            "| Benchmark | pass@1 | pass@k | Tasks | Duration | Trend |",
            "|---|---|---|---|---|---|",
        ]
        for r in self.suite_result.results:
            trend = self.trends.get(r.benchmark_name)
            direction = trend.direction if trend else "N/A"
            error_mark = " ERROR" if r.error else ""
            lines.append(
                f"| {r.benchmark_name}{error_mark:<10s} | "
                f"{r.pass_at_1:>7.1%} | "
                f"{r.pass_at_k:>7.1%} | "
                f"{r.n_tasks:>5d} | "
                f"{r.total_duration_seconds:>7.1f}s | "
                f"{direction} |"
            )

        if self.suite_result.regressions:
            lines.extend(["", "## Regression Alerts", ""])
            for alert in self.suite_result.regressions:
                lines.append(f"- **{alert.benchmark_name}**: {alert.message}")

        if self.ci:
            lines.extend(["", "## CI Integration", ""])
            lines.append(f"- **CI Status**: {'PASSED' if self.ci.passed else 'FAILED'}")
            lines.append(f"- **Exit Code**: {self.ci.exit_code}")
            lines.append(f"- **Passed**: {self.ci.passed_benchmarks}/{self.ci.total_benchmarks}")
            lines.append(f"- **Regressions**: {self.ci.failed_benchmarks}")
            lines.append(f"- **Errors**: {self.ci.errored_benchmarks}")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Benchmark Runner
# ---------------------------------------------------------------------------


class BenchmarkRunner:
    """Orchestrates automated benchmark evaluation and regression detection.

    v8.3 enhancements:
    - Scheduled runs via cron expressions
    - Trend tracking with linear regression
    - CI integration breakdown
    - Comprehensive BenchmarkReport
    - Multi-benchmark concurrency
    """

    _BENCHMARK_BUILDERS: dict[str, Callable] = {
        "tau-bench": lambda c: TauBenchRunner(domain=c.get("domain", "airline")),
        "tau-bench-retail": lambda c: TauBenchRunner(domain="retail"),
        "swe-bench": lambda c: SWEBenchRunner(),
        "terminal-bench": lambda c: TerminalBenchRunner(),
        "humaneval": lambda c: HumanEvalRunner(),
    }

    def __init__(
        self,
        agent: Any | None = None,
        config: BenchmarkConfig | None = None,
        baselines: BaselineManager | None = None,
    ) -> None:
        self.agent = agent
        self.config = config or BenchmarkConfig()
        self.baselines = baselines or BaselineManager(
            path=self.config.baseline_path
        )
        self._results: dict[str, BenchmarkResult] = {}
        self._history: list[BenchmarkSuiteResult] = []
        self._trends: dict[str, BenchmarkTrend] = {}
        self._scheduler_task: asyncio.Task | None = None

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------

    async def run_benchmark(
        self, benchmark: str | EvalRunner
    ) -> BenchmarkResult:
        """Run a single benchmark and return its result."""
        if isinstance(benchmark, str):
            runner = self._build_runner(benchmark)
        else:
            runner = benchmark

        harness = EvalHarness(
            "tau-bench" if isinstance(runner, TauBenchRunner) else "swe-bench"
        )
        harness.runner = runner
        harness.backend = runner.get_name()

        start = time.monotonic()

        if self.agent is not None:
            results = await harness.evaluate(
                agent=self.agent, tasks=self.config.tasks, k=self.config.k
            )
        else:
            results = await harness.evaluate(
                agent=self._stub_agent(), tasks=self.config.tasks, k=self.config.k
            )

        duration = time.monotonic() - start

        result = BenchmarkResult(
            benchmark_name=runner.get_name(),
            pass_at_1=results.pass_at_1,
            pass_at_k=results.pass_at_k,
            k=self.config.k,
            n_tasks=self.config.tasks,
            avg_cost_per_task=results.avg_cost_per_task,
            avg_tokens_per_task=results.avg_tokens_per_task,
            total_duration_seconds=duration,
            timestamp=results.timestamp,
        )

        self._results[result.benchmark_name] = result
        return result

    async def run_suite(self) -> BenchmarkSuiteResult:
        """Run all configured benchmarks and detect regressions."""
        benchmarks = self._resolve_benchmarks()
        start = time.monotonic()

        results: list[BenchmarkResult] = []
        for name in benchmarks:
            try:
                result = await self.run_benchmark(name)
                results.append(result)
            except Exception as exc:
                results.append(
                    BenchmarkResult(
                        benchmark_name=name,
                        pass_at_1=0.0,
                        pass_at_k=0.0,
                        k=self.config.k,
                        n_tasks=0,
                        avg_cost_per_task=0.0,
                        avg_tokens_per_task=0,
                        total_duration_seconds=0.0,
                        error=str(exc),
                    )
                )

        total_duration = time.monotonic() - start

        # Regression detection and baseline update
        regressions: list[RegressionAlert] = []
        for result in results:
            if result.error:
                continue
            if self.config.alert_on_regression:
                alert = self.baselines.check_regression(
                    result, threshold=self.config.regression_threshold
                )
                if alert:
                    regressions.append(alert)
            self.baselines.update(result)

        # Build suite result
        suite_result = BenchmarkSuiteResult(
            results=results,
            total_duration_seconds=total_duration,
            regressions=regressions,
            run_id=f"run-{int(time.time())}",
        )

        # Track history and trends
        self._history.append(suite_result)
        self._update_trends(suite_result)

        # Persist results
        if self.config.output_dir:
            self._persist(suite_result)

        return suite_result

    # ------------------------------------------------------------------
    # Scheduled Runs
    # ------------------------------------------------------------------

    def start_scheduler(self) -> None:
        """Start a background task that runs benchmarks on a cron schedule.

        The scheduler checks the cron expression every 60 seconds and
        triggers a suite run when the expression matches.
        """
        if self._scheduler_task is not None:
            return  # already running

        async def _scheduler_loop() -> None:
            try:
                if not self.config.cron_expr:
                    # Fall back to frequency-based scheduling
                    interval_seconds = {
                        "daily": 86400,
                        "weekly": 604800,
                    }.get(self.config.frequency, 604800)

                    while True:
                        self.config.cron_expr = str(int(time.time() + interval_seconds))
                        suite_result = await self.run_suite()
                        if self._scheduler_callback:
                            await self._scheduler_callback(suite_result)
                        await asyncio.sleep(interval_seconds)
                    return

                parsed = parse_cron(self.config.cron_expr)
                while True:
                    now = datetime.now()
                    if cron_matches(parsed, now):
                        suite_result = await self.run_suite()
                        if self._scheduler_callback:
                            await self._scheduler_callback(suite_result)
                        # Sleep 61s to avoid re-triggering on the same minute
                        await asyncio.sleep(61)
                    else:
                        await asyncio.sleep(60)
            except asyncio.CancelledError:
                pass

        self._scheduler_task = asyncio.ensure_future(_scheduler_loop())

    def stop_scheduler(self) -> None:
        """Stop the background scheduler task."""
        if self._scheduler_task is not None:
            self._scheduler_task.cancel()
            self._scheduler_task = None

    # ------------------------------------------------------------------
    # CI Integration
    # ------------------------------------------------------------------

    def ci_breakdown(self, suite_result: BenchmarkSuiteResult | None = None) -> CIBreakdown:
        """Produce a CI breakdown from a suite result."""
        result = suite_result or (self._history[-1] if self._history else None)
        if result is None:
            return CIBreakdown(
                passed=True,
                total_benchmarks=0,
                passed_benchmarks=0,
                failed_benchmarks=0,
                errored_benchmarks=0,
                exit_code=0,
            )

        total = len(result.results)
        errored = sum(1 for r in result.results if r.error is not None)
        regressed_names = {a.benchmark_name for a in result.regressions}
        has_regressions = len(regressed_names) > 0
        passed_bm = total - len(regressed_names) - errored

        if errored > 0:
            exit_code = 2
            passed = False
        elif has_regressions:
            exit_code = 1
            passed = False
        else:
            exit_code = 0
            passed = True

        return CIBreakdown(
            passed=passed,
            total_benchmarks=total,
            passed_benchmarks=passed_bm,
            failed_benchmarks=len(regressed_names),
            errored_benchmarks=errored,
            exit_code=exit_code,
        )

    # ------------------------------------------------------------------
    # Schedule callback
    # ------------------------------------------------------------------

    def on_scheduled_run(self, callback: Callable) -> None:
        """Register a callback invoked after each scheduled run."""
        self._scheduler_callback = callback

    _scheduler_callback: Callable | None = None

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def summary(self) -> str:
        """Generate a human-readable summary of the last run."""
        if not self._results:
            return "No benchmark results available."

        lines = [
            "| Benchmark           |     pass@1 |     pass@k | Tasks | Duration | Trend |",
            "|---------------------|-----------|-----------|-------|----------|-------|",
        ]
        for r in sorted(self._results.values(), key=lambda x: x.benchmark_name):
            trend = self._trends.get(r.benchmark_name)
            direction = trend.direction if trend else "N/A"
            lines.append(
                f"| {r.benchmark_name:<19s} | "
                f"{r.pass_at_1:>8.1%} | "
                f"{r.pass_at_k:>8.1%} | "
                f"{r.n_tasks:>5d} | "
                f"{r.total_duration_seconds:>6.1f}s | "
                f"{direction} |"
            )
        return "\n".join(lines)

    def result(self, name: str) -> BenchmarkResult | None:
        """Get the most recent result for *name*."""
        return self._results.get(name)

    def report(self) -> BenchmarkReport:
        """Generate a comprehensive BenchmarkReport."""
        suite_result = self._history[-1] if self._history else BenchmarkSuiteResult(results=[])
        # Build trends
        trends: dict[str, BenchmarkTrend] = {}
        for name in self._BENCHMARK_BUILDERS:
            points = []
            for sr in self._history:
                br = sr.by_name(name)
                if br:
                    points.append(TrendPoint(
                        score=br.score,
                        timestamp=br.timestamp,
                        run_id=sr.run_id,
                    ))
            if points:
                trends[name] = BenchmarkTrend(benchmark_name=name, points=points)

        ci = self.ci_breakdown(suite_result) if suite_result.results else None

        return BenchmarkReport(
            suite_result=suite_result,
            history=list(self._history),
            trends=trends,
            ci=ci,
        )

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    @property
    def history(self) -> list[BenchmarkSuiteResult]:
        """Return all previous suite results."""
        return list(self._history)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _resolve_benchmarks(self) -> list[str]:
        """Resolve the config's ``which`` field to a concrete list."""
        if isinstance(self.config.which, list):
            return self.config.which
        if self.config.which == "*":
            return list(self._BENCHMARK_BUILDERS.keys())
        return [self.config.which]

    def _build_runner(self, name: str) -> EvalRunner:
        """Build an EvalRunner for the given benchmark name."""
        builder = self._BENCHMARK_BUILDERS.get(name)
        if builder is None:
            raise ValueError(
                f"Unknown benchmark: {name}. "
                f"Known: {list(self._BENCHMARK_BUILDERS.keys())}"
            )
        return builder({})

    def _update_trends(self, suite_result: BenchmarkSuiteResult) -> None:
        """Update trend data with a new suite result."""
        for br in suite_result.results:
            if br.error:
                continue
            if br.benchmark_name not in self._trends:
                self._trends[br.benchmark_name] = BenchmarkTrend(
                    benchmark_name=br.benchmark_name
                )
            self._trends[br.benchmark_name].points.append(
                TrendPoint(
                    score=br.score,
                    timestamp=br.timestamp,
                    run_id=suite_result.run_id,
                )
            )

    def _persist(self, suite_result: BenchmarkSuiteResult) -> None:
        """Persist results to the output directory."""
        output_dir = Path(self.config.output_dir)  # type: ignore[arg-type]
        output_dir.mkdir(parents=True, exist_ok=True)

        # Write suite result
        suite_file = output_dir / f"suite_{suite_result.run_id}.json"
        with open(suite_file, "w") as f:
            json.dump(
                {
                    "run_id": suite_result.run_id,
                    "timestamp": suite_result.timestamp.isoformat(),
                    "total_duration_seconds": suite_result.total_duration_seconds,
                    "results": [
                        {
                            "benchmark_name": r.benchmark_name,
                            "pass_at_1": r.pass_at_1,
                            "pass_at_k": r.pass_at_k,
                            "k": r.k,
                            "n_tasks": r.n_tasks,
                            "error": r.error,
                        }
                        for r in suite_result.results
                    ],
                    "regressions": [
                        {
                            "benchmark_name": a.benchmark_name,
                            "previous_score": a.previous_score,
                            "current_score": a.current_score,
                            "drop": a.drop,
                        }
                        for a in suite_result.regressions
                    ],
                },
                f,
                indent=2,
            )

    @staticmethod
    def _stub_agent() -> Any:
        """Return a minimal stub agent for testing."""

        class _StubAgent:
            call_count = 0

            async def run(self, prompt: str, **kwargs) -> dict[str, Any]:
                _StubAgent.call_count += 1
                return {
                    "output": f"Stub response to: {prompt[:50]}",
                    "tokens": 150,
                    "cost": 0.01,
                }

        return _StubAgent()
