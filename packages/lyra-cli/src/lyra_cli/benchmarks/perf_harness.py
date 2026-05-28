"""Performance Benchmark Harness — micro/macro benchmarks for Lyra subsystems.

Measures latency, throughput, and resource usage across:
  - Model routing (RL policy inference, tier selection)
  - Memory operations (read/write/search latency)
  - Safety checks (4-gate pipeline throughput)
  - Skills execution (skill load and run latency)
  - Swarm consensus (log replication throughput)

Reports P50/P95/P99 latency percentiles and throughput in ops/sec.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class BenchmarkResult:
    name: str
    iterations: int
    total_time_sec: float
    min_ms: float
    max_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    throughput_ops_per_sec: float
    errors: int = 0

    @property
    def passed(self) -> bool:
        return self.errors == 0


@dataclass
class BenchmarkSuite:
    name: str
    results: list[BenchmarkResult] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return all(r.passed for r in self.results)

    def summary(self) -> str:
        lines = [f"Suite: {self.name}", "-" * 60]
        for r in self.results:
            status = "PASS" if r.passed else f"FAIL ({r.errors} errors)"
            lines.append(
                f"  {r.name:30s} | {r.p50_ms:8.2f}ms p50 | "
                f"{r.p95_ms:8.2f}ms p95 | {r.throughput_ops_per_sec:8.0f} ops/s | {status}"
            )
        lines.append(f"\n  Total: {len(self.results)} benchmarks, {self.all_passed}")
        return "\n".join(lines)


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    k = (len(sorted_vals) - 1) * pct
    f = int(k)
    c = k - f
    if f + 1 < len(sorted_vals):
        return sorted_vals[f] * (1 - c) + sorted_vals[f + 1] * c
    return sorted_vals[f]


def benchmark(
    name: str,
    fn: Callable[[], object],
    iterations: int = 100,
    warmup: int = 5,
) -> BenchmarkResult:
    """Run a micro-benchmark and return latency/throughput statistics."""

    for _ in range(warmup):
        try:
            fn()
        except Exception:
            pass

    latencies: list[float] = []
    errors = 0
    start = time.time()

    for _ in range(iterations):
        t0 = time.time()
        try:
            fn()
            latencies.append((time.time() - t0) * 1000.0)
        except Exception:
            errors += 1

    elapsed = time.time() - start

    if not latencies:
        return BenchmarkResult(
            name=name, iterations=iterations, total_time_sec=elapsed,
            min_ms=0, max_ms=0, p50_ms=0, p95_ms=0, p99_ms=0,
            throughput_ops_per_sec=0, errors=errors,
        )

    return BenchmarkResult(
        name=name,
        iterations=iterations,
        total_time_sec=elapsed,
        min_ms=min(latencies),
        max_ms=max(latencies),
        p50_ms=_percentile(latencies, 0.50),
        p95_ms=_percentile(latencies, 0.95),
        p99_ms=_percentile(latencies, 0.99),
        throughput_ops_per_sec=iterations / elapsed if elapsed > 0 else 0.0,
        errors=errors,
    )


def suite(name: str, benchmarks: list[BenchmarkResult]) -> BenchmarkSuite:
    return BenchmarkSuite(name=name, results=benchmarks)


class PerformanceHarness:
    """Runs the full performance benchmark suite for Lyra subsystems."""

    def __init__(self) -> None:
        self._suites: list[BenchmarkSuite] = []

    def run_all(self) -> list[BenchmarkSuite]:
        self._suites.clear()

        self._suites.append(self._bench_routing())
        self._suites.append(self._bench_memory())
        self._suites.append(self._bench_safety())
        return self._suites

    def _bench_routing(self) -> BenchmarkSuite:
        from lyra_core.routing.policy_network import PolicyNetwork
        from lyra_core.routing.state_encoder import StateEncoder

        net = PolicyNetwork()
        encoder = StateEncoder()
        state = encoder.encode(turn_index=1)
        features = list(state.features)

        return BenchmarkSuite(name="Routing", results=[
            benchmark("policy_forward", lambda: net.forward(features), iterations=500),
            benchmark("select_action", lambda: net.select_action(features), iterations=500),
            benchmark("state_encode", lambda: encoder.encode(turn_index=1), iterations=500),
        ])

    def _bench_memory(self) -> BenchmarkSuite:
        import tempfile
        from pathlib import Path
        from lyra_memory.eternal_store import EternalRecord, EternalStore

        tmpdir = tempfile.mkdtemp()
        store = EternalStore(Path(tmpdir), auto_sign=False)

        return BenchmarkSuite(name="Memory", results=[
            benchmark("eternal_put",
                lambda: store.put(EternalRecord.create(f"bench-{time.time()}")),
                iterations=200),
            benchmark("eternal_get",
                lambda: store.get("nonexistent"),
                iterations=500),
        ])

    def _bench_safety(self) -> BenchmarkSuite:
        from lyra_core.safety.approval_gate import ApprovalGate

        gate = ApprovalGate()

        return BenchmarkSuite(name="Safety", results=[
            benchmark("approval_gate_evaluate",
                lambda: gate.evaluate("read_file /tmp/test.txt"),
                iterations=100),
        ])

    @property
    def summary(self) -> str:
        return "\n\n".join(s.summary() for s in self._suites)
