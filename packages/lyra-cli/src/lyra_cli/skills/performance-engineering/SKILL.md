---
name: performance-engineering
description: Profiling, bottleneck identification, and optimization patterns
origin: Plan 13
tags: [performance, profiling, optimization, bottleneck]
triggers: [performance, slow, bottleneck, profiling, optimize, speed]
---

# Performance Engineering

## Profiling Approaches

- **CPU profiling**: Use sampling profiler to find hot functions. Focus on self-time, not inclusive time.
- **Memory profiling**: Heap snapshots to detect leaks, allocation-heavy paths, and GC pressure.
- **I/O profiling**: Trace file reads, network calls, and disk writes. I/O is almost always the bottleneck.
- **Lock profiling**: Contention on mutexes, semaphores, and database row locks.

## Bottleneck Identification Methodology

1. Measure end-to-end latency (not just p50 — track p95, p99)
2. Break down by component (network, app, database)
3. Isolate the slowest 5% of requests — find the pattern
4. Fix one bottleneck at a time, re-measure after each fix

## Optimization Patterns

- **Caching**: Cache at the read-heavy layer closest to the client (CDN > reverse proxy > app > DB). Tune TTLs, not cache keys.
- **Batching**: Replace N individual calls with 1 batched call. Common with DB queries and API clients.
- **Lazy loading**: Defer expensive initialization until first use. Works well for config, connections, images.
- **Connection pooling**: Reuse connections instead of opening per-request. Set min/max pool sizes based on concurrency.

## Benchmarking Setup

- Isolate the system under test (no noisy neighbors)
- Warm up before measuring (JIT, caches)
- Report p50, p95, p99, max, and throughput together
- Never optimize without a reproducible benchmark

## Flame Graph Interpretation

- **Width** = time spent on the stack (inclusive)
- **Tall narrow peak** = deep call chain, look for unnecessary abstraction
- **Wide flat plateau** = expensive leaf function, focus optimization here
- **Plateaus at the top** = system calls (kernel time), often I/O or lock contention

## N+1 Query Detection

Watch for: query count growing linearly with result set size. Fix with eager loading, batch fetching, or a single JOIN query. Monitor query count per request in observability tools.
