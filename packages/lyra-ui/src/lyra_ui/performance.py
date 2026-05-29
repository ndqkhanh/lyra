"""
Performance Optimization - Performance monitoring and optimization.

Features:
- Lazy loading for large conversations
- Virtual scrolling for message history
- Debounced rendering
- Cache optimization
- Memory monitoring
- Resource management
"""

import asyncio
import inspect
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Generic, TypeVar

T = TypeVar("T")


@dataclass
class CacheEntry:
    """Cache entry with TTL."""

    key: str
    value: Any
    created_at: datetime
    ttl: int | None = None  # seconds
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)

    def is_expired(self) -> bool:
        """Check if entry is expired."""
        if self.ttl is None:
            return False
        age = (datetime.now() - self.created_at).total_seconds()
        return age > self.ttl


class LRUCache:
    """
    LRU (Least Recently Used) cache.

    Features:
    - Size-based eviction
    - TTL support
    - Access tracking
    - Hit/miss statistics
    """

    def __init__(self, max_size: int = 1000, default_ttl: int | None = None):
        """
        Initialize LRU cache.

        Args:
            max_size: Maximum cache size
            default_ttl: Default TTL in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Any | None:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        if key not in self.cache:
            self.misses += 1
            return None

        entry = self.cache[key]

        # Check expiration
        if entry.is_expired():
            del self.cache[key]
            self.misses += 1
            return None

        # Update access stats
        entry.access_count += 1
        entry.last_accessed = datetime.now()

        # Move to end (most recently used)
        self.cache.move_to_end(key)

        self.hits += 1
        return entry.value

    def set(self, key: str, value: Any, ttl: int | None = None):
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: TTL in seconds (overrides default)
        """
        # Remove if exists
        if key in self.cache:
            del self.cache[key]

        # Create entry
        entry = CacheEntry(
            key=key,
            value=value,
            created_at=datetime.now(),
            ttl=ttl if ttl is not None else self.default_ttl,
        )

        # Add to cache
        self.cache[key] = entry

        # Evict if over size
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)

    def clear(self):
        """Clear cache."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0

    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Statistics dictionary
        """
        total = self.hits + self.misses
        hit_rate = self.hits / total if total > 0 else 0.0

        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
        }


class LazyLoader(Generic[T]):
    """
    Lazy loader for large data sets.

    Features:
    - Load data on demand
    - Pagination support
    - Prefetching
    - Memory efficient
    """

    def __init__(
        self,
        loader: Callable[[int, int], list[T]],
        page_size: int = 50,
        prefetch: bool = True,
    ):
        """
        Initialize lazy loader.

        Args:
            loader: Function to load data (offset, limit) -> items
            page_size: Items per page
            prefetch: Enable prefetching
        """
        self.loader = loader
        self.page_size = page_size
        self.prefetch = prefetch
        self.cache: dict[int, list[T]] = {}
        self.total_items: int | None = None

    def get_page(self, page: int) -> list[T]:
        """
        Get page of items.

        Args:
            page: Page number (0-indexed)

        Returns:
            List of items
        """
        if page in self.cache:
            return self.cache[page]

        offset = page * self.page_size
        items = self.loader(offset, self.page_size)
        self.cache[page] = items

        # Prefetch next page
        if self.prefetch and len(items) == self.page_size:
            next_page = page + 1
            if next_page not in self.cache:
                asyncio.create_task(self._prefetch_page(next_page))

        return items

    async def _prefetch_page(self, page: int):
        """Prefetch page in background."""
        offset = page * self.page_size
        items = self.loader(offset, self.page_size)
        self.cache[page] = items

    def clear_cache(self):
        """Clear cached pages."""
        self.cache.clear()


class VirtualScroller:
    """
    Virtual scrolling for large lists.

    Features:
    - Render only visible items
    - Smooth scrolling
    - Dynamic height support
    - Memory efficient
    """

    def __init__(
        self,
        total_items: int,
        viewport_height: int,
        item_height: int = 1,
    ):
        """
        Initialize virtual scroller.

        Args:
            total_items: Total number of items
            viewport_height: Viewport height in items
            item_height: Height of each item
        """
        self.total_items = total_items
        self.viewport_height = viewport_height
        self.item_height = item_height
        self.scroll_offset = 0

    def get_visible_range(self) -> tuple[int, int]:
        """
        Get range of visible items.

        Returns:
            (start_index, end_index)
        """
        start = self.scroll_offset
        end = min(start + self.viewport_height, self.total_items)
        return (start, end)

    def scroll_to(self, index: int):
        """
        Scroll to specific index.

        Args:
            index: Item index
        """
        self.scroll_offset = max(0, min(index, self.total_items - self.viewport_height))

    def scroll_by(self, delta: int):
        """
        Scroll by delta.

        Args:
            delta: Scroll delta (positive = down, negative = up)
        """
        new_offset = self.scroll_offset + delta
        self.scroll_offset = max(
            0, min(new_offset, self.total_items - self.viewport_height)
        )


