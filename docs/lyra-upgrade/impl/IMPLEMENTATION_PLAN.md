# Lyra Upgrade — Implementation Plan

> Dependency-ordered build queue. Every plan item from plans/4.x-*.md and plans/5.x-*.md tracked as a row.
> Status: `pending` | `spec'd` | `building` | `implemented` | `deferred(reason)` | `rejected(reason)`
> **Last updated:** 2026-06-07

---

## Dependency Graph (High-Level)

```
Phase 1 — SUBSTRATE (foundations nothing else can work without)
  ├── 4.5  Provider Abstraction Layer  ← EVERYTHING depends on this
  ├── 4.10 Hooks System                ← extensibility spine
  ├── 4.12 Permissions & Credentials   ← security foundation
  ├── 4.2  Memory Architecture         ← dreaming, skills, research depend on this
  ├── 4.3  Context & Auto-Compaction   ← deep research, voice depend on this
  ├── 4.6  Tools Implementation        ← agents need tools
  ├── 4.8  MCP Integration             ← tool ecosystem
  ├── 4.9  Commands & Interactive Mode ← UX foundation
  ├── 4.11 Sessions & Checkpointing    ← fleet, autonomy depend on this
  ├── 4.13 Supervisor/Fleet Core       ← autonomy, desktop depend on this
  ├── 4.4  Skills System               ← optimizer, self-evolving depend on this
  ├── 4.7  Plugins System              ← extensibility
  ├── 4.1  UI/UX Foundation            ← desktop, voice UI depend on this
  └── 4.26 Harness Engineering         ← underpins everything

Phase 2 — PRIMARY DIRECTIONS
  ├── 4.13+4.25 Multi-Agent Swarm + Adversarial Panel
  ├── 4.4+4.24+4.27 Self-Evolving (Skills + Dreaming + RL Optimizer)
  ├── 4.15 Auto-Research + Deep-Research
  └── 4.14 Full Autonomy

Phase 3 — VOICE MODE FLAGSHIP
  └── 4.18 Voice Mode (ultra-plan) + 5.3 SFX/Personality

Phase 3.5 — CODEBASE CLEANUP
  └── Restructure to best practice

REMAINING WORKSTREAMS (substrate-level, build after foundations)
  ├── 4.16 Reliability & Verifier
  ├── 4.17 Safety & Guardrails
  ├── 4.19 Self-Knowledge / Uncertainty
  ├── 4.20 Planning & Reasoning Layer
  ├── 4.21 Performance & Cost Economics
  ├── 4.22 Human Steering & Interruptibility
  ├── 4.23 Knowledge Ingestion / RAG
  ├── 4.28 Desktop GUI
  ├── 5.1 rmux Rebuild
  └── 5.2 Multi-Tenancy (AgentsMesh)

Phase 4 — DOCS + TEST PLAN
  ├── §6 Full docs tree
  └── §7 Test plan execution

Phase 5 — AUDIT
  └── Fresh auditor verification
```

---

## Build Queue (Dependency-Ordered)

### Phase 1 — SUBSTRATE

