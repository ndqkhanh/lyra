# Observability -- How It Works

> HIR JSONL event stream with a 13-category token observatory, real-time cost dashboard, OpenTelemetry integration, and full session replay at up to 1000x speed.
> **Block:** 11 | **Phase:** 2 (Quality & Planning) | **Depends on:** Agent Loop, Permission Bridge, Hooks (all blocks)

## HIR JSONL Event Stream

Every agent step, tool call, permission decision, and hook execution emits a structured HIR (Harness Intermediate Representation) event, written as newline-delimited JSON to `.lyra/<session>/events.jsonl`:

```jsonl
{"ts":1717201234.567,"kind":"AGENT_LOOP_STEP","session":"sess_abc","payload":{"phase":"EXECUTING","iteration":7,"tool":"bash","duration_ms":2340,"tokens_in":45200,"tokens_out":890,"cost":0.042}}
{"ts":1717201235.012,"kind":"TOOL_CALL_FINISHED","session":"sess_abc","payload":{"tool":"bash","exit_code":0,"duration_ms":2340}}
{"ts":1717201236.001,"kind":"PERMISSION_DECISION","session":"sess_abc","payload":{"tool":"write","action":"allow","guard":"tdd_gate","reason":"RED proof found"}}
```

30+ event types across 9 `HIREventKind` categories: `AgentLoop.start/step/end`, `Tool.call/result`, `PermissionBridge.decision`, `Hook.start/end`, `TDD.state_change`.

JSONL is streamable (append-only, no schema), grepable (`grep PERMISSION_DENIED events.jsonl`), diffable (`diff session_a events.jsonl session_b events.jsonl`), and requires zero infrastructure.

## Token Observatory (13 Waste Categories)

The observability block tracks 13 categories of token waste, surfaced in a "token observatory" dashboard:

| Category | What It Measures | Typical Waste |
|----------|-----------------|---------------|
| Repetition | Repeated tool calls with same args | 2-5% |
| Truncation | Tokens in content that was cut off | 1-3% |
| Oversized output | Tool results exceeding useful length | 5-15% |
| Memory reload | Re-fetching already-known facts | 3-8% |
| Plan bloat | Planning output that exceeds need | 1-2% |
| Hallucination | Tokens spent on fabricated results | <1% |
| Permission noise | Tokens explaining permission blocks | <1% |
| Redundant context | Context provided but not used | 10-20% |
| Error retries | Tokens burned on retry loops | 2-5% |
| Subagent overhead | Orchestration tokens per subagent | 3-7% |
| Cache misses | Cost of uncached context assembly | 15-25% |
| Hook overhead | Hook execution token cost | <1% |
| MCP transport | Transport framing and metadata | 1-2% |

The observatory runs as a post-hoc analysis pass (`lyra trace audit <session>`) and produces a report like:

```
Token Observatory Report: sess_abc123
Total tokens: 452,300  |  Total cost: $3.42

Waste categories:
  Cache misses:      89,400 tok ($0.68)  ━━━━━━━━━━━━━━━━━━━━
  Redundant context: 45,200 tok ($0.34)  ━━━━━━━━━━━━
  Oversized output:  22,600 tok ($0.17)  ━━━━━
  Repetition:        9,000 tok ($0.07)   ━━
  Other:             4,500 tok ($0.03)   ━

Total waste: 170,700 tok ($1.29)  =  37.7% of total
```

## Cost Dashboard

A real-time terminal dashboard renders at ~4fps using the `rich` library:

```
 Lyra Session Dashboard ── sess_abc123 ──────────────────────────────
 ┌────────────────────────────────────────────────────────────┐
 │ Active Agents: 3  │ Tools Called: 47  │ Turns: 12/25      │
 │ Total Cost: $3.42 │ Tokens In: 452.3K │ Tokens Out: 18.7K  │
 └────────────────────────────────────────────────────────────┘
 ┌─ Cost by Tool ────────────────────────────────────────────┐
 │ bash      ████████████████░░░░░░░  68%   $2.33            │
 │ write     ██████░░░░░░░░░░░░░░░░░  22%   $0.75            │
 │ search    ██░░░░░░░░░░░░░░░░░░░░░   8%   $0.27            │
 │ read      █░░░░░░░░░░░░░░░░░░░░░░   2%   $0.07            │
 └────────────────────────────────────────────────────────────┘
 ┌─ Token Observatory ───────────────────────────────────────┐
 │ Waste: 37.7% │ Cache misses: 19.8% │ Redundant: 10.0%    │
 │ Recommendation: Enable compaction at 75% threshold         │
 └────────────────────────────────────────────────────────────┘
```

The dashboard shows active agents, tool calls, token counts, cumulative cost, and a visual context-window gauge. Overhead on the agent loop is zero-perceivable -- the renderer runs on a 50ms throttle and never blocks the emit path.

## OpenTelemetry Integration

HIR events are also exported as OpenTelemetry spans via OTLP:

```python
# HIR event
{"kind": "TOOL_CALL_STARTED", "tool": "bash", "duration_ms": 2340}

# Maps to OTel span
Span(
    name="tool_call.bash",
    kind=SpanKind.CLIENT,
    attributes={
        "gen_ai.tool.name": "bash",
        "gen_ai.tool.duration_ms": 2340,
        "gen_ai.request.model": "claude-sonnet-4-20250514",
    },
    start_time=1717201234567000000,
    end_time=1717201236907000000,
)
```

Batch export: every 100 events or 5 seconds, whichever comes first. Async, non-blocking on the agent loop.

## Full Replay at 1000x Speed

The RetroEngine can replay an entire session from the JSONL event stream:

```bash
lyra trace replay sess_abc123 --speed 1000x
# Replays a 10-minute session in 600ms
```

The engine assembles session state at any step (`assemble_at(step=42)`), attributes costs per tool/model (`cost_attribution()`), diffs two sessions (`diff_sessions(a, b)`), and renders output as text/HTML/JSON. It uses lazy stream parsing -- never loads the entire event file into memory.

## Performance

| Metric | Value |
|--------|-------|
| Event emit (in-memory queue) | <10us |
| Secrets redaction | <50us |
| JSONL file append | <100us |
| Full event pipeline (emit to JSONL) | <160us |
| OTel batch export | <50ms |
| Trace replay (200-step session) | <5s |
| Heap allocations per event (warm) | 0 |
| Throughput (sustained) | 62,500 events/s |

## Related Documents

- **Concepts:** [Observability](../concepts/13-observability.md), [Agent Loop](../concepts/01-agent-loop.md), [Sessions and State](../concepts/08-sessions-and-state.md)
- **Architecture:** [Architecture Overview](../architecture/11-architecture-overview.md), [Breakthrough Architectures](../architecture/16-breakthrough-architectures.md)
- **Related blocks:** [Agent Loop](01-agent-loop.md), [Verifier](10-verifier.md), [Safety Monitor](12-safety-monitor.md)

---

*References: Dapper (Google TR 2010), Event Sourcing (Fowler, 2005), OpenTelemetry GenAI Conventions v1.32.0, JSON Lines (jsonlines.org, 2015)*
