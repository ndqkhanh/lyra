# Observability Deep Dive

## Advanced Patterns

This document covers advanced observability patterns, optimization techniques, edge cases, and internal algorithms.

## Pattern 1: Distributed Tracing Across Subagents

### Challenge
When spawning subagents, maintain trace continuity across process boundaries.

### Solution: W3C Trace Context Propagation

```python
from lyra_core.observability.telemetry_bridge import propagate_trace_context

async def spawn_subagent(task: str, parent_context: SessionContext) -> dict:
    """Spawn subagent with trace propagation"""
    
    # 1. Generate new span for subagent
    subagent_span_id = generate_span_id()
    
    # 2. Emit spawn event in parent
    await emit_event(parent_context, Subagent.spawn(
        trace_id=parent_context.trace_id,  # Same trace
        span_id=subagent_span_id,
        parent_span_id=parent_context.current_span_id,
        ts=now_micros(),
        session_id=parent_context.session_id,
        actor="scheduler",
        id=f"subagent_{subagent_span_id}",
        purpose=task,
        scope="isolated",
        budget={"max_cost": 0.10}
    ))
    
    # 3. Propagate trace context to subagent process
    trace_context = {
        "traceparent": f"00-{parent_context.trace_id}-{subagent_span_id}-01",
        "tracestate": f"lyra=session:{parent_context.session_id}",
    }
    
    # 4. Launch subagent with injected context
    result = await subprocess_run([
        "lyra", "agent", "run",
        "--task", task,
        "--trace-parent", trace_context["traceparent"],
        "--trace-state", trace_context["tracestate"]
    ])
    
    # 5. Emit result event
    await emit_event(parent_context, Subagent.result(
        trace_id=parent_context.trace_id,
        span_id=subagent_span_id,
        parent_span_id=parent_context.current_span_id,
        ts=now_micros(),
        session_id=parent_context.session_id,
        actor="scheduler",
        id=f"subagent_{subagent_span_id}",
        outcome="success",
        summary_ref=artifact_store.store(result.encode(), session_id)
    ))
    
    return result
```

### Trace Stitching

When collecting traces from multiple subagents:

```python
class MultiAgentTraceAggregator:
    """Merge traces from parent and subagent sessions"""
    
    def merge_traces(self, parent_session: str, subagent_sessions: List[str]) -> List[HIREvent]:
        """Reconstruct unified trace from distributed sessions"""
        
        all_events = []
        
        # 1. Load parent trace
        parent_events = self._load_trace(parent_session)
        all_events.extend(parent_events)
        
        # 2. Load subagent traces
        for sub_session in subagent_sessions:
            sub_events = self._load_trace(sub_session)
            
            # 3. Find matching spawn/result events in parent
            spawn_event = next(e for e in parent_events 
                             if e["event_type"] == "Subagent.spawn" 
                             and e["id"] == sub_session)
            
            # 4. Adjust subagent timestamps relative to spawn
            offset = spawn_event["ts"]
            for event in sub_events:
                event["ts"] += offset
                event["parent_session_id"] = parent_session
            
            all_events.extend(sub_events)
        
        # 5. Sort by timestamp for chronological order
        all_events.sort(key=lambda e: e["ts"])
        
        return all_events
```

## Pattern 2: Adaptive Sampling

### Challenge
High-frequency events (e.g., token streaming) generate too many spans.

### Solution: Dynamic Sampling Strategy

```python
class AdaptiveSampler:
    """Dynamically adjust sampling rate based on event frequency"""
    
    def __init__(self):
        self.event_counts = defaultdict(int)
        self.sample_rates = defaultdict(lambda: 1.0)
        self.window_start = time.time()
    
    def should_sample(self, event_type: str) -> bool:
        """Decide whether to emit this event"""
        
        # Always sample critical events
        if event_type in ["AgentLoop.start", "AgentLoop.end", "Safety.check"]:
            return True
        
        # Check if window expired (10 seconds)
        now = time.time()
        if now - self.window_start > 10:
            self._adjust_rates()
            self.window_start = now
        
        # Increment counter
        self.event_counts[event_type] += 1
        
        # Sample based on rate
        return random.random() < self.sample_rates[event_type]
    
    def _adjust_rates(self):
        """Adjust sampling rates based on observed frequencies"""
        
        for event_type, count in self.event_counts.items():
            rate_per_sec = count / 10.0
            
            if rate_per_sec > 100:
                # High frequency: sample 10%
                self.sample_rates[event_type] = 0.1
            elif rate_per_sec > 10:
                # Medium frequency: sample 50%
                self.sample_rates[event_type] = 0.5
            else:
                # Low frequency: sample 100%
                self.sample_rates[event_type] = 1.0
        
        # Reset counts for next window
        self.event_counts.clear()

# Usage in instrumentation
sampler = AdaptiveSampler()

async def emit_event_sampled(context: SessionContext, event: HIREvent) -> None:
    if sampler.should_sample(event.event_type):
        await emit_event(context, event)
```

## Pattern 3: Trace Compression

