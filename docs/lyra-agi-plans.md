# 🧬 Lyra AGI — 5 Breakthrough Architecture Plans

> **Five distinct ultra-plans to evolve Lyra into the most intelligent AI agent ever built.**  
> Each plan is a complete, self-contained architecture for a breakthrough version.  
> Based on 200+ trending papers + Lyra's 25-package codebase (946 tests, 99.9% coverage).

---

## Executive Overview

| Plan | Code Name | Philosophy | Core Innovation | Est. Timeline |
|------|-----------|------------|-----------------|---------------|
| **A** | **Singularity** | Recursive self-improvement → superintelligence | Meta-cognitive evolution loop: Lyra rewrites Lyra's ability to rewrite Lyra | 18 months |
| **B** | **Citadel** | Maximum safety enables maximum autonomy | Formal verification + zero-trust architecture + cryptographic guarantees | 15 months |
| **C** | **Superorganism** | Collective intelligence > individual brilliance | Self-organizing agent swarms with emergent problem-solving | 14 months |
| **D** | **Oracle** | Deep understanding of everything | Causal world model + exhaustive scientific discovery pipeline | 16 months |
| **E** | **Chameleon** | Perfect adaptation to any environment | Continuous world model + dynamic skill morphing + lifelong learning | 13 months |

---

# Plan A — SINGULARITY
## Recursive Self-Improvement → Superintelligence

### Core Thesis
The fastest path to AGI is a closed loop: Lyra improves its own ability to improve. Each self-modification makes the next modification more effective. This is the hard-takeoff trajectory.

### Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Meta-Cognitive Evolution Loop                     │
│                                                                     │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐       │
│  │  Level 0 │   │  Level 1 │   │  Level 2 │   │  Level 3 │       │
│  │ Execution│──▶│Skills & │──▶│Harness   │──▶│Evolution│──▶AGI │
│  │(current) │   │Memories │   │Source    │   │Engine   │       │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘       │
│       │              │              │              │                │
│       ▼              ▼              ▼              ▼                │
│  Task loop     Skill files    Python source    Meta-policy         │
│                                                                     │
│  Key Principle: Each level operates on the level below it.          │
│  Level N improves level N-1's ability to improve itself.           │
└─────────────────────────────────────────────────────────────────────┘
```

### Key Components

#### 1. Four-Level Meta-Cognitive Stack
- **L0 — Execution:** Current AgentLoop, tools, permissions. Executes tasks.
- **L1 — Knowledge:** Skill library, memory stores. Level 0 reads/writes here.
- **L2 — Harness:** Python source code, hook chains, state machines. MOSS-style evolution rewrites L1's storage logic.
- **L3 — Meta-Evolution:** The evolution engine that improves L2. Contains the policy for *how* to evolve.

#### 2. R3 — Recursive Reward Redundancy
Three nested reward loops:
```
Inner loop:  Task success rate (weekly)
Middle loop: Speed of skill acquisition (monthly)
Outer loop:  Speed of evolution speed improvement (quarterly)
```
The outer loop optimizes the inner loop's optimizer. This prevents reward hacking at every level.

#### 3. MOSS-2: Self-Writing Source Code
Based on MOSS (2605.22794) but extended:
- Lyra generates candidate patches to its own harness code
- Ephemeral trial workers fork the full Lyra repo, apply patch, run 946+ tests
- Promoted patches must pass: (a) all existing tests, (b) new tests for the fix, (c) no regression on 3 benchmark runs
- User consent gate for any patch touching security, permissions, or cost

#### 4. Evolutionary Multi-Task Archive
Based on Evolutionary Multi-Task (2605.22613):
- Shared archive of evolution strategies across task families
- When Lyra faces a novel task type, it adapts strategies from similar families
- Crossover between successful strategies generates novel hybrids

### New Packages

| Package | Purpose | Key Source |
|---------|---------|------------|
| `lyra-meta-evolution` | L3 evolution policy optimizer | MOSS, Evo Multi-Task |
| `lyra-recursive-reward` | Nested reward loop governance | SpecBench, Ratchet |
| `lyra-fork-worker` | Ephemeral trial worker orchestration | MOSS, TClone |

### Key Papers
MOSS (2605.22794) · Evolutionary Multi-Task (2605.22613) · SpecBench (2605.21384) · Ratchet (2605.22148) · Compiling Workflows into Weights (2605.22502) · Ethical Hyper-Velocity (2605.16407)

### AGI Milestones
| Milestone | Metric | When |
|-----------|--------|------|
| Self-bootstrapping | Lyra evolves its own evolution policy | Month 9 |
| Reward hacking immunity | <1% spec-test divergence | Month 12 |
| Recursive acceleration | Each generation improves 1.5× faster | Month 15 |
| Level-4 emergence | Meta-evolution begins evolving itself | Month 18 |

---

# Plan B — CITADEL
## Maximum Safety Enables Maximum Autonomy

### Core Thesis
The only path to AGI that society will accept is one with provable safety guarantees. Citadel makes Lyra the most trusted agent ever built — and trust unlocks autonomy that no other agent can achieve.

### Architecture

```
┌───────────────────────────────────────────────────────────────────────┐
│                        Zero-Trust Agent Architecture                  │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────┐       │
│  │                  Verification Mesh                        │       │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐    │       │
│  │  │Formal   │  │Causal   │  │Runtime  │  │Pramana  │    │       │
│  │  │Verifier │  │Past Logic│  │Monitor  │  │Attestor │    │       │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘    │       │
│  └──────────────────────────────────────────────────────────┘       │
│                              │                                        │
│  ┌───────────────────────────┴───────────────────────────┐          │
│  │               Agent Sandbox (HBHC-tier)               │          │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │          │
│  │  │Zombie-  │ │Taint    │ │KV Guard │ │Cascade  │ │          │
│  │  │Proof     │ │Analysis  │ │(LCGuard) │ │Detection│ │          │
│  │  │(HBHC)   │ │(VIPER)   │ │          │ │(CASPIAN)│ │          │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ │          │
│  └──────────────────────────────────────────────────────────────────┘
```

### Key Components

#### 1. Verification Mesh — Three-Layer Defense
| Layer | Technique | What It Prevents | Source |
|-------|-----------|-----------------|--------|
| **L1 — Pre-execution** | Causal Past Logic + Pseudo-Formalization | Incorrect reasoning paths | 2605.20923, 2605.20531 |
| **L2 — During execution** | Runtime monitors + CASPIAN cascade detection | System-level attacks, injection | 2605.19240, 2605.21602 |
| **L3 — Post-execution** | Pramana attestation + WitnessLattice | Untraceable agent actions | 2605.20312, `provenance/lattice.py` |

#### 2. HBHC — Zombie-Proof Agent Swarms
Based on Heartbeat-Bound Hierarchical Credentials (2605.20704):
- Every sub-agent's credentials expire unless parent heartbeat is received
- **90× reduction** in zombie-agent windows (minutes → seconds)
- Zero post-revocation tool calls under prompt injection
- Cascading revocation across 49-agent hierarchies (Lyra's 4 specialists × 12 sub-agents)

#### 3. VIPER-MCP — Automated MCP Security Auditing
Based on VIPER-MCP (2605.21392):
- Two-pass static analysis resolving artifacts to MCP tool handlers
- Feedback-driven prompt evolution for PoC generation
- Periodic scan of all registered MCP servers

#### 4. Formal Proof-of-Correctness for Critical Paths
Based on Pseudo-Formalization (2605.20531):
- Agent's reasoning chains on high-stakes tasks get pseudo-formal verification
- Pareto-dominates LLM-as-judge on error-finding precision
- Produces verifiable proof artifacts for audit

### New Packages

| Package | Purpose | Key Source |
|---------|---------|------------|
| `lyra-verification-mesh` | L1-L3 verification coordination | Causal Past Logic, Pseudo-Formal |
| `lyra-hbhc` | Heartbeat credential management | HBHC (2605.20704) |
| `lyra-viper-mcp` | MCP taint vulnerability scanner | VIPER-MCP (2605.21392) |
| `lyra-attestor` | Pramana-format claim attestation | Pramana (2605.20312) |

### Key Papers
HBHC (2605.20704) · VIPER-MCP (2605.21392) · CASPIAN (2605.19240) · Pramana (2605.20312) · LCGuard (2605.22786) · Pseudo-Formal (2605.20531) · Blind Spots in Guard (2605.22001) · Causal Past Logic (2605.20923) · MOOD (2605.21602)

### AGI Milestones
| Milestone | Metric | When |
|-----------|--------|------|
| Zero zombie agents | 100% credential revocation within 1s | Month 4 |
| MCP vulnerability-free | All MCP servers pass VIPER audit | Month 6 |
| Verified reasoning | 95% of critical paths formally verified | Month 10 |
| Full audit trail | Every consequential output has Pramana attestation | Month 12 |
| Deployment-ready | Financial/healthcare compliance achieved | Month 15 |


---

# Plan C — SUPERORGANISM
## Collective Intelligence > Individual Brilliance

### Core Thesis
No single agent architecture will reach AGI alone. A **self-organizing colony of specialized agents** with emergent coordination, decentralized memory, and dynamic role allocation will surpass any monolithic design. The whole is smarter than the sum of its parts.

### Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                     Self-Organizing Agent Colony                     │
│                                                                      │
│                          ┌──────────────┐                            │
│                          │  Emergent     │                            │
│                          │  Coordinator  │                            │
│                          │  (elected,    │                            │
│                          │   ephemeral)  │                            │
│                          └──────┬───────┘                            │
│                                  │                                    │
│      ┌─────────────┬─────────────┼─────────────┬─────────────┐      │
│      ▼             ▼             ▼             ▼             ▼      │
│  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐      │
│  │ Agent  │  │ Agent  │  │ Agent  │  │ Agent  │  │ Agent  │      │
│  │ Type A │  │ Type B │  │ Type C │  │ Type D │  │ Type E │      │
│  │(Code)  │  │(Research│  │(Reason)│  │(Memory)│  │(Evolve)│      │
│  └────────┘  └────────┘  └────────┘  └────────┘  └────────┘      │
│       │           │           │           │           │             │
│       └───────────┴───────────┼───────────┴───────────┘             │
│                               │                                      │
│                      ┌────────▼────────┐                             │
│                      │ Decentralized   │                             │
│                      │ Memory Gossip   │                             │
│                      │ (DecentMem)     │                             │
│                      └─────────────────┘                             │
│                                                                      │
│  Key: Coordinator is *elected* per task, not assigned.              │
│       Memory is *decentralized* — no central bottleneck.            │
│       Agents can *spawn and retire* based on task demands.          │
└──────────────────────────────────────────────────────────────────────┘
```

