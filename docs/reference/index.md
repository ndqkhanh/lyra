---
title: Reference
description: Authoritative tables and indexes — blocks, commands, env vars, hooks, tools, permission modes, and the long-form specs.
---

# Reference <span class="lyra-badge reference">reference</span>

Authoritative tables you'll come back to. Each entry on this index
either has its own page in this section, or links to the canonical
spec inside the project.

## Catalogues

| Page | What's there |
|---|---|
| [The 14 building blocks](blocks-index.md) | One-line summary + link to each block spec |
| [Slash commands](commands.md) | All ~80 slash commands grouped by category |
| [Environment variables](env-vars.md) | Canonical `LYRA_*` names + the legacy aliases each one shadows |
| [Hooks](hooks.md) | All lifecycle events, the `Decision` API, shipped hooks |
| [Tools](tools.md) | Every built-in tool with its schema, side-effects, default permission |
| [Permission modes](permission-modes.md) | All eight modes; the full mode × tool grid |
| [Subsystem map](subsystem-map.md) | Every directory under `lyra_core/` with what it does and where it's documented |

## Long-form specs

These pre-existed; they're under Reference for searchability.

| Page | What's there |
|---|---|
| [Feature parity](../feature-parity.md) | Table comparing Lyra to Claude Code / OpenClaw / Hermes / SemaClaw feature-by-feature |
| [Benchmarks](../benchmarks.md) | Internal eval numbers (SWE-bench Verified, sabotage suite, etc.) |
| [Threat model](../threat-model.md) | Adversaries, attack surfaces, mitigations |
| [TDD discipline](../tdd-discipline.md) | Full TDD plugin contract (gate hooks, modes, RED proof rules) |

## Naming conventions in code

Lyra uses **snake_case** for module names and Python identifiers and
**kebab-case** for CLI flags / slash command names / on-disk artifact
names. The package directory uses kebab-case (`lyra-core`) but the
import name uses snake_case (`lyra_core`). This is the standard
PEP 8 + setuptools idiom.

## Where to start

If you're looking up "how do I…?" → start with [How-To](../howto/index.md).
If you're looking up "what does X mean?" → start with [Concepts](../concepts/index.md).
If you're looking up "what's the exact value of …?" → you're in the right place.

[The 14 building blocks →](blocks-index.md){ .md-button .md-button--primary }
[Subsystem map →](subsystem-map.md){ .md-button }
