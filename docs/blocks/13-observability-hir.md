# Lyra Block 13 — Observability (Harness IR + OpenTelemetry)

Observability in Lyra is a first-class pillar, not an afterthought. It emits:

1. **Traces** that are both OpenTelemetry-compatible (for generic tools) and **Harness IR (HIR)**-compatible (for agent-specific analysis across frameworks).
2. **Metrics** (cost, latency, outcome) suitable for dashboards.
3. **Artifacts** (plans, diffs, evaluator verdicts, snapshots) addressable by stable hashes.

Reference: [docs/90-gnomon-irs.md](../../../../docs/90-gnomon-irs.md) (framework-agnostic agent traces), [docs/74-observability-and-eval-patterns.md](../../../../docs/74-observability-and-eval-patterns.md), [Orion-Code Block 08](../../../orion-code/docs/blocks/08-observability.md).

## HIR — Harness Intermediate Representation

Gnomon's thesis: every agent harness should emit a framework-neutral IR so that evaluation, visualization, and replay tooling are portable. Lyra adopts the HIR shape and extends with harness-specific event types.

### Event kinds

```
AgentLoop.start(session_id, task, soul_hash, plan_hash)
AgentLoop.step(step_no, think_text, model, usage)
PermissionBridge.decision(tool, args_digest, mode, policy_ref, decision, risk, reason)
Hook.start(event, hook_name), Hook.end(decision, duration_ms)
TDD.state_change(from, to, reason, evidence_ref)
Tool.call(tool, args_ref), Tool.result(result_ref, exit_code, duration_ms)
Subagent.spawn(id, purpose, scope, budget)
Subagent.result(id, outcome, summary_ref)
Context.compaction(strategy, tokens_before, tokens_after, preservation_refs)
Memory.read(tier, query, result_ref), Memory.write(tier, artifact_ref)
Evaluator.verdict(verdict, rubric_scores, evidence_refs)
Safety.check(verdict, confidence, evidence_refs)
AgentLoop.end(status, cost_usd, steps, final_text_ref)
```

Every event carries: `trace_id`, `span_id`, `parent_span_id`, `ts`, `session_id`, and an `actor` (generator/evaluator/monitor/scheduler).

### Storage

JSONL under `.lyra/<session-id>/events.jsonl`, appended as the session runs. Parallel binary OTLP export for OpenTelemetry backends (Jaeger, Honeycomb, etc.) when configured.

Artifacts referenced by events are stored under `.lyra/<session-id>/artifacts/<hash>` and deduplicated by content.

## OpenTelemetry mapping

```
hir.AgentLoop.step      → span "lyra.step"
hir.Tool.call           → span "lyra.tool.<tool_name>" with child "tool.exec"
hir.PermissionBridge    → span event on parent tool span
hir.Hook.start/end      → span "lyra.hook.<name>"
hir.Evaluator.verdict   → span "lyra.verifier" with rubric as attributes
hir.Context.compaction  → span "lyra.context.compact" with token counts
hir.Memory.*            → span "lyra.memory.<op>"
hir.Safety.check        → span "lyra.safety.check"
```

Exporters configured via `~/.lyra/telemetry.yaml`:

```yaml
exporters:
  otlp:
    endpoint: https://otel-collector.internal:4317
    headers: { authorization: "Bearer $OTEL_TOKEN" }
  file:
    path: .lyra/events.jsonl     # always on
  jaeger:
    endpoint: http://localhost:14268/api/traces   # optional
```

## Metrics