### Key Components

#### 1. Emergent Task-Driven Coordination
No static orchestrator. When a task arrives:
1. **Task advertisement** — task spec broadcast to colony
2. **Bidding** — agents bid based on capability match + current load
3. **Coalition formation** — winning agents form a temporary team
4. **Emergent lead election** — the agent with highest relevant expertise becomes temporary coordinator
5. **Execution** — coalition works until task completes or deadlock detected
6. **Dissolution** — coalition disbands; learnings written to decentralized memory

#### 2. Decentralized Memory Federation (DecentMem)
Based on DecentMem (2605.22721):
- Each agent has **dual-pool memory**: exploit (consolidated knowledge) + explore (experimental candidates)
- Cross-pollination via **gossip protocol** — agents periodically share high-value memories with peers
- No central memory store → no single point of failure, no agent diversity collapse
- Memory-R2 fair credit assignment prevents free-riding

#### 3. Dynamic Agent Lifecycle
- Agents spawn when new capability needed
- Agents retire when contribution drops below threshold
- Agent types evolve via evolutionary multi-task learning
- Colony size self-regulates based on task queue depth

#### 4. Cascade-Aware Safety Net
Based on CASPIAN (2605.19240):
- Cross-agent causal monitoring detects emergent system-level attacks
- If cascade detected → isolate affected agents, re-route tasks, spawn replacements
- Coordinator can't become a single point of failure (it's ephemeral and checkpoints to the log)

