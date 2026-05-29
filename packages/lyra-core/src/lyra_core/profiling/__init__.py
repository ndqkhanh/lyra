"""
Performance Profiling and Benchmarking System

Tracks performance metrics across the system.

Features:
- Function-level profiling
- Memory usage tracking
- Latency measurement
- Benchmark comparisons
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
import time
import functools


@dataclass
class ProfileResult:
    """Result of a profiling operation"""
    name: str
    duration: float
    memory_delta: int = 0
    call_count: int = 1
    metadata: Dict = field(default_factory=dict)

    @property
    def avg_duration(self) -> float:
        """Get average duration per call"""
        return self.duration / self.call_count if self.call_count > 0 else 0.0


@dataclass
class BenchmarkResult:
    """Result of a benchmark comparison"""
    name: str
    baseline_duration: float
    current_duration: float
    speedup: float
    metadata: Dict = field(default_factory=dict)

    @property
    def is_faster(self) -> bool:
        """Check if current is faster than baseline"""
        return self.speedup > 1.0

    @property
    def percentage_change(self) -> float:
        """Get percentage change from baseline"""
        if self.baseline_duration == 0:
            return 0.0
        return ((self.current_duration - self.baseline_duration) / self.baseline_duration) * 100


class Profiler:
    """
    Performance profiler

    Tracks execution time and memory usage for functions and code blocks.
    """

    def __init__(self):
        self.results: Dict[str, ProfileResult] = {}
        self._active_profiles: Dict[str, float] = {}

    def start(self, name: str):
        """Start profiling a code block"""
        self._active_profiles[name] = time.perf_counter()

    def stop(self, name: str) -> ProfileResult:
        """Stop profiling and record result"""
        if name not in self._active_profiles:
            raise ValueError(f"No active profile for {name}")

        start_time = self._active_profiles.pop(name)
        duration = time.perf_counter() - start_time

        if name in self.results:
            # Update existing result
            result = self.results[name]
            result.duration += duration
            result.call_count += 1
        else:
            # Create new result
            result = ProfileResult(name=name, duration=duration)
            self.results[name] = result

        return result

    def profile(self, func: Callable) -> Callable:
        """Decorator to profile a function"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            name = func.__name__
            self.start(name)
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                self.stop(name)
        return wrapper

    def get_result(self, name: str) -> Optional[ProfileResult]:
        """Get profiling result by name"""
        return self.results.get(name)

    def get_all_results(self) -> List[ProfileResult]:
        """Get all profiling results"""
        return list(self.results.values())

    def get_slowest(self, n: int = 5) -> List[ProfileResult]:
        """Get N slowest operations"""
        return sorted(
            self.results.values(),
            key=lambda r: r.duration,
            reverse=True
        )[:n]

    def get_most_called(self, n: int = 5) -> List[ProfileResult]:
        """Get N most called operations"""
        return sorted(
            self.results.values(),
            key=lambda r: r.call_count,
            reverse=True
        )[:n]

    def clear(self):
        """Clear all profiling results"""
        self.results.clear()
        self._active_profiles.clear()

    def get_stats(self) -> Dict:
        """Get profiling statistics"""
        if not self.results:
            return {
                'total_operations': 0,
                'total_duration': 0.0,
                'total_calls': 0
            }

        total_duration = sum(r.duration for r in self.results.values())
        total_calls = sum(r.call_count for r in self.results.values())

        return {
            'total_operations': len(self.results),
            'total_duration': total_duration,
            'total_calls': total_calls,
            'avg_duration': total_duration / len(self.results)
        }


class Benchmark:
    """
    Performance benchmark system

    Compares performance against baselines.
    """

    def __init__(self):
        self.baselines: Dict[str, float] = {}
        self.results: List[BenchmarkResult] = []

    def set_baseline(self, name: str, duration: float):
        """Set baseline duration for a benchmark"""
        self.baselines[name] = duration

    def run(self, name: str, func: Callable, *args, **kwargs) -> BenchmarkResult:
        """Run a benchmark"""
        # Measure current performance
        start = time.perf_counter()
        func(*args, **kwargs)
        current_duration = time.perf_counter() - start

        # Compare to baseline
        baseline_duration = self.baselines.get(name, current_duration)
        speedup = baseline_duration / current_duration if current_duration > 0 else 1.0

        result = BenchmarkResult(
            name=name,
            baseline_duration=baseline_duration,
            current_duration=current_duration,
            speedup=speedup
        )

        self.results.append(result)
        return result

    def compare(self, name: str, func1: Callable, func2: Callable, *args, **kwargs) -> BenchmarkResult:
        """Compare two functions"""
        # Measure func1 (baseline)
        start = time.perf_counter()
        func1(*args, **kwargs)
        baseline_duration = time.perf_counter() - start

        # Measure func2 (current)
        start = time.perf_counter()
        func2(*args, **kwargs)
        current_duration = time.perf_counter() - start

        speedup = baseline_duration / current_duration if current_duration > 0 else 1.0

        result = BenchmarkResult(
            name=name,
            baseline_duration=baseline_duration,
            current_duration=current_duration,
            speedup=speedup
        )

        self.results.append(result)
        return result

    def get_improvements(self) -> List[BenchmarkResult]:
        """Get benchmarks that show improvement"""
        return [r for r in self.results if r.is_faster]

    def get_regressions(self) -> List[BenchmarkResult]:
        """Get benchmarks that show regression"""
        return [r for r in self.results if not r.is_faster]

    def get_stats(self) -> Dict:
        """Get benchmark statistics"""
        if not self.results:
            return {
                'total_benchmarks': 0,
                'improvements': 0,
                'regressions': 0
            }

        improvements = len(self.get_improvements())
        regressions = len(self.get_regressions())

        return {
            'total_benchmarks': len(self.results),
            'improvements': improvements,
            'regressions': regressions,
            'avg_speedup': sum(r.speedup for r in self.results) / len(self.results)
        }


# Global profiler instance
_global_profiler = Profiler()


def profile(func: Callable) -> Callable:
    """Decorator to profile a function using global profiler"""
    return _global_profiler.profile(func)


def get_profiler() -> Profiler:
    """Get global profiler instance"""
    return _global_profiler
