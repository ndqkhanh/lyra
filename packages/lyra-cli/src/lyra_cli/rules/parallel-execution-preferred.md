---
name: parallel-execution-preferred
description: Use parallel execution for independent tasks
category: Performance
severity: medium
enabled: true
---

# Parallel Execution Preferred

Execute independent tasks in parallel for better performance.

## Rule

ALWAYS use parallel execution for independent operations:
- Multiple file reads
- Independent agent tasks
- Parallel test runs
- Concurrent API calls

## Rationale

Parallel execution reduces total execution time and improves throughput.

## Examples

```python
# Wrong - Sequential
result1 = agent1.execute()
result2 = agent2.execute()
result3 = agent3.execute()

# Correct - Parallel
results = await asyncio.gather(
    agent1.execute(),
    agent2.execute(),
    agent3.execute()
)
```
