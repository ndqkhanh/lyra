---
title: Subsystem map
description: Every directory under lyra_core/, what it does, and which doc page covers it (or "internal — see source").
---

# Subsystem map <span class="lyra-badge reference">reference</span>

Lyra has **45 top-level subsystems** under
`packages/lyra-core/src/lyra_core/`. This page is the index — every
directory, what it owns, and where to learn more.

## Convention

| Status | Meaning |
|---|---|
| **doc** | Has a dedicated concept / how-to / reference page |
| **block** | Specified in `docs/blocks/` (canonical) — concept page may also exist |
| **source** | No standalone doc; canonical answer is the source code |

## Core loop and orchestration

| Dir | Owns | Docs |
|---|---|---|
| `agent/` | The kernel agent loop | doc → [Agent loop](../concepts/agent-loop.md) · block → [01](../blocks/01-agent-loop.md) |
| `loop/` | Loop helpers (turn iterator, step accounting) | source |
| `gateway/` | Control plane: event bus, registries, routing dispatch | source |
| `sessions/` | Session store, STATE.md writer, JSONL migrations | doc → [Sessions and state](../concepts/sessions-and-state.md) |
| `store/` | Todo store and other small persistent stores | source |

## Modes and planning

| Dir | Owns | Docs |
|---|---|---|
| `plan/` | Plan mode: planner, artifact, heuristics, approval | doc → [Plan mode](../concepts/plan-mode.md) · block → [02](../blocks/02-plan-mode.md) |
| `meta/` | Mode definitions and metadata | source |
| `ide/` | IDE-channel hooks (cursor position, selection, etc.) | source — experimental |

## Tools and execution

| Dir | Owns | Docs |
|---|---|---|
| `tools/` | Built-in tools: view, write, bash, web, … | doc → [Tools reference](tools.md) · block → [04](../blocks/04-tools-mcp-bridge.md) |
| `terminal/` | Terminal capture, ANSI handling | source |
| `mcp/` | MCP client, server registration, tool exposure | doc → [Add MCP server](../howto/add-mcp-server.md) · block → [04](../blocks/04-tools-mcp-bridge.md) |
| `lsp_backend/` | LSP server integration (semantic search, refactor) | source — experimental |
| `tts/` | Text-to-speech voice channel | source — opt-in |

## Permissions and safety

| Dir | Owns | Docs |
|---|---|---|
| `permissions/` | Permission bridge, modes, policies, quotas | doc → [Permission bridge](../concepts/permission-bridge.md), [reference](permission-modes.md) · block → [05](../blocks/05-permission-bridge.md) |
| `hooks/` | Hook system: registry, loader, decisions, builtins | doc → [Tools and hooks](../concepts/tools-and-hooks.md), [write-hook](../howto/write-hook.md), [reference](hooks.md) · block → [06](../blocks/06-hooks-and-events.md) |
| `safety/` | Safety monitor + red-team suite | doc → [Safety monitor](../concepts/safety-monitor.md) · block → [12](../blocks/12-safety-monitor.md) |
| `auth/` | Auth preflight + diagnostics for providers | source |

## Memory and context

| Dir | Owns | Docs |
|---|---|---|
| `context/` | Context engine, layers L0–L4, compaction | doc → [Context engine](../concepts/context-engine.md) · block → [07](../blocks/07-context-engine.md) |
| `memory/` | Three-tier memory store and retrieval | doc → [Memory tiers](../concepts/memory-tiers.md) · block → [10](../blocks/10-three-tier-memory.md) |
| `retrieval/` | Embedding-side helpers, vector backends | source |
| `wiki/` | Agentic wiki generator (writes structured memory back) | source |
| `migrations/` | Memory store schema migrations | source |

## Skills and plugins

| Dir | Owns | Docs |
|---|---|---|
| `skills/` | Skill loader, router, extractor, curator | doc → [Skills](../concepts/skills.md), [write-skill](../howto/write-skill.md) · block → [09](../blocks/09-skill-engine-and-extractor.md) |
| `plugins/` | Plugin discovery, manifest, registry, runtime | doc → [Write a plugin](../howto/write-plugin.md) |

## Subagents and concurrency

