---
title: Permission modes reference
description: All eight modes, the full mode × tool grid, mode transitions, and the explain trail.
---

# Permission modes reference <span class="lyra-badge reference">reference</span>

The permission bridge is a **mode × tool × scope** decision matrix.
This page is the canonical grid.

For the concept, see [Permission bridge](../concepts/permission-bridge.md).

## The eight modes

| Mode | Risk shape | Default writes | Default bash | Network | Use when |
|---|---|---|---|---|---|
| `default` | Highest friction | ask | ask (allowlist auto-allows) | ask | First-time tasks, unknown territory |
| `acceptEdits` | Low-friction edits | allow | ask (allowlist auto-allows) | allow | Active development, planned changes |
| `acceptAll` | Trust mode | allow | allow | allow | CI runs, known-safe scripted tasks |
| `bypass` | Maximum trust | allow | allow | allow | Sandbox / disposable env only |
| `plan` | Read-only | deny | ask (read-only commands only) | ask | Plan mode (auto-set) |
| `debug` | Read + verify | deny except memory | ask | ask | Debug mode (auto-set) |
| `cron` | Acceptedits + safety | allow | ask + destructive denied | allow | Cron-spawned sessions (auto-set) |
| `frozen` | Total halt | deny | deny | deny | Emergency / kill-switch |

Modes are **per-session**. Switch with `/permissions <mode>` or
`--permission-mode <mode>` on launch. The HUD always shows the
current mode in the header.

## Full mode × tool grid

`A` = allow, `?` = ask, `D` = deny, `Aₚ` = allow if pattern allowlisted,
`?ᵤ` = ask once per session then remember.

| Tool | default | acceptEdits | acceptAll | bypass | plan | debug | cron | frozen |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `view` | A | A | A | A | A | A | A | D |
| `glob` | A | A | A | A | A | A | A | D |
| `grep` | A | A | A | A | A | A | A | D |
| `read_memory` | A | A | A | A | A | A | A | D |
| `time_travel_replay` | A | A | A | A | A | A | A | D |
| `web_fetch` | ? | A | A | A | ? | ? | A | D |
| `web_search` | ? | A | A | A | ? | ? | A | D |
| `write` | ? | A | A | A | D | D | A | D |
| `edit` | ? | A | A | A | D | D | A | D |
| `multiedit` | ? | A | A | A | D | D | A | D |
| `delete` | ? | ? | A | A | D | D | ? | D |
| `bash` | Aₚ/? | Aₚ/? | A | A | Aₚ/? | Aₚ/? | Aₚ/? + destructive D | D |
| `subagent_spawn` | A (≤3 depth) | A | A | A | D | D | D | D |
| `write_memory` | A | A | A | A | A | A | A | D |
| `run_tests` | A | A | A | A | A | A | A | D |
| `lint` / `typecheck` | A | A | A | A | A | A | A | D |
| MCP tools (default) | ? | ? | A | A | ?ᵤ | ?ᵤ | A | D |

Notes:

- "Aₚ" applies to bash commands matching the safe-pattern allowlist
  (`git status`, `pytest …`, `npm test …`, etc.) — the rest are `?`.
- "destructive D" applies to a built-in regex set (`rm -rf`, `chmod -R`,
  `git reset --hard`, `DROP TABLE`, …); see
  [`lyra_core/cron/destructive_patterns.yaml`](https://github.com/lyra-contributors/lyra).
- The MCP-tool default can be overridden per-server in the MCP
  config.

## Per-policy override

A policy file can override the grid for a specific scope:

```yaml title=".lyra/policies/dev.yaml"
extends: acceptEdits
overrides:
  - tool: bash
    pattern: "git push.*"
    decision: ask                # always ask before push
  - tool: web_fetch
    decision: deny               # no network in this repo
  - tool: mcp:supabase:*
    decision: ask
    remember_session: true
```

Activate with `lyra run … --permission-policy dev`.

## Mode transitions

| From → To | Trigger | Auto? |
|---|---|---|
| any → `plan` | Entering plan mode | yes |
| `plan` → `acceptEdits` (low-risk plan) | Plan approved | yes |
| `plan` → `default` (high-risk plan, > 10 files or has bash) | Plan approved | yes |
| any → `debug` | `/debug` command | manual |
| `debug` → previous | `/exit-debug` | manual |
| any → `frozen` | Safety monitor `interrupt`, kill-switch | yes |
| `frozen` → previous | User `/unfreeze` after review | manual |
| any → `cron` | Cron daemon spawn | yes |

Transitions are **logged** (`PermissionBridge.mode_change`) and
visible in the HUD when they happen.

## The decision

Every tool call returns one of:

| Verdict | Effect |
|---|---|
| `allow` | Proceed |
| `ask(prompt, scope)` | Pause loop, prompt user (`once`, `session`, `always`) |
| `deny(reason)` | Refuse; trace records reason |

Hooks can override an `allow` to `ask`/`deny` but **cannot override**
a permission `deny`. Hooks **can** override a permission `ask` to
`allow` (for project-specific shortcut) — but this surfaces as
`override:hook=<name>` in the trace.

## Inspecting

```bash
lyra permissions show                  # current mode + active overrides
lyra permissions explain bash 'git push origin HEAD'
   # → walks through the bridge logic step-by-step:
   # 1. Mode: acceptEdits
   # 2. Tool category: bash
   # 3. Safe-pattern allowlist match? no (git push not allowlisted)
   # 4. Mode-grid decision: ask
   # 5. Active hooks: dangerous-bash-guard ⇒ ask
   # 6. Final: ask
```

The `explain` command is **unconditional** — it never actually runs
the tool, just shows what would happen. Use this to verify a policy
change before deploying.

## Where to look

| File | What lives there |
|---|---|
| `lyra_core/permissions/bridge.py` | The decision pipeline |
| `lyra_core/permissions/modes.py` | Mode definitions and grid |
| `lyra_core/permissions/safe_patterns.yaml` | Bash allowlist |
| `lyra_core/permissions/policy.py` | Policy file loader |
| `lyra_cli/commands/permissions.py` | `lyra permissions …` CLI |

[← Reference: tools](tools.md){ .md-button }
[Continue: subsystem map →](subsystem-map.md){ .md-button .md-button--primary }
