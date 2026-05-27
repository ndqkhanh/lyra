---
title: Hooks reference
description: All lifecycle events, the Decision API, shipped hooks, and ordering rules.
---

# Hooks reference <span class="lyra-badge reference">reference</span>

This page catalogues every lifecycle event, the `Decision` API,
hook ordering, and the hooks Lyra ships with by default.

For a guided introduction, see [Write a hook](../howto/write-hook.md)
and [concept: tools and hooks](../concepts/tools-and-hooks.md).

## Lifecycle events

| Event | When it fires | Can deny? | Can mutate? | Common use |
|---|---|---|---|---|
| `UserPromptSubmit` | Before context assembly | yes | redact prompt | Strip secrets from user input |
| `PrePlan` | Before planner runs | yes | augment context | Inject project conventions |
| `PostPlan` | After plan written | warn only | annotate | Verify plan against budget |
| `PreToolUse` | Before any tool call | yes | redact / modify args | Permission gates beyond mode grid |
| `PostToolUse` | After any tool call | warn only | redact result | Log, redact secrets in output |
| `PreSubagent` | Before subagent spawn | yes | trim scope | Limit branch depth |
| `PostSubagent` | After subagent return | warn only | redact summary | Aggregate metrics |
| `PreVerify` | Before verifier runs | yes | inject extra checks | Add custom acceptance |
| `PostVerify` | After verdict | warn only | downgrade verdict | Project-specific quality gate |
| `PreSessionEnd` | Before STATE.md final write | warn only | append notes | Notifier (slack, email, …) |

`warn only` events still receive `Decision`s; `Decision.deny` is
upgraded to a warning in the trace and the action proceeds.

## The `Decision` API

```python
from lyra_core.hooks import Decision

Decision.allow()                        # default; no surface change
Decision.allow().with_warning("…")      # surfaces yellow in HUD; trace only
Decision.deny(reason="…",
              user_message="…")         # stops the action; both fields go to trace
Decision.modify(new_args={…})           # rewrite tool args (PreToolUse only)
Decision.redact(replacement="…")        # mask matches in args/result; default "«redacted»"
```

A decision is **immutable**. To combine outcomes (e.g. "allow but
with warning") use the chained constructors above.

## Hook context

The `ctx` argument passed to every hook:

```python
@dataclass
class HookContext:
    event: Event
    session: SessionMeta              # id, mode, cost, budget, tdd_phase, …
    tool: ToolInvocation | None       # only on tool events
    subagent: SubagentInvocation | None
    plan: Plan | None
    user_prompt: str | None           # only on UserPromptSubmit
    verdict: Verdict | None           # only on PostVerify
    artifacts: ArtifactStore          # read-only handle
    logger: Logger
```

Fields that don't apply to the current event are `None`. Type-narrow
with `if ctx.tool is not None: …`.

## Ordering and priority

Multiple hooks for the same event run in **registration order**.
Lower priority number = earlier:

```python
@hook(event=Event.PreToolUse, priority=10)   # very early
def cheap_deny_first(ctx): …

@hook(event=Event.PreToolUse, priority=100)  # default
def normal_logic(ctx): …

@hook(event=Event.PreToolUse, priority=200)  # late
def annotate_for_observability(ctx): …
```

| Priority band | Use for |
|---|---|
| 0–49 | Cheap deny-fast guards (path blocklists, kill switches) |
| 50–99 | Permission-adjacent project policies |
| 100 | Default; most application logic |
| 101–199 | Expensive checks (lint, network) |
| 200+ | Annotation-only, never deny |

**Any deny stops further evaluation** — if a priority-10 hook denies,
the priority-200 annotator never runs.

## Resolution order across sources

A hook's effective definition is resolved in this order (first wins
on collision by `name`):

1. `.lyra/hooks/` — repo-local
2. Plugin hooks (in plugin load order)
3. `~/.lyra/hooks/` — user-global

So a repo can override a user-global hook for project-specific
behaviour. `lyra hooks list` shows the effective registration with
`source: …`.

## Shipped hooks

Lyra ships these hooks under `lyra_core/hooks/builtin/`:

| Hook | Event | Default | Description |
|---|---|---|---|
| `secret-redactor` | `PreToolUse`, `PostToolUse` | on | Redacts API keys, tokens, AWS access keys |
| `tdd-anchor` | `PreToolUse` | on if TDD gate enabled | Blocks test edits in green phase |
| `path-quarantine` | `PreToolUse` | on | Denies writes outside repo + `~/.lyra/` |
| `cost-warner` | `PreToolUse` | on | Yellow-bars HUD at 80% budget |
| `dangerous-bash-guard` | `PreToolUse` | on | Asks before `rm -rf`, `chmod -R`, `sudo` |
| `large-write-guard` | `PreToolUse` | on | Asks before writing files > 100 KB |
| `subagent-depth-cap` | `PreSubagent` | on | Denies depth > 3 |
| `cascade-pulse` | `PreToolUse` | off | Logs cascade events for HUD widget |
| `cron-destructive-guard` | `PreToolUse` (cron only) | on | Denies destructive ops in cron-spawned sessions |

Disable any with:

```bash
lyra hooks disable secret-redactor
```

(Surfaced in trace; **enabled-and-bypassed via `--no-hooks` is the
only way to fully suppress** and that's logged at session start.)

## YAML hook schema

```yaml
name: <kebab-case>           # required, unique per source
event: <Event name>          # required
priority: 100                # optional
matcher:                     # optional; restricts which invocations the hook handles
  tool: { in: [view, write] }
  args: { path: { regex: "^src/" } }
action:                      # required; one of:
  redact:                    # redact mode
    patterns: [<regex>, …]
    replacement: "«redacted»"
  deny:                      # deny mode
    reason: "<short>"
    user_message: "<long>"
  warn:                      # warn mode
    message: "<short>"
  modify:                    # mutate args
    set:
      <field>: <value>
  shell:                     # run a shell command; deny on non-zero exit
    cmd: "make pre-write-check"
    timeout_s: 10
```

YAML hooks can't keep state across calls; for that use Python.

## Python hook decorator

```python
from lyra_core.hooks import hook, Event, Decision

@hook(
    event=Event.PreToolUse,
    name="my-guard",                 # optional; defaults to function name
    priority=80,
    scope="repo",                    # "repo" | "user" | "any" (default any)
    match={"tool": ["bash"]},        # optional declarative matcher
)
def my_guard(ctx) -> Decision:
    ...
```

Decorator-registered hooks live wherever you put them; Lyra finds
them by importing `~/.lyra/hooks/*.py` and `.lyra/hooks/*.py` at
session start.

## Tracing

Every hook fire emits two HIR events:

- `Hook.start(event, hook_name)`
- `Hook.end(decision, duration_ms)`

Both go into the JSONL trace and the HUD's `recent_hooks` widget.

## Where to look

| File | What lives there |
|---|---|
| `lyra_core/hooks/__init__.py` | `hook`, `Decision`, `Event` API |
| `lyra_core/hooks/registry.py` | Registration + resolution |
| `lyra_core/hooks/loader.py` | YAML and Python file loaders |
| `lyra_core/hooks/builtin/` | Shipped hooks |
| `lyra_cli/commands/hooks.py` | `lyra hooks …` CLI |

[← Reference index](index.md){ .md-button }
[Continue: tools reference →](tools.md){ .md-button .md-button--primary }
