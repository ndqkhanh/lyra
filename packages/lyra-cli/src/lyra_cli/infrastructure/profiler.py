"""Performance profiling and optimization tools.

Provides profiling capabilities for performance analysis:
- Function-level profiling
- Memory profiling
- Performance reports
- Bottleneck identification
"""

from __future__ import annotations

import cProfile
import io
import pstats
import time
import tracemalloc
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Callable, Dict, Iterator, List, Optional, TypeVar

from lyra_cli.logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


@dataclass
class ProfileResult:
    """Result of a profiling session."""

    name: str
    duration_ms: float
    call_count: int
    memory_peak_mb: Optional[float] = None
    memory_current_mb: Optional[float] = None
    stats: Optional[pstats.Stats] = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "duration_ms": self.duration_ms,
            "call_count": self.call_count,
            "memory_peak_mb": self.memory_peak_mb,
            "memory_current_mb": self.memory_current_mb,
            "timestamp": self.timestamp,
        }


@dataclass
class ProfileReport:
    """Comprehensive profiling report."""

    profiles: List[ProfileResult] = field(default_factory=list)
    total_duration_ms: float = 0.0
    bottlenecks: List[Dict[str, Any]] = field(default_factory=list)

    def add_profile(self, result: ProfileResult) -> None:
        """Add a profile result."""
        self.profiles.append(result)
        self.total_duration_ms += result.duration_ms

    def identify_bottlenecks(self, threshold_ms: float = 100.0) -> None:
        """Identify performance bottlenecks.

        Args:
            threshold_ms: Minimum duration to consider as bottleneck
        """
        self.bottlenecks = [
            {
                "name": profile.name,
                "duration_ms": profile.duration_ms,
                "percentage": (profile.duration_ms / self.total_duration_ms * 100)
                if self.total_duration_ms > 0
                else 0,
            }
            for profile in self.profiles
            if profile.duration_ms >= threshold_ms
        ]
        self.bottlenecks.sort(key=lambda x: x["duration_ms"], reverse=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_duration_ms": self.total_duration_ms,
            "profile_count": len(self.profiles),
            "profiles": [p.to_dict() for p in self.profiles],
            "bottlenecks": self.bottlenecks,
        }


