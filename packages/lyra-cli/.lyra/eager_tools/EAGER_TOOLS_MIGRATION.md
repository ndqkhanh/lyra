# Eager Tools Migration Guide

Guide for tool authors to enable eager dispatch for their tools.

## Step 1: Audit for Idempotency

Review each tool and classify:

**Idempotent (safe to retry):**
- Read operations (search, fetch, query)
- Pure computations (parse, transform, validate)
- Cached lookups

**Non-idempotent (NOT safe to retry):**
- Write operations (create, update, delete)
- Side effects (send email, charge payment)
- State mutations (increment counter, acquire lock)

## Step 2: Add Idempotent Flag

```python
# Before
@tool
async def search_docs(query: str) -> str:
    return await search_api(query)

# After
@tool(idempotent=True)
async def search_docs(query: str) -> str:
    return await search_api(query)
```

## Step 3: Implement Gate Callables (Optional)

For conditional eager dispatch:

```python
def can_dispatch_early(args: dict) -> bool:
    """Gate: only dispatch if cache hit likely."""
    return args.get("use_cache", False)

@tool(idempotent=True, gate=can_dispatch_early)
async def expensive_query(query: str, use_cache: bool = False) -> str:
    return await query_api(query, use_cache)
```

## Testing Checklist

- [ ] Tool marked as idempotent=True
- [ ] Tool produces same result when called multiple times
- [ ] Tool has no side effects
- [ ] Tool handles concurrent calls safely
- [ ] Gate callable (if used) returns correct boolean

## Rollback Plan

If issues detected:
1. Set `idempotent=False` to disable eager dispatch
2. Investigate root cause
3. Fix and re-enable
