# Observability Implementation Guide

## Getting Started

This guide walks through implementing observability in Lyra, from basic instrumentation to advanced trace analysis.

## Step 1: Basic Event Emission

### Instrumenting a New Component

**Example**: Adding observability to a custom tool

```python
from lyra_core.observability import SessionContext, emit_event
from lyra_core.hir.events import Tool
from lyra_core.observability.telemetry_bridge import generate_span_id, now_micros
import time
import json

async def my_custom_tool(args: dict, context: SessionContext) -> dict:
    """Custom tool with full observability"""
    
    span_id = generate_span_id()
    
    # 1. Store large payloads as artifacts
    args_ref = context.artifact_store.store(
        json.dumps(args).encode('utf-8'),
        context.session_id
    )
    
    # 2. Emit start event
    await emit_event(context, Tool.call(
        trace_id=context.trace_id,
        span_id=span_id,
        parent_span_id=context.current_span_id,
        ts=now_micros(),
        session_id=context.session_id,
        actor="generator",
        tool="my_custom_tool",
        args_ref=args_ref
    ))
    
    # 3. Execute the actual work
    start = time.monotonic()
    try:
        result = {"status": "success", "data": "..."}
        exit_code = 0
    except Exception as e:
        result = {"status": "error", "message": str(e)}
        exit_code = 1
    finally:
        duration_ms = (time.monotonic() - start) * 1000
    
    # 4. Store result as artifact
    result_ref = context.artifact_store.store(
        json.dumps(result).encode('utf-8'),
        context.session_id
    )
    
    # 5. Emit end event
    await emit_event(context, Tool.result(
        trace_id=context.trace_id,
        span_id=span_id,
        parent_span_id=context.current_span_id,
        ts=now_micros(),
        session_id=context.session_id,
        actor="generator",
        result_ref=result_ref,
        exit_code=exit_code,
        duration_ms=duration_ms
    ))
    
    return result
```

### Instrumenting a Hook

```python
from lyra_core.hir.events import Hook

async def my_post_tool_hook(tool_result: dict, context: SessionContext) -> dict:
    """Hook with observability"""
    
    span_id = generate_span_id()
    hook_name = "my_post_tool_hook"
    
    # Emit start
    await emit_event(context, Hook.start(
        trace_id=context.trace_id,
        span_id=span_id,
        parent_span_id=context.current_span_id,
        ts=now_micros(),
        session_id=context.session_id,
        actor="monitor",
        event="post_tool",
        hook_name=hook_name
    ))
    
    start = time.monotonic()
    try:
        # Hook logic
        modified_result = tool_result.copy()
        modified_result["hook_applied"] = True
        decision = "allow"
    except Exception:
        decision = "error"
    finally:
        duration_ms = (time.monotonic() - start) * 1000
    
    # Emit end
    await emit_event(context, Hook.end(
        trace_id=context.trace_id,
        span_id=span_id,
        parent_span_id=context.current_span_id,
        ts=now_micros(),
        session_id=context.session_id,
        actor="monitor",
        decision=decision,
        duration_ms=duration_ms
    ))
    
    return modified_result
```

## Step 2: Session Management

### Creating a Session Context

```python
from lyra_core.observability import SessionContext, EventBus
from lyra_core.observability.telemetry_bridge import (
    TraceWriter, MetricWriter, ArtifactStore
)

async def start_agent_session(task: str) -> SessionContext:
    """Initialize a new agent session with observability"""
    
    # 1. Generate unique IDs
    session_id = generate_session_id()
    trace_id = generate_trace_id()
    
    # 2. Create session directory
    session_dir = f".lyra/sessions/{session_id}"
    os.makedirs(session_dir, exist_ok=True)
    os.makedirs(f"{session_dir}/artifacts", exist_ok=True)
    
    # 3. Initialize event bus
    event_bus = EventBus(buffer_size=10_000)
    
    # 4. Create writers
    trace_writer = TraceWriter(session_id)
    metric_writer = MetricWriter(session_id)
    artifact_store = ArtifactStore(session_id)
    
    # 5. Subscribe writers to event bus
    event_bus.subscribe(trace_writer)
    event_bus.subscribe(metric_writer)
    
    # 6. Create session context
    context = SessionContext(
        session_id=session_id,
        trace_id=trace_id,
        start_ts=now_micros(),
        event_bus=event_bus,
        trace_writer=trace_writer,
        metric_writer=metric_writer,
        artifact_store=artifact_store
    )
    
    # 7. Emit session start event
    await emit_event(context, AgentLoop.start(
        trace_id=trace_id,
        span_id=generate_span_id(),
        parent_span_id=None,
        ts=now_micros(),
        session_id=session_id,
        actor="generator",
        task=task,
        soul_hash=compute_soul_hash(),
        plan_hash=None
    ))
    
    return context
```

## Step 3: Configuration

### Local Configuration

Create `~/.lyra/config.toml`:

```toml
[observability]
enabled = true
event_buffer_size = 10000
flush_interval = 5
retention_days = 30

[observability.secrets]
enabled = true
patterns = [
    "api[_-]?key",
    "api[_-]?secret",
    "password",
    "token",
    "bearer"
]

[observability.otel]
enabled = false
endpoint = "http://localhost:4317"
protocol = "grpc"
service_name = "lyra"

[observability.metrics]
enabled = true
port = 9090
```

## Step 4: CLI Usage

```bash
# View traces
lyra trace show ses_abc123
lyra trace show ses_abc123 --step 12

# Cost analysis
lyra trace cost ses_abc123 --by actor

# Session management
lyra session list
lyra session grep "implement auth"
```

## Common Pitfalls

### Pitfall 1: Forgetting to Flush

```python
# BAD: No flush
context = await start_agent_session(task)
await my_tool({}, context)
# Events lost on exit

# GOOD: Use context manager
async with managed_session(task) as context:
    await my_tool({}, context)
# Automatic flush
```

### Pitfall 2: Large Payloads

```python
# BAD: Inline large content
await emit_event(context, Tool.result(..., result_ref=large_json))

# GOOD: Store as artifact
ref = context.artifact_store.store(large_json.encode(), session_id)
await emit_event(context, Tool.result(..., result_ref=ref))
```

## References

- [HIR Events](../../packages/lyra-core/src/lyra_core/hir/events.py)
- [Retro Engine](../../packages/lyra-core/src/lyra_core/observability/retro.py)
