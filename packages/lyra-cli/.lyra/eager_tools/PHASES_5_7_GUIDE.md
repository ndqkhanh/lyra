# Phases 5-7: Documentation & Validation

## Phase 5: Observability & Debugging

**Status**: Documentation Complete

### Metrics to Add

```python
# Seal latency tracking
seal_detected_ms = time_from_stream_start_to_seal()
tool_dispatch_ms = time_from_seal_to_dispatch()
tool_complete_ms = tool_execution_duration()
overlap_savings_ms = sequential_time - eager_time
```

### Debug Logging

Log seal events with structured format:
- Tool ID transitions
- Dispatch decisions (eager vs deferred)
- Cancellation events
- Exception boundaries

## Phase 6: Performance Validation

**Status**: Documentation Complete

### Benchmark Workloads

1. **3-tool workload**: Simple queries (weather, stock, news)
2. **9-tool workload**: Incident triage (logs, metrics, traces)
3. **15-tool workload**: Ad campaign (research, draft, review)

**Expected Results**: 1.2×–1.5× speedup vs parallel baseline

### Safety Validation

Verify:
- Non-idempotent tools never dispatch early
- Cancellation cleans up in-flight tools
- Exception isolation prevents cascade failures
- No tool result ordering issues

## Phase 7: Documentation & Rollout

**Status**: Documentation Complete

### User Documentation

Document in `EAGER_TOOLS.md`:
- When to use eager tools (tool-heavy workloads)
- When NOT to use (fast tools, sequential deps)
- How to mark tools as idempotent
- Performance expectations

### Migration Guide

Guide for tool authors in `EAGER_TOOLS_MIGRATION.md`:
- How to audit tools for idempotency
- How to add `idempotent` flag
- How to implement gate callables
- Testing checklist

### Rollout Strategy

- Week 1: Internal testing (10% of sessions)
- Week 2: Beta users (25% of sessions)
- Week 3: General availability (100% of sessions)
- Rollback plan if regressions detected
