# Architecture Debate — Full Candidate Descriptions & Multi-Round Critique

> Run 1 — June 3, 2026 | The complete debate record — candidates, critiques, rebuttals, convergence
> Companion to DEBATE-LEDGER.md (round-by-round log)

---

## Candidate A — Memory-Centric Architecture

**Proposer:** Senior AI Researcher
**Core bet:** Memory is the AGI bottleneck (Hassabis). Build the breakthrough from memory outward.

### Design

```
Memory Plane (Foundation)
├── Field-Theoretic Memory (PDE-governed continuous fields)
├── Zettelkasten Graph (linked notes, LP-RAG prediction)
├── Cost-Sensitive Multi-Store Routing
├── A-MAC 5-Factor Admission Control
├── Dreaming Engine (idle-time PDE consolidation)
│
├── On top of memory:
│   ├── Context Manager (auto-compaction via memory retrieval)
│   ├── Skills System (skills as procedural memories)
│   ├── Agent Orchestration (agents read/write shared memory)
│   └── Fleet (fleet sessions share semantic memory)
```

### Strengths
- Strongest research foundation (28 papers)
- Field-theoretic memory is genuinely novel
- Memory improvements benefit every other subsystem
- Clean layering: memory is a service, everything else consumes it

### Weaknesses
- Memory is a SERVICE, not an architecture spine
- Field-theoretic approach is unproven in production (1 paper, 0 deployments)
- Doesn't address Lyra's most visible gap: can't run unattended or in parallel
- Fleet/supervisor/orchestration is an afterthought

### Critique Highlights
- **Senior Architect:** "Memory doesn't drive system boundaries. What's the API between memory and fleet? What's the concurrency model? Memory-centric architectures end up with everything depending on a singleton MemoryService that becomes the bottleneck."
- **Senior Backend:** "Building field-theoretic memory before graph memory is like building a quantum computer before a classical one. Ship incremental memory improvements, not a paradigm shift."
- **Adversarial Skeptic:** "This architecture optimizes for memory research novelty, not Lyra user value. Users need a fleet and voice more than they need PDE-governed memory consolidation."

### Verdict: ABSORBED into Candidate B — memory innovations preserved as the first major capability the fleet exercises. Field-theoretic approach gated behind bake-off.

---

## Candidate B — Fleet-Centric Architecture (WINNER)

**Proposer:** Senior Software Architect + Senior Distributed-Systems Engineer
**Core bet:** Orchestration IS the architecture. Build the fleet, then layer capabilities on top.

### Design

```
Orchestration Plane (Foundation)
├── Supervisor Daemon (session lifecycle, disk-persisted state)
├── Fleet View TUI (state-grouped rows, cheap row summaries)
├── Worktree Isolation Substrate (per-session git worktree, non-destructive cleanup)
├── Dynamic Workflow Engine (agent/parallel/pipeline, resumable checkpoints)
├── Channels (inter-agent comms, collusion-monitored)
│
├── Capability Planes (layered on orchestration):
│   ├── Intelligence: PrimaryAgent + Specialists + Model Router + Planning Layer
│   ├── Memory: Graph Memory + Vector + Cost-Sensitive Routing + Dreaming
│   ├── Skills: 330+ Skills + Self-Evolving + Safety Validator
│   ├── Voice: Provider-Swappable STT→Agent→TTS Pipeline
│   ├── Safety: 5-Layer Defense-in-Depth + Collusion Detection + Sandbox
│   └── Observability: Tracing + Monitoring + Eval Harness
│
├── User Surface:
    ├── CLI/TUI (terminal-native)
    ├── lyra-desktop (Electron/React GUI, multimodal)
    └── Local API (HTTP/SSE on localhost — both clients consume)
```

### Strengths
- Clean system boundaries: supervisor manages processes, worktrees manage files, workflow engine manages orchestration
- Addresses Lyra's most visible gap: can't run unattended or in parallel
- Phased rollout: each phase ships value
- Provider-agnostic at every layer
- Safety is architectural (worktree isolation, permission gates, collusion detection)

### Weaknesses
- Supervisor daemon is complex distributed systems engineering
- Worktree proliferation (100 sessions = 100 checkouts, disk-heavy)
- 6-9 month build for full implementation (team of 2)
- Tmux-based simple mode may be "good enough" for most users

### Critique Highlights
- **Senior SRE:** "The daemon is a single point of failure. Mitigation: sessions are independent processes, daemon restart recovers from disk. But the daemon is still a new service to monitor, debug, and maintain."
- **Senior PM:** "Phased rollout is the right strategy. Ship Phase 1 (router + embedding + skills + EnterWorktree) in 2 months — that alone makes Lyra a top-5 open-source harness. Phase 3 (daemon) is gated behind fleet demand data."
- **Adversarial Skeptic:** "Tmux + a status file handles 80% of fleet use cases for 5% of the effort. Ship that first, measure demand, THEN build the daemon only if data shows it's needed."

