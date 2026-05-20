# Phase 9 — Performance & Async Architecture

Modules: `performance.py`, `async_arch.py`, `resource_mgmt.py`

## Performance Optimization (`performance.py`)

LRU caching, lazy loading, virtual scrolling, debouncing, and profiling.

```python
from lyra_ui import (
    LRUCache,
    LazyLoader,
    VirtualScroller,
    Debouncer,
    MemoryMonitor,
    PerformanceProfiler,
)

# LRU cache with TTL
cache = LRUCache(max_size=100, ttl=60.0)
cache.put("key1", "value1")
value = cache.get("key1")

# Lazy loader with pagination
loader = LazyLoader(page_size=20, prefetch=True)
loader.set_data_source(lambda offset, limit: fetch_items(offset, limit))
items = loader.load_page(0)

# Virtual scrolling for huge lists
scroller = VirtualScroller(item_height=20, viewport_height=400)
scroller.set_total_items(10000)
visible = scroller.get_visible_range(scroll_top=200)

# Debouncer for rapid events
debouncer = Debouncer(delay=0.3)
debouncer.debounce(lambda: search(query))

# Memory monitoring
monitor = MemoryMonitor(threshold_mb=500)
monitor.start()
if monitor.is_above_threshold():
    print("Memory alert")
monitor.stop()

# Profiler
profiler = PerformanceProfiler()
with profiler.measure("operation"):
    expensive_work()
stats = profiler.get_stats("operation")
```

## Async Architecture (`async_arch.py`)

Background task queues, worker pools, batching, and connection pools.

```python
import asyncio
from lyra_ui import (
    BackgroundTaskQueue,
    BackgroundTask,
    TaskPriority,
    WorkerPool,
    AsyncFileIO,
    RequestBatcher,
    ConnectionPool,
)

async def main():
    queue = BackgroundTaskQueue(max_workers=4)
    await queue.start()
    await queue.submit(BackgroundTask(
        id="task1",
        coro=some_async_work(),
        priority=TaskPriority.HIGH,
    ))
    await queue.stop()

    pool = WorkerPool(num_workers=8)
    results = await pool.map(process_item, items)

    await AsyncFileIO.write("data.txt", "content")
    content = await AsyncFileIO.read("data.txt")

    batcher = RequestBatcher(batch_size=10, flush_interval=1.0)
    await batcher.add(request)

    pool = ConnectionPool(max_connections=20)
    async with pool.acquire() as conn:
        await conn.execute(query)
```

> Note: `TaskPriority` / `TaskStatus` here are integer-priority enums used by
> the async queue. They are distinct from the agent dashboard's
> `AgentTaskPriority` / `AgentTaskStatus` (string statuses) — see
> [phase-06-dashboard.md](phase-06-dashboard.md).

## Resource Management (`resource_mgmt.py`)

System resource monitoring, leak detection, and cleanup.

```python
from lyra_ui import (
    ResourceMonitor,
    MemoryLeakDetector,
    ResourceCleaner,
    DiskSpaceManager,
    BandwidthOptimizer,
)

monitor = ResourceMonitor()
snapshot = monitor.snapshot()
print(f"CPU: {snapshot.cpu_percent}%, RAM: {snapshot.memory_mb}MB")

detector = MemoryLeakDetector()
detector.start()
# ... run workload ...
leaks = detector.check_leaks()

cleaner = ResourceCleaner()
freed = cleaner.cleanup_temp_files(older_than_hours=24)

disk = DiskSpaceManager(threshold_gb=10.0)
if disk.is_low():
    disk.cleanup_oldest()

optimizer = BandwidthOptimizer(max_bytes_per_sec=1_000_000)
await optimizer.fetch(url)
```

## Components

- `LRUCache`, `LazyLoader`, `VirtualScroller`, `Debouncer`,
  `MemoryMonitor`, `PerformanceProfiler`
- `BackgroundTaskQueue`, `BackgroundTask`, `TaskPriority`, `TaskStatus`,
  `WorkerPool`, `AsyncFileIO`, `RequestBatcher`, `ConnectionPool`
- `ResourceMonitor`, `MemoryLeakDetector`, `ResourceCleaner`,
  `DiskSpaceManager`, `BandwidthOptimizer`
