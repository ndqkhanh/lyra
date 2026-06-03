# Observability

> **Every span, every cost, every decision -- machine-parseable, replayable, and OTel-compatible.** | **Phase:** 1

## 💡 What It Is

Observability is a first-class pillar of Lyra, not an afterthought. Every model call, tool execution, hook decision, permission check, and memory write emits a structured **span** -- a named, timed operation with metadata. Spans follow the **HIR** (Harness Intermediate Representation) schema and are **OTel** (OpenTelemetry)-compatible for backends like Jaeger, Honeycomb, or Datadog.

A **span** is the fundamental observability unit: it records one operation (e.g., "call tool bash" or "evaluate submission") with a start time, end time, and structured tags. **HIR** (Harness Intermediate Representation) is Lyra's own event schema that adds agent-specific fields (actor, risk, verdict) on top of standard OTel. **OTel** (OpenTelemetry) is the industry-standard observability framework for distributed systems.

## 🔄 How It Works

```mermaid
sequenceDiagram
    participant Loop as Agent Loop
    participant Bus as HIR Event Bus
    participant JSONL as trace.jsonl
    participant OTel as OTel Exporter
    participant UI as lyra CLI

    Loop->>Bus: emit span (tool.call, hook.decision, verdict, ...)
    Bus->>JSONL: append {trace_id, span_id, actor, duration, cost}
    Bus-->>OTel: parallel stream (optional)
    JSONL->>UI: lyra trace show &lt;id&gt; --step N
    JSONL->>UI: lyra trace diff &lt;id1&gt; &lt;id2&gt;
    JSONL->>UI: lyra trace replay &lt;id&gt; --replay-model gpt-5
```

Span types include `Tool.call`, `PermissionBridge.decision`, `Hook.start/end`, `Subagent.spawn`, `Context.compaction`, `Evaluator.verdict`, and `Safety.check`. Every span carries `trace_id`, `span_id`, `parent_span_id`, `actor` (generator|evaluator|monitor|scheduler), and `session_id`.

Three outputs per session:

1.  **`trace.jsonl`** -- append-only span log at `.lyra/sessions/<id>/trace.jsonl`. The single source of truth.
2.  **`metrics.jsonl`** -- Prometheus-shaped gauges for cost, latency, and outcome by actor.
3.  **`artifacts/`** -- hash-addressed blobs for plans, diffs, verdicts, and large tool outputs.

### Span Event Schema

```json
{
  "trace_id": "abc123def456",
  "span_id": "span-001",
  "parent_span_id": "session-root",
  "timestamp": "2025-06-01T12:00:00Z",
  "actor": "generator",
  "event": "Tool.call",
  "tool": "bash",
  "duration_ms": 2340,
  "token_usage": {"input": 1200, "output": 340},
  "cost_usd": 0.0034
}
```

### OTel Export Config

```toml
[observability.otel]
enable = true
endpoint = "http://localhost:4318"
protocol = "http/protobuf"
```

Live cost attribution is available with the `/cost` command, breaking down spend by actor: generator (fast), generator (smart), evaluator, and safety monitor (nano).

## 📊 Real Numbers

| Metric | Value | Notes |
|--------|-------|-------|
| Span emission latency | < 5 ms | Non-blocking JSONL append |
| Storage per session | 50--200 KB | Varies with session length |
| Replay fidelity | 100 % | No LLM calls; pure trace walk |

## 💡 Why This Design

Without structured traces, diagnosing agent decisions requires reconstructing ephemeral prompts. Lyra's JSONL trace is the source of truth -- replayable offline without re-calling the LLM. The OTel export is best-effort and runs in parallel. Privacy redaction via `lyra trace redact <id> --policy default` strips sensitive fields. Prune old sessions with `lyra sessions prune`.

## ⚠️ When to Use / When NOT to Use

Traces emit by default in every session. Enable OTel in `~/.lyra/config.toml` for external streaming. Do not rely solely on OTel for audit trails -- validate the JSONL side. Mark private observations with `is_private=1` to exclude them from exports.

## 🔗 Where Next

- **Block:** [13-observability-hir.md](../blocks/13-observability-hir.md)
- **Plan:** [16-reliability.md](../lyra-upgrade/plans/16-reliability.md)