class PerformanceProfiler:
    """Performance profiler for analyzing code execution.

    Features:
    - CPU profiling with cProfile
    - Memory profiling with tracemalloc
    - Decorator-based profiling
    - Context manager profiling
    - Report generation
    """

    def __init__(self, enable_memory_profiling: bool = True):
        """Initialize performance profiler.

        Args:
            enable_memory_profiling: Enable memory profiling
        """
        self.enable_memory_profiling = enable_memory_profiling
        self._profiles: List[ProfileResult] = []
        self._active_profilers: Dict[str, cProfile.Profile] = {}

    def profile_function(
        self,
        name: Optional[str] = None,
    ) -> Callable[[Callable[..., T]], Callable[..., T]]:
        """Decorator for profiling functions.

        Args:
            name: Profile name (uses function name if not provided)

        Returns:
            Decorated function
        """
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            profile_name = name or func.__name__

            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> T:
                with self.profile(profile_name):
                    return func(*args, **kwargs)

            return wrapper

        return decorator

    @contextmanager
    def profile(self, name: str) -> Iterator[None]:
        """Context manager for profiling code blocks.

        Args:
            name: Profile name

        Yields:
            None
        """
        # Start CPU profiling
        profiler = cProfile.Profile()
        profiler.enable()

        # Start memory profiling
        if self.enable_memory_profiling:
            tracemalloc.start()

        start_time = time.time()

        try:
            yield
        finally:
            # Stop CPU profiling
            profiler.disable()
            duration_ms = (time.time() - start_time) * 1000

            # Get stats
            stats = pstats.Stats(profiler)
            call_count = stats.total_calls

            # Stop memory profiling
            memory_peak_mb = None
            memory_current_mb = None
            if self.enable_memory_profiling:
                current, peak = tracemalloc.get_traced_memory()
                memory_peak_mb = peak / (1024 * 1024)
                memory_current_mb = current / (1024 * 1024)
                tracemalloc.stop()

            # Store result
            result = ProfileResult(
                name=name,
                duration_ms=duration_ms,
                call_count=call_count,
                memory_peak_mb=memory_peak_mb,
                memory_current_mb=memory_current_mb,
                stats=stats,
            )
            self._profiles.append(result)

            logger.debug(
                f"Profile {name}: {duration_ms:.2f}ms, {call_count} calls",
                extra={
                    "profile_name": name,
                    "duration_ms": duration_ms,
                    "memory_peak_mb": memory_peak_mb,
                },
            )

    def start_profiling(self, name: str) -> None:
        """Start a named profiling session.

        Args:
            name: Profile name
        """
        if name in self._active_profilers:
            logger.warning(f"Profile {name} already active")
            return

        profiler = cProfile.Profile()
        profiler.enable()
        self._active_profilers[name] = profiler

        if self.enable_memory_profiling and not tracemalloc.is_tracing():
            tracemalloc.start()

        logger.debug(f"Started profiling: {name}")

    def stop_profiling(self, name: str) -> Optional[ProfileResult]:
        """Stop a named profiling session.

        Args:
            name: Profile name

        Returns:
            Profile result or None if not found
        """
        if name not in self._active_profilers:
            logger.warning(f"Profile {name} not active")
            return None

        profiler = self._active_profilers.pop(name)
        profiler.disable()

        # Get stats
        stats = pstats.Stats(profiler)
        call_count = stats.total_calls

        # Get memory stats
        memory_peak_mb = None
        memory_current_mb = None
        if self.enable_memory_profiling and tracemalloc.is_tracing():
            current, peak = tracemalloc.get_traced_memory()
            memory_peak_mb = peak / (1024 * 1024)
            memory_current_mb = current / (1024 * 1024)
            if not self._active_profilers:  # Stop if no active profilers
                tracemalloc.stop()

        result = ProfileResult(
            name=name,
            duration_ms=0.0,  # Duration not tracked for manual start/stop
            call_count=call_count,
            memory_peak_mb=memory_peak_mb,
            memory_current_mb=memory_current_mb,
            stats=stats,
        )
        self._profiles.append(result)

        logger.debug(f"Stopped profiling: {name}")
        return result

    def get_profiles(self) -> List[ProfileResult]:
        """Get all profile results."""
        return self._profiles.copy()

    def get_profile(self, name: str) -> Optional[ProfileResult]:
        """Get a specific profile result.

        Args:
            name: Profile name

        Returns:
            Profile result or None if not found
        """
        for profile in reversed(self._profiles):
            if profile.name == name:
                return profile
        return None

    def generate_report(
        self,
        bottleneck_threshold_ms: float = 100.0,
    ) -> ProfileReport:
        """Generate comprehensive profiling report.

        Args:
            bottleneck_threshold_ms: Threshold for identifying bottlenecks

        Returns:
            Profile report
        """
        report = ProfileReport()

        for profile in self._profiles:
            report.add_profile(profile)

        report.identify_bottlenecks(bottleneck_threshold_ms)

        return report

    def print_stats(
        self,
        name: Optional[str] = None,
        sort_by: str = "cumulative",
        limit: int = 20,
    ) -> None:
        """Print profiling statistics.

        Args:
            name: Profile name (prints all if not provided)
            sort_by: Sort key (cumulative, time, calls)
            limit: Number of entries to show
        """
        profiles = self._profiles if name is None else [
            p for p in self._profiles if p.name == name
        ]

        for profile in profiles:
            if profile.stats:
                print(f"\n=== Profile: {profile.name} ===")
                print(f"Duration: {profile.duration_ms:.2f}ms")
                print(f"Calls: {profile.call_count}")
                if profile.memory_peak_mb:
                    print(f"Memory Peak: {profile.memory_peak_mb:.2f}MB")
                print("\nTop functions:")

                stream = io.StringIO()
                stats = profile.stats
                stats.stream = stream
                stats.sort_stats(sort_by)
                stats.print_stats(limit)
                print(stream.getvalue())

    def clear(self) -> None:
        """Clear all profile results."""
        self._profiles.clear()
        logger.debug("Cleared all profiles")


def profile_memory_usage() -> Dict[str, float]:
    """Get current memory usage statistics.

    Returns:
        Memory usage statistics in MB
    """
    import psutil
    import os

    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()

    return {
        "rss_mb": memory_info.rss / (1024 * 1024),
        "vms_mb": memory_info.vms / (1024 * 1024),
        "percent": process.memory_percent(),
    }


def profile_cpu_usage() -> Dict[str, float]:
    """Get current CPU usage statistics.

    Returns:
        CPU usage statistics
    """
    import psutil
    import os

    process = psutil.Process(os.getpid())

    return {
        "percent": process.cpu_percent(interval=0.1),
        "num_threads": process.num_threads(),
    }


__all__ = [
    "ProfileResult",
    "ProfileReport",
    "PerformanceProfiler",
    "profile_memory_usage",
    "profile_cpu_usage",
]
