"""Tests for performance optimization."""

import asyncio
import time

import pytest

from lyra_ui import (
    Debouncer,
    LazyLoader,
    LRUCache,
    MemoryMonitor,
    PerformanceProfiler,
    VirtualScroller,
)


# LRUCache Tests


def test_lru_cache_init():
    """Test LRU cache initialization."""
    cache = LRUCache(max_size=100)
    assert cache.max_size == 100
    assert len(cache.cache) == 0
    assert cache.hits == 0
    assert cache.misses == 0


def test_lru_cache_set_get():
    """Test setting and getting values."""
    cache = LRUCache()
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"
    assert cache.hits == 1


def test_lru_cache_miss():
    """Test cache miss."""
    cache = LRUCache()
    assert cache.get("nonexistent") is None
    assert cache.misses == 1


def test_lru_cache_ttl():
    """Test TTL expiration."""
    cache = LRUCache()
    cache.set("key1", "value1", ttl=1)
    assert cache.get("key1") == "value1"

    time.sleep(1.1)
    assert cache.get("key1") is None


def test_lru_cache_eviction():
    """Test LRU eviction."""
    cache = LRUCache(max_size=2)
    cache.set("key1", "value1")
    cache.set("key2", "value2")
    cache.set("key3", "value3")

    # key1 should be evicted
    assert cache.get("key1") is None
    assert cache.get("key2") == "value2"
    assert cache.get("key3") == "value3"


def test_lru_cache_clear():
    """Test clearing cache."""
    cache = LRUCache()
    cache.set("key1", "value1")
    cache.set("key2", "value2")

    cache.clear()
    assert len(cache.cache) == 0
    assert cache.hits == 0
    assert cache.misses == 0


def test_lru_cache_stats():
    """Test cache statistics."""
    cache = LRUCache()
    cache.set("key1", "value1")
    cache.get("key1")
    cache.get("key2")

    stats = cache.get_stats()
    assert stats["size"] == 1
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["hit_rate"] == 0.5


# LazyLoader Tests


def test_lazy_loader_init():
    """Test lazy loader initialization."""
    def loader(offset, limit):
        return list(range(offset, offset + limit))

    lazy = LazyLoader(loader, page_size=10)
    assert lazy.page_size == 10
    assert lazy.prefetch is True


def test_lazy_loader_get_page():
    """Test getting page."""
    def loader(offset, limit):
        return list(range(offset, offset + limit))

    lazy = LazyLoader(loader, page_size=10, prefetch=False)
    page = lazy.get_page(0)
    assert page == list(range(0, 10))


def test_lazy_loader_cache():
    """Test page caching."""
    call_count = [0]

    def loader(offset, limit):
        call_count[0] += 1
        return list(range(offset, offset + limit))

    lazy = LazyLoader(loader, page_size=10, prefetch=False)
    lazy.get_page(0)
    lazy.get_page(0)

    assert call_count[0] == 1


def test_lazy_loader_clear_cache():
    """Test clearing cache."""
    def loader(offset, limit):
        return list(range(offset, offset + limit))

    lazy = LazyLoader(loader, page_size=10, prefetch=False)
    lazy.get_page(0)
    assert len(lazy.cache) == 1

    lazy.clear_cache()
    assert len(lazy.cache) == 0


# VirtualScroller Tests


def test_virtual_scroller_init():
    """Test virtual scroller initialization."""
    scroller = VirtualScroller(total_items=100, viewport_height=10)
    assert scroller.total_items == 100
    assert scroller.viewport_height == 10
    assert scroller.scroll_offset == 0


def test_virtual_scroller_visible_range():
    """Test getting visible range."""
    scroller = VirtualScroller(total_items=100, viewport_height=10)
    start, end = scroller.get_visible_range()
    assert start == 0
    assert end == 10


def test_virtual_scroller_scroll_to():
    """Test scrolling to index."""
    scroller = VirtualScroller(total_items=100, viewport_height=10)
    scroller.scroll_to(50)
    assert scroller.scroll_offset == 50


def test_virtual_scroller_scroll_by():
    """Test scrolling by delta."""
    scroller = VirtualScroller(total_items=100, viewport_height=10)
    scroller.scroll_by(5)
    assert scroller.scroll_offset == 5

    scroller.scroll_by(-3)
    assert scroller.scroll_offset == 2


def test_virtual_scroller_bounds():
    """Test scroll bounds."""
    scroller = VirtualScroller(total_items=100, viewport_height=10)

    # Can't scroll below 0
    scroller.scroll_to(-10)
    assert scroller.scroll_offset == 0

    # Can't scroll beyond total - viewport
    scroller.scroll_to(100)
    assert scroller.scroll_offset == 90


# Debouncer Tests


def test_debouncer_init():
    """Test debouncer initialization."""
    debouncer = Debouncer(delay=0.1)
    assert debouncer.delay == 0.1


