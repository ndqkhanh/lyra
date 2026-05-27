# Lyra Eager Tools Integration Ultra Plan

**Version**: 1.0.0  
**Created**: 2026-05-17  
**Status**: Planning  
**Based on**: CloudThinker eager-tools (GitHub + blog research)

---

## Executive Summary

This plan integrates **eager tool calling** into Lyra to achieve 1.2×–1.5× faster agent execution by overlapping tool execution with LLM streaming, rather than waiting for `message_stop`.

**Current State**:
- Lyra executes tools after LLM completes streaming
- Tools run in parallel with each other (good)
- But stream phase and tool phase are sequential (bottleneck)
- Wall clock = stream time + tool time (added serially)

**Target State**:
- Tools dispatch the moment their JSON block completes in stream
- Wall clock = max(stream time, max(tool time)) (overlapped)
- 50% faster median task completion (per CloudThinker benchmarks)
- Idempotency checks prevent unsafe eager dispatch

**Success Criteria**:
- 1.2×–1.5× speedup on tool-heavy workloads
- Zero regressions on non-idempotent operations
- Graceful fallback for non-streaming backends
- Observable seal latency metrics

---

## Phase 1: Current State Analysis (Week 1)

### Objectives
Understand Lyra's existing tool execution pipeline and identify integration points.

### Tasks

#### T101: Map Lyra's Tool Execution Flow
**Priority**: P0 | **Effort**: 4 hours | **Risk**: Low

Analyze:
- Where tools are registered and dispatched
- How streaming responses are handled
- Current parallelization strategy
- Provider-specific streaming implementations

**Deliverable**: Architecture diagram of current tool flow

---

#### T102: Identify Idempotent vs Non-Idempotent Tools
**Priority**: P0 | **Effort**: 6 hours | **Risk**: Medium

Audit all Lyra tools and classify:
- **Safe for eager**: Read-only operations (file reads, API queries, searches)
- **Unsafe for eager**: Writes, payments, destructive ops, outbound messages
- **Conditional**: Tools that need argument inspection (e.g., file write with --dry-run)

**Deliverable**: Tool safety matrix with idempotency flags

---

#### T103: Benchmark Current Performance
**Priority**: P0 | **Effort**: 4 hours | **Risk**: Low

Establish baseline metrics:
- Stream time vs tool time distribution
- Tool count per agent turn
- Sequential vs parallel tool execution times
- End-to-end task completion times

**Deliverable**: Performance baseline report

---

## Phase 2: Seal Detection Engine (Week 2-3)

### Objectives
Build the core seal detection mechanism for Anthropic/OpenAI streams.

### Tasks

#### T201: Implement SealDetector
**Priority**: P0 | **Effort**: 12 hours | **Risk**: High

Create stream parser that:
- Buffers incoming chunks
- Tracks last-seen `tool_call_id`
- Detects ID transitions (seal events)
- Emits completed tool blocks for dispatch

```python
class SealDetector:
    """Detect tool block completion during streaming."""
    
    def __init__(self):
        self.current_id: str | None = None
        self.buffer: dict[str, ToolBlock] = {}
    
    def process_chunk(self, chunk: StreamChunk) -> list[ToolBlock]:
        """Return sealed (complete) tool blocks."""
        # Detect new tool_call_id → seal previous block
        # Buffer current block arguments
        # Return sealed blocks for dispatch
```

**Verification**: Unit tests with synthetic streams

---

#### T202: Add Provider Adapters
**Priority**: P0 | **Effort**: 8 hours | **Risk**: Medium

Normalize streaming formats:
- Anthropic: `content_block_delta` with `tool_use` type
- OpenAI: `tool_calls` array with `function` objects
- Bedrock: Provider-specific format

**Deliverable**: Unified stream adapter interface

---

#### T203: Implement Cancellation Scope
**Priority**: P1 | **Effort**: 6 hours | **Risk**: Medium

Handle stream interruptions:
- Cancel in-flight tools when stream dies
- Clean up background workers
- Emit cancellation events for observability

**Verification**: Test with aborted streams

---

