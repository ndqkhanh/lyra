"""
Tests for Performance Profiling and Benchmarking System
"""

import pytest
import time
from lyra_core.profiling import (
    ProfileResult,
    BenchmarkResult,
    Profiler,
    Benchmark,
    profile,
    get_profiler
)


class TestProfileResult:
    """Test ProfileResult"""

    def test_avg_duration(self):
        """Test average duration calculation"""
        result = ProfileResult(
            name="test",
            duration=10.0,
            call_count=5
        )
        assert result.avg_duration == 2.0


class TestBenchmarkResult:
    """Test BenchmarkResult"""

    def test_is_faster(self):
        """Test is_faster check"""
        faster = BenchmarkResult(
            name="test",
            baseline_duration=2.0,
            current_duration=1.0,
            speedup=2.0
        )
        slower = BenchmarkResult(
            name="test",
            baseline_duration=1.0,
            current_duration=2.0,
            speedup=0.5
        )

        assert faster.is_faster is True
        assert slower.is_faster is False

    def test_percentage_change(self):
        """Test percentage change calculation"""
        result = BenchmarkResult(
            name="test",
            baseline_duration=1.0,
            current_duration=1.5,
            speedup=0.67
        )
        assert result.percentage_change == 50.0


class TestProfiler:
    """Test Profiler"""

    def test_start_stop(self):
        """Test start/stop profiling"""
        profiler = Profiler()
        profiler.start("test")
        time.sleep(0.01)
        result = profiler.stop("test")

        assert result.name == "test"
        assert result.duration > 0

    def test_profile_decorator(self):
        """Test profile decorator"""
        profiler = Profiler()

        @profiler.profile
        def test_func():
            time.sleep(0.01)

        test_func()
        result = profiler.get_result("test_func")

        assert result is not None
        assert result.call_count == 1

    def test_multiple_calls(self):
        """Test profiling multiple calls"""
        profiler = Profiler()

        @profiler.profile
        def test_func():
            pass

        test_func()
        test_func()
        test_func()

        result = profiler.get_result("test_func")
        assert result.call_count == 3

    def test_get_slowest(self):
        """Test getting slowest operations"""
        profiler = Profiler()

        profiler.start("fast")
        profiler.stop("fast")

        profiler.start("slow")
        time.sleep(0.01)
        profiler.stop("slow")

        slowest = profiler.get_slowest(1)
        assert len(slowest) == 1
        assert slowest[0].name == "slow"

    def test_get_stats(self):
        """Test statistics collection"""
        profiler = Profiler()

        profiler.start("op1")
        profiler.stop("op1")

        profiler.start("op2")
        profiler.stop("op2")

        stats = profiler.get_stats()
        assert stats['total_operations'] == 2
        assert stats['total_calls'] == 2


class TestBenchmark:
    """Test Benchmark"""

    def test_set_baseline(self):
        """Test setting baseline"""
        benchmark = Benchmark()
        benchmark.set_baseline("test", 1.0)

        assert benchmark.baselines["test"] == 1.0

    def test_run(self):
        """Test running benchmark"""
        benchmark = Benchmark()
        benchmark.set_baseline("test", 1.0)

        def test_func():
            pass

        result = benchmark.run("test", test_func)
        assert result.name == "test"
        assert result.baseline_duration == 1.0

    def test_compare(self):
        """Test comparing functions"""
        benchmark = Benchmark()

        def slow_func():
            time.sleep(0.01)

        def fast_func():
            pass

        result = benchmark.compare("test", slow_func, fast_func)
        assert result.speedup > 1.0

    def test_get_improvements(self):
        """Test getting improvements"""
        benchmark = Benchmark()

        # Add improvement
        benchmark.results.append(BenchmarkResult(
            name="improved",
            baseline_duration=2.0,
            current_duration=1.0,
            speedup=2.0
        ))

        # Add regression
        benchmark.results.append(BenchmarkResult(
            name="regressed",
            baseline_duration=1.0,
            current_duration=2.0,
            speedup=0.5
        ))

        improvements = benchmark.get_improvements()
        assert len(improvements) == 1
        assert improvements[0].name == "improved"


class TestGlobalProfiler:
    """Test global profiler"""

    def test_profile_decorator(self):
        """Test global profile decorator"""
        @profile
        def test_func():
            pass

        test_func()

        profiler = get_profiler()
        result = profiler.get_result("test_func")
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
