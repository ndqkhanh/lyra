"""Tests for infrastructure performance profiler."""

from __future__ import annotations

import time

from lyra_cli.infrastructure.profiler import (
    PerformanceProfiler,
    ProfileReport,
    ProfileResult,
    profile_cpu_usage,
    profile_memory_usage,
)


class TestProfileResult:
    """Tests for ProfileResult."""

    def test_profile_result_creation(self):
        """Test creating a profile result."""
        result = ProfileResult(
            name="test_profile",
            duration_ms=100.0,
            call_count=50,
            memory_peak_mb=10.5,
        )

        assert result.name == "test_profile"
        assert result.duration_ms == 100.0
        assert result.call_count == 50
        assert result.memory_peak_mb == 10.5

    def test_profile_result_to_dict(self):
        """Test converting profile result to dictionary."""
        result = ProfileResult(
            name="test_profile",
            duration_ms=100.0,
            call_count=50,
        )

        result_dict = result.to_dict()
        assert result_dict["name"] == "test_profile"
        assert result_dict["duration_ms"] == 100.0
        assert result_dict["call_count"] == 50


class TestProfileReport:
    """Tests for ProfileReport."""

    def test_profile_report_creation(self):
        """Test creating a profile report."""
        report = ProfileReport()

        assert len(report.profiles) == 0
        assert report.total_duration_ms == 0.0

    def test_add_profile(self):
        """Test adding profiles to report."""
        report = ProfileReport()

        result1 = ProfileResult("profile1", 100.0, 10)
        result2 = ProfileResult("profile2", 200.0, 20)

        report.add_profile(result1)
        report.add_profile(result2)

        assert len(report.profiles) == 2
        assert report.total_duration_ms == 300.0

    def test_identify_bottlenecks(self):
        """Test identifying bottlenecks."""
        report = ProfileReport()

        report.add_profile(ProfileResult("fast", 50.0, 10))
        report.add_profile(ProfileResult("slow", 500.0, 5))
        report.add_profile(ProfileResult("medium", 150.0, 15))

        report.identify_bottlenecks(threshold_ms=100.0)

        assert len(report.bottlenecks) == 2
        assert report.bottlenecks[0]["name"] == "slow"  # Sorted by duration
        assert report.bottlenecks[1]["name"] == "medium"

    def test_report_to_dict(self):
        """Test converting report to dictionary."""
        report = ProfileReport()
        report.add_profile(ProfileResult("profile1", 100.0, 10))

        report_dict = report.to_dict()
        assert "total_duration_ms" in report_dict
        assert "profile_count" in report_dict
        assert "profiles" in report_dict
        assert report_dict["profile_count"] == 1


class TestPerformanceProfiler:
    """Tests for PerformanceProfiler."""

    def test_profiler_initialization(self):
        """Test profiler initialization."""
        profiler = PerformanceProfiler()

        assert profiler.enable_memory_profiling is True
        assert len(profiler.get_profiles()) == 0

    def test_profile_context_manager(self):
        """Test profiling with context manager."""
        profiler = PerformanceProfiler()

        with profiler.profile("test_operation"):
            time.sleep(0.01)  # Simulate work

        profiles = profiler.get_profiles()
        assert len(profiles) == 1
        assert profiles[0].name == "test_operation"
        assert profiles[0].duration_ms >= 10.0  # At least 10ms

    def test_profile_decorator(self):
        """Test profiling with decorator."""
        profiler = PerformanceProfiler()

        @profiler.profile_function("decorated_function")
        def test_function():
            time.sleep(0.01)
            return "result"

        result = test_function()

        assert result == "result"
        profiles = profiler.get_profiles()
        assert len(profiles) == 1
        assert profiles[0].name == "decorated_function"

    def test_start_stop_profiling(self):
        """Test manual start/stop profiling."""
        profiler = PerformanceProfiler()

        profiler.start_profiling("manual_profile")
        time.sleep(0.01)
        result = profiler.stop_profiling("manual_profile")

        assert result is not None
        assert result.name == "manual_profile"

    def test_get_profile_by_name(self):
        """Test getting specific profile by name."""
        profiler = PerformanceProfiler()

        with profiler.profile("profile1"):
            pass

        with profiler.profile("profile2"):
            pass

        profile = profiler.get_profile("profile1")
        assert profile is not None
        assert profile.name == "profile1"

    def test_generate_report(self):
        """Test generating profiling report."""
        profiler = PerformanceProfiler()

        with profiler.profile("operation1"):
            time.sleep(0.01)

        with profiler.profile("operation2"):
            time.sleep(0.02)

        report = profiler.generate_report(bottleneck_threshold_ms=5.0)

        assert len(report.profiles) == 2
        assert report.total_duration_ms >= 30.0

    def test_clear_profiles(self):
        """Test clearing profiles."""
        profiler = PerformanceProfiler()

        with profiler.profile("test"):
            pass

        assert len(profiler.get_profiles()) == 1

        profiler.clear()
        assert len(profiler.get_profiles()) == 0

    def test_nested_profiling(self):
        """Test nested profiling."""
        profiler = PerformanceProfiler()

        with profiler.profile("outer"):
            with profiler.profile("inner"):
                time.sleep(0.01)

        profiles = profiler.get_profiles()
        assert len(profiles) == 2

        outer = profiler.get_profile("outer")
        inner = profiler.get_profile("inner")

        assert outer.duration_ms >= inner.duration_ms

    def test_memory_profiling(self):
        """Test memory profiling."""
        profiler = PerformanceProfiler(enable_memory_profiling=True)

        with profiler.profile("memory_test"):
            # Allocate some memory
            list(range(10000))

        profile = profiler.get_profile("memory_test")
        assert profile.memory_peak_mb is not None
        assert profile.memory_current_mb is not None

    def test_memory_profiling_disabled(self):
        """Test profiling with memory profiling disabled."""
        profiler = PerformanceProfiler(enable_memory_profiling=False)

        with profiler.profile("no_memory"):
            pass

        profile = profiler.get_profile("no_memory")
        assert profile.memory_peak_mb is None
        assert profile.memory_current_mb is None


class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_profile_memory_usage(self):
        """Test profiling memory usage."""
        usage = profile_memory_usage()

        assert "rss_mb" in usage
        assert "vms_mb" in usage
        assert "percent" in usage
        assert usage["rss_mb"] > 0

    def test_profile_cpu_usage(self):
        """Test profiling CPU usage."""
        usage = profile_cpu_usage()

        assert "percent" in usage
        assert "num_threads" in usage
        assert usage["num_threads"] > 0
