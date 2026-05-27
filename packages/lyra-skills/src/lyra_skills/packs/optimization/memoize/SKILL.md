---
id: memoize
name: Memoize
description: Apply memoization and computed property caching to avoid redundant computation.
keywords:
  - memoize
  - memo
  - cache
  - useMemo
  - useCallback
  - reselect
  - computed
---

1. Profile to find functions called repeatedly with the same arguments.
2. Check that the function is pure (same inputs → same output, no side effects).
3. Apply memoization: lru_cache, useMemo, reselect, or manual cache.
4. Ensure the cache key covers all relevant inputs.
5. Measure CPU time reduction; verify cache invalidation on mutation.
