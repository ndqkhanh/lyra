"""Performance Optimization & Benchmarking system for Lyra (US-017).

Provides comprehensive performance benchmarking, profiling, optimization,
metrics collection, competitor comparison, and report generation.

Modules:
    benchmark_runner: Standard benchmark runner with baseline comparison
    profiler: Code-level profiling with cProfile integration
    optimizer: Performance optimization suggestion and application
    metrics_collector: Metrics aggregation with percentile computation
    competitor_benchmarks: Competitor comparison suite
    report_generator: Report generation in text, JSON, and markdown
"""

from __future__ import annotations

from lyra_cli.performance.benchmark_runner import (
    BaselineComparison,
    BenchmarkCategory,
    BenchmarkConfig,
    BenchmarkResult,
    BenchmarkRunner,
)
from lyra_cli.performance.competitor_benchmarks import (
    BenchmarkComparison,
    CompetitorBenchmark,
    CompetitorResult,
)
from lyra_cli.performance.metrics_collector import (
    MetricSample,
    MetricsCollector,
    MetricSeries,
)
from lyra_cli.performance.optimizer import (
    OptimizationImpact,
    OptimizationSuggestion,
    PerformanceOptimizer,
)
from lyra_cli.performance.profiler import (
    LyraProfiler,
    ProfileFrame,
    ProfileResult,
)
from lyra_cli.performance.report_generator import (
    ReportConfig,
    ReportGenerator,
)

__all__ = [
    "BaselineComparison",
    "BenchmarkCategory",
    "BenchmarkComparison",
    "BenchmarkConfig",
    "BenchmarkResult",
    "BenchmarkRunner",
    "CompetitorBenchmark",
    "CompetitorResult",
    "LyraProfiler",
    "MetricSample",
    "MetricSeries",
    "MetricsCollector",
    "OptimizationImpact",
    "OptimizationSuggestion",
    "PerformanceOptimizer",
    "ProfileFrame",
    "ProfileResult",
    "ReportConfig",
    "ReportGenerator",
]
