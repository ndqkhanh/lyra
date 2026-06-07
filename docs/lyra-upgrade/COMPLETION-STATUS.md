# COMPLETION-STATUS.md — Lyra Implementation Audit

> Run 5, 2026-06-03 | 21 agents, 2.28M tokens, 899 tool uses | Audit of 30 plans against actual codebase

## Critical Finding: Two Codebases

Lyra has TWO parallel implementations:
- **`packages/lyra-*`**: Advanced, feature-rich packages (100+). Comprehensive provider adapters, router, memory, skills, workflows, evolution. Each has its own test suite.
- **`src/`**: Older, simpler codebase. `src/agents/primary.py` uses hardcoded keyword matching. Not integrated with the package ecosystem.

**The implementation task is INTEGRATION, not greenfield construction.** Most features exist in packages but need to be wired into the main agent loop.

## Per-Plan Status

### TIER 1 — Provider & Reasoning Foundation

| Plan | Status | Key Gap |
|------|--------|---------|
| §4.5 Router | **PARTIAL** | Provider adapters exist (Anthropic/DeepSeek/OpenAI/Ollama in `packages/lyra-provider/`) but NOT wired into `src/agents/primary.py`. No YAML config loading. No auto-discover for local endpoints. Memory-augmented routing not implemented. |
| Effort Scale | **PARTIAL** | Effort-to-budget mapping in `lyra_provider/adapters/anthropic.py:198`. 6-item menu NOT in `/effort` command. Ultracode toggle not implemented. |

### TIER 2 — Memory & Context

| Plan | Status | Key Gap |
|------|--------|---------|
| §4.2 Memory | **PARTIAL** | 140+ .py files in `packages/lyra-memory/`. CraniMem, unified router, knowledge graph exist. NOT integrated with `src/memory/`. |
| §4.3 Context | **PARTIAL** | Auto-compaction exists in `packages/lyra-context/` (3 files). NOT wired into agent loop context management. |

### TIER 3 — Fleet, Workflow, Autonomy