### Challenge
Long sessions generate multi-gigabyte traces that are slow to load.

### Solution: Hierarchical Trace Digests

```python
class TraceDigester:
    """Create compressed trace summaries for evaluators"""
    
    def digest(self, session_id: str, max_events: int = 1000) -> dict:
        """Create trace digest with key events and statistics"""
        
        events = self._load_trace(session_id)
        
        # 1. Always include critical events
        critical = [e for e in events if e["event_type"] in [
            "AgentLoop.start", "AgentLoop.end",
            "Evaluator.verdict", "Safety.check",
            "TDD.state_change"
        ]]
        
        # 2. Sample intermediate events
        intermediate = [e for e in events if e not in critical]
        if len(intermediate) > max_events - len(critical):
            # Stratified sampling across time buckets
            intermediate = self._stratified_sample(
                intermediate, 
                max_events - len(critical)
            )
        
        # 3. Compute aggregate statistics
        stats = {
            "total_events": len(events),
            "sampled_events": len(critical) + len(intermediate),
            "sampling_ratio": (len(critical) + len(intermediate)) / len(events),
            "cost_by_actor": self._aggregate_cost(events),
            "tools_used": self._aggregate_tools(events),
            "duration_by_phase": self._aggregate_durations(events)
        }
        
        return {
            "session_id": session_id,
            "events": critical + intermediate,
            "statistics": stats,
            "digest_version": "1.0"
        }
    
    def _stratified_sample(self, events: List[dict], n: int) -> List[dict]:
        """Sample n events uniformly across time buckets"""
        
        if not events:
            return []
        
        # Divide timeline into buckets
        min_ts = min(e["ts"] for e in events)
        max_ts = max(e["ts"] for e in events)
        bucket_size = (max_ts - min_ts) / n
        
        sampled = []
        for i in range(n):
            bucket_start = min_ts + i * bucket_size
            bucket_end = bucket_start + bucket_size
            
            # Pick one event from bucket
            bucket_events = [e for e in events 
                           if bucket_start <= e["ts"] < bucket_end]
            if bucket_events:
                sampled.append(random.choice(bucket_events))
        
        return sampled
```

## Optimization: Zero-Copy Event Publishing

### Challenge
Copying event objects on publish adds latency and memory pressure.

### Solution: Immutable Events with Shared References

```python
from dataclasses import dataclass, field

@dataclass(frozen=True)
class HIREvent:
    """Immutable event (frozen=True prevents modification)"""
    trace_id: str
    span_id: str
    # ... other fields
    
    # Shared reference to large payload
    _payload: Optional[bytes] = field(default=None, repr=False, compare=False)
    
    @property
    def payload(self) -> Optional[bytes]:
        """Access payload without copying"""
        return self._payload

class EventBus:
    async def publish(self, event: HIREvent) -> None:
        """Publish without copying (event is immutable)"""
        
        # Zero-copy: just append reference to buffer
        self._buffer.append(event)
        
        # Subscribers receive same object (safe due to immutability)
        await self._notify_subscribers(event)
```

## Optimization: Batch OTLP Export

### Challenge
Individual span exports have high per-request overhead.

### Solution: Batched Export with Backpressure

```python
class BatchedOTLPExporter(EventConsumer):
    """Batch spans for efficient OTLP export"""
    
    def __init__(self, endpoint: str, batch_size: int = 100, flush_interval: float = 5.0):
        self.endpoint = endpoint
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        
        self.buffer = []
        self.last_flush = time.time()
        self.lock = asyncio.Lock()
    
    async def on_event(self, event: HIREvent) -> None:
        """Buffer event for batched export"""
        
        async with self.lock:
            self.buffer.append(event)
            
            # Flush if batch full or interval elapsed
            should_flush = (
                len(self.buffer) >= self.batch_size or
                time.time() - self.last_flush >= self.flush_interval
            )
            
            if should_flush:
                await self._flush_batch()
    
    async def _flush_batch(self) -> None:
        """Export batch of spans to OTLP endpoint"""
        
        if not self.buffer:
            return
        
        # Convert HIR events to OTel spans
        spans = [self._hir_to_otel(event) for event in self.buffer]
        
        # Export batch over gRPC
        try:
            await self._export_batch(spans)
            self.buffer.clear()
            self.last_flush = time.time()
        except Exception as e:
            logger.error(f"OTLP export failed: {e}")
            # Retain buffer for retry
```

## Edge Case: Clock Skew

### Problem
Distributed agents on different machines may have clock skew.

### Solution: Monotonic Ordering with Logical Clocks