| # | Item | Plan | Priority | Depends On | Status | Spec | Branch | PR/Commit |
|---|------|------|----------|------------|--------|------|--------|-----------|
| 1.1 | Provider Abstraction Layer (ProviderBackend protocol) | 05-model-router.md BP-2 | P0 — BLOCKS ALL | none | pending | — | — | — |
| 1.2 | Three-Tier Static Router (Haiku→Sonnet→Opus) | 05-model-router.md BP-1 | P0 | 1.1 | pending | — | — | — |
| 1.3 | Multi-Head Learned Router (DeBERTa-v3) | 05-model-router.md BP-1 | P2 | 1.2 | pending | — | — | — |
| 1.4 | Memory-Augmented Compound Routing | 05-model-router.md BP-3 | P2 | 1.2, 4.2 | pending | — | — | — |
| 1.5 | Hooks: 25+ Lifecycle Events | 10-hooks.md §3.1 | P0 | none | pending | — | — | — |
| 1.6 | Hooks: YAML Config + Hot-Reload | 10-hooks.md §3.2-3.3 | P0 | 1.5 | pending | — | — | — |
| 1.7 | Hooks: Exit Code 2 Protocol + Matchers | 10-hooks.md §3.4-3.5 | P0 | 1.5 | pending | — | — | — |
| 1.8 | Hooks: 5 Handler Types (cmd/http/mcp/prompt/agent) | 10-hooks.md §3.6 | P1 | 1.5 | pending | — | — | — |
| 1.9 | Permissions: Three-Valued Model (allow/deny/ask) | 12-permissions.md | P0 | none | pending | — | — | — |
| 1.10 | Credentials: Env-Var + Secret Manager | 12-permissions.md | P0 | 1.9 | pending | — | — | — |
| 1.11 | Memory: Three-Tier Architecture (Core/Archival/Recall) | 02-memory.md BP-1 | P0 | 1.1 | pending | — | — | — |
| 1.12 | Memory: Multi-Signal Retrieval (vector+BM25+entity) | 02-memory.md BP-2 | P0 | 1.11 | pending | — | — | — |
| 1.13 | Memory: LLM-Driven Extraction (ADD-only, Mem0 V3 pattern) | 02-memory.md BP-3 | P1 | 1.11 | pending | — | — | — |
| 1.14 | Context: Iterative Workspace Reconstruction (M_t) | 03-context-compaction.md BP-1 | P0 | 1.1 | pending | — | — | — |
| 1.15 | Context: Auto-Compaction with Staged Collapse | 03-context-compaction.md BP-2 | P0 | 1.14 | pending | — | — | — |
| 1.16 | Tools: Full Tool Implementation | 06-tools.md | P0 | 1.1, 1.5 | pending | — | — | — |
| 1.17 | MCP: Integration + Server Bundling | 08-mcp.md | P1 | 1.1, 1.16 | pending | — | — | — |
| 1.18 | Commands: Full Command Set + Interactive UX | 09-commands.md | P1 | 1.1 | pending | — | — | — |
| 1.19 | Sessions: Checkpointing + State Persistence | 11-sessions.md | P0 | 1.1 | pending | — | — | — |
| 1.20 | Supervisor Daemon: Two-Axis State + Lifecycle | 13-swarm-fleet.md BP-1 | P0 | 1.19 | pending | — | — | — |
| 1.21 | Worktree Isolation: EnterWorktree + .worktreeinclude | 13-swarm-fleet.md BP-3 | P0 | 1.20 | pending | — | — | — |
| 1.22 | Fleet View TUI: State-Grouped Rows + Peek/Attach | 13-swarm-fleet.md BP-2 | P1 | 1.20 | pending | — | — | — |
| 1.23 | Skills: Harness-Level Loader (progressive disclosure) | 04-skills.md BP-1 | P0 | 1.1 | pending | — | — | — |
| 1.24 | Skills: Deterministic Matching + Provider Matrix | 04-skills.md BP-2 | P1 | 1.23 | pending | — | — | — |
| 1.25 | Skills: Auto-Evaluator + Skill Graph | 04-skills.md BP-3 | P2 | 1.23 | pending | — | — | — |
| 1.26 | Plugins: Plugin System | 07-plugins.md | P2 | 1.5, 1.23 | pending | — | — | — |
| 1.27 | UI/UX: Color Themes + Keybindings + UX Features | 01-ui-ux.md | P1 | 1.1 | pending | — | — | — |
| 1.28 | Harness Engineering: 5-Pillar Discipline | 26-harness-engineering.md | P1 | 1.1, 1.5 | pending | — | — | — |

### Phase 2 — PRIMARY DIRECTIONS

