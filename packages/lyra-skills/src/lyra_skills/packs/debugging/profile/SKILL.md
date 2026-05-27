---
id: profile
name: Profile
description: Profile code to identify performance bottlenecks and hot paths.
keywords:
  - profile
  - profiling
  - slow
  - bottleneck
  - perf
  - performance
  - cpu profile
---

1. Run the workload with a profiler attached (cProfile, py-spy, perf, pprof).
2. Identify the top 3 functions by cumulative time.
3. For each hot function, measure: call count, per-call time, total time.
4. Flag any O(n²) or worse complexity in the hot path.
5. Propose targeted optimisations with before/after benchmarks.