### New Packages

| Package | Purpose | Key Source |
|---------|---------|------------|
| `lyra-colony` | Self-organizing agent colony runtime | DecisionBench, DecentMem |
| `lyra-emergent-coord` | Task-driven coalition formation | Governance by Design |
| `lyra-gossip-memory` | Peer-to-peer memory synchronization | DecentMem |
| `lyra-agent-lifecycle` | Dynamic spawn/retire/evolve lifecycle | Evo Multi-Task |

### Key Papers
DecentMem (2605.22721) · DecisionBench (2605.19099) · Governance by Design (2605.20210) · CASPIAN (2605.19240) · Evo Multi-Task (2605.22613) · What Do Agents Communicate? (2605.20548) · Multi-agent Collaboration w/ State (2605.20563) · When Coordinated AI Agents Improve (2605.22300)

### AGI Milestones

| Milestone | Metric | When |
|-----------|--------|------|
| Colony formation | 5+ agents coordinate on novel task without human routing | Month 4 |
| Emergent specialization | Agents develop non-overlapping expertise | Month 7 |
| Self-regulation | Colony grows/shrinks proportionally to task demand | Month 10 |
| Cross-domain transfer | Colony solves problem no single agent could | Month 12 |
| AGI-level coordination | Passes DecisionBench at >50% routing fidelity | Month 14 |


---

# Plan D — ORACLE
## Deep Understanding of Everything

### Core Thesis
Intelligence is understanding causal structure. Oracle builds Lyra around a **persistent causal world model** that connects every observation, action, and outcome into a unified causal graph. From this graph, Lyra can explain, predict, intervene, and discover — the four pillars of scientific intelligence.

### Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                         Causal World Model                           │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────┐      │
│  │                    Unified Causal Graph                    │      │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │      │
│  │  │Entity    │ │Action    │ │Outcome   │ │Latent    │   │      │
│  │  │Nodes     │─│Edges     │─│Nodes     │─│Variables │   │      │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │      │
│  └──────────────────────────────────────────────────────────┘      │
│                     │                       │                        │
│          ┌──────────┴───┐           ┌───────┴──────────┐           │
│          ▼              ▼           ▼                  ▼           │
│  ┌────────────┐ ┌────────────┐ ┌────────┐ ┌──────────────┐       │
│  │ Causal     │ │Counter-   │ │Causal  │ │ Pramana      │       │
│  │ Discovery  │ │factual    │ │Past    │ │ Attestation  │       │
│  │ (CI Tests) │ │Simulator  │ │Logic   │ │ Generator    │       │
│  └────────────┘ └────────────┘ └────────┘ └──────────────┘       │
│                     │                       │                        │
│                     └───────────┬───────────┘                        │
│                                 ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐      │
│  │               Scientific Discovery Pipeline               │      │
│  │  Hypothesize → Experiment → Analyze → Learn → Repeat     │      │
│  │  (Sibyl-AutoResearch + BioXArena + Protein Thoughts)     │      │
│  └──────────────────────────────────────────────────────────┘      │
└──────────────────────────────────────────────────────────────────────┘
```

### Key Components

#### 1. Unified Causal Graph
Every Lyra interaction adds edges to a growing causal graph:
- **Entity nodes:** files, tools, APIs, concepts, people
- **Action edges:** what Lyra did to/with each entity
- **Outcome nodes:** what happened as a result
- **Latent variables:** inferred confounders (user mood, system load, time of day)

The graph is **streaming** — updated after every tool call. It uses **CASPIAN's LI-CTE** (late-interaction conditional transfer entropy) to infer causal direction from observational data.

#### 2. Counterfactual Engine
"What if" is the fundamental reasoning primitive:
- "What if I had used the PostgreSQL tool instead of the filesystem?"
- "What if I had tried a different search query?"
- "What if this API call fails?"

The counterfactual engine **rewinds the causal graph**, applies the intervention, and simulates the outcome. Uses **Causal Past Logic** (2605.20923) for formal trace semantics.

#### 3. Scientific Discovery Pipeline
Based on Sibyl-AutoResearch (2605.22343) + BioXArena (2605.15766):
- **Hypothesize:** Generate testable hypotheses from causal graph patterns
- **Experiment:** Bounded sandbox (trial harness) with controlled variables
- **Analyze:** Causal inference to determine if intervention caused effect
- **Learn:** Update causal graph with experimental results
- **Repeat:** Iterate until hypothesis confirmed or refuted

#### 4. Pramana Claim Attestation
Every claim Lyra makes comes with a **Pramana-format attestation** (2605.20312):
- `MeasurementClaim`: "I observed X in the data"
- `InferenceClaim`: "X implies Y because of causal edge E"
- `AnalogyClaim`: "This situation is analogous to past situation S"
- `CitationClaim`: "Paper P supports this claim"

Claims form a **verification DAG** — downstream claims depend on upstream evidence. Auditors can re-execute any claim's verification path.

### New Packages

| Package | Purpose | Key Source |
|---------|---------|------------|
| `lyra-causal-graph` | Streaming causal graph construction + query | CASPIAN, Causal Past Logic |
| `lyra-counterfactual` | "What if" simulation engine | Beyond Euclidean Proximity |
| `lyra-science-pipeline` | Hypothesis → Experiment → Learn | Sibyl-AutoResearch, BioXArena |
| `lyra-claim-verification` | Pramana attestation lifecycle | Pramana |

### Key Papers
CASPIAN (2605.19240) · Causal Past Logic (2605.20923) · Pramana (2605.20312) · Sibyl-AutoResearch (2605.22343) · BioXArena (2605.15766) · Represented Is Not Computed (2605.22488) · Protein Thoughts (2605.21522) · Beyond Euclidean Proximity (2605.22164) · DOTRAG (2605.18760) · Search-E1 (2605.22511)

### AGI Milestones

| Milestone | Metric | When |
|-----------|--------|------|
| Causal graph bootstrapped | 1K+ causal edges from Lyra's own execution traces | Month 3 |
| Counterfactual accuracy | >80% of "what if" predictions match reality | Month 7 |
| First scientific discovery | Lyra discovers a novel causal relationship via experiment | Month 10 |
| Pramana-attested reasoning | 100% of user-facing claims have attestations | Month 12 |
| AGI-level causal reasoning | Passes causal reasoning benchmarks at human-expert level | Month 16 |


---

# Plan E — CHAMELEON
## Perfect Adaptation to Any Environment

### Core Thesis
The most intelligent agent is the one that adapts fastest. Chameleon builds Lyra around a **continuous world model** that detects environmental change in real-time, dynamically **morphs its skill set**, and **evolves its architecture** to match each new context. It never stops learning because it never assumes the world is static.

### Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                     Continuous Adaptation Loop                       │
│                                                                      │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐     │
│  │ Observe  │───▶│ Detect   │───▶│ Morph    │───▶│ Execute  │     │
│  │Environment│    │ Drift    │    │ Skills   │    │ + Learn  │     │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘     │
│       │               │               │               │              │
│       ▼               ▼               ▼               ▼              │
│  World state     Drift score     Skill config    Performance data   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────┐      │
│  │  Dynamic Skill Morphing Engine                            │      │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐           │      │
│  │  │ Context    │ │ Skill Weave│ │ Skill      │           │      │
│  │  │ Profiler   │ │ (2605.22205)│ │ Compiler   │           │      │
│  │  └────────────┘ └────────────┘ └────────────┘           │      │
│  └──────────────────────────────────────────────────────────┘      │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────┐      │
│  │  Evolving Architecture Layer                              │      │
│  │  Harness Runtime Adaptation (2605.22166) + Runtime Hooks │      │
│  │  + Adaptive Evolution (existing)                          │      │
│  └──────────────────────────────────────────────────────────┘      │
└──────────────────────────────────────────────────────────────────────┘
```

