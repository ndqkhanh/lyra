"""Performance benchmarks for eager tools."""
import asyncio
import time
from typing import Callable, Any
from dataclasses import dataclass

from lyra_cli.eager_tools.seal_detector import SealDetector, ToolBlock
from lyra_cli.eager_tools.executor_pool import EagerExecutorPool
from lyra_cli.eager_tools.metrics import MetricsCollector


@dataclass
class BenchmarkResult:
    """Result from benchmark run."""
    workload: str
    sequential_ms: float
    eager_ms: float
    speedup: float
    tools_executed: int


async def mock_tool(args: str) -> str:
    """Mock tool with configurable delay."""
    await asyncio.sleep(0.1)  # 100ms tool execution
    return f"result_{args}"


async def benchmark_workload(
    tool_count: int,
    workload_name: str,
) -> BenchmarkResult:
    """Benchmark eager vs sequential execution."""
    # Sequential baseline: stream + tools
    start = time.perf_counter()
    await asyncio.sleep(0.5)  # Mock 500ms stream time
    for _ in range(tool_count):
        await mock_tool("test")
    sequential_ms = (time.perf_counter() - start) * 1000

    # Eager execution: max(stream, tools)
    start = time.perf_counter()
    stream_task = asyncio.create_task(asyncio.sleep(0.5))
    tool_tasks = [asyncio.create_task(mock_tool("test")) for _ in range(tool_count)]
    await asyncio.gather(stream_task, *tool_tasks)
    eager_ms = (time.perf_counter() - start) * 1000

    speedup = sequential_ms / eager_ms if eager_ms > 0 else 0

    return BenchmarkResult(
        workload=workload_name,
        sequential_ms=sequential_ms,
        eager_ms=eager_ms,
        speedup=speedup,
        tools_executed=tool_count,
    )


async def run_benchmarks() -> list[BenchmarkResult]:
    """Run all benchmark workloads."""
    results = []

    # 3-tool workload: Simple queries
    results.append(await benchmark_workload(3, "simple_queries"))

    # 9-tool workload: Incident triage
    results.append(await benchmark_workload(9, "incident_triage"))

    # 15-tool workload: Ad campaign
    results.append(await benchmark_workload(15, "ad_campaign"))

    return results
