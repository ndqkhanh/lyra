---
title: Write a hook
description: Add custom checks at any lifecycle event using Python or YAML hooks, with examples for redaction, gating, and budget alarms.
---

# Write a hook <span class="lyra-badge intermediate">intermediate</span>

Hooks are how you extend Lyra without forking the kernel. They run
synchronously at lifecycle events (`PreToolUse`, `PostToolUse`,
`UserPromptSubmit`, `PreSubagent`, …) and can **block, redact, or
augment** the action.

There are two flavours:

| Flavour | When to use |
|---|---|
| **YAML hook** | Simple regex/shell guard; no state |
| **Python hook** | Conditional logic, network calls, state across events |

Hooks live under `~/.lyra/hooks/` (user) or `.lyra/hooks/` (repo).
Repo wins on collision so a project can pin its own gates.

## Recipe 1: secret-redactor (YAML, 6 lines)

```yaml title="~/.lyra/hooks/secret-redactor.yaml"
name: secret-redactor
event: PreToolUse
matcher:
  tool: { in: [view, write, edit] }
action:
  redact: true
  patterns:
    - 'sk-[A-Za-z0-9]{32,}'      # OpenAI / Anthropic
    - 'AKIA[0-9A-Z]{16}'          # AWS
    - 'ghp_[A-Za-z0-9]{36}'       # GitHub
    - 'xox[baprs]-[A-Za-z0-9-]+'  # Slack
```

Replaces matches with `«redacted»` before the tool sees them. No
Python, no dependencies.

## Recipe 2: budget alarm (Python)

```python title="~/.lyra/hooks/budget_alarm.py"
"""Warn at 80%, hard-stop at 100% of session budget."""

from lyra_core.hooks import hook, Decision, Event

BUDGET_USD = 5.0

@hook(event=Event.PreToolUse)
def check_budget(ctx) -> Decision:
    spent = ctx.session.cost_usd
    if spent >= BUDGET_USD:
        return Decision.deny(
            reason=f"session cost ${spent:.2f} >= budget ${BUDGET_USD}",
            user_message="Hit budget. Run `/budget +2` to extend.",
        )
    if spent >= BUDGET_USD * 0.8:
        return Decision.allow().with_warning(
            f"⚠️ {spent / BUDGET_USD:.0%} of budget used"
        )
    return Decision.allow()
```

The decorator registers the hook with the Python loader. The
`Decision` object is the same shape the permission bridge uses, so a
hook's deny is indistinguishable from a permission deny in the trace.

## Recipe 3: TDD anchor (Python, scope-aware)

```python title=".lyra/hooks/tdd_anchor.py"
"""Block writes to tests/ during 'green' phase to prevent test-rewriting."""

from lyra_core.hooks import hook, Decision, Event

@hook(event=Event.PreToolUse, scope="repo")
def block_test_edits_in_green(ctx) -> Decision:
    if ctx.session.tdd_phase != "green":
        return Decision.allow()
    if ctx.tool.name not in {"write", "edit"}:
        return Decision.allow()
    if not ctx.tool.args["path"].startswith("tests/"):
        return Decision.allow()
    return Decision.deny(
        reason="TDD green phase: tests must not be modified",
        user_message=(
            "You're in green phase; the tests are the spec. "
            "Run `/tdd phase red` if you genuinely need to revise the spec."
        ),
    )
```

`scope="repo"` means this hook only fires for sessions running in
this repository — useful when your gate depends on project-specific
conventions.

## All lifecycle events

| Event | When | Block? | Mutate? |
|---|---|---|---|
| `UserPromptSubmit` | Before context assembly | yes | redact |
| `PreToolUse` | Before any tool call | yes | redact args |
| `PostToolUse` | After any tool call | warn | redact result |
| `PreSubagent` | Before subagent spawn | yes | trim scope |
| `PostSubagent` | After subagent return | warn | redact summary |
| `PrePlan` | Before plan run | yes | augment context |
| `PostPlan` | After plan written | warn | annotate |
| `PreVerify` | Before verifier runs | yes | inject extra checks |
| `PostVerify` | After verdict | warn | downgrade verdict |
| `PreSessionEnd` | Before STATE.md final write | warn | append notes |

See [reference/hooks.md](../reference/hooks.md) for the full event
table and `Decision` types.

## The `Decision` API

```python
Decision.allow()                        # default
Decision.allow().with_warning("…")      # surfaces in HUD
Decision.deny(reason="…",
              user_message="…")         # stops the action
Decision.modify(new_args={…})           # rewrite args (PreToolUse only)
Decision.redact(replacement="…")        # mask matches in args/result
```

A hook can return early via raise — uncaught exceptions become
`Decision.deny(reason=…)` with the traceback in the trace.

## Order of evaluation

Multiple hooks for the same event run in **registration order**;
**any deny stops further evaluation**. So put cheap deny-fast hooks
first:

```python
@hook(event=Event.PreToolUse, priority=10)   # runs first
def deny_dangerous_paths(ctx): …

@hook(event=Event.PreToolUse, priority=50)   # runs after
def expensive_lint_check(ctx): …
```

Lower priority = earlier. Default priority is 100.

## Testing a hook

```bash
lyra hooks list                          # see what's registered
lyra hooks test secret-redactor \
    --event PreToolUse \
    --tool view \
    --args '{"path": "/etc/secrets.yaml"}'
```

The harness loads the hook in isolation and runs the simulated
event against it, returning the `Decision` it would have produced.
This is the right way to debug a misbehaving hook.

## Hooks vs permissions vs safety monitor

| Layer | When | Speed | Use for |
|---|---|---|---|
| **Permission bridge** | Every tool call | µs | Mode × tool grid (general policy) |
| **Hook** | Lifecycle event | ms | Project-specific gates, redaction |
| **Safety monitor** | Every N steps | s (model call) | Trajectory drift, scope creep |

The three layers are **independent voters** — a permission allow can
still be denied by a hook, and a hook allow can still be interrupted
by the safety monitor.

## Where hooks live

| Path | Scope |
|---|---|
| `~/.lyra/hooks/*.py`, `*.yaml` | User-global (every session) |
| `.lyra/hooks/*.py`, `*.yaml` | Repo (this project only) |
| Plugin packages | Bundled with installed plugins |

Repo > User > Plugin on collision. Use `lyra hooks list` to see what
won.

[← How-to index](index.md){ .md-button }
[Reference: hooks →](../reference/hooks.md){ .md-button .md-button--primary }