@pytest.mark.asyncio
async def test_debouncer_debounce():
    """Test debouncing."""
    call_count = [0]

    def func():
        call_count[0] += 1

    debouncer = Debouncer(delay=0.1)
    await debouncer.debounce(func)
    await asyncio.sleep(0.15)

    assert call_count[0] == 1


@pytest.mark.asyncio
async def test_debouncer_cancel_pending():
    """Test canceling pending calls."""
    call_count = [0]

    def func():
        call_count[0] += 1

    debouncer = Debouncer(delay=0.1)
    await debouncer.debounce(func)
    await debouncer.debounce(func)
    await asyncio.sleep(0.15)

    # Only last call should execute
    assert call_count[0] == 1


@pytest.mark.asyncio
async def test_debouncer_cancel():
    """Test manual cancellation."""
    call_count = [0]

    def func():
        call_count[0] += 1

    debouncer = Debouncer(delay=0.1)
    await debouncer.debounce(func)
    debouncer.cancel()
    await asyncio.sleep(0.15)

    assert call_count[0] == 0


# MemoryMonitor Tests


def test_memory_monitor_init():
    """Test memory monitor initialization."""
    monitor = MemoryMonitor(threshold_mb=100.0)
    assert monitor.threshold_mb == 100.0
    assert len(monitor.samples) == 0


def test_memory_monitor_get_memory_usage():
    """Test getting memory usage."""
    monitor = MemoryMonitor()
    usage = monitor.get_memory_usage()
    assert usage > 0


def test_memory_monitor_record_sample():
    """Test recording sample."""
    monitor = MemoryMonitor()
    monitor.record_sample()
    assert len(monitor.samples) == 1


def test_memory_monitor_max_samples():
    """Test max samples limit."""
    monitor = MemoryMonitor()
    monitor.max_samples = 5

    for _ in range(10):
        monitor.record_sample()

    assert len(monitor.samples) == 5


def test_memory_monitor_stats():
    """Test getting statistics."""
    monitor = MemoryMonitor()
    monitor.record_sample()
    monitor.record_sample()

    stats = monitor.get_stats()
    assert "current" in stats
    assert "average" in stats
    assert "peak" in stats


# PerformanceProfiler Tests


def test_performance_profiler_init():
    """Test profiler initialization."""
    profiler = PerformanceProfiler()
    assert len(profiler.timings) == 0


def test_performance_profiler_measure():
    """Test measuring execution time."""
    profiler = PerformanceProfiler()

    with profiler.measure("test"):
        time.sleep(0.1)

    stats = profiler.get_stats("test")
    assert stats["count"] == 1
    assert stats["average"] >= 0.1


def test_performance_profiler_multiple_measurements():
    """Test multiple measurements."""
    profiler = PerformanceProfiler()

    for _ in range(3):
        with profiler.measure("test"):
            time.sleep(0.05)

    stats = profiler.get_stats("test")
    assert stats["count"] == 3


def test_performance_profiler_report():
    """Test getting full report."""
    profiler = PerformanceProfiler()

    with profiler.measure("test1"):
        time.sleep(0.05)

    with profiler.measure("test2"):
        time.sleep(0.05)

    report = profiler.get_report()
    assert "test1" in report
    assert "test2" in report


# Integration Tests


def test_cache_with_loader():
    """Test cache with lazy loader."""
    cache = LRUCache(max_size=10)
    call_count = [0]

    def loader(offset, limit):
        # Check cache first
        key = f"page_{offset}_{limit}"
        cached = cache.get(key)
        if cached:
            return cached

        # Load and cache
        call_count[0] += 1
        data = list(range(offset, offset + limit))
        cache.set(key, data)
        return data

    lazy = LazyLoader(loader, page_size=5, prefetch=False)

    # First load - should call loader
    page1 = lazy.get_page(0)
    assert call_count[0] == 1

    # Second load - LazyLoader has its own cache, so loader won't be called
    page2 = lazy.get_page(0)
    assert call_count[0] == 1  # Still 1 because LazyLoader cached it
    assert page1 == page2

    # Clear LazyLoader's cache
    lazy.clear_cache()

    # Third load - should hit our LRU cache inside loader
    page3 = lazy.get_page(0)
    assert call_count[0] == 1  # Still 1 because LRU cache hit
    assert cache.hits == 1  # LRU cache was hit
    assert page1 == page3


@pytest.mark.asyncio
async def test_debouncer_with_profiler():
    """Test debouncer with profiler."""
    profiler = PerformanceProfiler()
    call_count = [0]

    def func():
        call_count[0] += 1

    debouncer = Debouncer(delay=0.1)

    with profiler.measure("debounce"):
        await debouncer.debounce(func)
        await asyncio.sleep(0.15)

    assert call_count[0] == 1
    stats = profiler.get_stats("debounce")
    assert stats["count"] == 1