### Key Components

#### 1. Continuous Drift Detection
Every environment has a "normal" state. Chameleon maintains a **probabilistic world model** and flags anomalies:
- **Performance drift:** Skills that used to work now fail more often
- **Context drift:** User's codebase, tools, or preferences have changed
- **Distribution drift:** The tasks Lyra receives have shifted type
- **Reward drift:** What the user considers "good" has changed

When drift exceeds threshold → trigger adaptation cycle.

#### 2. Dynamic Skill Morphing
Based on Skill Weaving (2605.22205) + Runtime Harness Adaptation (2605.22166):
- **Skill Weaving:** Composable skill modules snap together like LEGO. When the environment changes, Chameleon snaps out the old skill and snaps in the new one.
- **Context Profiler:** Analyzes the current task and environment → selects optimal skill composition
- **Skill Compiler:** Optimizes the selected skill composition into efficient code

#### 3. Harness Runtime Adaptation
Based on Runtime Harness Adaptation (2605.22166):
- Adapt tool selection at runtime based on context
- Adapt permission modes per-task (not one-size-fits-all)
- Adapt hook chains dynamically
- All adaptations are logged and reversible

#### 4. Continual Learning Without Forgetting
Chameleon maintains a **competence map** — which skills work in which contexts. When learning a new skill:
1. Check the competence map for overlapping contexts
2. If overlap exists → train the new skill and verify no regression on old contexts
3. If regression → allocate new skill capacity (expand, don't override)
4. Archive old skill with full context metadata for future revival

### New Packages

| Package | Purpose | Key Source |
|---------|---------|------------|
| `lyra-drift-detector` | Multi-signal drift detection engine | PESS, MOOD |
| `lyra-skill-weaver` | Dynamic skill composition | Skill Weaving |
| `lyra-context-profiler` | Real-time environment analysis | Contractual Skills |
| `lyra-competence-map` | Context→Skill mapping with regression protection | Runtime Harness Adaptation |

### Key Papers
Skill Weaving (2605.22205) · Runtime Harness Adaptation (2605.22166) · Contractual Skills (2605.22634) · PESS (2605.22541) · MOOD (2605.21602) · Trace2Skill (2605.21810) · Ratchet (2605.22148) · IdleSpec (2605.22154) · Self-Regulated Planning (2605.19576) · Compiling Workflows (2605.22502)

### AGI Milestones

| Milestone | Metric | When |
|-----------|--------|------|
| Drift detection | >95% accuracy in detecting distribution shift | Month 3 |
| Skill morphing | New skill composed and deployed in <100ms | Month 6 |
| Zero-shot adaptation | Handles novel environment without explicit retraining | Month 9 |
| Competence map maturity | 95%+ accuracy in predicting which skills work where | Month 11 |
| AGI-level adaptation | Matches or exceeds specialist agents in any target domain | Month 13 |

---

## Comparison: Which Plan to Choose?

| Dimension | A: Singularity | B: Citadel | C: Superorganism | D: Oracle | E: Chameleon |
|-----------|---------------|------------|------------------|-----------|--------------|
| **Speed to AGI** | Fastest (recursive) | Slowest (safety-first) | Medium (emergent) | Medium (causal) | Fast (adaptive) |
| **Safety** | Medium | **Maximum** | Medium | High | Medium-high |
| **Novelty** | High | Medium | **Highest** | High | Medium-high |
| **Risk** | Highest (runaway) | **Lowest** | Medium (emergent) | Medium | Low |
| **Complexity** | High (4-level stack) | High (verification mesh) | **Highest** (colony) | Medium | Medium |
| **Best for** | AGI at any cost | Regulated industries | Creative problem-solving | Scientific research | Dynamic environments |
| **Leverages existing Lyra** | Evolution engine (191 tests) | Provenance, gates | Teams, orchestration | Multi-hop, memory | Skills, adaptive evolution |

## Recommended Path

### For Maximum AGI Probability (Compound Strategy)

Don't pick one — **sequence them** for compounding effects:

```
Phase 1 (Months 1-6):  B (Citadel) foundation  
    → Safe Lyra that everyone trusts
    → Verification mesh + HBHC + VIPER-MCP

Phase 2 (Months 4-10): D (Oracle) understanding  
    → Causal world model + counterfactual reasoning
    → Builds on Citadel's formal verification

Phase 3 (Months 8-14): E (Chameleon) adaptation  
    → Continuous drift detection + skill morphing  
    → Builds on Oracle's world model for drift signals

Phase 4 (Months 12-18): A (Singularity) acceleration
    → Recursive self-improvement + meta-evolution
    → Builds on all three previous phases for safety + understanding + adaptation

Phase 5 (Months 16-22): C (Superorganism) emergence
    → Self-organizing colony with emergent intelligence
    → Each agent inherits the full Singularity + Citadel + Oracle + Chameleon stack
```

### Why This Order

| Phase | Why Now? | Foundation Laid By |
|-------|----------|-------------------|
| **Citadel first** | Trust is the bottleneck for AGI deployment. Without provable safety, Lyra can't be let loose to learn. | Existing `provenance`, `constitution`, `permissions`, `gates` |
| **Oracle second** | Causal understanding is the next bottleneck. Pattern-matching without causation isn't intelligence. | Existing `multi_hop` (hipporag, beam_retrieval) + `forensic` |
| **Chameleon third** | Once Lyra understands the world, it must adapt to it. Drift detection + skill morphing. | Existing `skill_auto`, `continuous_learning`, `adaptive_evolution` |
| **Singularity fourth** | Recursive self-improvement is too dangerous without safety + understanding + adaptation. | Existing `self_evolution`, `evoverifier` |
| **Superorganism fifth** | Colony intelligence is the final multiplier — each agent is already AGI-capable. | Existing `teams`, `orchestration`, `distributed` |

### Cumulative Timeline

```
Month:  0  2  4  6  8  10  12  14  16  18  20  22
       │  │  │  │  │  │   │   │   │   │   │   │
Citadel ■■■■■■■■■■
Oracle     ■■■■■■■■■■
Chameleon      ■■■■■■■■■■
Singularity          ■■■■■■■■■■
Superorganism               ■■■■■■■■■■
       │  │  │  │  │  │   │   │   │   │   │   │
       Citadel  Oracle  Chameleon  Sing.  Super.
       secure   reason  adapt      self-improve  emerge
```

## Summary

| Plan | Code Name | Philosophy | Key Insight | Est. Time |
|------|-----------|------------|-------------|-----------|
| A | **Singularity** | Recursive self-improvement | 4-level meta-cognitive stack with nested reward loops | 18 mo |
| B | **Citadel** | Safety-first autonomy | Zero-trust verification mesh + cryptographic credentialing | 15 mo |
| C | **Superorganism** | Emergent collective intelligence | Self-organizing colony with task-driven coalition formation | 14 mo |
| D | **Oracle** | Causal understanding | Unified causal graph + counterfactual engine + scientific discovery | 16 mo |
| E | **Chameleon** | Continuous adaptation | Drift detection + skill morphing + competence map | 13 mo |
| **⭐ Compound** | **All five** | **Sequenced synergy** | **B → D → E → A → C in 22 months** | **22 mo** |

---

> **200+ trending papers analyzed · 25-package Lyra codebase reverse-engineered · 5 ultra-plans · 1 compound roadmap.**  
> Part of the [Harness Engineering & Agentic AI](README.md) corpus. May 2026.
