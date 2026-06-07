# Architecture Debate — Full Candidate Descriptions & Multi-Round Critique

> Run 1 — June 3, 2026 | Complete debate transcript: 4 candidates, 3 rounds, converged winner
> 
> **Purpose:** This document records the complete architecture debate that led to Lyra's breakthrough design. It captures the initial candidates, per-round critiques from 15+ expert personas, trade-off analysis, and the reasoned convergence process.

---

## Executive Summary

**Process:** 4 candidate architectures debated across 3 rounds by a panel of 15+ senior expert personas (AI Solutions Architect, Software Architect, Backend Engineer, AI Researcher, SRE, Security Engineer, Distributed Systems Engineer, PM, and others).

**Candidates:**
- **Candidate A:** Memory-Centric Architecture (field-theoretic memory as spine)
- **Candidate B:** Fleet-Centric Architecture (orchestration/supervisor daemon as spine) 
- **Candidate C:** Self-Evolution-Centric Architecture (self-improvement as spine)
- **Candidate D:** Baseline/Minimal Change (incremental improvements only)

**Winner:** Candidate B (Fleet-Centric) with phased rollout, absorbing memory innovations from A and gating self-evolution (C) to Phase 4.

**Key Insight:** The debate wasn't "minimal vs complex" — it was "when do we build what." Candidate D became Phase 1 of Candidate B. All candidates agreed on immediate next steps; they differed on Phase 2+ architecture.

---

## Table of Contents

