---
title: Read and replay a trace
description: Walk a session's HIR span tree, reconstruct the transcript at any step, diff two runs, and replay against a different model.
---

# Read and replay a trace <span class="lyra-badge intermediate">intermediate</span>

Every Lyra session writes a complete event stream to
`.lyra/sessions/<id>/trace.jsonl`. With it, you can:

- See exactly what happened, step-by-step
- Reconstruct the transcript at any step
- Compare two runs to see why one diverged
- Replay the trace against a different model without paying for the
  original tool calls

Source: [`lyra_core/observability/retro.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/observability/retro.py) ·
[`lyra_core/hir/events.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/hir/events.py) ·
related concept: [Observability and HIR](../concepts/observability.md).

## Anatomy of a trace

`trace.jsonl` is **append-only**, one event per line:

```jsonl
{"kind":"AgentLoop.start","trace_id":"…","span_id":"01","ts":"…","session_id":"…","task":"add dark mode toggle","soul_hash":"…","plan_hash":"…"}
{"kind":"AgentLoop.step","trace_id":"…","span_id":"02","parent_span_id":"01","ts":"…","step_no":1,"think_text_ref":"art:8af1","model":"deepseek:deepseek-chat","usage":{"in":4231,"out":318}}
{"kind":"PermissionBridge.decision","trace_id":"…","span_id":"03","parent_span_id":"02","ts":"…","tool":"view","decision":"allow","mode":"default","risk":"safe","args_digest":"sha256:…"}
{"kind":"Tool.call","trace_id":"…","span_id":"04","parent_span_id":"02","ts":"…","tool":"view","args_ref":"art:1c4d"}
{"kind":"Tool.result","trace_id":"…","span_id":"05","parent_span_id":"02","ts":"…","exit_code":0,"duration_ms":42,"result_ref":"art:9b2e"}
…
```

Three things to know:

1. Spans form a **tree** via `parent_span_id`.
2. Large payloads (think-text, tool args, tool results) live in
   `artifacts/<hash>` and the event references them by `art:<short>`.
3. The order is **causal**, not strictly chronological — concurrent
   subagents interleave but each branch is consistent.

## CLI surface

```bash
# List sessions with trace files
lyra trace list

# Step-by-step (one event per line, condensed)
lyra trace show <session-id>

# Just step N
lyra trace show <session-id> --step 12

# A specific span (by short hash) and its descendants
lyra trace span <session-id> 8af1

# Cost timeline
lyra trace cost <session-id> --by tool
lyra trace cost <session-id> --by actor

# Compare two sessions
lyra trace diff <session-a> <session-b>

# Export to OTLP
lyra trace export <session-id> --format otlp > out.otlp

# Replay against a different model (no tool re-execution)
lyra trace replay <session-id> --replay-model anthropic:claude-opus-4.5
```

## `lyra trace show` walkthrough

```text
sess-20260501-abcd  ·  27 steps  ·  $0.124  ·  status=complete

  step  actor    model       tool         args                            ms     verdict
  ────  ───────  ──────────  ───────────  ─────────────────────────────   ───    ─────────
  01    gen      ds:chat     view         src/App.tsx                      18    allow
  02    gen      ds:chat     view         src/settings/                    24    allow
  03    plan     ds:reason   plan-write   …plans/sess-20260501-abcd.md    1820   approved
  04    gen      ds:chat     write        src/settings/useTheme.ts        152    allow
  05    gen      ds:chat     write        src/settings/__tests__/…ts       91    allow
  06    gen      ds:chat     bash         pytest tests/settings -k toggle 312    allow  ← TDD red
  07    gen      ds:chat     write        src/settings/ThemeToggle.tsx    178    allow
  08    gen      ds:chat     bash         pytest tests/settings -k toggle 280    allow  ← TDD green
  …
```

The columns are picked to fit the eye for a debugging pass — the
trace itself has more on every event.

## Reconstruct the transcript at any step

```python
from lyra_core.observability import retro
from lyra_core.sessions import SessionStore

sess = SessionStore.repo().load("sess-20260501-abcd")

snap = retro.assemble_at(sess, step=12)
print(snap.transcript)        # full transcript as the model saw it at step 12
print(snap.context_layers)    # which L0–L4 layers were live
print(snap.cost_so_far)       # cost up to step 12
```

This is the same code path the [debug mode](debug-mode.md)
`time_travel_replay` tool uses. It does **not** re-call the model;
it just walks the JSONL.

## Diff two runs

```bash
lyra trace diff sess-A sess-B
```

Shows divergence at the **action stream** level, not the text-token
level. Two runs with different model temperature but the same tool
call sequence will show **no diff**. Two runs with different tool
calls will show the divergent step inline.

```text
sess-A  vs  sess-B   (diverged at step 8)

  step 8                                step 8
  ──────────────────────────────────    ──────────────────────────────────
  bash: pytest tests/                   write: src/legacy/wrapper.py
  exit 0                                ──────────────────────────────────
  ──────────────────────────────────    bash: pytest tests/
                                        exit 1
```

Useful for "why did this run hallucinate the file?" investigations.

## Replay against a different model

```bash
lyra trace replay sess-20260501-abcd --replay-model anthropic:claude-opus-4.5
```

This re-runs the **assistant turns** against a new model, but
**replays tool calls from the original artifacts**. So you can
benchmark "would Claude Opus have written better code on this same
trajectory?" without re-running pytest 27 times.

The cost shown is *new model* cost; the original tool costs are
zeroed.

```text
Replay sess-20260501-abcd → anthropic:claude-opus-4.5

  original total  $0.124
  replay total    $0.418   (Opus is 3.4× the cost of DeepSeek-Chat)
  agreement       18 / 27 steps identical
  divergences     step 9 (Opus wrote a different test name)
                  step 14 (Opus added a comment block)
                  …
```

## Privacy redaction

Before sharing a trace (e.g. in a bug report):

```bash
lyra trace redact sess-20260501-abcd --policy default > redacted.jsonl
```

The default policy strips:

- Tokenised secrets (already redacted by the secret-redactor hook)
- Absolute paths under `$HOME`
- IPs and email addresses
- Anything matching configured `[redaction.patterns]`

Custom policies live in `~/.lyra/policies/redaction/<name>.yaml`.

## Programmatic walking

```python
from lyra_core.hir import events as E
from lyra_core.sessions import SessionStore

sess = SessionStore.repo().load("sess-20260501-abcd")

for ev in sess.iter_events():
    if isinstance(ev, E.ToolCall) and ev.tool == "bash":
        result_ev = sess.find_result_for(ev.span_id)
        if result_ev.exit_code != 0:
            print(f"step {ev.step_no}: bash failed",
                  sess.load_artifact(ev.args_ref).command)
```

Every event class is fully typed; mypy catches misspelt fields. See
the [HIR event schema](../reference/blocks-index.md#13--observability-hir)
for the full list.

## Where to look

| File | What lives there |
|---|---|
| `lyra_core/observability/retro.py` | `assemble_at`, `replay`, `diff` |
| `lyra_core/hir/events.py` | Event dataclasses |
| `lyra_cli/commands/trace.py` | The `lyra trace` CLI |

[← How-to index](index.md){ .md-button }
[Concept: Observability →](../concepts/observability.md){ .md-button .md-button--primary }