| Plan | Status | Key Gap |
|------|--------|---------|
| §4.13 Fleet/Swarm | **PARTIAL** | DAG orchestrator (13 files) in `packages/lyra-orchestration/`. Workflow engine (7 files) in `packages/lyra-workflow/`. Fleet TUI (5 files) in `packages/lyra-fleet-tui/`. Supervisor daemon NOT built. Worktree auto-isolation NOT built. |
| §4.14 Autonomy | **PARTIAL** | Crash detection, autoresearch (7 files) in `packages/lyra-autoresearch/`. Continuous loop NOT wired to supervisor (supervisor doesn't exist). |

### TIER 4 — Capability Surface

| Plan | Status | Key Gap |
|------|--------|---------|
| §4.6 Tools | **PARTIAL** | 23 .py files in `packages/lyra-tools/`. Tool runtime, masking, gating exist. NOT integrated with `src/` agent tool dispatch. |
| §4.7 Plugins | **STUBBED** | Manifest system (5 files) in `packages/lyra-plugins/`. No marketplace. No hot-reload integrated. |
| §4.8 MCP | **PARTIAL** | 17 .py files in `packages/lyra-mcp/`. Gateway, bundling exist. ANX 3EX decoupling not implemented. |
| §4.9 Commands | **NOT-STARTED** | Slash command registry exists but custom commands (.lyra/commands/*.md) not implemented. |
| §4.10 Hooks | **PARTIAL** | HookEngine in `packages/lyra-hooks/` (3 files). 27+ events exist. TDD gate not enforced in agent loop. |
| §4.11 Sessions | **STUBBED** | Fork + resumable (2 files) in `packages/lyra-sessions/`. Not integrated. No agent-view style backgrounding. |
| §4.12 Permissions | **PARTIAL** | Permission bridge + scope rules exist. Unwatched-session guard NOT implemented (depends on supervisor). |
| §4.23 Ingestion | **STUBBED** | ETL pipeline exists. SEMA-RAG multi-agent retrieval not implemented. |

### TIER 5 — Skills

| Plan | Status | Key Gap |
|------|--------|---------|
| §4.4 Skills | **PARTIAL** | 49 .py files in `packages/lyra-skills/`. Loader, curator, generator, evolution exist. SkillNet graph NOT integrated. Starter skills exist in `.lyra/skills/`. |

### TIER 6 — Voice (Flagship)

| Plan | Status | Key Gap |
|------|--------|---------|
| §4.18 Voice | **PARTIAL** | 11 .py files in `packages/lyra-voice/`. Pipeline, providers, SFX exist. No real-time VAD integration. No barge-in. No full-duplex S2S. |

### TIER 7 — Reliability, Safety, Self-Knowledge

| Plan | Status | Key Gap |
|------|--------|---------|
| §4.16 Reliability | **PARTIAL** | Observability (5 files), OTel tracer exist. Not integrated into agent loop. |
| §4.17 Safety | **PARTIAL** | Safety governance + AgentShield + sandbox (11 files) exist. 7-layer defense not all wired. |
| §4.19 Self-Knowledge | **STUBBED** | Beliefs, competence map, causal graph exist as packages. Not integrated. |
| §4.20 Planning | **PARTIAL** | 25 .py files in `packages/lyra-reasoning/`. CoT, tree search, plan-mode engine exist. |
| §4.21 Economics | **STUBBED** | Cost tracking (9 files) exists. Per-workflow budget API not integrated. |
| §4.22 Steering | **STUBBED** | Human interaction + cockpit (16 files) exist. Not wired to fleet view. |

### TIER 8 — UI/UX + Investigations

| Plan | Status | Key Gap |
|------|--------|---------|
| §4.1 UI/UX | **PARTIAL** | 25+ themes exist. Keybinding config NOT implemented. |
| §5.1 rmux | **STUBBED** | 12 .py files in `packages/lyra-rmux/`. Clean-room rebuild started. |
| §5.2 AgentsMesh | **NOT-STARTED** | Deferred to v2 per plan recommendation. |

### TIER 9 — Desktop + Multimodal

| Plan | Status | Key Gap |
|------|--------|---------|
| §4.28 Desktop | **NOT-STARTED** | No desktop app exists. Agent-core local API not exposed. |

### CROSS-CUTTING

| Plan | Status | Key Gap |
|------|--------|---------|
| §4.24 Dreaming | **STUBBED** | MemoryConsolidator exists with THRESHOLD policy. Not integrated with idle detection or fleet. |
| §4.25 Adversarial | **PARTIAL** | 8 attack strategies exist. Anonymization, ReTAS, triangulation NOT implemented. |
| §4.26 Harness Eng. | **PARTIAL** | Infrastructure exists as packages. Not formalized as 5-pillar discipline. |
| §4.27 RL Optimizer | **PARTIAL** | 30 .py files in `packages/lyra-evolution/`. GEPA, policy optimizer, meta-evolution exist. |

## Summary

| Status | Count | Plans |
|--------|-------|-------|
| DONE | 0 | — |
| PARTIAL | 21 | §4.1, §4.2, §4.3, §4.4, §4.5, §4.6, §4.8, §4.10, §4.12, §4.13, §4.14, §4.15, §4.16, §4.17, §4.18, §4.20, §4.25, §4.26, §4.27, Effort Scale |
| STUBBED | 7 | §4.7, §4.11, §4.19, §4.21, §4.22, §4.23, §4.24, §5.1 |
| NOT-STARTED | 3 | §4.9, §4.28, §5.2 |

## Root Cause

**The `packages/` ecosystem (40 modules) contains comprehensive implementations NOT wired into the main `src/` agent loop.** `src/agents/primary.py:92-110` uses hardcoded keyword matching instead of the package router. The implementation task is:

1. **Wire packages → src/** (integrate existing implementations into the agent loop)
2. **Build missing pieces** (supervisor daemon, worktree auto-isolation, ultracode toggle)
3. **Fill stub gaps** (replace placeholder code with real behavior)
4. **Add multi-provider fallbacks** (DeepSeek paths where only Anthropic exists)

## Ordered Implementation Checklist

### BLOCKERS (fix before any tier)
- [ ] Fix Python test import path (`ModuleNotFoundError: adapters.base`)
- [ ] Verify npm test suite passes for TypeScript code

### TIER 1 (Provider + Reasoning)
- [ ] Wire `lyra-provider` adapters into `src/agents/primary.py` dispatch
- [ ] Implement `/effort` 6-item menu with per-provider budget mapping
- [ ] Implement ultracode toggle (xhigh + auto-orchestration)
- [ ] Implement YAML provider config loading
- [ ] Implement Memory-Augmented Router for cache-hit routing
- [ ] Implement FallbackChain with typed escalation
- [ ] Integration tests for each provider

### TIER 2 (Memory + Context)
- [ ] Wire `lyra-memory` into `src/memory/`
- [ ] Integrate CraniMem with agent loop
- [ ] Wire auto-compaction into context management
- [ ] Implement Dreaming consolidation trigger

### TIER 3 (Fleet + Workflow + Autonomy)
- [ ] Build supervisor daemon (session lifecycle, disk state, survive sleep)
- [ ] Build EnterWorktree tool with auto-isolation
- [ ] Implement non-destructive cleanup (auto-stash default)
- [ ] Harden fleet view TUI (two-axis state model, peek/reply)
- [ ] Wire workflow engine (background, resumable, script variables)
- [ ] Implement unwatched-session permission guard
- [ ] Per-session quota governance

### TIER 4+ (remaining tiers in dependency order)
- [ ] (see per-plan criteria above — 20+ items)

## False-Done Hunt Results

| File | Issue | Severity |
|------|-------|----------|
| `src/agents/primary.py:92-110` | Hardcoded keyword matching instead of router | CRITICAL |
| `packages/lyra-cli/providers/ollama.py:256` | `TODO: phase-14 streaming` — streaming not implemented | HIGH |
| Multiple packages | Code exists in packages but `src/` has no import of them | CRITICAL |
| Test path | `tests/adapters/test_adapters.py` — import path broken | HIGH |
