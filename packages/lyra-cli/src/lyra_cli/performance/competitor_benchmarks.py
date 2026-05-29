"""Competitor benchmarking suite for Lyra.

Compares Lyra performance against Claude Code and Hermes Agent
across task completion time, token efficiency, tool latency, and memory.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class CompetitorName(Enum):
    """Name of a competitor system."""

    LYRA = "Lyra"
    CLAUDE_CODE = "Claude Code"
    HERMES_AGENT = "Hermes Agent"


class BenchmarkDimension(Enum):
    """Performance dimension for competitor comparison."""

    TASK_COMPLETION_TIME = "task_completion_time"
    TOKEN_EFFICIENCY = "token_efficiency"
    TOOL_CALL_LATENCY = "tool_call_latency"
    MEMORY_USAGE = "memory_usage"


@dataclass
class CompetitorResult:
    """Result for a single competitor across a benchmark dimension."""

    competitor: CompetitorName
    dimension: BenchmarkDimension
    value: float
    unit: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def formatted(self) -> str:
        """Human-readable formatted result."""
        return f"{self.competitor.value}: {self.value:.2f} {self.unit}"


@dataclass
class BenchmarkComparison:
    """Comparison of results across competitors for one dimension."""

    dimension: BenchmarkDimension
    results: list[CompetitorResult]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def best(self) -> CompetitorResult | None:
        """Get the best result (lowest value wins for all dimensions)."""
        if not self.results:
            return None
        return min(self.results, key=lambda r: r.value)

    @property
    def worst(self) -> CompetitorResult | None:
        """Get the worst result (highest value)."""
        if not self.results:
            return None
        return max(self.results, key=lambda r: r.value)

    @property
    def ranking(self) -> list[CompetitorResult]:
        """Get results sorted best-to-worst.

        Lower values rank higher for all dimensions.
        """
        return sorted(self.results, key=lambda r: r.value)

    def advantage_vs(self, competitor: CompetitorName) -> dict[str, float]:
        """Calculate Lyra's advantage percentage over a competitor."""
        lyra_result = next(
            (r for r in self.results if r.competitor == CompetitorName.LYRA),
            None,
        )
        comp_result = next(
            (r for r in self.results if r.competitor == competitor),
            None,
        )
        if lyra_result is None or comp_result is None or comp_result.value == 0:
            return {"advantage_pct": 0.0}

        advantage = (comp_result.value - lyra_result.value) / comp_result.value * 100
        return {"advantage_pct": advantage}


