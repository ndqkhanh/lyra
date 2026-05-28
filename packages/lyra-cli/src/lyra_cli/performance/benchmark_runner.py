"""Benchmark runner for Lyra performance benchmarking.

Orchestrates standard benchmarks across latency, throughput, memory,
and token efficiency categories, collecting metrics and comparing
results against baselines.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable

from lyra_cli.performance.metrics_collector import MetricsCollector


class BenchmarkCategory(Enum):
    """Category of benchmark to run."""

    LATENCY = "latency"
    THROUGHPUT = "throughput"
    MEMORY = "memory"
    TOKEN_EFFICIENCY = "token_efficiency"


class BenchmarkStatus(Enum):
    """Status of a benchmark execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class BaselineComparison:
    """Comparison of a result against a stored baseline."""

    baseline_value: float
    current_value: float
    change_pct: float
    regressed: bool

    @property
    def summary(self) -> str:
        """Human-readable summary of the comparison."""
        direction = "regressed" if self.regressed else "improved"
        return (
            f"{direction} by {abs(self.change_pct):.1f}% "
            f"({self.current_value:.3f} vs {self.baseline_value:.3f})"
        )


@dataclass
class BenchmarkConfig:
    """Configuration for a single benchmark."""

    name: str
    category: BenchmarkCategory
    benchmark_fn: Callable[[], dict[str, Any]] | None = None
    iterations: int = 5
    warmup_iterations: int = 2
    timeout_seconds: float = 60.0
    baseline_value: float | None = None
    tolerance_pct: float = 10.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkResult:
    """Result of executing a single benchmark."""

    config: BenchmarkConfig
    status: BenchmarkStatus
    metrics: dict[str, float] = field(default_factory=dict)
    duration_seconds: float = 0.0
    error_message: str | None = None
    baseline: BaselineComparison | None = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class BenchmarkRunner:
    """Orchestrates benchmark execution across categories.

    Runs standard benchmarks, collects timing/memory/token metrics,
    and compares results against stored baselines to detect regressions.
    """

    def __init__(self, configs: list[BenchmarkConfig] | None = None) -> None:
        """Initialize runner with optional pre-defined configs.

        Args:
            configs: Pre-defined benchmark configurations. If None,
                     standard default configs are created.
        """
        self.configs: list[BenchmarkConfig] = (
            configs if configs is not None else self._default_configs()
        )
        self.results: list[BenchmarkResult] = []
        self.collector = MetricsCollector()

    @staticmethod
    def _default_configs() -> list[BenchmarkConfig]:
        """Create a standard set of benchmark configurations."""
        configs: list[BenchmarkConfig] = []
        configs.extend(BenchmarkRunner._latency_configs())
        configs.extend(BenchmarkRunner._throughput_configs())
        configs.extend(BenchmarkRunner._memory_configs())
        configs.extend(BenchmarkRunner._token_configs())
        return configs

    @staticmethod
    def _latency_configs() -> list[BenchmarkConfig]:
        """Create latency benchmark configurations."""
        return [
            BenchmarkConfig(
                name="latency_llm_call", category=BenchmarkCategory.LATENCY,
                iterations=10, warmup_iterations=3, baseline_value=500.0,
                metadata={"unit": "ms", "description": "Average LLM call latency"},
            ),
            BenchmarkConfig(
                name="latency_tool_call", category=BenchmarkCategory.LATENCY,
                iterations=20, warmup_iterations=5, baseline_value=50.0,
                metadata={"unit": "ms", "description": "Average tool call latency"},
            ),
        ]

    @staticmethod
    def _throughput_configs() -> list[BenchmarkConfig]:
        """Create throughput benchmark configurations."""
        return [
            BenchmarkConfig(
                name="throughput_commands", category=BenchmarkCategory.THROUGHPUT,
                iterations=3, baseline_value=10.0,
                metadata={"unit": "commands/s", "description": "Command throughput"},
            ),
            BenchmarkConfig(
                name="throughput_tokens", category=BenchmarkCategory.THROUGHPUT,
                iterations=3, baseline_value=1000.0,
                metadata={"unit": "tokens/s", "description": "Token generation throughput"},
            ),
        ]

    @staticmethod
    def _memory_configs() -> list[BenchmarkConfig]:
        """Create memory benchmark configurations."""
        return [
            BenchmarkConfig(
                name="memory_context_load", category=BenchmarkCategory.MEMORY,
                iterations=5, baseline_value=256.0,
                metadata={"unit": "MB", "description": "Memory used loading context"},
            ),
            BenchmarkConfig(
                name="memory_session_state", category=BenchmarkCategory.MEMORY,
                iterations=5, baseline_value=50.0,
                metadata={"unit": "MB", "description": "Memory used per session"},
            ),
        ]

    @staticmethod
    def _token_configs() -> list[BenchmarkConfig]:
        """Create token efficiency benchmark configurations."""
        return [
            BenchmarkConfig(
                name="token_efficiency_prompt", category=BenchmarkCategory.TOKEN_EFFICIENCY,
                iterations=10, baseline_value=0.85,
                metadata={"unit": "ratio", "description": "Prompt token efficiency ratio"},
            ),
            BenchmarkConfig(
                name="token_efficiency_response", category=BenchmarkCategory.TOKEN_EFFICIENCY,
                iterations=10, baseline_value=0.80,
                metadata={"unit": "ratio", "description": "Response token efficiency ratio"},
            ),
        ]

    def run_all(self) -> list[BenchmarkResult]:
        """Run all configured benchmarks.

        Returns:
            List of results for all benchmarks.
        """
        self.results.clear()
        for config in self.configs:
            result = self.run_single(config)
            self.results.append(result)
        return self.results

    def run_category(self, category: BenchmarkCategory) -> list[BenchmarkResult]:
        """Run benchmarks for a specific category."""
        categorized = [c for c in self.configs if c.category == category]
        results: list[BenchmarkResult] = []
        for config in categorized:
            result = self.run_single(config)
            self.results.append(result)
            results.append(result)
        return results

    def run_single(self, config: BenchmarkConfig) -> BenchmarkResult:
        """Execute a single benchmark with warmup and measurement iterations."""
        start = time.perf_counter()

        try:
            warmup_metrics = self._run_warmup(config)
            measurement_metrics = self._run_measurements(config)

            duration = time.perf_counter() - start

            metrics: dict[str, float] = {}
            metrics.update(warmup_metrics)
            metrics.update(measurement_metrics)
            for key, values in self.collector.collected.items():
                if values:
                    metrics[key] = values[-1]

            baseline = self._compare_to_baseline(config, metrics)

            return BenchmarkResult(
                config=config,
                status=BenchmarkStatus.COMPLETE,
                metrics=metrics,
                duration_seconds=duration,
                baseline=baseline,
            )

        except Exception as e:
            duration = time.perf_counter() - start
            return BenchmarkResult(
                config=config,
                status=BenchmarkStatus.FAILED,
                duration_seconds=duration,
                error_message=str(e),
            )

    def _run_warmup(self, config: BenchmarkConfig) -> dict[str, float]:
        """Run warmup iterations to stabilize performance."""
        for _ in range(config.warmup_iterations):
            if config.benchmark_fn:
                config.benchmark_fn()
        return {}

    def _run_measurements(self, config: BenchmarkConfig) -> dict[str, float]:
        """Run measurement iterations and aggregate results."""
        measurements: list[float] = []

        for _ in range(config.iterations):
            iter_start = time.perf_counter()
            if config.benchmark_fn:
                config.benchmark_fn()
            elapsed = (time.perf_counter() - iter_start) * 1000
            measurements.append(elapsed)
            self.collector.record(f"{config.name}_latency_ms", elapsed)

        if not measurements:
            return {}

        p50 = _percentile(measurements, 50)
        p95 = _percentile(measurements, 95)
        p99 = _percentile(measurements, 99)
        mean = sum(measurements) / len(measurements)

        return {
            f"{config.name}_p50_ms": p50,
            f"{config.name}_p95_ms": p95,
            f"{config.name}_p99_ms": p99,
            f"{config.name}_mean_ms": mean,
        }

    def _compare_to_baseline(self, config: BenchmarkConfig, metrics: dict[str, float]) -> BaselineComparison | None:
        """Compare results against a stored baseline value."""
        if config.baseline_value is None:
            return None

        metric_key = f"{config.name}_mean_ms"
        current = metrics.get(metric_key, 0.0)
        if current == 0:
            return None

        change_pct = ((current - config.baseline_value) / config.baseline_value) * 100
        regressed = change_pct > config.tolerance_pct

        return BaselineComparison(
            baseline_value=config.baseline_value,
            current_value=current,
            change_pct=change_pct,
            regressed=regressed,
        )

    def detect_regressions(self) -> list[BenchmarkResult]:
        """Find benchmark results that have regressed against baselines."""
        return [
            r
            for r in self.results
            if r.baseline is not None and r.baseline.regressed
        ]

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of all benchmark results."""
        completed = [r for r in self.results if r.status == BenchmarkStatus.COMPLETE]
        failed = [r for r in self.results if r.status == BenchmarkStatus.FAILED]
        regressed = self.detect_regressions()

        return {
            "total": len(self.results),
            "completed": len(completed),
            "failed": len(failed),
            "regressed": len(regressed),
            "by_category": {
                cat.value: len([r for r in self.results if r.config.category == cat])
                for cat in BenchmarkCategory
            },
            "timestamp": datetime.now().isoformat(),
        }

    def export_results(self, path: str) -> None:
        """Export benchmark results to a JSON file.

        Args:
            path: Output file path.
        """
        data = {
            "summary": self.get_summary(),
            "results": [
                {
                    "name": r.config.name,
                    "category": r.config.category.value,
                    "status": r.status.value,
                    "metrics": r.metrics,
                    "duration_seconds": r.duration_seconds,
                    "error": r.error_message,
                    "baseline": {
                        "value": r.baseline.baseline_value,
                        "change_pct": r.baseline.change_pct,
                        "regressed": r.baseline.regressed,
                    }
                    if r.baseline
                    else None,
                }
                for r in self.results
            ],
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)


def _percentile(values: list[float], p: int) -> float:
    """Compute the p-th percentile of a list of values.

    Args:
        values: Sorted or unsorted list of floats.
        p: Percentile to compute (0-100).

    Returns:
        The p-th percentile value.
    """
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    k = (p / 100.0) * (len(sorted_vals) - 1)
    f_idx = int(k)
    c_idx = f_idx + 1
    if f_idx >= len(sorted_vals) - 1:
        return sorted_vals[-1]
    frac = k - f_idx
    return sorted_vals[f_idx] * (1 - frac) + sorted_vals[c_idx] * frac