```python
class LogicalClock:
    """Lamport-style logical clock for event ordering"""
    
    def __init__(self):
        self.counter = 0
        self.lock = threading.Lock()
    
    def tick(self) -> int:
        """Increment and return counter"""
        with self.lock:
            self.counter += 1
            return self.counter
    
    def update(self, received_counter: int) -> None:
        """Update from received event"""
        with self.lock:
            self.counter = max(self.counter, received_counter) + 1

@dataclass(frozen=True)
class HIREvent:
    ts: int                    # Wall clock (microseconds)
    logical_ts: int            # Logical clock for ordering
    # ...

# In event emission
logical_clock = LogicalClock()

async def emit_event(context: SessionContext, event: HIREvent) -> None:
    event = replace(event, 
                   ts=now_micros(),
                   logical_ts=context.logical_clock.tick())
    await context.event_bus.publish(event)

# In trace reconstruction
def sort_events_correctly(events: List[HIREvent]) -> List[HIREvent]:
    """Sort by logical clock, break ties with wall clock"""
    return sorted(events, key=lambda e: (e.logical_ts, e.ts))
```

## Edge Case: Trace Size Limits

### Problem
Some backends (Jaeger, Zipkin) have max span limits per trace.

### Solution: Trace Splitting with Correlation

```python
class TraceSplitter:
    """Split large traces into linked sub-traces"""
    
    def __init__(self, max_spans_per_trace: int = 10_000):
        self.max_spans = max_spans_per_trace
        self.trace_counter = 0
    
    def should_split(self, event_count: int) -> bool:
        return event_count > 0 and event_count % self.max_spans == 0
    
    def create_split_trace(self, parent_trace_id: str) -> str:
        """Create new trace ID linked to parent"""
        self.trace_counter += 1
        return f"{parent_trace_id}-{self.trace_counter:04d}"

# In session context
class SessionContext:
    def __init__(self, ...):
        self.trace_id = generate_trace_id()
        self.trace_splitter = TraceSplitter()
        self.current_trace_id = self.trace_id
    
    async def emit(self, event: HIREvent) -> None:
        # Check if trace should be split
        if self.trace_splitter.should_split(self.event_count):
            self.current_trace_id = self.trace_splitter.create_split_trace(self.trace_id)
            logger.info(f"Split trace: {self.trace_id} -> {self.current_trace_id}")
        
        # Use current trace ID
        event = replace(event, trace_id=self.current_trace_id)
        await self.event_bus.publish(event)
```

## Internal Algorithm: Cost Attribution

### Implementation

```python
def compute_cost_attribution(events: List[HIREvent]) -> dict:
    """Attribute costs across actors, models, and tools"""
    
    # Build cost tree
    cost_tree = {
        "by_actor": defaultdict(Decimal),
        "by_model": defaultdict(Decimal),
        "by_tool": defaultdict(Decimal),
        "by_phase": defaultdict(Decimal)
    }
    
    for event in events:
        if event.event_type == "AgentLoop.step":
            # Extract cost from token usage
            model = event.metadata.get("model")
            usage = event.metadata.get("usage", {})
            
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            
            # Model-specific pricing
            pricing = get_model_pricing(model)
            cost = (
                Decimal(prompt_tokens) * pricing["prompt_per_1k"] / 1000 +
                Decimal(completion_tokens) * pricing["completion_per_1k"] / 1000
            )
            
            # Attribute to actor
            actor = event.actor
            cost_tree["by_actor"][actor] += cost
            cost_tree["by_model"][model] += cost
            
            # Attribute to current tool (if in tool call span)
            if event.parent_span_id:
                parent = find_event_by_span(events, event.parent_span_id)
                if parent and parent.event_type == "Tool.call":
                    cost_tree["by_tool"][parent.metadata["tool"]] += cost
    
    return cost_tree
```

## Research References

### HIR Standardization
- [Gnomon HIR Spec](https://github.com/lyra-contributors/gnomon-hir)
- [OpenTelemetry GenAI Conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/)

### Distributed Tracing
- [W3C Trace Context](https://www.w3.org/TR/trace-context/)
- [Dapper (Google)](https://research.google/pubs/pub36356/)

### Adaptive Sampling
- [Reservoir Sampling Algorithm](https://en.wikipedia.org/wiki/Reservoir_sampling)
- [Stratified Sampling](https://en.wikipedia.org/wiki/Stratified_sampling)

## Future Improvements

### 1. Machine Learning-Based Anomaly Detection

```python
class TraceAnomalyDetector:
    """Detect anomalous agent behavior from traces"""
    
    def train(self, normal_traces: List[str]) -> None:
        """Train on successful traces"""
        
    def detect_anomalies(self, trace: List[HIREvent]) -> List[dict]:
        """Return anomaly scores for suspicious events"""
```

### 2. Query Language for Traces

```sql
-- Proposed TraceQL syntax
SELECT event_type, COUNT(*) as count
FROM trace('ses_abc123')
WHERE actor = 'generator' AND duration_ms > 1000
GROUP BY event_type
ORDER BY count DESC;
```

### 3. Real-Time Trace Streaming

```python
class TraceStreamer:
    """Stream trace events to web dashboard via WebSocket"""
    
    async def stream(self, session_id: str, websocket: WebSocket):
        """Push events as they occur"""
```

## References

- [Event Bus](../../packages/lyra-core/src/lyra_core/observability/event_bus.py)
- [Retro Engine](../../packages/lyra-core/src/lyra_core/observability/retro.py)
- [OTLP Exporter](../../packages/lyra-core/src/lyra_core/observability/otel_export.py)