| # | Item | Plan | Priority | Depends On | Status | Spec | Branch | PR/Commit |
|---|------|------|----------|------------|--------|------|--------|-----------|
| 2.1 | Dynamic Workflow Engine (code-driven orchestration) | 13-swarm-fleet.md BP-4 | P0 | 1.20, 1.21 | pending | — | — | — |
| 2.2 | Adversarial Verification Panel (3-verifier + skeptic) | 25-adversarial-panel.md | P0 | 1.20, 1.5 | pending | — | — | — |
| 2.3 | Self-Evolving: Post-Session Memory Extraction | 02-memory.md BP-4 / 24-dreaming.md BP-1 | P1 | 1.11, 1.13 | pending | — | — | — |
| 2.4 | Self-Evolving: SkillOpt-Style Bounded-Edit Optimization | 27-rl-optimizer.md BP-1 | P1 | 1.23, 2.3 | pending | — | — | — |
| 2.5 | Self-Evolving: GEPA-Style Prompt Evolution | 27-rl-optimizer.md BP-2 | P2 | 2.4 | pending | — | — | — |
| 2.6 | Self-Evolving: Misevolution Guardrails | 17-safety.md BP-4 / 27-rl-optimizer.md | P0 | 2.4 | pending | — | — | — |
| 2.7 | Auto-Research: Scientists Team (hypothesis→experiment→revise) | 15-deep-research.md BP-3 | P1 | 1.20, 1.11 | pending | — | — | — |
| 2.8 | Deep-Research: Dual-Agent + Evidence DAG | 15-deep-research.md BP-1 | P0 | 1.14, 1.11 | pending | — | — | — |
| 2.9 | Deep-Research: Bundled /deep-research Workflow | 15-deep-research.md BP-2 | P1 | 2.1, 2.8 | pending | — | — | — |
| 2.10 | Autonomy: Continuous-Operation Loop (unattended) | 14-autonomy.md | P1 | 1.20, 2.2 | pending | — | — | — |
| 2.11 | Autonomy: Uncertainty-Gated Intervention (CALM) | 14-autonomy.md BP-1 / 19-self-knowledge.md BP-1 | P1 | 1.20, 1.5 | pending | — | — | — |

### Phase 3 — VOICE MODE FLAGSHIP

| # | Item | Plan | Priority | Depends On | Status | Spec | Branch | PR/Commit |
|---|------|------|----------|------------|--------|------|--------|-----------|
| 3.1 | Voice: Pipecat Pipeline + LiveKit WebRTC Transport | 18-voice-mode.md | P0 | 1.1 | pending | — | — | — |
| 3.2 | Voice: ASR Integration (Parakeet TDT / Whisper) | 18-voice-mode.md | P0 | 3.1 | pending | — | — | — |
| 3.3 | Voice: TTS Integration (Orpheus / Kokoro) | 18-voice-mode.md | P0 | 3.1 | pending | — | — | — |
| 3.4 | Voice: VAD + Endpointing + Barge-In | 18-voice-mode.md | P0 | 3.1 | pending | — | — | — |
| 3.5 | Voice: Self-Correction Buffer + Task Router | 18-voice-mode.md | P1 | 3.2, 3.4 | pending | — | — | — |
| 3.6 | Voice: Safety Gate + Watermarking | 18-voice-mode.md | P1 | 3.3 | pending | — | — | — |
| 3.7 | Voice: SFX/Personality Layer via Hooks (§5.3) | 18-voice-mode.md / 5.3 | P1 | 1.5, 3.3 | pending | — | — | — |
| 3.8 | Voice: VI+EN Bilingual Path | 18-voice-mode.md | P1 | 3.2, 3.3 | pending | — | — | — |
| 3.9 | Voice: Inner Monologue Migration Path (v2) | 18-voice-mode.md | P2 | 3.1-3.8 | pending | — | — | — |

### Phase 3.5 — CODEBASE CLEANUP

