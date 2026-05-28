"""Tests for the LyraProfiler module."""

from __future__ import annotations

import time

from lyra_cli.performance.profiler import LyraProfiler, ProfileFrame, ProfileResult


def test_start_stop_returns_result() -> None:
    """Starting and stopping the profiler should return a ProfileResult."""
    profiler = LyraProfiler()
    profiler.start()
    time.sleep(0.001)
    result = profiler.stop()
    assert isinstance(result, ProfileResult)
    assert result.total_duration > 0


def test_markers_track_time() -> None:
    """Markers should accurately track elapsed time between points."""
    profiler = LyraProfiler()
    profiler.mark("start")
    time.sleep(0.01)
    profiler.mark("end")
    elapsed = profiler.time_between("start", "end")
    assert elapsed >= 0.008
    assert elapsed < 0.1


def test_markers_unknown_name_returns_zero() -> None:
    """time_between should return 0 for unknown marker names."""
    profiler = LyraProfiler()
    assert profiler.time_between("nonexistent", "also_missing") == 0.0


def test_profile_function_returns_frame() -> None:
    """profile_function should execute a function and return a ProfileFrame."""

    def add(a: int, b: int) -> int:
        time.sleep(0.002)
        return a + b

    profiler = LyraProfiler()
    result, frame = profiler.profile_function(add, 3, 4)
    assert result == 7
    assert isinstance(frame, ProfileFrame)
    assert frame.function_name == "add"
    assert frame.call_count == 1
    assert frame.total_time >= 0.001


def test_run_profile_returns_result() -> None:
    """run_profile should execute a function and return ProfileResult."""

    def work() -> int:
        total = 0
        for i in range(100):
            total += i
            time.sleep(0.0001)
        return total

    profiler = LyraProfiler()
    result, profile_result = profiler.run_profile(work)
    assert result == 4950
    assert isinstance(profile_result, ProfileResult)
    assert profile_result.total_runs >= 1


def test_hot_paths_sorted_by_time() -> None:
    """hot_paths should sort frames by total_time descending."""
    result = ProfileResult(
        frames=[
            ProfileFrame("func_a", "mod", 5, 10.0, 2.0, 15.0),
            ProfileFrame("func_b", "mod", 3, 30.0, 10.0, 35.0),
            ProfileFrame("func_c", "mod", 1, 5.0, 5.0, 5.0),
        ],
        total_runs=1,
        total_duration=45.0,
    )
    hot = result.hot_paths
    assert hot[0].function_name == "func_b"
    assert hot[1].function_name == "func_a"
    assert hot[2].function_name == "func_c"


def test_most_called_sorted_by_count() -> None:
    """most_called should sort frames by call_count descending."""
    result = ProfileResult(
        frames=[
            ProfileFrame("func_a", "mod", 10, 5.0, 0.5, 8.0),
            ProfileFrame("func_b", "mod", 3, 30.0, 10.0, 35.0),
            ProfileFrame("func_c", "mod", 20, 2.0, 0.1, 3.0),
        ],
        total_runs=1,
        total_duration=37.0,
    )
    top = result.most_called(2)
    assert len(top) == 2
    assert top[0].function_name == "func_c"
    assert top[1].function_name == "func_a"


def test_slowest_and_empty_result() -> None:
    """slowest should return top N and empty result has zero values."""
    result = ProfileResult()
    assert result.slowest(3) == []
    assert result.most_called(3) == []
    assert result.total_calls == 0


def test_reset_clears_everything() -> None:
    """reset should clear all profiler state."""
    profiler = LyraProfiler()
    profiler.start()
    profiler.mark("test")
    profiler.stop()
    assert len(profiler.results) == 1
    profiler.reset()
    assert len(profiler.results) == 0
    assert profiler.time_between("test", "end") == 0.0