| Dir | Owns | Docs |
|---|---|---|
| `subagent/` | Subagent kernel, scope checking, worktree lifecycle | doc → [Subagents](../concepts/subagents.md) · block → [03](../blocks/03-subagents.md) |
| `teams/` | Multi-team coordination registry | source |
| `org/` | Org-level coordination (roadmap, multi-repo) | source — experimental |

## Verification and TDD

| Dir | Owns | Docs |
|---|---|---|
| `verifier/` | Two-phase + cross-channel verifier, PRM, TDD reward | doc → [Verifier](../concepts/verifier.md) · block → [11](../blocks/11-verifier-cross-channel.md) |
| `tdd/` | TDD gate state machine | doc → [TDD gate](../howto/tdd-gate.md) |
| `eval/` | In-loop eval scaffolds: corpus, drift gate, pass@k, PRM, rubrics | doc → [Run an eval](../howto/run-eval.md) |
| `arena/` | Elo-rated comparison arena (configs, prompts) | source |

## Observability and tracing

| Dir | Owns | Docs |
|---|---|---|
| `observability/` | HIR span emission, OTel export, retro / replay | doc → [Observability](../concepts/observability.md), [replay-trace](../howto/replay-trace.md) · block → [13](../blocks/13-observability-hir.md) |
| `hir/` | HIR event schema | source |

## Routing and providers

| Dir | Owns | Docs |
|---|---|---|
| `providers/` | Provider clients (16 LLM backends) | doc → [Configure providers](../howto/configure-providers.md) · block → [14](../blocks/14-provider-routing.md) |
| `routing/` | Cascade logic + fast-slot escalation | doc → [Two-tier routing](../concepts/two-tier-routing.md) |
| `brains/` | Specialised inference paths (e.g. small-model nano calls) | source |

## Adapters (formerly "harnesses")

| Dir | Owns | Docs |
|---|---|---|
| `adapters/` | Plug-in harness shapes: 3-agent, single-agent, DAG-team, swarm | doc → [Harness plugins](../architecture/harness-plugins.md) |
| `harnesses/` | Backwards-compat re-export shim (deprecated) | source |
| `acp/` | ACP — Agent Control Protocol server bindings | source — experimental |

## Scheduling

| Dir | Owns | Docs |
|---|---|---|
| `cron/` | Cron daemon, schedule store, history | doc → [Cron skill](../howto/cron-skill.md) |

## Research and frontier

| Dir | Owns | Docs |
|---|---|---|
| `evolve/` | GEPA-style evolutionary skill optimisation | source — see [Phase J research](../research-synthesis-phase-j.md) |
| `diversity/` | Diversity metrics for multi-agent ensemble | source — see Phase J research |
| `rl/` | RL training scaffolds for skill / policy improvement | source — experimental |
| `klong/` | Klong-DSL checkpoints (compact policy programs) | source — research |

## Internal / scaffolding

| Dir | Owns | Docs |
|---|---|---|
| `mock_llm/` | Mock LLM for tests | source |
| `concurrency.py` | ContextVars helpers for thread-safe context | covered in [Subagents](../concepts/subagents.md) |
| `env_compat.py` | Legacy env-var compat layer | covered in [Env vars](env-vars.md) |
| `paths.py` | Repo / user / cache path resolver | source |

## Quick lookup

If you need to know "where does X live?", scan this table:

| Looking for… | Look in |
|---|---|
| The agent loop's main step iterator | `agent/`, `loop/` |
| Why a permission decision was made | `permissions/`, then `hooks/` |
| Why a tool call got modified | `hooks/` |
| The plan artifact | `plan/`, `.lyra/plans/` |
| Cost meter logic | `agent/loop.py`, `routing/cascade.py` |
| Where a session is stored | `sessions/`, `.lyra/sessions/` |
| The HIR event types | `hir/events.py` |
| OTel spans being emitted | `observability/otel_export.py` |
| Cascade decisions | `routing/cascade.py` |
| Skill matching for a task | `skills/router.py` |
| Skill curator decisions | `skills/curator.py` |
| MCP server lifecycle | `mcp/` |
| Cross-channel verification | `verifier/cross_channel.py` |
| Safety monitor verdicts | `safety/monitor.py` |
| Cron schedule parsing | `cron/schedule.py` |

[← Reference: permission modes](permission-modes.md){ .md-button }
[Reference index →](index.md){ .md-button .md-button--primary }
