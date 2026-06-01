"""
Tests for Performance Profiling System
"""

import pytest
import time
from lyra_core.profiling import (
    PerformanceProfiler,
    ProfileResult,
    get_profiler
)


class TestPerformanceProfiler:
    """Test Performance Profiler"""

    def test_initialization(self):
        """Test profiler initialization"""
        profiler = PerformanceProfiler()
        assert len(profiler.results) == 0

    def test_profile_context_manager(self):
        """Test profiling with context manager"""
        profiler = PerformanceProfiler()

        with profiler.profile("test_operation"):
            time.sleep(0.01)  # 10ms operation

        assert len(profiler.results) == 1
        result = profiler.results[0]
        assert result.name == "test_operation"
        assert result.duration_ms >= 10.0
        assert result.memory_peak_mb >= 0

    def test_profile_decorator(self):
        """Test profiling with decorator"""
        profiler = PerformanceProfiler()

        @profiler.profile_function("decorated_func")
        def slow_function():
            time.sleep(0.01)
            return "done"

        result = slow_function()
        assert result == "done"
        assert len(profiler.results) == 1
        assert profiler.results[0].name == "decorated_func"

    def test_get_bottlenecks(self):
        """Test bottleneck identification"""
        profiler = PerformanceProfiler()

        # Fast operation
        with profiler.profile("fast"):
            time.sleep(0.001)

        # Slow operation
        with profiler.profile("slow"):
            time.sleep(0.15)  # 150ms

        bottlenecks = profiler.get_bottlenecks(threshold_ms=100.0)
        assert len(bottlenecks) == 1
        assert bottlenecks[0].name == "slow"

    def test_get_stats(self):
        """Test statistics collection"""
        profiler = PerformanceProfiler()

        with profiler.profile("op1"):
            time.sleep(0.01)

        with profiler.profile("op2"):
            time.sleep(0.02)

        stats = profiler.get_stats()
        assert stats['total_profiles'] == 2
        assert stats['total_time_ms'] >= 30.0
        assert stats['avg_time_ms'] >= 15.0

    def test_clear(self):
        """Test clearing results"""
        profiler = PerformanceProfiler()

        with profiler.profile("test"):
            pass

        assert len(profiler.results) == 1
        profiler.clear()
        assert len(profiler.results) == 0

    def test_global_profiler(self):
        """Test global profiler instance"""
        profiler1 = get_profiler()
        profiler2 = get_profiler()
        assert profiler1 is profiler2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
