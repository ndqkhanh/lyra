"""Code-level profiler for Lyra performance analysis.

Provides LyraProfiler which wraps cProfile for function-level timing,
call counts, and memory allocation tracking to identify hot paths.
"""

from __future__ import annotations

import cProfile
import io
import pstats
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ProfileFrame:
    """A single profile observation for a function."""

    function_name: str
    module: str
    call_count: int
    total_time: float
    per_call_time: float
    cumulative_time: float


@dataclass
class ProfileResult:
    """Aggregated profiling result across one or more runs."""

    frames: list[ProfileFrame] = field(default_factory=list)
    total_runs: int = 0
    total_duration: float = 0.0

    @property
    def hot_paths(self) -> list[ProfileFrame]:
        """Return frames sorted by total time descending.

        Returns:
            Frames ordered by total time, most expensive first.
        """
        return sorted(self.frames, key=lambda f: f.total_time, reverse=True)

    @property
    def top_calls(self) -> list[ProfileFrame]:
        """Return frames sorted by call count descending.

        Returns:
            Frames ordered by call count, most called first.
        """
        return sorted(self.frames, key=lambda f: f.call_count, reverse=True)

    @property
    def total_calls(self) -> int:
        """Total number of function calls across all frames."""
        return sum(f.call_count for f in self.frames)

    def slowest(self, n: int = 5) -> list[ProfileFrame]:
        """Get the n slowest functions by total time.

        Args:
            n: Number of top functions to return.

        Returns:
            List of n slowest ProfileFrame entries.
        """
        return self.hot_paths[:n]

    def most_called(self, n: int = 5) -> list[ProfileFrame]:
        """Get the n most-called functions.

        Args:
            n: Number of top functions to return.

        Returns:
            List of n most-called ProfileFrame entries.
        """
        return self.top_calls[:n]


class LyraProfiler:
    """Profiler for measuring Lyra's code-level performance.

    Integrates cProfile for function timing and call counting,
    and supports manual memory tracking via time-window markers.
    """

    def __init__(self) -> None:
        """Initialize the profiler."""
        self._profiler: cProfile.Profile | None = None
        self._stream: io.StringIO | None = None
        self._markers: dict[str, float] = {}
        self._memory_snapshots: dict[str, float] = {}
        self.results: list[ProfileResult] = []

    def start(self) -> None:
        """Start profiling session.

        Begins cProfile collection and resets markers.
        """
        self._profiler = cProfile.Profile()
        self._profiler.enable()
        self._markers.clear()
        self._memory_snapshots.clear()

    def stop(self) -> ProfileResult:
        """Stop profiling and return aggregated result.

        Returns:
            ProfileResult with collected frames and statistics.
        """
        if self._profiler is None:
            return ProfileResult()

        self._profiler.disable()
        self._stream = io.StringIO()

        sortby = pstats.SortKey.CUMULATIVE
        ps = pstats.Stats(self._profiler, stream=self._stream).sort_stats(sortby)
        ps.print_stats()

        frames: list[ProfileFrame] = []
        for func_info, (cc, _nc, tt, ct, _callers) in ps.stats.items():
            module, _line, func_name = func_info
            per_call = tt / cc if cc > 0 else 0.0
            frames.append(
                ProfileFrame(
                    function_name=func_name,
                    module=module,
                    call_count=cc,
                    total_time=tt,
                    per_call_time=per_call,
                    cumulative_time=ct,
                )
            )

        total_duration = sum(f.total_time for f in frames)
        result = ProfileResult(
            frames=frames,
            total_runs=len(self.results) + 1,
            total_duration=total_duration,
        )
        self.results.append(result)
        self._profiler = None
        self._stream = None
        return result

    def mark(self, name: str) -> None:
        """Record a timestamp marker.

        Args:
            name: Name for this marker.
        """
        self._markers[name] = time.perf_counter()

    def snapshot_memory(self, label: str) -> None:
        """Record a memory snapshot timestamp.

        Args:
            label: Label for this snapshot.
        """
        self._memory_snapshots[label] = time.perf_counter()

    def time_between(self, start: str, end: str) -> float:
        """Compute elapsed time between two markers.

        Args:
            start: Name of start marker.
            end: Name of end marker.

        Returns:
            Elapsed time in seconds between markers.
        """
        if start not in self._markers or end not in self._markers:
            return 0.0
        return self._markers[end] - self._markers[start]

    def profile_function(
        self, fn: Any, *args: Any, **kwargs: Any
    ) -> tuple[Any, ProfileFrame]:
        """Profile a single function call.

        Args:
            fn: Function to profile.
            args: Positional arguments.
            kwargs: Keyword arguments.

        Returns:
            Tuple of (function result, ProfileFrame).
        """
        profiler = cProfile.Profile()
        profiler.enable()
        start = time.perf_counter()

        try:
            result = fn(*args, **kwargs)
        finally:
            elapsed = time.perf_counter() - start
            profiler.disable()

        stream = io.StringIO()
        ps = pstats.Stats(profiler, stream=stream).sort_stats(pstats.SortKey.TIME)
        ps.print_stats()

        frame = ProfileFrame(
            function_name=fn.__name__,
            module=getattr(fn, "__module__", "__unknown__"),
            call_count=1,
            total_time=elapsed,
            per_call_time=elapsed,
            cumulative_time=elapsed,
        )
        return result, frame

    def run_profile(
        self, fn: Any, *args: Any, **kwargs: Any
    ) -> tuple[Any, ProfileResult]:
        """Run a function under full profiling.

        Args:
            fn: Function to profile.
            args: Positional arguments.
            kwargs: Keyword arguments.

        Returns:
            Tuple of (function result, ProfileResult).
        """
        self.start()
        try:
            result = fn(*args, **kwargs)
        finally:
            profile_result = self.stop()
        return result, profile_result

    def reset(self) -> None:
        """Reset all profiling state."""
        self._profiler = None
        self._stream = None
        self._markers.clear()
        self._memory_snapshots.clear()
        self.results.clear()
