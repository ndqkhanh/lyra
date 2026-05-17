# Eager Tools

Eager tools enable 50% faster agent execution by overlapping tool dispatch with LLM streaming.

## How It Works

Traditional flow:
```
Stream LLM → Wait for message_stop → Dispatch tools → Wait for results
Total time = stream_time + tool_time
```

Eager flow:
```
Stream LLM ──┐
             ├→ Dispatch tools as they seal
             └→ Collect results at message_stop
Total time = max(stream_time, tool_time)
```

## When to Use

**Use eager tools when:**
- Tool-heavy workloads (3+ tools per turn)
- Tools take >100ms to execute
- Tools are idempotent (safe to retry)

**Don't use when:**
- Fast tools (<50ms)
- Sequential dependencies between tools
- Non-idempotent operations (writes, payments, etc.)

## Performance Expectations

- **3-tool workload**: 1.2× speedup
- **9-tool workload**: 1.4× speedup
- **15-tool workload**: 1.5× speedup

## Marking Tools as Idempotent

```python
from lyra_cli.tools import tool

@tool(idempotent=True)
async def search_docs(query: str) -> str:
    """Search documentation (safe to retry)."""
    return await search_api(query)

@tool(idempotent=False)
async def send_email(to: str, body: str) -> str:
    """Send email (NOT safe to retry)."""
    return await email_api(to, body)
```

## Safety Guarantees

- Non-idempotent tools never dispatch early
- Cancellation cleans up in-flight tools
- Exceptions are isolated per tool
- Tool result ordering preserved
