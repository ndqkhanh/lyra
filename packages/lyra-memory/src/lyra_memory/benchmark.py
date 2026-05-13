"""
Performance benchmarking for memory retrieval.

Measures and optimizes retrieval latency to achieve <100ms p95.
"""

import time
from pathlib import Path
from typing import Dict, List
import tempfile
import statistics

from lyra_memory.store import MemoryStore
from lyra_memory.schema import MemoryScope, MemoryType


class MemoryBenchmark:
    """Benchmark memory retrieval performance."""

    def __init__(self, store: MemoryStore):
        """
        Initialize benchmark.

        Args:
            store: Memory store to benchmark
        """
        self.store = store
        self.results: Dict[str, List[float]] = {}

    def benchmark_write(self, num_memories: int = 100) -> Dict[str, float]:
        """
        Benchmark write performance.

        Args:
            num_memories: Number of memories to write

        Returns:
            Performance metrics
        """
        latencies = []

        for i in range(num_memories):
            start = time.perf_counter()
            self.store.write(
                content=f"Test memory {i}: This is a benchmark memory for testing performance",
                scope=MemoryScope.SESSION if i % 2 == 0 else MemoryScope.PROJECT,
                type=MemoryType.SEMANTIC,
            )
            end = time.perf_counter()
            latencies.append((end - start) * 1000)  # Convert to ms

        self.results["write"] = latencies

        return {
            "count": num_memories,
            "mean_ms": statistics.mean(latencies),
            "median_ms": statistics.median(latencies),
            "p95_ms": self._percentile(latencies, 95),
            "p99_ms": self._percentile(latencies, 99),
            "min_ms": min(latencies),
            "max_ms": max(latencies),
        }

    def benchmark_retrieve_bm25(self, num_queries: int = 100) -> Dict[str, float]:
        """
        Benchmark BM25 retrieval performance.

        Args:
            num_queries: Number of queries to run

        Returns:
            Performance metrics
        """
        queries = [
            "test memory",
            "benchmark performance",
            "testing retrieval",
            "memory system",
            "performance optimization",
        ]

        latencies = []

        for i in range(num_queries):
            query = queries[i % len(queries)]
            start = time.perf_counter()
            self.store.retrieve(query, hybrid_alpha=0.0, limit=10)  # Pure BM25
            end = time.perf_counter()
            latencies.append((end - start) * 1000)

        self.results["retrieve_bm25"] = latencies

        return {
            "count": num_queries,
            "mean_ms": statistics.mean(latencies),
            "median_ms": statistics.median(latencies),
            "p95_ms": self._percentile(latencies, 95),
            "p99_ms": self._percentile(latencies, 99),
            "min_ms": min(latencies),
            "max_ms": max(latencies),
        }

    def benchmark_retrieve_hybrid(self, num_queries: int = 100) -> Dict[str, float]:
        """
        Benchmark hybrid retrieval performance.

        Args:
            num_queries: Number of queries to run

        Returns:
            Performance metrics
        """
        queries = [
            "test memory",
            "benchmark performance",
            "testing retrieval",
            "memory system",
            "performance optimization",
        ]

        latencies = []

        for i in range(num_queries):
            query = queries[i % len(queries)]
            start = time.perf_counter()
            self.store.retrieve(query, hybrid_alpha=0.5, limit=10)  # Hybrid
            end = time.perf_counter()
            latencies.append((end - start) * 1000)

        self.results["retrieve_hybrid"] = latencies

        return {
            "count": num_queries,
            "mean_ms": statistics.mean(latencies),
            "median_ms": statistics.median(latencies),
            "p95_ms": self._percentile(latencies, 95),
            "p99_ms": self._percentile(latencies, 99),
            "min_ms": min(latencies),
            "max_ms": max(latencies),
        }

    def benchmark_full_suite(self) -> Dict[str, Dict[str, float]]:
        """
        Run full benchmark suite.

        Returns:
            Complete benchmark results
        """
        print("Running memory performance benchmarks...")

        # Write benchmark
        print("\n1. Write performance...")
        write_results = self.benchmark_write(100)
        print(f"   Mean: {write_results['mean_ms']:.2f}ms")
        print(f"   P95: {write_results['p95_ms']:.2f}ms")

        # BM25 retrieval
        print("\n2. BM25 retrieval performance...")
        bm25_results = self.benchmark_retrieve_bm25(100)
        print(f"   Mean: {bm25_results['mean_ms']:.2f}ms")
        print(f"   P95: {bm25_results['p95_ms']:.2f}ms")

        # Hybrid retrieval
        print("\n3. Hybrid retrieval performance...")
        hybrid_results = self.benchmark_retrieve_hybrid(100)
        print(f"   Mean: {hybrid_results['mean_ms']:.2f}ms")
        print(f"   P95: {hybrid_results['p95_ms']:.2f}ms")

        results = {
            "write": write_results,
            "retrieve_bm25": bm25_results,
            "retrieve_hybrid": hybrid_results,
        }

        # Check if we meet targets
        print("\n" + "=" * 60)
        print("TARGET VALIDATION")
        print("=" * 60)

        targets = {
            "write_p95": 50.0,  # <50ms
            "retrieve_p95": 100.0,  # <100ms
        }

        write_pass = write_results["p95_ms"] < targets["write_p95"]
        bm25_pass = bm25_results["p95_ms"] < targets["retrieve_p95"]
        hybrid_pass = hybrid_results["p95_ms"] < targets["retrieve_p95"]

        print(f"Write P95 < 50ms: {'✓ PASS' if write_pass else '✗ FAIL'} ({write_results['p95_ms']:.2f}ms)")
        print(f"BM25 P95 < 100ms: {'✓ PASS' if bm25_pass else '✗ FAIL'} ({bm25_results['p95_ms']:.2f}ms)")
        print(f"Hybrid P95 < 100ms: {'✓ PASS' if hybrid_pass else '✗ FAIL'} ({hybrid_results['p95_ms']:.2f}ms)")

        all_pass = write_pass and bm25_pass and hybrid_pass
        print(f"\nOverall: {'✓ ALL TARGETS MET' if all_pass else '✗ SOME TARGETS MISSED'}")

        return results

    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile."""
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]


def run_benchmark() -> Dict[str, Dict[str, float]]:
    """
    Run memory benchmark suite.

    Returns:
        Benchmark results
    """
    # Create temporary store
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "benchmark.db"
        store = MemoryStore(db_path, enable_embeddings=False)

        # Run benchmarks
        benchmark = MemoryBenchmark(store)
        results = benchmark.benchmark_full_suite()

        store.close()

    return results


if __name__ == "__main__":
    results = run_benchmark()