Prometheus-compatible via OpenTelemetry metric API. Core metrics (see each block's "Metrics emitted" section):

- `lyra.steps.total{session,plugin,phase}`
- `lyra.cost_usd.total{session,model,actor}` counter
- `lyra.tokens.total{session,model,direction}`
- `lyra.latency_ms` histogram per tool/hook/permission
- `lyra.verdict.total{verdict,blocking}`
- `lyra.tdd.state_time_seconds{state}` gauge
- `lyra.outcome.total{status}` counter per session end
- `lyra.error.total{type}`

Local dashboards: `lyra doctor --dashboard` spins up a minimal HTML viewer over the JSONL + metrics. No external deps required.

## Artifacts

Addressable by sha256. Stored under `.lyra/<session>/artifacts/<hash>`. Types:

- `plan.md` — plan artifact (primary)
- `diff.patch` — unified diff snapshot
- `verdict.json` — evaluator verdict
- `env-snapshot.json` — filesystem/process delta
- `subagent-summary.json` — subagent result
- `skill-proposal.md` — extracted skill candidate
- `trace-digest.json` — compressed trace for evaluator input

Artifacts are referenced (not inlined) by events to keep event stream compact.

## Session retrospective — `lyra retro`

CLI command that reads a session's events and produces a human report:

```
lyra retro <session-id>
# ➜ .lyra/<session>/retro.md
```

Report sections:
- Outcome + cost + duration
- Plan vs actual (feature items done/pending/failed)
- Tool usage breakdown + cost attribution
- TDD gate violations (if any)
- Evaluator verdicts + rubric trends
- Safety monitor flags
- Subagent summaries
- Advisory items to track
- Suggested skill extractions

## Trace viewer — `lyra view`

```
lyra view <session-id> [--step N]
```

Textual TUI with keyboard navigation through steps. Non-goal for v1: a polished web UI (stretch goal). v1 emits JSONL + retro markdown; Honeycomb / Jaeger cover advanced cases.

## Session recall

Any artifact is queryable:

```
lyra artifact get <hash>          # raw contents
lyra artifact list <session>      # table
lyra session list                 # all sessions
lyra session grep "checkout bug"  # full-text across sessions
```

## Privacy and data handling

- By default, trace is **local-only**. No telemetry leaves the machine unless explicitly configured.
- Secrets masking applied at trace-write time using `secrets-scan` regex pack (same pack as hook).
- `lyra wipe <session>` removes a session's events + artifacts atomically.
- OTLP export redacts `tool.args` and `tool.result` bodies by default; users opt-in to include.

## Performance budget

- Event write: < 100 µs median (JSONL append).
- Artifact dedupe hash: < 2 ms for files < 1 MB.
- `lyra retro` generation: < 5 s for a 200-step session.
- Doctor dashboard startup: < 1 s.

## Failure modes and defenses

| Mode | Defense |
|---|---|
| Disk fills from traces | Rolling policy: keep last N sessions (config, default 50); older auto-compressed |
| JSONL write failure mid-session | Events buffered in memory; flushed at end; error visible in doctor |
| OTLP endpoint down | Exports queued; file export remains; warning surfaced; no block on loop |
| Artifact collisions across sessions | sha256 collision: negligible; ref-count protected |
| Trace contains secrets | Masking pipeline at write time; doctor validates samples |
| Trace too large for evaluator | Trace digest (structured) used instead of raw |
| Clock skew | Monotonic clock for spans; wall clock as attribute only |

## Testing

| Test kind | Coverage |
|---|---|
| Unit `test_hir.py` | Event schema validation across kinds |
| Unit `test_exporters.py` | File, OTLP, jaeger exporter shapes |
| Unit `test_secrets_mask.py` | Known secret patterns redacted |
| Integration | Full session → JSONL → retro.md generated |
| Integration | OTLP exporter pushes to mock collector; shapes match |
| Property | Artifact addressability: same content → same hash; different → different |

## Open questions

1. **HIR schema stabilization.** Currently aligned to Gnomon proposals; adopt the official spec once it freezes.
2. **Public trace format conversion.** Import LangSmith / LangGraph traces for replay comparison. v2.
3. **PII-aware masking.** Beyond secrets, PII patterns (emails, names) optionally masked. v2.
4. **Federated retros.** Team-level aggregation across engineers; requires explicit upload, privacy-reviewed. v2.
