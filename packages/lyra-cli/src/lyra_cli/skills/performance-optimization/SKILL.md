---
name: performance-optimization
description: Performance optimization techniques and patterns
origin: ECC
tags: [performance, optimization, efficiency]
triggers: [performance, optimize, slow]
---

# Performance Optimization

## Profiling First

- Measure before optimizing
- Identify bottlenecks
- Focus on hot paths
- Use profiling tools

## Common Optimizations

### Database
- Add indexes
- Use select_related/prefetch_related
- Avoid N+1 queries
- Implement caching
- Use pagination

### Caching
- Cache expensive computations
- Use Redis/Memcached
- Set appropriate TTLs
- Cache invalidation strategy

### Algorithms
- Choose right data structures
- Optimize time complexity
- Reduce memory usage
- Avoid unnecessary loops

### Python-Specific
- Use generators for large datasets
- List comprehensions over loops
- `__slots__` for memory
- Cython for CPU-intensive code

## Monitoring

- Track response times
- Monitor database queries
- Profile memory usage
- Set performance budgets
