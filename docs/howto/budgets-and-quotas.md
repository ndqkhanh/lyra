---
title: Set budgets and quotas
description: Cap session cost, per-tool quotas, and CI-wide spend with hard limits, soft warnings, and circuit breakers.
---

# Set budgets and quotas <span class="lyra-badge intermediate">intermediate</span>

Lyra has **three layers of cost control**:

| Layer | Scope | What it does |
|---|---|---|
| **Budget** | Per session | Hard ceiling on USD spent |
| **Quota** | Per tool, per scope | Limit calls per session/hour/day |
| **Circuit breaker** | Per role | Auto-disable a path after N failures |

All three are **opt-in** but the defaults catch the obvious mistakes
(unlimited bash, runaway cascade, infinite subagent spawn).

Source: [`lyra_core/agent/loop.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/agent/loop.py) ·
[`lyra_core/routing/cascade.py`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/routing/cascade.py) ·
[`lyra_core/permissions/`](https://github.com/lyra-contributors/lyra/tree/main/packages/lyra-core/src/lyra_core/permissions).

## Budget

### Hard ceiling per session

```toml title="~/.lyra/config.toml"
[budget]
default_session_usd = 5.0          # hard stop at $5
warn_at_pct = 0.80                 # nag at $4
extend_command = "/budget +2"      # how the user can extend live
```

When the running cost crosses the warn threshold, the HUD shows a
yellow bar; at 100% the kernel emits `BudgetExhausted` on the bus,
denies the next tool call, and prompts the user to `/budget +N` or
`/abort`.

### Per-task budget at run time

```bash
lyra run "implement auth flow" --budget 2.50
lyra plan run plans/big-refactor.md --budget 20
```

CLI flag wins over config wins over default.

### CI budget (across all jobs)

```bash
export LYRA_BUDGET_TOTAL=100        # total $ for this CI batch
export LYRA_BUDGET_LEDGER=.lyra/ci-ledger.jsonl
lyra ci run-suite tests/integration/lyra_runs/
```

The ledger is a single append-only file. Every session reads-then-
appends atomically (file lock). When the total crosses the cap, the
next session aborts before its first model call.

## Quotas

Quotas are **per-tool**, **per-scope**, **per-window**:

```toml title=".lyra/quotas.yaml"
- tool: bash
  scope: session
  limit: 50
  window: session

- tool: bash
  scope: hour
  limit: 200
  window: 1h

- tool: web_fetch
  scope: session
  limit: 20

- tool: subagent_spawn
  scope: session
  limit: 12

- tool: write
  scope: session
  limit: 200
```

Default quotas apply when no rule matches:

| Tool family | Default per-session limit |
|---|---|
| `bash` | 50 |
| `write` / `edit` | 200 |
| `web_fetch` / `web_search` | 20 |
| `subagent_spawn` | 12 |
| `mcp:*` | 100 |

Hitting a quota produces a `Decision.deny` with reason
`quota:bash:session:50` — same surface as a permission deny, so
**hooks and the trace see it identically**.

### Bypass for trusted runs

```bash
lyra run "…" --no-quotas              # tear down all quotas (use carefully)
lyra run "…" --quota bash=200         # raise just one tool
```

`--no-quotas` is logged in the trace and surfaced in the HUD.

## Circuit breakers

Circuit breakers turn off a path after repeated failures so the
agent can't loop forever burning tokens:

```toml title="~/.lyra/config.toml"
[circuit_breaker.cascade]
threshold = 8                       # cascades per session
on_trip = "disable_for_session"     # alternatives: warn, abort

[circuit_breaker.subjective_verify]
threshold = 3                       # consecutive subjective rejections
on_trip = "downgrade_to_objective_only"

[circuit_breaker.subagent]
threshold = 5                       # consecutive subagent failures
on_trip = "disable_for_session"
```

When tripped, the breaker emits a `CircuitTripped` event and the
HUD shows a red bar. The behaviour after trip depends on `on_trip`:

| Action | Effect |
|---|---|
| `warn` | Surface, continue |
| `disable_for_session` | This path is off until session restart |
| `abort` | End session immediately |
| `downgrade_…` | Fall back to a cheaper alternative |

## Where the meters live

```bash
/cost                    # interactive: live cost breakdown
/quota                   # interactive: quota usage
/budget                  # interactive: budget vs spend

lyra cost <session-id>           # static: post-hoc breakdown
lyra cost --since 24h --by tool  # rollup across sessions
```

The HUD's [cost-meter widget](customize-hud.md#widgets) shows the
same numbers continuously without opening a separate command.

## Patterns that work

**Daily-driver setup.** Budget = $5, default quotas, cascade circuit
at 8. You'll never blow $5 on a typo, and the rare big task asks for
`/budget +5` mid-session.

**CI integration suite.** `LYRA_BUDGET_TOTAL=$BATCH_DOLLARS`, no
per-session budget (let each session use what it needs from the pool),
all defaults for quotas. Suite aborts cleanly when the budget is gone
rather than half-running.

**Cheap-ground-truth eval.** No budget, low fast-slot model, very
high quotas, cascade circuit *disabled* — you want to see what the
fast model produces unaided.

## Where to look

| File | What lives there |
|---|---|
| `lyra_core/agent/loop.py` | Budget meter integration |
| `lyra_core/permissions/quota.py` | Quota counter + decision |
| `lyra_core/routing/cascade.py` | Cascade circuit |
| `lyra_cli/commands/budget.py` | `/budget`, `/cost`, `/quota` |

[← How-to index](index.md){ .md-button }
[Continue: customize the HUD →](customize-hud.md){ .md-button .md-button--primary }
