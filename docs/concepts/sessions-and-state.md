---
title: Sessions and state
description: How a session is structured on disk, why STATE.md is human-readable, and how resume actually works.
---

<!-- lyra-legacy-aware: page documents migration of pre-v3.0 sessions written by open-coding / open-harness, so the legacy brand names appear by design. -->


# Sessions and state <span class="lyra-badge intermediate">intermediate</span>

Lyra's session is the unit of work. Everything about it — transcript,
plan, tool calls, hooks, decisions, costs — persists to a directory
you can `ls` and `cat`. There is no binary pickle. Resume reads the
same files anyone else would read.

This is [Commitment 9](../architecture/commitments.md#9-session-continuity-via-human-readable-statemd)
realised: ungreppable state is a non-starter.

Source: [`lyra_core/sessions/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/sessions) ·
[`lyra_core/store/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/store).

## What's in a session directory

```
.lyra/sessions/sess-20260501-abcd/
├── STATE.md                # human-readable; load-bearing
├── recent.jsonl            # last N turns of transcript
├── trace.jsonl             # full HIR span stream
├── metrics.jsonl           # cost / latency / outcome timeseries
├── todo.json               # current todo list
├── artifacts/              # hash-addressed; immutable
│   ├── 8af1…d4f2           # a plan, a diff, a tool result, etc.
│   └── …
└── hooks/                  # per-hook last-result for /review
    ├── tdd-gate.json
    └── secret-redactor.json
```

Two layers of persistence:

| Layer | Where | Mutability |
|---|---|---|
| **State** | `STATE.md`, `todo.json`, `recent.jsonl` | Updated every step |
| **Trace** | `trace.jsonl`, `metrics.jsonl`, `artifacts/*` | Append-only |

State is small and live. Trace is large and immutable.

## STATE.md (the load-bearing file)

```markdown
---
session_id: sess-20260501-abcd
started_at: 2026-05-01T10:23:00Z
last_step_at: 2026-05-01T10:47:00Z
status: active             # active | paused | complete | aborted
mode: agent
plan: .lyra/plans/sess-20260501-abcd.md
plan_status: in-progress
fast_model: deepseek:deepseek-chat
smart_model: deepseek:deepseek-reasoner
cost_usd: 0.124
steps: 27
---

# Session sess-20260501-abcd

## Goal

Add dark mode toggle that persists across reloads.

## Status

- Plan approved at 10:24:12 UTC
- 3 of 4 plan steps complete
- TDD phase: green (3 of 3 acceptance tests passing)

## Open questions

- (none)

## Last 3 tool calls
1. write src/settings/ThemeToggle.tsx ✓
2. write src/settings/__tests__/useTheme.test.ts ✓
3. bash pytest tests/settings -k toggle ✓

## Next

- Mount ThemeToggle in src/App.tsx
```

This file is what `/resume` reads first. A human can read it. A `cat`
in CI can read it. A grep across `.lyra/sessions/` finds it. **No
binary format, ever.**

## Resume

```bash
lyra resume sess-20260501-abcd
# or pick interactively:
lyra sessions
```

The resume sequence:

```mermaid
sequenceDiagram
    participant CLI
    participant Store as sessions/store.py
    participant CE as Context Engine
    participant Loop as Agent Loop

    CLI->>Store: load(sess-20260501-abcd)
    Store->>Store: read STATE.md  → SessionMeta
    Store->>Store: read recent.jsonl  → last K turns
    Store->>Store: read todo.json
    Store->>Store: read plan-artifact ref
    Store-->>CLI: Session object
    CLI->>CE: assemble(session, task=continue, plan=loaded)
    CE-->>Loop: Transcript with SOUL, plan, todos, recent turns
    Loop->>Loop: AgentLoop.run() at next step
```

What survives resume:

| Survives | Why |
|---|---|
| Goal, mode, model | STATE.md frontmatter |
| Plan + plan status | Plan artifact ref |
| Todos | `todo.json` |
| Last K turns | `recent.jsonl` (default K=10) |
| Permission overrides | STATE.md "policy_overrides" section |
| Cost + budget remaining | STATE.md frontmatter |

What doesn't:

- Transient tool buffers (anything not in artifacts)
- Tool-call args older than the keep-window (compacted out)
- Per-tool counter state (re-initialised; not session-state)

## Migration: JSONL formats

Source: [`lyra_core/sessions/jsonl_migration.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/sessions/jsonl_migration.py).

Older sessions (pre-v3.0 written by `open-coding` and `open-harness`)
use slightly different JSONL shapes. The migration helper rewrites
them in place on first resume:

```bash
lyra sessions migrate ~/.opencoding/sessions/   # one-shot import
```

The original files are kept in `<dir>.bak.<ts>` until you delete them.

## The store API

If you want to programmatically inspect or operate on sessions:

```python
from lyra_core.sessions import SessionStore

store = SessionStore.user()                    # ~/.lyra/sessions/
store = SessionStore.repo()                    # .lyra/sessions/

for sess in store.list(status="active"):
    print(sess.id, sess.cost_usd, sess.steps)

sess = store.load("sess-20260501-abcd")
print(sess.state_md.next)                      # the parsed STATE.md
print(sess.replay_at_step(12).transcript)      # rebuilt transcript
```

Store is split into `repo`-scoped (`.lyra/sessions/`) and `user`-
scoped (`~/.lyra/sessions/`). They're separate; `lyra sessions` lists
both.

## Where to look in the source

| File | What lives there |
|---|---|
| `lyra_core/sessions/store.py` | `SessionStore`, `Session` dataclass |
| `lyra_core/sessions/jsonl_migration.py` | Pre-v3 → v3+ JSONL upgrade |
| `lyra_core/store/todo_store.py` | Todos persistence |

[← Observability and HIR](observability.md){ .md-button }
[Continue to Two-tier routing →](two-tier-routing.md){ .md-button .md-button--primary }
