---
id: memory-leak
name: Memory Leak
description: Diagnose and fix memory leaks using heap analysis and allocation tracing.
keywords:
  - memory leak
  - leak
  - oom
  - out of memory
  - heap
  - memory growth
---

1. Capture a heap dump or allocation profile over time.
2. Identify objects whose count grows monotonically without bound.
3. Trace the reference chain keeping those objects alive.
4. Check for: unclosed resources, circular references, global caches, dangling event listeners.
5. Apply the fix and verify with a soak test.
