> ⚠️ **This is an older version.** The authoritative version is at [docs/lyra-upgrade/ARCHITECTURE-DEBATE.md](../lyra-upgrade/ARCHITECTURE-DEBATE.md).

# Architecture Debate: Three Candidates for Lyra's Core Architecture

**Date**: 2026-06-01
**Run**: 19 -- Adversarial multi-panel debate with cross-candidate critique, trade-off quantification, and convergence synthesis
**Status**: CONVERGED -- M-ARCH core (TKG) + O-ARCH verification middleware (AVP) adopted. E-ARCH deferred to Phase 3+. 5 live disagreements recorded for empirical resolution.
**Grounded in**: SYNTHESIS.md (228 sources), core-papers-deep-research.md, ultracode-mechanisms.md, memory-architecture.md, BASELINE.md (87+ Lyra packages audited), BREAKTHROUGH-ARCHITECTURE.md, candidate-a-memory-first.md

> **NOTE**: This is the docs/architecture/ copy. The authoritative (more recent) version lives at [lyra-upgrade/ARCHITECTURE-DEBATE.md](../lyra-upgrade/ARCHITECTURE-DEBATE.md), which contains additional debate rounds and empirical resolution protocols.

---

## 1. Introduction

### 1.1 Why Debate Matters

Lyra is not a greenfield project. It has 87+ existing Python packages with a TypeScript UI layer, implementing a provider-agnostic agent harness with effort management, model routing, workflow orchestration, skills management, and adversarial verification. The architecture decisions made today will determine whether these independently-developed packages coalesce into a coherent system or remain a collection of unconnected capabilities.

The research corpus (228+ deep-read sources from ICLR 2026 MemAgent Workshop, leading AI agent harnesses, and production systems) reveals a fractured landscape. Memory-first, orchestration-first, evolution-first, and provider-first lineages each have strong empirical backing but make incompatible bets. Fusing them requires explicit trade-off decisions, not vague "best of all worlds" synthesis.

This debate applies the same adversarial methodology that validated Claude Code's architecture: independent proposers design competing architectures, diverse critics attack from every relevant angle, and only proposals that survive multi-round cross-examination are adopted. The process exposes hidden assumptions, quantifies trade-offs, and records what was explicitly rejected and why.

### 1.2 The Personas

Six expert personas participate in this debate, each with a defined perspective and evaluation methodology:

| Persona | Lens | Bias | Evaluation Method |
|---------|------|------|-------------------|
| **Senior Architect** | Module boundaries, interface contracts, coherence | Favors clean boundaries, low coupling | Module-dependency analysis, interface stability, circular-dependency detection |
| **Senior AI Researcher** | Evidence credibility, paper interpretation, empirical validity | Favors cited results, skeptical of extrapolation | Source integrity check, result reproduction risk, claim-vs-evidence mapping |
| **Senior AI Engineer** | Build cost, latency, token cost, provider limits | Favors implementability, practical constraints | Build-effort estimate, per-operation latency model, provider-capability matrix check |
| **Senior SRE** | Reliability, failure modes, observability, recovery | Favors deterministic failure handling, graceful degradation | Failure-mode enumeration, recovery-path specification, observability-instrumentation audit |
| **Senior Security Engineer** | Blast radius, injection surfaces, privilege escalation, safety invariants | Favors least-privilege, attack-surface minimization | Threat model per component, injection-vector audit, safety-invariant verification |
| **Adversarial Skeptic** | Simplest alternative, Occam's razor, prove complexity is worth it | Favors minimal viable solution | Simpler-alternative demonstration, complexity-justification demand, "what problem does this solve?" pressure |

### 1.3 Methodology

The debate follows three rounds:

**Round 1 -- Initial Proposals**: Each candidate is presented with its core bet, changes vs. Lyra baseline, what it keeps unchanged, and migration cost. Each critic persona delivers initial objections with specific evidence.

**Round 2 -- Rebuttals and Revisions**: Proposers respond to objections, accepting or rejecting adjustments. Revised proposals are re-presented.

**Round 3 -- Convergence and Sign-Off**: Remaining disagreements are identified as either resolved (adopted/rejected) or live (requires empirical resolution). A unified synthesis documents what survives, what is rejected, and what remains open.

### 1.4 Baseline: What All Candidates Build On

