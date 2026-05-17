---
name: async-patterns
description: Asynchronous programming patterns and best practices
origin: ECC
tags: [async, concurrency, patterns]
triggers: [async, await, concurrent]
---

# Async Patterns

## Python Async/Await

```python
import asyncio

async def fetch_data(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

async def main():
    results = await asyncio.gather(
        fetch_data(url1),
        fetch_data(url2),
        fetch_data(url3)
    )
```

## Best Practices

- Use async for I/O-bound operations
- Avoid blocking calls in async functions
- Use asyncio.gather for parallel execution
- Handle exceptions properly
- Use connection pooling

## Common Patterns

- **Producer-Consumer**: Queue-based processing
- **Fan-out/Fan-in**: Parallel processing with aggregation
- **Circuit Breaker**: Prevent cascading failures