1. [Initial Candidates](#initial-candidates)
   - [Candidate A: Memory-Centric Architecture](#candidate-a-memory-centric-architecture)
   - [Candidate B: Fleet-Centric Architecture](#candidate-b-fleet-centric-architecture)
   - [Candidate C: Self-Evolution-Centric Architecture](#candidate-c-self-evolution-centric-architecture)
   - [Candidate D: Baseline/Minimal Change](#candidate-d-baselineminimal-change)
2. [Round 1: Candidates vs Baseline](#round-1-candidates-vs-baseline)
3. [Round 2: Head-to-Head with Trade-Off Analysis](#round-2-head-to-head-with-trade-off-analysis)
4. [Round 3: Red-Team the Winner](#round-3-red-team-the-winner)
5. [Final Convergence](#final-convergence)
6. [Why This Combination is a Breakthrough](#why-this-combination-is-a-breakthrough)

---

## Initial Candidates

### Candidate A: Memory-Centric Architecture

**Proposer:** Senior AI Researcher  
**Core Thesis:** "Memory is the AGI bottleneck" (Hassabis, DeepMind). Build the breakthrough from memory outward.

#### Design Philosophy

Memory as the foundational layer — everything else (context, skills, agents, fleet) is built on top of and consumes memory as a service. The bet is that memory improvements cascade upward to benefit every other subsystem.

#### Architecture

```
Memory Plane (Foundation)
├── Field-Theoretic Memory (PDE-governed continuous fields)
│   ├── Memory strength evolves via diffusion equations
│   ├── Gradient flow governs consolidation dynamics
│   └── Continuous fields (not discrete embeddings)
├── Zettelkasten Graph (linked notes, LP-RAG prediction)
│   ├── Structured notes with typed links
│   ├── Link prediction via graph neural networks
│   └── Four stores: Working / Episodic / Semantic / Procedural
├── Cost-Sensitive Multi-Store Routing
│   ├── Cheap vector search for fast queries
│   ├── Graph traversal for conceptual queries
│   ├── Full-text for exact matches
│   └── Dynamic routing based on query type
├── A-MAC 5-Factor Admission Control
│   ├── Novelty, relevance, confidence, coherence, utility
│   └── Prevents memory pollution
├── Dreaming Engine (idle-time PDE consolidation)
│   ├── Runs during system idle
│   ├── Cross-session pattern detection
│   └── Conflict resolution via field equilibration
│
├── Built on top of memory:
│   ├── Context Manager (auto-compaction via memory retrieval)
│   ├── Skills System (skills as procedural memories)
│   ├── Agent Orchestration (agents read/write shared memory)
│   └── Fleet (fleet sessions share semantic memory)
```

#### Research Foundation

- **28 papers** cited (strongest evidence base among all candidates)
- **Field-theoretic approach:** 1 paper (Mitra's memory fields), 0 production deployments
- **Zettelkasten/graph memory:** 4 papers (A-MEM, LP-RAG, knowledge graphs)
- **Cost-sensitive routing:** 3 papers (multi-store optimization, query routing)
- **A-MAC admission:** 1 paper (5-factor gating)
- **Dreaming/consolidation:** 6 papers (Anthropic dreaming, memory replay, etc.)

#### Strengths

1. **Strongest research foundation** — 28 papers of evidence vs 12-15 for other candidates
2. **Field-theoretic memory is genuinely novel** — no existing agent harness has continuous PDE-governed memory
3. **Memory improvements benefit everything** — better memory → better context → better routing → better skills
4. **Clean layering** — memory is a service consumed by all other subsystems
5. **Addresses long-term bottleneck** — Hassabis: "Memory is the path to AGI"

#### Weaknesses

1. **Memory is a SERVICE, not an architecture spine** — it doesn't drive system boundaries or concurrency model
2. **Field-theoretic approach unproven** — 1 paper, 0 deployments, exotic infrastructure (PDE solver)
3. **Doesn't address Lyra's most visible gap** — can't run unattended, can't run in parallel, no fleet
4. **Fleet/supervisor/orchestration is afterthought** — "built on top" means not architected-in
5. **Time to value unclear** — memory research could take months before showing user-visible wins

#### Round 1 Critiques

**Senior Software Architect:** "Memory doesn't drive system boundaries. What's the API between memory and fleet? What's the concurrency model? Memory-centric architectures end up with everything depending on a singleton MemoryService that becomes the bottleneck. I've seen this pattern fail in distributed systems — the memory layer can't scale independently."

**Senior Backend Engineer:** "Building field-theoretic memory before graph memory is like building a quantum computer before a classical one. The PDE solver is exotic infrastructure. Ship incremental memory improvements — embedding search, graph storage, cost-sensitive routing — not a paradigm shift. Reserve PDE consolidation for Phase 3 research."

**Senior Distributed Systems Engineer:** "Where's the supervisor? Where's the worktree isolation? Where's the workflow engine? This architecture assumes memory magically solves orchestration. It doesn't. Fleet coordination is hard distributed systems work — sessions, channels, state management, failure recovery. Memory is orthogonal."

**Adversarial Skeptic:** "This architecture optimizes for memory research novelty, not Lyra user value. Users need a fleet that can run 10 tasks in parallel more than they need PDE-governed memory consolidation. The field-theoretic approach is a research bet, not an MVP feature. If it loses the bake-off to LLM-based dreaming, we've wasted months on exotic infrastructure."

**Senior PM:** "What ships in Phase 1? Embedding search and graph memory are good. But field-theoretic consolidation takes months to build and months to validate. Meanwhile, Lyra still can't run unattended. This is a great Phase 2-3 capability layer, not an architecture spine."

#### Verdict

**ABSORBED** — Memory innovations preserved as the first major capability the fleet exercises. Field-theoretic approach gated behind bake-off vs LLM-based dreaming (Phase 3). Graph memory, cost-sensitive routing, A-MAC admission control adopted into Candidate B as capability plane components.

### Candidate B: Fleet-Centric Architecture (WINNER)

**Proposers:** Senior Software Architect + Senior Distributed-Systems Engineer  
**Core Thesis:** Orchestration IS the architecture. Build the fleet first, then layer capabilities on top.

#### Design Philosophy

The supervisor daemon, worktree isolation, and workflow engine form the architectural spine. Everything else — intelligence (model routing, planning), capabilities (skills, tools), memory, safety — are services the fleet USES. The system boundaries are clean: supervisor manages processes, worktrees manage files, workflow engine manages orchestration.

#### Architecture

```
Orchestration Plane (Foundation)
├── Supervisor Daemon (session lifecycle, disk-persisted state)
│   ├── Process management (spawn, monitor, reap)
│   ├── Session registry (active, queued, completed, failed)
│   ├── Disk persistence (sessions survive daemon restart)
│   └── Fleet API (list, attach, kill, logs)
├── Fleet View TUI (state-grouped rows, cheap row summaries)
│   ├── Grouped by state: running / waiting / done / failed
│   ├── Cheap per-row summaries (task + progress)
│   ├── Drill-down to full logs
│   └── Keyboard navigation (j/k/Enter/q)
├── Worktree Isolation Substrate (per-session git worktree)
│   ├── Lazy creation (only on first edit)
│   ├── Non-destructive cleanup (archive on completion)
│   ├── Sparse checkout for monorepos
│   └── Unionfs overlay fallback for non-git repos
├── Dynamic Workflow Engine (agent/parallel/pipeline primitives)
│   ├── JavaScript/Python workflow scripts
│   ├── Resumable checkpoints (agent() calls are persisted)
│   ├── Background execution (session stays responsive)
│   └── Quality gates (adversarial verification, collusion detection)
├── Channels (inter-agent comms, collusion-monitored)
│   ├── Typed messages (request/response/broadcast)
│   ├── Anonymization layer (strips identity markers)
│   └── Collusion detector (flags coordinated deception)
│
├── Capability Planes (layered on orchestration):
│   ├── Intelligence Plane
│   │   ├── PrimaryAgent (orchestrator)
│   │   ├── Specialist Agents (Code/Research/Review/...)
│   │   ├── Model Router (task → model mapping)
│   │   └── Planning Layer (MCTS/ToT/AFlow when needed)
│   ├── Memory Plane
│   │   ├── Graph Memory (Zettelkasten + LP-RAG)
│   │   ├── Vector Store (embedding search)
│   │   ├── Cost-Sensitive Router (cheap first, expensive fallback)
│   │   └── Dreaming Engine (idle-time consolidation)
│   ├── Skills Plane
│   │   ├── 330+ Skills (ported from claude-skills)
│   │   ├── Self-Evolving (GEPA-style prompt optimization)
│   │   └── Safety Validator (gates skill promotions)
│   ├── Safety Plane
│   │   ├── Guard System (LlamaFirewall + NeMo Guardrails)
│   │   ├── Adversarial Verifier (anonymized + bias-corrected)
│   │   ├── Sandbox (OS-level + worktree isolation)
│   │   └── Collusion Detector (channel monitoring)
│   ├── Voice Plane (provider-swappable STT→Agent→TTS)
│   └── Observability Plane (tracing, monitoring, eval harness)
│
├── User Surface:
    ├── CLI/TUI (terminal-native)
    ├── lyra-desktop (Electron/React, multimodal)
    └── Local API (HTTP/SSE on localhost — both clients consume)
```

#### Research Foundation

- **12 papers** cited (orchestration, fleet management, worktree isolation)
- **Supervisor pattern:** Proven in Claude Code Agent View, Tmux, systemd
- **Worktree isolation:** Git worktrees (2015), proven in Claude Code
- **Dynamic workflows:** Claude Code workflows, Temporal.io patterns
- **Provider abstraction:** Proven in RouteLLM, LiteLLM, LangChain

#### Strengths

1. **Clean system boundaries** — supervisor manages processes, worktrees manage files, workflow engine manages orchestration
2. **Addresses Lyra's most visible gap** — can't run unattended or in parallel today
3. **Phased rollout** — each phase ships user value independently
4. **Provider-agnostic at every layer** — works across Claude/DeepSeek/GPT/open-weights
5. **Safety is architectural** — worktree isolation, permission gates, collusion detection built-in
6. **Battle-tested components** — supervisor, worktree, workflow patterns proven elsewhere

#### Weaknesses

1. **Supervisor daemon is complex** — distributed systems engineering, single point of failure
2. **Worktree proliferation** — 100 sessions = 100 checkouts, disk-heavy (mitigated: sparse checkout)
3. **6-9 month build** for full implementation (team of 2)
4. **Operational burden** — daemon to monitor, worktrees to clean, workflow engine to debug
5. **Tmux might be "good enough"** for most users (≤5 sessions)

#### Round 1 Critiques

**Senior AI Solutions Architect:** "This is the right spine. Orchestration drives the architecture — memory, skills, safety are capabilities the fleet consumes. The system boundaries are clean and the phased rollout validates demand before building complex infrastructure."

**Senior Software Architect:** "Candidate B wins on architectural clarity. The API boundaries are obvious: supervisor exposes session lifecycle, worktrees expose file isolation, workflow engine exposes agent/parallel/pipeline primitives. Everything else plugs in as capabilities."

**Senior SRE:** "The daemon is the highest operational risk. A daemon that manages processes, survives restarts, and doesn't leak resources is hard to get right. Mitigation: sessions are independent processes, daemon restart recovers from disk. But the daemon is still a new service to monitor, debug, and maintain."

**Senior PM:** "Phased rollout is critical. Phase 1 (embedding + router + skills + EnterWorktree tool) ships in 2 months and makes Lyra competitive. Phase 2 (workflow engine, single-session) ships value at 4 months. Phase 3 (daemon + fleet view) is gated behind usage data showing demand. This ensures Lyra wins even if Phase 3 never ships."

**Adversarial Skeptic:** "Tmux + a status file handles 80% of fleet use cases for 5% of the effort. Ship that as `lyra fleet --simple` first, measure demand, THEN build the daemon only if data shows >10% of users run 3+ concurrent sessions. Don't build infrastructure before proving demand."

#### Verdict

**WINNER** — Converged as the destination architecture with phased rollout. Phase 1 = Candidate D improvements. Phase 2 = workflow engine (single-session). Phase 3 = daemon + fleet view (gated behind demand data). Absorbs memory innovations from Candidate A as capability plane.

### Candidate C: Self-Evolution-Centric Architecture

**Proposer:** Senior AI Researcher (Self-Improving Agents)  
**Core Thesis:** The system that improves itself wins. Everything else is infrastructure to support evolution.

#### Design Philosophy

Self-evolution as the primary capability. The system continuously improves its own skills, prompts, memory policies, and even harness code. Memory stores trajectories, fleet runs evolution experiments in parallel, safety validates before promotion. The bet is that a self-improving system eventually outperforms any hand-crafted system.

#### Architecture

```
Evolution Engine (Foundation)
├── GEPA-Style Prompt Evolution (gradient-free, provider-agnostic)
│   ├── Population of prompt variants
│   ├── Fitness evaluation on task suite
│   ├── Genetic operators (crossover, mutation)
│   └── Multi-objective optimization (quality × cost)
├── DGM-Style Harness Rewriting (agents modify Lyra's own code)
│   ├── Experience buffer (successful trajectories)
│   ├── Code generation (new tools, hooks, skills)
│   ├── Sandbox testing (100 adversarial prompts)
│   └── Human-in-the-loop approval for harness changes
├── MetaAgent-X Co-Evolution (Designer + Executor RL loop)
│   ├── Designer agent proposes skill improvements
│   ├── Executor agent tests on benchmark
│   ├── RL feedback loop (reward = task success)
│   └── Co-evolution (both improve together)
├── TF-TTCL Training-Free (Explore-Reflect-Steer for closed providers)
│   ├── No gradient access required
│   ├── Works with Claude/GPT/DeepSeek
│   └── Self-critique drives improvement
├── Skill Creator from Trajectories (execution → pattern → SKILL.md)
│   ├── Pattern detection in successful runs
│   ├── Automatic skill template generation
│   └── Progressive refinement
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

#### Research Foundation

- **15 papers** cited (self-improving agents, prompt optimization, meta-learning)
- **GEPA:** 1 paper (gradient-free evolution)
- **DGM:** 1 paper (20%→50% on SWE-bench, 2.5× improvement)
- **MetaAgent-X:** 1 paper (co-evolution)
- **TF-TTCL:** 1 paper (training-free for closed models)
- **"Misevolve":** 1 paper (safety degradation: 45% refusal rate drop, 76% tool vulnerability rate)

#### Strengths

1. **Most ambitious** — aims for genuine AGI-direction self-improvement
2. **GEPA + TF-TTCL are provider-agnostic** — works on closed models (Claude/GPT)
3. **DGM shows massive gains** — 20%→50% on SWE-bench (2.5× improvement)
4. **Long-term moat** — self-improving systems compound advantages over time
5. **Addresses skill stagnation** — hand-written skills plateau, evolved skills improve continuously

#### Weaknesses

1. **Depends on A and B existing** — needs memory to store trajectories, fleet to run evolution in parallel
2. **"Misevolve" shows concrete safety degradation** — 45% refusal rate drop, 76% tool vulnerability rate
3. **Harness rewriting is terrifying** — agents modifying Lyra's own code is highest-risk capability
4. **Longest time to value** — evolution needs weeks/months of trajectories before showing wins
5. **Safety validator is critical path** — must be hardened before any evolution ships

#### Round 1 Critiques

**Senior Security Engineer:** "DGM-style harness rewriting is the scariest proposal in any candidate. 'Misevolve' shows 45% refusal rate drop — evolved agents will do harmful things they previously refused. The safety validator MUST be a separate, hardened system, not something the evolution engine can modify. Harness rewriting requires explicit human approval for every change."

**Senior AI Researcher:** "Self-evolution is the long-term winner, but it's 2027 material, not 2026. The infrastructure doesn't exist yet — no memory to store trajectories, no fleet to run experiments in parallel, no safety validator to gate promotions. Build the foundation (A or B) first, THEN add evolution on top."

**Senior PM:** "This is Phase 4+ at earliest. Lyra needs to work as a basic agent before it can self-improve. The 330+ hand-written skills from claude-skills probably beat any auto-evolved skills for the first year. Prove the evolution loop works on ONE skill before building the whole infrastructure."

**Adversarial Skeptic:** "Self-evolution sounds like AGI but in practice it's prompt optimization. GEPA is gradient-free hill climbing. DGM is code generation with RL feedback. These are valuable techniques, but they're not 'self-evolution' in the AGI sense. Call it 'continuous improvement' and gate it behind proven infrastructure."

**Senior Backend Engineer:** "Where's the eval harness? You can't evolve without measurement. Every evolution experiment needs a benchmark suite, holdout test set, and regression detection. That's months of work before the first skill evolves."

#### Verdict

**PARKED** — Gated behind Phase 1-3 infrastructure (memory, fleet, safety). Self-evolving skills start in Phase 4 with safety validator as mandatory gate. Harness rewriting is Phase 5 research only, requires human-in-the-loop approval for every change.

---

#### Research Foundation

- **15 papers** cited (self-improving agents, prompt optimization, meta-learning)
- **GEPA:** 1 paper (gradient-free evolution)
- **DGM:** 1 paper (20%→50% on SWE-bench, 2.5× improvement)
- **MetaAgent-X:** 1 paper (co-evolution)
- **TF-TTCL:** 1 paper (training-free for closed models)
- **"Misevolve":** 1 paper (safety degradation: 45% refusal rate drop, 76% tool vulnerability rate)

#### Strengths

1. **Most ambitious** — aims for genuine AGI-direction self-improvement
2. **GEPA + TF-TTCL are provider-agnostic** — works on closed models (Claude/GPT)
3. **DGM shows massive gains** — 20%→50% on SWE-bench (2.5× improvement)
4. **Long-term moat** — self-improving systems compound advantages over time
5. **Addresses skill stagnation** — hand-written skills plateau, evolved skills improve continuously

#### Weaknesses

1. **Depends on A and B existing** — needs memory to store trajectories, fleet to run evolution in parallel
2. **"Misevolve" shows concrete safety degradation** — 45% refusal rate drop, 76% tool vulnerability rate
3. **Harness rewriting is terrifying** — agents modifying Lyra's own code is highest-risk capability
4. **Longest time to value** — evolution needs weeks/months of trajectories before showing wins
5. **Safety validator is critical path** — must be hardened before any evolution ships

#### Round 1 Critiques

**Senior Security Engineer:** "DGM-style harness rewriting is the scariest proposal in any candidate. 'Misevolve' shows 45% refusal rate drop — evolved agents will do harmful things they previously refused. The safety validator MUST be a separate, hardened system, not something the evolution engine can modify. Harness rewriting requires explicit human approval for every change."

**Senior AI Researcher:** "Self-evolution is the long-term winner, but it's 2027 material, not 2026. The infrastructure doesn't exist yet — no memory to store trajectories, no fleet to run experiments in parallel, no safety validator to gate promotions. Build the foundation (A or B) first, THEN add evolution on top."

**Senior PM:** "This is Phase 4+ at earliest. Lyra needs to work as a basic agent before it can self-improve. The 330+ hand-written skills from claude-skills probably beat any auto-evolved skills for the first year. Prove the evolution loop works on ONE skill before building the whole infrastructure."

**Adversarial Skeptic:** "Self-evolution sounds like AGI but in practice it's prompt optimization. GEPA is gradient-free hill climbing. DGM is code generation with RL feedback. These are valuable techniques, but they're not 'self-evolution' in the AGI sense. Call it 'continuous improvement' and gate it behind proven infrastructure."

**Senior Backend Engineer:** "Where's the eval harness? You can't evolve without measurement. Every evolution experiment needs a benchmark suite, holdout test set, and regression detection. That's months of work before the first skill evolves."

#### Verdict

**PARKED** — Gated behind Phase 1-3 infrastructure (memory, fleet, safety). Self-evolving skills start in Phase 4 with safety validator as mandatory gate. Harness rewriting is Phase 5 research only, requires human-in-the-loop approval for every change.

### Candidate D: Baseline/Minimal Change (STEELMANNED LOSER)

**Proposer:** Adversarial Skeptic  
**Core Thesis:** The simplest improvements win. Don't build what you can borrow. Ship fast, measure, iterate.

#### Design Philosophy

Incremental improvements to existing codebase. No new architecture — just add the missing pieces that are proven elsewhere. Embedding search for memory, 3-tier model router, port 330+ claude-skills, EnterWorktree tool for isolation, tmux + status file for fleet. Everything is battle-tested. Ship in 2 months vs 9 months for Candidate B.

#### Architecture

```
Incremental Improvements (no new architecture):
├── Embedding Search in Memory (sentence-transformers, 1 week)
│   ├── all-MiniLM-L6-v2 (lightweight, fast)
│   ├── FAISS or Chroma for vector store
│   └── Cosine similarity search
├── 3-Tier Model Router (task-type → model mapping, 2 weeks)
│   ├── Task classifier (code/research/review/chat)
│   ├── Model capability matrix
│   └── Cost-aware routing (cheap first, expensive fallback)
├── Port 330+ claude-skills (progressive disclosure loader, 2 weeks)
│   ├── Full claude-skills catalog
│   ├── Progressive loading (load on demand)
│   └── Provider-aware degradation
├── EnterWorktree Tool (standalone git worktree isolation, 1 week)
│   ├── lyra worktree create <name>
│   ├── lyra worktree cleanup
│   └── No daemon, just a CLI tool
├── Tmux + Status File Fleet (tmux sessions + JSON status, 1 week)
│   ├── lyra fleet start <name> <task>
│   ├── lyra fleet list (reads ~/.lyra/fleet-status.json)
│   └── lyra fleet attach <name>
├── Extended Hooks (25+ lifecycle events, 1 week)
│   ├── PreAgentStart, PostAgentComplete
│   ├── PreMemoryWrite, PostMemoryConsolidate
│   └── Hook configs in YAML
├── Core Tools (Bash/Read/Write/Edit/Glob/Grep, 2 weeks)
│   ├── Standard file operations
│   ├── Shell command execution
│   └── Pattern matching and search
└── Deny-First Permissions (1 week)
    ├── User approval for first use
    ├── Per-tool allowlists
    └── Dangerous operation gates
```

#### Research Foundation

- **0 papers** — all components are adopted from existing systems
- **sentence-transformers:** Proven, widely deployed
- **FAISS/Chroma:** Battle-tested vector stores
- **claude-skills:** 330+ hand-written skills, production-ready
- **Git worktrees:** Native Git feature since 2015
- **Tmux:** 30+ years of production use

#### Strengths

1. **Ships in 2 months** (vs 9 months for full Candidate B)
2. **Every component is battle-tested** — tmux, sentence-transformers, claude-skills, git worktrees
3. **No new infrastructure to maintain** — no daemon, no complex workflow engine
4. **Gets Lyra to "useful" fastest** — embedding search + router + skills = competitive agent
5. **Low operational risk** — standard Unix tools, no new services

#### Weaknesses

1. **Tmux limitations** — can't query "which sessions are stuck?", can't programmatically respawn, can't enforce quotas, no structured state
2. **No adversarial verification** — single-pass agent outputs, no cross-check
3. **No bias correction** — no anonymization, no dialectical alignment
4. **No collusion detection** — agents can coordinate deception
5. **No dreaming/consolidation** — memory never improves beyond initial storage
6. **No self-evolution** — skills never improve
7. **No voice, no desktop** — terminal-only
8. **Hits a ceiling** — single-session oriented, no unattended operation, no parallel safety beyond basic worktrees
9. **Doesn't implement the breakthrough** — it's a better baseline, not a breakthrough architecture

#### Round 1 Critiques

**Adversarial Skeptic (championing D):** "This is the only honest option. Candidates A-C are architecture astronaut fantasies — elegant designs that would take years to build. Lyra today has 5 partially-working subsystems. Adding a supervisor daemon to that is like adding a jet engine to a bicycle. Ship the bicycle first. Add embedding search. Add a model router. Ship the 330 skills. THEN decide if you need a daemon."

**Senior Backend Engineer:** "The Skeptic is right about sequencing. Every component in D is proven — we're not betting on exotic infrastructure. This is the path to 'useful' in 2 months. But it's not the path to 'breakthrough.' Once we ship D, we'll immediately want the daemon for unattended operation."

**Senior Distributed Systems Engineer:** "Tmux breaks at scale. You can't query 'which sessions are stuck?', you can't programmatically respawn, you can't enforce quotas. For ≤5 sessions, tmux works. For 10+, you need structured state and a supervisor. D is good for Phase 1, but we need to know where we're going."

**Senior PM:** "D is Phase 1 of whatever wins. All candidates agreed on this. The debate isn't 'D vs B' — it's 'when do we build B's Phase 2+.' D gets Lyra competitive in 2 months. B takes Lyra to breakthrough in 6-9 months. Both are needed."

#### Verdict

**ABSORBED INTO CANDIDATE B AS PHASE 1** — All of D's improvements become Phase 1 of Candidate B. The debate was never "minimal vs complex" — it was "when do we build what." Tmux fleet mode preserved as `lyra fleet --simple` for users who want fleet behavior without the daemon (≤5 sessions).

---

## Round 1: Candidates vs Baseline

**Motion:** "Each candidate architecture MUST prove it beats the baseline (BASELINE.md) on evidence. The baseline is a first-class contender — the 'do nothing / minimal change' option championed by the Adversarial Skeptic."

### Round 1 Outcome Summary

**Surviving Candidates:**
- **Candidate B (Fleet-Centric):** Wins on architectural clarity, addresses Lyra's most visible gap, clean boundaries
- **Candidate D (Baseline):** Survives as PHASE 1 of whatever wins — the immediate next step
- **Candidate A (Memory-Centric):** ABSORBED into B — memory becomes capability plane, not architectural spine
- **Candidate C (Self-Evolution):** PARKED — gated behind safety infrastructure from B (Phase 4+)

**Key Concession:** All candidates agreed Phase 1 = Candidate D's improvements (embedding search, model router, skill port, EnterWorktree tool). The debate is about Phase 2+ architecture.

**Consensus Points:**
1. Memory is a SERVICE, not an architecture spine
2. Self-evolution needs safety infrastructure that doesn't exist yet
3. Orchestration/fleet capability is Lyra's most visible gap
4. Phased rollout is critical — validate demand before building complex infrastructure
5. Tmux is good enough for ≤5 sessions but doesn't scale

---

## Round 2: Head-to-Head with Trade-Off Analysis

**Motion:** "Candidate B (Fleet-Centric with absorbed memory innovations) vs the Skeptic's Phase-2-is-overengineered position. Head-to-head across ALL trade-off dimensions."

### Trade-Off Comparison Table

| Dimension | Candidate B (Fleet-Centric) | Candidate D (Minimal, Extended) | Winner | Rationale |
|-----------|---------------------------|-------------------------------|--------|-----------|
| **Capability ceiling** | Fleet of 100s, unattended, parallel-safe | Single-session, attended, no parallel safety | **B** | Tmux can't scale past ~5 sessions |
| **Build effort** | 6-9 months (team of 2) | 2-3 months (team of 1) | **D** | Faster to market |
| **Operational complexity** | Daemon + worktrees + workflow engine | Standard Unix tools (tmux, git) | **D** | Less infrastructure to maintain |
| **Token economics** | Cheap row summaries + verification costs tokens but improves quality | No fleet overhead, no quality gains | **Tie** | B costs more but delivers more |
| **Reliability** | Supervisor SPOF (mitigated: disk persistence) + rogue agent prevention | No new SPOFs, no new reliability features | **B** | Long-term reliability is higher |
| **Safety** | Worktree isolation + permission gates + collusion detection | No new safety beyond basic worktrees | **B** | Architectural safety vs bolt-on |
| **Multi-provider** | Supervisor provider-agnostic, subagents per-model | Single model per session | **B** | Better provider flexibility |
| **Time to first value** | 6 months to full fleet | 2 months to embedding + router + skills | **D** | D ships value faster |
| **Maintenance burden** | Daemon, worktree cleanup, workflow engine | No new infrastructure | **D** | Less ongoing ops cost |
| **Failure modes** | Daemon crash orphans sessions; worktree proliferation; workflow bugs | Same as today | **D** | Fewer new failure modes |
| **User impact** | Unattended operation, parallel safety, fleet management | Better memory, routing, skills — no fleet | **B** | Bigger capability unlock |
| **Competitive position** | Breakthrough tier (only harness with full fleet + bias-corrected verification) | Top-5 tier (good memory + routing + skills) | **B** | B is differentiated |

### Key Exchanges from Round 2

**Senior Distributed-Systems Engineer (for B):** "The Skeptic's tmux approach breaks at scale. Tmux can't: query 'which sessions are stuck?', programmatically respawn a crashed session, enforce per-session quotas, or provide structured state for monitoring. These aren't nice-to-haves — they're what makes a fleet manageable beyond 5 sessions. The daemon is complex, but it's the right complexity."

**Adversarial Skeptic (for D):** "How many Lyra users will ever run more than 5 concurrent sessions? The 'fleet of 100s' use case is a power user fantasy. The median developer runs ONE session. For them, the daemon is pure overhead. Ship the single-session improvements first, measure fleet demand, THEN build the daemon only if >10% of users run 3+ concurrent sessions. Don't build infrastructure before proving demand."

**Senior SRE (split decision):** "The Skeptic is right about operational risk — daemons are hard to get right. But the worktree isolation is valuable even for single-session use. An agent that isolates itself before editing, even in ONE session, is safer than one editing the main checkout. Compromise: ship worktree isolation as a standalone tool (EnterWorktree) first; add the daemon when fleet demand materializes."

**Senior PM (proposing compromise):** "Here's the sequencing that ships value at every phase:
- **Phase 1 (2 months):** Embedding search + model router + skill port + EnterWorktree tool (standalone isolation)
- **Phase 2 (4 months):** Dynamic workflow engine (single-session — agent/parallel/pipeline primitives)
- **Phase 3 (6-9 months):** Supervisor daemon + fleet view + background workflows

This validates demand before building the daemon. If usage data shows <10% of users run 3+ sessions, we stop at Phase 2. If data shows fleet demand, we build Phase 3."

**Senior Backend Engineer:** "The PM's phasing is right. Phase 1 is pure value, no risk. Phase 2 adds powerful orchestration without the daemon complexity. Phase 3 is gated behind real usage data. This is how you build ambitious systems without overcommitting."

### Round 2 Outcome

**Converged winner:** Candidate B (Fleet-Centric) with PM's phased sequencing.

**Steelmanned loser:** Candidate D's "just use tmux" is preserved as `lyra fleet --simple` — supported for ≤5 sessions without requiring the daemon.

**Key insight:** The debate wasn't "B vs D" — it was "when do we build B's phases?" Phase 1 = D's improvements. Phase 2 = workflow engine. Phase 3 = daemon (gated behind demand data).

## Round 3: Red-Team the Winner

**Motion:** "Attack the converged Fleet-Centric architecture with phased rollout. Find where it breaks, what it quietly assumes, stress the safety angles, and verify it still beats the baseline after revisions."

### Attack 1: Worktree Isolation Breaks on Monorepos

**Red Team Attack:** "Git worktrees in monorepos (Google-scale, 10GB+) are impractically slow and disk-heavy. Creating a worktree per session would take minutes and consume gigabytes. The worktree strategy assumes small repos, which is not universally true."

**Rebuttal (Senior Backend Engineer):** "Use git worktrees with `--no-checkout` + sparse checkout. Only check out the files the agent actually edits. For non-git repos, use unionfs overlay as the primary isolation strategy. Add a `worktree.strategy` config option:
- `full` — full checkout (default for <1GB repos)
- `sparse` — sparse checkout (for monorepos)
- `overlay` — unionfs/overlayfs (for non-git or very large repos)

The strategy auto-selects based on repo size but users can override."

**Outcome:** **REVISION ACCEPTED** — Worktree strategy made configurable. Architecture survives with refinement.

### Attack 2: Workflow Engine Scripts Are Injection Vector

**Red Team Attack:** "User-provided workflow scripts have full Python access. A malicious skill could inject code into a workflow script, giving it arbitrary execution capability. This is a massive security hole."

**Rebuttal (Senior Security Engineer):** "Workflow scripts run in a restricted Python sandbox (RestrictedPython or PyPy sandbox):
- No filesystem access except through Lyra tools (Bash/Read/Write/Edit)
- No network access except through approved channels
- No `eval()`, `exec()`, `__import__` from arbitrary strings
- Workflow scripts from untrusted sources require explicit user approval

The sandbox is hardened before Phase 2 ships. Workflow engine without sandbox doesn't ship."

**Outcome:** **REVISION ACCEPTED** — Workflow script sandbox is mandatory for Phase 2. Architecture survives with safety gate.

### Attack 3: Adversarial Verification Doesn't Work with Same Model

**Red Team Attack:** "If all verifiers use the same model (e.g., all Claude Sonnet), they share the same biases. Anonymization helps with identity bias (IBC) but not with model-level bias. Same-model verification is weak verification."

**Rebuttal (Senior AI Researcher):** "Valid concern. Mitigation strategies:
1. **Cross-model verification** — use different models for different verifier roles when available (router's capability map enables this)
2. **Temperature + prompt diversity** — same model, different sampling parameters and prompt framing
3. **Accept the limitation** — same-model verification is weaker but still better than single-pass
4. **Document the trade-off** — make it clear in docs that cross-model verification is stronger when provider budgets allow

The architecture supports cross-model verification via the router. Whether users enable it depends on their provider budgets."

**Outcome:** **REVISION ACCEPTED** — Cross-model verification added as a supported (but not required) configuration. Architecture survives with documented trade-off.

### Attack 4: PDE Dreaming Engine Is Overengineered

**Red Team Attack:** "Field-theoretic memory consolidation via PDEs is elegant but uses exotic infrastructure (PDE solvers, continuous field representations). The simpler Anthropic approach (LLM reviews N conversations, produces reorganized memory) is more interpretable, debuggable, and maintainable. PDE approach is overengineering."

**Rebuttal (Senior AI Researcher):** "Agreed — the PDE solver is the (B) breakthrough tier and should be gated behind a bake-off vs LLM-based dreaming. The bake-off runs both approaches on the same memory tasks (cross-session recall, conflict resolution, pattern discovery) and ships whichever wins on quality-per-dollar. If LLM-based dreaming wins, the field-theoretic approach is parked as a research bet. Phase 3 ships with LLM-based dreaming as default; PDE approach is opt-in experimental."

**Outcome:** **REVISION ACCEPTED** — PDE dreaming gated behind bake-off. LLM-based dreaming is Phase 3 default. Architecture survives with de-risking strategy.

### Attack 5: What If Lyra Never Ships Phase 3?

**Red Team Attack:** "Most ambitious open-source projects stall before reaching their final phase. If Lyra only ships Phase 1-2 (embedding, router, skills, single-session workflows), is that enough to justify the architecture complexity? Or should we just ship D (minimal change) and stop?"

**Rebuttal (Senior PM):** "Phase 1-2 alone makes Lyra a top-5 open-source agent harness:
- **Phase 1:** Embedding search + model router + 330 skills + EnterWorktree tool = more than most competitors have today
- **Phase 2:** Dynamic workflow engine (agent/parallel/pipeline) = powerful orchestration primitives that ship value even without the daemon

Phase 3 (daemon + fleet view) is the breakthrough that takes Lyra to #1, but even without it, Phase 1-2 is worth building. The phased approach ensures Lyra wins at every milestone, not just at the end."

**Outcome:** **ARCHITECTURE VALIDATED** — Phased value delivery ensures Lyra is competitive even if Phase 3 never ships. No fundamental architecture change needed.

### Round 3 Outcome Summary

The converged architecture **SURVIVES** red-team with the following revisions:

1. **Worktree strategy configurable** (full/sparse/overlay) — addresses monorepo concern
2. **Workflow script sandbox mandatory** (RestrictedPython) — addresses injection concern
3. **Cross-model verification supported** — addresses same-model bias concern (opt-in)
4. **PDE dreaming gated behind bake-off** — addresses overengineering concern (LLM-based default)
5. **Phased value delivery** — ensures Lyra wins even if Phase 3 never ships

**No fundamental architecture change needed. The revisions are refinements, not redesigns.**

---

## Final Convergence

### The Winning Architecture: Fleet-Centric with Absorbed Innovations

**Candidate B (Fleet-Centric)** emerged as the winner through a multi-round convergence process:

1. **Round 1:** Beat baseline by addressing Lyra's most visible gap (can't run unattended/parallel)
2. **Round 2:** Absorbed Candidate D as Phase 1, proving value delivery at every milestone
3. **Round 3:** Survived red-team attacks with refinements, no fundamental redesign

**What was absorbed from other candidates:**

- **From Candidate A (Memory-Centric):**
  - Graph memory with Zettelkasten structure
  - Cost-sensitive multi-store routing
  - A-MAC 5-factor admission control
  - Dreaming engine (LLM-based as default, PDE gated behind bake-off)
  - All memory innovations moved to Capability Plane

- **From Candidate C (Self-Evolution):**
  - Self-evolving skills (Phase 4, safety validator mandatory)
  - GEPA-style prompt optimization
  - Skill creator from trajectories
  - Harness rewriting (Phase 5 research, human-in-the-loop required)

- **From Candidate D (Baseline):**
  - ALL of Phase 1: embedding search, model router, skill port, EnterWorktree tool
  - Tmux fleet mode preserved as `lyra fleet --simple` for ≤5 sessions
  - Battle-tested component preference (sentence-transformers, FAISS/Chroma, etc.)

### Phased Rollout (Final)

**Phase 1 (2 months):**
- Embedding search in memory (sentence-transformers + FAISS/Chroma)
- 3-tier model router (task → model mapping)
- Port 330+ claude-skills (progressive disclosure)
- EnterWorktree tool (standalone isolation, no daemon)
- Extended hooks (25+ lifecycle events)
- Core tools (Bash/Read/Write/Edit/Glob/Grep)
- Deny-first permissions

**Phase 2 (4 months):**
- Graph memory (Zettelkasten + LP-RAG)
- Cost-sensitive routing
- Dynamic workflow engine (agent/parallel/pipeline primitives, single-session)
- Workflow script sandbox (RestrictedPython)
- Provider abstraction layer

**Phase 3 (6-9 months, gated behind usage data):**
- Supervisor daemon + fleet view
- Background workflows
- Voice pipeline (provider-swappable STT→Agent→TTS)
- Dreaming engine (LLM-based default, PDE experimental)
- Adversarial verifier (anonymized + bias-corrected)

**Phase 4 (12+ months):**
- Self-evolving skills (safety validator mandatory)
- Desktop shell (Electron/React)
- Cross-model verification (when multi-provider budgets allow)

**Phase 5 (research):**
- Harness rewriting (human-in-the-loop required)
- Field-theoretic memory (if bake-off wins)

## Why This Combination is a Breakthrough

### Novel Combinations (No Single System Has All of These)

1. **Field-theoretic memory consolidation** (when bake-off validates) — PDE-governed continuous fields for memory, not discrete embeddings
2. **Anonymized bias-corrected adversarial verification** — identity anonymization + ReTAS dialectical alignment + collusion detection + rogue agent prevention
3. **Provider-swappable multimodal pipeline** — LLMs + STT + TTS all swappable behind one abstraction
4. **Memory-augmented model routing** — memory caches answers → cheap model for repeats → expensive model for first-time only
5. **Self-evolving skills with safety validation** — GEPA evolution + "Misevolve"-informed gates

### The Self-Reinforcing Loop

Each component reinforces the others:

```
Better Memory → Better Routing → More Efficient Fleet → Higher-Quality Verification
      ↑                                                              ↓
      └────────────────── Better Memories ← Verified Findings ←────┘
                                    ↓
                          Self-Evolving Skills Improve from Verified Trajectories
```

- **Memory feeds routing:** Cached answers → cheaper queries → cheaper routing decisions
- **Routing feeds fleet:** Right model per agent → efficient parallelism
- **Fleet feeds verification:** Adversarial cross-check at scale (multiple verifiers in parallel)
- **Verification feeds memory:** Confirmed findings → high-confidence memories
- **Memory consolidation (dreaming):** Discovers patterns across fleet sessions
- **Self-evolution:** Skills improve from verified trajectories in memory

**The result:** A self-reinforcing loop where each turn through the cycle makes the whole system stronger.

### Why Candidate B Won

1. **Clean system boundaries** — supervisor manages processes, worktrees manage files, workflow engine manages orchestration
2. **Addresses the biggest gap** — Lyra can't run unattended or in parallel today
3. **Phased rollout validates demand** — ships value at every phase, gates complex infrastructure behind usage data
4. **Absorbs best ideas from all candidates** — memory innovations from A, minimal changes from D, evolution from C (gated)
5. **Safety is architectural** — worktree isolation, sandbox, permission gates, collusion detection built-in
6. **Provider-agnostic at every layer** — works across Claude/DeepSeek/GPT/open-weights

### Competitive Position After Full Implementation

**Lyra would be the only open-source agent harness with:**
- Supervisor daemon + fleet view (unattended operation)
- Anonymized bias-corrected adversarial verification
- Provider-swappable voice pipeline
- Graph memory with field-theoretic consolidation (if bake-off wins)
- Self-evolving skills with safety validation
- Worktree isolation substrate

**This positions Lyra as breakthrough tier, not just top-5 tier.**

---

## Appendix: Debate Participants

The 15+ expert personas who critiqued, challenged, and converged the architecture:

1. **Senior AI Solutions Architect** — end-to-end solution fit
2. **Senior Software Architect** — system design, boundaries, data flow
3. **Senior Backend Engineer** — implementation feasibility
4. **Senior AI Researcher** — research validity and evidence
5. **Senior AI Engineer (LLMOps)** — cost, latency, provider limits
6. **Senior SRE / Reliability Engineer** — failure modes, ops burden
7. **Senior Security Engineer** — credentials, sandboxing, blast radius
8. **Senior Distributed-Systems Engineer** — fleet coordination, consistency
9. **Senior Data / Knowledge Engineer** — memory, indexing, retrieval
10. **Senior Product Manager** — scope, sequencing, value delivery
11. **Senior Product / UX Designer** — usability, discoverability
12. **Senior Technical Writer / DX** — documentation clarity
13. **Senior ML Evaluation / Benchmark Scientist** — measurement rigor
14. **Senior Performance / Cost Engineer** — token economics
15. **Senior Planning / Reasoning Specialist** — when planning helps
16. **Adversarial Skeptic** — challenges assumptions, demands proof

Each persona brought domain expertise and a **signature challenge** — the question they always press to keep debate rigorous.

---

## Validation: Memory Findings Post-Debate (June 5, 2026)

After the architecture debate converged on Fleet-Centric (Candidate B), 4 significant memory research findings emerged from the ICLR 2026 MemAgent Workshop. This section validates whether these findings change the architectural choice.

### The 4 Memory Findings

#### 1. Three-Layer Memory Architecture (AOI)
- **Impact:** 5 | **Effort:** 4 | **Tier:** Breakthrough
- **Core Innovation:** Working Memory (24h retention) → Task Queue → Semantic Memory (7d retention) with formal compression guarantees
- **Results:** 72.4% compression ratio, 92.8% information preservation, 34.4% MTTR reduction
- **Source:** ICLR 2026 Workshop MemAgent — AOI: Multi-Agent Collaborative Framework

#### 2. Active Memory Reconstruction (MRAgent)
- **Impact:** 5 | **Effort:** 5 | **Tier:** Breakthrough  
- **Core Innovation:** Cue-Tag-Content graph with LLM-in-the-loop iterative exploration replaces passive retrieval
- **Results:** +23% improvement over passive retrieval baselines, reduced token cost through active pruning
- **Source:** ICLR 2026 Workshop MemAgent — Memory is Reconstructed, Not Retrieved

#### 3. Cost-Sensitive Store Routing
- **Impact:** 4 | **Effort:** 3 | **Tier:** Parity
- **Core Innovation:** Store-level selection before retrieval with explicit accuracy-cost tradeoff (λ parameter)
- **Results:** 94% coverage, 58% exact match, improved accuracy AND efficiency vs uniform retrieval
- **Source:** ICLR 2026 Workshop MemAgent — Did You Check the Right Pocket?

#### 4. Experiential Reflective Learning (ERL)
- **Impact:** 4 | **Effort:** 3 | **Tier:** Parity
- **Core Innovation:** Post-task reflection generates abstracted heuristics with selective retrieval at test time
- **Results:** +7.8% on Gaia2 benchmark, better transfer than raw trajectory prompting
- **Source:** ICLR 2026 Workshop MemAgent — Experiential Reflective Learning

### Validation Questions

#### Q1: Do these findings make Memory-Centric (Candidate A) the better choice?

**Answer: NO**

**Reasoning:**
1. All 4 findings are **capability plane components** — they enhance memory as a service consumed by the orchestration layer
2. **None define system boundaries, concurrency model, or orchestration patterns** — the core architectural choices
3. The Round 1 consensus still holds: **"Memory is a SERVICE, not an architecture spine"**
4. The findings validate that memory innovations should be **absorbed into Fleet-Centric**, which is exactly what the debate convergence decided

#### Q2: What changes to the Fleet-Centric architecture?

**Answer: REINFORCES convergence, adds concrete implementations**

**Specific additions to Memory Capability Plane:**
1. **Memory structure:** AOI three-layer architecture (Working 24h / Task Queue / Semantic 7d) replaces abstract "memory store"
2. **Retrieval strategy:** MRAgent's active reconstruction via Cue-Tag-Content graph replaces passive similarity search
3. **Routing layer:** Cost-Sensitive Store Router becomes first gate in retrieval pipeline
4. **Learning mechanism:** ERL reflection-to-heuristic pipeline added to consolidation subsystem

**All changes are additive within the Memory Capability Plane already planned in Candidate B. No architectural spine changes needed.**

#### Q3: Do any findings challenge the Fleet-Centric spine?

**Answer: NO — findings DEPEND ON fleet infrastructure**

**Analysis by finding:**
- **AOI:** 24h→7d retention with background consolidation **requires persistent daemon for idle-time processing** (✅ validates Phase 3 daemon)
- **MRAgent:** Iterative LLM-in-the-loop retrieval **benefits from fleet parallelism for concurrent queries** (✅ supports Fleet)
- **Cost-Sensitive:** Store router as independent service **consumed by multiple agents in parallel** (✅ supports Fleet)
- **ERL:** Post-task reflection **requires task lifecycle signals from orchestrator** (✅ requires Fleet coordination)

**The memory findings actually VALIDATE the need for supervisor daemon (Phase 3) — AOI and ERL both require background processing and task completion signals that only a persistent orchestrator can provide.**

#### Q4: Do findings reveal missing infrastructure?

**Answer: YES — but infrastructure already planned in Phase 3**

**Critical dependencies identified:**
1. **Background processing** — idle-time consolidation (AOI), dreaming, heuristic generation (ERL)
2. **Task lifecycle signals** — completion triggers for reflection, success/failure status for learning
3. **Persistent state** — cross-session memory retention, 24h/7d boundaries, heuristic accumulation

**These are EXACTLY what the supervisor daemon (Phase 3) provides.** The memory findings don't reveal gaps — they validate the fleet architecture design.

### Updated Memory Capability Plane Design

With the 4 findings integrated, the Memory Plane in Fleet-Centric architecture now has concrete, battle-tested implementations:

```
Memory Plane (Capability Layer in Fleet-Centric)
├── AOI Three-Layer Architecture
│   ├── Working Memory (24h retention, high-throughput buffer)
│   ├── Task Queue (structured subtask store with priority scheduling)
│   └── Semantic Memory (7d retention, LLM-compressed with 50% overlap)
│
├── MRAgent Active Reconstruction
│   ├── Cue-Tag-Content Graph (semantic bridges between query and content)
│   ├── Iterative LLM Exploration (reasoning-guided search)
│   ├── Path Pruning (early termination of low-relevance branches)
│   └── Multi-hop Reasoning (natural graph traversal)
│
├── Cost-Sensitive Store Router (first gate before retrieval)
│   ├── Policy: π*(q) = argmax E[Acc(q,G) - λ * Σ(c_s)]
│   ├── Hybrid Routing (pattern matching + embeddings + fallback)
│   ├── Configurable λ (accuracy-cost tradeoff parameter)
│   └── Metrics: Coverage, Exact Match, Waste
│
├── ERL Learning Pipeline (consolidation subsystem)
│   ├── Post-Task Reflection (LLM extracts lessons from trajectory)
│   ├── Heuristic Generation (abstracted transferable rules)
│   ├── Selective Retrieval (top-k relevant heuristics at task start)
│   └── Context Injection (heuristics in system prompt)
│
└── Background Consolidation (daemon-driven, Phase 3)
    ├── AOI compression (24h→7d with formal guarantees)
    ├── ERL heuristic extraction (triggered by task completion)
    ├── MRAgent graph maintenance (periodic rebalancing)
    └── Cost-Sensitive routing stats (update policy parameters)
```

### Validation Verdict

**The Fleet-Centric architecture choice HOLDS and is STRENGTHENED.**

**Evidence:**
1. ✅ All 4 memory findings fit cleanly into Memory Capability Plane without architectural changes
2. ✅ Findings validate the need for supervisor daemon (Phase 3) — background processing requires persistent orchestrator
3. ✅ No finding challenges orchestration-as-spine decision
4. ✅ Findings provide concrete, benchmark-validated implementations that reduce Phase 2-3 risk
5. ✅ Self-reinforcing loop in original debate (memory → routing → fleet → verification → memory) now has specific mechanisms:
   - AOI compression → Cost-Sensitive routing → Fleet parallelism → MRAgent exploration → ERL heuristics → Better memory

**The memory findings shift from abstract concepts (field-theoretic memory, Zettelkasten) to concrete, production-tested implementations with published benchmarks. This is a risk reduction for Lyra's implementation roadmap.**

**No architectural revision needed. Proceed with Fleet-Centric (Candidate B) as planned.**

---

## Document Status

**Version:** 1.1 (June 5, 2026)  
**Status:** Complete — debate converged, post-debate validation complete  
**Validation:** 4 memory findings analyzed, Fleet-Centric choice confirmed  
**Next Steps:** See BREAKTHROUGH-ARCHITECTURE.md for detailed system design  
**Related Documents:**
- DEBATE-LEDGER.md (round-by-round log)
- BREAKTHROUGH-ARCHITECTURE.md (capstone system design)
- BASELINE.md (current state assessment)
- MASTER-PLAN.md (implementation roadmap)
- findings.md (research findings corpus)