## Phase 3: Eager Executor Pool (Week 4)

### Objectives
Build concurrent executor that dispatches tools during streaming.

### Tasks

#### T301: Implement ExecutorPool
**Priority**: P0 | **Effort**: 10 hours | **Risk**: High

Create background worker pool:
- Fire-and-forget dispatch on seal events
- Concurrent execution (asyncio.gather)
- Exception isolation per tool
- Result collection and ordering

```python
class EagerExecutorPool:
    """Execute tools concurrently during streaming."""
    
    async def dispatch(self, tool: ToolBlock) -> None:
        """Fire tool immediately (non-blocking)."""
        
    async def collect_results(self) -> list[ToolResult]:
        """Gather all results after stream completes."""
```

**Verification**: Synthetic workload with 9-15 tools

---

#### T302: Add Idempotency Gates
**Priority**: P0 | **Effort**: 6 hours | **Risk**: Medium

Implement safety checks:
- Tool-level `idempotent` flag (default: False for safety)
- Argument-level gate callable for conditional dispatch
- Fallback to post-stream execution for unsafe tools

```python
class Tool:
    idempotent: bool = False
    gate: Callable[[dict], bool] | None = None
```

**Verification**: Test non-idempotent tools wait for `message_stop`

---

## Phase 4: Integration with Lyra (Week 5)

### Objectives
Wire eager execution into Lyra's agent loop.

### Tasks

#### T401: Add Eager Middleware
**Priority**: P0 | **Effort**: 8 hours | **Risk**: High

Create middleware layer:
- Intercept streaming responses
- Route to SealDetector
- Dispatch via ExecutorPool
- Merge results back into agent state

**Deliverable**: `eager_tools_middleware` for Lyra's agent loop

---

#### T402: Update Tool Registry
**Priority**: P0 | **Effort**: 6 hours | **Risk**: Low

Extend tool metadata:
- Add `idempotent` field to tool definitions
- Add `gate` callable for conditional dispatch
- Update tool registration API

**Verification**: All existing tools default to safe (non-eager)

---

#### T403: Add Configuration Flags
**Priority**: P1 | **Effort**: 4 hours | **Risk**: Low

Enable/disable eager execution:
- Global flag: `LYRA_EAGER_TOOLS=true`
- Per-tool override: `Tool.eager=false`
- Per-session toggle: `/eager-tools on|off`

**Deliverable**: Configuration system

---

## Phase 5: Observability & Debugging (Week 6)

### Objectives
Add metrics and debugging tools for eager execution.

### Tasks

#### T501: Add Seal Latency Metrics
**Priority**: P0 | **Effort**: 6 hours | **Risk**: Low

Emit spans for:
- `seal_detected_ms`: Time from stream start to seal
- `tool_dispatch_ms`: Time from seal to dispatch
- `tool_complete_ms`: Tool execution duration
- `overlap_savings_ms`: Time saved vs sequential

**Deliverable**: Prometheus/OpenTelemetry metrics

---

#### T502: Add Debug Logging
**Priority**: P1 | **Effort**: 4 hours | **Risk**: Low

Log seal events:
- Tool ID transitions
- Dispatch decisions (eager vs deferred)
- Cancellation events
- Exception boundaries

**Deliverable**: Structured debug logs

---

## Phase 6: Performance Validation (Week 7)

### Objectives
Benchmark eager tools against baseline and validate improvements.

### Tasks

#### T601: Run Synthetic Benchmarks
**Priority**: P0 | **Effort**: 8 hours | **Risk**: Low

Test workloads:
- 3-tool: Simple queries (weather, stock, news)
- 9-tool: Incident triage (logs, metrics, traces)
- 15-tool: Ad campaign (research, draft, review)

**Expected**: 1.2×–1.5× speedup vs parallel baseline

---

#### T602: Run Production Workloads
**Priority**: P0 | **Effort**: 8 hours | **Risk**: Medium

Test on real Lyra tasks:
- Code review with multiple file reads
- Research pipeline with parallel searches
- Multi-agent team coordination

**Deliverable**: Performance comparison report

---