| # | Item | Plan | Priority | Depends On | Status | Spec | Branch | PR/Commit |
|---|------|------|----------|------------|--------|------|--------|-----------|
| 3.5.1 | Codebase Cleanup: Spec + Panel Sign-Off | (new spec) | P1 | Phase 1-3 complete | pending | — | — | — |
| 3.5.2 | Codebase Cleanup: Restructure + Hygiene | (new spec) | P1 | 3.5.1 | pending | — | — | — |

### REMAINING WORKSTREAMS

| # | Item | Plan | Priority | Depends On | Status | Spec | Branch | PR/Commit |
|---|------|------|----------|------------|--------|------|--------|-----------|
| R.1 | Reliability: Monitoring + Tracing (Langfuse/OpenLLMetry) | 16-reliability.md | P1 | 1.5, 1.1 | pending | — | — | — |
| R.2 | Reliability: Intelligent Verifier | 16-reliability.md BP-1 | P1 | 1.5, 1.20 | pending | — | — | — |
| R.3 | Safety: 5-Layer Defense-in-Depth | 17-safety.md BP-1 | P0 | 1.5, 1.9 | pending | — | — | — |
| R.4 | Safety: Deterministic Tool-Call Gating (Progent) | 17-safety.md BP-2 | P1 | R.3, 1.16 | pending | — | — | — |
| R.5 | Safety: Collusion Detection ("Lying with Truths") | 17-safety.md BP-3 | P2 | 1.20 | pending | — | — | — |
| R.6 | Self-Knowledge: Calibrated Confidence (JSD LoRA) | 19-self-knowledge.md BP-1 | P2 | 1.1 | pending | — | — | — |
| R.7 | Planning: MCTS + Deliberation Layer | 20-planning.md | P2 | 1.11, 1.14 | pending | — | — | — |
| R.8 | Economics: Cost Tracking + Token Budget per Session | 21-economics.md | P1 | 1.2 | pending | — | — | — |
| R.9 | Economics: Prompt Cache Hit-Rate Strategy | 21-economics.md BP-1 | P2 | 1.2, R.8 | pending | — | — | — |
| R.10 | Economics: KV-Cache Orchestration | 21-economics.md BP-2 | P2 | 1.1 | pending | — | — | — |
| R.11 | Steering: Steer-by-Exception Panel | 22-steering.md BP-1 | P1 | 1.20, 1.22 | pending | — | — | — |
| R.12 | Steering: Proactive Preference Elicitation | 22-steering.md BP-2 | P2 | R.11 | pending | — | — | — |
| R.13 | RAG: Hybrid Dense+Sparse + Graph RAG | 23-ingestion.md | P1 | 1.11 | pending | — | — | — |
| R.14 | Desktop: Electron + React GUI Shell | 28-desktop.md | P2 | 1.1, 1.27, 3.1 | pending | — | — | — |
| R.15 | Desktop: Multimodal Input/Output Routing | 28-desktop.md | P2 | R.14 | pending | — | — | — |
| R.16 | Desktop: Fleet View in GUI | 28-desktop.md | P2 | R.14, 1.22 | pending | — | — | — |
| R.17 | rmux: Clean Rebuild for Lyra | 51-rmux.md | P2 | 1.20, 1.21 | pending | — | — | — |
| R.18 | Multi-Tenancy: AgentsMesh Evaluation | 52-agentsmesh.md | P2 | 1.20 | pending | — | — | — |

---

## Summary

| Phase | Total Items | P0 (Blocks Others) | P1 (High) | P2 (Standard) |
|-------|-------------|---------------------|-----------|---------------|
| 1. Substrate | 28 | 14 | 10 | 4 |
| 2. Primary Directions | 11 | 4 | 5 | 2 |
| 3. Voice Mode | 9 | 4 | 4 | 1 |
| 3.5 Cleanup | 2 | 0 | 2 | 0 |
| Remaining | 18 | 1 | 8 | 9 |
| **TOTAL** | **68** | **23** | **29** | **16** |

**P0 items (23) must be implemented first** — they block all other work. Estimated: 2-4 weeks of focused development.