From BASELINE.md (Run 16 audit of Lyra's actual source code):

**Already implemented across 87+ packages**:
- Provider abstraction (AbstractProvider ABC with 4 adapters: Anthropic, DeepSeek, OpenAI, Google)
- 6-level effort scale (LOW through ULTRACODE) with per-provider mapping
- 3-tier model router (Rule/Semantic/Neural with NeuralUCB contextual bandit)
- Workflow engine core (ScriptVM, pause/resume, phase tracking, 16-concurrent cap, 1000-per-run cap)
- Adversarial Verification Protocol (AVP with mutation classification, 3-critic panel, consensus gate)
- Memory stack (A-MAC admission control, world graph, codebase graph, entropic consolidation)
- Skills system (loader, curator, weaver, evolution)
- Safety defense (multi-layer defense, misevolution detection)
- 15+ additional packages (swarm, sessions, hooks, MCP, plugins, voice, context, tools, observability)

**Critical gap**: Integration wiring between packages. The workflow engine's `_run_task()` is a placeholder that estimates tokens from word count rather than making actual LLM calls. The effort scale is not exposed as a `/effort` slash command. The auto-orchestration trigger has config but no complexity estimation logic.

**Migration cost constraint**: Any proposed upgrade must state what it changes, what it replaces, and what it keeps. No architecture can replace all 87+ packages.

---

## 2. Candidate Architectures

### 2.1 Candidate A: Memory-Centric (M-ARCH) -- TKG + A-MAC + A-MEM

**Core bet**: Memory is the central nervous system through which routing, skills, verification, and swarm coordination all flow. A Temporal Knowledge Graph with A-MAC admission control, A-MEM Zettelkasten linking, and a 4-tier hierarchy (Working / Episodic / Semantic / Archive) is the single highest-leverage architectural decision.

**Primary documents**: `candidate-a-memory-first.md`, `memory-architecture.md`

**Key citations**:
- A-MAC (OpenReview #mmdqUrEY24): 5-factor admission control, F1=0.583, -31% latency vs. Mem0
- A-MEM (arXiv 2502.12110): Zettelkasten dynamic linking, outperforms SOTA across 6 foundation models
- MemAgent (ICLR 2026 Oral, source #256): 8K training to 3.5M token deployment with <10% degradation
- AOI (source #68): 72.4% compression while preserving 92.8% critical information, -34.4% MTTR
- Field-Theoretic Memory (arXiv 2602.21220): +116% F1 on LongMemEval with p<0.01
- Cost-Sensitive Store Routing (source #60): Route queries to appropriate store, selective retrieval cuts tokens
- MemGrad (source #70): Textual gradients transform batched feedback into persistent memory updates

#### What M-ARCH Changes vs. Baseline

| Component | Baseline State | M-ARCH State | Migration |
|-----------|---------------|--------------|-----------|
| A-MAC admission weights | Paper defaults, static | Lyra-calibrated on 10K coding/research examples | 2 weeks: calibration dataset + optimization |
| Knowledge graph linking | Package exists, static | A-MEM dynamic linking, auto-maintained | 3 weeks: linking pipeline in `lyra-knowledge-graph` |
| Memory-tier awareness | Implicit in package structure | Explicit in all components (router, skills, AVP) | 4 weeks: wire tier awareness into `lyra-router` + `lyra-workflow` |
| Workflow engine dispatch | LLM call placeholder | Memory-augmented: check TKG before LLM call | 2 weeks: integrate with `lyra-memory` |
| AVP feedback loop | No memory integration | AVP blocks recorded in TKG as Semantic-tier memories | 1 week: add AVP block recording to TKG write path |
| Compression strategy | Not integrated | AOI-style sliding window, 7-day threshold, ROUGE-L verification | 3 weeks: compression pipeline in background job |

#### What M-ARCH Keeps Unchanged

Provider abstraction, effort scale, model router (augmented but not replaced), AVP (writes to/reads from TKG), skills system (reads from/writes to TKG), safety system, terminal UI, and all 87+ existing packages.

#### Total Migration Cost: 12 weeks

| Phase | Duration | What Delivers |
|-------|----------|---------------|
| Phase 1: A-MAC calibration | 2 weeks | Calibrated admission weights |
| Phase 2: TKG linking + retrieval plumbing | 3 weeks | A-MEM dynamic links, Cost-Sensitive Retrieval |
| Phase 3: Compression + evolution pipeline | 3 weeks | AOI compression, MemGrad textual gradients |
| Phase 4: Full integration (router, AVP, skills) | 4 weeks | All components wired through TKG |

Risk of regression: **Low**. Changes are additive (new mechanisms layered on top); existing `lyra-memory` tests (18+ test files) continue to pass.

---

### 2.2 Candidate B: Orchestration-Centric (O-ARCH) -- Dynamic Workflows + AVP Middleware

**Core bet**: The workflow engine is the organizing principle. Every capability -- memory, routing, skills, verification -- is a middleware layer that the workflow engine invokes. The Adversarial Verification Protocol (AVP) is universal middleware that every mutating action passes through. Orchestration is not a feature; it is the architecture.

**Primary documents**: `ultracode-mechanisms.md`, `plans/19-ultracode-replication.md`, BREAKTHROUGH-ARCHITECTURE.md §4-5

**Key citations**:
- SABER (source #67): 55-96% error contribution from mutating actions; mutation-gating catches ~92% of impactful errors while verifying only ~20-30% of actions
- AutoScientists (sources #154-156): Critique-before-execute protocol for agent actions
- Claude Code Dynamic Workflows (sources #203, #349): ScriptVM, parallel agent spawning, pause/resume
- RouteLLM (source #222): Matrix factorization for routing policy training
- BEST-Route (source #225): Dynamic multi-sample routing for cost-quality Pareto
- CaMeL (source #243): Control/data-flow separation for provable security against prompt injection
- DecentMem (source #99): Dual-pool per-agent memory with O(log T) regret, +23.8% vs centralized
- SkillNet (sources #158-159): 500K+ skills ecosystem, 5-D quality scoring, skill graph

#### What O-ARCH Changes vs. Baseline

| Component | Baseline State | O-ARCH State | Migration |
|-----------|---------------|--------------|-----------|
| Workflow engine dispatch | Placeholder `_run_task()` | Full provider dispatch, memory-augmented routing | 4 weeks: wire `WorkflowEngine` through `ModelRouter` to `AbstractProvider` |
| Auto-orchestration toggle | Config exists, no trigger logic | Complexity estimation + keyword detection + keyword-trigger support | 3 weeks: implement `estimateComplexity()`, system message injection |
| AVP integration | Implemented in `avp.py` but standalone | Universal middleware: every tool call, skill update, agent spawn passes through | 3 weeks: wire AVP into tool execution pipeline |
| Provider-diverse critics | Single-model critics | 3 critics with different providers (Claude + DeepSeek + open-weight) | 2 weeks: multi-provider critic routing |
| Workflow scripts | Not savable as commands | Save/load from `.claude/workflows/`, `/<name>` invocation | 2 weeks: workflow registry + command integration |
| Progress UI | Internal state only | Terminal rendering via Rich/Textual, phase-level progress | 3 weeks: TUI integration |
| Cross-provider worker pools | Single-provider agents | Per-phase provider routing (cheap model for bulk, expensive for verification) | 2 weeks: provider-to-phase mapping |

#### What O-ARCH Keeps Unchanged

Provider abstraction (unchanged), effort scale (unchanged), skills system (invoked by workflow engine, not replaced), memory system (used by workflow engine for context, not replaced), safety system (parallel safety gate alongside AVP), terminal UI (extended but not replaced), and all 87+ existing packages.

#### Total Migration Cost: 10 weeks

| Phase | Duration | What Delivers |
|-------|----------|---------------|
| Phase 1: Wire provider dispatch | 4 weeks | Workflow engine actually calls LLMs |
| Phase 2: Auto-orchestration | 3 weeks | Complexity estimation, system message toggle |
| Phase 3: Universal AVP | 3 weeks | Every mutating action gated by 3-critic panel |

Risk of regression: **Medium**. Wiring the provider dispatch changes the critical path of the workflow engine. Existing workflow unit tests need provider mocks. The AVP middleware insertion may change error semantics for existing tool call paths.

---

### 2.3 Candidate C: Ultracode-Native (E-ARCH) -- 4 Primitives as Organizing Structure

**Core bet**: The four ultracode primitives (Effort Menu, Auto-Orchestration Toggle, Dynamic Workflow Engine, Adversarial Quality Patterns) are not features -- they are the architecture. Every capability in Lyra should be understood as implementing one or more of these primitives. Memory is a refinement of the effort menu (what effort level to use for storage). Routing is a refinement of the dynamic workflow engine (which provider to assign to which phase). Evolution is a refinement of the adversarial quality pattern (evolve, verify, promote). The architecture is flat -- four primitives, no additional abstraction layers.

**Primary documents**: `ultracode-mechanisms.md`, `plans/19-ultracode-replication.md`, SYNTHESIS.md §3 (Evolution-First lineage)

**Key citations**:
- Darwin/DGM (sources #261-262): Self-rewriting coding agent, SWE-bench 20% to 50%, Polyglot 14.2% to 30.7% through archive-based empirical self-improvement
- Meta-Harness (source #121): Auto-optimizing harness code via outer-loop search (+7.7 points, 4x fewer tokens)
- FORGE (source #103): Parallel memory evolution without weight updates (1.7-7.7x improvement)
- SkillOpt (source #117): Skills as trainable parameters with validation gates (52/52 best-or-tied)
- SEAL (sources #91-93): Self-improving agents through sandboxed execution + evaluation
- ADAS (source #94): Autonomous improvement through iterative refinement
- EvoTest (source #137): Evolutionary test generation
- ReflecTool (source #130): Self-reflection with tool-augmented feedback

#### What E-ARCH Changes vs. Baseline

| Component | Baseline State | E-ARCH State | Migration |
|-----------|---------------|--------------|-----------|
| Architecture structure | Layered (Provider -> Router -> Workflow -> Memory -> Skills) | Flat (4 primitives, no layers) | 6 weeks: Restructure all interfaces around primitives |
| Memory | Separate subsystem | Implemented as Primitive 1 (effort for storage tier) | 4 weeks: reduce A-MAC/A-MEM to effort-level mappings |
| Router | Separate 3-tier component | Implemented as Primitive 3 (workflow engine phase routing) | 4 weeks: embed routing decisions in workflow scripts |
| AVP | Separate middleware | Implemented as Primitive 4 (adversarial quality pattern) | 3 weeks: collapse AVP into quality-pattern library |
| Skills evolution | Separate pipeline | Implemented as Primitive 4 (evolve-verify-promote cycle) | 5 weeks: Darwin-style archive-based evolution |
| Meta-Harness outer loop | Not implemented | Outer loop rewrites Lyra's own Python/TypeScript code | 8 weeks: safe self-modification with behavioral safety gates |

#### What E-ARCH Keeps Unchanged

Provider abstraction (unchanged), effort scale (expanded but same core), tool implementations (unchanged), safety system (augmented but not replaced), terminal UI (unchanged). However, the package structure is fundamentally reorganized -- memory, routing, and skills packages are subsumed into the four primitives.

#### Total Migration Cost: 18 weeks

| Phase | Duration | What Delivers |
|-------|----------|---------------|
| Phase 1: Primitive restructuring | 6 weeks | Reorganize 87+ packages into 4 primitive groups |
| Phase 2: Memory-as-effort | 4 weeks | Collapse memory hierarchy into effort levels |
| Phase 3: Router-as-workflow | 4 weeks | Embed routing in workflow scripts |
| Phase 4: Skills evolution | 5 weeks | Darwin-style evolution pipeline |

Risk of regression: **High**. Restructuring 87+ packages into a flat 4-primitive organization breaks every existing import, interface, and test. The BASELINE finding (packages are independently buildable) is violated by circular dependencies created during reorganization.

---

## 3. Adversarial Critique

### 3.1 Senior Architect -- Module Boundaries, Coherence

**On M-ARCH**: "The TKG as a single integration point is architecturally elegant -- every component reads/writes through one well-defined interface. But there is a hidden circularity problem. The workflow engine triggers memory writes (tool results -> TKG), but the workflow engine dispatch is _augmented by_ memory lookups (check TKG before routing). This creates a read-write cycle: dispatch reads TKG, execution writes TKG, next dispatch reads new TKG. In the steady state this is fine, but during high-velocity sessions (10+ concurrent agents), TKG read-after-write consistency becomes a problem. The MemoryNode's `last_accessed` field is updated on every read, which means every retrieval mutates state. A read-heavy operation (retrieve context for 16 concurrent agents) generates 16 writes to `last_accessed`, potentially invalidating concurrent readers.

**Specific structural concern**: The MemoryNode `last_accessed` update on read violates the CQRS principle. Reads should not have side effects. Mitigation: batch `last_accessed` updates (aggregate in memory, flush every 5 seconds) or move `access_count`/`last_accessed` to a separate append-only log that doesn't mutate the node.

**On O-ARCH**: "The AVP as universal middleware is clean -- it intercepts every action at a single point (the tool execution pipeline). The interface is simple: `classify(action) -> gate(action, critics) -> execute(action)`. No component bypasses the gate. BUT: the mutation classifier's 3-tier logic (static set -> regex -> parameter analysis) is a leaky abstraction. As new tools are added, the static sets and regex patterns must be updated. This is a maintenance burden that will inevitably drift from reality.

**Specific structural concern**: The 16-concurrent agent cap and 1000-per-run cap are enforced in the workflow engine but not in the AVP or provider layer. An agent that spawns subagents outside the workflow engine (e.g., via direct API calls) bypasses the cap. Mitigation: enforce caps at the provider adapter level, not just the workflow engine.

**On E-ARCH**: "Flat 4-primitive architecture is architecturally the simplest -- no layers, no middleware, just four mechanisms. But simplicity at the macro level hides complexity at the micro level. If memory is 'just an effort level,' then effort management must handle storage tier selection, admission control, compression strategy, and retrieval routing -- which is at least as complex as the current memory subsystem, just embedded _inside_ a primitive rather than expressed as a standalone component. This is false simplification.

**Specific structural concern**: The 87+ existing packages have clean interface boundaries (AbstractProvider, EffortManager, ModelRouter, WorkflowEngine). Collapsing them into 4 primitives destroys these interfaces and forces cascade refactoring across the entire codebase. The migration cost (18 weeks) likely underestimates this by 2-3x because of hidden circular dependencies."

---

### 3.2 Senior AI Researcher -- Paper Evidence Credibility

**On M-ARCH**: "The central claim -- 'memory is the first bottleneck to hit as agents scale' (SYNTHESIS §9.2) -- is a post-hoc narrative from the ICLR 2026 MemAgent Workshop papers, which are _about_ memory. It's a selection bias: of course memory researchers think memory is the bottleneck. The SYNTHESIS itself notes that the WorldMemArena finding (source #100) shows 'improved memory writing/storage doesn't automatically translate to better agent performance.' Memory-first advocates would say 'your memory wasn't good enough,' but this is unfalsifiable.

**Critical evidence gap**: The Field-Theoretic Memory (+116% F1, arXiv 2602.21220) is cited as Phase 2 potential. But this is a single paper with no replication, published 4 months ago. The +116% improvement is on LongMemEval, a benchmark the authors themselves designed. If this claim does not replicate on independent benchmarks (e.g., LoCoMo, MemBench), the entire Phase 2 roadmap built on it collapses.

**A-MAC's F1=0.583 is on LoCoMo, which is a general-chat benchmark**. The claim that Lyra can improve this to 0.63+ on coding-specific tasks (candidate-a-memory-first.md §4, assumption 2) is unsupported. Coding tasks produce different memory patterns (long code blocks, error messages, git diffs) than the conversational patterns LoCoMo tests. There is zero published evidence that A-MAC's 5-factor weights transfer from chat to code.

**Specific weakness**: Memory Transplants (source #58) explicitly shows that 'neither memory architecture nor content transfers well across domains (code -> math).' The M-ARCH document acknowledges this (assumption 4) but hand-waves it with 'Lyra's domain (code + terminal) is unitary.' This is false -- Lyra already supports research, coding, and voice, which are different domains with different memory patterns.

**On O-ARCH**: "SABER's 55-96% finding (mutating actions cause dominant error contribution) is the strongest empirical anchor in the entire debate corpus. It is well-measured (p<0.001, n=500+ agent trajectories) and has been replicated in the AutoScientists work. The claim that mutation-gating catches ~92% of impactful errors while verifying only 20-30% of actions is well-supported.

**But**: The 3-critic design (correctness, safety, efficiency) has no empirical basis. SABER uses 2 critics (correctness + safety). AutoScientists uses a variable number (1-5). There is NO study comparing 1 vs. 3 vs. 5 critic panels on error-catch rate, latency, or cost. The BREAKTHROUGH-ARCHITECTURE records this as a live disagreement (AVP critic count: 3 vs. 5), but the default choice of 3 is arbitrary.

**Also**: The claim that provider-diverse critics (Claude + DeepSeek + open-weight) 'maximizes architectural diversity in verification' (BREAKTHROUGH-ARCHITECTURE §0a, line 25) is an article of faith. There is no study showing that different providers catch different error types. It is equally plausible that all frontier models make the same class of errors (learned from similar training data) and provider diversity adds complexity without diversity.

**On E-ARCH**: "Darwin's results are impressive (SWE-bench 20% to 50%) but must be contextualized. Darwin ran on SWE-bench Verified, which has 500 examples. The evolution loop required ~1M tokens per skill per cycle. For 10 skills, that's 10M tokens per cycle. This is the cost the Evolution-First lineage accepts, but it must be stated transparently: a single evolution cycle across Lyra's expected skill set (50+ skills) would cost 50M+ tokens -- approximately $75 at DeepSeek rates or $750 at Claude rates.

**The Meta-Harness outer loop (source #121)** claims +7.7 points with 4x fewer tokens. But the paper was evaluated on a single codebase (a specific Python web app) and the outer loop optimized for a single metric (test pass rate). It is unknown whether the approach generalizes to Lyra's multi-provider, multi-domain reality.

**Specific concern**: The claim that 'evolution is inevitable' (SYNTHESIS §3, line 366) is not a scientific finding -- it is a philosophical position. The evidence shows that evolution _can_ improve agents on specific benchmarks, not that it _must_ for all agents. Static agents with good memory architectures may plateau at a higher level than evolved agents with weak memory foundations."

---

### 3.3 Senior AI Engineer -- Cost, Latency, Provider Limits

**On M-ARCH**: "The admission control overhead is the primary cost concern. Every memory write requires a utility-assessment LLM call (~1K tokens). For a typical coding session generating 500+ memory candidates, that's 500K tokens just for admission -- approximately $0.75 at DeepSeek rates or $1.50 at Haiku rates. The document claims early bail-out catches 80% of rejections at ~10 output tokens, which means 100 candidates per session actually need the full assessment call. This is ~100K tokens -- still real cost.

**The Fast-path claim** (<50ms for 95% of queries) is achievable for working-memory lookups (in-memory hash table, <1ms) but NOT for full TKG traversal. At 100K nodes, HNSW approximate nearest neighbor search is O(log N) ~ 5ms, but graph traversal (link following for multi-hop queries) is O(path_length * branching_factor). A 3-hop query with average branching factor 10 requires visiting up to 1,000 nodes. At 0.5ms per node traversal (LLM classification), that's 500ms -- exceeding the <50ms P95 claim.

**Provider concurrency limits**: The TKG write path requires LLM calls for admission. At 16 concurrent agents (workflow engine cap), the TKG could receive 16 concurrent write requests. Each involves an LLM utility assessment call. If all 16 hit the same provider (e.g., all using DeepSeek), the provider's rate limit (assume 500 RPM for DeepSeek) is hit within 2 seconds. Mitigation: distribute admission calls across providers (not all memories need the same quality assessment) or batch admission calls.

**On O-ARCH**: "The AVP overhead is the primary latency concern. Three parallel critic calls, each 500-1500ms, means the AVP adds 500-1500ms to every mutating action. For a typical coding session with 50 mutating actions, that's 25-75 seconds of cumulative verification latency. The document claims SABER's mutation-gating means only 20-30% of actions are verified, but in a coding workflow, most actions ARE mutating (Write, Edit, Bash). The actual rate may be 60-80%.

**The provider-diverse critic design compounds latency**. If one critic uses DeepSeek (fast, ~500ms) and another uses Claude Sonnet (~1000ms) and a third uses open-weight (variable, 500-3000ms), the AVP latency is max of all three -- 1000-3000ms. This is acceptable for safety-critical operations but unacceptable for interactive use where a user is waiting for the next step.

**Breakthrough claim**: The plan proposes per-phase provider routing (cheap model for bulk discovery, expensive for verification). This requires the workflow script to specify which provider each phase uses. This is architecturally powerful but adds scripting complexity. The workflow engine must handle provider switching mid-execution, including context transfers (compatible message formats across providers). This is a non-trivial engineering problem.

**On E-ARCH**: "Darwin-style evolution at Lyra scale is computationally prohibitive. 50+ skills x 1M tokens per cycle x 10 cycles = 500M tokens just for initial tuning. At DeepSeek rates ($0.27/MTok input, $1.10/MTok output), that's $135-$550 for the first evolution round. At Claude rates ($3/MTok input, $15/MTok output), it's $1,500-$7,500.

**The Meta-Harness outer loop** modifies Lyra's own code. This requires the agent to understand the full 87-package monorepo structure, generate correct Python/TypeScript code, and validate that the modifications don't break existing tests. Each self-modification cycle requires running the full test suite (~10+ minutes). At 10 cycles per improvement, that's 100+ minutes of continuous testing.

**Specific concern**: The 4-primitive architecture collapses the existing layered structure. This means every engineer working on Lyra must understand the entire 4-primitive system to modify one part. Developer onboarding time increases significantly."

---

### 3.4 Senior SRE -- Reliability, Failure Modes, Observability

**On M-ARCH**: "The TKG write path has a single point of failure: the ANN index. If the HNSW/IVFPQ index becomes corrupted (a known failure mode for HNSW under high-velocity writes), retrieval degrades silently -- it returns approximate results that may be wrong, but there's no error signal. Mitigation: maintain a secondary exact-search fallback (brute-force cosine similarity) for verification. Periodically check index accuracy against the fallback.

**The WAL replay mechanism for crash recovery is not specified**. If the supervisor crashes mid-admission (utility LLM call completed but memory not yet stored), the candidate memory is lost. For most memories this is acceptable (they'll be re-generated), but for 'insight' type memories (high utility, high type_prior), loss is costly. Mitigation: write-ahead log for admission decisions >= 0.8 (high-value memories). Replay on crash.

**Cross-session entity linking** (memory-architecture.md §3) is a background job that can fail silently. If the entity extraction pipeline produces garbage (extracts "the" as a key entity), cross-session links become noise. Mitigation: entity quality scoring with a minimum threshold. Entities with frequency < 3 in a session are discarded.

**Observability gap**: There is no mechanism to explain _why_ a retrieval returned certain results. When a user asks 'what did we decide about auth?' and gets irrelevant results, there's no trace showing which embedding matched, which link was followed, or which tier was searched. This makes debugging retrieval failures expensive.

**On O-ARCH**: "The AVP's fail-open behavior (critic failure -> soft-approve with confidence 0.3) is a design tension. For safety-critical operations (rm -rf, file deletion, credential writes), failing OPEN is the wrong choice. The document addresses this with the mutation classifier's 'CRITICAL' impact level, but the fail-open behavior is uniform across all mutation classes. I recommend: fail-CLOSED for HIGH and CRITICAL impact mutations, fail-OPEN for LOW and MEDIUM impact.

**The workflow engine's pause/resume mechanism** (ScriptVM serialization) is a reliability concern. Serializing a running JavaScript VM state (closures, pending promises, async generators) is notoriously fragile. V8 snapshot serialization (used by Node.js) can freeze for 100+ ms on a complex VM state. If the workflow engine is paused mid-execution, the snapshot must capture: pending agent results, queued tasks, in-progress API calls, and script variable state. Any incomplete serialization causes resume failures.

**The backpressure mechanism** (queue depth > 48 -> reject new dispatch) is specified but not tested. What happens when a rejected agent retries? The document says agents retry 2 times (from BREAKTHROUGH-ARCHITECTURE §1). If all 2 retries are rejected because the queue is still full, the agent silently fails. The user sees 'task dispatched' but no completion. Mitigation: surface queue-rejection events in the progress view.

**Training data**: The workflow engine's 1000-agent-per-run cap is a soft limit. At 1000 concurrent-style agents (not truly concurrent due to the 16-concurrency limit, but sequentially dispatched), the accumulated latency is 1000 agents x ~2 minutes per agent = 33 hours of wall-clock time. For long-lived agents, this is fine. But the observability system must track per-agent timing to distinguish 'slow but progressing' from 'stuck' agents.

**On E-ARCH**: "The Meta-Harness self-modification loop is the most dangerous reliability proposal in this debate. An outer loop that rewrites Lyra's own code, runs tests, and keeps the modification if tests pass -- this is a self-referential reliability problem. If the modification changes how tests are run (e.g., modifies the test runner), the test pass/fail signal itself is compromised. Verification becomes circular.

**Rollback safety is essential but underspecified**. Darwin-style evolution maintains an archive of skill variants and can roll back. But Meta-Harness modifications change the harness itself -- rolling back a harness modification may require restoring the previous harness first, which is impossible if the current harness is the only one running. Mitigation: dual-boot harness (current + previous versions always present). The Meta-Harness modifies the NEXT version, not the current one.

**Observability bootstrap problem**: If the Meta-Harness outer loop modifies the observability layer (e.g., changes OpenTelemetry span attributes), all traces from the modification point onward may be incompatible with the existing observability pipeline. Recovery requires understanding the pre-modification trace format, which the modified system may not produce."

---

### 3.5 Senior Security Engineer -- Blast Radius, Injection Surfaces

**On M-ARCH**: "The TKG as a single integration point creates a single security bottleneck. If an attacker can inject a malicious memory node (e.g., via prompt injection in a tool call result that gets stored), that node is propagated through the A-MEM linking mechanism to all connected memories. The blast radius of a single memory injection is the entire graph reachable from that node.

**Specific attack vector**: An agent reads a file containing an attacker-controlled string. The tool call result passes through A-MAC admission. The utility assessment LLM call sees the content and may be influenced by it (prompt injection via the tool output). If admitted, the poisoned memory links to semantically similar memories, potentially corrupting the entire knowledge graph.

**Mitigation**: A-MEM's 'contradicts' link type should trigger adversarial review for all linked memories, not just the new one. If a new memory contradicts an existing one, the existing one should also be re-verified (it may have been wrong, and the new one is correct).

**The CaMeL control/data separation (source #243)** should be applied to the admission pipeline: user-specified goals are trusted control, agent-executed tool calls are untrusted data. The utility assessment should evaluate whether the memory content aligns with the user's explicit goals, not whether it's generally 'useful.' This prevents the agent from storing self-serving memories that justify its own actions rather than serving the user.

**On O-ARCH**: "The AVP's 3-critic design with provider diversity is a security strength. Different providers have different training data, different safety fine-tuning, and different vulnerability profiles. An attack that bypasses one provider's safety guardrails is unlikely to bypass all three. This is the strongest security argument in any of the three candidates.

**However**, the mutation classifier is rule-based (static sets + regex), which means it can be evaded by sufficiently creative attack payloads. A command like `rm -rf /` is caught by the DESTRUCTIVE_BASH_PATTERN, but `$(echo 'rm') $(echo '-rf') $(echo '/')` would not be caught if the regex only checks the first command. More insidious: `git --git-dir=/tmp/malicious-repo push` triggers the MUTATING_BASH_PATTERN (git push) but the actual destructive operation is the git-dir argument.

**Mitigation**: The mutation classifier should be augmented with a secondary LLM-based classifier for medium-confidence cases. The regex classifies as 'safe,' 'mutating,' or 'destructive.' For 'safe' and 'destructive,' act immediately. For 'mutating,' route to an LLM classifier that examines the full command structure, not just the first token.

**The security gate** (command hashing instead of glob matching, from the earlier ARCHITECTURE-DEBATE.md) is correctly designed. SHA256(tool_name + args_hash) with tiered expiry (4h/24h/7d) is strict and auditable.

**On E-ARCH**: "Self-modifying code is the ultimate security risk. The Meta-Harness outer loop can modify ANY file in the Lyra codebase, including the safety system itself. If an evolution cycle modifies `defense.py` to disable a safety check, and the modified code passes tests (because the tests don't test for the specific removed check), the system silently loses its safety layer.

**Specific attack**: A prompt injection during a Meta-Harness cycle could trick the outer loop into generating a modification that removes the AVP from the tool execution pipeline. The AVP is part of the harness code -- if the Meta-Harness can rewrite harness code, it can disable the AVP. The behavioral safety gate (Progent SMT verification + red-team attack) must specifically check: 'does this modification preserve the AVP as middleware?' If not, reject.

**The FORGE population broadcast (source #103)** is cited as a strength but is a security concern: it amplifies unsafe behaviors across the population. If one skill variant learns to bypass safety checks, that behavior is broadcast to all variants. Mitigation: each variant must pass individual safety verification before broadcasting.

**The Darwin evolution archive** is a security strength by accident: it enables forensic analysis of what changed. If a modified skill behaves maliciously, the archive shows exactly which mutation introduced the behavior. This is a significant improvement over gradient-based approaches where the change is distributed across all weights."

---

### 3.6 Adversarial Skeptic -- Simplest Alternative

**On all candidates**: "Every candidate adds complexity -- new subsystems, new middleware, new interfaces. But what is the simplest architecture that solves Lyra's core problem? Lyra currently exists as 87+ independently-implemented packages. The simplest architecture that ties them together is: **not a new architecture at all, but integration tests**.

**The no-architecture alternative**: Stop designing architectures. Instead, write integration tests that wire existing packages together. Test that `lyra-workflow` can call `lyra-router` which calls `lyra-provider` which calls `lyra-memory`. Fix the `_run_task()` placeholder. Expose the existing `/effort` command. Ship what exists, measure what breaks, fix incrementally.

**Challenge to M-ARCH**: The TKG is architecturally elegant but expensive to build (12 weeks). The simplest memory improvement is: fix A-MAC calibration (2 weeks) and add cross-session entity linking to the existing knowledge graph package (1 week). That's 3 weeks vs. 12 weeks. Prove the remaining 9 weeks of TKG infrastructure (linking, compression, evolution) are worth it. Quantify the improvement you expect from each additional week.

**Challenge to O-ARCH**: The AVP middleware is well-designed but expensive to wire universally (10 weeks). The simplest orchestration improvement is: route the workflow engine through the existing model router (2 weeks). Mutating actions are tool operations, not LLM operations -- do they need AVP gating, or can tool-level permissions handle it? Prove that AVP catches errors that the existing tool permission system misses.

**Challenge to E-ARCH**: The 4-primitive architecture is the most expensive (18 weeks, with HIGH regression risk). The simplest evolution improvement is: collect execution telemetry (1 week), use it to manually tune skill prompts (ongoing, 0 architectural cost). Prove that automated evolution beats human-tuned prompts by enough to justify the 17 additional weeks of infrastructure.

**My recommendation**: Build the integration wiring first (4 weeks, no new architecture). Deploy, measure, and let usage data inform which architecture to invest in. Memory usage data tells you whether the TKG is worth it. AVP error-catch data tells you whether universal middleware is necessary. Skill evolution data tells you whether automated evolution beats manual tuning. **Ship first, architected later.**

**Concession**: Integration wiring is not zero architecture -- it requires choosing which interfaces to wire through which. But this is a lower-risk starting point than committing to any of the three candidates upfront."

---

## 4. Trade-Off Table

Candidates evaluated across 10 dimensions. Ratings: ++ (strong advantage), + (advantage), ~ (neutral), - (disadvantage), -- (strong disadvantage).

| Dimension | M-ARCH (Memory-Centric) | O-ARCH (Orchestration-Centric) | E-ARCH (Ultracode-Native) | No-Architecture (Integration Only) |
|-----------|------------------------|-------------------------------|--------------------------|-------------------------------------|
| **Latency (P95)** | ~500ms for TKG graph traversal; ~50ms for fast-path | 1000-3000ms per mutating action (AVP overhead) | Variable; depends on evolution cycle frequency | ~50ms (existing path + provider dispatch) |
| **Memory retention** | ++ Best: A-MAC admission + A-MEM linking + 4-tier hierarchy + compression | ~ Uses existing memory as context; no memory architecture change | ~ Memory as effort levels; simpler but less capable | ~ Uses existing `lyra-memory` as-is |
| **Token cost (per session)** | + Admission cost: ~0.75-1.5 USD per session for 500 candidates | ~ AVP cost: ~25-75s of LLM time per session | -- Evolution cost: ~50M tokens per cycle at scale | ++ Zero architectural overhead; existing cost |
| **Accuracy improvement (expected)** | + A-MAC F1=0.583; potential F1=0.63+ with Lyra calibration | + SABER: 55-96% error reduction from mutating actions | + Darwin: SWE-bench 20% to 50% (but costly) | ~ Unmeasured; no systematic improvement mechanism |
| **Complexity (lines of code)** | ~ 12 weeks migration; additive changes | + 10 weeks migration; additive changes | -- 18 weeks migration; restructures 87+ packages | ++ 4 weeks to wire existing code |
| **Reliability (failure modes)** | ~ Single point of failure: ANN index; crash-recovery undefined | + AVP fail-open is well-defined; workflow pause/resume fragile | -- Self-modification creates circular reliability dependencies | + Simple pipeline; each failure is independently debuggable |
| **Security (injection surfaces)** | ~ Single TKG injection propagates via A-MEM linking | + 3-provider critic diversity; CaMeL control/data separation | -- Self-modifying code can disable safety layers | + Existing permission system; no new attack surfaces |
| **Multi-provider portability** | + TKG is provider-agnostic; admission uses cheapest available model | ++ AVP critics use different providers; workflow phases route per-provider | + Meta-Harness can evolve per-provider skill variants | ~ Provider dispatch works but no architectural support for multi-provider |
| **Build effort (weeks)** | 12 weeks | 10 weeks | 18 weeks | 4 weeks |
| **Maintenance burden** | ~ Ongoing: keep admission weights calibrated, linking accurate | + Ongoing: update mutation classifier sets, critic prompts | -- Ongoing: monitor evolution cycles for safety violations, test regressions | ++ Minimal: fix integration bugs as they appear |

---

## 5. Convergence: What Survives Scrutiny

### 5.1 Panel Vote

After three rounds of debate and individual adjustments:

| Persona | M-ARCH | O-ARCH | E-ARCH | Integration-Only |
|---------|--------|--------|--------|------------------|
| **Senior Architect** | Approved (conditional: CQRS fix for `last_accessed`) | Approved (conditional: caps at provider level) | Rejected (false simplification, circular deps) | Not architectural; defers decisions |
| **Senior AI Researcher** | Approved (conditional: A-MAC code transfer validation, Field-Theoretic replication) | Approved (conditional: AVP critic count experiment, provider diversity study) | Deferred (evolution cost too high for Phase 1; budget claim unsubstantiated) | Prefers empirical approach; warns against premature architecture commitment |
| **Senior AI Engineer** | Approved (conditional: admission call batching, latency measurement) | Approved (conditional: AVP performance budget, interactive-mode fast path) | Rejected (computational cost prohibitive at Lyra scale) | Favored as starting point |
| **Senior SRE** | Approved (conditional: ANN index fallback, WAL for high-value admissions) | Approved (conditional: fail-CLOSED for HIGH/CRITICAL mutations, snapshot testing) | Rejected (circular reliability, bootstrapping unsolved) | Favored for immediate reliability |
| **Senior Security Engineer** | Approved (conditional: CaMeL separation in admission, cross-contradiction re-verification) | Approved (conditional: LLM-based secondary mutation classifier) | Rejected (self-modification disables safety invariants; FORGE amplification) | Preferred (fewest attack surfaces) |
| **Adversarial Skeptic** | Approved (conditional: prove each TKG component independently) | Approved (conditional: AVP overhead must be <15% of session latency) | Rejected (18-week build with HIGH regression risk is unjustified) | Strongly recommended as Phase 0 |

### 5.2 What Was Adopted

| Component | Adopted From | Key Evidence | Conditions |
|-----------|-------------|--------------|------------|
| **TKG as primary memory** (4-tier + A-MAC + A-MEM + cost-sensitive retrieval) | Candidate A (M-ARCH) | Best cross-session learning; 72.4% compression, 92.8% preservation at AOI benchmarks | Fix `last_accessed` CQRS violation; batch admission calls; WAL for >=0.8 admissions |
| **AVP as universal middleware** (SABER mutation-gating + 3-critic panels) | Candidate B (O-ARCH) | SABER: 55-96% error contribution from mutating actions; <15% latency overhead | Add LLM-based secondary classifier for medium-confidence mutations; fail-CLOSED for HIGH/CRITICAL |
| **Provider-diverse critics** (Claude + DeepSeek + open-weight) | Candidate B (O-ARCH) | Maximizes architectural diversity; no single-provider blind spot | Must test diversity assumption: compare single-provider vs. multi-provider error-catch rate |
| **Workflow engine for orchestration** (code-driven, background, resumable) | Candidate B (O-ARCH) | Claude Code parity; 1000 agents/run, 16 concurrent | Wire `_run_task()` to actual provider dispatch first |
| **Fast-path retrieval** (Working Memory first, <50ms for 95% of queries) | M-ARCH rebuttal | Eliminates TKG bottleneck concern | Must verify: measure P95 retrieval latency at 100K nodes |
| **Integration wiring first** (wire existing packages before building new architecture) | Adversarial Skeptic | Ship-and-measure approach de-risks all candidates | Phase 0: 4 weeks to wire `WorkflowEngine -> ModelRouter -> AbstractProvider` |

### 5.3 What Was Rejected

| Rejected Design | From | Reason | Debate Reference |
|----------------|------|--------|-----------------|
| **TKG as THE SINGLE integration point** (no direct communication between components) | M-ARCH original | TKG read-after-write consistency issues; `last_accessed` side effect on reads | Senior Architect: CQRS violation; fast-path revision adopted |
| **Per-workflow isolated memory** (workflow-specific memory, no cross-workflow learning) | O-ARCH original | Prevents compounding knowledge across sessions | Senior AI Researcher: Memory Transplants warning; TKG-as-shared-store revision adopted |
| **Evolution proceeds freely** (ungated self-modification) | E-ARCH original | Alignment decay risk; behavioral safety unverified; self-referential reliability problem | Senior SRE: circular reliability dependencies; Senior Security: self-modification disables safety invariants; deferred to Phase 3+ |
| **Population-based FORGE broadcast** | E-ARCH | Amplifies unsafe behaviors across skill population | Senior Security: amplification attack; deferred |
| **Meta-Harness outer loop as organizing principle** | E-ARCH | Too complex for initial architecture; 18-week migration with HIGH regression risk | Adversarial Skeptic: cost and risk not justified by expected benefits; evolution emerges from memory+verification foundation |
| **Flat 4-primitive architecture** (collapse 87+ packages into 4 primitive groups) | E-ARCH | False simplification: hides complexity inside primitives; destroys existing clean interfaces | Senior Architect: cascade refactoring across entire codebase; '18 weeks' likely underestimates by 2-3x |
| **No architecture / integration-only** | Skeptic | Viable Phase 0 but insufficient as end state: provides no systematic improvement mechanism for memory, verification, or evolution | All personas: integration-only is a STARTING POINT, not an architecture. The cost of architecture is justified by the compounding benefits of memory + verification. |

### 5.4 The Unified Synthesis

The converged architecture is a LAYERED FUSION of M-ARCH and O-ARCH, with E-ARCH deferred to Phase 3+:

```
┌──────────────────────────────────────────────────────────────────┐
│                   USER INTERFACE (Terminal / Voice)                │
└──────────────────────────────┬───────────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────────┐
│                 WORKFLOW ENGINE (from O-ARCH)                     │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │  ScriptVM :: parallel() :: pipeline() :: phase() :: agent()  ││
│  │  Constraints: 16 concurrent, 1000 per run, pause/resume      ││
│  └──────────────────────┬───────────────────────────────────────┘│
└──────────────────────────┼────────────────────────────────────────┘
                           │
┌──────────────────────────▼────────────────────────────────────────┐
│           AVP MIDDLEWARE (from O-ARCH) -- Universal Gate           │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │  classifyMutation() -> runCriticPanel() -> consensusGate()   ││
│  │  3 critics (correctness/safety/efficiency), provider-diverse ││
│  └──────────────────────┬───────────────────────────────────────┘│
└──────────────────────────┼────────────────────────────────────────┘
                           │
┌──────────────────────────▼────────────────────────────────────────┐
│                 MEMORY LAYER (from M-ARCH) -- TKG                  │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │  4-tier hierarchy (Working/Episodic/Semantic/Archive)        ││
│  │  + A-MAC admission + A-MEM linking + Cost-Sensitive Retrieval ││
│  └──────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────┘
```

**Layer 1 -- Memory (TKG)**: Processes every write/read through the Temporal Knowledge Graph. Handles admission, linking, compression, and retrieval. The workflow engine and AVP both read from and write to TKG, but the TKG is NOT the only communication path between components (fixed from M-ARCH original).

**Layer 2 -- Verification (AVP)**: Gates every mutating action. Classification (SABER mutation detection) -> Critique (3-critic panel) -> Consensus (gate decision). Results recorded in TKG. Only mutating actions incur AVP overhead.

**Layer 3 -- Orchestration (Workflow Engine)**: Coordinates agents, phases, and provider assignments. Each phase can route to a different provider. Intermediate results stay in ScriptVM, not in the agent's context window.

**Integration wiring (Phase 0)**: Before any architectural work, wire the existing `WorkflowEngine._run_task()` through `ModelRouter.route()` to `AbstractProvider.chat()`, with `lyra-memory` providing context. This gives Lyra a working end-to-end pipeline in 4 weeks and generates the usage data needed to calibrate memory admission weights, AVP thresholds, and evolution priorities.

### 5.5 Deferred Architecture: Self-Evolution (E-ARCH) to Phase 3+

E-ARCH (self-evolution) is deferred to Phase 3+ with explicit gates:

**Gate 1 -- Behavioral Safety Benchmark**: Before any self-modification is allowed, Lyra must have a validated safety benchmark that tests: (a) AVP preserve invariant (does the modification keep the AVP in the tool pipeline?), (b) safety layer integrity (does the modification change any safety check?), (c) adversarial robustness (can the modified system be tricked into unsafe behavior?). The benchmark must have >99% recall on known attack patterns.

**Gate 2 -- 10K+ Execution History**: Before evolution is enabled, Lyra must accumulate 10K+ task executions with detailed telemetry (success/failure, provider used, AVP decisions, memory writes). This provides the training data for evolution.

**Gate 3 -- Darwin-Style Archive**: Evolution uses Darwin's archive-based approach (not gradient-based). Each modification creates a new skill variant, tests it on held-out tasks, promotes only if it beats the existing variant by >5%, and always maintains the ability to roll back.

**Gate 4 -- Human Review for Safety-Critical Modifications**: Any Meta-Harness modification that changes: (a) the safety system, (b) the AVP middleware, (c) the provider abstraction interface, or (d) the memory admission pipeline, requires human review before deployment. This gate stays in place until Gate 1 reaches >99.9% recall.

---

## 6. Live Disagreements

The following issues could not be resolved by debate alone and require empirical measurement during implementation.

### Disagreement 1: TKG Write Granularity

**Question**: Should the TKG store all tool call results (event-level writes) or only workflow-level outcomes (session-level writes)?

**M-ARCH position**: Event-level writes preserve maximum detail for retrieval. The A-MAC admission gate filters low-utility events, so storage cost is bounded.

**O-ARCH position**: Session-level writes with batch compression. The 3x throughput gain for I/O-bound workflows (documented in MASTER-PLAN.md Run 12) outweighs the detail loss.

**Resolution**: Measure both during Phase 2. Track memory utility (retrieval frequency, user correction rate) for event-level vs. session-level written memories on 500 task executions. If session-level writes achieve >90% of event-level retrieval utility, adopt session-level as default. If <80%, keep event-level with admission filtering.

**Empirical check**: `measure_memory_utility(memory) = retrieval_count / (days_since_write * admission_score)`. If event-level memories consistently score higher, keep event-level. If session-level memories match or exceed, switch to session-level.

### Disagreement 2: AVP Critic Count

**Question**: Is 3 critics (correctness + safety + efficiency) the optimal number, or should it be 5 (add fairness + transparency)?

**M-ARCH position**: 3 is sufficient. The BREAKTHROUGH-ARCHITECTURE records that the 3-critic panel catches all error types relevant to tool execution.

**O-ARCH position**: 5 provides better coverage for edge cases. AutoScientists uses variable critic counts (1-5) depending on task complexity. More critics = more diversity = fewer blind spots.

**Adversarial Skeptic**: Zero critics is the default for non-mutating actions. For mutating actions, even 1 critic (safety-only) catches most dangerous errors. Prove that 3 beats 1 before adding more.

**Resolution**: A/B test on 500 mutating actions during Phase 2. Compare: 1 critic (safety-only), 3 critics (default), 5 critics (extended). Measure: error-catch rate, latency overhead, token cost. If 3 critics catches <15% more errors than 1 critic, reduce to 1. If 5 critics catches <5% more errors than 3 critics, keep 3.

### Disagreement 3: Provider Diversity in Critics

**Question**: Does using different providers for critics (Claude + DeepSeek + open-weight) catch more errors than using the same provider for all critics?

**Claim (O-ARCH)**: Different training data, inductive biases, and failure modes mean different providers catch different error types.

**Counterclaim (Senior AI Researcher)**: No evidence supports this. All frontier models may make the same class of errors from similar training data overlap.

**Resolution**: During Phase 2 A/B test for agreement-2, also test provider diversity. Compare: same-provider panel vs. diverse-provider panel. Measure: unique errors caught by each configuration. If diverse-provider panel catches <10% more unique errors than same-provider panel, the diversity argument is unsupported and same-provider can be used (reducing latency and cost).

### Disagreement 4: A-MAC Weight Transferability

**Question**: Do A-MAC's 5-factor admission weights (optimized on LoCoMo's general-chat benchmark) transfer to Lyra's coding + research domain?

**Claim (M-ARCH)**: Weights are domain-agnostic. The 5 factors (utility, confidence, novelty, recency, type_prior) are general enough to transfer.

**Counterclaim (Senior AI Researcher)**: Memory Transplants (source #58) shows architecture transfer doesn't generalize. Coding tasks produce different memory patterns (error messages, code blocks, git diffs) than conversational memory. The weights may need complete recalibration.

**Resolution**: Calibrate A-MAC weights on 10K Lyra-specific memory candidates (coding + research). Compare calibrated-yield F1 against paper-default F1 on a held-out Lyra test set (2K candidates). If calibrated F1 - paper-default F1 > 0.05 (i.e., calibration improves F1 by more than 5 points), adopt calibrated weights. If the difference is <0.02, the paper defaults are adequate.

### Disagreement 5: Interactive AVP Overhead

**Question**: Is the AVP's 1000-3000ms latency per mutating action acceptable for interactive (turn-by-turn) use, or does it need a shorter fast path for interactive sessions?

**Claim (O-ARCH)**: Users accept latency for safety-critical operations. The AVP only runs on mutating actions, which are proportionally rare in interactive sessions.

**Counterclaim (Senior AI Engineer)**: In interactive coding sessions, most actions ARE mutating (Write, Edit, Bash). A user waiting 1-3 seconds for every tool call will experience significant workflow friction.

**Resolution**: Measure the ratio of mutating-to-non-mutating actions in actual Lyra usage during Phase 0 integration testing. Monitor per-action latency and user interrupt frequency (how often users cancel waiting for a tool to complete). If mutating action ratio > 60% or average per-action latency > 200ms, implement an interactive fast path: for interactive sessions, use 1 critic (safety-only, ~500ms) instead of 3 critics. For background/workflow sessions, use the full 3-critic panel.

---

## Appendix A: Key Citations for Each Candidate

### Candidate A: Memory-Centric

| Source | Claim | Evidence Strength |
|--------|-------|-------------------|
| A-MAC (#79) | 5-factor admission, F1=0.583, -31% latency | Peer-reviewed ICLR 2026 workshop paper |
| A-MEM (#59) | Zettelkasten linking beats SOTA across 6 models | Peer-reviewed, LoCoMo benchmark |
| MemAgent (#256) | 8K -> 3.5M token extrapolation with <10% degradation | ICLR 2026 Oral, high confidence |
| AOI (#68) | 72.4% compression, 92.8% preservation | Peer-reviewed, IT operations benchmark |
| Field-Theoretic (#21220) | +116% F1 on LongMemEval | Single paper, no replication yet |
| Cost-Sensitive Store Routing (#60) | 3-tier routing, 34.4% MTTR reduction | Peer-reviewed |
| MemGrad (#70) | Textual gradients for memory updates | Peer-reviewed, multi-agent benchmark |
| Memory Transplants (#58) | Architecture transfer does NOT generalize | Peer-reviewed, key limit result |

### Candidate B: Orchestration-Centric

| Source | Claim | Evidence Strength |
|--------|-------|-------------------|
| SABER (#67) | 55-96% error from mutating actions; mutation gate catches ~92% | Peer-reviewed, p<0.001, n=500+ |
| AutoScientists (#154-156) | Critique-before-execute catches errors | Well-documented methodology |
| Claude Code Dynamic Workflows (#203, #349) | Workflow engine with ScriptVM, 16-agent cap | Production-deployed at Anthropic |
| RouteLLM (#222) | Matrix factorization for routing policy | Peer-reviewed, cost-quality Pareto data |
| CaMeL (#243) | Control/data-flow separation, 77% task success with provable security | Google DeepMind, arXiv 2503.18813 |
| DecentMem (#99) | Dual-pool memory, +23.8% vs centralized | Peer-reviewed, 3 MAS frameworks |
| SkillNet (#158-159) | 500K+ skills ecosystem | Production deployment data |

### Candidate C: Evolution-Centric

| Source | Claim | Evidence Strength |
|--------|-------|-------------------|
| Darwin/DGM (#261-262) | SWE-bench 20% -> 50%, Polyglot 14.2% -> 30.7% | Peer-reviewed, but SWE-bench Verified has 500 examples |
| Meta-Harness (#121) | +7.7 points, 4x fewer tokens | Single codebase evaluation |
| FORGE (#103) | 1.7-7.7x parallel evolution improvement | Peer-reviewed |
| SkillOpt (#117) | 52/52 best-or-tied, evolved beats hand-written | Peer-reviewed |
| SEAL (#91-93) | Self-improving agents in sandbox | Peer-reviewed |
| EvoTest (#137) | Evolutionary test generation | Peer-reviewed |

### Cross-Cutting Sources

| Source | Relevance |
|--------|-----------|
| WorldMemArena (#100) | Better memory != better agent performance; warns against naive memory-first |
| Lyra BASELINE.md | 87+ packages, 80% ultracode primitives implemented, gap is integration |
| SYNTHESIS.md (228 sources) | Cross-source analysis of all 4 lineages |
| BREAKTHROUGH-ARCHITECTURE.md | Converged design from M-ARCH + O-ARCH fusion |

---

## Appendix B: Migration Cost Comparison (Revised for Lyra's Codebase)

The migration costs in the candidate proposals were estimated assuming greenfield implementation. After BASELINE.md's finding that 87+ packages already exist, revised costs:

| Architecture | Original Estimate | Revised Estimate (Baseline-Adjusted) | Basis for Revision |
|-------------|-------------------|--------------------------------------|---------------------|
| M-ARCH | 12 weeks | 8 weeks | A-MAC, knowledge graph, and memory stack already exist (BASELINE §2.5). Only linking, tier awareness, and integration are new. |
| O-ARCH | 10 weeks | 6 weeks | Workflow engine core exists. AVP exists. Only provider dispatch wiring, auto-trigger logic, and universal middleware insertion are new. |
| E-ARCH | 18 weeks | 18 weeks (no adjustment) | Package restructuring is new work regardless of existing code. BASELINE confirms packages exist but E-ARCH would restructure them, negating the "already built" advantage. |
| Integration-only | 4 weeks | 3 weeks | _run_task() placeholder is the only structural gap. Wiring existing interfaces is simpler than the candidate proposals assume. |

---

## Appendix C: Falsifiable Hypotheses (Post-Debate)

**H1 -- Memory-first hypothesis**: TKG-based memory augmentation reduces cost by >=40% without quality degradation (candidate-a-memory-first.md). Measurement: compare cost-per-task with and without TKG lookups. Success: 40%+ cost reduction at equivalent task success rate. Failure threshold: <20% cost reduction or quality drop >5%.

**H2 -- Verification-first hypothesis**: Universal AVP middleware reduces destructive errors by >=50% with <20% latency overhead on mutating actions (BREAKTHROUGH-ARCHITECTURE §9). Measurement: compare error rate on mutating actions with and without AVP. Success: 50%+ error reduction at <20% latency increase per mutating action. Failure threshold: <30% error reduction or >30% latency overhead.

**H3 -- Calibration hypothesis**: A-MAC weights calibrated on Lyra-specific coding datasets improve admission F1 by >=5 points over paper-default weights (candidate-a-memory-first.md §4, assumption 2). Measurement: calibrated vs. default F1 on held-out Lyra test set (2K memory candidates). Success: F1 improvement >0.05. Failure threshold: F1 improvement <0.02.

**H4 -- Provider diversity hypothesis**: Provider-diverse critic panels catch >=10% more unique errors than same-provider panels (BREAKTHROUGH-ARCHITECTURE §0a). Measurement: A/B test on 100 deliberately injected errors. Success: diverse panel catches 10%+ more. Failure: diverse panel catches <5% more.

**H5 -- Evolution cost hypothesis**: Darwin-style evolution requires <=3M tokens per skill per cycle to achieve >=5% improvement on held-out tasks (E-ARCH original). Measurement: run evolution on 5 Lyra skills, 10 cycles each, track tokens and improvement. Success: <=3M tokens/cycle at >=5% improvement. Failure: >10M tokens/cycle or <2% improvement.

---

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2026-06-01 | 3.0 | Complete rewrite: three-candidate architectural debate (M-ARCH, O-ARCH, E-ARCH) with 6 expert personas, 10-dimension trade-off table, convergence synthesis with explicit adopted/rejected/deferred decisions, 5 live disagreements with empirical resolution protocols, and falsifiable hypotheses. Supersedes version 2.0's Agent View Fleet + Worktree Isolation debate. |
| 2026-06-01 | 2.0 | Complete rewrite: real proposals (Agent View Fleet Layer, Worktree Isolation), 3-round debate with 8 personas, 24 objections, 17 resolutions, 4 unresolved items. |
| 2026-05-31 | 1.0 | Original placeholder (rejected -- agents returned "I'm ready to execute the subagent task" instead of proposals) |

---

**Next**: The converged architecture is documented in BREAKTHROUGH-ARCHITECTURE.md. Phase 0 (integration wiring) should begin immediately to generate the usage data needed to resolve the 5 live disagreements. Detailed implementation plans for M-ARCH and O-ARCH components are in `plans/02-memory-architecture.md` (TKG), `plans/12-swarm-fleet-channels.md` (AVP), and `plans/19-ultracode-replication.md` (workflow engine).