class Debouncer:
    """
    Debouncer for rate-limiting function calls.

    Features:
    - Delay execution until quiet period
    - Cancel pending calls
    - Async support
    """

    def __init__(self, delay: float = 0.3):
        """
        Initialize debouncer.

        Args:
            delay: Delay in seconds
        """
        self.delay = delay
        self.task: asyncio.Task | None = None

    async def debounce(self, func: Callable, *args, **kwargs):
        """
        Debounce function call.

        Args:
            func: Function to call
            *args: Positional arguments
            **kwargs: Keyword arguments
        """
        # Cancel pending task
        if self.task and not self.task.done():
            self.task.cancel()

        # Create new task
        async def delayed_call():
            await asyncio.sleep(self.delay)
            if inspect.iscoroutinefunction(func):
                await func(*args, **kwargs)
            else:
                func(*args, **kwargs)

        self.task = asyncio.create_task(delayed_call())

    def cancel(self):
        """Cancel pending call."""
        if self.task and not self.task.done():
            self.task.cancel()


class MemoryMonitor:
    """
    Memory usage monitor.

    Features:
    - Track memory usage
    - Memory leak detection
    - Usage alerts
    - Statistics
    """

    def __init__(self, threshold_mb: float = 200.0):
        """
        Initialize memory monitor.

        Args:
            threshold_mb: Alert threshold in MB
        """
        self.threshold_mb = threshold_mb
        self.samples: list[float] = []
        self.max_samples = 100

    def get_memory_usage(self) -> float:
        """
        Get current memory usage in MB.

        Returns:
            Memory usage in MB
        """
        import os

        import psutil

        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024

    def record_sample(self):
        """Record memory usage sample."""
        usage = self.get_memory_usage()
        self.samples.append(usage)

        # Keep only recent samples
        if len(self.samples) > self.max_samples:
            self.samples.pop(0)

    def is_over_threshold(self) -> bool:
        """
        Check if over threshold.

        Returns:
            True if over threshold
        """
        if not self.samples:
            return False
        return self.samples[-1] > self.threshold_mb

    def get_stats(self) -> dict[str, float]:
        """
        Get memory statistics.

        Returns:
            Statistics dictionary
        """
        if not self.samples:
            return {
                "current": 0.0,
                "average": 0.0,
                "peak": 0.0,
                "threshold": self.threshold_mb,
            }

        return {
            "current": self.samples[-1],
            "average": sum(self.samples) / len(self.samples),
            "peak": max(self.samples),
            "threshold": self.threshold_mb,
        }


class PerformanceProfiler:
    """
    Performance profiler.

    Features:
    - Measure execution time
    - Track function calls
    - Generate reports
    """

    def __init__(self):
        """Initialize profiler."""
        self.timings: dict[str, list[float]] = {}

    def measure(self, name: str):
        """
        Context manager for measuring execution time.

        Args:
            name: Measurement name
        """
        return _TimingContext(self, name)

    def record_timing(self, name: str, duration: float):
        """
        Record timing.

        Args:
            name: Measurement name
            duration: Duration in seconds
        """
        if name not in self.timings:
            self.timings[name] = []
        self.timings[name].append(duration)

    def get_stats(self, name: str) -> dict[str, float]:
        """
        Get timing statistics.

        Args:
            name: Measurement name

        Returns:
            Statistics dictionary
        """
        if name not in self.timings or not self.timings[name]:
            return {
                "count": 0,
                "total": 0.0,
                "average": 0.0,
                "min": 0.0,
                "max": 0.0,
            }

        timings = self.timings[name]
        return {
            "count": len(timings),
            "total": sum(timings),
            "average": sum(timings) / len(timings),
            "min": min(timings),
            "max": max(timings),
        }

    def get_report(self) -> dict[str, dict[str, float]]:
        """
        Get full report.

        Returns:
            Report dictionary
        """
        return {name: self.get_stats(name) for name in self.timings}


class _TimingContext:
    """Context manager for timing measurements."""

    def __init__(self, profiler: PerformanceProfiler, name: str):
        """Initialize timing context."""
        self.profiler = profiler
        self.name = name
        self.start_time = 0.0

    def __enter__(self):
        """Start timing."""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timing and record."""
        duration = time.time() - self.start_time
        self.profiler.record_timing(self.name, duration)
        return False