#### T603: Validate Safety Properties
**Priority**: P0 | **Effort**: 6 hours | **Risk**: High

Verify:
- Non-idempotent tools never dispatch early
- Cancellation cleans up in-flight tools
- Exception isolation prevents cascade failures
- No tool result ordering issues

**Deliverable**: Safety validation report

---

## Phase 7: Documentation & Rollout (Week 8)

### Objectives
Document eager tools and enable for production use.

### Tasks

#### T701: Write User Documentation
**Priority**: P1 | **Effort**: 6 hours | **Risk**: Low

Document:
- When to use eager tools (tool-heavy workloads)
- When NOT to use (fast tools, sequential deps)
- How to mark tools as idempotent
- Performance expectations

**Deliverable**: `EAGER_TOOLS.md` guide

---

#### T702: Add Migration Guide
**Priority**: P1 | **Effort**: 4 hours | **Risk**: Low

Guide for tool authors:
- How to audit tools for idempotency
- How to add `idempotent` flag
- How to implement gate callables
- Testing checklist

**Deliverable**: `EAGER_TOOLS_MIGRATION.md`

---

#### T703: Enable Gradual Rollout
**Priority**: P0 | **Effort**: 4 hours | **Risk**: Low

Rollout strategy:
- Week 1: Internal testing (10% of sessions)
- Week 2: Beta users (25% of sessions)
- Week 3: General availability (100% of sessions)
- Rollback plan if regressions detected

**Deliverable**: Rollout plan and monitoring dashboard

---

## Success Metrics

### Performance
- 1.2×–1.5× speedup on tool-heavy workloads (9+ tools)
- 50% faster median task completion (CloudThinker benchmark)
- <5% overhead on fast tools (<50ms)
- <10% overhead on non-streaming backends

### Safety
- Zero non-idempotent tools dispatched early
- 100% clean cancellation on stream abort
- Zero tool result ordering issues
- Zero cascade failures from tool exceptions

### Adoption
- 80% of read-only tools marked idempotent
- 50% of agent sessions use eager execution
- <1% rollback rate due to issues

---

## Risk Mitigation

### High-Risk Items

1. **Tool retraction**: Models sometimes emit then replace tools mid-stream
   - **Mitigation**: Track tool versions, cancel retracted tools, only commit on `message_stop`

2. **Non-idempotent safety**: Accidental early dispatch of destructive operations
   - **Mitigation**: Default `idempotent=False`, require explicit opt-in, audit all tools

3. **Stream cancellation**: In-flight tools may not clean up properly
   - **Mitigation**: Cancellation scope with timeout, resource cleanup hooks

### Medium-Risk Items

1. **Provider compatibility**: Different streaming formats across providers
   - **Mitigation**: Adapter layer with provider-specific tests

2. **Performance regression**: Overhead exceeds benefit for fast tools
   - **Mitigation**: Benchmark-driven thresholds, per-tool eager flag

---

## Dependencies

### External
- Streaming support from LLM providers (Anthropic, OpenAI, Bedrock)
- Asyncio runtime for concurrent execution
- Observability stack (Prometheus/OpenTelemetry)

### Internal
- Lyra's tool registry and execution pipeline
- Agent loop streaming handler
- Configuration system

---

## Timeline

**Total Duration**: 8 weeks

- Week 1: Current state analysis
- Week 2-3: Seal detection engine
- Week 4: Eager executor pool
- Week 5: Integration with Lyra
- Week 6: Observability & debugging
- Week 7: Performance validation
- Week 8: Documentation & rollout

**Milestones**:
- M1 (Week 3): Seal detection working for Anthropic streams
- M2 (Week 4): Eager executor dispatching tools concurrently
- M3 (Week 5): Integrated into Lyra agent loop
- M4 (Week 7): Performance validation complete
- M5 (Week 8): Production rollout

---

## Next Steps

1. Review this plan with team
2. Audit Lyra's current tool execution pipeline
3. Begin Phase 1: Current state analysis
4. Run baseline performance benchmarks
5. Prototype seal detection for Anthropic streams

---

**Status**: Ready for review and approval