class CompetitorBenchmark:
    """Benchmark suite for comparing Lyra vs competitors.

    Measures task completion time, token efficiency, tool call latency,
    and memory usage across Lyra, Claude Code, and Hermes Agent.
    """

    def __init__(self) -> None:
        """Initialize the competitor benchmark suite."""
        self.comparisons: dict[BenchmarkDimension, BenchmarkComparison] = {}

    def benchmark_task_completion(
        self,
        task_name: str,
        lyra_time: float,
        claude_time: float,
        hermes_time: float,
    ) -> BenchmarkComparison:
        """Benchmark task completion time across competitors."""
        results = [
            CompetitorResult(
                competitor=CompetitorName.LYRA,
                dimension=BenchmarkDimension.TASK_COMPLETION_TIME,
                value=lyra_time,
                unit="s",
                metadata={"task": task_name},
            ),
            CompetitorResult(
                competitor=CompetitorName.CLAUDE_CODE,
                dimension=BenchmarkDimension.TASK_COMPLETION_TIME,
                value=claude_time,
                unit="s",
                metadata={"task": task_name},
            ),
            CompetitorResult(
                competitor=CompetitorName.HERMES_AGENT,
                dimension=BenchmarkDimension.TASK_COMPLETION_TIME,
                value=hermes_time,
                unit="s",
                metadata={"task": task_name},
            ),
        ]
        comparison = BenchmarkComparison(
            dimension=BenchmarkDimension.TASK_COMPLETION_TIME,
            results=results,
        )
        self.comparisons[BenchmarkDimension.TASK_COMPLETION_TIME] = comparison
        return comparison

    def benchmark_token_efficiency(
        self,
        task_name: str,
        lyra_ratio: float,
        claude_ratio: float,
        hermes_ratio: float,
    ) -> BenchmarkComparison:
        """Benchmark token efficiency across competitors."""
        results = [
            CompetitorResult(
                competitor=CompetitorName.LYRA,
                dimension=BenchmarkDimension.TOKEN_EFFICIENCY,
                value=lyra_ratio,
                unit="ratio",
                metadata={"task": task_name},
            ),
            CompetitorResult(
                competitor=CompetitorName.CLAUDE_CODE,
                dimension=BenchmarkDimension.TOKEN_EFFICIENCY,
                value=claude_ratio,
                unit="ratio",
                metadata={"task": task_name},
            ),
            CompetitorResult(
                competitor=CompetitorName.HERMES_AGENT,
                dimension=BenchmarkDimension.TOKEN_EFFICIENCY,
                value=hermes_ratio,
                unit="ratio",
                metadata={"task": task_name},
            ),
        ]
        comparison = BenchmarkComparison(
            dimension=BenchmarkDimension.TOKEN_EFFICIENCY,
            results=results,
        )
        self.comparisons[BenchmarkDimension.TOKEN_EFFICIENCY] = comparison
        return comparison

    def benchmark_tool_call_latency(
        self,
        tool_name: str,
        lyra_ms: float,
        claude_ms: float,
        hermes_ms: float,
    ) -> BenchmarkComparison:
        """Benchmark tool call latency across competitors."""
        results = [
            CompetitorResult(
                competitor=CompetitorName.LYRA,
                dimension=BenchmarkDimension.TOOL_CALL_LATENCY,
                value=lyra_ms,
                unit="ms",
                metadata={"tool": tool_name},
            ),
            CompetitorResult(
                competitor=CompetitorName.CLAUDE_CODE,
                dimension=BenchmarkDimension.TOOL_CALL_LATENCY,
                value=claude_ms,
                unit="ms",
                metadata={"tool": tool_name},
            ),
            CompetitorResult(
                competitor=CompetitorName.HERMES_AGENT,
                dimension=BenchmarkDimension.TOOL_CALL_LATENCY,
                value=hermes_ms,
                unit="ms",
                metadata={"tool": tool_name},
            ),
        ]
        comparison = BenchmarkComparison(
            dimension=BenchmarkDimension.TOOL_CALL_LATENCY,
            results=results,
        )
        self.comparisons[BenchmarkDimension.TOOL_CALL_LATENCY] = comparison
        return comparison

    def benchmark_memory_usage(
        self,
        scenario: str,
        lyra_mb: float,
        claude_mb: float,
        hermes_mb: float,
    ) -> BenchmarkComparison:
        """Benchmark memory usage across competitors."""
        results = [
            CompetitorResult(
                competitor=CompetitorName.LYRA,
                dimension=BenchmarkDimension.MEMORY_USAGE,
                value=lyra_mb,
                unit="MB",
                metadata={"scenario": scenario},
            ),
            CompetitorResult(
                competitor=CompetitorName.CLAUDE_CODE,
                dimension=BenchmarkDimension.MEMORY_USAGE,
                value=claude_mb,
                unit="MB",
                metadata={"scenario": scenario},
            ),
            CompetitorResult(
                competitor=CompetitorName.HERMES_AGENT,
                dimension=BenchmarkDimension.MEMORY_USAGE,
                value=hermes_mb,
                unit="MB",
                metadata={"scenario": scenario},
            ),
        ]
        comparison = BenchmarkComparison(
            dimension=BenchmarkDimension.MEMORY_USAGE,
            results=results,
        )
        self.comparisons[BenchmarkDimension.MEMORY_USAGE] = comparison
        return comparison

    def run_all(
        self,
        scenarios: dict[str, dict[str, dict[str, float]]] | None = None,
    ) -> list[BenchmarkComparison]:
        """Run all benchmark dimensions with sample data or provided scenarios."""
        if scenarios:
            return self._run_scenarios(scenarios)

        return self._run_default()

    def _run_default(self) -> list[BenchmarkComparison]:
        """Run benchmarks with default sample data."""
        results: list[BenchmarkComparison] = []

        results.append(
            self.benchmark_task_completion(
                "code_generation", lyra_time=12.5, claude_time=15.2, hermes_time=18.7
            )
        )
        results.append(
            self.benchmark_token_efficiency(
                "code_review", lyra_ratio=0.92, claude_ratio=0.85, hermes_ratio=0.78
            )
        )
        results.append(
            self.benchmark_tool_call_latency(
                "file_read", lyra_ms=45.0, claude_ms=62.0, hermes_ms=80.0
            )
        )
        results.append(
            self.benchmark_memory_usage(
                "session_idle", lyra_mb=128.0, claude_mb=185.0, hermes_mb=220.0
            )
        )

        return results

    def _run_scenarios(
        self, scenarios: dict[str, dict[str, dict[str, float]]]
    ) -> list[BenchmarkComparison]:
        """Run benchmarks from provided scenario data."""
        results: list[BenchmarkComparison] = []
        dimension_map = {
            "task_completion_time": (
                BenchmarkDimension.TASK_COMPLETION_TIME,
                self.benchmark_task_completion,
            ),
            "token_efficiency": (
                BenchmarkDimension.TOKEN_EFFICIENCY,
                self.benchmark_token_efficiency,
            ),
            "tool_call_latency": (
                BenchmarkDimension.TOOL_CALL_LATENCY,
                self.benchmark_tool_call_latency,
            ),
            "memory_usage": (
                BenchmarkDimension.MEMORY_USAGE,
                self.benchmark_memory_usage,
            ),
        }

        for dim_key, (_dim_enum, bench_fn) in dimension_map.items():
            if dim_key not in scenarios:
                continue
            data = scenarios[dim_key]
            lyra_val = data.get("lyra", 0.0)
            claude_val = data.get("claude_code", data.get("claude", 0.0))
            hermes_val = data.get("hermes_agent", data.get("hermes", 0.0))

            comparison = bench_fn(
                f"{dim_key}_scenario", lyra_val, claude_val, hermes_val
            )  # type: ignore[operator]
            results.append(comparison)

        return results

    def advantage_summary(self) -> dict[str, dict[str, float]]:
        """Summarize Lyra's advantage vs each competitor across dimensions."""
        summary: dict[str, dict[str, float]] = {}

        for comp in [CompetitorName.CLAUDE_CODE, CompetitorName.HERMES_AGENT]:
            comp_name = comp.value
            summary[comp_name] = {}
            for dim, comparison in self.comparisons.items():
                adv = comparison.advantage_vs(comp)
                summary[comp_name][dim.value] = adv["advantage_pct"]

        return summary