### Revisions After Red-Team (Round 3)
1. Worktree strategy configurable: full/sparse/overlay (addresses monorepo concern)
2. Workflow scripts sandboxed via RestrictedPython (addresses injection concern)
3. Cross-model verification where available (addresses same-model bias)
4. PDE dreaming gated behind bake-off (addresses overengineering concern)
5. Phased value delivery ensures Lyra wins even if Phase 3 never ships

### Verdict: CONVERGED WINNER — adopted as BREAKTHROUGH-ARCHITECTURE.md

---

## Candidate C — Self-Evolution-Centric Architecture

**Proposer:** Senior AI Researcher (Self-Improving Agents)
**Core bet:** The system that improves itself wins. Everything else is infrastructure to support evolution.

### Design

```
Evolution Engine (Foundation)
├── GEPA-Style Prompt Evolution (gradient-free, provider-agnostic)
├── DGM-Style Harness Rewriting (agents modify Lyra's own code)
├── MetaAgent-X Co-Evolution (Designer + Executor RL loop)
├── TF-TTCL Training-Free (Explore-Reflect-Steer for closed providers)
├── Skill Creator from Trajectories (execution → pattern → SKILL.md)
│
├── Evolution targets:
│   ├── Skills (prompts, examples, trigger patterns)
│   ├── Agent Configs (system prompts, tool bindings, routing rules)
│   ├── Memory Policies (admission thresholds, consolidation schedules)
│   └── Harness Code (tools, hooks, even the evolution engine itself)
│
├── Safety Gates:
    ├── Safety Validator (refusal rate, tool vulnerability, alignment checks)
    ├── Sandbox Testing (100 adversarial prompts before promotion)
    └── Human-in-the-Loop (harness changes require explicit approval)
```

### Strengths
- Most ambitious — aims for genuine AGI-direction self-improvement
- GEPA + TF-TTCL make evolution provider-agnostic
- DGM shows 20%→50% on SWE-bench (2.5× improvement)

### Weaknesses
- Depends on A and B existing (needs memory to store trajectories, fleet to run evolution in parallel)
- "Misevolve" shows concrete safety degradation (45% refusal rate drop)
- Harness rewriting is terrifying from safety perspective
- Longest time to value — evolution needs data (weeks/months of trajectories)

### Critique Highlights
- **Senior Safety Engineer:** "DGM-style harness rewriting is the scariest proposal in any candidate. 45% refusal rate drop from 'Misevolve' means evolved agents will do harmful things they previously refused. The safety validator MUST be a separate, hardened system."
- **Senior PM:** "This is 2027 material. Lyra needs to work as a basic agent before it can self-improve. Build the foundation first."
- **Adversarial Skeptic:** "Self-evolution sounds like AGI but in practice it's prompt optimization. The 330+ hand-written skills from claude-skills probably beat any auto-evolved skills for the first year. Prove the evolution loop works on ONE skill before building the whole infrastructure."

### Verdict: PARKED — gated behind Phase 1-3 infrastructure (memory, fleet, safety). Self-evolving skills start in Phase 4 with safety validator as mandatory gate. Harness rewriting is Phase 5 research only.

---

## Candidate D — Baseline / Minimal Change (STEELMANNED LOSER)

**Proposer:** Adversarial Skeptic
**Core bet:** The simplest improvements win. Don't build what you can borrow.

### Design

```
Incremental Improvements (no new architecture):
├── Embedding Search in Memory (sentence-transformers, 1 week)
├── 3-Tier Model Router (task-type → model mapping, 2 weeks)
├── Port 330+ claude-skills (progressive disclosure loader, 2 weeks)
├── EnterWorktree Tool (standalone git worktree isolation, 1 week)
├── Tmux + Status File Fleet (tmux sessions + JSON status, 1 week)
├── Extended Hooks (25+ lifecycle events, 1 week)
├── Core Tools (Bash/Read/Write/Edit/Glob/Grep, 2 weeks)
└── Deny-First Permissions (1 week)
```

### Strengths
- Ships in 2 months (vs 9 months for full Candidate B)
- Every component is battle-tested (tmux, sentence-transformers, claude-skills)
- No new infrastructure to maintain
- Gets Lyra to "useful" fastest

### Weaknesses
- Tmux can't: query "which sessions are stuck?", programmatically respawn, enforce per-session quotas, provide structured state
- No adversarial verification, no bias correction, no collusion detection
- No dreaming/consolidation, no self-evolution, no voice, no desktop
- Hits a ceiling: single-session, no unattended operation, no parallel safety beyond basic worktrees
- Doesn't implement the breakthrough — it's a better baseline, not a breakthrough architecture

### Why It Lost
The debate wasn't "minimal vs complex" — it was "when do we build what." Candidate D IS Phase 1 of Candidate B. All candidates agreed Phase 1 = Candidate D's improvements. The debate was about Phase 2+.

### What Was Preserved
- Tmux fleet mode ships as `lyra fleet --simple` — supported for ≤5 sessions
- All Phase 1 improvements from D are Phase 1 of B
- The "prove demand before building" principle from D is applied to: daemon (Phase 3), dreaming (Phase 3), voice full-duplex (Phase 3), self-evolution (Phase 4)
