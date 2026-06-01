"""
Performance Profiling System

Implements comprehensive profiling for:
- CPU profiling
- Memory profiling
- Bottleneck identification
- Performance metrics collection
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
import time
import tracemalloc
from contextlib import contextmanager
from functools import wraps


@dataclass
class ProfileResult:
    """Result of a profiling session"""
    name: str
    duration_ms: float
    memory_peak_mb: float
    memory_current_mb: float
    call_count: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)


class PerformanceProfiler:
    """
    Performance profiler for identifying bottlenecks

    Features:
    - CPU time profiling
    - Memory usage tracking
    - Call count tracking
    - Bottleneck identification
    """

    def __init__(self):
        self.results: List[ProfileResult] = []
        self._active_profiles: Dict[str, float] = {}

    @contextmanager
    def profile(self, name: str, metadata: Optional[Dict[str, Any]] = None):
        """Profile a code block"""
        # Start memory tracking
        tracemalloc.start()
        start_time = time.perf_counter()
        start_memory = tracemalloc.get_traced_memory()[0] / 1024 / 1024  # MB

        try:
            yield
        finally:
            # Calculate metrics
            end_time = time.perf_counter()
            current_memory, peak_memory = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            duration_ms = (end_time - start_time) * 1000
            peak_mb = peak_memory / 1024 / 1024
            current_mb = current_memory / 1024 / 1024

            # Store result
            result = ProfileResult(
                name=name,
                duration_ms=duration_ms,
                memory_peak_mb=peak_mb,
                memory_current_mb=current_mb,
                metadata=metadata or {}
            )
            self.results.append(result)

    def profile_function(self, name: Optional[str] = None):
        """Decorator to profile a function"""
        def decorator(func: Callable) -> Callable:
            profile_name = name or func.__name__

            @wraps(func)
            def wrapper(*args, **kwargs):
                with self.profile(profile_name):
                    return func(*args, **kwargs)
            return wrapper
        return decorator

    def get_bottlenecks(self, threshold_ms: float = 100.0) -> List[ProfileResult]:
        """Get operations slower than threshold"""
        return [r for r in self.results if r.duration_ms > threshold_ms]

    def get_memory_hogs(self, threshold_mb: float = 10.0) -> List[ProfileResult]:
        """Get operations using more memory than threshold"""
        return [r for r in self.results if r.memory_peak_mb > threshold_mb]

    def get_stats(self) -> Dict[str, Any]:
        """Get profiling statistics"""
        if not self.results:
            return {"total_profiles": 0}

        total_time = sum(r.duration_ms for r in self.results)
        total_memory = sum(r.memory_peak_mb for r in self.results)

        return {
            "total_profiles": len(self.results),
            "total_time_ms": total_time,
            "avg_time_ms": total_time / len(self.results),
            "max_time_ms": max(r.duration_ms for r in self.results),
            "total_memory_mb": total_memory,
            "avg_memory_mb": total_memory / len(self.results),
            "max_memory_mb": max(r.memory_peak_mb for r in self.results),
            "bottlenecks": len(self.get_bottlenecks()),
            "memory_hogs": len(self.get_memory_hogs())
        }

    def clear(self):
        """Clear all profiling results"""
        self.results.clear()


# Global profiler instance
_global_profiler: Optional[PerformanceProfiler] = None


def get_profiler() -> PerformanceProfiler:
    """Get the global profiler instance"""
    global _global_profiler
    if _global_profiler is None:
        _global_profiler = PerformanceProfiler()
    return _global_profiler
